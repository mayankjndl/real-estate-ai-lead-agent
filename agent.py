import json
import logging
import string
import time
from datetime import datetime, timezone
import google.generativeai as genai
from config import settings
from system_prompt import REAL_ESTATE_SYSTEM_PROMPT
from sqlalchemy.orm import Session as DBSession
from models import Session, Message, Lead
from rag import retrieve

# 1. Gemini Initialization
genai.configure(api_key=settings.GEMINI_API_KEY)
logger = logging.getLogger("agent")

# 2. Lightweight Guardrail Helpers
def check_topic_drift(query: str) -> bool:
    """Detects if the user has drifted from real estate topics."""
    query_lower = query.lower()
    off_topic = ["weather", "news", "movie", "food", "joke"]
    re_keywords = ["rent", "buy", "invest", "price", "bhk", "flats", "apartments", "properties", "listings", "available", "options", "villa"]
    return any(w in query_lower for w in off_topic) and not any(w in query_lower for w in re_keywords)

def is_vague_without_location(query: str, lead) -> bool:
    """Blocks vague queries if no location is specified or remembered."""
    query_lower = query.lower()
    vague_triggers = ["cheap", "affordable", "budget", "options", "listings", "flats", "any available"]
    
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
    intent_val = str(intent_val).title()
    
    if "intent" in args and args["intent"]:
        args["intent"] = str(args["intent"]).title()
        
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
        
        # Check for direct or fuzzy match in canonical list
        canonical_match = next((area for area in canonical_locations if area.lower() in loc_lower), None)
        
        if canonical_match:
            args["location"] = canonical_match
        else:
            # Check fallback mapping if missing from canonical list
            fallback_match = next((fallback for key, fallback in fallback_mapping.items() if key in loc_lower), None)
            if fallback_match:
                args["location"] = fallback_match
            elif " or " in loc_lower or "," in loc_lower:
                # Basic fallback for multiple unknown locations
                args["location"] = loc_lower.replace(" or ", ",").split(",")[0].strip().title()

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
    visit_date: str = None
):
    """
    Saves or updates the lead's information in the database. Use this tool silently when the
    user shares their budget, location, intent (buy/rent/investment), name, phone number,
    or a requested visit date/time.

    Args:
        name: The name of the client.
        phone: The phone number of the client.
        budget: The requested budget range (e.g., '80L', '20k', '1Cr').
        location: The area they are looking in (e.g., 'Hinjewadi', 'Pune').
        property_type: The type of property they want (e.g., '1BHK', '2BHK', 'Villa').
        intent: The goal (e.g., 'buy', 'rent', 'investment', 'browsing').
        score: Your internal lead scoring evaluation (High, Medium, Low).
        visit_date: The user's requested visit date/time (e.g., 'Tuesday 2pm', 'Saturday morning').
    """
    pass  # Schema definition only. Execution is handled in process_chat.

# Initialize the generative model with Anohita's system instruction and the extraction tool
model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    system_instruction=REAL_ESTATE_SYSTEM_PROMPT,
    tools=[extract_lead_info]
)

# Lightweight stateless model is no longer needed — replaced with zero-latency smart templates

