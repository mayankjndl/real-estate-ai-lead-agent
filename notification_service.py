import logging
from datetime import datetime, timezone, timedelta

from twilio.rest import Client

from config import settings
from database import SessionLocal
from models import Lead, NotificationLog, Agent

logger = logging.getLogger("notification_service")

async def trigger_hot_lead_notification(lead_id: int, reason: str = "High-intent behavior detected"):
    """
    Asynchronously fires a WhatsApp notification to the assigned agent.
    Guarantees idempotency (no duplicate spam).
    """
    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return

        # 1. IDEMPOTENCY CHECK: Did we already notify an agent about this lead?
        existing_log = db.query(NotificationLog).filter(
            NotificationLog.lead_id == lead.id,
            NotificationLog.status.in_(["pending_ack", "acknowledged", "escalated"])
        ).first()

        if existing_log:
            logger.info(f"Notification bypassed: Lead {lead.id} already has an active escalation state.")
            return

        # 2. RESOLVE AGENT VIA DATABASE
        target_agent = None
        if lead.assigned_agent:
            # Find the specific agent assigned to this lead
            target_agent = db.query(Agent).filter(
                Agent.client_id == lead.client_id,
                Agent.name == lead.assigned_agent
            ).first()

        if not target_agent:
            # Fallback: Find the Team Manager for this client
            target_agent = db.query(Agent).filter(
                Agent.client_id == lead.client_id,
                Agent.is_manager == True
            ).first()

        # Extreme Fallback (For local testing so it doesn't crash if DB is empty)
        agent_phone = target_agent.phone if target_agent else lead.phone
        agent_name = target_agent.name if target_agent else (lead.assigned_agent or "Unassigned")

        # 3. FORMAT THE APPROVED PDF MESSAGE
        dashboard_link = f"http://localhost:3000/crm?lead_id={lead.id}"
        message_body = (
            f"🚨 *Hot Lead Alert*\n\n"
            f"*{lead.name or 'Unknown'}* is looking to {lead.intent or 'explore'} a "
            f"{lead.property_type or 'property'} in {lead.location or 'Pune'} "
            f"with a budget of {lead.budget or 'TBD'}.\n\n"
            f"*Reason:* {reason}\n"
            f"*Next Action:* Please contact within 15 minutes.\n\n"
            f"View Lead: {dashboard_link}"
        )

        # 4. DISPATCH VIA TWILIO
        if settings.TEST_MODE:
            logger.info(f"[TEST MODE] Simulated WhatsApp Alert to {agent_name} ({agent_phone})")
            delivery_status = "pending_ack"
        elif settings.TWILIO_ACCOUNT_SID:
            try:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                to_number = f"whatsapp:{agent_phone}" if not agent_phone.startswith("whatsapp:") else agent_phone
                client.messages.create(
                    from_=settings.TWILIO_PHONE_NUMBER,
                    body=message_body,
                    to=to_number
                )
                delivery_status = "pending_ack"
                logger.info(f"WhatsApp Alert dispatched to {agent_name}")
            except Exception as e:
                logger.error(f"WhatsApp Alert failed: {e}")
                delivery_status = "failed"  # Email fallback goes here later

        # 5. CREATE AUDIT LOG (15-minute escalation timer)
        escalation_deadline = datetime.now(timezone.utc) + timedelta(minutes=15)
        new_log = NotificationLog(
            client_id=lead.client_id,
            lead_id=lead.id,
            assigned_agent=agent_name,
            status=delivery_status,
            escalate_at=escalation_deadline
        )
        db.add(new_log)
        db.commit()

    except Exception as e:
        logger.error(f"Notification Engine crashed: {e}")
        db.rollback()
    finally:
        db.close()