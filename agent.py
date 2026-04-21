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

# 4. Structured Tool Calling Definition
def extract_lead_info(
    name: str = None,
    phone: str = None,
    budget: str = None,
    location: str = None,
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

# Lightweight stateless model used ONLY to generate a natural one-line reply after
# lead extraction. No system prompt, no tools, no history — keeps it fast (~400-800ms).
reply_model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)

# 3. Stateful Memory Function
def process_chat(session_id: str, user_message: str, db: DBSession, client_id: str = "default", is_background: bool = False) -> str:
    """
    Main orchestrator for user input. Fetches memory, injects context to the LLM, 
    extracts function calls for lead generation, and commits all data to DB.
    """
    
    # Ensure session exists in the database
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        session = Session(id=session_id, client_id=client_id)
        db.add(session)
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
    lead_summary = db.query(Lead).filter(Lead.session_id == session_id).first()
    summary_text = ""
    if lead_summary:
        summary_parts = [
            f"Location: {lead_summary.location}" if lead_summary.location else None,
            f"Budget: {lead_summary.budget}" if lead_summary.budget else None,
            f"Intent: {lead_summary.intent}" if lead_summary.intent else None,
            f"Name: {lead_summary.name}" if lead_summary.name else None,
            f"Visit scheduled: {lead_summary.visit_date}" if lead_summary.visit_date else None,
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
        try:
            context_items, score = retrieve(user_message)
            if score < 0.8 and context_items:
                context_text = "\n".join([
                    f"- {item['location']} {item['type']}: {item['details']} ({item['description']})"
                    for item in context_items
                ])
                user_message_for_llm = f"Summary: {summary_text}\nProperty Context:\n{context_text}\n\nUser Message: {user_message}"
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
    else:
        logger.info(f"RAG skipped (non-property query) for session={session_id}")

    # Start Gemini Chat with retrieved history
    chat = model.start_chat(history=formatted_history)

    # Send the history + new message to Gemini (with retry logic for API reliability)
    max_retries = 2
    response = None
    for attempt in range(max_retries):
        try:
            response = chat.send_message(user_message_for_llm)
            break  # Success — exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 0.5  # flat short wait — 2 attempts only, no need for full backoff
                logger.warning(f"Gemini API attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Gemini API failed after {max_retries} attempts: {e}")
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
        # Extract arguments payload securely
        args = fc.args
        
        # Fetch existing lead record or create a new one
        lead = db.query(Lead).filter(Lead.session_id == session_id).first()
        if not lead:
            lead = Lead(session_id=session_id)
            db.add(lead)
        
        # Update Lead table fields dynamically
        if "name" in args: lead.name = args["name"]
        
        # Automatically capture WhatsApp number from session context
        if session_id.startswith("+") and not lead.phone:
            lead.phone = session_id
        elif "phone" in args: 
            lead.phone = args["phone"]
        if "budget" in args: lead.budget = args["budget"]
        if "location" in args: lead.location = args["location"]
        if "intent" in args: lead.intent = args["intent"]
        if "score" in args: lead.score = args["score"]
        if "visit_date" in args: lead.visit_date = args["visit_date"]

        
        db.commit()

        # Generate a context-aware reply using a STATELESS Gemini call.
        # Pass the FULL current lead state from DB so it never re-asks for things
        # that were already captured in an earlier turn.
        captured_fields = [k for k in ["name", "phone", "budget", "location", "intent", "visit_date"] if k in args]

        # Build the full picture of what we already know about this lead from the DB
        full_lead = db.query(Lead).filter(Lead.session_id == session_id).first()
        already_known = []
        if full_lead:
            if full_lead.name:       already_known.append(f"name={full_lead.name}")
            if full_lead.phone:      already_known.append(f"phone={full_lead.phone}")
            if full_lead.budget:     already_known.append(f"budget={full_lead.budget}")
            if full_lead.location:   already_known.append(f"location={full_lead.location}")
            if full_lead.intent:     already_known.append(f"intent={full_lead.intent}")
            if full_lead.visit_date: already_known.append(f"visit_date={full_lead.visit_date}")

        known_str = ", ".join(already_known) if already_known else "nothing yet"
        visit_concluded = bool(full_lead and full_lead.visit_date and full_lead.phone)

        if visit_concluded:
            mini_prompt = (
                f"You are a friendly real estate assistant. "
                f"The user just said: \"{user_message}\". "
                f"The visit is fully arranged — you already have: {known_str}. "
                f"Write ONE warm closing sentence confirming everything is set. "
                f"Do NOT ask any more questions — the conversation is complete."
            )
        else:
            mini_prompt = (
                f"You are a friendly real estate assistant. "
                f"The user just said: \"{user_message}\". "
                f"You already know these details about them: {known_str}. "
                f"Write ONE warm sentence acknowledging what they said. "
                f"Then, ask exactly ONE logical follow-up question for the most important MISSING piece of information. "
                f"Priority of missing info to ask for: 1. Budget 2. Location 3. Property Type/Intent 4. Visit Date 5. Name/Contact. "
                f"Do NOT ask for anything that is already in the 'already know' list! Keep it under 2 lines."
            )

        try:
            mini_response = reply_model.generate_content(mini_prompt)
            local_reply = mini_response.text.strip()
        except Exception as e:
            logger.warning(f"Mini reply model failed: {e} — using fallback")
            local_reply = "Got it! I've noted your details and our team will be in touch shortly."

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
        
    lead = db.query(Lead).filter(Lead.session_id == session_id).first()
    if not lead:
        lead = Lead(session_id=session_id)
        db.add(lead)
        
    # Dynamically ensure phone number is correctly parsed even if LLM bypasses function extraction
    if session_id.startswith("+") and not lead.phone:
        lead.phone = session_id
    
    lead.score = calculated_score.capitalize()
    db.commit()

    if calculated_score == "high":
        final_text += "\n\nWould you like me to arrange a visit or share details?"
    elif calculated_score == "medium":
        final_text += "\n\nI can refine options further if you'd like."

    # Save Gemini's textual response to the Message table
    db.add(Message(session_id=session_id, role="assistant", content=final_text))
    db.commit()
    
    # Return the text response isolated from tool calls
    return final_text