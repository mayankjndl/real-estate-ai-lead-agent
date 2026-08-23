import asyncio
import csv
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Optional

import redis.asyncio as aioredis
import stripe
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Depends, HTTPException, Security, status, Request, Form, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security.api_key import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

import auth
import models
from app.agents.qualification import process_chat
from app.agents.whatsapp_agent import whatsapp_agent_v3
from app.knowledge_graph.neo4j_kg import knowledge_graph
from app.memory.conversation_memory import conversation_memory
from config import settings, tenant_id_ctx, request_id_ctx


def _select_chat_fn():
    """Phase 5 (5.1): FEATURE_WHATSAPP_V3 selects the v3 orchestrator.

    Returns the async chat function to use for /chat and /whatsapp routes.
    Legacy (default) keeps the original `agent.process_chat` pipeline.
    """
    if getattr(settings, "FEATURE_WHATSAPP_V3", False):
        return whatsapp_agent_v3.process_chat
    return process_chat


async def _publish_bus_event(
    event_type: str,
    client_id: int,
    entity_id: str,
    payload: Optional[dict] = None,
    source: str = "main",
) -> Optional[str]:
    """Best-effort Redis Streams publish. Never raises; never blocks product path hard."""
    try:
        from app.clients.event_bus_client import event_bus

        if not getattr(event_bus, "_running", False):
            return None
        return await event_bus.publish(
            event_type,
            f"Client_{client_id}",
            str(entity_id),
            payload or {},
            source=source,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("BUS_PUBLISH_FAIL | type=%s entity=%s err=%s", event_type, entity_id, exc)
        return None


def _is_lead_qualified(lead) -> bool:
    """6-field gate used before visit confirmation (same rule as agent qualification)."""
    if lead is None:
        return False
    return bool(
        lead.visit_date
        and lead.phone
        and lead.name
        and lead.location
        and lead.budget
        and lead.property_type
    )


async def _emit_turn_events(
    *,
    client_id: int,
    scoped_session_id: str,
    lead,
    source_channel: str,
    is_new_lead: bool,
    message: str = "",
    db: Optional[DBSession] = None,
) -> None:
    """Publish lifecycle events so CEO bus agents (scoring/CRM/KG/arm) run on real traffic.

    PR #10 / BA-2: when ``db`` is set, attaches ``chat_context`` for n8n / scoring.
    Qualify-close also dual-publishes ``session.completed`` (PR #10 alias).
    """
    if lead is None or not getattr(lead, "id", None):
        return
    lead_id = lead.id
    chat_context = ""
    if db is not None:
        try:
            chat_context = (
                conversation_memory.summarize_recent(
                    db, session_id=scoped_session_id, turns=10
                )
                or ""
            )[:4000]
        except Exception as exc:  # noqa: BLE001
            logger.debug("chat_context summarize skipped: %s", exc)
    base = {
        "lead_id": lead_id,
        "session_id": scoped_session_id,
        "source": source_channel,
        "name": lead.name,
        "phone": lead.phone,
        "location": lead.location,
        "budget": lead.budget,
        "property_type": lead.property_type,
        "intent": lead.intent,
        "lead_temperature": getattr(lead, "lead_temperature", None),
        "conversion_probability": getattr(lead, "conversion_probability", None),
        "budget_alignment_status": getattr(lead, "budget_alignment_status", None),
        "chat_context": chat_context,
    }
    channel_event = "whatsapp.received" if source_channel == "whatsapp" else (
        "chat.received" if source_channel in ("chat", "web", "api") else f"{source_channel}.received"
    )
    await _publish_bus_event(channel_event, client_id, str(lead_id), {**base, "message": (message or "")[:500]})
    if is_new_lead:
        await _publish_bus_event("lead.created", client_id, str(lead_id), base)
    await _publish_bus_event("conversation.updated", client_id, str(lead_id), base)
    if _is_lead_qualified(lead):
        await _publish_bus_event("lead.qualified", client_id, str(lead_id), base)


async def _send_whatsapp_via_ee(
    client_id: int,
    to: str,
    body: str,
    entity_id: str,
    source: str = "main",
    media_url: Optional[str] = None,
) -> dict:
    """Outbound WhatsApp through AutomationEngine → WhatsAppExecutor (DLQ-protected)."""
    from app.execution_engine.outbound import send_whatsapp_async

    return await send_whatsapp_async(
        to=to,
        body=body,
        tenant_id=f"Client_{client_id}",
        entity_id=entity_id,
        source=source,
        media_url=media_url,
    )

from crm_sync import crm_resync_job
from database import engine, Base, get_db, SessionLocal
from follow_up import check_and_send_followups
from metrics import BACKGROUND_FAILURE_COUNT, INTEGRATION_FAILURES
from app.api.events import router as events_router

# Create a global set to protect background tasks from garbage collection
running_bg_tasks = set()

def send_critical_alert(title: str, detail: str):
    """Simulates sending a webhook alert to Slack/Discord/Email"""
    logger.error(f"🚨 [CRITICAL ALERT DISPATCHED TO TEAM] {title}: {detail}")

# Admin Security for Revenue Phase
ADMIN_API_KEY_NAME = "X-Admin-Token"
admin_api_key_header = APIKeyHeader(name=ADMIN_API_KEY_NAME, auto_error=True)

def verify_admin_key(api_key: str = Security(admin_api_key_header)):
    admin_key = os.getenv("ADMIN_API_KEY")
    if not admin_key or admin_key == "real-estate-super-secret-key":
        raise RuntimeError("CRITICAL SECURITY RISK: ADMIN_API_KEY is missing or insecure in .env.")
    if api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing Admin API Key"
        )
    return api_key


