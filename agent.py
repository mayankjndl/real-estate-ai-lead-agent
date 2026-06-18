import json
import logging
import string
import time
import asyncio
from datetime import datetime, timezone
import google.generativeai as genai
from config import settings
from system_prompt import REAL_ESTATE_SYSTEM_PROMPT
from sqlalchemy.orm import Session as DBSession
from models import Session, Message, Lead, EventLog
from rag import retrieve
from app.intelligence.lead_scoring import calculate_lead_score
from app.intelligence.agent_matcher import match_best_agent

# 1. Gemini Initialization
genai.configure(api_key=settings.GEMINI_API_KEY)
logger = logging.getLogger("agent")
PUNE_AREAS = ["wakad", "hinjewadi", "baner", "kharadi", "kothrud", "hadapsar",
                  "ravet", "balewadi", "aundh", "pashan", "viman nagar", "magarpatta",
                  "kondhwa", "undri", "mundhwa", "punawale", "tathawade", "bavdhan",
                  "sinhagad road", "pune"]

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

    return args


# 4. Structured Tool Calling Definition
def extract_lead_info(
        name: str = None,
        phone: str = None,
        budget: str = None,
        location: str = None,
        property_type: str = None,
        intent: str = None,
        score: str = None,
        visit_date: str = None,
        conversational_reply: str = None
):
    """
    Saves the lead's property search details to the CRM database.

    ⚠️  WHEN TO CALL THIS TOOL:
    ONLY call this tool when the user explicitly provides NEW personal search information:
    - Their name
    - Their phone number
    - Their budget (e.g. "80 lakhs", "25k per month", "1.2 crores")
    - Their preferred location (e.g. "Baner", "Wakad", "Hinjewadi")
    - Their property type preference (e.g. "2BHK", "3BHK", "Villa")
    - Their intent (buy / rent / investment)
    - A requested visit date or time

    ⛔ DO NOT CALL THIS TOOL for:
    - General property questions ("What are prices in Baner?")
    - Questions about amenities, connectivity, traffic, schools
    - Acknowledgements ("Thanks", "Perfect", "Ok", "Got it")
    - Greetings ("Hi", "Hello", "Hey")
    - Any message that doesn't contain NEW personal search data
    For those messages, respond naturally with text only.

    Args:
        name: The name of the client (VERY IMPORTANT to capture).
        phone: The phone number of the client.
        budget: The requested budget range (e.g., '80L', '20k', '1Cr').
        location: The area they are looking in. If they mention multiple or add a new area to an existing search, return BOTH areas combined (e.g., 'Baner, Wakad').
        property_type: The type of property they want (e.g., '1BHK', '2BHK', 'Villa'). MUST remain empty/None if the user has not explicitly stated a size. Do NOT guess or default to 2BHK.
        intent: The goal (e.g., 'buy', 'rent', 'investment', 'browsing').
        score: Your internal lead scoring evaluation (High, Medium, Low).
        visit_date: The user's requested visit date/time (e.g., 'Tuesday 2pm', 'Saturday morning').
        conversational_reply: Your natural, conversational response to the user's message. MUST NOT BE EMPTY.

    INTENT-BASED BEHAVIOR:
    - HIGH: Be proactive. Offer a specific next step like shortlisting or a site visit.
    - MEDIUM: Provide data/description only. Do NOT ask follow-up questions or offer next steps. Answer and STOP.
    - LOW: Provide general info. Ask one clarifying question (e.g., buy vs. rent) to narrow the search.
    - CRITICAL: For Medium/Low intent, you are FORBIDDEN from ending with "Would you like to see options?" or "Shall I help you buy?"

    -----------------------------------
    🔹 TOOL CALL RULE (CRITICAL):
    - Whenever you call extract_lead_info, you MUST also write a conversational text reply in the SAME response.
    - The text reply should naturally continue the conversation based on what the user said.
    - NEVER return a function call without also including a text message.
    - Do NOT mention data capture, fields, or databases in your text reply.
    """
    pass  # Schema definition only. Execution is handled in process_chat.


# Initialize the generative model with the AI's system instruction and the extraction tool
model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    system_instruction=REAL_ESTATE_SYSTEM_PROMPT,
    tools=[extract_lead_info]
)


