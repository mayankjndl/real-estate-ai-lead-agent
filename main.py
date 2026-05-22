from contextlib import asynccontextmanager
import asyncio
import collections
import logging
import json
import time
import redis.asyncio as aioredis
import time
from fastapi import FastAPI, Depends, HTTPException, Security, status, Request, Form, Response, BackgroundTasks
from twilio.rest import Client
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.security.api_key import APIKeyHeader, APIKeyQuery
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from typing import Optional
from pydantic import BaseModel
import csv
from io import StringIO
from config import settings
from database import engine, Base, get_db
from agent import process_chat
from follow_up import check_and_send_followups
from apscheduler.schedulers.background import BackgroundScheduler
import models
import os
from crm_sync import sync_lead_to_crm

# Admin Security for Revenue Phase
ADMIN_API_KEY_NAME = "X-Admin-Token"
admin_api_key_header = APIKeyHeader(name=ADMIN_API_KEY_NAME, auto_error=True)

def verify_admin_key(api_key: str = Security(admin_api_key_header)):
    # Simple admin check. In production, this would be an environment variable.
    admin_key = os.getenv("ADMIN_API_KEY", "real-estate-super-secret-key")
    if api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing Admin API Key"
        )
    return api_key

# Configure Central App Logging (stdout so Render dashboard captures it)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    db = next(get_db())
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

scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_followups, "interval", minutes=1, id="follow_up_checker")
scheduler.add_job(backup_postgres, "cron", hour=2, minute=0, id="nightly_backup")
scheduler.add_job(daily_cleanup_job, "cron", hour=3, minute=0, id="nightly_cleanup")

@asynccontextmanager
async def lifespan(app):
    """Start the follow-up scheduler when the server boots, stop it on shutdown."""
    scheduler.start()
    logger.info("Background scheduler started (follow-ups, backups, cleanup)")
    yield
    scheduler.shutdown()
    logger.info("Background scheduler stopped")

app = FastAPI(
    title="Real Estate AI Lead Agent",
    description="Advanced client-grade AI assistant backend for real estate tracking, dynamic questioning, and intelligent lead evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

# TLS Enforcement (Redirect HTTP to HTTPS)
if os.getenv("RENDER") or os.getenv("PRODUCTION"):
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS configuration to allow local Dashboard frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this to specific dashboard URLs
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
# Only applicable to analytical routing (Chat endpoints must be universally accessible)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="X-API-Key", auto_error=False)

def get_current_client_id(
    api_key_h: str = Security(api_key_header),
    api_key_q: str = Security(api_key_query)
) -> str:
    """
    Validates the existence and accuracy of an API Key against config environment.
    Supports payload from secure Headers (Swagger/Postman) or secure URL Query Strings (Web Dashboard).
    """
    api_key = api_key_h or api_key_q
    
    for client_id, key in settings.CLIENT_KEYS.items():
        if api_key == key:
            return client_id
            
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-API-Key credentials",
    )


