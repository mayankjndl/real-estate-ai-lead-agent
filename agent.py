"""
IREIOS Chat Orchestration (agent.py)

Two separate FSMs govern lead lifecycle — they are intentionally independent:

1. session.status (chat FSM): active → closed
   Controls follow-up scheduling. Closed means no more automated messages.

2. Lead.conversion_status (sales FSM): open → claimed
   Controls assignment stickiness. Claimed means a human owns the lead.

Full qualification closes the chat FSM but does NOT auto-claim the lead.
Only an explicit dashboard claim sets conversion_status = "claimed".

Canonical terminal-state table (P2.2):
| Event                  | session.status | follow_up       | whatsapp_opt_in | conversion_status |
|------------------------|----------------|-----------------|-----------------|-------------------|
| Normal chat            | active         | stopped→rearm   | true            | open              |
| Full qualify           | closed         | completed       | true            | open              |
| Opt-out                | closed         | stopped         | false           | unchanged         |
| Handoff                | closed         | stopped         | true            | open (stage=Contacted) |
| Claim on dashboard     | unchanged      | unchanged       | unchanged       | claimed           |
"""
import asyncio
import json
import logging
import re
import string
import time
from datetime import datetime, timedelta, timezone

from google.genai import types
from llm_client import client
from sqlalchemy.orm import Session as DBSession

from app.intelligence.agent_matcher import ensure_lead_assignment, hot_threshold_notification_reason
from app.intelligence.lead_scoring import calculate_lead_score
from config import settings

from models import Session, Message, Lead, EventLog
from notification_service import trigger_hot_lead_notification, SEVERITY_HANDOFF, SEVERITY_SCORE_ALERT
from rag import retrieve
from system_prompt import REAL_ESTATE_SYSTEM_PROMPT

logger = logging.getLogger("agent")
PUNE_AREAS = ["wakad road", "wakad", "hinjewadi", "baner", "kharadi", "kothrud", "hadapsar",
                  "ravet", "balewadi", "aundh", "pashan", "viman nagar", "magarpatta",
                  "kondhwa", "undri", "mundhwa", "punawale", "tathawade", "bavdhan",
                  "sinhagad road", "pune"]


def is_hinglish(text: str) -> bool:
    # Strong Hindi/Hinglish tokens only. Bare "me"/"ha"/"ka"/"ki"/"ko" are English
    # false positives ("let me share…", "ha ha") and must not trip the output guard.
    hinglish_keywords = {
        "kya", "hai", "hain", "mujhe", "mein", "chahiye", "tha", "bas", "nahi",
        "haan", "kab", "karna", "liye", "aapka", "apna", "humare", "ke",
    }
    words = set(text.lower().replace("?", "").replace(".", "").replace(",", "").split())
    return bool(words.intersection(hinglish_keywords))


def build_english_fallback_reply(lead) -> str:
    """P2.6 safe English reply that only asks for fields still missing on the lead."""
    _loc = (getattr(lead, "location", None) if lead else None) or "Pune"
    _pt = (getattr(lead, "property_type", None) if lead else None) or "property"
    name = (getattr(lead, "name", None) or "").strip() if lead else ""
    budget = getattr(lead, "budget", None) if lead else None
    has_budget = budget is not None and str(budget).strip() not in ("", "0", "None")
    has_location = bool(getattr(lead, "location", None) if lead else None)
    has_property_type = bool(getattr(lead, "property_type", None) if lead else None)

    asks = []
    if not has_budget:
        asks.append("your approximate budget")
    if not name:
        asks.append("your name")
    if not has_location:
        asks.append("which area you're interested in")
    if not has_property_type:
        asks.append("property type (e.g. 2BHK)")

    name_bit = f", {name}" if name else ""
    if asks:
        if len(asks) == 1:
            ask_str = asks[0]
        elif len(asks) == 2:
            ask_str = f"{asks[0]} and {asks[1]}"
        else:
            ask_str = ", ".join(asks[:-1]) + f", and {asks[-1]}"
        return (
            f"Got it{name_bit} — {_pt} options in {_loc} are available. "
            f"Could you share {ask_str}?"
        )
    return (
        f"Got it{name_bit} — {_pt} options in {_loc} are available. "
        f"Would you like shortlisted options or to book a site visit?"
    )


def detect_user_language(text: str) -> str:
    """P2.6: Return 'hinglish' if user initiated Hindi/Hinglish, else 'english' (default).

    Product rule: default is always English. Only switch to Hinglish when the
    user explicitly uses Hindi/Hinglish keywords. Place names and '2BHK' in
    Latin script are NOT Hinglish signals.
    """
    if is_hinglish(text):
        return "hinglish"
    return "english"


CLOSING_PHRASES = [
    "thanks", "thank you", "goodbye", "ok thanks", "perfect thanks", "done",
    "great thanks", "thanks a lot", "stop", "unsubscribe",
]
OPT_OUT_PHRASES = ["dont message", "stop messaging", "dont contact", "please stop"]

# P2.4: Single source of truth for allowed funnel stages.
# Backend writes only these values; frontend Kanban/filters must match.
# "Closed Won" and "Lost" are manual/dashboard-only (backend never auto-sets them).
FUNNEL_STAGES = ("New", "Contacted", "Appointment Scheduled", "Closed Won", "Lost")


def clean_user_message(user_message: str) -> str:
    """Lowercase, strip, strip punctuation for closing/opt-out matching."""
    msg_lower = user_message.lower().strip()
    return msg_lower.translate(str.maketrans("", "", string.punctuation))


def has_goodbye_token(msg_clean: str) -> bool:
    """True only for whole-word bye/goodbye — not substrings like buyer/maybe."""
    tokens = msg_clean.split()
    return "bye" in tokens or "goodbye" in tokens


def is_opt_out_message(msg_clean: str) -> bool:
    return any(phrase in msg_clean for phrase in OPT_OUT_PHRASES)


def is_closing_message(msg_clean: str) -> bool:
    """Whether the user is ending the conversation (session should close)."""
    if any(msg_clean == p for p in CLOSING_PHRASES):
        return True
    if msg_clean.startswith("stop"):
        return True
    if has_goodbye_token(msg_clean):
        return True
    if is_opt_out_message(msg_clean):
        return True
    if msg_clean.endswith(" thanks"):
        return True
    return False


def is_fully_qualified(lead) -> bool:
    """All six mandatory fields present (same gate as qualification close)."""
    if not lead:
        return False
    return bool(
        lead.visit_date and lead.phone and lead.name
        and lead.location and lead.budget and lead.property_type
    )


def is_terminal_chat_state(lead) -> bool:
    """
    P0.4 / P0.5 / P2.2: Do not reopen session to active when opted out,
    fully qualified, or handoff-closed. Polite thanks-only close (not
    terminal) may reopen.

    Terminal conditions (any = terminal):
      - whatsapp_opt_in is False (opt-out)
      - all six mandatory fields present (fully qualified)
      - funnel_stage == "Human Handoff"

    Non-terminal: session closed for polite thanks, "bye" without
    full qualification, or session.status == "closed" alone does NOT
    make a lead terminal for re-arm purposes.
    """
    if not lead:
        return False
    if lead.whatsapp_opt_in is False:
        return True
    if is_fully_qualified(lead):
        return True
    if getattr(lead, "funnel_stage", None) == "Human Handoff":
        return True
    return False


def should_rearm_day0(session, lead) -> bool:
    """Whether Day 0 follow-up may be re-armed after this turn."""
    if is_terminal_chat_state(lead):
        return False
    if session is not None and getattr(session, "status", None) == "closed":
        return False
    return True


def finalize_turn(db, session, lead, f_state):
    """P2.1: Consolidate re-arm / terminal logic — call at EVERY exit point.

    Without this helper, early intercepts (instant reply, property intent,
    guardrail, fatal LLM fallback) returned before the re-arm block at the
    end of process_chat, so Day 0 was never scheduled for those paths.
    """
    if not f_state:
        return
    f_state.last_ai_reply_timestamp = datetime.now(timezone.utc)
    if should_rearm_day0(session, lead):
        day0_delay = timedelta(minutes=1) if settings.FOLLOW_UP_TEST_MODE else timedelta(minutes=30)
        f_state.follow_up_stage = "Day 0"
        f_state.follow_up_status = "active"
        f_state.next_follow_up_at = datetime.now(timezone.utc) + day0_delay
    elif is_fully_qualified(lead):
        f_state.follow_up_status = "completed"
        f_state.next_follow_up_at = None
    elif lead and lead.whatsapp_opt_in is False:
        f_state.follow_up_status = "stopped"
        f_state.next_follow_up_at = None
    db.commit()


