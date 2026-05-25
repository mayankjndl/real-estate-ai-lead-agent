import asyncio
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
from models import DLQEvent, EventLog, Message
from datetime import datetime, timezone

from config import settings
from twilio.rest import Client
from crm_sync import _push_to_hubspot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - DLQ Replay - %(levelname)s - %(message)s')
logger = logging.getLogger("dlq_replay")

async def process_hubspot_crm(payload: dict) -> bool:
    try:
        await _push_to_hubspot(payload)
        return True
    except Exception as e:
        logger.error(f"HubSpot CRM Replay Failed: {e}")
        return False

def process_twilio_outbound(payload: dict) -> bool:
    if not settings.TWILIO_ACCOUNT_SID:
        logger.warning("Twilio credentials missing, cannot replay.")
        return False
    
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=settings.TWILIO_PHONE_NUMBER,
            body=payload.get("body"),
            to=payload.get("to")
        )
        return True
    except Exception as e:
        logger.error(f"Twilio Outbound Replay Failed: {e}")
        return False

def process_ml_followup(payload: dict, db: Session) -> bool:
    try:
        # Import dynamically to avoid circular issues
        from follow_up import generate_followup_payload
        
        session_id = payload.get("session_id")
        current_stage = payload.get("stage", "Day 0")
        lead_data = payload.get("lead_data", {})
        
        day_map = {"Day 0": 0, "Day 1": 1, "Day 3": 3, "Day 7": 7}
        current_day = day_map.get(current_stage, 0)
        
        # We mock assigned_agent here just to replay the message payload generation
        assigned_agent = {"assigned_agent": lead_data.get("assigned_agent", "ABC Properties Team")}
        
        generated = generate_followup_payload(
            lead_data=lead_data,
            assigned_agent=assigned_agent,
            session_id=session_id,
            current_day=current_day,
            inactivity=lead_data.get("inactive_lead", False)
        )
        
        payload_msg = generated.get("message")
        if not payload_msg:
            raise ValueError("Empty message generated.")
            
        if settings.TWILIO_ACCOUNT_SID:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_=settings.TWILIO_PHONE_NUMBER,
                body=payload_msg,
                to=f"whatsapp:{session_id}" if session_id.startswith("+") else session_id
            )
            
        # Log successful recovery
        event = EventLog(session_id=session_id, event_type="tracking", action_type="follow_up_sent_from_dlq")
        db.add(event)
        db.add(Message(session_id=session_id, role="assistant", content=f"[DLQ RECOVERY {current_stage.upper()}] {payload_msg}"))
        db.commit()
        return True
    except Exception as e:
        logger.error(f"ML Followup Replay Failed: {e}")
        return False

async def main():
    logger.info("Starting DLQ Replay Job...")
    db = SessionLocal()
    try:
        pending_events = db.query(DLQEvent).filter(DLQEvent.status == "pending").all()
        if not pending_events:
            logger.info("No pending events in DLQ.")
            return

        logger.info(f"Found {len(pending_events)} pending events. Beginning replay...")
        success_count = 0
        
        for event in pending_events:
            logger.info(f"Replaying Event ID: {event.id} | Target: {event.target_endpoint}")
            
            success = False
            
            if event.target_endpoint == "hubspot_crm":
                success = await process_hubspot_crm(event.payload)
            elif event.target_endpoint == "twilio_outbound":
                success = process_twilio_outbound(event.payload)
            elif event.target_endpoint == "ml_followup_scheduler":
                success = process_ml_followup(event.payload, db)
            else:
                logger.warning(f"Unknown target endpoint: {event.target_endpoint}")
                
            if success:
                event.status = "resolved"
                db.commit()
                logger.info(f"[PASS] Event {event.id} resolved.")
                success_count += 1
            else:
                logger.error(f"[FAIL] Event {event.id} failed again. Keeping as pending.")
                
        logger.info(f"DLQ Replay complete. {success_count}/{len(pending_events)} events recovered successfully.")
    except Exception as e:
        logger.error(f"DLQ Replay Job crashed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