# Configure Central App Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class SecurePIILogFilter(logging.Filter):
    def filter(self, record):
        req_id = request_id_ctx.get()
        tenant_id = tenant_id_ctx.get()
        msg = str(record.msg)

        # PII MASKING: Mask Phone Numbers (e.g. +919163962356 -> +91******2356)
        msg = re.sub(r'(\+\d{1,3})\d{6,8}(\d{4})', r'\1******\2', msg)
        # PII MASKING: Mask Emails (e.g. aritro@gmail.com -> a***@gmail.com)
        msg = re.sub(r'([a-zA-Z])[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'\1***@\2', msg)

        record.msg = f"[Req: {req_id}] [Tenant: {tenant_id}] {msg}"
        return True


# Apply the PII filter to all logs
for handler in logging.root.handlers:
    handler.addFilter(SecurePIILogFilter())
logger = logging.getLogger("main")

# Automatically orchestrate DB creation on application boot
Base.metadata.create_all(bind=engine)

# Redis-based distributed locking for multi-worker concurrency
redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

# Track server start time for uptime reporting in /health
import datetime as _dt
APP_START_TIME = _dt.datetime.now(_dt.timezone.utc)

from db_backup import backup_postgres

# --- Background Scheduler for Follow-Up System & Maintenance ---
def daily_cleanup_job():
    logger.info("Running daily maintenance cleanup...")
    db = SessionLocal()  # Create a dedicated standard DB session
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        # Delete old EventLogs
        deleted_events = db.query(models.EventLog).filter(models.EventLog.timestamp < cutoff).delete()
        # Sessions and their cascaded dependencies
        deleted_sessions = db.query(models.Session).filter(models.Session.last_activity_at < cutoff).delete()
        db.commit()
        logger.info(f"Cleanup complete. Deleted {deleted_events} EventLogs and {deleted_sessions} Sessions older than 90 days.")
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        db.rollback()
    finally:
        db.close()


def escalation_cron_job():
    """Checks for unacknowledged hot leads and escalates to managers at 10m and Directors at 30m."""
    from models import NotificationLog, Agent
    from database import SessionLocal
    from datetime import datetime, timezone, timedelta
    from config import settings, tenant_id_ctx
    from notification_service import resolve_escalation_recipient
    import logging
    from app.execution_engine.outbound import send_whatsapp_blocking

    logger = logging.getLogger("escalation_engine")
    with SessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)

            # --- 10-MINUTE ESCALATION ---
            expired_10m = db.query(NotificationLog).filter(
                NotificationLog.status == "pending_ack",
                NotificationLog.escalate_at <= now
            ).all()

            for log in expired_10m:
                tenant_id_ctx.set(f"Client_{log.client_id}")
                logger.warning(f"⚠️ 10M ESCALATION TRIGGERED: Lead {log.lead_id} ignored by {log.assigned_agent}.")

                manager = db.query(Agent).filter(Agent.client_id == log.client_id, Agent.is_manager == True).first()
                if manager and manager.phone:
                    try:
                        msg = f"🚨 *10-Min Escalation:* Lead #{log.lead_id} was ignored by {log.assigned_agent}. Please review immediately."
                        send_whatsapp_blocking(
                            to=manager.phone,
                            body=msg,
                            tenant_id=f"Client_{log.client_id}",
                            entity_id=f"lead:{log.lead_id}",
                            source="escalation_10m",
                        )
                    except Exception as e:
                        logger.error(f"10m escalation Twilio failed: {e}")

                log.status = "escalated_10m"
                log.escalate_at = now + timedelta(minutes=20)  # Schedule next check 20 mins from now (30 mins total)

            # --- 30-MINUTE ESCALATION ---
            expired_30m = db.query(NotificationLog).filter(
                NotificationLog.status == "escalated_10m",
                NotificationLog.escalate_at <= now
            ).all()

            for log in expired_30m:
                tenant_id_ctx.set(f"Client_{log.client_id}")
                logger.error(
                    f"🚨 30M CRITICAL ESCALATION TRIGGERED: Lead {log.lead_id} still unacknowledged! Alerting Director.")

                director = resolve_escalation_recipient(db, log.client_id, "30m")
                if director and director.phone:
                    try:
                        msg = f"🚨 *URGENT ESCALATION (30 Min)*\nLead #{log.lead_id} requires immediate Director intervention."
                        send_whatsapp_blocking(
                            to=director.phone,
                            body=msg,
                            tenant_id=f"Client_{log.client_id}",
                            entity_id=f"lead:{log.lead_id}",
                            source="escalation_30m",
                        )
                    except Exception as e:
                        logger.error(f"30m escalation Twilio failed: {e}")

                log.status = "escalated_30m"

            # --- NOTIFICATION DELIVERY FAILURE HANDLER (P0.6: alert once) ---
            failed_notifs = db.query(NotificationLog).filter(
                NotificationLog.status == "failed",
                NotificationLog.sent_at <= now - timedelta(minutes=5)
            ).all()
            from notification_service import terminal_status_after_failed_delivery_alert

            for log in failed_notifs:
                tenant_id_ctx.set(f"Client_{log.client_id}")
                logger.error(f"⚠️ NOTIFICATION DELIVERY FAILED: Lead {log.lead_id}, agent {log.assigned_agent}")
                send_critical_alert("Notification Delivery Failure",
                    f"Lead {log.lead_id} failed to deliver to {log.assigned_agent}.")
                log.status = terminal_status_after_failed_delivery_alert(log.status)

            db.commit()
        except Exception as e:
            logger.error(f"Escalation job failed: {e}")

scheduler = BackgroundScheduler()


def dispatch_followups() -> None:
    """Phase 4.2 — follow-up engine selector (legacy | v3 | shadow).

    - legacy: original ``follow_up.check_and_send_followups`` (default).
    - v3:     ``app.workflows.followup_scheduler`` (AE->EE pipeline).
    - shadow: v3 in dry-run (logs + persists audit message, does NOT send).
    """
    engine = settings.FOLLOWUP_ENGINE
    if engine == "v3":
        from app.workflows.followup_scheduler import check_and_send_followups_v3

        check_and_send_followups_v3()
    elif engine == "shadow":
        from app.workflows.followup_scheduler import check_and_send_followups_v3

        # Shadow dry-run: build the payloads but skip the actual AE send.
        with _ShadowsFollowups():
            check_and_send_followups_v3()
    else:
        check_and_send_followups()


class _ShadowsFollowups:
    """Context manager that forces TEST_MODE so v3 logs instead of sending."""

    def __enter__(self):
        self._prev = settings.TEST_MODE
        settings.TEST_MODE = True
        return self

    def __exit__(self, *a):
        settings.TEST_MODE = self._prev
        return False


scheduler.add_job(dispatch_followups, "interval", minutes=1, id="follow_up_checker")
scheduler.add_job(backup_postgres, "cron", hour=2, minute=0, id="nightly_backup")
scheduler.add_job(daily_cleanup_job, "cron", hour=3, minute=0, id="nightly_cleanup")
scheduler.add_job(escalation_cron_job, "interval", minutes=1, id="escalation_checker")
scheduler.add_job(crm_resync_job, "interval", minutes=5, id="crm_resync")
# Phase 8.4: competitor keyword monitor (nightly; no-op when COMPETITOR_KEYWORDS empty).
from app.workflows.competitor_monitor import competitor_monitor_job
scheduler.add_job(competitor_monitor_job, "cron", hour=1, minute=0, id="competitor_monitor")

# Wave A.1: weekly marketing cron (publishes cron.weekly_report per client).
from app.workflows.weekly_marketing_cron import weekly_marketing_cron_job
scheduler.add_job(weekly_marketing_cron_job, "cron", day_of_week="mon", hour=8, minute=0, id="weekly_marketing_report")

# Wave A.4: expire stale approvals every 15 minutes.
from app.automation_engine.engine import expire_stale_approvals
scheduler.add_job(expire_stale_approvals, "interval", minutes=15, id="expire_approvals", args=[24])

@asynccontextmanager
async def lifespan(app):
    """Start the follow-up scheduler and the IREIOS 3.0 event bus when the server boots, stop them on shutdown.

    Order: event bus starts before the scheduler (so bus-backed jobs can
    publish); on shutdown the scheduler stops first, then the bus.
    """
    from app.clients.event_bus_client import event_bus
    from app.execution_engine.registry import register_executors
    from app.orchestrator.ceo_orchestrator import ceo

    await event_bus.start()
    # n8n bridge: separate Streams group → POST webhooks (Gmail/ops). Never joins CEO group.
    from app.automation_engine.n8n_bridge import n8n_bridge

    try:
        await n8n_bridge.start()
    except Exception as e:  # noqa: BLE001 - never block boot
        logger.warning("n8n bridge start skipped: %s", e)
    register_executors()  # wire real executors (Phase 3) into the EE singleton
    ceo.bootstrap()  # subscribes CEO as the single wildcard bus handler (no agents yet ok)
    # Phase 4.3: arm FollowUpState when a lead is created/updated on the bus.
    from app.workflows.followup_arm import on_lead_created

    ceo.register_agent("followup_arm", on_lead_created, ["lead.created", "conversation.updated"], status="active")

    # --- Full-parity active agents/workflows (Workstream B/C) ---
    from app.agents.lead_scoring_handler import register_lead_scoring
    from app.workflows.crm_automation import register_crm_automation
    from app.agents.marketing_agent import register_marketing_agent
    from app.agents.customer_success_agent import register_customer_success
    from app.knowledge_graph.event_writers import register_graph_writers

    register_lead_scoring(ceo)      # conversation.updated -> lead.scored
    register_crm_automation(ceo)    # lead.* -> assign + CRM sync -> lead.assigned
    register_marketing_agent(ceo)   # cron.weekly_report -> marketing.report.generated
    register_customer_success(ceo)  # booking/payment/renewal -> reminders
    register_graph_writers(ceo)     # core events -> Neo4j async writers

    # Wave B.1: Sales AI on the CEO bus — reacts to scored/hot leads.
    from app.agents.sales_agent import register_sales_agent
    register_sales_agent(ceo)

    # Wave C: Promote 6 placeholders to real agents.
    from app.agents.negotiation_agent import register_negotiation
    from app.agents.pricing_agent import register_pricing
    from app.agents.inventory_agent import register_inventory
    from app.agents.onboarding_agent import register_onboarding
    from app.agents.finance_agent import register_finance
    from app.agents.legal_agent import register_legal
    register_negotiation(ceo)
    register_pricing(ceo)
    register_inventory(ceo)
    register_onboarding(ceo)
    register_finance(ceo)
    register_legal(ceo)

    # Phase 7.2: apply Neo4j schema (idempotent no-op when Neo4j unconfigured).
    from app.knowledge_graph.neo4j_client import neo4j_client
    try:
        neo4j_client.migrate_schema()
    except Exception as e:  # noqa: BLE001 - never block boot
        logger.warning("Neo4j schema migrate skipped: %s", e)

    # Phase 10.1: register Layer-2 placeholder agents (visible, skipped by CEO).
    from app.agents.placeholders import register_placeholders
    register_placeholders(ceo)
    scheduler.start()
    logger.info("Background scheduler started (follow-ups, backups, cleanup)")
    try:
        yield
    finally:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
        try:
            from app.automation_engine.n8n_bridge import n8n_bridge as _n8n_bridge

            await _n8n_bridge.stop()
        except Exception as e:  # noqa: BLE001
            logger.warning("n8n bridge stop: %s", e)
        await event_bus.stop()

