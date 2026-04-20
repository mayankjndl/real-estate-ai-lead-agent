import json
import logging
import google.generativeai as genai
from config import settings
from system_prompt import REAL_ESTATE_SYSTEM_PROMPT
from sqlalchemy.orm import Session as DBSession
from models import Session, Message, Lead

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
    score: str = None
):
    """
    Saves or updates the lead's information in the database. Use this tool silently when the user shares their budget, location, intent (buy/rent/investment), name, or phone number.

    Args:
        name: The name of the client.
        phone: The phone number of the client.
        budget: The requested budget range (e.g., '80L', '20k', '1Cr').
        location: The area they are looking in (e.g., 'Hinjewadi', 'Pune').
        intent: The goal (e.g., 'buy', 'rent', 'investment', 'browsing').
        score: Your internal lead scoring evaluation (High, Medium, Low).
    """
    pass # This function is a schema definition for Gemini. Execution is handled manually in process_chat.

# Initialize the generative model with the Anohita's system instruction and the extraction tool
model = genai.GenerativeModel(
    model_name=settings.GEMINI_MODEL,
    system_instruction=REAL_ESTATE_SYSTEM_PROMPT,
    tools=[extract_lead_info]
)

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
    from datetime import datetime, timezone
    session.follow_up_count = 0
    session.last_activity_at = datetime.now(timezone.utc)
    
    # Detect if user is naturally closing the conversation
    msg_lower = user_message.lower().strip()
    # Remove punctuation
    import string
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

    # LIMIT CONTEXT: last 6 turns (12 messages) — enough for natural conversation,
    # small enough to keep the Gemini payload fast and reduce first-token latency.
    past_messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.id.desc()).limit(12).all()
    past_messages.reverse()

    formatted_history = []
    # Build history excluding the just-saved user message.
    # Strip [AUTO FOLLOW-UP] prefix so follow-up messages don't inflate token count.
    for m in past_messages[:-1]:
        role = "user" if m.role == "user" else "model"
        clean_content = m.content.replace("[AUTO FOLLOW-UP] ", "")
        formatted_history.append({"role": role, "parts": [clean_content]})
        
    # Anohita Memory Summarization Logic
    lead_summary = db.query(Lead).filter(Lead.session_id == session_id).first()
    summary_text = ""
    if lead_summary:
        summary_text = f"User: {lead_summary.location or 'unknown'}, Budget: {lead_summary.budget or 'unknown'}, Intent: {lead_summary.intent or 'unknown'}\n"

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
    from rag import retrieve
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
    import time
    max_retries = 2 # Initial try + 1 retry
    response = None
    for attempt in range(max_retries):
        try:
            response = chat.send_message(user_message_for_llm)
            break  # Success — exit retry loop
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
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
        
        db.commit()

        # PERFORMANCE: Do NOT send the tool result back to Gemini for a follow-up
        # response — that would fire a SECOND Gemini API call (~5s extra latency).
        # Instead, generate the continuation reply locally based on what was just saved.
        # The lead is already in the DB; Gemini's confirmation sentence is cosmetic only.
        captured_fields = [k for k in ["name", "phone", "budget", "location", "intent"] if k in args]
        if "name" in args:
            local_reply = f"Got it, {args['name']}! "
        else:
            local_reply = "Got it! "

        if "budget" in args and "location" in args:
            local_reply += f"I'm looking for options in {args['location']} within your budget. What else would you like to know?"
        elif "budget" in args:
            local_reply += "I've noted your budget. Which area in Pune are you considering?"
        elif "location" in args:
            local_reply += f"Great choice — {args['location']} has some excellent options. What's your budget range?"
        elif "phone" in args:
            local_reply += "Our team will reach out to you shortly. Is there anything else I can help you with?"
        else:
            local_reply += "I've updated your profile. What else can I help you find today?"

        db.add(Message(session_id=session_id, role="assistant", content=local_reply))
        db.commit()
        logger.info(f"LEAD_EXTRACT | session={session_id} | fields={captured_fields} | local_reply (no 2nd Gemini call)")
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