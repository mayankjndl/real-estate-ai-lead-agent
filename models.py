from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Client(Base):
    """
    SaaS Tenant account containing secure credentials and API keys.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False) # For server-to-server ingestion
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    settings = Column(JSONB, default=lambda: {})
    subscription_status = Column(String, default="inactive")
    stripe_customer_id = Column(String, nullable=True)

    sessions = relationship("Session", back_populates="client", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="client", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="client", cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="client", cascade="all, delete-orphan")
    followup_states = relationship("FollowUpState", back_populates="client", cascade="all, delete-orphan")
    dlq_events = relationship("DLQEvent", back_populates="client", cascade="all, delete-orphan")

class Session(Base):
    """
    Tracks an interaction session for a specific user to maintain contextual memory.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True) # Unique UUID for the session
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True) 
    follow_up_count = Column(Integer, default=0)
    status = Column(String, default="active")
    
    client = relationship("Client", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    lead = relationship("Lead", back_populates="session", uselist=False, cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="session", cascade="all, delete-orphan")
    followup_state = relationship("FollowUpState", back_populates="session", uselist=False, cascade="all, delete-orphan")

class Message(Base):
    """
    Records human and AI messages.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("Session", back_populates="messages")
    client = relationship("Client", back_populates="messages")

class Lead(Base):
    """
    Client-grade tracking.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    location = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    score = Column(String, default="Low")
    visit_date = Column(String, nullable=True)
    
    source = Column(String, default="whatsapp")
    whatsapp_opt_in = Column(Boolean, default=False)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    conversion_probability = Column(Integer, default=0)
    expected_closure_days = Column(Integer, default=0)
    lead_temperature = Column(String, default='cold')
    engagement_score = Column(Integer, default=0)
    budget_alignment_status = Column(String, default='unknown')
    inactivity_penalty = Column(Integer, default=0)
    response_speed_score = Column(Integer, default=0)
    urgency_level = Column(String, default='low')
    assigned_agent = Column(String, nullable=True)
    conversion_status = Column(String, default='open')
    followup_stage = Column(String, default='new')
    best_performing_script = Column(Text, nullable=True)

    funnel_stage = Column(String, default="New")
    external_crm_id = Column(String, nullable=True)
    crm_sync_status = Column(String, default="pending")

    session = relationship("Session", back_populates="lead")
    client = relationship("Client", back_populates="leads")

class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    action_type = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    agent_type = Column(String, default="AI")
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="events")
    client = relationship("Client", back_populates="events")

class FollowUpState(Base):
    __tablename__ = "follow_up_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    last_user_reply_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    last_ai_reply_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    follow_up_stage = Column(String, default="Day 0")
    follow_up_sent_at = Column(DateTime(timezone=True), nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    
    follow_up_status = Column(String, default="active")
    inactivity_score = Column(Integer, default=0)

    session = relationship("Session", back_populates="followup_state")
    client = relationship("Client", back_populates="followup_states")

class WebhookLog(Base):
    """
    Prevents duplicate message processing from automatic webhook retries.
    """
    __tablename__ = "webhook_logs"

    message_sid = Column(String, primary_key=True, index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

class DLQEvent(Base):
    """
    Dead-Letter Queue for failed external integrations.
    """
    __tablename__ = "dlq_events"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True, index=True)
    target_endpoint = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    error_trace = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="pending")

    client = relationship("Client", back_populates="dlq_events")


import uuid


class Agent(Base):
    """
    Directory of human agents available for assignment and escalation.
    """
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    is_manager = Column(Boolean, default=False)  # True if they receive escalations

    client = relationship("Client")

class NotificationLog(Base):
    """
    Audit log for human handoff and hot-lead notifications.
    Tracks acknowledgments and escalation timelines.
    """
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)

    correlation_id = Column(String, default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False)
    assigned_agent = Column(String, nullable=True)

    # Statuses: pending_ack, acknowledged, escalated, failed
    status = Column(String, default="pending_ack")

    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    escalate_at = Column(DateTime(timezone=True), nullable=False)  # The 15-minute deadline

    client = relationship("Client")
    lead = relationship("Lead")
