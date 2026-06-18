"""
Automated Follow-Up Scheduler System
Backend state machine executing scheduled follow-ups based on FollowUpState tracking.
Now integrated with Anohita's ML Intelligence Layer.
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from twilio.rest import Client
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from database import SessionLocal
from models import Session, Message, Lead, FollowUpState, EventLog, DLQEvent

from app.intelligence.followup_engine import generate_followup_sequence
from app.intelligence.push_wait_engine import decide_push_vs_wait
from metrics import BACKGROUND_FAILURE_COUNT, SCHEDULER_JOB_DURATION, SCHEDULER_JOB_FAILURES

logger = logging.getLogger("follow_up")
logging.basicConfig(level=logging.INFO)


# ==========================================
# STAGE RESOLVER
# ==========================================

def resolve_current_followup_stage(
    followups,
    current_day=0
):

    if not followups:
        return None

    selected = None

    for item in followups:

        if item.get("day", 0) <= current_day:
            selected = item

    if not selected:
        selected = followups[0]

    return selected


# ==========================================
# FOLLOWUP PAYLOAD BUILDER
# ==========================================

def generate_followup_payload(
    lead_data,
    assigned_agent,
    session_id,
    current_day=0,
    inactivity=False
):

    probability = lead_data.get(
        "conversion_probability",
        0
    )

    urgency = lead_data.get(
        "urgency_level",
        "low"
    )

    engagement_score = lead_data.get(
        "engagement_score",
        0
    )

    response_speed_score = lead_data.get(
        "response_speed_score",
        0
    )

    budget_alignment_score = lead_data.get(
        "budget_alignment_score",
        0
    )

    # ==========================================
    # PUSH / WAIT ENGINE
    # ==========================================

    strategy_data = decide_push_vs_wait(
        probability=probability,
        urgency=urgency,
        inactivity=inactivity,
        engagement_score=engagement_score,
        response_speed_score=response_speed_score,
        budget_alignment_score=budget_alignment_score
    )

    engagement_strategy = (
        strategy_data["strategy"]
    )

    recommended_tone = (
        strategy_data["recommended_tone"]
    )

    # ==========================================
    # GENERATE AI FOLLOWUPS
    # ==========================================

    followup_sequence = (
        generate_followup_sequence(
            lead_name=lead_data.get(
                "name"
            ),
            location=lead_data.get(
                "location"
            ),
            budget=lead_data.get(
                "budget"
            ),
            property_type=lead_data.get(
                "property_type"
            ),
            urgency=urgency,
            probability=probability,
            inactivity=inactivity,
            engagement_score=engagement_score,
            response_speed_score=response_speed_score,
            budget_alignment_score=budget_alignment_score,
            assigned_agent=(
                assigned_agent.get(
                    "assigned_agent"
                )
                if assigned_agent
                else None
            )
        )
    )

    followups = followup_sequence.get(
        "sequence",
        []
    )

    # ==========================================
    # CURRENT EXECUTION STAGE
    # ==========================================

    current_followup = (
        resolve_current_followup_stage(
            followups=followups,
            current_day=current_day
        )
    )

    # ==========================================
    # PRIORITY
    # ==========================================

    if probability >= 85:

        priority = "critical"

    elif probability >= 70:

        priority = "high"

    elif probability >= 45:

        priority = "medium"

    else:

        priority = "low"

    # ==========================================
    # FALLBACK
    # ==========================================

    if not current_followup:

        current_followup = {
            "day": current_day,
            "stage": "general_followup",
            "message": (
                "Checking in regarding your "
                "property requirements."
            )
        }

    # ==========================================
    # FINAL PAYLOAD
    # ==========================================

    return {

        # ======================================
        # CORE
        # ======================================

        "session_id": session_id,

        "generated_at": str(
            datetime.utcnow()
        ),

        # ======================================
        # LEAD INTELLIGENCE
        # ======================================

        "conversion_probability":
            probability,

        "expected_closure_days":
            lead_data.get(
                "expected_closure_days"
            ),

        "urgency_level":
            urgency,

        "priority":
            priority,

        "engagement_strategy":
            engagement_strategy,

        "recommended_tone":
            recommended_tone,

        # ======================================
        # AGENT
        # ======================================

        "assigned_agent":
            assigned_agent.get(
                "assigned_agent"
            )
            if assigned_agent
            else None,

        # ======================================
        # ANALYTICS SAFE
        # ======================================

        "stage":
            current_followup.get(
                "stage"
            ),

        "message":
            current_followup.get(
                "message"
            ),

        "delay_days":
            current_followup.get(
                "day"
            ),

        # ======================================
        # SCHEDULER SAFE
        # ======================================

        "followups":
            followups,

        "current_followup":
            current_followup,

        # ======================================
        # EXTRA INTELLIGENCE
        # ======================================

        "budget_alignment_status":
            lead_data.get(
                "budget_alignment_status"
            ),

        "response_speed_score":
            response_speed_score,

        "engagement_score":
            engagement_score,

        "inactive_lead":
            lead_data.get(
                "inactive_lead",
                False
            )
    }

# ==========================================
# MAIN SCHEDULER LOOP
# ==========================================

def check_and_send_followups():
    """
    State machine execution engine for follow-ups.
    Scans the FollowUpState table for triggered follow-up windows.
    Integrates ML dynamically via the generate_followup_payload hook.
    """
    _JOB = "check_and_send_followups"
    db = SessionLocal()
    try:
        with SCHEDULER_JOB_DURATION.labels(job_name=_JOB).time():
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

                # Maps current stage string to hour integer for the ML engine
                current_stage = state.follow_up_stage
                hour_map = {"Day 0": 0, "Day 1": 24, "Day 3": 72, "Day 7": 168}
                current_day = hour_map.get(current_stage, 0)

                # Calculate inactivity boolean
                # TEST MODE: inactivity triggers after 60 seconds instead of 7 days.
                # Production: delta.days > 7
                inactivity = False
                if state.last_user_reply_timestamp:
                    # Ensure offset-aware timestamp arithmetic
                    if state.last_user_reply_timestamp.tzinfo is None:
                        user_tz_aware = state.last_user_reply_timestamp.replace(tzinfo=timezone.utc)
                    else:
                        user_tz_aware = state.last_user_reply_timestamp

                    delta = now - user_tz_aware
                    if settings.FOLLOW_UP_TEST_MODE:
                        inactivity = delta.total_seconds() > 60  # 1 minute in test mode
                    else:
                        inactivity = delta.days > 7
                logger.info(f"INACTIVITY_FLAG={inactivity} | session={session_id} | test_mode={settings.FOLLOW_UP_TEST_MODE}")
                if inactivity and state:
                    state.inactivity_score = (state.inactivity_score or 0) + 1

                    # --- NEW: Bridge Scheduler Inactivity with ML Lead Data ---
                    if lead:
                        # 1. Sync the penalty score to the Leads table (10 points per missed follow-up)
                        lead.inactivity_penalty = state.inactivity_score * 10

                        # 2. Cool down the lead's conversion probability
                        if lead.conversion_probability and lead.conversion_probability > 10:
                            lead.conversion_probability -= 5

                        # 3. Automatically downgrade temperature if they ignore us too long
                        if getattr(lead, 'conversion_probability', 0) < 55:
                            lead.lead_temperature = "cold"
                            lead.score = "Low"
                    # -----------------------------------------------------------

                    logger.info(f"INACTIVITY_SCORE incremented to {state.inactivity_score} | session={session_id}")

                # Parameter Mapping
                lead_data = {}
                assigned_agent = None
                if lead:
                    lead_data = {
                        "name": lead.name,
                        "location": lead.location,
                        "budget": lead.budget,
                        "property_type": lead.property_type,
                        "conversion_probability": getattr(lead, "conversion_probability", 0) or 0,
                        "urgency_level": getattr(lead, "urgency_level", "low") or "low",
                        "engagement_score": getattr(lead, "engagement_score", 0) or 0,
                        "expected_closure_days": getattr(lead, "expected_closure_days", 0),
                        "budget_alignment_status": "aligned",
                        "response_speed_score": 50, # Default or mocked
                        "inactive_lead": inactivity
                    }
                    assigned_agent = {"assigned_agent": getattr(lead, "assigned_agent", "ABC Properties Team") or "ABC Properties Team"}

                try:
                    # DLQ TEST HOOK: set FOLLOW_UP_DLQ_TEST=true in .env (alongside TEST_MODE)
                    # to force a DLQ entry. Check dlq_events table, then remove it from .env.
                    if settings.FOLLOW_UP_TEST_MODE and settings.FOLLOW_UP_DLQ_TEST:
                        raise Exception("QA_DLQ_TEST — intentional failure to verify DLQ pipeline")

                    # Day 7 is the final stage — send a closure notice, not another follow-up.
                    # Skip the ML engine entirely and close the session cleanly.
                    if current_stage == "Day 7":
                        closure_msg = (
                            f"Hi {lead.name or 'there'}, we haven't heard back from you in a while. "
                            f"We'll pause our updates for now. Feel free to reach out anytime — "
                            f"we're happy to help with your property search. Take care! 🏡"
                        )
                        if session_id.startswith("+") and settings.TWILIO_ACCOUNT_SID:
                            try:
                                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                                to_number = f"whatsapp:{session_id}" if lead and lead.source == "whatsapp" else session_id
                                client.messages.create(
                                    from_=settings.TWILIO_PHONE_NUMBER,
                                    body=closure_msg,
                                    to=to_number
                                )
                            except Exception as ex:
                                logger.error(f"Closure message failed for {session_id}: {ex}")
                        state.follow_up_status = "stopped"
                        state.next_follow_up_at = None
                        session.status = "closed"
                        db.add(Message(session_id=session_id, client_id=state.client_id, role="assistant", content=f"[AUTO DAY7 CLOSURE] {closure_msg}"))
                        db.add(Message(session_id=session_id, client_id=state.client_id, role="assistant", content="[SESSION CLOSED DUE TO INACTIVITY]"))
                        db.commit()
                        continue

                    # ML Engine Call
                    generated_payload = generate_followup_payload(
                        lead_data=lead_data,
                        assigned_agent=assigned_agent,
                        session_id=session_id,
                        current_day=current_day,
                        inactivity=inactivity
                    )

                    payload_msg = generated_payload.get("message")
                    if not payload_msg:
                        raise ValueError("ML Engine returned an empty message payload.")

                    # Dispatch
                    success = False
                    success = False
                    followup_latency_ms = None

                    # --- FIX: Check raw lead.phone instead of prefixed session_id ---
                    if lead and lead.phone and lead.phone.startswith("+") and settings.TWILIO_ACCOUNT_SID:
                        try:
                            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                            to_number = f"whatsapp:{lead.phone}" if lead and lead.source == "whatsapp" else lead.phone

                            @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30),
                                   reraise=True)
                            def _send_twilio_msg():
                                client.messages.create(
                                    from_=settings.TWILIO_PHONE_NUMBER,
                                    body=payload_msg,
                                    to=to_number
                                )

                            _twilio_start = time.time()
                            _send_twilio_msg()
                            followup_latency_ms = round((time.time() - _twilio_start) * 1000)

                            success = True
                            logger.info(f"Follow-up {current_stage} sent to {session_id} via {'WhatsApp' if lead and lead.source == 'whatsapp' else 'SMS'} | latency={followup_latency_ms}ms")
                        except Exception as ex:
                            logger.error(f"Follow-up Twilio push failed for {session_id}: {ex}")
                            raise ex
                    else:
                        success = True
                        logger.info(f"Simulated follow-up {current_stage} sent to {session_id}")

                    if success:
                        state.follow_up_sent_at = now
                        state.last_ai_reply_timestamp = now

                        # --- FIX: Sync count and lead stage ---
                        session.follow_up_count = (session.follow_up_count or 0) + 1
                        if lead:
                            lead.followup_stage = current_stage
                        # --------------------------------------

                        # Create EventLog with latency
                        event = EventLog(
                            session_id=session_id,
                            client_id=state.client_id,
                            event_type="tracking",
                            action_type=f"{current_stage} follow_up_sent",  # <-- FIX IS HERE
                            latency_ms=followup_latency_ms
                        )
                        db.add(event)

                        # Save as AI Message
                        db.add(Message(
                            session_id=session_id,
                            client_id=state.client_id,
                            role="assistant",
                            content=f"[AUTO {current_stage.upper()}] {payload_msg}"
                        ))

                        # Transition State Machine
                        followups = generated_payload.get("followups", [])
                        # TEST MODE: collapse inter-stage gaps to 1 minute each.
                        # Production: gaps come from the ML payload (24h, 48h, 96h).
                        def _next_delay(prod_hours):
                            if settings.FOLLOW_UP_TEST_MODE:
                                return timedelta(minutes=1)
                            return timedelta(hours=prod_hours)

                        if current_stage == "Day 0" and len(followups) > 1:
                            state.follow_up_stage = "Day 1"
                            prod_hours = followups[1].get("day", 24) - followups[0].get("day", 0)
                            state.next_follow_up_at = now + _next_delay(prod_hours)
                        elif current_stage == "Day 1" and len(followups) > 2:
                            state.follow_up_stage = "Day 3"
                            prod_hours = followups[2].get("day", 72) - followups[1].get("day", 24)
                            state.next_follow_up_at = now + _next_delay(prod_hours)
                        elif current_stage == "Day 3" and len(followups) > 3:
                            state.follow_up_stage = "Day 7"
                            prod_hours = followups[3].get("day", 168) - followups[2].get("day", 72)
                            state.next_follow_up_at = now + _next_delay(prod_hours)
                        elif current_stage == "Day 7" or len(followups) <= 1:
                            state.follow_up_status = "stopped"
                            state.next_follow_up_at = None
                            session.status = "closed"
                            db.add(Message(
                                session_id=session_id,
                                client_id=state.client_id,
                                role="assistant",
                                content="[SESSION CLOSED DUE TO INACTIVITY]"
                            ))

                        db.commit()
                except Exception as ml_err:
                    logger.error(f"ML Follow-up Engine failed for session {session_id}: {ml_err}")
                    BACKGROUND_FAILURE_COUNT.labels(component="scheduler").inc()

                    # Push to DLQ instead of crashing scheduler
                    try:
                        dlq_entry = DLQEvent(
                            target_endpoint="ml_followup_scheduler",
                            payload={"session_id": session_id, "stage": current_stage, "lead_data": lead_data},
                            error_trace=str(ml_err),
                            status="pending",
                            client_id=state.client_id
                        )
                        db.add(dlq_entry)
                        db.commit()
                    except Exception as dlq_err:
                        logger.error(f"Failed to write ML error to DLQ for {session_id}: {dlq_err}")

    except Exception as e:
        logger.error(f"Follow-up scheduler main loop error: {e}")
        SCHEDULER_JOB_FAILURES.labels(job_name=_JOB).inc()
    finally:
        db.close()