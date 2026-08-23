import asyncio
import logging
import os
import re

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import settings
from database import SessionLocal
from metrics import BACKGROUND_FAILURE_COUNT, INTEGRATION_FAILURES, SCHEDULER_JOB_DURATION
from models import Lead, DLQEvent

logger = logging.getLogger("crm_sync")
logging.basicConfig(level=logging.INFO)

# Dummy HubSpot CRM API settings (Using a generic placeholder URL for demo)
CRM_API_URL = os.getenv("CRM_API_URL", "https://api.hubapi.com/crm/v3/objects/contacts")
CRM_API_KEY = os.getenv("CRM_API_KEY", "demo-hubspot-key")

# P5.2: extended property map. These are the custom HubSpot properties pushed
# only when CRM_SYNC_EXTENDED_PROPERTIES is enabled (portal may not define all).
_EXTENDED_CRM_PROPERTIES = (
    "location",
    "intent",
    "property_type",
    "visit_date",
    "assignee",
    "budget_alignment_status",
    "urgency_level",
    "engagement_score",
    "lead_temperature",
)

# Fields that constitute a usable CRM identity. P5.3 guards against marking a
# lead "success" when these are still missing after the create-time poll.
_IDENTITY_FIELDS = ("phone", "name")


class CRMAPIError(Exception):
    """Custom exception to trigger retries for transient HTTP errors."""
    pass


def _rejected_property_from_4xx(exc) -> str | None:
    """Best-effort parse of a HubSpot 4xx body to find the unknown property."""
    try:
        body = exc.response.json()
    except Exception:
        return None

    # HubSpot structured error: body["errors"][0]["context"]["propertyName"]
    errors = body.get("errors", [])
    if errors and isinstance(errors[0], dict):
        ctx = errors[0].get("context", {})
        prop_names = ctx.get("propertyName", [])
        if prop_names:
            return prop_names[0]

    msg = body.get("message", "") if isinstance(body, dict) else ""
    for pattern in [
        r"[Pp]roperty ['\"]?([a-zA-Z0-9_.]+)['\"]? does not exist",
        r"[Uu]nknown property[: ]+['\"]?([a-zA-Z0-9_.]+)['\"]?",
        r"[Ii]nvalid value for property ['\"]?([a-zA-Z0-9_.]+)['\"]?",
        r"[Uu]nknown property name[: ]+['\"]?([a-zA-Z0-9_.]+)['\"]?",
        r"[Nn]o such property ['\"]?([a-zA-Z0-9_.]+)['\"]?",
    ]:
        match = re.search(pattern, msg)
        if match:
            return match.group(1)
    return None


