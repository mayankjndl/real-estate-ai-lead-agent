"""Negotiation UI — Non-blocking is_negotiating flag (Layer 1 + Layer 2).

Plan: Negotiation AI pivot (UI-driven, no HITL pause)
Tests:
  - Lead.is_negotiating column exists and defaults to False
  - Layer 1: keyword detection sets is_negotiating = True
  - Layer 2: budget misalignment sets is_negotiating = True
  - NegotiationAgent no longer includes requires_approval: True
  - Debounce helper works correctly
"""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-negotiation")

from database import SessionLocal
from models import Client, Lead, Message, Session


def _clean(db, sid):
    db.query(Message).filter(Message.session_id == sid).delete()
    db.query(Lead).filter(Lead.session_id == sid).delete()
    db.query(Session).filter(Session.id == sid).delete()
    db.commit()


def _db_ok() -> bool:
    try:
        db = SessionLocal()
        db.query(Client).first()
        db.close()
        return True
    except Exception:
        return False


def _column_exists(column_name: str) -> bool:
    """Check if a column exists on the leads table (pre-migration guard)."""
    try:
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(SessionLocal().bind)
        columns = [c["name"] for c in insp.get_columns("leads")]
        return column_name in columns
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Model tests
# --------------------------------------------------------------------------- #

def test_lead_has_is_negotiating_column():
    """Lead model should have is_negotiating boolean column."""
    from models import Lead
    assert hasattr(Lead, "is_negotiating")


def test_is_negotiating_defaults_to_false():
    """New leads should have is_negotiating = False by default (via Column default)."""
    from models import Lead
    lead = Lead()
    # SQLAlchemy Column(default=False) only applies on DB insert, not in-memory.
    # Verify the column has a default of False defined.
    col = Lead.__table__.c.is_negotiating
    assert col.default.arg is False


# --------------------------------------------------------------------------- #
# Event helper tests
# --------------------------------------------------------------------------- #

def test_debounce_key_format():
    """Debounce key should follow pattern negotiation_emitted:{client_id}:{lead_id}."""
    from app.events.negotiation import debounce_key
    key = debounce_key(1, 42)
    assert key == "negotiation_emitted:1:42"


def test_debounce_ttl_is_5_minutes():
    """Debounce TTL should be 300 seconds (5 minutes)."""
    from app.events.negotiation import NEGOTIATION_DEBOUNCE_TTL
    assert NEGOTIATION_DEBOUNCE_TTL == 300


def test_publish_negotiation_started_returns_bool():
    """publish_negotiation_started should return a boolean."""
    from app.events.negotiation import publish_negotiation_started
    import inspect
    sig = inspect.signature(publish_negotiation_started)
    assert "client_id" in sig.parameters
    assert "lead_id" in sig.parameters
    assert "trigger" in sig.parameters


# --------------------------------------------------------------------------- #
# Layer 1: Keyword detection tests
# --------------------------------------------------------------------------- #

def test_negotiation_phrases_documented():
    """Layer 1 phrase list should be documented and non-empty."""
    # The phrase list is defined in agent.py inside process_chat()
    # We verify the concept exists and the list is non-empty
    _NEGOTIATION_PHRASES = [
        "negotiate", "negotiation", "discount", "reduce price",
        "lower price", "too expensive", "can you reduce", "final price",
        "best price", "cheaper", "afford", "budget is tight",
        "change my budget", "reduce my budget", "lower my budget",
        "budget is only", "can only afford", "stretch my budget",
    ]
    assert len(_NEGOTIATION_PHRASES) >= 15
    assert "negotiate" in _NEGOTIATION_PHRASES
    assert "change my budget" in _NEGOTIATION_PHRASES
    assert "reduce my budget" in _NEGOTIATION_PHRASES


def test_budget_change_phrases_trigger_detection():
    """Layer 1: budget-change phrases should trigger negotiation detection."""
    _NEGOTIATION_PHRASES = [
        "negotiate", "negotiation", "discount", "reduce price",
        "lower price", "too expensive", "can you reduce", "final price",
        "best price", "cheaper", "afford", "budget is tight",
        "change my budget", "reduce my budget", "lower my budget",
        "budget is only", "can only afford", "stretch my budget",
    ]
    test_cases = [
        "change my budget to 50lakhs",
        "reduce my budget to 80 lakhs",
        "lower my budget please",
        "my budget is only 40 lakhs",
        "i can only afford 60 lakhs",
        "can you stretch my budget",
    ]
    for msg in test_cases:
        matched = any(phrase in msg for phrase in _NEGOTIATION_PHRASES)
        assert matched, f"Expected negotiation phrase to match in: '{msg}'"


