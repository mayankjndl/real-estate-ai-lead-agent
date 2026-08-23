"""IREIOS 4.0 — FEATURE_HUBSPOT_LIVE gate on CRM push (P4-4)."""
from __future__ import annotations

import asyncio


def test_hubspot_stub_when_flag_false(monkeypatch):
    import crm_sync

    monkeypatch.setattr(crm_sync.settings, "FEATURE_HUBSPOT_LIVE", False)
    monkeypatch.setattr(crm_sync.settings, "IS_PRODUCTION", False)
    monkeypatch.setattr(crm_sync, "CRM_API_KEY", "demo-hubspot-key")

    out = asyncio.run(crm_sync._push_to_hubspot({"properties": {"firstname": "x"}}))
    assert "id" in out
    assert out.get("stub") is True
    assert out.get("hubspot_live") is False


def test_hubspot_stub_when_flag_false_even_with_real_looking_key(monkeypatch):
    import crm_sync

    monkeypatch.setattr(crm_sync.settings, "FEATURE_HUBSPOT_LIVE", False)
    monkeypatch.setattr(crm_sync.settings, "IS_PRODUCTION", False)
    monkeypatch.setattr(crm_sync, "CRM_API_KEY", "pat-not-demo")
    monkeypatch.setattr(
        crm_sync, "CRM_API_URL", "https://api.hubapi.com/crm/v3/objects/contacts"
    )

    out = asyncio.run(crm_sync._push_to_hubspot({"properties": {"firstname": "x"}}))
    assert out.get("stub") is True


def test_env_example_documents_flags():
    from pathlib import Path

    text = Path(".env.example").read_text(encoding="utf-8")
    assert "FEATURE_GRAPH_VIZ" in text
    assert "FEATURE_TWIN_LIVE" in text
    assert "FEATURE_HUBSPOT_LIVE" in text
