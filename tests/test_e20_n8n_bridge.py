"""n8n bus→webhook bridge — delivery path for ops workflows (Gmail-first)."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.automation_engine.n8n_bridge import (
    DEFAULT_WEBHOOK_MAP,
    N8NBridge,
    parse_webhook_map,
)


def test_default_webhook_map_catalog_only():
    assert "lead.hot" in DEFAULT_WEBHOOK_MAP
    assert "lead.escalated" not in DEFAULT_WEBHOOK_MAP  # alias — avoid double Gmail
    assert "site_visit.scheduled" in DEFAULT_WEBHOOK_MAP
    assert "lead.qualified" in DEFAULT_WEBHOOK_MAP
    assert "approval.requested" in DEFAULT_WEBHOOK_MAP
    assert DEFAULT_WEBHOOK_MAP["lead.hot"] == "ireios_hot_lead_alert"


def test_parse_webhook_map_empty_uses_defaults():
    m = parse_webhook_map("")
    assert m == DEFAULT_WEBHOOK_MAP


def test_parse_webhook_map_json_override():
    raw = json.dumps({"lead.hot": "custom_hot", "lead.qualified": "custom_crm"})
    m = parse_webhook_map(raw)
    assert m["lead.hot"] == "custom_hot"
    assert m["lead.qualified"] == "custom_crm"
    assert "site_visit.scheduled" not in m


def test_parse_webhook_map_invalid_falls_back():
    m = parse_webhook_map("not-json{")
    assert m == DEFAULT_WEBHOOK_MAP


def test_forward_envelope_posts_full_envelope():
    captured = {}

    class FakeClient:
        configured = True

        async def trigger_workflow(self, workflow_id, payload):
            captured["id"] = workflow_id
            captured["payload"] = payload
            return {"status": "success", "workflow_id": workflow_id}

    bridge = N8NBridge(n8n_client=FakeClient())
    env = {
        "event_id": "e1",
        "event_type": "lead.hot",
        "tenant_id": "Client_1",
        "entity_id": "42",
        "payload": {"name": "Demo", "trigger": "hot_threshold"},
    }
    out = asyncio.run(bridge.forward_envelope(env))
    assert out["status"] == "success"
    assert captured["id"] == "ireios_hot_lead_alert"
    assert captured["payload"]["event_type"] == "lead.hot"
    assert captured["payload"]["payload"]["name"] == "Demo"


def test_forward_envelope_skips_unmapped():
    bridge = N8NBridge(webhook_map={"lead.hot": "ireios_hot_lead_alert"}, n8n_client=MagicMock())
    out = asyncio.run(
        bridge.forward_envelope({"event_type": "conversation.updated", "payload": {}})
    )
    assert out["status"] == "skipped"


def test_handle_message_acks_unmapped(monkeypatch):
    acked = []

    class FakeRedis:
        async def xack(self, stream, group, msg_id):
            acked.append(msg_id)

    bridge = N8NBridge(webhook_map={"lead.hot": "ireios_hot_lead_alert"})
    bridge._redis = FakeRedis()
    env = {"event_type": "lead.scored", "payload": {}}
    fields = {"data": json.dumps(env)}
    asyncio.run(bridge._handle_message("1-0", fields))
    assert acked == ["1-0"]


def test_handle_message_acks_when_n8n_unconfigured():
    acked = []

    class FakeRedis:
        async def xack(self, stream, group, msg_id):
            acked.append(msg_id)

    class Unconf:
        configured = False

    bridge = N8NBridge(
        webhook_map={"lead.hot": "ireios_hot_lead_alert"},
        n8n_client=Unconf(),
    )
    bridge._redis = FakeRedis()
    env = {
        "event_type": "lead.hot",
        "event_id": "x",
        "payload": {"trigger": "hot_threshold"},
    }
    asyncio.run(bridge._handle_message("2-0", {"data": json.dumps(env)}))
    assert acked == ["2-0"]


def test_handle_message_forwards_and_acks_on_success():
    acked = []
    calls = []

    class FakeRedis:
        async def xack(self, stream, group, msg_id):
            acked.append(msg_id)

    class OkClient:
        configured = True

        async def trigger_workflow(self, workflow_id, payload):
            calls.append((workflow_id, payload))
            return {"status": "success", "workflow_id": workflow_id}

    bridge = N8NBridge(
        webhook_map={"lead.hot": "ireios_hot_lead_alert"},
        n8n_client=OkClient(),
    )
    bridge._redis = FakeRedis()
    env = {
        "event_id": "e9",
        "event_type": "lead.hot",
        "tenant_id": "Client_1",
        "entity_id": "9",
        "payload": {"name": "A", "trigger": "human_handoff"},
    }
    asyncio.run(bridge._handle_message("3-0", {"data": json.dumps(env)}))
    assert acked == ["3-0"]
    assert calls[0][0] == "ireios_hot_lead_alert"
    assert calls[0][1]["payload"]["trigger"] == "human_handoff"


def test_handle_message_acks_4xx_permanent():
    acked = []

    class FakeRedis:
        async def xack(self, stream, group, msg_id):
            acked.append(msg_id)

    class Client404:
        configured = True

        async def trigger_workflow(self, workflow_id, payload):
            return {"status": "error", "error": "n8n_http_404"}

    bridge = N8NBridge(
        webhook_map={"lead.hot": "ireios_hot_lead_alert"},
        n8n_client=Client404(),
    )
    bridge._redis = FakeRedis()
    env = {"event_type": "lead.hot", "payload": {}}
    asyncio.run(bridge._handle_message("4-0", {"data": json.dumps(env)}))
    assert acked == ["4-0"]


def test_handle_message_leaves_pel_on_retryable():
    acked = []

    class FakeRedis:
        async def xack(self, stream, group, msg_id):
            acked.append(msg_id)

    class Client503:
        configured = True

        async def trigger_workflow(self, workflow_id, payload):
            return {"status": "error", "error": "n8n_unreachable"}

    bridge = N8NBridge(
        webhook_map={"lead.hot": "ireios_hot_lead_alert"},
        n8n_client=Client503(),
    )
    bridge._redis = FakeRedis()
    env = {"event_type": "lead.hot", "payload": {}}
    asyncio.run(bridge._handle_message("5-0", {"data": json.dumps(env)}))
    assert acked == []  # leave in PEL


def test_start_noop_when_disabled(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "N8N_BRIDGE_ENABLED", False)
    bridge = N8NBridge()
    asyncio.run(bridge.start())
    assert bridge._running is False
    assert bridge._task is None


def test_bridge_docs_and_gmail_recipes_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    integ = (root / "docs" / "N8N_INTEGRATION.md").read_text(encoding="utf-8")
    plan = (root / "plans" / "phase3" / "N8N_LIVE_WORKFLOWS_PLAN.md").read_text(encoding="utf-8")
    assert "ireios-n8n" in integ
    assert "n8n_bridge" in integ
    assert "Gmail" in integ or "gmail" in integ.lower()
    assert "ireios_hot_lead_alert" in integ
    assert "ireios_hot_lead_alert" in plan
    assert "Gmail" in plan


def test_lifespan_references_n8n_bridge():
    from pathlib import Path

    src = (Path(__file__).resolve().parent.parent / "main.py").read_text(encoding="utf-8")
    assert "n8n_bridge" in src
    assert "n8n_bridge.start" in src or "await n8n_bridge.start()" in src