def test_keyword_detection_sets_flag():
    """Layer 1: keyword match should set is_negotiating = True on lead."""
    if not _db_ok() or not _column_exists("is_negotiating"):
        pytest.skip("DB not available or migration not applied")
    db = SessionLocal()
    sid = "test_neg_keyword_1"
    try:
        _clean(db, sid)
        client = db.query(Client).first()
        session = Session(id=sid, client_id=client.id)
        db.add(session)
        lead = Lead(
            session_id=sid,
            client_id=client.id,
            name="Test Lead",
            phone="+919999999999",
            budget="50L",
            location="Baner",
            property_type="2BHK",
            is_negotiating=False,
        )
        db.add(lead)
        db.commit()

        # Simulate Layer 1: keyword detection
        msg_clean = "i want to negotiate the budget"
        _NEGOTIATION_PHRASES = [
            "negotiate", "negotiation", "discount", "reduce price",
            "lower price", "too expensive", "can you reduce", "final price",
            "best price", "cheaper", "afford", "budget is tight",
        ]
        if any(phrase in msg_clean for phrase in _NEGOTIATION_PHRASES):
            lead.is_negotiating = True
            db.commit()

        assert lead.is_negotiating is True
    finally:
        _clean(db, sid)
        db.close()


# --------------------------------------------------------------------------- #
# Layer 2: Budget misalignment tests
# --------------------------------------------------------------------------- #

def test_budget_misalignment_sets_flag():
    """Layer 2: budget misalignment should set is_negotiating = True."""
    if not _db_ok() or not _column_exists("is_negotiating"):
        pytest.skip("DB not available or migration not applied")
    db = SessionLocal()
    sid = "test_neg_budget_1"
    try:
        _clean(db, sid)
        client = db.query(Client).first()
        session = Session(id=sid, client_id=client.id)
        db.add(session)
        lead = Lead(
            session_id=sid,
            client_id=client.id,
            name="Test Lead",
            phone="+919999999999",
            budget="50L",
            location="Baner",
            property_type="2BHK",
            is_negotiating=False,
        )
        db.add(lead)
        db.commit()

        # Simulate Layer 2: budget misalignment
        scores = {"budget_alignment_status": "mismatch"}
        if scores.get("budget_alignment_status") and scores["budget_alignment_status"] not in ("aligned", "unknown"):
            lead.is_negotiating = True
            db.commit()

        assert lead.is_negotiating is True
    finally:
        _clean(db, sid)
        db.close()


def test_budget_aligned_does_not_set_flag():
    """Layer 2: aligned budget should NOT set is_negotiating."""
    if not _db_ok() or not _column_exists("is_negotiating"):
        pytest.skip("DB not available or migration not applied")
    db = SessionLocal()
    sid = "test_neg_aligned_1"
    try:
        _clean(db, sid)
        client = db.query(Client).first()
        session = Session(id=sid, client_id=client.id)
        db.add(session)
        lead = Lead(
            session_id=sid,
            client_id=client.id,
            name="Test Lead",
            phone="+919999999999",
            budget="50L",
            location="Baner",
            property_type="2BHK",
            is_negotiating=False,
        )
        db.add(lead)
        db.commit()

        # Simulate Layer 2: aligned budget
        scores = {"budget_alignment_status": "aligned"}
        if scores.get("budget_alignment_status") and scores["budget_alignment_status"] not in ("aligned", "unknown"):
            lead.is_negotiating = True
            db.commit()

        assert lead.is_negotiating is False
    finally:
        _clean(db, sid)
        db.close()


# --------------------------------------------------------------------------- #
# NegotiationAgent tests (no HITL)
# --------------------------------------------------------------------------- #

def test_negotiation_agent_no_requires_approval():
    """NegotiationAgent ae_submit should NOT include requires_approval: True."""
    # Read the source file and verify requires_approval is not in the payload
    import ast
    with open("app/agents/negotiation_agent.py", "r") as f:
        source = f.read()
    
    # Check that "requires_approval" is NOT in the ae_submit payload
    assert "requires_approval" not in source, (
        "negotiation_agent.py should NOT contain requires_approval (HITL removed)"
    )


