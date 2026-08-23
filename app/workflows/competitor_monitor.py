"""IREIOS 3.0 — Phase 8.4: Competitor Monitor workflow (cron).

Scheduler job that scans each active client's recent lead text for configured
competitor keywords (`COMPETITOR_KEYWORDS`, no external network call) and
publishes `market.alert.generated` when a match is found.

Runs from the BackgroundScheduler (a worker thread), so it publishes to the
Redis Streams bus via a short-lived async connection inside `asyncio.run`
(the loop-bound `event_bus` singleton belongs to the app lifespan loop and
cannot be driven from a scheduler thread).
"""
from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.clients.event_bus_client import EventBusClient
from app.services.prediction_service import competitor_signals
from config import settings
from database import SessionLocal
from datetime import datetime, timezone

from models import Client, Lead, Message, NotificationLog

logger = logging.getLogger("competitor_monitor")


async def _publish(envelopes: list[dict]) -> None:
    """Publish envelopes via a fresh, short-lived Redis connection."""
    if not envelopes:
        return
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        for env in envelopes:
            await r.xadd(settings.EVENT_STREAM_KEY, {"data": json.dumps(env, default=str)})
    finally:
        try:
            await r.aclose()
        except Exception:  # noqa: BLE001
            pass


def _scan_client(db, client: Client) -> list[dict]:
    """Return market.alert envelopes for a client's recent lead activity."""
    keywords = getattr(settings, "COMPETITOR_KEYWORDS", "") or ""
    if not keywords.strip():
        return []
    leads = (
        db.query(Lead)
        .filter(Lead.client_id == client.id, Lead.conversion_status == "open")
        .limit(200)
        .all()
    )
    envelopes: list[dict] = []
    for lead in leads:
        text_parts = [lead.intent or "", lead.location or "", lead.property_type or ""]
        recent = (
            db.query(Message)
            .filter(Message.session_id == lead.session_id, Message.role == "user")
            .order_by(Message.id.desc())
            .limit(5)
            .all()
        )
        text_parts.extend(m.content or "" for m in recent)
        print("DEBUG TEXT PARTS INSIDE SCAN CLIENT:", text_parts)
        signal = competitor_signals(" ".join(text_parts))
        print("DEBUG SIGNAL INSIDE SCAN CLIENT:", signal)
        if signal["alert"]:
            envelopes.append(
                EventBusClient.build_envelope(
                    "market.alert.generated",
                    f"Client_{client.id}",
                    str(lead.id),
                    {"lead_id": lead.id, "matches": signal["matches"],
                     "monitored": signal["monitored"]},
                    source="competitor_monitor",
                )
            )
    return envelopes


def _write_notification(db, envelope: dict) -> None:
    """Write a NotificationLog row for a market alert."""
    tenant_id = envelope.get("tenant_id", "")
    payload = envelope.get("payload", {})
    lead_id = payload.get("lead_id")
    client_id = None
    if str(tenant_id).startswith("Client_"):
        try:
            client_id = int(tenant_id.split("_", 1)[1])
        except (ValueError, TypeError):
            pass
    if client_id and lead_id:
        try:
            log = NotificationLog(
                client_id=client_id,
                lead_id=lead_id,
                assigned_agent="manager",
                status="pending_ack",
                reason="competitor_alert",
                severity=2,
                escalate_at=datetime.now(timezone.utc),
            )
            db.add(log)
            db.commit()
        except Exception as e:  # noqa: BLE001
            db.rollback()
            logger.warning("failed to write competitor notification log: %s", e)


def _notify_for_envelopes(envelopes: list[dict]) -> None:
    """Write NotificationLog rows for each alert (sync, own session)."""
    if not envelopes:
        return
    db = SessionLocal()
    try:
        for env in envelopes:
            _write_notification(db, env)
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.warning("competitor notification batch failed: %s", e)
    finally:
        db.close()


def competitor_monitor_job() -> None:
    """Scheduler entry point: scan all active clients, publish alerts."""
    keywords = getattr(settings, "COMPETITOR_KEYWORDS", "") or ""
    if not keywords.strip():
        logger.debug("competitor_monitor: no COMPETITOR_KEYWORDS configured; skip")
        return
    db = SessionLocal()
    envelopes: list[dict] = []
    try:
        clients = db.query(Client).filter(Client.is_active.is_(True)).all()
        for client in clients:
            try:
                envelopes.extend(_scan_client(db, client))
            except Exception as e:  # noqa: BLE001 - isolate per client
                logger.warning("competitor scan failed for client %s: %s", client.id, e)
    finally:
        db.close()
    if envelopes:
        _notify_for_envelopes(envelopes)
        try:
            asyncio.run(_publish(envelopes))
            logger.info("competitor_monitor published %d market alerts", len(envelopes))
        except Exception as e:  # noqa: BLE001
            logger.error("competitor_monitor publish failed: %s", e)