def _has_recent_duplicate_message(db: DBSession, session_id: str, content: str, minutes: int = 5) -> bool:
    """P3.3: Check if the same user message was already saved recently for this session.

    Used by the background path (is_background=True) to avoid inserting duplicate
    user messages when the webhook timeout causes a re-run of process_chat.
    """
    if not content:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    existing = db.query(Message).filter(
        Message.session_id == session_id,
        Message.role == "user",
        Message.content == content,
        Message.timestamp >= cutoff,
    ).first()
    return existing is not None


_NAME_BLOCKLIST = frozenset({
    "bhk", "budget", "lakhs", "lakh", "crore", "cr",
    "tomorrow", "today", "yes", "no", "ok", "okay", "sure",
    "please", "hi", "hello", "hey", "buy", "rent", "flat",
    "villa", "plot", "property", "project",
} | set(PUNE_AREAS))

# Strip digits/units and check core word (catches "2BHK" → "bhk", "3bhk" → "bhk")
_BHK_PATTERN = re.compile(r"^\d*\s*(bhk|bhk\s*$)", re.IGNORECASE)


def validate_extracted_name(name: str) -> bool:
    """P2.3: Reject garbage from concurrent name extraction.

    Rules: 1–3 tokens, mostly alphabetic, not a property keyword,
    budget term, time word, affirmation, or Pune area name.
    """
    if not name or len(name) > 80:
        return False
    tokens = name.split()
    if len(tokens) < 1 or len(tokens) > 3:
        return False
    # Mostly alphabetic (allow hyphens and spaces for real Indian names)
    alpha_chars = sum(c.isalpha() or c in "- " for c in name)
    if alpha_chars / max(len(name), 1) < 0.7:
        return False
    # Blocklist check (case-insensitive)
    name_lower = name.lower()
    if name_lower in _NAME_BLOCKLIST:
        return False
    # Also block if any single token is a blocklist word (e.g. "Priya Budget")
    for t in tokens:
        if t.lower() in _NAME_BLOCKLIST:
            return False
    # Block BHK variants: "2BHK", "3 BHK", "bhk" with optional leading digits
    if _BHK_PATTERN.match(name.strip()):
        return False
    return True


# 2. Lightweight Guardrail & Tracking Helpers
async def log_event_async(session_id: str, action_type: str, latency_ms: int = 0, agent_type: str = "AI",
                          client_id: int = 1):
    """Highly asynchronous background tracking so core response latency remains 0ms."""
    from database import SessionLocal
    # We must use a fresh DB session for the background task
    db = SessionLocal()
    try:
        event = EventLog(
            session_id=session_id,
            event_type="tracking",
            action_type=action_type,
            latency_ms=latency_ms,
            agent_type=agent_type,
            client_id=client_id
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log event {action_type}: {e}")
    finally:
        db.close()


def check_topic_drift(query: str) -> bool:
    """Detects if the user has drifted from real estate topics."""
    query_lower = query.lower()
    off_topic = ["weather", "news", "movie", "food", "joke"]
    re_keywords = ["rent", "buy", "invest", "price", "bhk", "flats", "apartments", "properties", "listings",
                   "available", "options", "villa"]
    return any(w in query_lower for w in off_topic) and not any(w in query_lower for w in re_keywords)


def is_vague_without_location(query: str, lead) -> bool:
    """Blocks vague queries if no location is specified or remembered."""
    query_lower = query.lower()
    vague_triggers = ["cheap", "affordable", "any available"]

    if not any(trigger in query_lower for trigger in vague_triggers):
        return False

    pune_areas = ["wakad", "hinjewadi", "baner", "kharadi", "kothrud", "hadapsar", "ravet", "pune"]
    has_loc_now = any(area in query_lower for area in pune_areas)
    has_loc_mem = lead and lead.location and lead.location.lower() != "unknown"
    return not has_loc_now and not has_loc_mem


def normalize_lead_data(args: dict, existing_intent: str = None) -> dict:
    """Normalizes fuzzy LLM extractions into clean structured CRM data."""
    import re

    # 2. Normalize Intent (do this first to use it for budget formatting)
    intent_val = args.get("intent") or existing_intent or ""
    intent_val = str(intent_val).title().replace(" Or ", "/")  # <--- FIX: Forces "Buy Or Rent" to "Buy/Rent"

    if "intent" in args and args["intent"]:
        args["intent"] = str(args["intent"]).title().replace(" Or ", "/")  # <--- FIX

    # 1. Normalize Budget
    if "budget" in args and args["budget"]:
        budget_str = str(args["budget"]).upper().replace(" ", "")

        # Strip trailing PERMONTH/PM variants for clean parsing
        budget_str = re.sub(r'(PERMONTH|PM|/MONTH|MONTH|-MONTH)$', '', budget_str)

        # Format Lakhs
        if re.search(r'(LAKHS?|L)$', budget_str):
            budget_str = re.sub(r'(LAKHS?|L)$', '', budget_str) + "LAKHS"

        # Format Crores
        elif re.search(r'(CRORES?|CR)$', budget_str):
            num = re.sub(r'(CRORES?|CR)$', '', budget_str)
            budget_str = "1CRORE" if num == "1" else num + "CRORES"

        # Format Rent
        if intent_val == "Rent":
            budget_str = budget_str + "PERMONTH"

        args["budget"] = budget_str

    # 3. Normalize Location with Canonical List and Fallbacks
    if "location" in args and args["location"]:
        loc_lower = str(args["location"]).lower()

        canonical_locations = [
            "Wakad", "Hinjewadi", "Baner", "Kharadi", "Kothrud", "Hadapsar",
            "Ravet", "Balewadi", "Aundh", "Pashan", "Viman Nagar", "Magarpatta",
            "Kondhwa", "Undri", "Mundhwa", "Wakad Road", "Punawale", "Tathawade",
            "Bavdhan", "Sinhagad Road"
        ]

        fallback_mapping = {
            "punawale": "Wakad or Ravet",
            "tathawade": "Wakad",
            "pashan": "Baner or Bavdhan",
            "mundhwa": "Kharadi or Magarpatta"
        }

        # --- FIX: Find ALL canonical matches instead of just the first one ---
        # We sort by length descending so "Wakad Road" is matched before "Wakad"
        matched_canonicals = []
        for area in sorted(canonical_locations, key=len, reverse=True):
            if area.lower() in loc_lower and not any(
                    area.lower() in existing.lower() for existing in matched_canonicals):
                matched_canonicals.append(area)

        if matched_canonicals:
            # Join all found locations with a comma
            args["location"] = ", ".join(matched_canonicals)
        else:
            # Check fallback mapping if missing from canonical list
            matched_fallbacks = [fallback for key, fallback in fallback_mapping.items() if key in loc_lower]
            if matched_fallbacks:
                args["location"] = ", ".join(matched_fallbacks)
            elif " or " in loc_lower or "," in loc_lower:
                # Basic fallback for multiple unknown locations
                import re
                parts = re.split(r'\s+or\s+|,', loc_lower)
                args["location"] = ", ".join(p.strip().title() for p in parts if p.strip())
            else:
                args["location"] = loc_lower.title()
        # ----------------------------------------------------------------------

    # 4. Normalize Visit Date (e.g. "this saturday at 10am" -> "Saturday 10:00 AM")
    if "visit_date" in args and args["visit_date"]:
        vd = str(args["visit_date"]).strip()

        def _normalize_time(match):
            time_str = match.group(0)
            m = re.match(r'(\d{1,2}:\d{2})\s*(am|pm|AM|PM)', time_str)
            if m:
                return f"{m.group(1)} {m.group(2).upper()}"
            m = re.match(r'(\d{1,2})\s*(am|pm|AM|PM)', time_str)
            if m:
                return f"{m.group(1)}:00 {m.group(2).upper()}"
            return time_str

        vd = re.sub(r'\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)', _normalize_time, vd)
        vd = re.sub(r'\b(this|next|on|at|the|around|approximately)\b', '', vd, flags=re.IGNORECASE)
        vd = re.sub(r'\s+', ' ', vd).strip()
        vd = vd.title()
        vd = re.sub(r'\b(Am|Pm)\b', lambda m: m.group(1).upper(), vd)

        args["visit_date"] = vd

    return args


def _lead_field_empty(value) -> bool:
    if value is None:
        return True
    s = str(value).strip().lower()
    return s in ("", "unknown", "none", "null")


def extract_location_from_text(text: str) -> str | None:
    """Deterministic Pune area from raw user text (empty-only backfill)."""
    if not text:
        return None
    lower = text.lower()
    # Longer names first (e.g. wakad road before wakad)
    candidates = sorted(set(PUNE_AREAS), key=len, reverse=True)
    for area in candidates:
        if area in lower:
            return " ".join(w.capitalize() for w in area.split())
    return None


def extract_property_type_from_text(text: str) -> str | None:
    if not text:
        return None
    import re
    lower = text.lower()
    m = re.search(r"\b([1-4])\s*bhk\b", lower)
    if m:
        return f"{m.group(1)}BHK"
    if "penthouse" in lower:
        return "Penthouse"
    if "villa" in lower:
        return "Villa"
    if re.search(r"\bplot\b", lower):
        return "Plot"
    if re.search(r"\b(flat|apartment|apt)\b", lower):
        return "Apartment"
    return None


def extract_budget_from_text(text: str, existing_intent: str = None) -> str | None:
    if not text:
        return None
    import re
    lower = text.lower().replace(",", "")
    # 90 lakhs / 90 lakh / 90l / 1.2 crore / 1 cr
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|l)\b",
        lower,
    )
    if not m:
        return None
    num, unit = m.group(1), m.group(2)
    raw = f"{num}{unit}"
    normalized = normalize_lead_data({"budget": raw}, existing_intent=existing_intent)
    return normalized.get("budget")