# 3. Stateful Memory Function
async def process_chat(session_id: str, user_message: str, db: DBSession, client_id: int = 1,
                       is_background: bool = False) -> str:
    """
    Main orchestrator for user input. Fetches memory, injects context to the LLM,
    extracts function calls for lead generation, and commits all data to DB.
    """
    start_time = time.time()

    # Ensure session and lead exist in the database exactly once to prevent redundant queries
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        session = Session(id=session_id, client_id=client_id)
        db.add(session)

    lead = db.query(Lead).filter(Lead.session_id == session_id).first()
    if not lead:
        lead = Lead(session_id=session_id, client_id=client_id)
        db.add(lead)
        latency = round((time.time() - start_time) * 1000)
        asyncio.create_task(log_event_async(session_id, "lead_created", latency_ms=latency, client_id=client_id))

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


        # Ensure ALL mandatory fields are present before marking follow-up complete
        is_fully_qualified = bool(
            lead and lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)

        if is_fully_qualified:
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
    msg_lower = user_message.lower().strip()
    # Remove punctuation
    msg_clean = msg_lower.translate(str.maketrans('', '', string.punctuation))
    closing_phrases = ["thanks", "thank you", "goodbye", "ok thanks", "perfect thanks", "done", "great thanks",
                       "thanks a lot", "stop"]

    logger.info(f"DEBUG_MSG_CLEAN: '{msg_clean}' (original: '{user_message}')")

    # --- FIX: Support explicit opt-out phrases to stop follow-ups ---
    opt_out_phrases = ["dont message", "stop messaging", "dont contact", "please stop"]
    is_opt_out = any(phrase in msg_clean for phrase in opt_out_phrases)

    if any(msg_clean == p for p in closing_phrases) or msg_clean.startswith(
            "stop") or "bye" in msg_clean or is_opt_out or msg_clean.endswith(" thanks"):
        session.status = "closed"
        logger.info(f"Session {session_id} marked as CLOSED (user concluded conversation).")
    else:
        session.status = "active"
    db.commit()

    # Save the new user message to the Message table
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
        return guardrail_reply

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
        if sanitized_history and sanitized_history[-1]["role"] == msg["role"]:
            sanitized_history[-1]["parts"][0] += " " + msg["parts"][0]
        else:
            sanitized_history.append(msg)
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

        # THE FIX: If they want to visit but are missing details, force Gemini to naturally ask for them.
        if lead.visit_date and missing_fields:
            summary_text += f"CRITICAL INSTRUCTION: The user has requested a visit, but we are missing mandatory details: {', '.join(missing_fields)}. You MUST naturally ask them for these missing details before finalizing the visit. Do NOT say the visit is fully booked yet.\n"

    # Dynamic Repetition Prevention
    # Check if the agent already proactively asked for the name in recent history.
    # If so, forcefully instruct the LLM not to ask again to prevent an endless loop.
    if not lead.name:
        for m in past_messages[:-1]:
            if m.role == "assistant" and any(
                    ph in m.content.lower() for ph in ["name", "speaking with", "who is this", "know you as"]):
                summary_text += "SYSTEM NOTE: You have already asked for their name in a previous message. DO NOT ask for their name again. Focus ONLY on their property requirements.\n"
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
                timeout=2.0
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

    # Start Gemini Chat with retrieved history
    chat = model.start_chat(history=formatted_history)

    # 2c: Dynamic Name Interceptor (Concurrent, strict timeout)
    # If the user's name is unknown and they give a short response, dynamically extract it.
    # Wrapped in a 2-second timeout to guarantee it NEVER causes latency spikes.
    name_extraction_task = None
    # Expanded: fire on any message up to 12 words when name is unknown.
    # Property query restriction removed — name must be captured even if the message
    # also mentions a location or BHK type (those are handled by extract_lead_info).
    if not lead.name and len(user_message.split()) <= 12:
        name_model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        name_extraction_task = asyncio.create_task(
            asyncio.wait_for(
                name_model.generate_content_async(
                    f"Extract the person's name from this message. Return ONLY the extracted name, or 'NONE' if no name is present. Message: '{user_message}'"
                ),
                timeout=2.0
            )
        )

    # Send the history + new message to Gemini (with retry logic for API reliability)
    max_retries = 3
    response = None
    for attempt in range(max_retries):
        llm_start = time.time()
        try:
            if attempt == 0 and name_extraction_task:
                # Run the main chat and the name extraction concurrently.
                # return_exceptions=True prevents the 2s timeout from crashing the main chat.
                # Added 6.0s strict timeout to prevent catastrophic 35s latency spikes.
                results = await asyncio.gather(
                    asyncio.wait_for(chat.send_message_async(user_message_for_llm), timeout=6.0),
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
                        if extracted_name and extracted_name.upper() != "NONE":
                            lead.name = extracted_name
                            db.commit()
                            logger.info(f"CONCURRENT_NAME_INTERCEPT | session={session_id} | name={extracted_name}")
                    except Exception as e:
                        logger.warning(f"Fast name extraction text parsing failed: {e}")
            else:
                response = await asyncio.wait_for(chat.send_message_async(user_message_for_llm), timeout=6.0)

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
            logger.warning(json.dumps(
                {"event": "llm_main_call", "latency_ms": llm_time, "attempt": attempt + 1, "success": False,
                 "error": type(e).__name__, "detail": str(e)[:200]}))
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                await asyncio.sleep(wait_time)
            else:
                logger.error(json.dumps({"event": "llm_main_fatal", "error": type(e).__name__, "detail": str(e)[:200],
                                         "session": session_id}))
                # Proper closure — no false promise, offer human support immediately
                fallback = (
                    "I'm currently experiencing a technical issue and couldn't process your request. "
                    "Our team is here to help — please reach us directly at *+91 [CLIENT_SUPPORT_NUMBER]* "
                    "or try again in a few minutes. Apologies for the inconvenience! 🙏"
                )
                db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=fallback))
                db.commit()
                return fallback

    # 5. Database Commits & Tool Execution Handling
    # Detect if Gemini triggered the lead extraction tool
    fc = None
    # We look inside the 'parts' of the response to find the function call
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                fc = part.function_call
                if fc and fc.name == "extract_lead_info":
                    # Extract and normalize arguments payload securely
                    args = normalize_lead_data(dict(fc.args), existing_intent=lead.intent)

                    # Snapshot which fields are GENUINELY NEW in this turn vs already known.
                    # This prevents re-extracted old data from triggering the same template repeatedly.
                    prev_budget = lead.budget
                    prev_location = lead.location
                    prev_intent = lead.intent
                    prev_name = lead.name
                    prev_visit_date = lead.visit_date
                    prev_property_type = lead.property_type
                    was_fully_qualified = bool(lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)

                    # Update Lead table fields dynamically (using the in-memory lead object)
                    if "name" in args: lead.name = args["name"]

                    # Phone from args (explicit user input) — session_id auto-set happens above
                    if "phone" in args:
                        lead.phone = args["phone"]
                    if "budget" in args: lead.budget = args["budget"]
                    if "location" in args: lead.location = args["location"]
                    if "property_type" in args: lead.property_type = args["property_type"]
                    if "intent" in args: lead.intent = args["intent"]
                    if "score" in args: lead.score = args["score"]
                    if "visit_date" in args: lead.visit_date = args["visit_date"]

                    db.commit()

                    # Determine which fields are truly new this turn (value changed or was None before)
                    new_fields = set()
                    if "budget" in args and args["budget"] != prev_budget: new_fields.add("budget")
                    if "location" in args and args["location"] != prev_location: new_fields.add("location")
                    if "intent" in args and args["intent"] != prev_intent: new_fields.add("intent")
                    if "name" in args and args["name"] != prev_name: new_fields.add("name")
                    if "visit_date" in args and args["visit_date"] != prev_visit_date: new_fields.add("visit_date")
                    if "property_type" in args and args["property_type"] != prev_property_type: new_fields.add(
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
                    if not text_from_response:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'text') and part.text and part.text.strip():
                                text_from_response = part.text.strip()
                                break

                    is_fully_qualified = bool(
                        lead and lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)
                    captured_fields = [k for k in
                                       ["name", "phone", "budget", "location", "property_type", "intent", "visit_date"]
                                       if k in args]

                    # ONLY fire the confirmation when the lead crosses from incomplete to fully complete
                    if is_fully_qualified and not was_fully_qualified:
                        # TEMPLATE 1: Visit fully booked!
                        loc = lead.location
                        vdate = lead.visit_date
                        local_reply = f"Fantastic! Everything is set for your visit to {loc} on {vdate}. Our team will be in touch to confirm. Looking forward to seeing you! 🏡"

                        # Properly lock the session and follow-ups
                        session.status = "closed"
                        if f_state:
                            f_state.follow_up_status = "completed"
                            f_state.next_follow_up_at = None

                    elif text_from_response:
                        # PRIMARY PATH: Use Gemini's own text from this same single response.
                        # Gemini sees the full 20-message conversation history, so it knows
                        # what was said, handles all context correctly, and produces natural
                        # replies with zero additional API calls or latency overhead.
                        local_reply = text_from_response

                    else:
                        # SAFETY FALLBACK: Gemini returned only a function call with no text.
                        # Should be rare now that system prompt instructs text alongside tool calls.
                        # No CTAs in fallbacks — just clean, concise acknowledgements.
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

                    db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=local_reply))
                    db.commit()
                    logger.info(
                        f"LEAD_EXTRACT | session={session_id} | fields={captured_fields} | new_fields={list(new_fields)} | has_gemini_text={text_from_response is not None} | concluded={is_fully_qualified}")
                    final_text = local_reply
                    extracted_early = True
                    message_saved = True
                    break

    # Safely get the final text (handling cases where only a tool call was returned)
    if 'extracted_early' not in locals():
        try:
            if not response.candidates or not response.candidates[0].content.parts:
                finish = response.candidates[0].finish_reason if response.candidates else 'None'
                logger.warning(f"Empty response from Gemini. finish_reason: {finish}. Using smart local fallback.")
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
            logger.warning(f"ValueError accessing response.text. Parts: {response.candidates[0].content.parts}")
            final_text = "Got it. Let me know if you need anything else or want to schedule a visit."

    # ==========================================
    # NEW ML INTELLIGENCE LAYER
    # ==========================================
    history_text = " ".join([m.content for m in past_messages if m.role == "user"]).lower() + " " + user_message.lower()

    memory_dicts = []
    for m in past_messages:
        memory_dicts.append({
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat() if hasattr(m, "timestamp") and m.timestamp else None
        })

    # 1. Calculate advanced lead score
    ml_score_data = calculate_lead_score(
        query=user_message,
        memory=memory_dicts,
        intent=lead.intent or "low"
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

    # --- CRITICAL FIX: Use strict 6-field qualification ---
    is_fully_qualified = bool(
        lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)
    has_visit = bool(lead.visit_date)
    has_core = all([lead.location, lead.budget, lead.property_type, lead.intent])

    if is_fully_qualified:
        prob = max(prob, 88)
        lead.lead_temperature = "hot"
        lead.expected_closure_days = min(lead.expected_closure_days, 7)
    elif has_visit:
        prob = max(prob, 82)
        lead.lead_temperature = "hot"

    lead.conversion_probability = prob

    if prob >= 82:
        lead.score = "High"
    elif prob >= 55:
        lead.score = "Medium"
    else:
        lead.score = "Low"

    # 2. Match Best Agent
    agent_data = match_best_agent(
        location=lead.location,
        query=history_text
    )

    if agent_data.get("assigned_agent"):
        lead.assigned_agent = agent_data["assigned_agent"]

    # --- FIX: SYNCHRONIZE FUNNEL STAGE WITH EVENT LOGS ---
    if is_fully_qualified:  # <--- FIX: Only jump to Appointment Scheduled if ALL fields are captured!
        if lead.funnel_stage not in ["Site Visit Done", "Closed Won"]:
            lead.funnel_stage = "Appointment Scheduled"
    elif has_core:
        if lead.funnel_stage == "New":
            lead.funnel_stage = "Contacted"

    # Sync the dormant followup_stage column so the dashboard reads it accurately
    if f_state:
        lead.followup_stage = f_state.follow_up_stage
    # -----------------------------------------------------

    db.commit()

    if lead.score == "High" and not lead.visit_date and session.status != "closed":
        # We rely on the LLM to naturally propose a visit if the context feels right.
        pass

    # Save Gemini's textual response to the Message table (skip if already saved inside tool call block)
    if not locals().get('message_saved', False):
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=final_text))
        db.commit()

    # Log the response speed for the ROI dashboard
    total_latency_ms = round((time.time() - start_time) * 1000)
    asyncio.create_task(
        log_event_async(session_id, "message_sent", latency_ms=total_latency_ms, agent_type="AI", client_id=client_id))

    # Re-arm Day 0 follow-up scheduler
    if f_state:
        from datetime import timedelta
        f_state.last_ai_reply_timestamp = datetime.now(timezone.utc)

        # Check qualification again to be safe
        is_fully_qualified_now = bool(
            lead and lead.visit_date and lead.phone and lead.name and lead.location and lead.budget and lead.property_type)

        if session.status != "closed":
            if not is_fully_qualified_now:  # <--- FIX: Keep followups ACTIVE until the lead is 100% complete
                f_state.follow_up_stage = "Day 0"
                f_state.follow_up_status = "active"
                # TEST MODE: compress Day 0 to 1 minute. Production: 30 minutes.
                day0_delay = timedelta(minutes=1) if settings.FOLLOW_UP_TEST_MODE else timedelta(minutes=30)
                f_state.next_follow_up_at = datetime.now(timezone.utc) + day0_delay
            else:
                f_state.follow_up_status = "completed"
                f_state.next_follow_up_at = None
        db.commit()

    # Return the text response isolated from tool calls
    return final_text