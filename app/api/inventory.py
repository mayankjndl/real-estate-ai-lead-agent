"""IREIOS 4.0 — inventory twin layout API.

``GET /api/v1/inventory/twin`` — JWT, client-scoped hierarchical layout for the
Digital Twin page (project → towers → floors → units). Floor comes from
``meta_json.floor`` (zero-migrate MVP). Soft-empty when FEATURE_TWIN_LIVE=false
or no inventory rows.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_client
from config import settings
from database import get_db
from models import Client, InventoryUnit

logger = logging.getLogger("api.inventory")
router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

_STATUS_CANON = {
    "available": "available",
    "hold": "hold",
    "held": "hold",
    "sold": "sold",
    "reserved": "hold",
}


def _slug(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return s or "unknown"


def _floor_of(unit: InventoryUnit) -> int:
    meta = unit.meta_json if isinstance(unit.meta_json, dict) else {}
    raw = meta.get("floor")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    # Fallback: parse unit_code like A-101 → floor 1, A-1002 → floor 10
    code = unit.unit_code or ""
    m = re.search(r"-(\d+)$", code)
    if m:
        num = m.group(1)
        if len(num) >= 3:
            try:
                return int(num[:-2])  # 101 → 1, 1002 → 10
            except ValueError:
                pass
    return 0


def _norm_status(raw: Optional[str]) -> str:
    key = (raw or "available").strip().lower()
    return _STATUS_CANON.get(key, "available")


def _empty_twin(message: str = "Demo inventory layout") -> dict:
    return {
        "status": "success",
        "disclaimer": message,
        "available": False,
        "project": None,
        "towers": [],
        "counts": {"available": 0, "hold": 0, "sold": 0},
    }


def build_twin_payload(units: list[InventoryUnit], *, preferred_project: str = "The Summit") -> dict:
    """Group InventoryUnit rows into the frozen twin contract shape."""
    if not units:
        return _empty_twin()

    by_project: dict[str, list[InventoryUnit]] = defaultdict(list)
    for u in units:
        by_project[u.project_name or "Unknown"].append(u)

    project_name = preferred_project if preferred_project in by_project else next(iter(by_project))
    project_units = by_project[project_name]
    location = next((u.location for u in project_units if u.location), None)

    tower_map: dict[str, dict[int, list[InventoryUnit]]] = defaultdict(lambda: defaultdict(list))
    counts = {"available": 0, "hold": 0, "sold": 0}
    for u in project_units:
        tower_name = u.tower or "Tower"
        # Normalize short codes "A" → "Tower A"
        if len(tower_name) <= 2 and not tower_name.lower().startswith("tower"):
            tower_name = f"Tower {tower_name}"
        floor = _floor_of(u)
        tower_map[tower_name][floor].append(u)
        st = _norm_status(u.status)
        counts[st] = counts.get(st, 0) + 1

    towers_out: list[dict[str, Any]] = []
    for tower_name in sorted(tower_map.keys()):
        floors_dict = tower_map[tower_name]
        floors_out = []
        for level in sorted(floors_dict.keys()):
            level_units = sorted(floors_dict[level], key=lambda x: x.unit_code or "")
            floors_out.append({
                "level": level,
                "units": [
                    {
                        "id": f"unit:{u.id}",
                        "unit_number": u.unit_code,
                        "status": _norm_status(u.status),
                        "price": u.list_price,
                        "currency": "INR",
                        "bhk": u.bhk,
                        "lead_id": None,
                    }
                    for u in level_units
                ],
            })
        towers_out.append({
            "id": f"tw:{_slug(tower_name)}",
            "name": tower_name,
            "floors": floors_out,
        })

    return {
        "status": "success",
        "disclaimer": "Demo inventory layout",
        "available": True,
        "project": {
            "id": f"prj:{_slug(project_name)}",
            "name": project_name,
            "location": location or "",
        },
        "towers": towers_out,
        "counts": counts,
    }


@router.get("/twin")
def get_inventory_twin(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Hierarchical twin layout for Digital Twin (read-only)."""
    if not getattr(settings, "FEATURE_TWIN_LIVE", True):
        return _empty_twin("Twin live disabled (FEATURE_TWIN_LIVE=false)")

    units = (
        db.query(InventoryUnit)
        .filter(InventoryUnit.client_id == client.id)
        .all()
    )
    return build_twin_payload(units)
