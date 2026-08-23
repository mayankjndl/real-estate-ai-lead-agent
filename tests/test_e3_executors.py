"""Expansion Phase 3 — WhatsApp & CRM executors (Tasks 3.1–3.4).

Tracks Step 12 (Expansion Phase 3). Exercises the WhatsApp/CRM/calendar/
notification executors and their registration in the Execution Engine, plus the
success event map.

See plans/IREIOS_3.0_EXPANSION_CHANGELOG.md (Phase 3 status).
"""
import asyncio
import json

import pytest

from app.execution_engine.base_executor import BaseExecutor, NoopExecutor
from app.execution_engine.calendar_executor import CalendarExecutor
from app.execution_engine.crm_executor import CRMExecutor
from app.execution_engine.execution_engine import ExecutionEngine, execution_engine
from app.execution_engine.notification_executor import NotificationExecutor
from app.execution_engine.registry import register_executors
from app.execution_engine.whatsapp_executor import WhatsAppExecutor, get_twilio_client
from config import settings
from models import ApprovalRequest  # noqa: F401 (ensure importability)


# --------------------------------------------------------------------------- #
# Task 3.1 — WhatsAppExecutor
# --------------------------------------------------------------------------- #
def test_whatsapp_executor_registered():
    register_executors()
    assert "send_whatsapp" in execution_engine._executors
    assert execution_engine._event_map.get("send_whatsapp") == "whatsapp.sent"


