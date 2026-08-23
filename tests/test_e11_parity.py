"""Expansion — Full plan parity (Workstream B/C/D).

Covers the newly promoted real agents/workflows and integrations:
  * crm_automation workflow (6.1) — assign + CRM sync + lead.assigned
  * lead_scoring handler — publishes lead.scored
  * marketing_agent (8.2) — segmentation report
  * customer_success_agent (8.3) — reminder via AE
  * competitor_monitor (8.4) — market.alert.generated on keyword match
  * CalendarExecutor — real/stub schedule_visit contract
  * GraphClient / KnowledgeGraph — safe no-op when Neo4j unconfigured

Uses the repo's `asyncio.run` + monkeypatch conventions (no pytest-asyncio).
"""
import asyncio

import pytest

from config import settings
from models import Client, Lead, Message, Session


def _clean(db, sid):
    db.query(Message).filter(Message.session_id == sid).delete()
    db.query(Lead).filter(Lead.session_id == sid).delete()
    db.query(Session).filter(Session.id == sid).delete()
    db.commit()


# --------------------------------------------------------------------------- #
# CRM automation workflow (6.1)
# --------------------------------------------------------------------------- #
def test_crm_automation_syncs_and_emits_assigned(monkeypatch):
    import app.workflows.crm_automation as ca

    submitted = {}
    published = []

    async def fake_submit(req):
        submitted.update(req)
        return {"status": "success"}

    async def fake_publish(event_type, tenant_id, entity_id, payload, source="system"):
        published.append((event_type, tenant_id, payload))
        return "evt"

    def fake_ensure(db, lead, client_id, query, force=False):
        lead.assigned_agent = "NewAgent"
        return "NewAgent"

    monkeypatch.setattr(ca, "ae_submit", fake_submit)
    monkeypatch.setattr(ca.event_bus, "publish", fake_publish)
    monkeypatch.setattr(ca, "ensure_lead_assignment", fake_ensure)

    with __import__("database").SessionLocal() as db:
        _clean(db, "sess_ca_1")
        db.add(Session(id="sess_ca_1", client_id=1, status="active"))
        lead = Lead(session_id="sess_ca_1", client_id=1, name="Buyer",
                    location="Wakad", intent="buy")
        db.add(lead)
        db.commit()
        lead_id = lead.id

        env = {"event_type": "lead.created", "tenant_id": "Client_1",
               "entity_id": str(lead_id), "payload": {"lead_id": lead_id}}
        asyncio.run(ca.crm_automation_handler(env))
        _clean(db, "sess_ca_1")

    assert submitted["action_type"] == "update_crm"
    assert any(e[0] == "lead.assigned" for e in published)


def test_crm_automation_ignores_bad_tenant():
    import app.workflows.crm_automation as ca
    # No client_id resolvable -> returns without error.
    asyncio.run(ca.crm_automation_handler({"event_type": "lead.created",
                                           "tenant_id": "bogus", "payload": {}}))


# --------------------------------------------------------------------------- #
# lead_scoring handler
# --------------------------------------------------------------------------- #
def test_lead_scoring_publishes_scored(monkeypatch):
    import app.agents.lead_scoring_handler as ls

    published = []

    async def fake_publish(event_type, tenant_id, entity_id, payload, source="system"):
        published.append((event_type, payload))
        return "evt"

    monkeypatch.setattr(ls.event_bus, "publish", fake_publish)

    with __import__("database").SessionLocal() as db:
        _clean(db, "sess_ls_1")
        db.add(Session(id="sess_ls_1", client_id=1, status="active"))
        lead = Lead(session_id="sess_ls_1", client_id=1, name="Buyer",
                    location="Wakad", budget="80L", property_type="2BHK")
        db.add(lead)
        db.commit()
        lead_id = lead.id
        env = {"event_type": "conversation.updated", "tenant_id": "Client_1",
               "entity_id": str(lead_id), "payload": {"lead_id": lead_id}}
        asyncio.run(ls.lead_scoring_handler(env))
        _clean(db, "sess_ls_1")

    assert published and published[0][0] == "lead.scored"
    assert "conversion_probability" in published[0][1]


# --------------------------------------------------------------------------- #
# marketing_agent (8.2)
# --------------------------------------------------------------------------- #
def test_marketing_agent_report(monkeypatch):
    import app.agents.marketing_agent as ma

    published = []

    async def fake_publish(event_type, tenant_id, entity_id, payload, source="system"):
        published.append((event_type, payload))
        return "evt"

    monkeypatch.setattr(ma.event_bus, "publish", fake_publish)
    asyncio.run(ma.marketing_agent_handler({"event_type": "cron.weekly_report",
                                            "tenant_id": "Client_1"}))
    assert published and published[0][0] == "marketing.report.generated"
    report = published[0][1]
    assert "segments" in report and "suggestions" in report
    assert set(report["suggestions"]) == {"hot", "warm", "cold"}


# --------------------------------------------------------------------------- #
# customer_success_agent (8.3)
# --------------------------------------------------------------------------- #
def test_customer_success_reminder(monkeypatch):
    import app.agents.customer_success_agent as cs

    submitted = {}

    async def fake_submit(req):
        submitted.update(req)
        return {"status": "success"}

    monkeypatch.setattr(cs, "ae_submit", fake_submit)
    asyncio.run(cs.customer_success_handler({"event_type": "booking.confirmed",
                                             "tenant_id": "Client_1", "entity_id": "42"}))
    assert submitted["action_type"] == "notify_agent"
    assert submitted["parameters"]["kind"] == "notify_admin"