# 3. Stateful Memory Function
async def process_chat(session_id: str, user_message: str, db: DBSession, client_id: str = "default", is_background: bool = False) -> str:
    """
    Main orchestrator for user input. Fetches memory, injects context to the LLM, 
    extracts function calls for lead generation, and commits all data to DB.
    """
    
    # Ensure session and lead exist in the database exactly once to prevent redundant queries
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        session = Session(id=session_id, client_id=client_id)
        db.add(session)
        
    lead = db.query(Lead).filter(Lead.session_id == session_id).first()
    if not lead:
        lead = Lead(session_id=session_id)
        db.add(lead)
        
    db.commit()
    # User replied — reset follow-up state
    session.follow_up_count = 0
    session.last_activity_at = datetime.now(timezone.utc)
    
    # Detect if user is naturally closing the conversation
    msg_lower = user_message.lower().strip()
    # Remove punctuation
    msg_clean = msg_lower.translate(str.maketrans('', '', string.punctuation))
    closing_phrases = ["thanks", "thank you", "bye", "goodbye", "ok thanks", "perfect thanks", "done", "great thanks", "thanks a lot"]
    
    if any(msg_clean == p for p in closing_phrases) or msg_clean.endswith(" bye") or msg_clean.endswith(" thanks"):
        session.status = "closed"
        logger.info(f"Session {session_id} marked as CLOSED (user concluded conversation).")
    else:
        session.status = "active"
    db.commit()

    # Save the new user message to the Message table
    db.add(Message(session_id=session_id, role="user", content=user_message))
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
    
    if msg_clean in INSTANT_REPLIES:
        instant_reply = INSTANT_REPLIES[msg_clean]
        db.add(Message(session_id=session_id, role="assistant", content=instant_reply))
        db.commit()
        logger.info(f"INSTANT_INTERCEPT | session={session_id} | bypassed LLM")
        return instant_reply

    # -----------------------------------
    # Anohita's Lightweight Guardrail Intercepts
    # -----------------------------------
    guardrail_reply = None
    
    if check_topic_drift(user_message):
        guardrail_reply = "I specialize in Pune real estate. Shall we get back to your property search?"
    elif is_vague_without_location(user_message, lead):
        guardrail_reply = "I'd be happy to help! Which specific area in Pune are you looking into? (e.g., Wakad, Kharadi, Baner)"
        
    if guardrail_reply:
        db.add(Message(session_id=session_id, role="assistant", content=guardrail_reply))
        db.commit()
        logger.info(f"GUARDRAIL_INTERCEPT | session={session_id} | bypassed LLM")
        return guardrail_reply

    # LIMIT CONTEXT: last 10 turns (20 messages) — keeps enough history for the full
    # conversation to remain coherent, including the user's opening requirements.
    past_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id.desc()).limit(20).all()
    past_messages.reverse()

    formatted_history = []
    # Build history excluding the just-saved user message.
    # Strip [AUTO FOLLOW-UP] prefix so follow-up messages don't inflate token count.
    for m in past_messages[:-1]:
        role = "user" if m.role == "user" else "model"
        clean_content = m.content.replace("[AUTO FOLLOW-UP] ", "")
        formatted_history.append({"role": role, "parts": [clean_content]})
        
    # Anohita Memory Summarization Logic
    # Inject the FULL persisted lead state so the LLM always knows what was captured,
    # even if the original extraction message has rolled out of the 12-message window.
    summary_text = ""
    if lead:
        summary_parts = [
            f"Location: {lead.location}" if lead.location else None,
            f"Budget: {lead.budget}" if lead.budget else None,
            f"Property Type: {lead.property_type}" if lead.property_type else None,
            f"Intent: {lead.intent}" if lead.intent else None,
            f"Name: {lead.name}" if lead.name else None,
            f"Visit scheduled: {lead.visit_date}" if lead.visit_date else None,
        ]
        parts = [p for p in summary_parts if p]
        if parts:
            summary_text = "Known about this user: " + ", ".join(parts) + ".\n"

    # Keyword gateway: only call RAG (Gemini Embedding API) for property-related queries.
    # Greetings, acks, and short responses skip the embedding call, saving 1-4s per message.
    PROPERTY_KEYWORDS = {
        "flat", "bhk", "rent", "buy", "invest", "area", "location", "baner", "wakad",
        "hinjewadi", "price", "budget", "property", "apartment", "villa", "plot",
        "2bhk", "3bhk", "1bhk", "pune", "noida", "mumbai", "sqft", "furnish",
        "visit", "book", "schedule", "bedroom", "floor", "tower", "society",
        "possession", "ready", "availability", "cheap", "affordable", "luxury",
    }
    words = user_message.lower().split()
    is_property_query = any(w.strip(".,!?") in PROPERTY_KEYWORDS for w in words)

    # Fetch RAG Context from the FAQ store (only for property-related queries)
    user_message_for_llm = f"Summary: {summary_text}\nUser Message: {user_message}"
    if is_property_query:
        rag_start = time.time()
        try:
            context_items, score = retrieve(user_message)
            rag_time = round((time.time() - rag_start) * 1000)
            logger.info(json.dumps({"event": "rag_retrieval", "latency_ms": rag_time, "success": True}))
            if score < 0.8 and context_items:
                context_text = "\n".join([
                    f"- {item['location']} {item['type']}: {item['details']} ({item['description']})"
                    for item in context_items
                ])
                user_message_for_llm = f"Summary: {summary_text}\nProperty Context:\n{context_text}\n\nUser Message: {user_message}"
        except Exception as e:
            rag_time = round((time.time() - rag_start) * 1000)
            logger.error(json.dumps({"event": "rag_retrieval", "latency_ms": rag_time, "success": False, "error": type(e).__name__}))
    else:
        logger.info(f"RAG skipped (non-property query) for session={session_id}")

    # Start Gemini Chat with retrieved history
    chat = model.start_chat(history=formatted_history)

    # Send the history + new message to Gemini (with retry logic for API reliability)
    max_retries = 3
    response = None
    for attempt in range(max_retries):
        llm_start = time.time()
        try:
            response = await chat.send_message_async(user_message_for_llm)
            llm_time = round((time.time() - llm_start) * 1000)
            logger.info(json.dumps({"event": "llm_main_call", "latency_ms": llm_time, "attempt": attempt + 1, "success": True}))
            break  # Success — exit retry loop
        except Exception as e:
            llm_time = round((time.time() - llm_start) * 1000)
            logger.warning(json.dumps({"event": "llm_main_call", "latency_ms": llm_time, "attempt": attempt + 1, "success": False, "error": type(e).__name__}))
            if attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                time.sleep(wait_time)
            else:
                logger.error(json.dumps({"event": "llm_main_fatal", "error": type(e).__name__, "session": session_id}))
                # Proper closure — no false promise, offer human support immediately
                fallback = (
                    "I'm currently experiencing a technical issue and couldn't process your request. "
                    "Our team is here to help — please reach us directly at *+91 9876543210* "
                    "or try again in a few minutes. Apologies for the inconvenience! 🙏"
                )
                db.add(Message(session_id=session_id, role="assistant", content=fallback))
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
                break

    if fc and fc.name == "extract_lead_info":
        # Extract and normalize arguments payload securely
        args = normalize_lead_data(dict(fc.args), existing_intent=lead.intent)
        
        # Update Lead table fields dynamically (using the in-memory lead object)
        if "name" in args: lead.name = args["name"]
        
        # Automatically capture WhatsApp number from session context
        if session_id.startswith("+") and not lead.phone:
            lead.phone = session_id
        elif "phone" in args: 
            lead.phone = args["phone"]
        if "budget" in args: lead.budget = args["budget"]
        if "location" in args: lead.location = args["location"]
        if "property_type" in args: lead.property_type = args["property_type"]
        if "intent" in args: lead.intent = args["intent"]
        if "score" in args: lead.score = args["score"]
        if "visit_date" in args: lead.visit_date = args["visit_date"]

        
        db.commit()

        # Zero-latency smart template reply — replaces expensive second LLM call
        # Saves 5-18s per CRM-update message with no loss in conversational quality
        visit_concluded = bool(lead and lead.visit_date and lead.phone)
        captured_fields = [k for k in ["name", "phone", "budget", "location", "property_type", "intent", "visit_date"] if k in args]

        if visit_concluded:
            loc = lead.location or "the property"
            vdate = lead.visit_date or "your requested time"
            local_reply = f"Fantastic! Everything is set for your visit to {loc} on {vdate}. Our team will be in touch to confirm. Looking forward to seeing you! 🏡"
        elif "visit_date" in args:
            loc = lead.location or "the property"
            local_reply = f"Great, I've noted your visit request for {args['visit_date']}! Our team will confirm the details shortly. Anything else you'd like to know about {loc}?"
        elif "budget" in args and "location" in args:
            local_reply = f"Perfect, I've saved your budget of {lead.budget} for a property in {lead.location}. When are you looking to move in, or would you like to schedule a visit?"
        elif "budget" in args:
            local_reply = f"Got it, budget of {lead.budget} noted! Which area in Pune are you looking at?"
        elif "location" in args and "intent" in args:
            intent_str = lead.intent.lower() if lead.intent else "buy"
            local_reply = f"Great choice! {lead.location} is a fantastic area to {intent_str}. What's your approximate budget?"
        elif "location" in args:
            local_reply = f"Noted — {lead.location} is on your list! Are you looking to buy or rent, and what's your budget range?"
        elif "name" in args:
            local_reply = f"Nice to meet you, {lead.name}! What kind of property are you looking for?"
        else:
            local_reply = "Got it, I've noted your details! What else can I help you find?"

        db.add(Message(session_id=session_id, role="assistant", content=local_reply))
        db.commit()
        logger.info(f"LEAD_EXTRACT | session={session_id} | fields={captured_fields} | concluded={visit_concluded}")
        return local_reply

    # Safely get the final text (handling cases where only a tool call was returned)
    try:
        final_text = response.text
    except ValueError:
        final_text = "I've noted those details. What else can I help you find today?"

    # Anohita's Conversion Intelligence Logic
    history_text = " ".join([m.content for m in past_messages if m.role == "user"]).lower() + " " + user_message.lower()
    calculated_score = "low"
    if any(x in history_text for x in ["visit", "book", "finalize", "ready"]):
        calculated_score = "high"
    elif any(x in history_text for x in ["budget", "options", "compare", "price"]):
        calculated_score = "medium"
        
    # Dynamically ensure phone number is correctly parsed even if LLM bypasses function extraction
    if session_id.startswith("+") and not lead.phone:
        lead.phone = session_id
    
    lead.score = calculated_score.capitalize()
    db.commit()

    if calculated_score == "high":
        if not lead.visit_date and session.status != "closed":
            final_text += "\n\nWould you like me to arrange a visit or share details?"
    elif calculated_score == "medium":
        if not lead.visit_date and session.status != "closed":
            final_text += "\n\nI can refine options further if you'd like."

    # Save Gemini's textual response to the Message table
    db.add(Message(session_id=session_id, role="assistant", content=final_text))
    db.commit()
    
    # Return the text response isolated from tool calls
    return final_text