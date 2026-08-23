"""IREIOS 4.0 — inventory twin API + seed shape (P4-3). Mostly DB-free."""
from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import inventory as inv
from models import InventoryUnit


def test_build_twin_payload_groups_floors():
    units = [
        InventoryUnit(
            id=1,
            client_id=1,
            project_name="The Summit",
            tower="Tower A",
            unit_code="A-101",
            bhk="3",
            list_price=15_000_000,
            status="available",
            location="Downtown",
            meta_json={"floor": 1},
        ),
        InventoryUnit(
            id=2,
            client_id=1,
            project_name="The Summit",
            tower="Tower A",
            unit_code="A-102",
            bhk="2",
            list_price=12_000_000,
            status="Hold",
            location="Downtown",
            meta_json={"floor": 1},
        ),
        InventoryUnit(
            id=3,
            client_id=1,
            project_name="The Summit",
            tower="Tower B",
            unit_code="B-201",
            bhk="4",
            list_price=20_000_000,
            status="sold",
            location="Downtown",
            meta_json={"floor": 2},
        ),
    ]
    payload = inv.build_twin_payload(units)
    assert payload["available"] is True
    assert payload["project"]["name"] == "The Summit"
    assert payload["counts"]["available"] == 1
    assert payload["counts"]["hold"] == 1
    assert payload["counts"]["sold"] == 1
    tower_names = {t["name"] for t in payload["towers"]}
    assert "Tower A" in tower_names and "Tower B" in tower_names
    a = next(t for t in payload["towers"] if t["name"] == "Tower A")
    assert a["floors"][0]["level"] == 1
    assert a["floors"][0]["units"][0]["currency"] == "INR"
    assert a["floors"][0]["units"][0]["status"] == "available"


def test_build_twin_empty():
    out = inv.build_twin_payload([])
    assert out["available"] is False
    assert out["towers"] == []
    assert out["counts"]["available"] == 0


def test_twin_endpoint_flag_off(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_TWIN_LIVE", False)
    app = FastAPI()
    app.include_router(inv.router)
    app.dependency_overrides[inv.get_current_client] = lambda: SimpleNamespace(id=1)

    def _db():
        yield None

    app.dependency_overrides[inv.get_db] = _db
    try:
        r = TestClient(app).get("/api/v1/inventory/twin")
        assert r.status_code == 200
        body = r.json()
        assert body["available"] is False
        assert body["towers"] == []
    finally:
        app.dependency_overrides.clear()


def test_twin_endpoint_with_units(monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "FEATURE_TWIN_LIVE", True)
    units = []
    for tower, letter in (("Tower A", "A"), ("Tower B", "B")):
        for floor in range(1, 11):
            for u in (1, 2):
                units.append(
                    InventoryUnit(
                        id=len(units) + 1,
                        client_id=1,
                        project_name="The Summit",
                        tower=tower,
                        unit_code=f"{letter}-{floor}0{u}",
                        bhk="3",
                        list_price=15_000_000,
                        status="available" if u == 1 else "sold",
                        location="Downtown",
                        meta_json={"floor": floor},
                    )
                )
    assert len(units) == 40

    class _Q:
        def filter(self, *a, **k):
            return self

        def all(self):
            return units

    class _Db:
        def query(self, *a, **k):
            return _Q()

    app = FastAPI()
    app.include_router(inv.router)
    app.dependency_overrides[inv.get_current_client] = lambda: SimpleNamespace(id=1)

    def _db():
        yield _Db()

    app.dependency_overrides[inv.get_db] = _db
    try:
        r = TestClient(app).get("/api/v1/inventory/twin")
        assert r.status_code == 200
        body = r.json()
        assert body["project"]["name"] == "The Summit"
        n = sum(len(f["units"]) for t in body["towers"] for f in t["floors"])
        assert n == 40
    finally:
        app.dependency_overrides.clear()


def test_seed_twin_demo_script_shape():
    """seed_twin_demo builds 40 unit specs (no live DB)."""
    from seed_twin_demo import FLOORS, PROJECT, TOWERS, UNITS_PER_FLOOR

    assert PROJECT == "The Summit"
    assert len(TOWERS) == 2
    assert list(FLOORS) == list(range(1, 11))
    assert UNITS_PER_FLOOR == 2
    assert len(TOWERS) * len(list(FLOORS)) * UNITS_PER_FLOOR == 40


def test_feature_flags_on_settings():
    from config import settings

    assert hasattr(settings, "FEATURE_GRAPH_VIZ")
    assert hasattr(settings, "FEATURE_TWIN_LIVE")
    assert hasattr(settings, "FEATURE_HUBSPOT_LIVE")


def test_inventory_router_mounted_in_main():
    from pathlib import Path

    src = Path("main.py").read_text(encoding="utf-8")
    assert "inventory_router" in src
    assert "app.api.inventory" in src