def extract_intent_from_text(text: str) -> str | None:
    """Only clear buy/rent/invest signals — not weak words like 'looking'."""
    if not text:
        return None
    lower = text.lower()
    if re.search(r"\b(rent|rental|lease|tenant)\b", lower):
        return "Rent"
    if re.search(r"\b(invest|investment|roi|yield)\b", lower):
        return "Invest"
    if re.search(r"\b(buy|buying|purchase|purchasing)\b", lower):
        return "Buy"
    return None


def backfill_missing_lead_fields(lead, user_message: str) -> list[str]:
    """
    Safety net when the LLM tool omits fields clearly present in the user message.
    Only fills empty/unknown fields; never overwrites existing values.
    """
    if not lead or not user_message:
        return []

    filled: list[str] = []

    if _lead_field_empty(lead.location):
        loc = extract_location_from_text(user_message)
        if loc:
            lead.location = loc
            filled.append("location")

    if _lead_field_empty(lead.property_type):
        ptype = extract_property_type_from_text(user_message)
        if ptype:
            lead.property_type = ptype
            filled.append("property_type")

    if _lead_field_empty(lead.budget):
        budget = extract_budget_from_text(user_message, existing_intent=lead.intent)
        if budget:
            lead.budget = budget
            filled.append("budget")

    if _lead_field_empty(lead.intent):
        intent = extract_intent_from_text(user_message)
        if intent:
            lead.intent = intent
            filled.append("intent")

    return filled


# 4. Structured Tool Calling Definition
extract_lead_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="extract_lead_info",
            description="""Saves the lead's property search details to the CRM database.

⚠️ WHEN TO CALL THIS TOOL:
YOU MUST call this tool IMMEDIATELY the very first time the user provides ANY of these:
- Their name
- Their phone number
- Their budget (e.g. "80 lakhs", "25k per month", "1.2 crores")
- Their preferred location (e.g. "Baner", "Wakad", "Hinjewadi")
- Their property type preference (e.g. "2BHK", "3BHK", "Villa")
- Their intent (buy / rent / investment)
- A requested visit date or time
Do NOT wait to gather more information. Extract what you have immediately.

⛔ DO NOT CALL THIS TOOL for:
- General property questions
- Questions about amenities, connectivity, traffic, schools
- Acknowledgements ("Thanks", "Perfect", "Ok", "Got it")
- Greetings
- Any message that doesn't contain NEW personal search data
For those messages, respond naturally with text only.

INTENT-BASED BEHAVIOR:
- HIGH: Be proactive. Offer a specific next step like shortlisting or a site visit.
- MEDIUM: Provide data/description only. Answer and STOP.
- LOW: Provide general info. Ask one clarifying question.
- CRITICAL: For Medium/Low intent, you are FORBIDDEN from ending with "Would you like to see options?" or "Shall I help you buy?"

🔹 TOOL CALL RULE (CRITICAL):
- Whenever you call extract_lead_info, you MUST also write a conversational text reply in the SAME response.
- The text reply should naturally continue the conversation based on what the user said.
- NEVER return a function call without also including a text message.
- Do NOT mention data capture, fields, or databases in your text reply.""",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "name": types.Schema(type="STRING", description="The name of the client."),
                    "phone": types.Schema(type="STRING", description="The phone number of the client."),
                    "budget": types.Schema(type="STRING", description="The requested budget range. MUST remain empty if the user has not explicitly stated their own personal budget. NEVER extract or assume a budget based on RAG context."),
                    "location": types.Schema(type="STRING", description="The area they are looking in. MUST remain empty if the user has not explicitly stated their preferred area."),
                    "property_type": types.Schema(type="STRING", description="The type of property they want (e.g., '1BHK', '2BHK'). MUST remain empty if not explicitly stated."),
                    "intent": types.Schema(type="STRING", description="The goal (buy / rent / investment)."),
                    "score": types.Schema(type="STRING", description="Internal lead scoring (High, Medium, Low)."),
                    "visit_date": types.Schema(type="STRING", description="Requested visit date/time."),
                    "conversational_reply": types.Schema(type="STRING", description="Your natural response to the user's message. MUST match the user's language: English user → English only, Hinglish user → Hinglish. Do NOT use Hinglish words when the user writes English. MUST NOT BE EMPTY."),
                    "confidence_score": types.Schema(type="INTEGER", description="Rate confidence from 0 to 100. If ambiguous, output below 75.")
                }
            )
        )
    ]
)


