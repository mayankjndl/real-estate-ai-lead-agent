"""
Automated Follow-Up Scheduler System
Backend state machine executing scheduled follow-ups based on FollowUpState tracking.
"""
import logging
from datetime import datetime, timezone, timedelta
from twilio.rest import Client

from config import settings
from database import SessionLocal
from models import Session, Message, Lead, FollowUpState, EventLog

logger = logging.getLogger("follow_up")
logging.basicConfig(level=logging.INFO)


def generate_followup_payload(session_id: str, stage: str, db) -> str:
    """
    Modular placeholder for Anohita's Intelligence Layer.
    Currently falls back to generic stages, but will soon use predictive scoring 
    and personalized generation logic.
    """
    # This will be replaced by Anohita's layer.
    if stage == "Day 0":
        return "Hey, just checking if you're still looking for property options. Let me know!"
    elif stage == "Day 1":
        return "Hi again! I have some great matches for your property search. Are you available to chat?"
    elif stage == "Day 3":
        return "Properties in your desired area are moving fast! Let me know if you want to schedule a site visit."
    elif stage == "Day 7":
        return "Hi! I'm closing out some old inquiries. Whenever you're ready to explore properties again, just reply here!"
    return "Are you still looking for a property?"


def check_and_send_followups():
    """
    State machine execution engine for follow-ups.
    Scans the FollowUpState table for triggered follow-up windows.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # 1. Fetch all active states where next_follow_up_at <= now
        triggered_states = db.query(FollowUpState).filter(
            FollowUpState.follow_up_status == "active",
            FollowUpState.next_follow_up_at <= now
        ).all()
        
        logger.info(f"SCHEDULER_HEARTBEAT | Triggers found: {len(triggered_states)}")
        
        for state in triggered_states:
            session_id = state.session_id
            
            # Double check the session/lead to make sure it shouldn't be stopped
            session = db.query(Session).filter(Session.id == session_id).first()
            lead = db.query(Lead).filter(Lead.session_id == session_id).first()
            
            if not session:
                continue

            if session.status == "closed" or (lead and lead.visit_date):
                state.follow_up_status = "stopped"
                db.commit()
                continue
                
            # Generate Payload
            current_stage = state.follow_up_stage
            payload = generate_followup_payload(session_id, current_stage, db)
            
            # Dispatch
            success = False
            if session_id.startswith("+") and settings.TWILIO_ACCOUNT_SID:
                try:
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        from_=settings.TWILIO_PHONE_NUMBER,
                        body=payload,
                        to=f"whatsapp:{session_id}"
                    )
                    success = True
                    logger.info(f"Follow-up {current_stage} sent to {session_id}")
                except Exception as ex:
                    logger.error(f"Follow-up failed for {session_id}: {ex}")
            else:
                # If not WhatsApp, just log it as a simulation success for now
                success = True
                logger.info(f"Simulated follow-up {current_stage} sent to {session_id}")
            
            if success:
                state.follow_up_sent_at = now
                state.last_ai_reply_timestamp = now
                
                # Create EventLog
                event = EventLog(
                    session_id=session_id,
                    event_type="tracking",
                    action_type="follow_up_sent"
                )
                db.add(event)
                
                # Save as AI Message
                db.add(Message(
                    session_id=session_id,
                    role="assistant",
                    content=f"[AUTO {current_stage.upper()}] {payload}"
                ))
                
                # Transition State Machine
                if current_stage == "Day 0":
                    state.follow_up_stage = "Day 1"
                    state.next_follow_up_at = now + timedelta(days=1)
                elif current_stage == "Day 1":
                    state.follow_up_stage = "Day 3"
                    state.next_follow_up_at = now + timedelta(days=2)
                elif current_stage == "Day 3":
                    state.follow_up_stage = "Day 7"
                    state.next_follow_up_at = now + timedelta(days=4)
                elif current_stage == "Day 7":
                    state.follow_up_status = "completed"
                    state.next_follow_up_at = None
                    session.status = "closed"
                    db.add(Message(
                        session_id=session_id,
                        role="assistant",
                        content="[SESSION CLOSED DUE TO INACTIVITY]"
                    ))
                    
                db.commit()
                
    except Exception as e:
        logger.error(f"Follow-up scheduler error: {e}")
    finally:
        db.close()
