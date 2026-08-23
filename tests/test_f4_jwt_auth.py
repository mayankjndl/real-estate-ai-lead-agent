"""IREIOS 4.0 — Command Center JWT auth unification (P4-QA prep).

Covers the shared JWT resolution added in ``auth.py``:

- ``get_current_client`` accepts ``Authorization: Bearer <jwt>`` **or** the
  HttpOnly ``jwt`` cookie (digital twin / predictions browser fetches).
- ``get_events_client`` accepts X-API-Key, Bearer JWT, or cookie JWT
  (knowledge-graph neighborhood / copilot ego server actions).

DB-free: fake session objects back the auth + handler queries.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import inventory as inv
from app.knowledge_graph import graph_api as ga
from auth import (
    _client_from_jwt_token,
    create_access_token,
    resolve_jwt_from_request,
)
from models import Client, Lead

CLIENT_ID = 1


class _FakeClient:
    id = CLIENT_ID
    is_active = True


# --------------------------------------------------------------------------- #
# Fake DB helpers
# --------------------------------------------------------------------------- #
class _FakeQ:
    def __init__(self, model, *, lead=None, client=None):
        self._model = model
        self._lead = lead
        self._client = client

    def filter(self, *a, **k):
        return self

    def first(self):
        if self._model is Client:
            return self._client if self._client is not None else _FakeClient()
        return self._lead

    def all(self):
        return []


class _FakeDb:
    def __init__(self, lead=None):
        self._lead = lead

    def query(self, model):
        return _FakeQ(model, lead=self._lead)


def _token() -> str:
    return create_access_token({"sub": str(CLIENT_ID)})


# --------------------------------------------------------------------------- #
# Unit: helpers
# --------------------------------------------------------------------------- #
def test_resolve_jwt_prefers_bearer_over_cookie():
    class _Req:
        def __init__(self, cookie_value):
            self.cookies = {"jwt": cookie_value}

    req = _Req("cookie-jwt")
    assert resolve_jwt_from_request(req, "bearer-jwt") == "bearer-jwt"
    assert resolve_jwt_from_request(req, None) == "cookie-jwt"
    assert resolve_jwt_from_request(_Req(None), None) is None


def test_client_from_jwt_token_returns_active_client():
    client = _client_from_jwt_token(_token(), _FakeDb())
    assert client.id == CLIENT_ID


def test_client_from_jwt_token_rejects_garbage_token():
    with pytest.raises(HTTPException) as ei:
        _client_from_jwt_token("not.a.jwt", _FakeDb())
    assert ei.value.status_code == 401


def test_client_from_jwt_token_rejects_non_numeric_sub():
    with pytest.raises(HTTPException) as ei:
        _client_from_jwt_token(create_access_token({"sub": "abc"}), _FakeDb())
    assert ei.value.status_code == 401


def test_client_from_jwt_token_rejects_inactive_client():
    inactive = SimpleNamespace(id=CLIENT_ID, is_active=False)

    class _Q(_FakeQ):
        def first(self):
            return inactive

    class _Db:
        def query(self, model):
            return _Q(model)

    with pytest.raises(HTTPException) as ei:
        _client_from_jwt_token(_token(), _Db())
    assert ei.value.status_code == 401


# --------------------------------------------------------------------------- #
# get_current_client (twin endpoint): Bearer / cookie / none
# --------------------------------------------------------------------------- #
def _twin_app(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_TWIN_LIVE", True)
    app = FastAPI()
    app.include_router(inv.router)

    def _db():
        yield _FakeDb()

    app.dependency_overrides[inv.get_db] = _db
    return TestClient(app)


def test_twin_bearer_jwt_ok(monkeypatch):
    client = _twin_app(monkeypatch)
    try:
        r = client.get(
            "/api/v1/inventory/twin", headers={"Authorization": f"Bearer {_token()}"}
        )
        assert r.status_code == 200
        assert r.json()["status"] == "success"
    finally:
        client.app.dependency_overrides.clear()


def test_twin_cookie_jwt_ok(monkeypatch):
    client = _twin_app(monkeypatch)
    try:
        r = client.get("/api/v1/inventory/twin", cookies={"jwt": _token()})
        assert r.status_code == 200
        assert r.json()["status"] == "success"
    finally:
        client.app.dependency_overrides.clear()


def test_twin_no_auth_401(monkeypatch):
    client = _twin_app(monkeypatch)
    try:
        r = client.get("/api/v1/inventory/twin")
        assert r.status_code == 401
    finally:
        client.app.dependency_overrides.clear()


def test_twin_invalid_jwt_401(monkeypatch):
    client = _twin_app(monkeypatch)
    try:
        r = client.get(
            "/api/v1/inventory/twin", headers={"Authorization": "Bearer garbage"}
        )
        assert r.status_code == 401
    finally:
        client.app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# get_events_client (neighborhood): API key / Bearer / cookie / none
# --------------------------------------------------------------------------- #
def _neighborhood_app(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_GRAPH_VIZ", False)
    lead = Lead(id=10, client_id=CLIENT_ID, name="Auth Lead")
    app = FastAPI()
    app.include_router(ga.router)

    def _db():
        yield _FakeDb(lead=lead)

    app.dependency_overrides[ga.get_db] = _db
    return TestClient(app)


def test_neighborhood_bearer_jwt_ok(monkeypatch):
    client = _neighborhood_app(monkeypatch)
    try:
        r = client.get(
            "/api/v1/graph/neighborhood?lead_id=10",
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert r.status_code == 200
        assert r.json()["lead_id"] == 10
    finally:
        client.app.dependency_overrides.clear()


def test_neighborhood_cookie_jwt_ok(monkeypatch):
    client = _neighborhood_app(monkeypatch)
    try:
        r = client.get(
            "/api/v1/graph/neighborhood?lead_id=10", cookies={"jwt": _token()}
        )
        assert r.status_code == 200
    finally:
        client.app.dependency_overrides.clear()


def test_neighborhood_api_key_ok(monkeypatch):
    client = _neighborhood_app(monkeypatch)
    try:
        r = client.get(
            "/api/v1/graph/neighborhood?lead_id=10",
            headers={"X-API-Key": "wave-test-key-1"},
        )
        assert r.status_code == 200
    finally:
        client.app.dependency_overrides.clear()


def test_neighborhood_no_auth_401(monkeypatch):
    client = _neighborhood_app(monkeypatch)
    try:
        r = client.get("/api/v1/graph/neighborhood?lead_id=10")
        assert r.status_code == 401
    finally:
        client.app.dependency_overrides.clear()