app = FastAPI(
    title="Real Estate AI Lead Agent",
    description="Advanced client-grade AI assistant backend for real estate tracking, dynamic questioning, and intelligent lead evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(events_router)

# Wave A.2: Lifecycle event producers (admin-gated).
from app.api.lifecycle import router as lifecycle_router
app.include_router(lifecycle_router)

# Phase 7.3: Graph API routes (tenant-scoped; graceful no-op when Neo4j down).
from app.knowledge_graph.graph_api import router as graph_router
app.include_router(graph_router)

# Wave D.1: Prediction / forecast routes (JWT, client-scoped, heuristic MVP).
from app.api.predictions import router as predictions_router
app.include_router(predictions_router)

# IREIOS 4.0: inventory twin layout (JWT, client-scoped, read-only).
from app.api.inventory import router as inventory_router
app.include_router(inventory_router)

# Automations closeout BA-5: calendar availability + AE-backed confirm for n8n.
from app.api.calendar import router as calendar_router
app.include_router(calendar_router)

# TLS Enforcement (Redirect HTTP to HTTPS)
if settings.IS_PRODUCTION or os.getenv("RENDER"):
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS configuration to allow local Dashboard frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", "https://real-estate-ai-lead-agent-5q20tzn22.vercel.app")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total HTTP Requests", 
    ["method", "endpoint", "http_status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", 
    "HTTP Request Latency", 
    ["method", "endpoint"]
)

# --- Production Monitoring Middleware ---
@app.middleware("http")
async def production_monitoring_middleware(request: Request, call_next):
    request_id_ctx.set(str(uuid.uuid4())[:8])
    tenant_id_ctx.set("Pending")
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time_s = time.time() - start_time
        
        # Prometheus recording
        REQUEST_COUNT.labels(
            method=request.method, 
            endpoint=request.url.path, 
            http_status=response.status_code
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method, 
            endpoint=request.url.path
        ).observe(process_time_s)

        # Log clean structured JSON for observability
        process_time_ms = round(process_time_s * 1000)
        log_data = {
            "event": "request_completed",
            "method": request.method,
            "url": str(request.url.path),
            "status": response.status_code,
            "latency_ms": process_time_ms,
            "client_ip": request.client.host if request.client else "unknown"
        }
        logger.info(json.dumps(log_data))
        return response
    except Exception as e:
        process_time_s = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method=request.method, 
            endpoint=request.url.path, 
            http_status=500
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method, 
            endpoint=request.url.path
        ).observe(process_time_s)

        process_time_ms = round(process_time_s * 1000)
        log_data = {
            "event": "request_failed",
            "method": request.method,
            "url": str(request.url.path),
            "error": str(type(e).__name__),
            "latency_ms": process_time_ms
        }
        logger.error(json.dumps(log_data))
        raise

@app.get("/metrics")
def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# --- Security Dependency ---

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: DBSession = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.email == form_data.username).first()
    if not client or not auth.verify_password(form_data.password, client.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(client.id)}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}



@app.post("/api/v1/chat")
async def chat_endpoint(session_id: str, message: str, current_client: models.Client = Depends(auth.get_client_by_api_key), db: DBSession = Depends(get_db)):
    client_id = current_client.id
    """
    Public AI chat interface.
    Receives user utterance and a session ID to keep multi-turn context.
    Orchestrates Gemini response generation and silent lead data capture.
    """
    # --- FIX: Apply tenant prefix ---
    prefix = f"{client_id}_"
    scoped_session_id = session_id if session_id.startswith(prefix) else f"{prefix}{session_id}"
    try:
        lead_before = db.query(models.Lead).filter(models.Lead.session_id == scoped_session_id).first()
        is_new_lead = lead_before is None
        reply = await _select_chat_fn()(scoped_session_id, message, db, client_id=client_id)
        lead = db.query(models.Lead).filter(models.Lead.session_id == scoped_session_id).first()
        await _emit_turn_events(
            client_id=client_id,
            scoped_session_id=scoped_session_id,
            lead=lead,
            source_channel="chat",
            is_new_lead=is_new_lead,
            message=message,
            db=db,
        )
        media_url = None
        try:
            from app.agents.whatsapp_agent import take_outbound_media_url

            media_url = take_outbound_media_url(session_id=scoped_session_id)
        except Exception:
            pass
        out = {
            "status": "success",
            "session_id": session_id,
            "client_id": client_id,
            "reply": reply,
        }
        if media_url:
            out["media_url"] = media_url
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _wa_support_number() -> str:
    return (getattr(settings, "CLIENT_SUPPORT_NUMBER", None) or "+91 9876543210").strip()


def _wa_fallback_body() -> str:
    return (
        "I'm experiencing a brief connectivity issue. Please try again in a moment, "
        f"or reach our team directly at {_wa_support_number()}."
    )


async def _session_turn_locked(session_id: str, body: str, client_id: int) -> str:
    """Run one WhatsApp turn under the session lock with a private DB session.

    Lock lives for the *full* turn (including after the webhook race window) so a
    concurrent message cannot interleave while Gemini is still finishing.
    Own SessionLocal avoids request-scoped session close when the webhook returns
    interim TwiML and the task continues.

    ``session_id`` should already be tenant-scoped (``{client_id}_{phone}``).
    """
    prefix = f"{client_id}_"
    scoped_session_id = session_id if session_id.startswith(prefix) else f"{prefix}{session_id}"
    lock = redis_client.lock(f"session_lock:{scoped_session_id}", timeout=45.0, blocking_timeout=30.0)
    acquired = await lock.acquire()
    if not acquired:
        logger.warning(
            "SESSION_TURN_LOCK | session=%s | could not acquire lock; skipping",
            scoped_session_id,
        )
        raise RuntimeError("session_lock_unavailable")
    try:
        with SessionLocal() as db:
            payload = LeadIngestionPayload(
                session_id=scoped_session_id,
                source="whatsapp",
                message=body,
                whatsapp_opt_in=True,
            )
            # Single in-flight turn — never cancel/re-run, so is_background=False.
            return await process_unified_lead(payload, db, client_id, background=False)
    finally:
        await lock.release()


async def _await_inflight_and_push(
    task: asyncio.Task,
    session_id: str,
    client_id: int,
    to_phone: Optional[str] = None,
):
    """After webhook race timeout: await the *same* turn task and push via EE.

    Does not start a second process_unified_lead (avoids double Gemini / double writes).
    ``to_phone`` is the raw WhatsApp number for Twilio; ``session_id`` is scoped for media.
    """
    prefix = f"{client_id}_"
    scoped_session_id = session_id if session_id.startswith(prefix) else f"{prefix}{session_id}"
    phone = (to_phone or "").strip()
    if not phone:
        phone = scoped_session_id[len(prefix):] if scoped_session_id.startswith(prefix) else scoped_session_id
    try:
        reply_text = await task
        media_url = None
        try:
            from app.agents.whatsapp_agent import take_outbound_media_url

            media_url = take_outbound_media_url(session_id=scoped_session_id)
        except Exception:  # noqa: BLE001
            media_url = None
        result = await _send_whatsapp_via_ee(
            client_id,
            phone,
            reply_text or _wa_fallback_body(),
            scoped_session_id,
            source="inflight_push",
            media_url=media_url,
        )
        if result.get("status") == "error":
            raise RuntimeError(result.get("error") or "ee_send_failed")
        logger.info("INFLIGHT_PUSH | session=%s | status=delivered", scoped_session_id)
    except Exception as e:
        logger.error("INFLIGHT_PUSH failed for %s: %s", scoped_session_id, e)
        try:
            result = await _send_whatsapp_via_ee(
                client_id,
                phone,
                _wa_fallback_body(),
                scoped_session_id,
                source="inflight_fallback",
            )
            if result.get("status") == "error":
                raise RuntimeError(result.get("error") or "ee_fallback_failed")
            logger.warning(
                "FALLBACK | session=%s | reason=inflight_task_failure | detail=graceful_fallback_via_ee",
                scoped_session_id,
            )
        except Exception as fallback_err:
            logger.error("FALLBACK push also failed for %s: %s", scoped_session_id, fallback_err)
            BACKGROUND_FAILURE_COUNT.labels(component="twilio").inc()
            INTEGRATION_FAILURES.labels(integration="twilio").inc()
            with SessionLocal() as db:
                db.add(
                    models.DLQEvent(
                        target_endpoint="twilio_outbound",
                        payload={
                            "session_id": scoped_session_id,
                            "body": _wa_fallback_body(),
                            "to": f"whatsapp:{phone}",
                        },
                        error_trace=str(fallback_err),
                        status="pending",
                        client_id=client_id,
                    )
                )
                db.commit()