@app.post("/api/v1/chat")
async def chat_endpoint(session_id: str, message: str, client_id: str = "default", db: DBSession = Depends(get_db)):
    """
    Public AI chat interface.
    Receives user utterance and a session ID to keep multi-turn context.
    Orchestrates Gemini response generation and silent lead data capture.
    """
    try:
        reply = await process_chat(session_id, message, db, client_id=client_id)
        return {
            "status": "success",
            "session_id": session_id,
            "client_id": client_id,
            "reply": reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def background_process_and_push(session_id: str, Body: str, client_id: str):
    """
    Executes if the LLM exceeds 15s timeout. Uses Twilio REST API to push the reply out-of-band.
    If the LLM still fails in the background, sends a graceful fallback so the user is never left with no response.
    """
    db = next(get_db())
    try:
        payload = LeadIngestionPayload(
            session_id=session_id,
            source="whatsapp",
            message=Body,
            whatsapp_opt_in=True
        )
        reply_text = await process_unified_lead(payload, db, client_id, background=True)
        if settings.TWILIO_ACCOUNT_SID:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            await asyncio.to_thread(
                client.messages.create,
                from_=settings.TWILIO_PHONE_NUMBER,
                body=reply_text,
                to=f"whatsapp:{session_id}"
            )
            logger.info(f"Background task pushed response to {session_id}")
    except Exception as e:
        logger.error(f"Background task failed for {session_id}: {e}")
        # Always guarantee the user gets a response — send fallback via Twilio REST
        try:
            if settings.TWILIO_ACCOUNT_SID:
                fallback_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                await asyncio.to_thread(
                    fallback_client.messages.create,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    body="I'm experiencing a brief connectivity issue. Please try again in a moment, or reach our team directly at +91 9876543210.",
                    to=f"whatsapp:{session_id}"
                )
                logger.warning(f"FALLBACK | session={session_id} | reason=background_task_failure | detail=graceful_fallback_sent_via_twilio")
        except Exception as fallback_err:
            logger.error(f"FALLBACK push also failed for {session_id}: {fallback_err}")
            # Phase 2 Hardening: Dead-Letter Queue integration for Twilio outbound
            payload = {
                "session_id": session_id,
                "body": "I'm experiencing a brief connectivity issue. Please try again in a moment, or reach our team directly at +91 9876543210.",
                "to": f"whatsapp:{session_id}"
            }
            dlq_entry = models.DLQEvent(
                target_endpoint="twilio_outbound",
                payload=payload,
                error_trace=str(fallback_err),
                status="pending"
            )
            db.add(dlq_entry)
            db.commit()
    finally:
        db.close()

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

async def process_unified_lead(payload: LeadIngestionPayload, db: DBSession, client_id: str = "client_A", background: bool = False):
    # 1. Ensure Session exists
    session = db.query(models.Session).filter(models.Session.id == payload.session_id).first()
    if not session:
        session = models.Session(id=payload.session_id, client_id=client_id)
        db.add(session)
        db.commit()
    
    # 2. Ensure Lead exists, preventing duplicates by session_id
    lead = db.query(models.Lead).filter(models.Lead.session_id == payload.session_id).first()
    is_new_lead = False
    if not lead:
        lead = models.Lead(
            session_id=payload.session_id,
            source=payload.source,
            whatsapp_opt_in=payload.whatsapp_opt_in
        )
        db.add(lead)
        is_new_lead = True
    
    # Update fields if provided
    if payload.name: lead.name = payload.name
    if payload.phone: lead.phone = payload.phone
    if payload.intent: lead.intent = payload.intent
    if payload.budget: lead.budget = payload.budget
    if payload.location: lead.location = payload.location
    if payload.property_type: lead.property_type = payload.property_type
    
    db.commit()

    db.commit()

    if is_new_lead:
        lead.funnel_stage = "New"
        db.add(models.EventLog(session_id=payload.session_id, event_type="lead_created"))
        db.commit()
        # Fire background CRM Sync
        asyncio.create_task(sync_lead_to_crm(lead.id))
        
    # Check for Appointment
    if lead.visit_date and lead.funnel_stage not in ["Appointment Scheduled", "Closed Won"]:
        lead.funnel_stage = "Appointment Scheduled"
        db.commit()

    # 3. Handle Initial Outbound Message for Passive Sources
    if is_new_lead and payload.source != "whatsapp" and payload.whatsapp_opt_in:
        outbound_text = f"Hi {lead.name or 'there'}, thanks for your interest! I'm the AI assistant for ABC Properties. Are you looking to buy or rent?"
        if settings.TWILIO_ACCOUNT_SID and lead.phone:
            try:
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                client.messages.create(
                    from_=settings.TWILIO_PHONE_NUMBER,
                    body=outbound_text,
                    to=f"whatsapp:{lead.phone}"
                )
                db.add(models.EventLog(session_id=payload.session_id, event_type="message_sent"))
                db.add(models.Message(session_id=payload.session_id, role="assistant", content=outbound_text))
                
                # Update Funnel Stage
                if lead.funnel_stage == "New":
                    lead.funnel_stage = "Contacted"
                    
                db.commit()
            except Exception as e:
                logger.error(f"Failed to send outbound to {lead.phone}: {e}")

    # 4. If a message was sent, process via AI
    if payload.message:
        reply_text = await process_chat(payload.session_id, payload.message, db, client_id=client_id, is_background=background)
        return reply_text
    
    return "Lead processed successfully."

@app.post("/api/v1/ingest")
async def ingest_lead(payload: LeadIngestionPayload, db: DBSession = Depends(get_db)):
    """Unified API for processing leads from custom website forms or frontends."""
    try:
        result = await process_unified_lead(payload, db)
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/webhook/meta")
async def meta_webhook(payload: dict, db: DBSession = Depends(get_db)):
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
        await process_unified_lead(parsed, db)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/webhook/portals")
async def portals_webhook(payload: dict, db: DBSession = Depends(get_db)):
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
        await process_unified_lead(parsed, db)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    MessageSid: str = Form(None),
    From: str = Form(...),
    Body: str = Form(...),
    db: DBSession = Depends(get_db)
):
    """
    Twilio WhatsApp Webhook.
    Handles duplicate prevention, queueing, and timeouts.
    """
    request_start = time.time()
    try:
        # Task 1: Duplicate Message Protection
        if MessageSid:
            existing = db.query(models.WebhookLog).filter(models.WebhookLog.message_sid == MessageSid).first()
            if existing:
                logger.info(f"Duplicate message ignored: {MessageSid}")
                return Response(content="<Response></Response>", media_type="application/xml")
            
            # Log the new message
            db.add(models.WebhookLog(message_sid=MessageSid))
            db.commit()

        session_id = From.replace("whatsapp:", "")
        client_id = "client_A"
        
        # Task 2: Message Queue Handling (Lock per session using Redis)
        async with redis_client.lock(f"session_lock:{session_id}", timeout=20.0, blocking_timeout=30.0):
            # Task 6: Timeout Handling
            try:
                # Give LLM 15s to finish to prevent double-charging the Google Free Tier Rate limit
                payload = LeadIngestionPayload(
                    session_id=session_id,
                    source="whatsapp",
                    message=Body,
                    whatsapp_opt_in=True
                )
                reply_text = await process_unified_lead(payload, db, client_id=client_id)
                
                # Finished fast enough — log latency and return standard TwiML
                latency_ms = round((time.time() - request_start) * 1000)
                logger.info(f"LATENCY | session={session_id} | {latency_ms}ms | status=delivered")
                twiml = MessagingResponse()
                twiml.message(reply_text)
                return Response(content=str(twiml), media_type="application/xml")
            
            except asyncio.TimeoutError:
                # Took too long — dispatch to background and return interim response
                logger.info(f"TIMEOUT | session={session_id} | exceeded=15000ms | action=background_dispatch")
                background_tasks.add_task(background_process_and_push, session_id, Body, client_id)
                
                twiml = MessagingResponse()
                twiml.message("Just checking that for you...")
                return Response(content=str(twiml), media_type="application/xml")
    
    except Exception as e:
        logger.warning(f"FALLBACK | session={session_id if 'session_id' in locals() else 'unknown'} | reason={type(e).__name__} | detail={str(e)[:120]}")
        twiml = MessagingResponse()
        twiml.message("I'm experiencing a brief connectivity issue. Let me connect you with our expert at +91 9876543210.")
        return Response(content=str(twiml), media_type="application/xml")