# 3. Stateful Memory Function
async def process_chat(session_id: str, user_message: str, db: DBSession, client_id: int = 1,
                       is_background: bool = False, extra_context: str | None = None) -> str:
    """
    Main orchestrator for user input. Fetches memory, injects context to the LLM,
    extracts function calls for lead generation, and commits all data to DB.
    """
    start_time = time.time()
    final_text = ""

    # Ensure session and lead exist in the database exactly once to prevent redundant queries
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        session = Session(id=session_id, client_id=client_id)
        db.add(session)

    lead = db.query(Lead).filter(Lead.session_id == session_id).first()
    if not lead:
        # Interactive chat/WA defaults to opted-in; explicit STOP sets False (P0.5).
        lead = Lead(session_id=session_id, client_id=client_id, whatsapp_opt_in=True)
        db.add(lead)
        db.commit()

        # --- FIX 7: Added error handling to background tasks ---
        def handle_task_result(task):
            try:
                task.result()
            except Exception as e:
                logger.error(f"Background task failed: {e}")

        latency = round((time.time() - start_time) * 1000)
        task1 = asyncio.create_task(log_event_async(session_id, "lead_created", latency_ms=latency, client_id=client_id))
        task1.add_done_callback(handle_task_result)

        # CRM create is bus-owned (lead.created → crm_automation → AE→EE).
        # Do not dual-call sync_lead_to_crm here (BD-1).

    # --- FIX: Extract raw phone number from the tenant-prefixed Session ID ---
    if not lead.phone:
        raw_phone = session_id.split("_")[-1]
        if raw_phone.startswith("+"):
            lead.phone = raw_phone

    db.commit()

    from models import FollowUpState
    f_state = db.query(FollowUpState).filter(FollowUpState.session_id == session_id).first()
    if not f_state:
        f_state = FollowUpState(session_id=session_id, client_id=client_id)
        db.add(f_state)

    f_state.last_user_reply_timestamp = datetime.now(timezone.utc)

    # If the user replies while follow-up is active (e.g. Day 1, Day 3), log it and stop follow-ups
    if f_state.follow_up_status == "active" and f_state.follow_up_stage != "Day 0":
        latency = round((time.time() - start_time) * 1000)
        asyncio.create_task(
            log_event_async(session_id, f"{f_state.follow_up_stage} follow_up_replied", latency_ms=latency,
                            client_id=client_id))

    # If the lead already has a visit date booked, mark follow-up as completed (not just stopped).
    # "stopped" = paused mid-sequence by user reply; "completed" = goal achieved, no further action needed.

    # --- FIX 4: Corrected indentation for Qualification Logic ---
    # Ensure ALL mandatory fields are present before marking follow-up complete
    is_qualified_now = bool(
        lead and lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)

    if is_qualified_now:
        f_state.follow_up_status = "completed"
        f_state.next_follow_up_at = None
        session.status = "closed"
    else:
        f_state.follow_up_status = "stopped"  # User replied, so we stop active automated follow-ups for now.

    # User replied — reset old follow-up state (for backwards compatibility temporarily)
    session.follow_up_count = 0
    session.last_activity_at = datetime.now(timezone.utc)
    db.commit()

    # Detect if user is naturally closing the conversation
    msg_clean = clean_user_message(user_message)
    logger.info(f"DEBUG_MSG_CLEAN: '{msg_clean}' (original: '{user_message}')")

    is_opt_out = is_opt_out_message(msg_clean)

    if is_closing_message(msg_clean):
        session.status = "closed"
        if f_state:
            f_state.follow_up_status = "stopped"
            f_state.next_follow_up_at = None

        if is_opt_out or msg_clean.startswith("stop") or "unsubscribe" in msg_clean:
            lead.whatsapp_opt_in = False

        logger.info(f"Session {session_id} marked as CLOSED (user concluded conversation).")
    elif not is_terminal_chat_state(lead):
        # P0.4: never force active over qualified / opt-out / handoff terminal state
        session.status = "active"
    # else: leave session.status unchanged (stay closed when terminal)
    db.commit()

    # P0.5: opted-out users get a short ack; do not re-arm or run full pipeline
    if lead.whatsapp_opt_in is False:
        opt_out_reply = (
            "You're unsubscribed from automated messages. "
            "We won't send further follow-ups. Reply if you need a human agent."
        )
        # P3.3: Background re-run should not insert duplicate messages
        if not is_background or not _has_recent_duplicate_message(db, session_id, user_message):
            db.add(Message(session_id=session_id, client_id=client_id, role="user", content=user_message))
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=opt_out_reply))
        if f_state:
            f_state.follow_up_status = "stopped"
            f_state.next_follow_up_at = None
        session.status = "closed"
        db.commit()
        finalize_turn(db, session, lead, f_state)
        return opt_out_reply

    # P3.3: Background re-run should not insert duplicate user messages
    if not is_background or not _has_recent_duplicate_message(db, session_id, user_message):
        db.add(Message(session_id=session_id, client_id=client_id, role="user", content=user_message))
    db.commit()

    # PERFORMANCE: Instant-Reply Intercept
    # Bypasses Gemini completely for basic generic texts to deliver 0ms backend latency
    INSTANT_REPLIES = {
        "hi": "Hello! How can I help you with your property search today?",
        "hello": "Hi there! Are you looking to buy or rent a property?",
        "hey": "Hello! What kind of property are you looking for?",
        "ok": "Got it! Let me know if you have any other questions.",
        "okay": "Got it! Let me know if you have any other questions.",
        "thanks": "You're welcome! Feel free to ask if you need anything else.",
        "thank you": "You're welcome! Feel free to ask if you need anything else."
    }

    # --- FIX: Prevent Amnesia for Greetings Mid-Conversation ---
    is_mid_conversation = bool(lead and (
                lead.budget or lead.name or lead.visit_date or (lead.location and lead.location.lower() != "unknown")))

    if msg_clean in INSTANT_REPLIES and not is_mid_conversation:
        local_reply = INSTANT_REPLIES[msg_clean]
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=local_reply))
        db.commit()

        # Log the response speed for the ROI dashboard
        total_latency_ms = round((time.time() - start_time) * 1000)
        asyncio.create_task(log_event_async(session_id, "message_sent", latency_ms=total_latency_ms, agent_type="AI",
                                            client_id=client_id))

        logger.info(f"INSTANT_INTERCEPT | session={session_id} | bypassed LLM")
        finalize_turn(db, session, lead, f_state)
        return local_reply

    # PROPERTY INTENT INTERCEPT — Deterministic zero-latency reply for the most common opener
    # "I'm looking to buy/rent X in Y" consistently causes Gemini to misfire (function call with no text)
    # Catching it here guarantees sub-1s response and naturally elicits budget/name.
    PROPERTY_INTENT_OPENERS = [
        "i'm looking to buy", "i am looking to buy",
        "i'm looking to rent", "i am looking to rent",
        "i want to buy", "i want to rent",
        "looking for a flat", "looking for an apartment",
        "i need a flat", "i need a property",
        "searching for", "i want a 2bhk", "i want a 3bhk", "i want a 1bhk",
        # Location-only openers that skip "i'm looking" prefix (common in real usage):
        "looking to buy in", "looking to rent in", "looking to buy",
        "looking to rent", "want to buy in", "want to rent in",
        "buy in ", "rent in ",
        # Investment intent:
        "investment property", "invest in",
        # Property qualifier phrases that trigger slow function-call overhead:
        "ready to move", "ready-to-move",
        "under construction", "new launch",
        "i prefer", "we prefer",
        "resale flat", "resale property",
        "furnished", "semi-furnished",
    ]
    # Skip intent intercept if the message also contains personal data
    # (name, budget, phone) — those need Gemini to extract and save properly.
    # Also skip if the message contains location or property type — those are
    # meaningful DB fields that the intercept template never captures.

    HAS_PERSONAL_DATA = any([
        "my name is" in msg_clean,
        "i am " in msg_clean and len(msg_clean.split()) <= 8,
        "budget is" in msg_clean,
        "budget" in msg_clean and any(c.isdigit() for c in msg_clean),
        "lakhs" in msg_clean or "crore" in msg_clean or "lakh" in msg_clean,
        "per month" in msg_clean,
        any(area in msg_clean for area in PUNE_AREAS),        # has location — send to Gemini
        "2bhk" in msg_clean or "3bhk" in msg_clean or "1bhk" in msg_clean or "4bhk" in msg_clean,
        "2 bhk" in msg_clean or "3 bhk" in msg_clean or "1 bhk" in msg_clean,
        "villa" in msg_clean or "plot" in msg_clean,
    ])

    # --- FIX: Prevent Amnesia for Property Modifiers (like "ready to move") ---
    if is_mid_conversation:
        HAS_PERSONAL_DATA = True
    # --------------------------------------------------------------------------

    for opener in PROPERTY_INTENT_OPENERS:
        if opener in msg_clean and not HAS_PERSONAL_DATA:
            loc_hint = lead.location or ""
            pt_hint = lead.property_type or ""
            msg_l2 = msg_clean
            if "ready to move" in msg_l2 or "ready-to-move" in msg_l2:
                local_reply = f"Great preference! Ready-to-move-in {pt_hint or '2BHK'} flats in {loc_hint or 'Pune'} are available. What is your budget range?"
            elif "under construction" in msg_l2 or "new launch" in msg_l2:
                local_reply = f"Noted! New launch projects in {loc_hint or 'Pune'} offer excellent early-bird pricing. What is your target budget?"
            elif "furnished" in msg_l2:
                label = "Semi-furnished" if "semi" in msg_l2 else "Fully furnished"
                local_reply = f"Got it! {label} options in {loc_hint or 'Pune'} are available across multiple societies. What is your budget range?"
            elif loc_hint and pt_hint:
                local_reply = f"Great choice! {pt_hint} in {loc_hint} is an excellent option. What's your approximate budget? And may I know your name?"
            elif loc_hint:
                local_reply = f"Perfect! {loc_hint} has some great options. What's your budget range, and what type of property are you looking for (2BHK, 3BHK, villa)?"
            elif pt_hint:
                local_reply = f"Looking for a {pt_hint} — great! Which area in Pune interests you most?"
            else:
                local_reply = "Great! To find the best match, could you tell me which area in Pune you're interested in, and your approximate budget?"

            db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=local_reply))
            db.commit()
            total_latency_ms = round((time.time() - start_time) * 1000)
            asyncio.create_task(
                log_event_async(session_id, "message_sent", latency_ms=total_latency_ms, agent_type="AI",
                                client_id=client_id))
            logger.info(f"INTENT_INTERCEPT | session={session_id} | bypassed LLM")
            finalize_turn(db, session, lead, f_state)
            return local_reply

    # -----------------------------------
    # AI Lightweight Guardrail Intercepts
    # -----------------------------------
    guardrail_reply = None

    if check_topic_drift(user_message):
        guardrail_reply = "I specialize in Pune real estate. Shall we get back to your property search?"
    elif is_vague_without_location(user_message, lead):
        guardrail_reply = "I'd be happy to help! Which specific area in Pune are you looking into? (e.g., Wakad, Kharadi, Baner)"

    if guardrail_reply:
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=guardrail_reply))
        db.commit()
        logger.info(f"GUARDRAIL_INTERCEPT | session={session_id} | bypassed LLM")
        finalize_turn(db, session, lead, f_state)
        return guardrail_reply

    # -----------------------------------
    # HUMAN HANDOFF INTERCEPT
    # -----------------------------------
    handoff_phrases = ["human", "agent", "real person", "call me", "speak to someone", "customer service"]
    if any(phrase in msg_clean for phrase in handoff_phrases):
        # P1.5: assign before notify so hot alert can reach a real agent
        previous_agent = lead.assigned_agent
        assigned = ensure_lead_assignment(
            db, lead, client_id, user_message or msg_clean, force=False
        )
        if assigned and previous_agent != assigned:
            db.add(EventLog(
                session_id=session_id,
                client_id=client_id,
                event_type="audit",
                action_type=f"assigned_to_{assigned.replace(' ', '_').lower()}",
                agent_type="System",
            ))

        lead.lead_temperature = "hot"
        lead.funnel_stage = "Contacted"  # P2.4: map "Human Handoff" → "Contacted" (Kanban-aligned)
        session.status = "closed"
        if f_state:
            f_state.follow_up_status = "stopped"
            f_state.next_follow_up_at = None

        db.add(EventLog(
            session_id=session_id,
            client_id=client_id,
            event_type="lead.handoff",
            action_type="human_handoff_requested",
            agent_type="System",
        ))
        db.add(EventLog(
            session_id=session_id,
            client_id=client_id,
            event_type="lead.hot",
            action_type="human_handoff",
            agent_type="System",
        ))

        db.commit()

        logger.info(f"🚨 HUMAN HANDOFF TRIGGERED: Lead {lead.phone} requested an agent!")
        asyncio.create_task(
            trigger_hot_lead_notification(lead.id, "Explicit human agent requested.", severity=SEVERITY_HANDOFF)
        )
        # PR #10 / BA-1: bus lead.hot + alias lead.escalated; session.completed on close
        try:
            from types import SimpleNamespace

            from app.events.lead_hot import publish_lead_hot, publish_session_completed
            from app.memory.conversation_memory import conversation_memory

            _chat_ctx = ""
            try:
                _chat_ctx = conversation_memory.summarize_recent(
                    db, session_id=session_id, turns=10
                ) or ""
            except Exception:
                pass
            # Snapshot before create_task — session may expire the ORM row.
            _snap = SimpleNamespace(
                id=lead.id,
                session_id=session_id,
                name=lead.name,
                phone=lead.phone,
                location=lead.location,
                budget=lead.budget,
                property_type=lead.property_type,
                intent=lead.intent,
                lead_temperature=lead.lead_temperature,
                conversion_probability=lead.conversion_probability,
                assigned_agent=lead.assigned_agent,
            )
            asyncio.create_task(
                publish_lead_hot(
                    client_id=client_id,
                    lead=_snap,
                    trigger="human_handoff",
                    reason="Explicit human agent requested.",
                    session_id=session_id,
                    chat_context=_chat_ctx,
                    source="agent",
                )
            )
            asyncio.create_task(
                publish_session_completed(
                    client_id=client_id,
                    lead=_snap,
                    session_id=session_id,
                    close_reason="human_handoff",
                    chat_context=_chat_ctx,
                    source="agent",
                )
            )
        except Exception as _bus_exc:  # noqa: BLE001
            logger.debug("handoff bus publish skipped: %s", _bus_exc)

        handoff_reply = "I completely understand. I have paused my automated responses and alerted our human team. An expert will review our chat and reach out to you shortly!"
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=handoff_reply))
        db.commit()
        finalize_turn(db, session, lead, f_state)
        return handoff_reply

    # -----------------------------------
    # NEGOTIATION INTERCEPT (Layer 1: keyword detection)
    # -----------------------------------
    # Detects explicit user negotiation intent. Sets is_negotiating = True
    # and publishes lead.negotiation.started. Does NOT short-circuit —
    # conversation continues to LLM.
    # PHRASE EXPANSION: Add domain-specific phrases here as user patterns
    # emerge. Consider moving to a shared lexicon (app/agents/negotiation_lexicon.py)
    # if phrase list grows beyond 15 entries.
    _NEGOTIATION_PHRASES = [
        "negotiate", "negotiation", "discount", "reduce price",
        "lower price", "too expensive", "can you reduce", "final price",
        "best price", "cheaper", "afford", "budget is tight",
        "change my budget", "reduce my budget", "lower my budget",
        "budget is only", "can only afford", "stretch my budget",
    ]
    if any(phrase in msg_clean for phrase in _NEGOTIATION_PHRASES):
        if not lead.is_negotiating:
            lead.is_negotiating = True
            db.add(EventLog(
                session_id=session_id,
                client_id=client_id,
                event_type="lead.negotiation.started",
                action_type="user_phrase",
                agent_type="System",
            ))
            db.commit()

        from app.events.negotiation import publish_negotiation_started
        asyncio.create_task(
            publish_negotiation_started(
                client_id=client_id,
                lead_id=lead.id,
                session_id=session_id,
                trigger="user_phrase",
                message=user_message[:200],
                budget=lead.budget or "",
                budget_alignment_status=getattr(lead, "budget_alignment_status", "unknown"),
                source="agent",
            )
        )
        # DO NOT RETURN — let the conversation continue to the LLM

    # LIMIT CONTEXT: last 6 turns (12 messages) — keeps enough history for the full
    # conversation to remain coherent. CRM fields are always protected by the DB summary
    # so they are never lost even if the extraction turn scrolls out of the window.
    past_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id.desc()).limit(
        12).all()
    past_messages.reverse()

    formatted_history = []
    # Build history excluding the just-saved user message.
    # Strip [AUTO FOLLOW-UP] prefix so follow-up messages don't inflate token count.
    for m in past_messages[:-1]:
        role = "user" if m.role == "user" else "model"
        clean_content = m.content.replace("[AUTO FOLLOW-UP] ", "")
        formatted_history.append({"role": role, "parts": [clean_content]})

    # SAFETY: Gemini API rejects history with consecutive same-role messages (InvalidArgument).
    # This can occur after an API failure where a fallback is saved, then the follow-up
    # scheduler also fires — producing two consecutive 'assistant' entries.
    # This loop merges them silently. In a clean conversation it is a no-op.
    sanitized_history = []
    for msg in formatted_history:
        role = msg["role"]
        text = msg["parts"][0]
        if sanitized_history and sanitized_history[-1].role == role:
            sanitized_history[-1].parts[0].text += " " + text
        else:
            sanitized_history.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    formatted_history = sanitized_history

    # Agent Memory Summarization Logic
    # Inject the FULL persisted lead state so the LLM always knows what was captured,
    # even if the original extraction message has rolled out of the 12-message window.
    summary_text = ""
    missing_fields = []
    if lead:
        summary_parts = []

        # --- FIX: Tell Gemini we already have the phone number! ---
        if lead.phone:
            summary_parts.append(f"Phone: {lead.phone}")
        # ---------------------------------------------------------

        if lead.location:
            summary_parts.append(f"Location: {lead.location}")
        else:
            missing_fields.append("location")

        if lead.budget:
            summary_parts.append(f"Budget: {lead.budget}")
        else:
            missing_fields.append("budget")

        if lead.property_type:
            summary_parts.append(f"Property Type: {lead.property_type}")
        else:
            missing_fields.append("property type (e.g., 2BHK, 3BHK)")

        if lead.name:
            summary_parts.append(f"Name: {lead.name}")
        else:
            missing_fields.append("name")

        if lead.intent: summary_parts.append(f"Intent: {lead.intent}")
        if lead.visit_date: summary_parts.append(f"Visit scheduled: {lead.visit_date}")

        if summary_parts:
            summary_text = "Known about this user: " + ", ".join(summary_parts) + ".\n"

        # BD-5: Neo4j / graph micro-market context (injected by WhatsAppAgent).
        if extra_context:
            summary_text += f"Knowledge graph signal: {extra_context}\n"

        if summary_parts:
            # THE FIX: If they want to visit but are missing details, force Gemini to naturally ask for them.
            # Check if they are discussing a visit in this turn
            wants_visit = lead.visit_date or (lead.intent and "visit" in lead.intent.lower()) or any(
                w in user_message.lower() for w in
                ["visit", "schedule", "tomorrow", "saturday", "sunday", "morning", "afternoon", "pm", "am"])

            if wants_visit and missing_fields:
                summary_text += f"CRITICAL INSTRUCTION: The user is trying to schedule a visit, but we are missing mandatory details: {', '.join(missing_fields)}. You MUST ask them for these missing details before confirming the booking. Do NOT say the visit is fully booked yet.\n"

    # Dynamic Repetition Prevention
    # Check if the agent already proactively asked for the name in recent history.
    # If so, forcefully instruct the LLM not to ask again to prevent an endless loop.
    if not lead.name:
        for m in past_messages[:-1]:
            if m.role == "assistant" and any(
                    ph in m.content.lower() for ph in
                    ["name", "speaking with", "who is this", "know you as", "may i have"]):
                summary_text += "SYSTEM NOTE: You previously asked for their name. DO NOT ask for it again right now, UNLESS they are trying to schedule a visit (in which case it is mandatory to ask before confirming).\n"
                break

    # Keyword gateway: only call RAG (Gemini Embedding API) for property-related queries.
    # Greetings, acks, and short responses skip the embedding call, saving 1-4s per message.
    PROPERTY_KEYWORDS = {
        "flat", "bhk", "rent", "buy", "invest", "area", "location", "baner", "wakad",
        "hinjewadi", "price", "budget", "property", "apartment", "villa", "plot",
        "2bhk", "3bhk", "1bhk", "pune", "noida", "mumbai", "sqft", "furnish",
        "visit", "book", "schedule", "bedroom", "floor", "tower", "society",
        "possession", "ready", "availability", "cheap", "affordable", "luxury",
        "options", "available"
    }
    words = user_message.lower().split()
    is_property_query = any(w.strip(".,!?") in PROPERTY_KEYWORDS for w in words)

    # Only trigger RAG if we have a location in context OR if the user explicitly mentions a Pune area
    has_loc_ctx = bool(lead and lead.location and lead.location.lower() != "unknown")
    has_loc_msg = any(area in user_message.lower() for area in PUNE_AREAS)
    is_rag_eligible = is_property_query and (has_loc_ctx or has_loc_msg)

    # Fetch RAG Context from the FAQ store (only for property-related queries)
    user_message_for_llm = f"Summary: {summary_text}\nUser Message: {user_message}"
    if is_rag_eligible:
        rag_start = time.time()
        try:
            # Contextualize RAG query with known location to resolve pronouns like "there"
            rag_query = f"{lead.location} {user_message}" if (lead and lead.location) else user_message
            # Offload synchronous RAG/FAISS to thread to prevent blocking FastAPI event loop
            context_items, score = await asyncio.wait_for(
                asyncio.to_thread(retrieve, rag_query),
                timeout=float(getattr(settings, "RAG_TIMEOUT_SECONDS", 2.0)),
            )
            rag_time = round((time.time() - rag_start) * 1000)
            logger.info(json.dumps({"event": "rag_retrieval", "latency_ms": rag_time, "success": True}))
            if score < 0.8 and context_items:
                # Trim RAG context: flatten to a compact string, max 280 chars per item.
                # Nested dicts in faq.json can be verbose; we only need the key facts.
                def _fmt_item(item):
                    det = item.get('details', '')
                    if isinstance(det, dict):
                        det = ', '.join(f"{k}: {v}" for k, v in det.items())
                    raw = f"{item['location']} ({item.get('type', '')}) — {det}. {item.get('description', '')}"
                    return raw[:280]

                context_text = "\n".join(_fmt_item(i) for i in context_items)
                user_message_for_llm = f"Summary: {summary_text}\nProperty Context:\n{context_text}\n\nUser Message: {user_message}"
        except Exception as e:
            rag_time = round((time.time() - rag_start) * 1000)
            logger.error(json.dumps(
                {"event": "rag_retrieval", "latency_ms": rag_time, "success": False, "error": type(e).__name__}))
    else:
        logger.info(f"RAG skipped (non-property query) for session={session_id}")

    # P2.6: Language lock — append hard instruction adjacent to user turn.
    # This is stronger than system-prompt bullets because it's in the user-message context.
    user_lang = detect_user_language(user_message)
    if user_lang == "english":
        lang_instruction = (
            "\n\nLANGUAGE LOCK (MANDATORY — overrides all other instructions):\n"
            "User language: ENGLISH. You MUST reply in natural English only. "
            "Do NOT use Hinglish words (mein, hain, aapka, kya, ke liye, etc.). "
            "conversational_reply MUST be English."
        )
    else:
        lang_instruction = (
            "\n\nLANGUAGE LOCK (MANDATORY — overrides all other instructions):\n"
            "User language: HINGLISH. Reply in natural Hinglish (Latin script). "
            "Keep real estate nouns in English (Budget, Location, 2BHK, etc.)."
        )
    user_message_for_llm = user_message_for_llm + lang_instruction

    # Start Gemini Chat with retrieved history
    _support = (getattr(settings, "CLIENT_SUPPORT_NUMBER", None) or "+91 9876543210").strip()
    system_instruction = REAL_ESTATE_SYSTEM_PROMPT.replace(
        "+91 [CLIENT_SUPPORT_NUMBER]", _support
    ).replace("[CLIENT_SUPPORT_NUMBER]", _support)
    chat = client.aio.chats.create(
        model=settings.GEMINI_MODEL,
        config={"system_instruction": system_instruction, "tools": [extract_lead_tool]},
        history=sanitized_history
    )

    # 2c: Dynamic Name Interceptor (Concurrent, strict timeout)
    # If the user's name is unknown and they give a short response, dynamically extract it.
    # Wrapped in a 2-second timeout to guarantee it NEVER causes latency spikes.
    name_extraction_task = None

    # OPTIMIZATION: Bypass during TEST_MODE to prevent request multiplication.
    # Also skip obvious short greetings/acknowledgements to conserve API quota.
    if not settings.TEST_MODE and not lead.name and len(user_message.split()) <= 12:
        ignorable_short_words = ["hi", "hello", "hey", "ok", "okay", "thanks", "thank", "yes", "no", "sure", "bye"]
        if msg_clean not in ignorable_short_words:
            name_extraction_task = asyncio.create_task(
                asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=f"Extract the person's name from this message. Return ONLY the extracted name, or 'NONE' if no name is present. Message: '{user_message}'"
                    ),
                    timeout=2.0
                )
            )

    # Send the history + new message to Gemini.
    # Retry only transient API failures — never retry asyncio.TimeoutError (would
    # burn 3× LLM_TIMEOUT and still fail; user already may be on interim path).
    max_retries = 3
    llm_timeout = float(settings.LLM_TIMEOUT_SECONDS)
    support_num = (
        getattr(settings, "CLIENT_SUPPORT_NUMBER", None) or "+91 9876543210"
    ).strip()
    response = None
    for attempt in range(max_retries):
        llm_start = time.time()
        try:
            if attempt == 0 and name_extraction_task:
                # Run the main chat and the name extraction concurrently.
                # return_exceptions=True prevents the name-extract timeout from crashing main chat.
                # LLM hard cap: settings.LLM_TIMEOUT_SECONDS (may exceed WA race; inflight continues).
                results = await asyncio.gather(
                    asyncio.wait_for(
                        chat.send_message(user_message_for_llm),
                        timeout=llm_timeout,
                    ),
                    name_extraction_task,
                    return_exceptions=True
                )
                response = results[0]
                name_resp = results[1]

                # If the main chat failed, manually raise so the retry loop catches it
                if isinstance(response, Exception):
                    raise response

                if not isinstance(name_resp, Exception):
                    try:
                        extracted_name = name_resp.text.strip()
                        if extracted_name and extracted_name.upper() != "NONE" and validate_extracted_name(extracted_name):
                            lead.name = extracted_name
                            db.commit()
                            logger.info(f"CONCURRENT_NAME_INTERCEPT | session={session_id} | name={extracted_name}")
                        elif extracted_name and not validate_extracted_name(extracted_name):
                            logger.debug(f"NAME_INTERCEPT_REJECTED | session={session_id} | name={extracted_name}")
                    except Exception as e:
                        logger.warning(f"Fast name extraction text parsing failed: {e}")
            else:
                response = await asyncio.wait_for(
                    chat.send_message(user_message_for_llm),
                    timeout=llm_timeout,
                )

            llm_time = round((time.time() - llm_start) * 1000)
            logger.info(
                json.dumps({"event": "llm_main_call", "latency_ms": llm_time, "attempt": attempt + 1, "success": True}))

            # Token usage + cost tracking for gemini-3.1-flash-lite
            # Pricing (paid tier, standard): $0.25/1M input tokens, $1.50/1M output tokens
            try:
                usage = response.usage_metadata
                input_tokens = usage.prompt_token_count or 0
                output_tokens = usage.candidates_token_count or 0
                cost_usd = (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 1.50)
                logger.info(json.dumps({
                    "event": "llm_token_usage",
                    "model": settings.GEMINI_MODEL,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "estimated_cost_usd": round(cost_usd, 6),
                    "session_id": session_id
                }))
            except Exception:
                pass  # Never let cost logging crash the main flow

            break  # Success — exit retry loop
        except Exception as e:
            llm_time = round((time.time() - llm_start) * 1000)
            err_name = type(e).__name__
            logger.warning(json.dumps(
                {"event": "llm_main_call", "latency_ms": llm_time, "attempt": attempt + 1, "success": False,
                 "error": err_name, "detail": str(e)[:200]}))
            # Hard client-side timeout: do not retry (each attempt would burn full budget).
            is_timeout = isinstance(e, (asyncio.TimeoutError, TimeoutError)) or err_name in (
                "TimeoutError",
                "CancelledError",
            )
            if is_timeout:
                logger.error(json.dumps({
                    "event": "llm_main_fatal",
                    "error": err_name,
                    "detail": "timeout_no_retry",
                    "session": session_id,
                    "timeout_s": llm_timeout,
                }))
                fallback = (
                    "I'm currently experiencing a technical issue and couldn't process your request. "
                    f"Our team is here to help — please reach us directly at *{support_num}* "
                    "or try again in a few minutes. Apologies for the inconvenience! 🙏"
                )
                db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=fallback))
                db.commit()
                finalize_turn(db, session, lead, f_state)
                return fallback
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Standard exponential backoff
                await asyncio.sleep(wait_time)
            else:
                logger.error(json.dumps({"event": "llm_main_fatal", "error": err_name, "detail": str(e)[:200],
                                         "session": session_id}))
                fallback = (
                    "I'm currently experiencing a technical issue and couldn't process your request. "
                    f"Our team is here to help — please reach us directly at *{support_num}* "
                    "or try again in a few minutes. Apologies for the inconvenience! 🙏"
                )
                db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=fallback))
                db.commit()
                finalize_turn(db, session, lead, f_state)
                return fallback

    # 5. Database Commits & Tool Execution Handling
    # Detect if Gemini triggered the lead extraction tool
    fc = None
    if response.function_calls:
        for function_call in response.function_calls:
            if function_call.name == "extract_lead_info":
                fc = function_call
                # Extract and normalize arguments payload securely
                raw_args = fc.args if isinstance(fc.args, dict) else dict(fc.args)
                args = normalize_lead_data(raw_args, existing_intent=lead.intent)

                # Snapshot which fields are GENUINELY NEW in this turn vs already known.
                # This prevents re-extracted old data from triggering the same template repeatedly.
                prev_budget = lead.budget
                prev_location = lead.location
                prev_intent = lead.intent
                prev_name = lead.name
                prev_visit_date = lead.visit_date
                prev_property_type = lead.property_type

                # Update Lead table fields dynamically (using the in-memory lead object)
                # OPTIMIZATION: Only overwrite DB fields if Gemini passes a non-null, valid value.
                # This prevents incomplete tool calls from wiping out previously saved database state.
                if "name" in args and args["name"]: lead.name = args["name"]
                if "phone" in args and args["phone"]: lead.phone = args["phone"]
                if "budget" in args and args["budget"]: lead.budget = args["budget"]
                if "location" in args and args["location"]: lead.location = args["location"]
                if "property_type" in args and args["property_type"]: lead.property_type = args["property_type"]
                if "intent" in args and args["intent"]: lead.intent = args["intent"]
                if "score" in args and args["score"]: lead.score = args["score"]
                if "visit_date" in args and args["visit_date"]: lead.visit_date = args["visit_date"]

                # --- FIX: Process Confidence Score & Manual Review ---
                if "confidence_score" in args:
                    lead.confidence_score = args["confidence_score"]
                    if args["confidence_score"] < 75:
                        lead.requires_manual_review = True
                        logger.info(f"⚠️ Low confidence ({lead.confidence_score}%). Flagged for manual review.")
                # -----------------------------------------------------

                # Deterministic backfill when tool omits fields present in user text
                backfilled = backfill_missing_lead_fields(lead, user_message)
                if backfilled:
                    logger.info(
                        f"LEAD_BACKFILL | session={session_id} | fields={backfilled}"
                    )

                db.commit()

                # Determine which fields are truly new this turn (value changed or was None before)
                new_fields = set()
                if lead.budget and lead.budget != prev_budget: new_fields.add("budget")
                if lead.location and lead.location != prev_location: new_fields.add("location")
                if lead.intent and lead.intent != prev_intent: new_fields.add("intent")
                if lead.name and lead.name != prev_name: new_fields.add("name")
                if lead.visit_date and lead.visit_date != prev_visit_date: new_fields.add("visit_date")
                if lead.property_type and lead.property_type != prev_property_type: new_fields.add(
                    "property_type")

                # Fire highly-asynchronous funnel events based on new data
                current_latency = round((time.time() - start_time) * 1000)
                if any(k in new_fields for k in ["budget", "location", "intent", "property_type"]):
                    asyncio.create_task(
                        log_event_async(session_id, "qualified", latency_ms=current_latency, client_id=client_id))

                if "visit_date" in new_fields:
                    asyncio.create_task(
                        log_event_async(session_id, "appointment_booked", latency_ms=current_latency,
                                        client_id=client_id))

                # Extract Gemini's own conversational text from this same response.
                text_from_response = args.get("conversational_reply", None)
                if not text_from_response and response.text:
                    text_from_response = response.text.strip()

                captured_fields = [k for k in
                                   ["name", "phone", "budget", "location", "property_type", "intent", "visit_date"]
                                   if k in args]

                # Use Gemini's text from the same response, or fall back safely.
                if text_from_response:
                    local_reply = text_from_response
                else:
                    if "budget" in new_fields and "location" in new_fields:
                        local_reply = f"Got it — budget of {lead.budget} for {lead.location} noted."
                    elif "budget" in new_fields:
                        loc_hint = f" for {lead.location}" if lead.location else ""
                        local_reply = f"Got it — budget of {lead.budget} noted{loc_hint}."
                    elif "location" in new_fields:
                        local_reply = f"Noted — {lead.location} added to your search."
                    elif "property_type" in new_fields:
                        local_reply = f"Noted — {lead.property_type} it is."
                    elif "intent" in new_fields and lead.intent and "visit" in lead.intent.lower():
                        local_reply = "I'd be happy to arrange a site visit! What day or time works best for you?"
                    elif "name" in new_fields:
                        local_reply = f"Got it, {lead.name}. Thanks for sharing!"
                    else:
                        local_reply = "Got it, noted."

                logger.info(
                    f"LEAD_EXTRACT | session={session_id} | fields={captured_fields} | new_fields={list(new_fields)}")
                final_text = local_reply
                extracted_early = True
                break

    # Backfill even when Gemini skipped the tool call but user text has clear signals
    if 'extracted_early' not in locals() or not locals().get('extracted_early'):
        backfilled = backfill_missing_lead_fields(lead, user_message)
        if backfilled:
            db.commit()
            logger.info(f"LEAD_BACKFILL | session={session_id} | fields={backfilled} | path=no_tool")

    # Safely get the final text (handling cases where only a tool call was returned)
    if 'extracted_early' not in locals():
        try:
            if not response.text and not response.function_calls:
                logger.warning("Empty response from Gemini (no text, no function calls). Using smart local fallback.")
                # Smart zero-latency local fallback — no second LLM call, no extra latency
                msg_l = user_message.lower()
                if any(k in msg_l for k in ["school", "hospital", "infrastructure", "connectivity", "transport"]):
                    final_text = f"{lead.location or 'That area'} has good infrastructure with reputed schools and hospitals nearby. Would you like to schedule a visit?"
                elif any(k in msg_l for k in ["safe", "family", "kids", "children"]):
                    final_text = f"{lead.location or 'Baner'} is considered a safe, family-friendly area. Are you looking for a ready-to-move-in flat or under construction?"
                elif any(k in msg_l for k in ["resale", "investment", "appreciation"]):
                    final_text = f"Properties in {lead.location or 'Pune'} have shown consistent appreciation. Would you like options with good resale value?"
                elif any(k in msg_l for k in ["gym", "pool", "club", "amenities", "parking"]):
                    final_text = "Most modern societies in that area offer premium amenities including gym, pool, and covered parking. Shall I suggest some specific projects?"
                else:
                    final_text = f"I'd be happy to help with that! Based on your interest in {lead.location or 'Pune'}, shall we schedule a visit to a property that fits your requirements?"
            else:
                final_text = response.text
        except ValueError:
            # If Gemini returned a function call but we somehow missed it, or if it returned no text
            logger.warning(f"ValueError accessing response.text.")
            final_text = "Got it. Let me know if you need anything else or want to schedule a visit."

    # ==========================================
    # NEW ML INTELLIGENCE LAYER
    # ==========================================
    history_text = " ".join([m.content for m in past_messages if m.role == "user"]).lower() + " " + user_message.lower()

    # --- FIX 1: Initialize ml_score_data to prevent UnboundLocalError ---
    ml_score_data = {
        "conversion_probability": 0,
        "lead_temperature": "cold",
        "expected_closure_days": 60,
        "engagement_score": 0,
        "urgency_level": "low",
        "response_speed_score": 0,
        "inactivity_penalty": 0,
        "budget_alignment_status": "unknown"
    }

    memory_dicts = []
    for m in past_messages:
        memory_dicts.append({
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if hasattr(m, "timestamp") and m.timestamp else None
        })

    # --- FIX 1: Calculate advanced lead score outside the loop or with proper check ---
    # 1. Calculate advanced lead score
    # Map Gemini's database intent strings to the scoring engine's expected weights
    _raw_intent = (lead.intent or "").lower()
    if _raw_intent in ("buy", "invest", "investment"):
        _scoring_intent = "high"
    elif _raw_intent in ("rent", "lease", "buy/rent", "buy or rent"):
        _scoring_intent = "medium"
    else:
        _scoring_intent = "low"

    ml_score_data = calculate_lead_score(
        query=user_message,
        memory=memory_dicts,
        intent=_scoring_intent
    )

    lead.conversion_probability = ml_score_data.get("conversion_probability", 0)
    lead.lead_temperature = ml_score_data.get("lead_temperature", "cold")
    lead.expected_closure_days = ml_score_data.get("expected_closure_days", 60)
    lead.engagement_score = ml_score_data.get("engagement_score", 0)
    lead.urgency_level = ml_score_data.get("urgency_level", "low")
    lead.response_speed_score = ml_score_data.get("response_speed_score", 0)
    lead.inactivity_penalty = ml_score_data.get("inactivity_penalty", 0)
    new_alignment = ml_score_data.get("budget_alignment_status", "unknown")
    if new_alignment == "unknown" and lead.budget and lead.location and lead.property_type:
        try:
            from app.intelligence.budget_alignment import evaluate_budget_alignment
            recalculated = evaluate_budget_alignment(
                budget_text=lead.budget,
                location=lead.location.split(",")[0].strip(),
                property_type=lead.property_type
            )
            lead.budget_alignment_status = recalculated.get("alignment_status", "unknown")
        except Exception as e:
            logger.warning(f"Failed to recalculate budget alignment: {e}")
            lead.budget_alignment_status = "unknown"
    else:
        lead.budget_alignment_status = new_alignment

    # Optional: Map the raw integer score back to High/Medium/Low string if needed for frontend backward compatibility
    prob = ml_score_data.get("conversion_probability", 0)

    # DB-aware score override: ML scoring only sees the current message text,
    # so it misses signals already committed to the lead row. Apply overrides here.

    # Use helper — do not bind a bool named is_fully_qualified (shadows function → TypeError on re-arm)
    is_fully_qualified_row = is_fully_qualified(lead)
    has_visit = bool(lead.visit_date)
    has_core = all([lead.location, lead.budget, lead.property_type, lead.intent])

    if is_fully_qualified_row:
        prob = max(prob, 88)
        lead.lead_temperature = "hot"
        lead.expected_closure_days = min(lead.expected_closure_days, 7)
    elif has_visit:
        prob = max(prob, 82)
        lead.lead_temperature = "hot"

    lead.conversion_probability = prob

    if prob >= 82:
        lead.score = "High"
        lead.lead_temperature = "hot"
    elif prob >= 45:
        lead.score = "Medium"
        lead.lead_temperature = "warm"
    else:
        lead.score = "Low"
        lead.lead_temperature = "cold"

    # P1.1 / P1.2 / P1.4: assign (sticky if claimed) → commit → then hot notify
    previous_agent = lead.assigned_agent
    assigned = ensure_lead_assignment(
        db, lead, client_id, history_text or user_message or "", force=False
    )
    if assigned and previous_agent != assigned:
        db.add(EventLog(
            session_id=session_id,
            client_id=client_id,
            event_type="audit",
            action_type=f"assigned_to_{assigned.replace(' ', '_').lower()}",
            agent_type="System",
        ))
    db.commit()

    if prob >= 82 and session.status != "closed":
        logger.info(
            f"🔔 HOT THRESHOLD: Lead {lead.phone} conversion_probability={prob}; notifying after assignment."
        )
        db.add(EventLog(
            session_id=session_id,
            client_id=client_id,
            event_type="lead.hot",
            action_type=f"hot_threshold_score_{prob}",
            agent_type="System",
        ))
        db.commit()
        asyncio.create_task(
            trigger_hot_lead_notification(
                lead.id,
                hot_threshold_notification_reason(prob),
                severity=SEVERITY_SCORE_ALERT,
            )
        )

    # --- SYNCHRONIZE FUNNEL STAGE WITH EVENT LOGS (MOVED OUTSIDE AGENT ASSIGNMENT) ---
    is_fully_qualified_now = is_fully_qualified(lead)

    if is_fully_qualified_now:
        # P2.4: only advance to "Appointment Scheduled" if not already at a later stage
        if lead.funnel_stage not in ("Appointment Scheduled", "Closed Won", "Lost"):
            lead.funnel_stage = "Appointment Scheduled"
    elif has_core:
        if lead.funnel_stage == "New":
            lead.funnel_stage = "Contacted"

    if f_state:
        lead.followup_stage = f_state.follow_up_stage

    # =================================================================
    # UNIVERSAL QUALIFICATION OVERRIDE (Fires closing template safely)
    # =================================================================
    _just_closed_qualified = False
    if is_fully_qualified_now and session.status != "closed":
        loc = lead.location
        vdate = lead.visit_date

        if is_hinglish(user_message):
            final_text = f"Perfect! Aapka {loc} ka site visit {vdate} ke liye schedule ho gaya hai. Humari team jaldi hi confirmation ke liye aapse connect karegi. See you there! 🏡"
        else:
            final_text = f"Fantastic! Everything is set for your visit to {loc} on {vdate}. Our team will be in touch to confirm. Looking forward to seeing you! 🏡"

        session.status = "closed"
        _just_closed_qualified = True
        if f_state:
            f_state.follow_up_status = "completed"
            f_state.next_follow_up_at = None

        logger.info(f"🏆 LEAD FULLY QUALIFIED: {lead.phone} | Session {session_id}")

    db.commit()

    if _just_closed_qualified:
        try:
            from types import SimpleNamespace

            from app.events.lead_hot import publish_session_completed
            from app.memory.conversation_memory import conversation_memory

            _q_ctx = ""
            try:
                _q_ctx = conversation_memory.summarize_recent(
                    db, session_id=session_id, turns=10
                ) or ""
            except Exception:
                pass
            _q_snap = SimpleNamespace(
                id=lead.id,
                session_id=session_id,
                name=lead.name,
                phone=lead.phone,
                location=lead.location,
                budget=lead.budget,
                property_type=lead.property_type,
                intent=lead.intent,
                lead_temperature=lead.lead_temperature,
                conversion_probability=lead.conversion_probability,
                assigned_agent=lead.assigned_agent,
            )
            asyncio.create_task(
                publish_session_completed(
                    client_id=client_id,
                    lead=_q_snap,
                    session_id=session_id,
                    close_reason="fully_qualified",
                    chat_context=_q_ctx,
                    source="agent",
                )
            )
        except Exception as _sc_exc:  # noqa: BLE001
            logger.debug("session.completed publish skipped: %s", _sc_exc)

    # P5.1: if this lead was already synced to the CRM at create time, flag a
    # debounced re-sync so post-qualification fields (budget/location/visit_date/
    # assignee) are pushed without re-syncing on every single turn.
    _flag_crm_resync_if_synced(db, lead, session)

    if lead.score == "High" and not lead.visit_date and session.status != "closed":
        # We rely on the LLM to naturally propose a visit if the context feels right.
        pass

    # P2.6: Language output guard — English user must not receive Hinglish reply.
    # Catches mismatches from ALL paths (tool conversational_reply, response.text, fallback).
    # Fallback is field-aware so we never re-ask name/budget/etc. already on the lead.
    if detect_user_language(user_message) == "english" and is_hinglish(final_text):
        logger.warning(f"LANGUAGE_MISMATCH | session={session_id} | user=en | reply=hinglish")
        final_text = build_english_fallback_reply(lead)

    # Save Gemini's textual response to the Message table (skip if already saved inside tool call block)
    if not locals().get('message_saved', False):
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=final_text))
        db.commit()

    # Log the response speed for the ROI dashboard
    total_latency_ms = round((time.time() - start_time) * 1000)
    asyncio.create_task(
        log_event_async(session_id, "message_sent", latency_ms=total_latency_ms, agent_type="AI", client_id=client_id))

    # P2.1: Consolidated re-arm / terminal logic — single call replaces old inline block
    finalize_turn(db, session, lead, f_state)

    # Return the text response isolated from tool calls
    return final_text


def _flag_crm_resync_if_synced(db, lead, session):
    """
    P5.1: mark a lead for a debounced CRM re-sync when it was already synced at
    create time (has an external id) and isn't already flagged. The scheduled
    `crm_resync_job` picks these up so post-qualification field changes reach
    the CRM without re-pushing on every turn. Deliberately skips closed sessions
    (no point re-syncing a concluded lead on every later message).
    """
    try:
        if (
            lead.external_crm_id
            and lead.crm_sync_status == "success"
            and not lead.crm_resync_pending
            and session.status != "closed"
        ):
            lead.crm_resync_pending = True
            db.commit()
            logger.info(f"P5.1 CRM re-sync flagged for lead {lead.id}")
    except Exception as e:
        logger.warning(f"P5.1 failed to flag CRM re-sync for lead {lead.id}: {e}")