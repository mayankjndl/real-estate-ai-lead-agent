"""IREIOS 3.0 — Phase 7.3: Graph API routes (tenant-scoped).

Mounted at ``/api/v1/graph``:

- ``GET  /health``               — driver availability + schema version (no data).
- ``GET  /leads/{id}/context``   — graph context for a lead (tenant-scoped, 404
                                    if not owned by the caller's client).
- ``GET  /neighborhood``         — IREIOS 4.0 ego graph {nodes,edges} for FE.
- ``POST /upsert``               — admin/service-gated node upsert.

Neo4j down => health reports unavailable and context returns an empty graph
(Postgres remains the source of truth). Reuses the events-API auth so both the
API key and the FE JWT cookie work.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.events import get_events_client, _verify_admin_key
from app.clients.graph_client import graph_client
from app.knowledge_graph.neo4j_client import neo4j_client
from app.knowledge_graph.neo4j_kg import knowledge_graph
from config import settings
from database import get_db
from models import Client, Lead

logger = logging.getLogger("graph_api")

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])

_TEMP_COLORS = {
    "hot": "#ef4444",
    "warm": "#f59e0b",
    "cold": "#3b82f6",
}
_AGENT_COLOR = "#8b5cf6"
_AI_SUMMARY = "Ego network: center lead, assigned agent, and similar leads."


def _empty_neighborhood(lead_id: int) -> dict:
    return {
        "status": "success",
        "available": False,
        "lead_id": lead_id,
        "data": {"nodes": [], "edges": []},
        "ai_summary": _AI_SUMMARY,
    }


def _temp_color(temperature: str | None) -> str:
    return _TEMP_COLORS.get((temperature or "cold").lower(), _TEMP_COLORS["cold"])


def _title_temp(temperature: str | None) -> str:
    t = (temperature or "cold").strip().lower()
    return {"hot": "Hot", "warm": "Warm", "cold": "Cold"}.get(t, t.title() or "Cold")


def _lead_node(lead: Lead, *, center: bool = False) -> dict:
    temp = _title_temp(lead.lead_temperature)
    score = lead.conversion_probability
    try:
        score_val = int(score) if score is not None else 0
    except (TypeError, ValueError):
        score_val = 0
    return {
        "id": f"lead:{lead.id}",
        "label": "Lead",
        "node_type": "lead",
        "properties": {
            "name": lead.name or f"Lead {lead.id}",
            "phone": lead.phone or "",
            "location": lead.location or "",
            "score": score_val,
            "temperature": temp,
            "lead_id": lead.id,
            "funnel_stage": lead.funnel_stage or "",
            "property_type": lead.property_type or "",
        },
        "val": 24 if center else 16,
        "color": _temp_color(lead.lead_temperature),
    }


def _agent_node(name: str) -> dict:
    return {
        "id": f"agent:{name}",
        "label": "Agent",
        "node_type": "agent",
        "properties": {"name": name, "role": "Assigned Agent"},
        "val": 18,
        "color": _AGENT_COLOR,
    }


@router.get("/health")
async def graph_health():
    """Neo4j connectivity + schema version. No tenant data exposed."""
    return {"status": "success", **neo4j_client.health()}


@router.get("/neighborhood")
async def graph_neighborhood(
    lead_id: int = Query(..., description="Center lead id"),
    limit: int = Query(25, ge=1, le=50),
    client: Client = Depends(get_events_client),
    db: Session = Depends(get_db),
):
    """IREIOS 4.0 ego neighborhood for Sales Copilot embed.

    Soft-fails (HTTP 200, available=false) when Neo4j is down or FEATURE_GRAPH_VIZ=false.
    """
    t0 = time.perf_counter()
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.client_id == client.id).first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    if not getattr(settings, "FEATURE_GRAPH_VIZ", True) or not graph_client.available:
        return _empty_neighborhood(lead_id)

    nodes: list[dict] = []
    edges: list[dict] = []
    nodes.append(_lead_node(lead, center=True))
    seen_leads = {lead.id}

    agent_name = None
    try:
        agent_name = knowledge_graph.get_assigned_agent(lead_id, client.id)
    except Exception as e:  # noqa: BLE001
        logger.warning("neighborhood assigned_agent degraded: %s", e)
    if not agent_name:
        agent_name = lead.assigned_agent
    if agent_name:
        nodes.append(_agent_node(agent_name))
        edges.append({
            "source": f"lead:{lead.id}",
            "target": f"agent:{agent_name}",
            "type": "ASSIGNED_TO",
            "properties": {},
        })

    similar_rows: list[dict] = []
    try:
        similar_rows = knowledge_graph.get_similar_leads(lead_id, client.id, limit=limit) or []
    except Exception as e:  # noqa: BLE001
        logger.warning("neighborhood similar_leads degraded: %s", e)

    similar_ids = []
    for row in similar_rows:
        try:
            sid = int(row.get("lead_id"))
        except (TypeError, ValueError):
            continue
        if sid in seen_leads:
            continue
        seen_leads.add(sid)
        similar_ids.append(sid)

    if similar_ids:
        peers = (
            db.query(Lead)
            .filter(Lead.client_id == client.id, Lead.id.in_(similar_ids))
            .all()
        )
        peer_by_id = {p.id: p for p in peers}
        for sid in similar_ids:
            peer = peer_by_id.get(sid)
            if peer is None:
                # Graph-only stub when PG row missing
                row = next((r for r in similar_rows if int(r.get("lead_id") or 0) == sid), {})
                temp = _title_temp(row.get("lead_temperature"))
                nodes.append({
                    "id": f"lead:{sid}",
                    "label": "Lead",
                    "node_type": "stub",
                    "properties": {
                        "name": f"Lead {sid}",
                        "score": 0,
                        "temperature": temp,
                        "lead_id": sid,
                    },
                    "val": 16,
                    "color": _temp_color(row.get("lead_temperature")),
                })
            else:
                nodes.append(_lead_node(peer, center=False))
            edges.append({
                "source": f"lead:{lead.id}",
                "target": f"lead:{sid}",
                "type": "SIMILAR_TO",
                "properties": {"strength": 0.72},
            })

    elapsed_ms = (time.perf_counter() - t0) * 1000
    if elapsed_ms > 200:
        logger.info("graph.neighborhood soft-latency %.0fms lead_id=%s", elapsed_ms, lead_id)

    return {
        "status": "success",
        "available": True,
        "lead_id": lead_id,
        "data": {"nodes": nodes, "edges": edges},
        "ai_summary": _AI_SUMMARY,
    }


@router.get("/leads/{lead_id}/context")
async def graph_lead_context(
    lead_id: int,
    client: Client = Depends(get_events_client),
    db: Session = Depends(get_db),
):
    """Graph context for a lead, tenant-scoped (404 if not owned)."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.client_id == client.id).first()
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    context = graph_client.get_lead_context(lead_id, client.id)
    return {
        "lead_id": lead_id,
        "available": graph_client.available,
        "context": context,
    }


@router.post("/upsert")
async def graph_upsert(request: Request, db: Session = Depends(get_db)):
    """Admin/service-gated Lead node upsert.

    Body: ``{"lead_id": int, "client_id": int, "props": {...},
    "agent_name"?: str}``.
    """
    _verify_admin_key(request)
    body = await request.json()
    lead_id = body.get("lead_id")
    client_id = body.get("client_id")
    if lead_id is None or client_id is None:
        raise HTTPException(status_code=422, detail="lead_id and client_id are required")
    if not knowledge_graph.available:
        return {"status": "skipped", "reason": "graph_unavailable"}
    knowledge_graph.upsert_lead(int(lead_id), int(client_id), body.get("props") or {})
    agent_name = body.get("agent_name")
    if agent_name:
        knowledge_graph.link_lead_agent(int(lead_id), str(agent_name), int(client_id))
    return {"status": "success", "lead_id": lead_id}
