"""IREIOS 3.0 — Wave C: NegotiationAgent."""
from __future__ import annotations

import logging
from typing import Optional

from app.clients.event_bus_client import event_bus
from app.automation_engine.engine import submit as ae_submit
from database import SessionLocal

logger = logging.getLogger(__name__)

_EVENTS = ["lead.negotiation.started", "lead.negotiation.counter"]


def _resolve_client_id(tenant_id) -> Optional[int]:
    if tenant_id is None:
        return None
    s = str(tenant_id)
    if s.startswith("Client_"):
        s = s.split("_", 1)[1]
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


async def handler(envelope: dict) -> None:
    client_id = _resolve_client_id(envelope.get("tenant_id"))
    if client_id is None:
        return
    event_type = envelope.get("event_type")
    payload = envelope.get("payload") or {}
    lead_id = envelope.get("entity_id") or payload.get("lead_id")
    if lead_id is None:
        return
    try:
        lead_id = int(lead_id)
    except (ValueError, TypeError):
        return
    db = SessionLocal()
    try:
        from models import Lead as LeadModel
        lead = db.query(LeadModel).filter(LeadModel.id == lead_id, LeadModel.client_id == client_id).first()
        if lead is None:
            return
        budget_raw = (lead.budget or "").strip().lower()
        is_aligned = lead.budget_alignment_status in ("aligned", "excellent", "strong")
        needs_approval = not is_aligned and bool(budget_raw)
        if needs_approval:
            # Non-blocking: keep chatting (no HITL pause) but notify manager + n8n.
            await ae_submit({
                "action_type": "notify_agent",
                "tenant_id": f"Client_{client_id}",
                "entity_id": str(lead_id),
                "parameters": {
                    "kind": "notify_admin",
                    "lead_id": lead_id,
                    "message": f"Lead {lead_id} is open for negotiation (Budget: {budget_raw}). Flagged on dashboard.",
                },
                "source": "negotiation_agent",
            })
            # Fan-out to n8n WF-3 (approval.requested) without pausing the chat path.
            try:
                await event_bus.publish(
                    "approval.requested",
                    f"Client_{client_id}",
                    str(lead_id),
                    {
                        "approval_id": None,
                        "action_type": "negotiation.counter",
                        "entity_id": str(lead_id),
                        "name": lead.name or "",
                        "parameters_summary": {
                            "budget": budget_raw,
                            "lead_id": lead_id,
                            "trigger": "budget_misaligned",
                        },
                        "approve_path": f"/api/v1/leads/{lead_id}",
                        "reject_path": f"/api/v1/leads/{lead_id}",
                    },
                    source="negotiation_agent",
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("negotiation approval.requested publish skipped: %s", e)
        if event_type == "lead.negotiation.counter":
            try:
                await event_bus.publish(
                    "negotiation.counter.sent",
                    f"Client_{client_id}",
                    str(lead_id),
                    {"lead_id": lead_id, "counter": payload.get("counter", {})},
                    source="negotiation_agent",
                )
            except Exception as e:
                logger.warning("negotiation counter publish failed: %s", e)
    finally:
        db.close()


def register_negotiation(ceo) -> None:
    ceo.register_agent("negotiation_agent", handler, subscriptions=list(_EVENTS), status="active")
    logger.info("Registered negotiation_agent")
