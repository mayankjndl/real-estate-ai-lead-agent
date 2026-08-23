"""IREIOS 4.0 — GET /api/v1/graph/neighborhood (P4-2). DB-free with mocks."""
from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.knowledge_graph import graph_api as ga
from models import Lead


def _make_app(client_obj, lead_or_none):
    app = FastAPI()
    app.include_router(ga.router)
    app.dependency_overrides[ga.get_events_client] = lambda: client_obj

    class _Q:
        def filter(self, *a, **k):
            return self

        def first(self):
            return lead_or_none

        def all(self):
            return []

    class _Db:
        def query(self, *a, **k):
            return _Q()

    def _db():
        yield _Db()

    app.dependency_overrides[ga.get_db] = _db
    return app


def test_neighborhood_404_when_lead_missing():
    app = _make_app(SimpleNamespace(id=1), None)
    try:
        r = TestClient(app).get("/api/v1/graph/neighborhood?lead_id=999")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_neighborhood_soft_empty_when_flag_off(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_GRAPH_VIZ", False)
    lead = Lead(
        id=10,
        client_id=1,
        name="X",
        lead_temperature="hot",
        conversion_probability=80,
    )
    app = _make_app(SimpleNamespace(id=1), lead)
    try:
        r = TestClient(app).get("/api/v1/graph/neighborhood?lead_id=10")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert body["data"]["nodes"] == []
        assert body["data"]["edges"] == []
        assert "ai_summary" in body
    finally:
        app.dependency_overrides.clear()


def test_neighborhood_soft_empty_when_neo4j_down(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_GRAPH_VIZ", True)
    monkeypatch.setattr(ga, "graph_client", SimpleNamespace(available=False))
    lead = Lead(id=11, client_id=1, name="Y")
    app = _make_app(SimpleNamespace(id=1), lead)
    try:
        r = TestClient(app).get("/api/v1/graph/neighborhood?lead_id=11")
        assert r.status_code == 200
        assert r.json()["available"] is False
    finally:
        app.dependency_overrides.clear()


def test_neighborhood_builds_ego_when_graph_available(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_GRAPH_VIZ", True)
    monkeypatch.setattr(ga, "graph_client", SimpleNamespace(available=True))

    center = Lead(
        id=100,
        client_id=1,
        name="Center",
        lead_temperature="hot",
        conversion_probability=88,
        assigned_agent="Jane",
    )
    peer = Lead(
        id=200,
        client_id=1,
        name="Peer",
        lead_temperature="warm",
        conversion_probability=60,
    )

    class _Q:
        def __init__(self):
            self._ids = None

        def filter(self, *a, **k):
            # detect Lead.id.in_(...) vs ownership filter via crude check
            return self

        def first(self):
            return center

        def all(self):
            return [peer]

    class _Db:
        def query(self, model):
            return _Q()

    monkeypatch.setattr(
        ga.knowledge_graph,
        "get_assigned_agent",
        lambda lid, cid: "Jane",
    )
    monkeypatch.setattr(
        ga.knowledge_graph,
        "get_similar_leads",
        lambda lid, cid, limit=25: [
            {"lead_id": 200, "location": "Wakad", "lead_temperature": "warm"}
        ],
    )

    app = FastAPI()
    app.include_router(ga.router)
    app.dependency_overrides[ga.get_events_client] = lambda: SimpleNamespace(id=1)

    def _db():
        yield _Db()

    app.dependency_overrides[ga.get_db] = _db
    try:
        r = TestClient(app).get("/api/v1/graph/neighborhood?lead_id=100&limit=10")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is True
        ids = {n["id"] for n in body["data"]["nodes"]}
        assert "lead:100" in ids
        assert "agent:Jane" in ids
        assert "lead:200" in ids
        types = {e["type"] for e in body["data"]["edges"]}
        assert "ASSIGNED_TO" in types
        assert "SIMILAR_TO" in types
        center_node = next(n for n in body["data"]["nodes"] if n["id"] == "lead:100")
        props = center_node["properties"]
        assert "phone" in props
        assert "location" in props
        assert props["name"] == "Center"
        center_node = next(n for n in body["data"]["nodes"] if n["id"] == "lead:100")
        assert center_node["color"] == "#ef4444"
        assert center_node["properties"]["temperature"] == "Hot"
    finally:
        app.dependency_overrides.clear()


def test_lead_node_helpers():
    lead = Lead(
        id=7,
        name="X",
        lead_temperature="cold",
        conversion_probability=12,
    )
    node = ga._lead_node(lead, center=True)
    assert node["id"] == "lead:7"
    assert node["color"] == "#3b82f6"
    assert ga._agent_node("Bob")["id"] == "agent:Bob"


def test_route_registered_in_source():
    from pathlib import Path

    src = Path("app/knowledge_graph/graph_api.py").read_text(encoding="utf-8")
    assert '/neighborhood"' in src or "/neighborhood" in src
    assert "FEATURE_GRAPH_VIZ" in src
