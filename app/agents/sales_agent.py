"""IREIOS 3.0 — Phase 6 + Wave B.1/B.2: Sales AI agent + CEO bus + objections.

`SalesAgent` turns qualification output into a recommended next-best sales
action and (optionally) advances the deal stage and syncs the lead to the CRM
through the AutomationEngine -> ExecutionEngine (so CRM writes are observable
and DLQ-protected, reusing the Phase 3 `CRMExecutor`).

Wave B.1: registered on the CEO bus (``lead.scored``, ``lead.hot``, ``conversation.updated``, ``lead.qualified``)
so hot/scored leads trigger real AE actions without an HTTP call.
Wave B.2: lightweight objection detection via rule lexicon.

It is deterministic (no extra LLM call) and reuses:
  * `agent_matcher.ensure_lead_assignment` for sticky assignment
  * `whatsapp_agent.score_lead` for the lead score breakdown
  * `crm_sync` indirectly via the `update_crm` executor

See plans/IREIOS_3.0_STEP_BY_STEP_EXPANSION.md (Phase 6) and
plans/IREIOS_3.0_EXPANSION_CHANGELOG.md.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

from config import settings
from database import SessionLocal
from models import Lead

from app.agents.whatsapp_agent import score_lead
from app.automation_engine.engine import submit as ae_submit
from app.intelligence.agent_matcher import ensure_lead_assignment

logger = logging.getLogger("sales_agent")


class SalesAiBody(BaseModel):
    """HTTP body for POST /leads/{id}/sales-ai (IREIOS 4.0)."""

    mode: Literal["preview", "execute"] = "preview"

    @field_validator("mode", mode="before")
    @classmethod
    def _mode_ok(cls, v):
        m = (v or "preview")
        if isinstance(m, str):
            m = m.strip().lower()
        if m not in ("preview", "execute"):
            raise ValueError("mode must be 'preview' or 'execute'")
        return m

# Wave B.1: bus subscription events.
SALES_BUS_EVENTS = ["lead.scored", "lead.hot", "conversation.updated", "lead.qualified"]

# Wave B.2: objection lexicon.
_OBJECTION_PATTERNS = {
    "price": ["too expensive", "out of budget", "over budget", "costly", "high price", "can't afford", "pricey"],
    "timing": ["not now", "later", "not ready", "need time", "thinking", "maybe next month", "no rush"],
    "location": ["too far", "not in that area", "other location", "wrong area", "too remote"],
    "trust": ["scam", "fraud", "not sure about you", "unreliable", "never heard"],
    "competitor": ["other builder", "another project", "found better", "going with", "other company"],
}

# Canonical funnel progression used by `progress_deal_stage`.
_FUNNEL_NEXT = {
    "New": "Contacted",
    "Contacted": "Qualified",
    "Qualified": "Site Visit Booked",
    "Site Visit Booked": "Negotiation",
    "Negotiation": "Closed Won",
}
_TERMINAL_STAGES = {"Closed Won", "Closed Lost", "Lost"}


def recommend_next_action(lead: Lead) -> dict:
    """Return the next-best sales action for a lead.

    Deterministic policy:
      * terminal stage (Closed Won/Lost) -> deal_closed (no AE)
      * missing mandatory fields -> request_info
      * temperature hot -> escalate_hot (human handoff)
      * visit_date present but stage < Site Visit Booked -> schedule_site_visit
      * warm + assigned -> send_brochure
      * assigned + qualified-ish -> assign_agent (notify)
      * otherwise -> nurture_followup
    """
    stage = (lead.funnel_stage or "New").strip()
    if stage in _TERMINAL_STAGES:
        return {
            "action": "deal_closed",
            "rationale": (
                f"Lead is already {stage} — no further outbound NBA "
                "(brochure / visit / escalate). Review in CRM if needed."
            ),
        }

    temp = (lead.lead_temperature or "cold").lower()
    has_core = all([lead.name, lead.phone, lead.location, lead.budget, lead.property_type])

    if not has_core:
        missing = [f for f in ("name", "phone", "location", "budget", "property_type")
                   if not getattr(lead, f)]
        return {"action": "request_info", "missing_fields": missing,
                "rationale": "Capture remaining mandatory fields before routing."}

    # Active pipeline stages only (Closed Won already returned above)
    if lead.visit_date and stage not in ("Site Visit Booked", "Negotiation"):
        return {"action": "schedule_site_visit",
                "rationale": "Visit date captured — confirm and book the site tour."}

    if temp == "hot":
        return {"action": "escalate_hot",
                "rationale": "Hot lead — pause automation and alert a human agent."}

    if temp == "warm" and lead.assigned_agent:
        return {"action": "send_brochure",
                "rationale": "Warm, assigned lead — share property brochure to build intent."}

    if lead.assigned_agent:
        return {"action": "assign_agent",
                "rationale": "Assigned lead — notify the human owner to take over."}

    return {"action": "nurture_followup",
            "rationale": "Cold/unassigned — keep in the automated follow-up sequence."}


def progress_deal_stage(lead: Lead, recommendation: Optional[dict] = None) -> Optional[str]:
    """Advance funnel only when NBA / qualification signals warrant it.

    Does **not** blindly step New→Contacted→Qualified on every Confirm.
    """
    current = lead.funnel_stage or "New"
    if current in _TERMINAL_STAGES:
        return None

    nba = (recommendation or {}).get("action") if recommendation else None

    # Full 6-field + visit (or explicit schedule NBA) → Site Visit Booked
    fully_ready = all([
        lead.name, lead.phone, lead.location, lead.budget, lead.property_type, lead.visit_date,
    ])
    if fully_ready or nba == "schedule_site_visit":
        if lead.visit_date and current not in ("Site Visit Booked", "Negotiation"):
            return "Site Visit Booked"
        return None

    # First human ownership: New → Contacted only
    if current == "New" and lead.assigned_agent:
        return "Contacted"

    # Hot escalate does not force a funnel jump beyond Contacted
    if nba == "escalate_hot" and current == "New":
        return "Contacted"

    return None


class SalesAgent:
    """Phase 6 Sales AI orchestrator."""

    async def run_sales_ai(
        self,
        db,
        lead: Lead,
        client_id: int,
        *,
        sync_crm: bool = False,
        mode: str = "execute",
    ) -> dict:
        """Score, assign, recommend, and (optionally) advance + sync the lead.

        ``mode``:
          * ``preview`` — compute scores/NBA/would-be assignee; **no** DB writes,
            no CRM, no commit. ``applied=false``.
          * ``execute`` (default for bus/legacy callers) — full pipeline + commit.

        HTTP default is ``preview`` (see main endpoint). Bus path stays execute.
        """
        mode_norm = (mode or "execute").strip().lower()
        if mode_norm not in ("preview", "execute"):
            raise ValueError(f"invalid sales-ai mode: {mode}")

        scores = score_lead(lead)

        if mode_norm == "preview":
            return self._preview_sales_ai(db, lead, client_id, scores)

        from models import EventLog

        db.refresh(lead)
        stage_before = lead.funnel_stage or "New"
        scores_before = {
            "conversion_probability": getattr(lead, "conversion_probability", None),
            "lead_temperature": getattr(lead, "lead_temperature", None),
        }

        for k, v in scores.items():
            setattr(lead, k, v)

        previous_agent = lead.assigned_agent
        assigned = ensure_lead_assignment(db, lead, client_id, lead.intent or lead.location or "", force=False)
        if assigned and previous_agent != assigned:
            db.add(EventLog(
                session_id=lead.session_id, client_id=client_id, event_type="audit",
                action_type=f"sales_ai_assigned_{assigned.replace(' ', '_').lower()}", agent_type="SalesAI",
            ))
            db.add(EventLog(
                session_id=lead.session_id, client_id=client_id, event_type="lead.assigned",
                action_type=f"assigned_{str(assigned).replace(' ', '_').lower()}", agent_type="SalesAI",
            ))

        recommendation = recommend_next_action(lead)
        nba_action = recommendation.get("action") or "unknown"

        db.add(EventLog(
            session_id=lead.session_id, client_id=client_id, event_type="lead.scored",
            action_type=f"score_{scores.get('lead_temperature', 'unknown')}",
            agent_type="SalesAI",
        ))
        if (scores.get("lead_temperature") or "").lower() == "hot":
            db.add(EventLog(
                session_id=lead.session_id, client_id=client_id, event_type="lead.hot",
                action_type="hot_threshold", agent_type="SalesAI",
            ))

        new_stage = progress_deal_stage(lead, recommendation)
        if new_stage:
            lead.funnel_stage = new_stage
            db.add(EventLog(
                session_id=lead.session_id, client_id=client_id, event_type="audit",
                action_type=f"stage_{new_stage.replace(' ', '_').lower()}", agent_type="SalesAI",
            ))

        db.add(EventLog(
            session_id=lead.session_id, client_id=client_id, event_type="sales_ai.execute",
            action_type=f"nba_{nba_action}", agent_type="SalesAI",
        ))

        crm_status = None
        if sync_crm and lead.id:
            crm_status = await self.sync_crm_via_ae(lead.id, client_id)

        actions_executed = await _nba_to_ae_action(lead, client_id, recommendation)

        db.commit()
        scores_unchanged = (
            scores_before.get("conversion_probability") == scores.get("conversion_probability")
            and (scores_before.get("lead_temperature") or "").lower()
            == (scores.get("lead_temperature") or "").lower()
        )
        return {
            "mode": "execute",
            "applied": True,
            "scores": scores,
            "assigned_agent": assigned,
            "recommendation": recommendation,
            "funnel_stage": lead.funnel_stage,
            "crm_sync": crm_status,
            "actions_executed": actions_executed,
            "stage_before": stage_before,
            "scores_before": scores_before,
            "scores_unchanged": scores_unchanged,
            "test_mode": bool(settings.TEST_MODE),
            "note": (
                "Confirm wrote the lead row. Conversion uses the same floors as chat "
                "(visit/full-qualify boosts) and will not drop a higher stored score "
                "while the lead stays complete. "
                + (
                    "TEST_MODE is on — outbound WhatsApp is not delivered to real phones."
                    if settings.TEST_MODE
                    else ""
                )
            ).strip(),
        }

    def _preview_sales_ai(self, db, lead: Lead, client_id: int, scores: dict) -> dict:
        """Compute NBA without persisting scores, assignment, or stage."""
        from app.intelligence.agent_matcher import match_best_agent

        snapshot = {k: getattr(lead, k, None) for k in scores}
        try:
            for k, v in scores.items():
                setattr(lead, k, v)
            recommendation = recommend_next_action(lead)
        finally:
            for k, v in snapshot.items():
                setattr(lead, k, v)

        assigned = lead.assigned_agent
        if getattr(lead, "conversion_status", None) != "claimed":
            agent_data = match_best_agent(
                db=db,
                client_id=client_id,
                location=getattr(lead, "location", None) or "",
                query=lead.intent or lead.location or "",
                apply_workload=False,
            )
            candidate = agent_data.get("assigned_agent")
            match_score = agent_data.get("match_score", 0)
            if candidate and match_score >= settings.MIN_MATCH_SCORE:
                assigned = candidate

        try:
            db.refresh(lead)
        except Exception:
            db.expire(lead)

        # Project stage if Confirm were clicked (no write)
        snap_agent = lead.assigned_agent
        try:
            if assigned:
                lead.assigned_agent = assigned
            proposed = progress_deal_stage(lead, recommendation)
        finally:
            lead.assigned_agent = snap_agent

        stored_prob = getattr(lead, "conversion_probability", None)
        return {
            "mode": "preview",
            "applied": False,
            "scores": scores,
            "assigned_agent": assigned,
            "recommendation": recommendation,
            "funnel_stage": lead.funnel_stage,
            "proposed_stage": proposed,
            "crm_sync": None,
            "scores_before": {
                "conversion_probability": stored_prob,
                "lead_temperature": getattr(lead, "lead_temperature", None),
            },
            "test_mode": bool(settings.TEST_MODE),
            "note": (
                "Preview only (not saved). Conversion is a fresh recompute aligned with "
                f"chat score floors; Postgres still has {stored_prob}% until Confirm. "
                "Confirm writes scores/assignment/stage when warranted and may send brochure/notify."
                + (
                    " TEST_MODE: WhatsApp will not reach a real phone."
                    if settings.TEST_MODE
                    else ""
                )
            ),
        }

    async def sync_crm_via_ae(self, lead_id: int, client_id: int) -> dict:
        """Route CRM sync through AutomationEngine -> ExecutionEngine (CRMExecutor)."""
        try:
            result = await ae_submit({
                "action_type": "update_crm",
                "tenant_id": f"Client_{client_id}",
                "entity_id": f"lead:{lead_id}",
                "parameters": {"lead_id": lead_id},
                "source": "sales_agent",
            })
            return result
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"SalesAI CRM sync via AE failed (DLQ may catch): {e}")
            return {"status": "error", "error": str(e)}


# --------------------------------------------------------------------------- #
# Wave B.1: CEO bus handler — maps NBA actions to AE submissions.
# --------------------------------------------------------------------------- #

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


def _lead_id(envelope: dict) -> Optional[int]:
    payload = envelope.get("payload") or {}
    raw = payload.get("lead_id", envelope.get("entity_id"))
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _debounce_key(client_id: int, lead_id: int) -> str:
    """Redis key for per-lead sales AI debounce (10min TTL)."""
    return f"sales_ai_lock:{client_id}:{lead_id}"


async def _nba_to_ae_action(lead: Lead, client_id: int, recommendation: dict) -> list[dict]:
    """Map a Sales NBA recommendation to AE action requests. Returns status rows."""
    action = recommendation.get("action")
    executed: list[dict] = []

    stage = getattr(lead, "funnel_stage", None) or ""
    if action in ("deal_closed", "none", None) or stage in _TERMINAL_STAGES:
        executed.append({
            "action": action or "deal_closed",
            "status": "skipped",
            "nba": action,
            "note": "Terminal or no-op NBA — no outbound AE dispatch",
        })
        return executed

    async def _submit(action_type: str, parameters: dict) -> None:
        try:
            await ae_submit({
                "action_type": action_type,
                "tenant_id": f"Client_{client_id}",
                "entity_id": str(lead.id),
                "parameters": parameters,
                "source": "sales_agent",
            })
            executed.append({"action": action_type, "status": "ok", "nba": action})
        except Exception as e:  # noqa: BLE001
            logger.warning("sales AE submit failed action=%s err=%s", action_type, e)
            executed.append({
                "action": action_type,
                "status": "error",
                "nba": action,
                "error": str(e)[:200],
            })

    if action == "escalate_hot":
        reason = recommendation.get("rationale", "Hot lead — auto-escalated by Sales AI")
        await _submit("notify_agent", {
            "kind": "hot_lead",
            "lead_id": lead.id,
            "reason": reason,
        })
        await _submit("create_task", {
            "lead_id": lead.id,
            "title": f"Call hot lead {lead.name or lead.id}",
            "description": reason,
            "assignee": lead.assigned_agent or None,
            "source": "sales_agent",
        })
    elif action == "schedule_site_visit" and lead.visit_date:
        await _submit("schedule_visit", {
            "lead_id": lead.id,
            "visit_date": lead.visit_date,
            "name": lead.name or "",
            "phone": lead.phone or "",
            "location": lead.location or "",
        })
        if (lead.lead_temperature or "").lower() == "hot":
            hot_reason = "Hot lead with confirmed visit date — alert agent."
            await _submit("notify_agent", {
                "kind": "hot_lead",
                "lead_id": lead.id,
                "reason": hot_reason,
            })
            await _submit("create_task", {
                "lead_id": lead.id,
                "title": f"Call hot lead {lead.name or lead.id}",
                "description": hot_reason,
                "assignee": lead.assigned_agent or None,
                "source": "sales_agent",
            })
    elif action == "send_brochure":
        from app.agents.whatsapp_agent import generate_brochure, resolve_tool_media_url

        # Debounce repeat brochure from HTTP Confirm (10 min) — bus path has its own lock
        brochure_key = f"sales_ai_brochure:{client_id}:{lead.id}"
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            already = await r.get(brochure_key)
            if already:
                await r.aclose()
                executed.append({
                    "action": "send_whatsapp",
                    "status": "skipped",
                    "nba": action,
                    "note": "Brochure already sent recently (10 min debounce) — not re-dispatched",
                })
                return executed
            await r.set(brochure_key, "1", ex=600)
            await r.aclose()
        except Exception:  # noqa: BLE001
            pass  # best-effort debounce

        media_url = resolve_tool_media_url("brochure")
        if media_url:
            body = (
                f"Hi {lead.name or 'there'}, here is the brochure for "
                f"{lead.property_type or 'properties'} in {lead.location or 'our projects'}."
            )
        else:
            body = generate_brochure(lead)
        params = {
            "to": lead.phone or "",
            "body": body,
            "source": "sales_agent",
            "tool": "brochure",
        }
        if media_url:
            params["media_url"] = media_url
        await _submit("send_whatsapp", params)
        if settings.TEST_MODE:
            for row in executed:
                if row.get("action") == "send_whatsapp" and row.get("status") == "ok":
                    row["note"] = (
                        "TEST_MODE — pipeline OK; WhatsApp not sent to the phone "
                        "(set TEST_MODE=false + real TWILIO_* for live send)"
                    )
                    row["delivery"] = "test_mode_skipped"
    else:
        # request_info / nurture_followup / assign_agent — no AE side effect
        executed.append({
            "action": action or "none",
            "status": "skipped",
            "nba": action,
            "note": "Handled by assignment/follow-up; no AE dispatch",
        })
    return executed


async def sales_bus_handler(envelope: dict) -> None:
    """CEO handler for sales bus events: score/assign/recommend → AE actions."""
    client_id = _resolve_client_id(envelope.get("tenant_id"))
    lid = _lead_id(envelope)
    if client_id is None or lid is None:
        return

    # Debounce: skip if this lead was acted on recently.
    # P3: lead.qualified bypasses debounce — visit booking is time-critical.
    event_type = envelope.get("event_type", "")
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        lock_key = _debounce_key(client_id, lid)
        already = await r.get(lock_key)
        if already:
            if event_type == "lead.qualified":
                logger.debug("sales_bus debounce bypassed for lead.qualified: lead %s client %s", lid, client_id)
            else:
                logger.debug("sales_bus debounce: lead %s client %s skipped", lid, client_id)
                await r.aclose()
                return
        await r.set(lock_key, "1", ex=600)  # 10 minute TTL (refreshes for bypassed events)
        await r.aclose()
    except Exception:
        pass  # debounce is best-effort; proceed without it

    db = SessionLocal()
    try:
        lead = db.query(Lead).filter(Lead.id == lid, Lead.client_id == client_id).first()
        if lead is None:
            return

        recommendation = recommend_next_action(lead)
        await _nba_to_ae_action(lead, client_id, recommendation)
        try:
            from models import EventLog
            db.add(EventLog(
                session_id=lead.session_id,
                client_id=client_id,
                event_type="sales_ai.bus",
                action_type=f"nba_{recommendation.get('action') or 'unknown'}",
                agent_type="SalesAI",
            ))
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# Wave B.2: Objection detection (lightweight rule lexicon).
# --------------------------------------------------------------------------- #

def detect_objections(message: str) -> list[dict]:
    """Scan a user message for known objection patterns.

    Returns a list of dicts ``[{"type": "price", "matched": "too expensive"}, …]``.
    Empty list when no objection is detected.
    """
    if not message:
        return []
    msg_lower = message.lower()
    hits: list[dict] = []
    for obj_type, patterns in _OBJECTION_PATTERNS.items():
        for pat in patterns:
            if pat in msg_lower:
                hits.append({"type": obj_type, "matched": pat})
                break  # one match per type per message
    return hits


async def persist_objection(db, lead_id: int, client_id: int, objection: dict) -> None:
    """Store an objection in LeadMemory."""
    from models import LeadMemory
    mem = LeadMemory(
        client_id=client_id,
        lead_id=lead_id,
        key=f"objection_{objection['type']}",
        value=objection["matched"],
        memory_type="objection",
    )
    db.add(mem)
    db.commit()


# --------------------------------------------------------------------------- #
# CEO registration
# --------------------------------------------------------------------------- #

def register_sales_agent(ceo) -> None:
    ceo.register_agent(
        "sales_agent", sales_bus_handler, subscriptions=list(SALES_BUS_EVENTS), status="active"
    )
    logger.info("Registered sales_agent on %d event types (B.1 bus)", len(SALES_BUS_EVENTS))


sales_agent = SalesAgent()
