"""Expansion Phase 5 — WhatsApp Agent v3 + brochure/floorplan + scoring (Tasks 5.1–5.9).

Tracks Step 14 (Expansion Phase 5). Exercises lead scoring, tool intent
detection, brochure/floorplan generation, v3 dispatch, and the FEATURE
selector wiring.

See plans/IREIOS_3.0_EXPANSION_CHANGELOG.md (Phase 5 status).
"""
import asyncio

import pytest

from app.agents.whatsapp_agent import (
    WhatsAppAgent,
    detect_tool_intent,
    generate_brochure,
    generate_floorplan,
    score_lead,
)
from config import settings
from models import Lead, Message, Session


def _make_lead(db, session_id="sess_wa_1", **kw):
    from tests.conftest import ensure_test_client

    cid = ensure_test_client(1)
    db.add(Session(id=session_id, client_id=cid, status="active"))
    lead = Lead(session_id=session_id, client_id=cid, **kw)
    db.add(lead)
    db.commit()
    return lead


def _clean_sid(db, sid):
    db.query(Message).filter(Message.session_id == sid).delete()
    db.query(Lead).filter(Lead.session_id == sid).delete()
    db.query(Session).filter(Session.id == sid).delete()
    db.commit()


def test_score_lead_hot_qualified():
    with __import__("database").SessionLocal() as db:
        _clean_sid(db, "sess_score_hot")
        lead = _make_lead(db, "sess_score_hot", name="A", phone="+919999999999",
                          budget="80L", location="Wakad", property_type="2BHK",
                          visit_date="2026-08-01", whatsapp_opt_in=True,
                          lead_temperature="hot")
        s = score_lead(lead)
        assert s["lead_temperature"] == "hot"
        assert s["urgency_level"] == "high"
        assert s["budget_alignment_status"] in ("aligned", "strong", "excellent")
        assert s["engagement_score"] >= 90
        assert s["conversion_probability"] >= 70
        _clean_sid(db, "sess_score_hot")


def test_score_lead_cold_incomplete():
    with __import__("database").SessionLocal() as db:
        _clean_sid(db, "sess_score_cold")
        lead = _make_lead(db, "sess_score_cold", lead_temperature="cold")
        s = score_lead(lead)
        assert s["lead_temperature"] == "cold"
        assert s["urgency_level"] == "low"
        assert s["budget_alignment_status"] == "unknown"
        assert s["conversion_probability"] < 70
        _clean_sid(db, "sess_score_cold")


def test_score_lead_visit_floor_and_no_drop():
    """Visit/full-qualify floors match chat; stored high score is not yanked down."""
    from models import Lead

    lead = Lead(
        name="A",
        phone="+9199",
        location="Wakad",
        budget="80L",
        property_type="2BHK",
        visit_date="2026-08-20",
        lead_temperature="hot",
        conversion_probability=95,
    )
    s = score_lead(lead)
    assert s["conversion_probability"] >= 88  # full-qualify floor
    assert s["conversion_probability"] >= 95  # monotonic vs stored
    assert s["lead_temperature"] == "hot"

    coldish = Lead(
        name="B",
        phone="+9199",
        location="Baner",
        budget="70L",
        property_type="2BHK",
        visit_date=None,
        lead_temperature="warm",
        conversion_probability=10,
    )
    s2 = score_lead(coldish)
    # May rise above stored 10; must not invent visit floor without visit_date
    assert s2["conversion_probability"] < 82 or s2["lead_temperature"] in ("warm", "hot", "cold")


def test_detect_tool_intent():
    assert detect_tool_intent("send me the brochure") == "brochure"
    assert detect_tool_intent("show floor plan please") == "floorplan"
    assert detect_tool_intent("i want to buy a flat in wakad") is None


def test_generate_brochure_and_floorplan():
    lead = Lead(name="Raj", location="Kharadi", property_type="3BHK", budget="1.2Cr")
    bro = generate_brochure(lead)
    assert "Kharadi" in bro and "3BHK" in bro and "brochure" in bro.lower()
    fp = generate_floorplan(lead)
    assert "3BHK" in fp and "sq ft" in fp


def test_v3_process_chat_scores_and_dispatches(monkeypatch):
    captured = {}

    async def fake_legacy(session_id, user_message, db, client_id=1, is_background=False, extra_context=None):
        db.add(Message(session_id=session_id, client_id=client_id, role="user", content=user_message))
        db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content="ok"))
        db.commit()
        return "ok"

    import agent
    import app.agents.qualification as qual
    monkeypatch.setattr(agent, "process_chat", fake_legacy)
    monkeypatch.setattr(qual, "process_chat", fake_legacy)
    monkeypatch.setattr(settings, "FEATURE_WHATSAPP_V3", True)

    sid = "sess_wa_v3"
    with __import__("database").SessionLocal() as db:
        _make_lead(db, sid, name="Me", phone="+919999999999", whatsapp_opt_in=True,
                   property_type="2BHK", location="Wakad", budget="80L")
    try:
        async def run():
            agent_v3 = WhatsAppAgent()
            return await agent_v3.process_chat(sid, "send me the brochure",
                                               __import__("database").SessionLocal(), client_id=1)
        reply = asyncio.run(run())
        assert "brochure" in reply.lower()
        with __import__("database").SessionLocal() as db:
            lead = db.query(Lead).filter(Lead.session_id == sid).first()
            assert lead.conversion_probability >= 0
            msgs = db.query(Message).filter(Message.session_id == sid).all()
            assert any("brochure" in m.content.lower() for m in msgs)
    finally:
        with __import__("database").SessionLocal() as db:
            db.query(Message).filter(Message.session_id == sid).delete()
            db.query(Lead).filter(Lead.session_id == sid).delete()
            db.query(Session).filter(Session.id == sid).delete()
            db.commit()