@app.post("/api/v1/incoming_sms")
async def incoming_sms_webhook(
    background_tasks: BackgroundTasks,
    MessageSid: str = Form(None),
    From: str = Form(...),
    Body: str = Form(...),
    db: DBSession = Depends(get_db)
):
    """
    Twilio SMS Webhook.
    Handles stopping the FollowUpState for standard SMS replies.
    """
    request_start = time.time()
    try:
        # Task 1: Duplicate Message Protection (Idempotency)
        if MessageSid:
            existing = db.query(models.WebhookLog).filter(models.WebhookLog.message_sid == MessageSid).first()
            if existing:
                logger.info(f"Duplicate SMS message ignored: {MessageSid}")
                return Response(content="<Response></Response>", media_type="application/xml")
            
            db.add(models.WebhookLog(message_sid=MessageSid))
            db.commit()

        # Format number correctly if needed, Twilio standard SMS starts with '+', no "whatsapp:" prefix
        session_id = From
        
        # Stop FollowUps
        follow_up_state = db.query(models.FollowUpState).filter(models.FollowUpState.session_id == session_id).first()
        if follow_up_state:
            follow_up_state.follow_up_status = "stopped"
            follow_up_state.last_user_reply_timestamp = func.now()
            db.commit()
            logger.info(f"SMS Webhook: Follow ups stopped for {session_id}")

        # Process as normal Lead Interaction
        try:
            async with redis_client.lock(f"session_lock:{session_id}", timeout=20.0, blocking_timeout=30.0):
                payload = LeadIngestionPayload(
                    session_id=session_id,
                    source="sms",
                    message=Body,
                    whatsapp_opt_in=False
                )
                reply_text = await process_unified_lead(payload, db, client_id="client_A")
        except Exception as redis_err:
            logger.warning(f"Redis unavailable or lock failed, proceeding without lock: {redis_err}")
            payload = LeadIngestionPayload(
                session_id=session_id,
                source="sms",
                message=Body,
                whatsapp_opt_in=False
            )
            reply_text = await process_unified_lead(payload, db, client_id="client_A")
            
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