def should_retry(exception):
    """Determine if we should retry based on the exception."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Retry on Rate Limit (429) or Server Errors (5xx)
        return exception.response.status_code == 429 or exception.response.status_code >= 500
    return isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout, CRMAPIError))


def build_crm_properties(lead, include_extended: bool = True) -> dict:
    """
    P5.2 (pure): construct the HubSpot `properties` object for a lead.

    Always includes the base contact identity. When `include_extended` is True
    (gated by settings.CRM_SYNC_EXTENDED_PROPERTIES) the richer map is added.
    """
    props = {
        "firstname": lead.name or "Unknown",
        "phone": lead.phone or "",
        "budget": lead.budget or "",
        "lifecyclestage": "lead",
    }
    if include_extended:
        for field in _EXTENDED_CRM_PROPERTIES:
            # `assignee` is stored on the lead as `assigned_agent`.
            attr = "assigned_agent" if field == "assignee" else field
            value = getattr(lead, attr, None)
            if value is None:
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            props[field] = str(value)
    return props


def decide_crm_status_after_poll(lead) -> str:
    """
    P5.3 (pure): decide the sync status once the create-time poll completes.

    If the lead still lacks a usable identity (phone/name), we must NOT report
    "success" — leave it `pending` so a later field update (P5.1) re-syncs.
    """
    for field in _IDENTITY_FIELDS:
        if getattr(lead, field, None):
            return "success"
    return "pending"


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((httpx.RequestError, CRMAPIError)),
    reraise=True
)
async def _push_to_hubspot(payload: dict, external_id: str | None = None) -> dict:
    """Makes the actual HTTP request to HubSpot with tenacity backoff logic.

    When ``external_id`` is provided (lead already synced once) the request is a
    PATCH to the existing contact so we UPDATE instead of creating duplicates.
    """
    headers = {
        "Authorization": f"Bearer {CRM_API_KEY}",
        "Content-Type": "application/json"
    }

    # --- PRODUCTION SAFETY CHECK ---
    if settings.IS_PRODUCTION and CRM_API_KEY == "demo-hubspot-key":
        raise RuntimeError("CRITICAL: Production HubSpot credentials not configured. Set CRM_API_URL and CRM_API_KEY.")
    # --------------------------------------

    # --- DEMO / FLAG-OFF STUB ---
    # FEATURE_HUBSPOT_LIVE=false keeps demo stub even if a key is present (safe default).
    # Live path requires flag + non-demo key. Identity match: email + phone (ops/Piyush).
    hubspot_live = bool(getattr(settings, "FEATURE_HUBSPOT_LIVE", False))
    is_demo_key = CRM_API_KEY == "demo-hubspot-key"
    if not hubspot_live or is_demo_key:
        if not settings.IS_PRODUCTION:
            import uuid
            return {"id": str(uuid.uuid4()), "stub": True, "hubspot_live": hubspot_live}
        if is_demo_key:
            raise RuntimeError(
                "CRITICAL: Production HubSpot credentials not configured. "
                "Set CRM_API_URL, CRM_API_KEY, and FEATURE_HUBSPOT_LIVE=true."
            )
    # --------------------------------------

    async with httpx.AsyncClient() as client:
        logger.info(f"Syncing to CRM: {payload}")

        if external_id:
            url = f"{CRM_API_URL}/{external_id}"
            method = client.patch
        else:
            url = CRM_API_URL
            method = client.post

        response = await method(url, json=payload, headers=headers, timeout=10.0)

        if response.status_code in [429, 500, 502, 503, 504]:
            raise CRMAPIError(f"CRM returned transient error {response.status_code}")

        # P5.2: a 4xx for an unknown custom property is recoverable — strip it
        # and retry in a loop until success or no more parseable rejections.
        if 400 <= response.status_code < 500:
            logger.warning(f"CRM 400 response body: {response.text}")
            for _strip_attempt in range(10):
                rejected = _rejected_property_from_4xx(response)
                if not rejected or rejected not in payload["properties"]:
                    break
                logger.warning(f"CRM rejected property '{rejected}'; retrying without it.")
                payload["properties"].pop(rejected, None)
                response = await method(url, json=payload, headers=headers, timeout=10.0)
                if response.status_code in [429, 500, 502, 503, 504]:
                    raise CRMAPIError(f"CRM returned transient error {response.status_code}")
                if response.status_code < 400:
                    return response.json()

        response.raise_for_status()
        return response.json()


async def _sync_lead_to_crm_async(lead_id: int, resync: bool = False):
    """
    Core async CRM sync. See `sync_lead_to_crm` for the public wrapper.
    """
    with SessionLocal() as db:
        try:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                logger.error(f"CRM Sync failed: Lead ID {lead_id} not found.")
                return

            include_extended = settings.CRM_SYNC_EXTENDED_PROPERTIES

            # P5.3: create-time poll for agent.py / ingest to finish writing the
            # lead's identity before the first push. Skipped on re-sync.
            if not resync:
                for attempt in range(10):
                    db.refresh(lead)
                    if lead.phone and lead.name:
                        break
                    await asyncio.sleep(0.5)

            payload = {
                "properties": build_crm_properties(lead, include_extended=include_extended)
            }

            # Attempt to push to CRM
            try:
                response_data = await _push_to_hubspot(payload, external_id=lead.external_crm_id)

                external_id = response_data.get("id")
                if external_id:
                    lead.external_crm_id = external_id
                    # P5.3: never mark success when identity is still empty.
                    lead.crm_sync_status = decide_crm_status_after_poll(lead)
                    if resync:
                        lead.crm_resync_pending = False
                    db.commit()
                    logger.info(
                        f"Synced Lead {lead_id} to CRM. External ID: {external_id} "
                        f"| status={lead.crm_sync_status}"
                    )
                else:
                    lead.crm_sync_status = "failed"
                    if resync:
                        lead.crm_resync_pending = False
                    db.commit()
                    logger.error(f"CRM Sync succeeded but no ID returned for Lead {lead_id}: {response_data}")

            except Exception as e:
                logger.error(f"CRM Sync permanently failed for Lead {lead_id} after retries: {e}")
                lead.crm_sync_status = "failed"
                if resync:
                    # Keep pending=True so the next job run retries the update.
                    lead.crm_resync_pending = True
                BACKGROUND_FAILURE_COUNT.labels(component="crm").inc()
                INTEGRATION_FAILURES.labels(integration="crm").inc()

                # Phase 2 Hardening: Dead-Letter Queue integration
                dlq_entry = DLQEvent(
                    target_endpoint="hubspot_crm",
                    payload=payload,
                    error_trace=str(e),
                    status="pending",
                    client_id=lead.client_id
                )
                db.add(dlq_entry)
                db.commit()

        except Exception as outer_e:
            logger.error(f"Unexpected error in CRM sync for lead {lead_id}: {outer_e}")


def sync_lead_to_crm(lead_id: int, resync: bool = False):
    """
    Public wrapper. Safe to call from an async context (fire-and-forget via
    asyncio.create_task) OR from a synchronous scheduler thread (APScheduler
    runs jobs in worker threads; no running loop there).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        return asyncio.create_task(_sync_lead_to_crm_async(lead_id, resync=resync))
    return asyncio.run(_sync_lead_to_crm_async(lead_id, resync=resync))


def crm_resync_job():
    """
    P5.1: debounced re-sync scheduler. Picks up leads that were already synced
    once (have an external id) but had meaningful field changes after create
    time, and re-pushes them without re-polling or spamming on every turn.
    """
    _JOB = "crm_resync_job"
    db = SessionLocal()
    try:
        with SCHEDULER_JOB_DURATION.labels(job_name=_JOB).time():
            pending = db.query(Lead).filter(
                Lead.external_crm_id.isnot(None),
                Lead.crm_sync_status == "success",
                Lead.crm_resync_pending == True,  # noqa: E712
            ).all()
            for lead in pending:
                logger.info(f"P5.1 CRM re-sync for lead {lead.id} (client {lead.client_id}).")
                sync_lead_to_crm(lead.id, resync=True)
    except Exception as e:
        logger.error(f"CRM re-sync job failed: {e}")
    finally:
        db.close()
