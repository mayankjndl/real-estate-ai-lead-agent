from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Session(Base):
    """
    Tracks an interaction session for a specific user to maintain contextual memory.
    """
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True) # Unique UUID for the session
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    client_id = Column(String, index=True, nullable=True) # Scalable tracking for particular clients
    follow_up_count = Column(Integer, default=0)  # How many follow-ups have been sent (0, 1, or 2)
    status = Column(String, default="active")  # "active" or "closed"
    
    # Cascade delete messages and lead if session is destroyed
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    lead = relationship("Lead", back_populates="session", uselist=False, cascade="all, delete-orphan")
    events = relationship("EventLog", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    """
    Records human and AI messages, providing memory payload for LLM context injection.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, nullable=False) # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("Session", back_populates="messages")


class Lead(Base):
    """
    Client-grade tracking using Gemini's structured output function call extraction.
    Dynamically scoring based on user properties and interaction depth.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Core requested fields
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    location = Column(String, nullable=True)
    property_type = Column(String, nullable=True) # e.g. 1BHK, 2BHK, Villa
    intent = Column(String, nullable=True) # buy, rent, investment, browsing
    score = Column(String, default="Low") # internal logic rating (High, Medium, Low)
    visit_date = Column(String, nullable=True) # e.g. "Tuesday 2pm" — persisted so it survives context window rollover
    
    # Multi-channel integration fields
    source = Column(String, default="whatsapp") # 'whatsapp', 'facebook', 'instagram', 'website', 'magicbricks'
    whatsapp_opt_in = Column(Boolean, default=False) # MUST BE TRUE to send outbound WhatsApp messages
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    # Revenue-Phase Intelligence Fields
    conversion_probability = Column(Integer, default=0)
    expected_closure_days = Column(Integer, default=0)
    lead_temperature = Column(String, default='cold')
    engagement_score = Column(Integer, default=0)
    urgency_level = Column(String, default='low')
    assigned_agent = Column(String, nullable=True)
    conversion_status = Column(String, default='open')
    followup_stage = Column(String, default='new')
    best_performing_script = Column(Text, nullable=True)

    session = relationship("Session", back_populates="lead")

class EventLog(Base):
    """
    Tracks lifecycle events for leads across all channels.
    Events: lead_created, lead_qualified, message_sent, follow_up_sent, appointment_booked, deal_closed
    """
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    action_type = Column(String, nullable=True) # lead_created, qualified, appointment_booked, etc.
    latency_ms = Column(Integer, nullable=True)
    agent_type = Column(String, default="AI") # 'AI' vs 'Human'
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("Session", back_populates="events")

class WebhookLog(Base):
    """
    Prevents duplicate message processing from automatic webhook retries.
    """
    __tablename__ = "webhook_logs"

    message_sid = Column(String, primary_key=True, index=True) # Twilio's unique message ID
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