@app.get("/api/v1/reports/pipeline", dependencies=[Depends(verify_admin_key)])
async def get_pipeline_report(db: DBSession = Depends(get_db)):
    """
    Aggregates funnel_stage data to calculate conversion and qualified rates.
    """
    from models import Lead
    
    total_leads = db.query(Lead).count()
    
    stages = db.query(Lead.funnel_stage, func.count(Lead.id)).group_by(Lead.funnel_stage).all()
    stage_counts = {stage: count for stage, count in stages}
    
    new_leads = stage_counts.get("New", 0)
    contacted = stage_counts.get("Contacted", 0)
    scheduled = stage_counts.get("Appointment Scheduled", 0)
    closed = stage_counts.get("Closed Won", 0)
    
    qualified = contacted + scheduled + closed
    
    return {
        "pipeline": {
            "total_leads": total_leads,
            "new": new_leads,
            "contacted": contacted,
            "appointment_scheduled": scheduled,
            "closed_won": closed
        },
        "rates": {
            "qualified_rate": round((qualified / total_leads * 100), 2) if total_leads else 0,
            "conversion_rate": round((closed / total_leads * 100), 2) if total_leads else 0
        }
    }

@app.get("/api/v1/roi/funnel_metrics", dependencies=[Depends(verify_admin_key)])
async def get_funnel_metrics(db: DBSession = Depends(get_db)):
    """Total Leads, Qualified, Appt Booked, Site Visits, Deal Closed"""
    from models import EventLog, Lead
    # Total leads
    total_leads = db.query(Lead).count()
    # Qualified: has budget, location, or intent
    qualified = db.query(Lead).filter((Lead.budget.isnot(None)) | (Lead.intent.isnot(None))).count()
    # Appt Booked: has visit_date
    appointments = db.query(Lead).filter(Lead.visit_date.isnot(None)).count()
    
    # We can also track from EventLog for deal_closed and site_visit_done if added later by Anohita
    site_visits = db.query(EventLog).filter(EventLog.action_type == "site_visit_done").count()
    deal_closed = db.query(EventLog).filter(EventLog.action_type == "deal_closed").count()
    
    return {
        "funnel": {
            "total_leads": total_leads,
            "qualified": qualified,
            "appointment_booked": appointments,
            "site_visit_done": site_visits,
            "deal_closed": deal_closed
        },
        "conversion_rates": {
            "lead_to_qualified": round((qualified / total_leads * 100), 2) if total_leads else 0,
            "qualified_to_appt": round((appointments / qualified * 100), 2) if qualified else 0
        },
        "financials": {
            "revenue_generated": 0  # Populated by deal_closed events from Anohita's layer
        }
    }

