from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
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
    
    # Anohita's requested fields
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    location = Column(String, nullable=True)
    intent = Column(String, nullable=True) # buy, rent, investment, browsing
    score = Column(String, default="Low") # internal logic rating (High, Medium, Low)
    visit_date = Column(String, nullable=True) # e.g. "Tuesday 2pm" — persisted so it survives context window rollover
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    
    session = relationship("Session", back_populates="lead")

class WebhookLog(Base):
    """
    Prevents duplicate message processing from automatic webhook retries.
    """
    __tablename__ = "webhook_logs"

    message_sid = Column(String, primary_key=True, index=True) # Twilio's unique message ID
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