async def background_process_and_push(session_id: str, Body: str, client_id: int):
    """Legacy full re-run path (kept for SMS / callers that need a fresh turn).

    WhatsApp webhook preferred path is _session_turn_locked + _await_inflight_and_push
    (no cancel, no second Gemini call). This helper still re-acquires the session lock
    and uses background=True for P3.3 duplicate-message guard when a full re-run is required.
    """
    prefix = f"{client_id}_"
    scoped_session_id = session_id if session_id.startswith(prefix) else f"{prefix}{session_id}"
    phone = scoped_session_id[len(prefix):] if scoped_session_id.startswith(prefix) else scoped_session_id
    lock = redis_client.lock(f"session_lock:{scoped_session_id}", timeout=45.0, blocking_timeout=10.0)
    lock_acquired = False
    try:
        lock_acquired = await lock.acquire()
        if not lock_acquired:
            logger.warning(
                "BACKGROUND_LOCK | session=%s | another worker holds the lock; skipping duplicate background run",
                scoped_session_id,
            )
            return

        with SessionLocal() as db:
            try:
                payload = LeadIngestionPayload(
                    session_id=scoped_session_id,
                    source="whatsapp",
                    message=Body,
                    whatsapp_opt_in=True,
                )
                reply_text = await process_unified_lead(payload, db, client_id, background=True)
                media_url = None
                try:
                    from app.agents.whatsapp_agent import take_outbound_media_url

                    media_url = take_outbound_media_url(session_id=scoped_session_id)
                except Exception:  # noqa: BLE001
                    pass
                result = await _send_whatsapp_via_ee(
                    client_id,
                    phone,
                    reply_text or _wa_fallback_body(),
                    scoped_session_id,
                    source="background_push",
                    media_url=media_url,
                )
                if result.get("status") == "error":
                    raise RuntimeError(result.get("error") or "ee_send_failed")
                logger.info("Background task pushed response to %s via EE", scoped_session_id)
            except Exception as e:
                logger.error("Background task failed for %s: %s", scoped_session_id, e)
                try:
                    result = await _send_whatsapp_via_ee(
                        client_id,
                        phone,
                        _wa_fallback_body(),
                        scoped_session_id,
                        source="background_fallback",
                    )
                    if result.get("status") == "error":
                        raise RuntimeError(result.get("error") or "ee_fallback_failed")
                    logger.warning(
                        "FALLBACK | session=%s | reason=background_task_failure | detail=graceful_fallback_via_ee",
                        scoped_session_id,
                    )
                except Exception as fallback_err:
                    logger.error("FALLBACK push also failed for %s: %s", scoped_session_id, fallback_err)
                    BACKGROUND_FAILURE_COUNT.labels(component="twilio").inc()
                    INTEGRATION_FAILURES.labels(integration="twilio").inc()
                    db.add(
                        models.DLQEvent(
                            target_endpoint="twilio_outbound",
                            payload={
                                "session_id": scoped_session_id,
                                "body": _wa_fallback_body(),
                                "to": f"whatsapp:{phone}",
                            },
                            error_trace=str(fallback_err),
                            status="pending",
                            client_id=client_id,
                        )
                    )
                    db.commit()
    finally:
        if lock_acquired:
            await lock.release()


def _stop_followups_for_session(db: DBSession, scoped_session_id: str) -> bool:
    """P3.5 edge case: idempotently stop follow-ups for a session.

    Returns True if a FollowUpState row existed and was stopped.
    Used in both normal (locked) and degraded (Redis-down) paths.
    """
    follow_up_state = db.query(models.FollowUpState).filter(
        models.FollowUpState.session_id == scoped_session_id
    ).first()
    if follow_up_state:
        follow_up_state.follow_up_status = "stopped"
        follow_up_state.last_user_reply_timestamp = func.now()
        db.commit()
        logger.info(f"SMS Webhook: Follow ups stopped for {scoped_session_id}")
    return follow_up_state is not None


class LeadIngestionPayload(BaseModel):
    session_id: str
    source: str
    name: Optional[str] = None
    phone: Optional[str] = None
    message: Optional[str] = None
    intent: Optional[str] = None
    budget: Optional[str] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    whatsapp_opt_in: bool = False


async def _emit_turn_events_deferred(
    *,
    client_id: int,
    scoped_session_id: str,
    lead_id: int,
    source_channel: str,
    is_new_lead: bool,
    message: str = "",
) -> None:
    """Bus publish with a private DB session — safe after the reply path returns."""
    try:
        with SessionLocal() as db:
            lead = (
                db.query(models.Lead)
                .filter(models.Lead.id == lead_id, models.Lead.client_id == client_id)
                .first()
            )
            if not lead:
                return
            await _emit_turn_events(
                client_id=client_id,
                scoped_session_id=scoped_session_id,
                lead=lead,
                source_channel=source_channel,
                is_new_lead=is_new_lead,
                message=message,
                db=db,
            )
    except Exception as e:  # noqa: BLE001
        logger.debug("deferred turn events skipped: %s", e)


async def process_unified_lead(payload: LeadIngestionPayload, db: DBSession, client_id: int, background: bool = False):
    """
    Unified entry point for lead ingestion.
    Refactored to call process_chat for Gemini processing to avoid logic duplication.

    Bus events (_emit_turn_events) run off the reply critical path so WhatsApp TwiML
    is not delayed by Redis Streams / chat_context summarize.
    """
    raw_session_id = payload.session_id
    prefix = f"{client_id}_"
    scoped_session_id = raw_session_id if raw_session_id.startswith(prefix) else f"{prefix}{raw_session_id}"

    # Ensure Session exists BEFORE creating the Lead
    session = db.query(models.Session).filter(models.Session.id == scoped_session_id).first()
    if not session:
        session = models.Session(id=scoped_session_id, client_id=client_id)
        db.add(session)
        db.commit()

    # Pre-sync lead data from payload if provided
    lead = db.query(models.Lead).filter(models.Lead.session_id == scoped_session_id).first()
    is_new_lead = False
    if not lead:
        lead = models.Lead(
            session_id=scoped_session_id,
            client_id=client_id,
            source=payload.source,
            whatsapp_opt_in=payload.whatsapp_opt_in,
            name=payload.name,
            phone=payload.phone,
            budget=payload.budget,
            location=payload.location,
            property_type=payload.property_type,
            intent=payload.intent
        )
        db.add(lead)
        is_new_lead = True
    else:
        if payload.name: lead.name = payload.name
        if payload.phone: lead.phone = payload.phone
        if payload.budget: lead.budget = payload.budget
        if payload.location: lead.location = payload.location
        if payload.property_type: lead.property_type = payload.property_type
        if payload.intent: lead.intent = payload.intent

    db.commit()

    # --- FIX: FIRE THE CRM SYNC SAFELY ---
    if is_new_lead:
        lead.funnel_stage = "New"
        db.add(models.EventLog(
            session_id=scoped_session_id,
            client_id=client_id,
            event_type="tracking",
            action_type="lead_created",
            latency_ms=0
        ))
        db.commit()

        # CRM create is bus-owned: lead.created → crm_automation → AE→EE (BD-1).
        # Field updates still debounced via crm_resync_job.
    # --------------------------------------------------------

    # Now delegate the core logic to the selected chat pipeline
    reply = await _select_chat_fn()(
        scoped_session_id,
        payload.message or "",
        db,
        client_id=client_id,
        is_background=background,
    )
    # Refresh lead after chat extraction so bus payloads carry latest fields.
    db.refresh(lead)
    lead_id = lead.id
    source_channel = payload.source or "api"
    message = payload.message or ""

    # Off critical path: bus publish must not delay TwiML / chat JSON return.
    evt_task = asyncio.create_task(
        _emit_turn_events_deferred(
            client_id=client_id,
            scoped_session_id=scoped_session_id,
            lead_id=lead_id,
            source_channel=source_channel,
            is_new_lead=is_new_lead,
            message=message,
        )
    )
    running_bg_tasks.add(evt_task)
    evt_task.add_done_callback(running_bg_tasks.discard)
    if getattr(settings, "TEST_MODE", False):
        await evt_task

    return reply