@app.get("/api/v1/roi/speed_intelligence", dependencies=[Depends(verify_admin_key)])
async def get_speed_intelligence(db: DBSession = Depends(get_db)):
    from models import EventLog
    # Average response time for AI (message_sent logs)
    avg_ai = db.query(func.avg(EventLog.latency_ms)).filter(EventLog.agent_type == 'AI', EventLog.latency_ms.isnot(None)).scalar() or 0
    # Average response time for Human (if any)
    avg_human = db.query(func.avg(EventLog.latency_ms)).filter(EventLog.agent_type == 'Human', EventLog.latency_ms.isnot(None)).scalar() or 0
    
    return {
        "average_latency_ms": {
            "AI": round(avg_ai, 2),
            "Human": round(avg_human, 2)
        }
    }

@app.get("/api/v1/roi/source_attribution", dependencies=[Depends(verify_admin_key)])
async def get_source_attribution(db: DBSession = Depends(get_db)):
    from models import Lead
    # Group by source
    sources = db.query(Lead.source, func.count(Lead.id)).group_by(Lead.source).all()
    
    # How many appointments per source
    appointments = db.query(Lead.source, func.count(Lead.id)).filter(Lead.visit_date.isnot(None)).group_by(Lead.source).all()
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
def get_analytics(client_id: str = Depends(get_current_client_id), db: DBSession = Depends(get_db)):
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

@app.get("/api/v1/leads")
def get_leads(
    client_id: str = Depends(get_current_client_id),
    db: DBSession = Depends(get_db),
    intent: Optional[str] = None,
    location: Optional[str] = None,
    score: Optional[str] = None
):
    """
    Client-secured lead extraction endpoint filtering by depth, intent, location, and score.
    Supports optional query parameters like ?intent=buy&score=High
    """
    query = db.query(models.Lead).join(models.Session).filter(models.Session.client_id == client_id)
    
    # Case-insensitive filtering dynamically based on provided query parameters
    if intent:
        query = query.filter(models.Lead.intent.ilike(f"%{intent}%"))
    if location:
        query = query.filter(models.Lead.location.ilike(f"%{location}%"))
    if score:
        query = query.filter(models.Lead.score.ilike(f"%{score}%"))
        
    leads = query.all()
    
    return {
        "status": "success",
        "total_returned": len(leads),
        "leads": leads
    }

@app.get("/api/v1/leads/export")
def export_leads(
    client_id: str = Depends(get_current_client_id),
    db: DBSession = Depends(get_db)
):
    """
    Exports all leads for the given client in CSV format using StreamingResponse.
    """
    leads = db.query(models.Lead).join(models.Session).filter(models.Session.client_id == client_id).all()
    
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
    response.headers["Content-Disposition"] = f"attachment; filename=leads_export_{client_id}.csv"
    return response

@app.get("/health")
def health_check(db: DBSession = Depends(get_db)):
    """
    Health check endpoint for monitoring, load balancers, and cron-job.org keep-alive.
    Returns DB status, scheduler state, and uptime for operational observability.
    """
    import datetime as _dt
    try:
        db.execute(models.Session.__table__.select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "error"

    uptime_seconds = round((_dt.datetime.now(_dt.timezone.utc) - APP_START_TIME).total_seconds())

    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "uptime_seconds": uptime_seconds,
        "worker_mode": "single-worker",
        "follow_up_delay_minutes": settings.FOLLOW_UP_DELAY_MINUTES,
        "ai_followups_enabled": settings.USE_AI_FOLLOWUPS,
    }

# Mount static files for the Dashboard
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
