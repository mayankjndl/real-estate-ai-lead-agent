"""IREIOS 3.0 — Phase 3.2 CRM Executor.

Ports the HubSpot push logic (currently in root ``crm_sync.py``) into an
Execution-Engine executor so CRM writes flow through ``AE -> EE -> Event``.

The executor intentionally reuses the existing ``crm_sync`` helpers
(``build_crm_properties``, ``decide_crm_status_after_poll``, ``_push_to_hubspot``)
so CRM behavior stays identical during the dual-path window. Phase 10 will
thin-wrap ``crm_sync`` into this executor and retire the direct callers.

Runtime: ``Event -> CEO -> Agent/Workflow -> Automation Engine -> Execution Engine -> Event``.
"""
from __future__ import annotations

import logging
from typing import Any

from app.execution_engine.base_executor import BaseExecutor
from config import settings
from database import SessionLocal
from models import Lead

logger = logging.getLogger("executor.crm")

# Reuse the proven CRM helpers rather than copy them (Phase 10 decommissions
# the direct callers; until then the single source of truth stays in crm_sync).
from crm_sync import (  # noqa: E402
    _push_to_hubspot,
    build_crm_properties,
    decide_crm_status_after_poll,
)


class CRMExecutor(BaseExecutor):
    """Syncs a lead (or raw properties) to the configured CRM.

    ``parameters`` (one of):
        - ``lead_id`` (int): load the lead, build properties, push, and update
          ``external_crm_id`` / ``crm_sync_status`` on the lead row.
        - ``properties`` (dict): push an already-built property map.
        - ``client_id`` (int, optional): tenant scoping for DLQ/status.

    On success publishes ``lead.crm_synced`` via the Execution Engine event map.
    """

    action_type = "update_crm"

    async def execute(self, action_request: dict) -> dict:
        params = action_request.get("parameters", {}) or {}
        lead_id = params.get("lead_id")
        raw_props = params.get("properties")

        if lead_id is not None:
            return await self._sync_lead(int(lead_id))
        if raw_props:
            return await self._push_raw(raw_props)
        return {"status": "error", "error": "update_crm requires 'lead_id' or 'properties'"}

    async def _push_raw(self, properties: dict) -> dict:
        payload = {"properties": properties}
        try:
            result = await _push_to_hubspot(payload)
            external_id = (result or {}).get("id")
            return {
                "status": "success",
                "external_id": external_id,
                "crm_sync_status": "success",
            }
        except Exception as exc:  # noqa: BLE001 - EE captures into DLQ
            logger.error("CRM raw push failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def _sync_lead(self, lead_id: int) -> dict:
        with SessionLocal() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if lead is None:
                return {"status": "error", "error": f"lead {lead_id} not found"}
            try:
                props = build_crm_properties(lead, include_extended=settings.CRM_SYNC_EXTENDED_PROPERTIES)
                payload = {"properties": props}
                result = await _push_to_hubspot(payload, external_id=lead.external_crm_id)
                external_id = (result or {}).get("id")
                lead.external_crm_id = external_id
                lead.crm_sync_status = decide_crm_status_after_poll(lead)
                db.commit()
                return {
                    "status": "success",
                    "external_id": external_id,
                    "crm_sync_status": lead.crm_sync_status,
                    "lead_id": lead_id,
                }
            except Exception as exc:  # noqa: BLE001 - EE captures into DLQ
                logger.error("CRM lead sync failed for %s: %s", lead_id, exc)
                try:
                    lead.crm_sync_status = "failed"
                    db.commit()
                except Exception:  # noqa: BLE001
                    pass
                return {"status": "error", "error": str(exc)}