def test_whatsapp_test_mode_success(monkeypatch):
    monkeypatch.setattr(settings, "TEST_MODE", True)

    async def run():
        ex = WhatsAppExecutor()
        return await ex.execute({
            "action_type": "send_whatsapp",
            "tenant_id": "Client_1",
            "entity_id": "sess_1",
            "parameters": {"phone": "+919999999999", "message": "Hi there"},
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert res["mode"] == "test"
    assert res["to"] == "whatsapp:+919999999999"


def test_whatsapp_missing_phone_errors():
    async def run():
        ex = WhatsAppExecutor()
        return await ex.execute({
            "action_type": "send_whatsapp",
            "tenant_id": "Client_1",
            "entity_id": "sess_1",
            "parameters": {"message": "Hi"},
        })

    res = asyncio.run(run())
    assert res["status"] == "error"
    assert "phone" in res["error"]


def test_whatsapp_media_url_accepted(monkeypatch):
    """media_url must be forwarded to the Twilio create call."""
    captured = {}

    class _Msg:
        sid = "SM123"

    class _Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Msg()

    class _Client:
        def __init__(self, *a, **k):
            self.messages = _Messages()

    monkeypatch.setattr("twilio.rest.Client", _Client)
    monkeypatch.setattr(settings, "TEST_MODE", False)
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "tok")
    monkeypatch.setattr(settings, "TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
    monkeypatch.setattr(settings, "WEBHOOK_BASE_URL", "")

    async def run():
        ex = WhatsAppExecutor()
        return await ex.execute({
            "action_type": "send_whatsapp",
            "tenant_id": "Client_1",
            "entity_id": "sess_1",
            "parameters": {
                "phone": "+919999999999",
                "message": "Brochure",
                "media_url": "https://x/b.pdf",
            },
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert captured["media_url"] == ["https://x/b.pdf"]
    assert captured["to"] == "whatsapp:+919999999999"


def test_whatsapp_not_configured_errors(monkeypatch):
    monkeypatch.setattr("app.execution_engine.whatsapp_executor.get_twilio_client", lambda: None)
    monkeypatch.setattr(settings, "TEST_MODE", False)

    async def run():
        ex = WhatsAppExecutor()
        return await ex.execute({
            "action_type": "send_whatsapp",
            "tenant_id": "Client_1",
            "entity_id": "sess_1",
            "parameters": {"phone": "+919999999999", "message": "Hi"},
        })

    res = asyncio.run(run())
    assert res["status"] == "error"
    assert res["error"] == "twilio_not_configured"


# --------------------------------------------------------------------------- #
# Task 3.2 — CRMExecutor (mock httpx push)
# --------------------------------------------------------------------------- #
def test_crm_executor_registered():
    register_executors()
    assert "update_crm" in execution_engine._executors
    assert execution_engine._event_map.get("update_crm") == "lead.crm_synced"


def test_crm_push_raw_success(monkeypatch):
    import crm_sync

    monkeypatch.setattr(crm_sync, "CRM_API_URL", "https://crm.example.com/contacts")
    monkeypatch.setattr(crm_sync, "CRM_API_KEY", "real-key")
    monkeypatch.setattr(crm_sync.settings, "FEATURE_HUBSPOT_LIVE", True)

    class _Resp:
        status_code = 200

        def json(self):
            return {"id": "ext-123"}

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

    monkeypatch.setattr("httpx.AsyncClient", _Client)

    async def run():
        ex = CRMExecutor()
        return await ex.execute({
            "action_type": "update_crm",
            "tenant_id": "Client_1",
            "entity_id": "lead_1",
            "parameters": {"properties": {"firstname": "A", "phone": "+91"}},
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert res["external_id"] == "ext-123"


def test_crm_push_retries_on_429(monkeypatch):
    """HubSpot 429 must raise CRMAPIError and tenacity must retry (>=2 calls)."""
    calls = {"n": 0}

    class _Resp:
        status_code = 429

        def json(self):
            return {}

        def raise_for_status(self):
            raise RuntimeError("429")

        @property
        def response(self):
            return self

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, *a, **k):
            calls["n"] += 1
            return _Resp()

    monkeypatch.setattr("httpx.AsyncClient", _Client)
    # demo sim / FEATURE_HUBSPOT_LIVE=false would short-circuit; force live path
    import crm_sync

    monkeypatch.setattr(crm_sync, "CRM_API_URL", "https://crm.example.com/contacts")
    monkeypatch.setattr(crm_sync, "CRM_API_KEY", "real-key")
    monkeypatch.setattr(crm_sync.settings, "FEATURE_HUBSPOT_LIVE", True)

    async def run():
        ex = CRMExecutor()
        return await ex.execute({
            "action_type": "update_crm",
            "tenant_id": "Client_1",
            "entity_id": "lead_1",
            "parameters": {"properties": {"firstname": "A"}},
        })

    res = asyncio.run(run())
    assert res["status"] == "error"
    assert calls["n"] >= 2  # tenacity retried


# --------------------------------------------------------------------------- #
# Task 3.3 — Calendar + Notification executors
# --------------------------------------------------------------------------- #
def test_calendar_executor_success(monkeypatch):
    from config import settings as _settings

    # Stub path must stay deterministic even when local .env has real GCal.
    monkeypatch.setattr(_settings, "GOOGLE_CALENDAR_ID", "")
    monkeypatch.setattr(_settings, "GOOGLE_CALENDAR_CREDENTIALS_JSON", "")

    async def run():
        ex = CalendarExecutor()
        return await ex.execute({
            "action_type": "schedule_visit",
            "tenant_id": "Client_1",
            "entity_id": "lead_1",
            "parameters": {"visit_date": "2026-08-01T10:00:00Z"},
        })

    res = asyncio.run(run())
    assert res["status"] == "success"
    assert res["visit_id"].startswith("visit_")
    assert res["visit_date"] == "2026-08-01T10:00:00Z"
    assert res.get("provider") == "stub"


def test_notification_executor_unknown_kind_errors():
    async def run():
        ex = NotificationExecutor()
        return await ex.execute({
            "action_type": "notify_agent",
            "tenant_id": "Client_1",
            "entity_id": "lead_1",
            "parameters": {"kind": "bogus"},
        })

    res = asyncio.run(run())
    assert res["status"] == "error"


# --------------------------------------------------------------------------- #
# Task 3.4 — EE dispatch via registered executors + DLQ on unknown
# --------------------------------------------------------------------------- #
def test_ee_dispatch_unknown_action_dlq():
    sink = []
    ee = ExecutionEngine(session_factory=lambda: _SinkSession(sink), bus=None)
    ee.register("noop", NoopExecutor())

    async def run():
        return await ee.dispatch({"action_type": "does_not_exist", "tenant_id": "Client_1", "entity_id": "e"})

    res = asyncio.run(run())
    assert res["status"] == "error"
    assert res["error"] == "no_executor"
    # EE writes a DLQEvent row on failure
    assert len(sink) >= 1
    assert sink[0].__class__.__name__ == "DLQEvent"


class _SinkSession:
    def __init__(self, sink):
        self.sink = sink

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def add(self, o):
        self.sink.append(o)

    def commit(self):
        pass

    def close(self):
        pass