@app.post("/api/v1/ingest")
async def ingest_lead(payload: LeadIngestionPayload, current_client: models.Client = Depends(auth.get_client_by_api_key), db: DBSession = Depends(get_db)):
    """Unified API for processing leads from custom website forms or frontends."""
    try:
        result = await process_unified_lead(payload, db, client_id=current_client.id)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/webhook/meta")
async def meta_webhook(payload: dict, current_client: models.Client = Depends(auth.get_client_by_api_key), db: DBSession = Depends(get_db)):
    """Webhook for Facebook and Instagram Lead Ads."""
    try:
        # Example naive parsing. Real implementation would parse Facebook Graph API response.
        parsed = LeadIngestionPayload(
            session_id=payload.get("lead_id", str(time.time())),
            source="facebook",
            name=payload.get("full_name"),
            phone=payload.get("phone_number"),
            whatsapp_opt_in=payload.get("opt_in", False)
        )
        await process_unified_lead(parsed, db, client_id=current_client.id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/webhook/portals")
async def portals_webhook(payload: dict, current_client: models.Client = Depends(auth.get_client_by_api_key), db: DBSession = Depends(get_db)):
    """Webhook for Magicbricks / 99acres."""
    try:
        parsed = LeadIngestionPayload(
            session_id=payload.get("lead_id", str(time.time())),
            source=payload.get("portal", "portal"),
            name=payload.get("name"),
            phone=payload.get("phone"),
            intent=payload.get("intent"),
            location=payload.get("location"),
            whatsapp_opt_in=payload.get("whatsapp_opt_in", False)
        )
        await process_unified_lead(parsed, db, client_id=current_client.id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class AcknowledgeNotificationBody(BaseModel):
    """P1.11: optional agent binding when claiming (avoids freezing null assignee)."""
    agent_name: Optional[str] = None
    agent_id: Optional[int] = None


@app.post("/api/v1/notifications/acknowledge")
def acknowledge_notification(
        lead_id: int,
        body: Optional[AcknowledgeNotificationBody] = None,
        current_client: models.Client = Depends(auth.get_current_client),
        db: DBSession = Depends(get_db),
):
    """Allows human agents to clear the Priority Alert from the dashboard and claim the lead."""
    from models import NotificationLog, Lead, Agent

    body = body or AcknowledgeNotificationBody()

    log = db.query(NotificationLog).filter(
        NotificationLog.lead_id == lead_id,
        NotificationLog.client_id == current_client.id,
        NotificationLog.status.in_(["pending_ack", "escalated_10m", "escalated_30m"])
    ).first()

    if log:
        log.status = "acknowledged"

    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.client_id == current_client.id).first()
    if lead:
        if lead.conversion_status != "claimed":
            lead.conversion_status = "claimed"

        # P1.11: bind assignee on claim when client provides agent identity
        if body.agent_id is not None:
            agent = db.query(Agent).filter(
                Agent.id == body.agent_id,
                Agent.client_id == current_client.id,
            ).first()
            if agent:
                lead.assigned_agent = agent.name
        elif body.agent_name:
            agent = db.query(Agent).filter(
                Agent.client_id == current_client.id,
                Agent.name == body.agent_name,
            ).first()
            if agent:
                lead.assigned_agent = agent.name

    db.commit()
    return {"status": "success", "message": "Lead successfully claimed and alert acknowledged."}

@app.post("/api/v1/whatsapp")
async def whatsapp_webhook(
        request: Request,
        background_tasks: BackgroundTasks,
        MessageSid: str = Form(None),
        From: str = Form(...),
        Body: str = Form(...),
        current_client: models.Client = Depends(auth.get_client_by_api_key),
        db: DBSession = Depends(get_db)
):
    """
    Twilio WhatsApp Webhook.
    Handles duplicate prevention, queueing, timeouts, and signature validation.
    """
    # --- SECURITY: VALIDATE TWILIO SIGNATURE ---
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")

    # Twilio validates against the exact URL it called (enforce https in prod)
    url = str(request.url).replace("http://", "https://") if settings.IS_PRODUCTION else str(request.url)

    # Bypass validation ONLY if we are in local development testing mode
    if not settings.TEST_MODE and not validator.validate(url, form_data, signature):
        logger.warning(f"SECURITY ALERT: Invalid Twilio signature from IP {request.client.host}")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    # -------------------------------------------

    request_start = time.time()
    try:
        raw_from = From.replace("whatsapp:", "")
        client_id = current_client.id
        scoped_session_id = f"{client_id}_{raw_from}"
        session_id = scoped_session_id  # for except logging

        # Dedup key: Twilio MessageSid, or synthetic hash when SID missing (prod safety).
        dedupe_sid = MessageSid
        if not dedupe_sid:
            import hashlib

            window = int(time.time()) // 60
            dedupe_sid = "nosid_" + hashlib.sha256(
                f"{client_id}:{raw_from}:{Body}:{window}".encode()
            ).hexdigest()[:28]
            if settings.IS_PRODUCTION:
                logger.warning(
                    "WA webhook missing MessageSid; using synthetic dedupe key session=%s",
                    scoped_session_id,
                )

        # Task 1: Duplicate Message Protection (P3.4: insert-first with IntegrityError)
        try:
            db.add(models.WebhookLog(message_sid=dedupe_sid))
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info(f"Duplicate message ignored (race): {dedupe_sid}")
            return Response(content="<Response></Response>", media_type="application/xml")

        # Race window under Twilio ~15s HTTP limit. Turn runs in a task that owns
        # its own SessionLocal + session_lock for the full duration (not cancelled).
        webhook_timeout = float(getattr(settings, "WHATSAPP_WEBHOOK_TIMEOUT", 12.0))
        chat_task = asyncio.create_task(_session_turn_locked(scoped_session_id, Body, client_id))
        done, _pending = await asyncio.wait({chat_task}, timeout=webhook_timeout)

        if chat_task in done:
            reply_text = chat_task.result()  # re-raises turn errors → outer except
            latency_ms = round((time.time() - request_start) * 1000)
            logger.info(
                "LATENCY | session=%s | %sms | status=delivered | window=%ss",
                scoped_session_id,
                latency_ms,
                webhook_timeout,
            )
            twiml = MessagingResponse()
            msg = twiml.message(reply_text or "")
            try:
                from app.agents.whatsapp_agent import take_outbound_media_url

                media_url = take_outbound_media_url(session_id=scoped_session_id)
                if media_url:
                    msg.media(media_url)
            except Exception as e:  # pragma: no cover
                logger.debug("outbound media attach skipped: %s", e)
            return Response(content=str(twiml), media_type="application/xml")

        # Slow path: do NOT cancel chat_task — await same turn and EE-push.
        timeout_ms = int(webhook_timeout * 1000)
        logger.info(
            "TIMEOUT | session=%s | exceeded=%sms | action=await_inflight_push",
            scoped_session_id,
            timeout_ms,
        )
        background_tasks.add_task(
            _await_inflight_and_push, chat_task, scoped_session_id, client_id, raw_from
        )

        # P3.1: Only send one interim "Just checking..." per MessageSid (atomic SET NX)
        interim_key = f"interim_sent:{dedupe_sid}"
        send_interim = True
        try:
            was_set = await redis_client.set(interim_key, "1", ex=120, nx=True)
            send_interim = bool(was_set)
        except Exception as redis_err:  # noqa: BLE001
            logger.debug("interim dedupe redis failed: %s", redis_err)

        twiml = MessagingResponse()
        if send_interim:
            twiml.message("Just checking that for you...")
        return Response(content=str(twiml), media_type="application/xml")
    
    except Exception as e:
        logger.warning(f"FALLBACK | session={session_id if 'session_id' in locals() else 'unknown'} | reason={type(e).__name__} | detail={str(e)[:120]}")
        twiml = MessagingResponse()
        twiml.message(
            f"I'm experiencing a brief connectivity issue. Let me connect you with our expert at {_wa_support_number()}."
        )
        return Response(content=str(twiml), media_type="application/xml")


@app.post("/api/v1/webhook/twilio-status")
async def twilio_status_webhook(
        request: Request,
        MessageSid: str = Form(None),
        MessageStatus: str = Form(None),
        db: DBSession = Depends(get_db)
):
    """
    Twilio Status Callback Endpoint.
    Tracks exact delivery status (sent, delivered, read, failed).
    Safely ignores unexpected payloads via Form(None).
    """
    if MessageSid and MessageStatus:
        logger.info(f"Twilio Delivery Tracking | SID: {MessageSid} | Status: {MessageStatus.upper()}")
        log = db.query(models.NotificationLog).filter(models.NotificationLog.twilio_message_sid == MessageSid).first()

        if log and log.status in ["pending_ack", "sent", "delivered", "failed"]:
            log.twilio_delivery_status = MessageStatus

            # If Twilio physically failed to deliver, mark it failed to halt escalation
            if MessageStatus.lower() == "failed":
                log.status = "failed"
            db.commit()

    # Twilio requires an empty TwiML response to acknowledge receipt
    return Response(content="<Response></Response>", media_type="application/xml")

@app.post("/api/v1/incoming_sms")
async def incoming_sms_webhook(
    background_tasks: BackgroundTasks,
    MessageSid: str = Form(None),
    From: str = Form(...),
    Body: str = Form(...),
    current_client: models.Client = Depends(auth.get_client_by_api_key),
    db: DBSession = Depends(get_db)
):
    """
    Twilio SMS Webhook.
    Handles stopping the FollowUpState for standard SMS replies.
    """
    request_start = time.time()
    try:
        # Task 1: Duplicate Message Protection (P3.4: insert-first with IntegrityError)
        if MessageSid:
            try:
                db.add(models.WebhookLog(message_sid=MessageSid))
                db.commit()
            except IntegrityError:
                db.rollback()
                logger.info(f"Duplicate SMS message ignored (race): {MessageSid}")
                return Response(content="<Response></Response>", media_type="application/xml")

        # P3.5: Use client-scoped session id for FollowUpState lookup and lock
        raw_from = From
        scoped_session_id = f"{current_client.id}_{raw_from}"

        # Process as normal Lead Interaction (lock serializes per-session)
        try:
            async with redis_client.lock(f"session_lock:{scoped_session_id}", timeout=20.0, blocking_timeout=30.0):
                # P3.5 edge case: stop FollowUps INSIDE the lock for atomicity
                _stop_followups_for_session(db, scoped_session_id)
                payload = LeadIngestionPayload(
                    session_id=scoped_session_id,
                    source="sms",
                    message=Body,
                    whatsapp_opt_in=False
                )
                reply_text = await process_unified_lead(payload, db, client_id=current_client.id)
        except Exception as redis_err:
            logger.warning(f"Redis unavailable or lock failed, proceeding without lock: {redis_err}")
            # Degraded path: best-effort stop (no lock available)
            _stop_followups_for_session(db, scoped_session_id)
            payload = LeadIngestionPayload(
                session_id=scoped_session_id,
                source="sms",
                message=Body,
                whatsapp_opt_in=False
            )
            reply_text = await process_unified_lead(payload, db, client_id=current_client.id)
            
        twiml = MessagingResponse()
        twiml.message(reply_text)
        return Response(content=str(twiml), media_type="application/xml")
            
    except Exception as e:
        logger.error(f"Error in SMS webhook: {e}")
        twiml = MessagingResponse()
        return Response(content=str(twiml), media_type="application/xml")

# =====================================================================
# REVENUE PHASE: ROI & Funnel Dashboards
# =====================================================================

# =====================================================================
# REVENUE PHASE: ROI & Funnel Dashboards
# =====================================================================

@app.get("/api/v1/reports/pipeline")
async def get_pipeline_report(current_client: models.Client = Depends(auth.get_current_client),
                              db: DBSession = Depends(get_db)):
    """Aggregates funnel_stage data to calculate conversion and qualified rates."""
    from models import Lead

    total_leads = db.query(Lead).filter(Lead.client_id == current_client.id).count()
    stages = db.query(Lead.funnel_stage, func.count(Lead.id)).filter(Lead.client_id == current_client.id).group_by(
        Lead.funnel_stage).all()
    stage_counts = {stage: count for stage, count in stages}

    new_leads = stage_counts.get("New", 0)
    contacted = stage_counts.get("Contacted", 0)
    scheduled = stage_counts.get("Appointment Scheduled", 0)
    closed = stage_counts.get("Closed Won", 0)
    lost = stage_counts.get("Lost", 0)
    qualified = contacted + scheduled + closed

    return {
        "pipeline": {
            "total_leads": total_leads, "new": new_leads, "contacted": contacted,
            "appointment_scheduled": scheduled, "closed_won": closed, "lost": lost
        },
        "rates": {
            "qualified_rate": round((qualified / total_leads * 100), 2) if total_leads else 0,
            "conversion_rate": round((closed / total_leads * 100), 2) if total_leads else 0
        }
    }


@app.get("/api/v1/roi/funnel_metrics")
async def get_funnel_metrics(current_client: models.Client = Depends(auth.get_current_client),
                             db: DBSession = Depends(get_db)):
    """Total Leads, Qualified, Appt Booked, Site Visits, Deal Closed"""
    from models import EventLog, Lead

    total_leads = db.query(Lead).filter(Lead.client_id == current_client.id).count()
    qualified = db.query(Lead).filter(Lead.client_id == current_client.id,
                                      ((Lead.budget.isnot(None)) | (Lead.intent.isnot(None)))).count()
    appointments = db.query(Lead).filter(Lead.client_id == current_client.id, Lead.visit_date.isnot(None)).count()
    site_visits = db.query(EventLog).filter(EventLog.client_id == current_client.id,
                                            EventLog.action_type == "site_visit_done").count()
    deal_closed = db.query(EventLog).filter(EventLog.client_id == current_client.id,
                                            EventLog.action_type == "deal_closed").count()

    return {
        "funnel": {
            "total_leads": total_leads, "qualified": qualified, "appointment_booked": appointments,
            "site_visit_done": site_visits, "deal_closed": deal_closed
        },
        "conversion_rates": {
            "lead_to_qualified": round((qualified / total_leads * 100), 2) if total_leads else 0,
            "qualified_to_appt": round((appointments / qualified * 100), 2) if qualified else 0
        },
        "financials": {"revenue_generated": 0}
    }


@app.get("/api/v1/roi/speed_intelligence")
async def get_speed_intelligence(current_client: models.Client = Depends(auth.get_current_client),
                                 db: DBSession = Depends(get_db)):
    from models import EventLog
    # Filter by client_id to prevent cross-tenant data leakage
    avg_ai = db.query(func.avg(EventLog.latency_ms)).filter(
        EventLog.client_id == current_client.id,
        EventLog.agent_type == 'AI',
        EventLog.latency_ms.isnot(None)
    ).scalar() or 0

    avg_human = db.query(func.avg(EventLog.latency_ms)).filter(
        EventLog.client_id == current_client.id,
        EventLog.agent_type == 'Human',
        EventLog.latency_ms.isnot(None)
    ).scalar() or 0

    return {
        "average_latency_ms": {
            "AI": round(avg_ai, 2),
            "Human": round(avg_human, 2)
        }
    }


@app.get("/api/v1/roi/source_attribution")
async def get_source_attribution(current_client: models.Client = Depends(auth.get_current_client),
                                 db: DBSession = Depends(get_db)):
    from models import Lead
    # Filter by client_id
    sources = db.query(Lead.source, func.count(Lead.id)).filter(
        Lead.client_id == current_client.id
    ).group_by(Lead.source).all()

    appointments = db.query(Lead.source, func.count(Lead.id)).filter(
        Lead.client_id == current_client.id,
        Lead.visit_date.isnot(None)
    ).group_by(Lead.source).all()

    appt_dict = {k: v for k, v in appointments}

    results = []
    for source, count in sources:
        appt_count = appt_dict.get(source, 0)
        results.append({
            "source": source,
            "total_leads": count,
            "appointments_booked": appt_count,
            "conversion_rate": round((appt_count / count * 100), 2) if count else 0
        })

    return {"sources": results}

@app.get("/api/v1/analytics")
def get_analytics(current_client: models.Client = Depends(auth.get_current_client), db: DBSession = Depends(get_db)):
    client_id = current_client.id
    """
    Client-secured analytics dashboard tracking total leads, AI conversion rating, and user intents.
    """
    total_sessions = db.query(models.Session).filter(models.Session.client_id == client_id).count()
    total_leads_captured = db.query(models.Lead).join(models.Session).filter(models.Session.client_id == client_id).count()
    
    # Calculate conversion rate robustly
    conversion_rate = 0.0
    if total_sessions > 0:
        conversion_rate = round((total_leads_captured / total_sessions) * 100, 2)
        
    # Group leads by their intent to provide an intent breakdown
    intent_counts = db.query(
        models.Lead.intent, func.count(models.Lead.id)
    ).join(models.Session).filter(models.Session.client_id == client_id).group_by(models.Lead.intent).all()
    
    # Convert grouped data into a clean JSON dictionary
    intent_breakdown = { 
        (intent if intent else "unknown"): count 
        for intent, count in intent_counts 
    }

    return {
        "status": "success",
        "client_id": client_id,
        "data": {
            "total_sessions": total_sessions,
            "total_leads_captured": total_leads_captured,
            "conversion_rate": conversion_rate,
            "intent_breakdown": intent_breakdown
        }
    }


class SettingsUpdate(BaseModel):
    settings: dict


@app.get("/api/v1/settings")
def get_settings(current_client: models.Client = Depends(auth.get_current_client)):
    """Retrieve user settings for frontend sync."""
    return {"status": "success", "settings": current_client.settings or {}}


@app.patch("/api/v1/settings")
def update_settings(
        payload: SettingsUpdate,
        current_client: models.Client = Depends(auth.get_current_client),
        db: DBSession = Depends(get_db)
):
    """Save user preferences across devices."""
    current_client.settings = payload.settings
    db.commit()
    return {"status": "success", "settings": current_client.settings}


class ContactForm(BaseModel):
    name: str
    email: str
    message: str


@app.post("/api/v1/contact")
async def submit_contact_form(form: ContactForm):
    """
    Accepts contact form submissions.
    Logs the output for now. Can be directly wired to Resend/SendGrid later.
    """
    logger.info(f"CONTACT FORM SUBMISSION | Name: {form.name} | Email: {form.email} | Message: {form.message}")
    return {"status": "success", "message": "Contact form delivered successfully."}


@app.post("/api/v1/webhook/stripe")
async def stripe_webhook(request: Request, db: DBSession = Depends(get_db)):
    """Listens for Stripe checkout events and activates subscriptions."""
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        # Cryptographically verify the payload actually came from Stripe
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        logger.error(f"Stripe signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        customer_email = data.get("customer_details", {}).get("email")
        if customer_email:
            client = db.query(models.Client).filter(models.Client.email == customer_email).first()
            if client:
                client.subscription_status = "active"
                client.stripe_customer_id = data.get("customer")
                db.commit()
                logger.info(f"STRIPE WEBHOOK | Activated subscription for {customer_email}")

    return {"status": "success"}

# --- AGENT MANAGEMENT ROUTES FOR FRONTEND ---
class AgentCreate(BaseModel):
    name: str
    phone: str
    email: str
    is_manager: bool = False
    is_director: bool = False
    locations: Optional[str] = None
    speciality: Optional[str] = None
    deal_size: Optional[str] = None
    lead_type: Optional[str] = None

@app.get("/api/v1/agents")
def get_agents(current_client: models.Client = Depends(auth.get_current_client), db: DBSession = Depends(get_db)):
    """Returns all human agents belonging to the authenticated client."""
    agents = db.query(models.Agent).filter(models.Agent.client_id == current_client.id).all()
    return {"status": "success", "agents": agents}

@app.post("/api/v1/agents")
def create_agent(agent: AgentCreate, current_client: models.Client = Depends(auth.get_current_client), db: DBSession = Depends(get_db)):
    """Creates a new human agent for the authenticated client's workspace."""
    new_agent = models.Agent(
        client_id=current_client.id,
        **agent.model_dump()
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return {"status": "success", "agent": new_agent}

# --- IREIOS 3.0 PHASE 2: HITL approve / reject API ---
class ApprovalResolveBody(BaseModel):
    decision: str  # "approve" | "reject"
    reason: Optional[str] = None


@app.get("/api/v1/approvals")
def list_approvals(
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """List pending approval requests for the authenticated tenant (managers)."""
    from app.automation_engine.hitl import get_pending

    return {"status": "success", "approvals": get_pending(current_client.id, db)}


@app.post("/api/v1/approvals/{approval_id}/approve")
async def approve_approval(
    approval_id: int,
    body: Optional[ApprovalResolveBody] = None,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """Approve a pending action and resume it through the Automation Engine."""
    from app.automation_engine.engine import resume

    manager_id = str(current_client.id)
    reason = body.reason if body else None
    try:
        result = await resume(
            approval_id,
            manager_id=manager_id,
            reason=reason,
            client_id=current_client.id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "result": result}


@app.post("/api/v1/approvals/{approval_id}/reject")
async def reject_approval(
    approval_id: int,
    body: Optional[ApprovalResolveBody] = None,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """Reject a pending action (drops it; notifies the requesting agent)."""
    from app.automation_engine.engine import reject

    manager_id = str(current_client.id)
    reason = body.reason if body else None
    try:
        result = await reject(
            approval_id,
            manager_id=manager_id,
            reason=reason,
            client_id=current_client.id,
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Approval not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"status": "success", "result": result}


@app.get("/api/v1/leads")
def get_leads(
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
    intent: Optional[str] = None,
    location: Optional[str] = None,
    score: Optional[str] = None,
    source: Optional[str] = None,
    assigned_agent: Optional[str] = None
):
    """
    Client-secured lead extraction endpoint filtering by depth, intent, location, and score.
    Supports optional query parameters like ?intent=buy&score=High
    """
    query = db.query(models.Lead).filter(models.Lead.client_id == current_client.id)
    
    # Case-insensitive filtering dynamically based on provided query parameters
    if intent:
        query = query.filter(models.Lead.intent.ilike(f"%{intent}%"))
    if location:
        query = query.filter(models.Lead.location.ilike(f"%{location}%"))
    if score:
        query = query.filter(models.Lead.score.ilike(f"%{score}%"))
    if source:
        query = query.filter(models.Lead.source.ilike(f"%{source}%"))
    if assigned_agent:
        query = query.filter(models.Lead.assigned_agent.ilike(f"%{assigned_agent}%"))
        
    leads = query.all()

    return {
        "status": "success",
        "total_returned": len(leads),
        "leads": [serialize_lead(lead) for lead in leads]
    }


def serialize_lead(lead) -> dict:
    """
    P6.5: ORM row -> JSON-safe dict. Title-cases `lead_temperature` so the
    dashboard (which compares against 'Hot'/'Warm'/'Cold') matches the backend's
    lowercase storage ('hot'/'warm'/'cold').
    """
    data = {c.name: getattr(lead, c.name) for c in lead.__table__.columns}
    temp = data.get("lead_temperature")
    if isinstance(temp, str) and temp:
        data["lead_temperature"] = temp[:1].upper() + temp[1:]
    return data

class LeadStageUpdate(BaseModel):
    stage: str

    # P2.4: validate against canonical enum — reject "Human Handoff", "Qualified", etc.
    @field_validator("stage")
    @classmethod
    def stage_must_be_valid(cls, v):
        from agent import FUNNEL_STAGES
        if v not in FUNNEL_STAGES:
            raise ValueError(f"Invalid stage '{v}'. Allowed: {FUNNEL_STAGES}")
        return v

@app.patch("/api/v1/leads/{lead_id}/stage")
def update_lead_stage(
    lead_id: int,
    stage_update: LeadStageUpdate,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db)
):
    """
    Updates the funnel stage of a specific lead.
    """
    lead = db.query(models.Lead).filter(models.Lead.id == lead_id, models.Lead.client_id == current_client.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.funnel_stage = stage_update.stage

    # --- AUDIT TRAIL FOR FUNNEL STAGE CHANGES ---
    safe_stage_name = stage_update.stage.replace(' ', '_').lower()
    db.add(models.EventLog(
        session_id=lead.session_id,
        client_id=current_client.id,
        event_type="audit",
        action_type=f"stage_changed_to_{safe_stage_name}",
        agent_type="Human_User"
    ))

    db.commit()
    return {"status": "success", "lead_id": lead.id, "stage": lead.funnel_stage}


@app.get("/api/v1/leads/{lead_id}/score")
def score_lead_endpoint(
    lead_id: int,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """
    Phase 5 (5.6): compute the IREIOS lead score for a client-owned lead.

    Returns the deterministic scoring breakdown (conversion probability,
    temperature, urgency, engagement, budget alignment) without mutating the row.
    """
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.client_id == current_client.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    from app.agents.whatsapp_agent import score_lead
    return {"status": "success", "lead_id": lead_id, "scores": score_lead(lead)}


from app.agents.sales_agent import SalesAiBody, sales_agent  # IREIOS 4.0 sales-ai body


@app.post("/api/v1/leads/{lead_id}/sales-ai")
async def sales_ai_endpoint(
    lead_id: int,
    body: Optional[SalesAiBody] = None,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """
    IREIOS 4.0: Sales AI with preview|execute.

    * preview (default) — compute scores + NBA; no DB/CRM side effects
    * execute — score, assign, stage progress, CRM via AE (Phase 6 path)
    """
    body = body or SalesAiBody()
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.client_id == current_client.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    sync_crm = body.mode == "execute"
    result = await sales_agent.run_sales_ai(
        db, lead, current_client.id, sync_crm=sync_crm, mode=body.mode
    )
    return {"status": "success", "lead_id": lead_id, **result}


@app.get("/api/v1/leads/{lead_id}/memory")
def lead_memory_endpoint(
    lead_id: int,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """
    Phase 7 (7.5): return persisted conversation-memory items for a client-owned
    lead, plus a recent-message summary.
    """
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.client_id == current_client.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    items = conversation_memory.recall(db, lead_id=lead_id, client_id=current_client.id)
    summary = conversation_memory.summarize_recent(db, session_id=lead.session_id)
    return {
        "status": "success",
        "lead_id": lead_id,
        "memory": [{"key": m.key, "value": m.value, "type": m.memory_type} for m in items],
        "recent_summary": summary,
    }


@app.get("/api/v1/kg/status")
def kg_status_endpoint():
    """
    Phase 7 (7.1): report whether the Neo4j knowledge graph is available.
    Returns availability only (no tenant data) — safe to expose.
    """
    return {"status": "success", "knowledge_graph_available": bool(knowledge_graph.available)}


@app.post("/api/v1/leads/{lead_id}/memory")
def store_lead_memory_endpoint(
    lead_id: int,
    body: dict,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """
    Phase 7 (7.5): store a structured memory item for a client-owned lead.
    Body: {"key": str, "value": str, "memory_type": str (optional)}.
    """
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.client_id == current_client.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    key = (body or {}).get("key")
    value = (body or {}).get("value")
    if not key or value is None:
        raise HTTPException(status_code=422, detail="key and value are required")
    item = conversation_memory.remember(
        db, lead_id=lead_id, client_id=current_client.id, key=key, value=str(value),
        session_id=lead.session_id, memory_type=(body or {}).get("memory_type", "fact"),
    )
    return {"status": "success", "id": item.id, "key": item.key, "value": item.value}


# ---------------------------------------------------------------------------
# Phase 8 — Prediction APIs + Marketing / CS / Competitor (Tasks 8.1–8.5)
# ---------------------------------------------------------------------------

@app.get("/api/v1/leads/{lead_id}/prediction")
def lead_prediction_endpoint(
    lead_id: int,
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """Phase 8 (8.1): conversion prediction + expected closure days for a lead."""
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.client_id == current_client.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    from app.services.prediction_service import predict_conversion
    return {"status": "success", "lead_id": lead_id, "prediction": predict_conversion(lead)}


@app.get("/api/v1/marketing/segments")
def marketing_segments_endpoint(
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """Phase 8 (8.2/8.3): segment open leads and suggest a campaign per segment."""
    from app.services.prediction_service import marketing_campaign_suggestion, segment_leads
    segments = segment_leads(db, current_client.id)
    suggestions = {seg: marketing_campaign_suggestion(seg) for seg in ("hot", "warm", "cold")}
    return {"status": "success", "client_id": current_client.id,
            "segments": segments, "campaign_suggestions": suggestions}


@app.get("/api/v1/cs/at-risk")
def cs_at_risk_endpoint(
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db),
):
    """Phase 8 (8.4): customer-success — list cold/inactive open leads."""
    from app.services.prediction_service import detect_at_risk
    at_risk = detect_at_risk(db, current_client.id)
    return {"status": "success", "client_id": current_client.id, "at_risk": at_risk,
            "count": len(at_risk)}


@app.post("/api/v1/competitor/signals")
def competitor_signals_endpoint(body: dict = {}):
    """Phase 8 (8.5): competitor keyword monitor (no external network call)."""
    from app.services.prediction_service import competitor_signals
    text = (body or {}).get("text")
    return {"status": "success", "signals": competitor_signals(text)}


@app.get("/api/v1/leads/export")
def export_leads(
    current_client: models.Client = Depends(auth.get_current_client),
    db: DBSession = Depends(get_db)
):
    """
    Exports all leads for the given client in CSV format using StreamingResponse.
    """
    leads = db.query(models.Lead).filter(models.Lead.client_id == current_client.id).all()
    
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(["Session ID", "Name", "Phone", "Budget", "Location", "Intent", "Score", "Visit Date", "Updated At"])
    
    for lead in leads:
        writer.writerow([
            lead.session_id, lead.name or "N/A", lead.phone or "N/A",
            lead.budget or "N/A", lead.location or "N/A", lead.intent or "N/A",
            lead.score or "Low", lead.visit_date or "N/A", str(lead.updated_at)
        ])
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=leads_export_{current_client.id}.csv"
    return response


@app.get("/health")
async def health_check(db: DBSession = Depends(get_db)):
    """Enterprise Provider Health Checks"""
    import datetime as _dt

    # 1. Postgres Check
    try:
        db.execute(models.Session.__table__.select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "error"
        send_critical_alert("Database Outage", "PostgreSQL connection refused.")

    # 2. Redis Check
    try:
        await redis_client.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "error"
        logger.error("ALERT: Redis Cache connection failed in health check!")

    # 3. Third-Party Provider Checks
    twilio_status = "configured" if settings.TWILIO_ACCOUNT_SID else "missing"
    gemini_status = "configured" if settings.GEMINI_API_KEY else "missing"

    uptime_seconds = round((_dt.datetime.now(_dt.timezone.utc) - APP_START_TIME).total_seconds())
    system_status = "healthy" if db_status == "connected" and redis_status == "connected" else "degraded"

    return {
        "status": system_status,
        "database_postgres": db_status,
        "cache_redis": redis_status,
        "provider_twilio": twilio_status,
        "provider_gemini": gemini_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "uptime_seconds": uptime_seconds,
    }

# Mount static files for the Dashboard
# Note: events_router is mounted once near app construction (above); do not
# re-include here — duplicate include breaks OpenAPI operation IDs and route lookup.
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
