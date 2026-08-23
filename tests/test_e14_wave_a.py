"""Wave A — close dead loops + AE template dispatch + producers.

Plan: plans/IREIOS_3.0_WAVE_A_D_EXPANSION.md §1
Changelog: plans/IREIOS_3.0_WAVE_A_D_CHANGELOG.md

A.1 + A.2 implemented. A.3/A.4/A.5 skeletons remain until later sub-phases.
"""
from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key-wave-a")

from config import settings
from models import Client, Lead, Message, Session


def _clean(db, sid):
    db.query(Message).filter(Message.session_id == sid).delete()
    db.query(Lead).filter(Lead.session_id == sid).delete()
    db.query(Session).filter(Session.id == sid).delete()
    db.commit()


def _db_ok() -> bool:
    try:
        from database import SessionLocal
        db = SessionLocal()
        db.query(Client).first()
        db.close()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# A.1 — weekly marketing cron publishes cron.weekly_report
# --------------------------------------------------------------------------- #
def test_weekly_marketing_cron_publishes_per_client(monkeypatch):
    """A.1: cron job publishes one cron.weekly_report envelope per active client."""
    if not _db_ok():
        pytest.skip("requires Postgres")
    from app.workflows.weekly_marketing_cron import weekly_marketing_cron_job
    from tests.conftest import ensure_test_client

    ensure_test_client(1)

    published = []

    def fake_publish(envelopes):
        published.extend(envelopes)
        return

    import app.workflows.weekly_marketing_cron as wmc
    monkeypatch.setattr(wmc, "_publish_envelopes", fake_publish)

    weekly_marketing_cron_job()

    assert len(published) >= 1, "expected at least one active client event"
    for env in published:
        assert env["event_type"] == "cron.weekly_report"
        assert env["tenant_id"].startswith("Client_")
        assert env["entity_id"] == "marketing"


def test_marketing_agent_still_emits_report_on_weekly_event(monkeypatch):
    """A.1 parity: marketing_agent_handler still publishes marketing.report.generated."""
    if not _db_ok():
        pytest.skip("requires Postgres")
    from app.agents.marketing_agent import marketing_agent_handler

    published = []

    async def fake_publish(event_type, tenant_id, entity_id, payload, source="system"):
        published.append((event_type, tenant_id, payload))
        return "evt"

    import app.agents.marketing_agent as ma
    monkeypatch.setattr(ma.event_bus, "publish", fake_publish)

    envelope = {
        "event_type": "cron.weekly_report",
        "tenant_id": "Client_1",
        "entity_id": "marketing",
        "payload": {"source": "scheduler"},
    }
    asyncio.run(marketing_agent_handler(envelope))

    assert any(e[0] == "marketing.report.generated" for e in published)
    _, t_id, payload = published[0]
    assert t_id == "Client_1"
    assert "segments" in payload
    assert "suggestions" in payload


# --------------------------------------------------------------------------- #
# A.2 — lifecycle producers
# --------------------------------------------------------------------------- #
def test_lifecycle_inject_booking_confirmed_wakes_cs(monkeypatch):
    """A.2: lifecycle inject booking.confirmed triggers CS ae_submit."""
    if not _db_ok():
        pytest.skip("requires Postgres")
    from app.agents.customer_success_agent import customer_success_handler

    submitted = []

    async def fake_submit(req):
        submitted.append(req)
        return {"status": "success"}

    import app.agents.customer_success_agent as cs
    monkeypatch.setattr(cs, "ae_submit", fake_submit)
    
    async def mock_resolve_lead_phone(lead_id):
        return None
    monkeypatch.setattr(cs, "_resolve_lead_phone", mock_resolve_lead_phone)

    envelope = {
        "event_type": "booking.confirmed",
        "tenant_id": "Client_1",
        "entity_id": "99",
        "payload": {"lead_id": 99},
    }
    asyncio.run(customer_success_handler(envelope))

    assert len(submitted) >= 1
    assert submitted[0]["action_type"] == "notify_agent"


def test_lifecycle_inject_rejects_bad_event_type(monkeypatch):
    """A.2: unknown event_type returns 400."""
    from fastapi.testclient import TestClient
    import main as main_mod
    from config import settings
    monkeypatch.setattr(settings, "ADMIN_API_KEY", os.environ["ADMIN_API_KEY"])
    client = TestClient(main_mod.app)

    resp = client.post(
        "/api/v1/lifecycle/events",
        json={"event_type": "invalid_type", "lead_id": 1},
        headers={"X-Admin-Token": os.environ["ADMIN_API_KEY"]},
    )
    assert resp.status_code == 400
    assert "Invalid event_type" in resp.text


