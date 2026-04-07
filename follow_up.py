"""
Automated Follow-Up System
Periodically scans for stale sessions and sends AI-personalized (or static) follow-up messages.
"""
import logging
from datetime import datetime, timezone, timedelta
from twilio.rest import Client

import google.generativeai as genai
from config import settings
from database import SessionLocal
from models import Session, Message

logger = logging.getLogger("follow_up")
logging.basicConfig(level=logging.INFO)

# Static fallback messages (used when USE_AI_FOLLOWUPS is False or if AI call fails)
STATIC_FOLLOWUPS = [
    "Hey, just checking if you're still looking for property options. I can share some great matches!",
    "Hi again! I wanted to follow up one last time. If you're still interested, I'm here to help with any property queries. Feel free to reach out anytime!"
]

CLOSING_MESSAGE = "It seems like you're busy right now. No worries at all! Whenever you're ready to explore property options, feel free to come back. I'll be here to help. Have a great day!"


def generate_ai_followup(session_id: str, follow_up_number: int, db) -> str:
    """
    Uses Gemini to generate a personalized follow-up message based on conversation history.
    Falls back to static message if AI call fails.
    """
    try:
        # Fetch recent conversation history for context
        messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.id.desc()).limit(6).all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        # Build a summary of recent conversation
        history_text = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        if follow_up_number == 1:
            instruction = (
                "You are a real estate assistant. The user hasn't replied for a while. "
                "Based on the conversation below, generate a brief, warm, personalized follow-up message. "
                "Reference specific details they mentioned (budget, location, property type). "
                "End with a helpful question or offer. Keep it to 2-3 sentences max.\n\n"
                f"Recent conversation:\n{history_text}"
            )
        else:
            instruction = (
                "You are a real estate assistant. This is your FINAL follow-up to a user who hasn't replied. "
                "Based on the conversation below, generate a brief, friendly closing message. "
                "Let them know you're available whenever they're ready. Keep it warm and to 2-3 sentences max.\n\n"
                f"Recent conversation:\n{history_text}"
            )
        
        model = genai.GenerativeModel(model_name=settings.GEMINI_MODEL)
        response = model.generate_content(instruction)
        return response.text.strip()
        
    except Exception as e:
        logger.warning(f"AI follow-up generation failed for session {session_id}: {e}")
        # Fall back to static message
        idx = min(follow_up_number - 1, len(STATIC_FOLLOWUPS) - 1)
        return STATIC_FOLLOWUPS[idx]


def check_and_send_followups():
    """
    The main scheduled job. Scans all active sessions for stale ones and sends follow-ups.
    Called periodically by APScheduler.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        delay = timedelta(minutes=settings.FOLLOW_UP_DELAY_MINUTES)
        cutoff_time = now - delay
        
        # Find all active sessions where last activity is older than the delay
        stale_sessions = db.query(Session).filter(
            Session.status == "active",
            Session.last_activity_at < cutoff_time,
            Session.follow_up_count < settings.FOLLOW_UP_MAX_COUNT
        ).all()
        
        for session in stale_sessions:
            # Check that the last message was from the assistant (user hasn't replied)
            last_msg = db.query(Message).filter(
                Message.session_id == session.id
            ).order_by(Message.id.desc()).first()
            
            if not last_msg or last_msg.role == "user":
                # Last message was from user — they spoke, just no AI reply somehow. Skip.
                continue
            
            next_followup_number = session.follow_up_count + 1
            logger.info(f"Sending follow-up #{next_followup_number} to session: {session.id}")
            
            # Generate follow-up message
            if settings.USE_AI_FOLLOWUPS:
                followup_text = generate_ai_followup(session.id, next_followup_number, db)
            else:
                idx = min(next_followup_number - 1, len(STATIC_FOLLOWUPS) - 1)
                followup_text = STATIC_FOLLOWUPS[idx]
            
            # Save the follow-up as an assistant message
            db.add(Message(
                session_id=session.id,
                role="assistant",
                content=f"[AUTO FOLLOW-UP] {followup_text}"
            ))
            
            # Send the outbound message via Twilio if it's a WhatsApp session
            if session.id.startswith("+") and settings.TWILIO_ACCOUNT_SID:
                try:
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        from_=settings.TWILIO_PHONE_NUMBER,
                        body=followup_text,
                        to=f"whatsapp:{session.id}"
                    )
                    logger.info(f"Successfully pushed Twilio outbound message to {session.id}")
                except Exception as ex:
                    logger.error(f"Failed to push Twilio outbound message to {session.id}: {ex}")

            session.follow_up_count = next_followup_number
            session.last_activity_at = now  # Reset timer for next follow-up window
            db.commit()
            
            logger.info(f"Follow-up #{next_followup_number} sent to session {session.id}")
        
        # Close sessions that have exhausted all follow-ups
        exhausted_sessions = db.query(Session).filter(
            Session.status == "active",
            Session.follow_up_count >= settings.FOLLOW_UP_MAX_COUNT,
            Session.last_activity_at < cutoff_time
        ).all()
        
        for session in exhausted_sessions:
            # Check last message is not from user (they haven't replied)
            last_msg = db.query(Message).filter(
                Message.session_id == session.id
            ).order_by(Message.id.desc()).first()
            
            if last_msg and last_msg.role != "user":
                session.status = "closed"
                db.add(Message(
                    session_id=session.id,
                    role="assistant",
                    content=f"[SESSION CLOSED] {CLOSING_MESSAGE}"
                ))
                db.commit()
                logger.info(f"Session {session.id} closed after {settings.FOLLOW_UP_MAX_COUNT} unanswered follow-ups.")
    
    except Exception as e:
        logger.error(f"Follow-up scheduler error: {e}")
    finally:
        db.close()
