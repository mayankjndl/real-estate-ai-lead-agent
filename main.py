from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Security, status, Request, Form, Response
from fastapi.responses import StreamingResponse, PlainTextResponse
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from twilio.twiml.messaging_response import MessagingResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from typing import Optional
import csv
from io import StringIO
from config import settings
from database import engine, Base, get_db
from agent import process_chat
from follow_up import check_and_send_followups
from apscheduler.schedulers.background import BackgroundScheduler
import models

# Automatically orchestrate DB creation on application boot
Base.metadata.create_all(bind=engine)

# --- Background Scheduler for Follow-Up System ---
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_followups, "interval", minutes=1, id="follow_up_checker")

@asynccontextmanager
async def lifespan(app):
    """Start the follow-up scheduler when the server boots, stop it on shutdown."""
    scheduler.start()
    print("✅ Follow-up scheduler started (checking every 1 minute)")
    yield
    scheduler.shutdown()
    print("🛑 Follow-up scheduler stopped")

app = FastAPI(
    title="Real Estate AI Lead Agent",
    description="Advanced client-grade AI assistant backend for real estate tracking, dynamic questioning, and intelligent lead evaluation.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration to allow local Dashboard frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, restrict this to specific dashboard URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security Dependency ---
# Only applicable to analytical routing (Chat endpoints must be universally accessible)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_current_client_id(api_key: str = Security(api_key_header)) -> str:
    """
    Validates the existence and accuracy of an API Key header against config environment.
    """
    for client_id, key in settings.CLIENT_KEYS.items():
        if api_key == key:
            return client_id
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-API-Key header",
    )

# --- Endpoints ---

@app.post("/api/v1/chat")
def chat_endpoint(session_id: str, message: str, client_id: str = "default", db: DBSession = Depends(get_db)):
    """
    Public AI chat interface.
    Receives user utterance and a session ID to keep multi-turn context.
    Orchestrates Gemini response generation and silent lead data capture.
    """
    try:
        reply = process_chat(session_id, message, db, client_id=client_id)
        return {
            "status": "success",
            "session_id": session_id,
            "client_id": client_id,
            "reply": reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    db: DBSession = Depends(get_db)
):
    """
    Twilio WhatsApp Webhook.
    Extracts sender phone number as session_id and processes the message natively in our CRM.
    Returns TwiML XML format required by Twilio in < 3 seconds.
    """
    try:
        # 'From' comes format 'whatsapp:+919876543210' - use this as a unique session ID
        session_id = From.replace("whatsapp:", "")
        client_id = "client_A" # Default assignment for pilot, could route dynamically later

        # Native processing through our optimized, async-capable backend
        reply_text = process_chat(session_id, Body, db, client_id=client_id)

        # Build TwiML response
        twiml = MessagingResponse()
        twiml.message(reply_text)
        
        return Response(content=str(twiml), media_type="application/xml")
    
    except Exception as e:
        # Fallback ensuring the message doesn't drop
        twiml = MessagingResponse()
        twiml.message("I'm experiencing a brief connectivity issue. Let me connect you with our expert at +91 9876543210.")
        return Response(content=str(twiml), media_type="application/xml")

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
    writer.writerow(["Session ID", "Name", "Phone", "Budget", "Location", "Intent", "Score", "Updated At"])
    
    for lead in leads:
        writer.writerow([
            lead.session_id, lead.name or "N/A", lead.phone or "N/A",
            lead.budget or "N/A", lead.location or "N/A", lead.intent or "N/A",
            lead.score or "Low", str(lead.updated_at)
        ])
    
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=leads_export_{client_id}.csv"
    return response

@app.get("/health")
def health_check(db: DBSession = Depends(get_db)):
    """
    Simple health check endpoint for monitoring and load balancers.
    Verifies that the server, database, and scheduler are all operational.
    """
    # Test database connectivity
    try:
        db.execute(models.Session.__table__.select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "error"
    
    return {
        "status": "healthy",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped",
        "follow_up_delay_minutes": settings.FOLLOW_UP_DELAY_MINUTES,
        "ai_followups_enabled": settings.USE_AI_FOLLOWUPS
    }

# Mount static files for the Dashboard
app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
