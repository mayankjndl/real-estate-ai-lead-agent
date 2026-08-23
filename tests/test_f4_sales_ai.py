"""IREIOS 4.0 — Sales AI preview|execute (P4-1 contract).

DB-free: uses in-memory Lead objects + monkeypatched helpers.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.agents.sales_agent import SalesAgent, SalesAiBody, recommend_next_action
from models import Lead
from pydantic import ValidationError


def test_sales_ai_body_validator():
    assert SalesAiBody().mode == "preview"
    assert SalesAiBody(mode="EXECUTE").mode == "execute"
    try:
        SalesAiBody(mode="auto")
        assert False, "expected ValidationError"
    except ValidationError:
        pass


def test_preview_does_not_mutate_lead(monkeypatch):
    lead = Lead(
        id=1,
        session_id="s1",
        client_id=1,
        name="Buyer",
        phone="+9199",
        location="Wakad",
        budget="80L",
        property_type="2BHK",
        lead_temperature="warm",
        funnel_stage="New",
        conversion_probability=None,
        assigned_agent=None,
    )
    scores = {
        "conversion_probability": 72.0,
        "lead_temperature": "hot",
        "engagement_score": 60.0,
        "urgency_level": "high",
        "confidence_score": 80.0,
    }
    monkeypatch.setattr(
        "app.agents.sales_agent.score_lead",
        lambda _lead: dict(scores),
    )
    monkeypatch.setattr(
        "app.intelligence.agent_matcher.match_best_agent",
        lambda **kw: {"assigned_agent": "WouldBeAgent", "match_score": 90},
    )

    class _Db:
        def refresh(self, obj):
            pass

        def expire(self, obj):
            pass

        def commit(self):
            raise AssertionError("preview must not commit")

    async def run():
        return await SalesAgent().run_sales_ai(
            _Db(), lead, 1, sync_crm=False, mode="preview"
        )

    res = asyncio.run(run())
    assert res["mode"] == "preview"
    assert res["applied"] is False
    assert res["crm_sync"] is None
    assert res["scores"]["conversion_probability"] == 72.0
    assert res["assigned_agent"] == "WouldBeAgent"
    assert res["funnel_stage"] == "New"
    # lead row fields unchanged
    assert lead.lead_temperature == "warm"
    assert lead.conversion_probability is None
    assert lead.assigned_agent is None
    assert lead.funnel_stage == "New"


def test_execute_applies_scores_and_commits(monkeypatch):
    lead = Lead(
        id=2,
        session_id="s2",
        client_id=1,
        name="Buyer",
        phone="+9199",
        location="Wakad",
        budget="80L",
        property_type="2BHK",
        lead_temperature="warm",
        funnel_stage="New",
        assigned_agent=None,
    )
    scores = {
        "conversion_probability": 55.0,
        "lead_temperature": "warm",
        "engagement_score": 50.0,
        "urgency_level": "medium",
        "confidence_score": 70.0,
    }
    monkeypatch.setattr(
        "app.agents.sales_agent.score_lead",
        lambda _lead: dict(scores),
    )
    def _assign(db, lead, client_id, q, force=False):
        lead.assigned_agent = "AssignedX"
        return "AssignedX"

    monkeypatch.setattr(
        "app.agents.sales_agent.ensure_lead_assignment",
        _assign,
    )
    async def _fake_ae(lead, client_id, recommendation):
        return [{"action": "send_whatsapp", "status": "ok", "nba": recommendation.get("action")}]

    monkeypatch.setattr("app.agents.sales_agent._nba_to_ae_action", _fake_ae)
    committed = {"ok": False}

    class _Db:
        def add(self, *a, **k):
            pass

        def commit(self):
            committed["ok"] = True

        def refresh(self, *a, **k):
            pass

    async def run():
        return await SalesAgent().run_sales_ai(
            _Db(), lead, 1, sync_crm=False, mode="execute"
        )

    res = asyncio.run(run())
    assert res["mode"] == "execute"
    assert res["applied"] is True
    assert committed["ok"] is True
    assert lead.lead_temperature == "warm"
    assert lead.conversion_probability == 55.0
    assert lead.assigned_agent == "AssignedX"
    assert "actions_executed" in res
    assert res["actions_executed"][0]["action"] == "send_whatsapp"
    assert "scores_before" in res
    assert "note" in res


def test_invalid_mode_raises():
    lead = Lead(id=3, client_id=1, session_id="s3")

    class _Db:
        pass

    async def run():
        return await SalesAgent().run_sales_ai(
            _Db(), lead, 1, sync_crm=False, mode="nope"
        )

    try:
        asyncio.run(run())
        assert False, "expected ValueError"
    except ValueError as e:
        assert "invalid" in str(e).lower()


def test_http_route_source_has_preview_default():
    """Source-level contract: endpoint uses SalesAiBody default preview."""
    from pathlib import Path

    src = Path("main.py").read_text(encoding="utf-8")
    assert "SalesAiBody" in src
    assert 'mode == "execute"' in src or "mode == 'execute'" in src
    sa = Path("app/agents/sales_agent.py").read_text(encoding="utf-8")
    assert 'mode: str = "execute"' in sa or 'mode: str = "execute"' in sa
    assert "preview" in sa
    assert "applied" in sa


def test_recommend_still_works_with_preview_scores():
    lead = Lead(
        lead_temperature="hot",
        name="A",
        phone="+91",
        location="W",
        budget="80L",
        property_type="2BHK",
    )
    assert recommend_next_action(lead)["action"] == "escalate_hot"