def test_lifecycle_inject_unknown_lead_returns_404(monkeypatch):
    """A.2: non-existent lead returns 404."""
    from fastapi.testclient import TestClient
    import main as main_mod
    from config import settings
    monkeypatch.setattr(settings, "ADMIN_API_KEY", os.environ["ADMIN_API_KEY"])
    client = TestClient(main_mod.app)

    resp = client.post(
        "/api/v1/lifecycle/events",
        json={"event_type": "booking.confirmed", "lead_id": 999999},
        headers={"X-Admin-Token": os.environ["ADMIN_API_KEY"]},
    )
    assert resp.status_code == 404
    assert "not found" in resp.text.lower()


# --------------------------------------------------------------------------- #
# A.3 — AE template_type dispatch
# --------------------------------------------------------------------------- #
def _fake_session_factory(sink):
    class _S:
        def __init__(self):
            self.sink = sink
        def add(self, o):
            self.sink.append(o)
        def commit(self):
            pass
        def close(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            self.close()
    return lambda: _S()


def test_ae_n8n_template_unconfigured_returns_clean_error(monkeypatch):
    """A.3: template_type=n8n without workflow_id returns error."""
    from app.automation_engine.engine import submit
    from app.execution_engine.execution_engine import ExecutionEngine
    from app.execution_engine.base_executor import NoopExecutor
    import app.automation_engine.engine as eng

    sink = []
    ee = ExecutionEngine(session_factory=_fake_session_factory(sink), bus=None)
    ee.register("send_whatsapp", NoopExecutor())
    orig = eng.execution_engine
    eng.execution_engine = ee
    try:
        res = asyncio.run(submit({
            "action_type": "send_whatsapp",
            "template_type": "n8n",
            "tenant_id": "Client_1",
            "entity_id": "e",
            "parameters": {},
        }))
        assert res["status"] == "error"
        assert "workflow_id" in res.get("error", "")
    finally:
        eng.execution_engine = orig


def test_ae_n8n_template_calls_client_when_configured(monkeypatch):
    """A.3: template_type=n8n with configured n8n succeeds."""
    from app.automation_engine.engine import submit
    from app.execution_engine.execution_engine import ExecutionEngine
    from app.execution_engine.base_executor import NoopExecutor
    import app.automation_engine.engine as eng
    import app.automation_engine.n8n_client as nc
    from config import settings

    monkeypatch.setattr(settings, "N8N_BASE_URL", "http://n8n:5678")
    monkeypatch.setattr(settings, "N8N_API_KEY", "test-key")

    class _Resp:
        status_code = 200
        content = b'{"ok":true}'
        def json(self):
            return {"ok": True}
        def raise_for_status(self):
            pass

    class _Client:
        def __init__(self, *a, **k):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            return False
        async def post(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(nc.httpx, "AsyncClient", _Client)

    sink = []
    ee = ExecutionEngine(session_factory=_fake_session_factory(sink), bus=None)
    ee.register("send_whatsapp", NoopExecutor())
    orig = eng.execution_engine
    eng.execution_engine = ee
    try:
        res = asyncio.run(submit({
            "action_type": "send_whatsapp",
            "template_type": "n8n",
            "tenant_id": "Client_1",
            "entity_id": "e",
            "parameters": {"workflow_id": "wf1"},
        }))
        assert res["status"] == "success"
        assert res.get("workflow_id") == "wf1"
    finally:
        eng.execution_engine = orig
        monkeypatch.undo()  # restore n8n settings


def test_ae_langgraph_template_reaches_execute_or_fallback(monkeypatch):
    """A.3: template_type=langgraph runs or falls back to linear EE."""
    from app.automation_engine.engine import submit
    from app.execution_engine.execution_engine import ExecutionEngine
    from app.execution_engine.base_executor import NoopExecutor
    import app.automation_engine.engine as eng

    sink = []
    ee = ExecutionEngine(session_factory=_fake_session_factory(sink), bus=None)
    ee.register("send_whatsapp", NoopExecutor())
    orig = eng.execution_engine
    eng.execution_engine = ee
    try:
        res = asyncio.run(submit({
            "action_type": "send_whatsapp",
            "template_type": "langgraph",
            "tenant_id": "Client_1",
            "entity_id": "e",
            "parameters": {"message": "hello"},
        }))
        # langgraph runner marks ready_to_execute then falls back to EE
        assert res["status"] == "success"
    finally:
        eng.execution_engine = orig


def test_ae_linear_default_unchanged(monkeypatch):
    """A.3 regression: default linear path still hits EE dispatch."""
    from app.automation_engine.engine import submit
    from app.execution_engine.execution_engine import ExecutionEngine
    from app.execution_engine.base_executor import NoopExecutor
    import app.automation_engine.engine as eng

    sink = []
    ee = ExecutionEngine(session_factory=_fake_session_factory(sink), bus=None)
    ee.register("noop", NoopExecutor())
    orig = eng.execution_engine
    eng.execution_engine = ee
    try:
        res = asyncio.run(submit({
            "action_type": "noop",
            "tenant_id": "Client_1",
            "entity_id": "e",
            "parameters": {},
        }))
        assert res["status"] == "success"
    finally:
        eng.execution_engine = orig


# --------------------------------------------------------------------------- #
# A.4 — expire_stale_approvals
# --------------------------------------------------------------------------- #
def test_expire_stale_approvals_marks_old_pending():
    """A.4: expire_stale_approvals marks old pending requests as expired."""
    from app.automation_engine.engine import expire_stale_approvals
    from database import SessionLocal
    from models import ApprovalRequest
    from datetime import datetime, timezone, timedelta
    from uuid import uuid4
    from tests.conftest import ensure_test_client

    cid = ensure_test_client(1)
    entity = f"e_expire_{uuid4()}"
    with SessionLocal() as db:
        old = ApprovalRequest(
            client_id=cid,
            entity_id=entity,
            action_type="test",
            action_payload={},
            status="pending",
            created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        )
        db.add(old)
        db.commit()
        db.refresh(old)
        old_id = old.id

    try:
        expired = expire_stale_approvals(max_age_hours=24)
        assert expired >= 1
        with SessionLocal() as db:
            row = db.query(ApprovalRequest).filter(ApprovalRequest.id == old_id).first()
            assert row is not None
            assert row.status == "expired"
            assert row.resolved_at is not None
    finally:
        with SessionLocal() as db:
            db.query(ApprovalRequest).filter(ApprovalRequest.entity_id == entity).delete()
            db.commit()


def test_expire_approvals_job_registered_in_scheduler():
    """A.4: main scheduler has expire_approvals job."""
    import main as main_mod
    assert hasattr(main_mod, "scheduler")
    job_ids = [j.id for j in main_mod.scheduler.get_jobs()]
    assert "expire_approvals" in job_ids


# --------------------------------------------------------------------------- #
# A.5 — NotificationExecutor admin / manager
# --------------------------------------------------------------------------- #
def test_notify_admin_invokes_outbound_not_log_only(monkeypatch):
    """A.5: notify_admin resolves manager phone and calls WhatsApp executor."""
    from app.execution_engine.notification_executor import NotificationExecutor

    sent = []

    async def fake_send(to, body, source="test"):
        sent.append({"to": to, "body": body, "source": source})
        return {"status": "success"}

    import app.execution_engine.notification_executor as ne
    monkeypatch.setattr(ne, "_resolve_manager_phone", lambda cid: "+919999999999")
    monkeypatch.setattr("app.execution_engine.outbound.send_whatsapp_via_executor", fake_send)

    exc = NotificationExecutor()

    async def run():
        return await exc.execute({
            "action_type": "notify_agent",
            "tenant_id": "Client_1",
            "parameters": {"kind": "notify_admin", "message": "Test admin message"},
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert "sent_to" in res


def test_notify_admin_logs_when_no_manager():
    """A.5: notify_admin without manager phone falls back to log."""
    from app.execution_engine.notification_executor import NotificationExecutor
    import app.execution_engine.notification_executor as ne

    orig = ne._resolve_manager_phone
    ne._resolve_manager_phone = lambda cid: None
    try:
        exc = NotificationExecutor()

        async def run():
            return await exc.execute({
                "action_type": "notify_agent",
                "tenant_id": "Client_1",
                "parameters": {"kind": "notify_admin", "message": "Test"},
            })

        res = asyncio.run(run())
        assert res["status"] == "success"
        assert "logged only" in res.get("note", "")
    finally:
        ne._resolve_manager_phone = orig


def test_manager_approval_kind_notifies_manager(monkeypatch):
    """A.5: manager_approval sends WhatsApp to manager."""
    from app.execution_engine.notification_executor import NotificationExecutor

    sent = []

    async def fake_send(to, body, source="test"):
        sent.append({"to": to, "body": body, "source": source})
        return {"status": "success"}

    import app.execution_engine.notification_executor as ne
    monkeypatch.setattr(ne, "_resolve_manager_phone", lambda cid: "+919999999999")
    monkeypatch.setattr("app.execution_engine.outbound.send_whatsapp_via_executor", fake_send)

    exc = NotificationExecutor()

    async def run():
        return await exc.execute({
            "action_type": "notify_agent",
            "tenant_id": "Client_1",
            "parameters": {
                "kind": "manager_approval",
                "approval_id": 42,
                "entity_id": "e1",
                "reason": "Discount > 5%",
            },
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert "sent_to" in res
    assert len(sent) >= 1
    assert "Approval" in sent[0]["body"]