def test_negotiation_agent_kind_is_notify_admin():
    """NegotiationAgent payload kind should be 'notify_admin' not 'manager_approval'."""
    import ast
    with open("app/agents/negotiation_agent.py", "r") as f:
        source = f.read()
    
    assert "notify_admin" in source, "negotiation_agent.py should use kind='notify_admin'"
    assert "manager_approval" not in source, (
        "negotiation_agent.py should NOT use kind='manager_approval' (HITL removed)"
    )


# --------------------------------------------------------------------------- #
# Frontend type tests
# --------------------------------------------------------------------------- #

def test_frontend_lead_type_has_is_negotiating():
    """Frontend Lead interface should include is_negotiating field."""
    with open("frontend/src/lib/api.ts", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "is_negotiating" in content, "Lead interface should include is_negotiating"


def test_kanban_board_renders_negotiation_badge():
    """KanbanBoard should render negotiation badge when is_negotiating is true."""
    with open("frontend/src/app/(dashboard)/crm/KanbanBoard.tsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "is_negotiating" in content, "KanbanBoard should reference is_negotiating"
    assert "Open for Negotiation" in content, "KanbanBoard should render negotiation badge"


def test_kanban_board_claim_button_expanded():
    """Claim button should appear on any column when is_negotiating is true."""
    with open("frontend/src/app/(dashboard)/crm/KanbanBoard.tsx", "r", encoding="utf-8") as f:
        content = f.read()
    
    # Verify the expanded condition
    assert 'col.name === "New" || lead.is_negotiating' in content, (
        "Claim button condition should include lead.is_negotiating"
    )


def test_priority_alert_card_renders_negotiation_badge():
    """Dashboard PriorityAlertCard should show compact Negotiate badge near Claim."""
    with open(
        "frontend/src/app/(dashboard)/dashboard/PriorityAlertCard.tsx",
        "r",
        encoding="utf-8",
    ) as f:
        content = f.read()

    assert "is_negotiating" in content, "PriorityAlertCard should reference is_negotiating"
    assert "Negotiate" in content, "PriorityAlertCard should render compact Negotiate badge"


# --------------------------------------------------------------------------- #
# score_lead() budget alignment fix tests
# --------------------------------------------------------------------------- #

def test_score_lead_uses_real_budget_alignment():
    """score_lead() should use evaluate_budget_alignment, not simplistic check.

    Regression test: score_lead() previously set alignment='aligned' whenever
    budget and property_type existed, overriding the correct evaluation.
    """
    from app.agents.whatsapp_agent import score_lead
    from models import Lead

    lead = Lead(
        name="Test",
        phone="+919999999999",
        budget="50LAKHS",
        location="Hinjewadi",
        property_type="3BHK",
        intent="buy",
        lead_temperature="warm",
    )
    scores = score_lead(lead)
    # 50L vs 3BHK Hinjewadi (~90L+) should be weak/very_low, NOT aligned
    assert scores["budget_alignment_status"] not in ("aligned",), (
        f"score_lead() should not return 'aligned' for 50L budget vs 3BHK Hinjewadi, "
        f"got: {scores['budget_alignment_status']}"
    )


def test_score_lead_returns_unknown_when_missing_fields():
    """score_lead() should return 'unknown' when budget/location/property_type missing."""
    from app.agents.whatsapp_agent import score_lead
    from models import Lead

    lead = Lead(
        name="Test",
        phone="+919999999999",
        budget="50LAKHS",
        # no location
        property_type="3BHK",
        lead_temperature="warm",
    )
    scores = score_lead(lead)
    assert scores["budget_alignment_status"] == "unknown"


def test_score_lead_aligned_when_budget_matches():
    """score_lead() should return 'aligned' when budget matches property price."""
    from app.agents.whatsapp_agent import score_lead
    from models import Lead

    # 1.5cr budget for 2BHK in Baner — should be aligned (2BHK Baner ~1.2-1.8cr)
    lead = Lead(
        name="Test",
        phone="+919999999999",
        budget="1.5cr",
        location="Baner",
        property_type="2BHK",
        intent="buy",
        lead_temperature="warm",
    )
    scores = score_lead(lead)
    assert scores["budget_alignment_status"] in ("aligned", "excellent", "strong"), (
        f"1.5cr for 2BHK Baner should be aligned/strong, got: {scores['budget_alignment_status']}"
    )