# --------------------------------------------------------------------------- #
# competitor_monitor (8.4)
# --------------------------------------------------------------------------- #
def test_competitor_scan_matches(monkeypatch):
    import app.workflows.competitor_monitor as cm
    monkeypatch.setattr(settings, "COMPETITOR_KEYWORDS", "lodha,godrej")

    with __import__("database").SessionLocal() as db:
        _clean(db, "sess_cm_1")
        db.query(Client).filter(Client.id == 999).delete()
        db.commit()
        db.add(Client(id=999, company_name="TestCompany", email="test@test.com", hashed_password="fake", api_key="fake_key"))
        db.add(Session(id="sess_cm_1", client_id=999, status="active"))
        lead = Lead(session_id="sess_cm_1", client_id=999, name="Buyer",
                    location="Wakad", intent="comparing with Lodha towers",
                    conversion_status="open")
        db.add(lead)
        db.commit()
        client = db.query(Client).filter(Client.id == 999).first()
        envelopes = cm._scan_client(db, client)
        _clean(db, "sess_cm_1")
        db.query(Client).filter(Client.id == 999).delete()
        db.commit()

    assert any(e["event_type"] == "market.alert.generated" for e in envelopes)
    assert any("lodha" in e["payload"]["matches"] for e in envelopes)


def test_competitor_job_noop_without_keywords(monkeypatch):
    import app.workflows.competitor_monitor as cm
    monkeypatch.setattr(settings, "COMPETITOR_KEYWORDS", "")
    # Should return immediately without touching Redis.
    cm.competitor_monitor_job()


# --------------------------------------------------------------------------- #
# CalendarExecutor — stub fallback contract
# --------------------------------------------------------------------------- #
def test_calendar_executor_stub_fallback(monkeypatch):
    from app.execution_engine.calendar_executor import CalendarExecutor
    monkeypatch.setattr(settings, "GOOGLE_CALENDAR_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
    ex = CalendarExecutor()
    res = asyncio.run(ex.execute({"entity_id": "lead:1",
                                  "parameters": {"visit_date": "2026-08-01T10:00:00"}}))
    assert res["status"] == "success"
    assert res["visit_id"].startswith("visit_")
    assert res["provider"] == "stub"


# --------------------------------------------------------------------------- #
# GraphClient / KnowledgeGraph — safe when Neo4j unconfigured
# --------------------------------------------------------------------------- #
def test_graph_client_noop_when_unavailable():
    from app.clients.graph_client import GraphClient
    from app.knowledge_graph.neo4j_client import Neo4jClient
    from app.knowledge_graph.neo4j_kg import KnowledgeGraph

    c = Neo4jClient.__new__(Neo4jClient)
    c._driver = None
    c.available = False
    kg = KnowledgeGraph(client=c)
    assert kg.available is False
    gc = GraphClient(kg=kg)
    assert gc.get_lead_context(1, 1) == {}


def test_neo4j_client_health_unavailable():
    from app.knowledge_graph.neo4j_client import Neo4jClient

    c = Neo4jClient.__new__(Neo4jClient)
    c._driver = None
    c.available = False
    h = c.health()
    assert h["available"] is False
    assert c.migrate_schema()["migrated"] is False


# --------------------------------------------------------------------------- #
# Graph API routes (7.3) — mounted, health public, context tenant-scoped
# --------------------------------------------------------------------------- #
def test_graph_api_routes():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.api.events import router as events_router
    from app.knowledge_graph.graph_api import router as graph_router
    from database import Base, engine

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.api_key == "e11_key").first()
        if not client:
            client = Client(company_name="E11", email="e11@test.com",
                            hashed_password="x", api_key="e11_key",
                            is_active=True, subscription_status="inactive")
            db.add(client)
            db.commit()
    finally:
        db.close()

    app = FastAPI()
    app.include_router(events_router)
    app.include_router(graph_router)
    with TestClient(app) as tc:
        h = tc.get("/api/v1/graph/health")
        assert h.status_code == 200
        body = h.json()
        assert body.get("status") == "success"
        assert "available" in body  # True when local Neo4j is up; False when not
        # context: 401 without key, 404 for a non-owned/unknown lead
        assert tc.get("/api/v1/graph/leads/999999/context").status_code == 401
        r = tc.get("/api/v1/graph/leads/999999/context?api_key=e11_key")
        assert r.status_code == 404


# --------------------------------------------------------------------------- #
# n8n client — safe no-op when unconfigured (config-later)
# --------------------------------------------------------------------------- #
def test_n8n_not_configured():
    from app.automation_engine.n8n_client import N8NClient
    c = N8NClient(base_url="", api_key="")
    assert c.configured is False
    out = asyncio.run(c.trigger_workflow("wf1", {"x": 1}))
    assert out == {"status": "error", "error": "n8n_not_configured"}


def test_n8n_configured_flag():
    from app.automation_engine.n8n_client import N8NClient
    c = N8NClient(base_url="https://n8n.example.com", api_key="k")
    assert c.configured is True
