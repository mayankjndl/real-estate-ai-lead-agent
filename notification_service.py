import logging
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone, timedelta

from twilio.rest import Client

from config import settings
from database import SessionLocal
from models import Lead, NotificationLog, Agent

logger = logging.getLogger("notification_service")


def send_fallback_email(agent_email: str, agent_name: str, lead: Lead, reason: str):
    """Sends an email fallback if Twilio WhatsApp dispatch fails."""
    try:
        smtp_host = settings.SMTP_HOST
        smtp_port = settings.SMTP_PORT
        smtp_user = settings.SMTP_USER
        smtp_pass = settings.SMTP_PASS

        if not smtp_user or not smtp_pass:
            logger.error("Email fallback failed: SMTP credentials not configured in environment.")
            return

        msg = EmailMessage()
        msg['Subject'] = f"🚨 URGENT: Hot Lead Alert (System Fallback) - {lead.name or 'Unknown'}"
        msg['From'] = smtp_user
        msg['To'] = agent_email

        dashboard_link = f"http://localhost:3000/crm?lead_id={lead.id}"
        body = f"""
Hello {agent_name},

Our WhatsApp notification system encountered a connectivity issue. 
This is an automated EMAIL FALLBACK for a Hot Lead.

Lead Name: {lead.name or 'Unknown'}
Intent: {lead.intent or 'explore'}
Property Type: {lead.property_type or 'property'}
Location: {lead.location or 'Pune'}
Budget: {lead.budget or 'TBD'}

Reason for Alert: {reason}

Please contact the lead immediately.
View in CRM: {dashboard_link}
        """
        msg.set_content(body)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info(f"Fallback email successfully sent to {agent_email}")
    except Exception as email_err:
        logger.error(f"Fallback email dispatch failed: {email_err}")


async def trigger_hot_lead_notification(lead_id: int, reason: str = "High-intent behavior detected"):
    """
    Asynchronously fires a WhatsApp notification to the assigned agent.
    Guarantees idempotency (no duplicate spam).
    """
    with SessionLocal() as db:
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return

            # 1. IDEMPOTENCY CHECK
            existing_log = db.query(NotificationLog).filter(
                NotificationLog.lead_id == lead.id,
                NotificationLog.status.in_(["pending_ack", "acknowledged", "escalated_10m", "escalated_30m"])
            ).first()

            if existing_log:
                logger.info(f"Notification bypassed: Lead {lead.id} already has an active escalation state.")
                return

            # 2. RESOLVE AGENT VIA DATABASE
            target_agent = None
            if lead.assigned_agent:
                target_agent = db.query(Agent).filter(
                    Agent.client_id == lead.client_id,
                    Agent.name == lead.assigned_agent
                ).first()

            if not target_agent:
                target_agent = db.query(Agent).filter(
                    Agent.client_id == lead.client_id,
                    Agent.is_manager == True
                ).first()

            agent_phone = target_agent.phone if target_agent else lead.phone
            agent_name = target_agent.name if target_agent else (lead.assigned_agent or "Unassigned")
            # Safe fallback to Admin Email if agent email is missing
            agent_email = target_agent.email if target_agent else settings.ADMIN_EMAIL

            # 3. FORMAT THE MESSAGE
            dashboard_link = f"http://localhost:3000/crm?lead_id={lead.id}"
            message_body = (
                f"🚨 *Hot Lead Alert*\n\n"
                f"*{lead.name or 'Unknown'}* is looking to {lead.intent or 'explore'} a "
                f"{lead.property_type or 'property'} in {lead.location or 'Pune'} "
                f"with a budget of {lead.budget or 'TBD'}.\n\n"
                f"*Reason:* {reason}\n"
                f"*Next Action:* Please contact within 10 minutes.\n\n"
                f"View Lead: {dashboard_link}"
            )

            delivery_status = "pending_ack"
            twilio_sid = None

            # 4. DISPATCH VIA TWILIO
            if settings.TEST_MODE:
                logger.info(f"[TEST MODE] Simulated WhatsApp Alert to {agent_name} ({agent_phone})")
            elif settings.TWILIO_ACCOUNT_SID:
                try:
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    to_number = f"whatsapp:{agent_phone}" if not agent_phone.startswith("whatsapp:") else agent_phone

                    # Construct status callback URL
                    base_url = settings.WEBHOOK_BASE_URL
                    status_callback_url = f"{base_url}/api/v1/webhook/twilio-status" if base_url else None

                    message = client.messages.create(
                        from_=settings.TWILIO_PHONE_NUMBER,
                        body=message_body,
                        to=to_number,
                        status_callback=status_callback_url
                    )
                    twilio_sid = message.sid
                    delivery_status = "pending_ack"
                    logger.info(f"WhatsApp Alert dispatched to {agent_name} | SID: {twilio_sid}")
                except Exception as e:
                    logger.error(f"WhatsApp Alert failed: {e}. Triggering Email Fallback.")
                    delivery_status = "failed"
                    # Trigger Email Fallback gracefully
                    send_fallback_email(agent_email, agent_name, lead, reason)

            # 5. CREATE AUDIT LOG (10-minute escalation timer)
            escalation_deadline = datetime.now(timezone.utc) + timedelta(minutes=10)
            new_log = NotificationLog(
                client_id=lead.client_id,
                lead_id=lead.id,
                assigned_agent=agent_name,
                status=delivery_status,
                escalate_at=escalation_deadline,
                twilio_message_sid=twilio_sid
            )
            db.add(new_log)
            db.commit()

        except Exception as e:
            logger.error(f"Notification Engine crashed: {e}")