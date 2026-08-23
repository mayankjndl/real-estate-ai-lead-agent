"""IREIOS 3.0 — Phase 5: WhatsApp Agent v3 + brochure/floorplan + lead scoring.

`WhatsAppAgent` is the v3 chat orchestrator. It reuses the proven qualification
pipeline in `agent.process_chat` (no behaviour regression) and layers on:

  * deterministic lead scoring (`score_lead`) — conversion probability,
    temperature, urgency, engagement, budget alignment.
  * brochure / floorplan tool handlers that produce rich outbound media-style
    messages and dispatch them through the AutomationEngine -> ExecutionEngine
    (so outbound delivery is observable / DLQ-protected).
  * intent routing so a "send brochure" / "show floor plan" request is served
    by the new tools instead of the generic pipeline.

The v3 path is selected by `FEATURE_WHATSAPP_V3` in `main.py`; legacy routes
still call `agent.process_chat` directly when the flag is off.

See plans/IREIOS_3.0_STEP_BY_STEP_EXPANSION.md (Phase 5) and
plans/IREIOS_3.0_EXPANSION_CHANGELOG.md.
"""
from __future__ import annotations

import asyncio
import contextvars
import logging
import re
from typing import Optional, Set

from config import settings
from database import SessionLocal
from models import Lead, Message, Session
from sqlalchemy.orm import Session as DBSession

from app.automation_engine.engine import submit as ae_submit

logger = logging.getLogger("whatsapp_agent_v3")

# Keep fire-and-forget post-turn tasks alive until done (prod path).
_post_turn_tasks: Set[asyncio.Task] = set()

_PROP_TYPE_RE = re.compile(r"\b(1bhk|2bhk|3bhk|4bhk|villa|plot|studio|penthouse|flat|apartment)\b", re.I)
_AREA_RE = re.compile(r"\b(\d{3,5})\s*sq\s*(ft|feet)\b", re.I)

# Post-G3 Approach B: structured media URL for the current turn (TwiML path).
# ContextVar keeps concurrent requests isolated; per-session map avoids races when
# multiple turns finish under different tasks; module fallback covers tests that
# call process_chat via asyncio.run (new context copy).
_outbound_media_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "wa_outbound_media", default=None
)
_outbound_media_fallback: Optional[str] = None
_outbound_media_by_session: dict[str, str] = {}
_outbound_media_session_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "wa_outbound_media_session", default=None
)


def take_outbound_media_url(session_id: Optional[str] = None) -> Optional[str]:
    """Return and clear the media URL staged for this turn (if any)."""
    global _outbound_media_fallback
    sid = session_id or _outbound_media_session_ctx.get()
    if sid and sid in _outbound_media_by_session:
        return _outbound_media_by_session.pop(sid, None)
    url = _outbound_media_ctx.get()
    _outbound_media_ctx.set(None)
    if url is None:
        url = _outbound_media_fallback
    _outbound_media_fallback = None
    return url


def peek_outbound_media_url(session_id: Optional[str] = None) -> Optional[str]:
    """Read staged media URL without clearing (tests)."""
    sid = session_id or _outbound_media_session_ctx.get()
    if sid and sid in _outbound_media_by_session:
        return _outbound_media_by_session.get(sid)
    return _outbound_media_ctx.get() or _outbound_media_fallback


def _stage_outbound_media_url(url: Optional[str], session_id: Optional[str] = None) -> None:
    global _outbound_media_fallback
    val = url if url else None
    sid = session_id or _outbound_media_session_ctx.get()
    if sid:
        if val:
            _outbound_media_by_session[sid] = val
        else:
            _outbound_media_by_session.pop(sid, None)
    _outbound_media_ctx.set(val)
    _outbound_media_fallback = val


def resolve_tool_media_url(tool: str) -> Optional[str]:
    """Return public HTTPS media URL for brochure|floorplan, or None (text fallback).

    Approach B: Twilio fetches this URL and delivers a document bubble.
    Non-HTTPS values are rejected so broken local paths never reach Twilio.
    """
    raw = None
    if tool == "brochure":
        raw = (getattr(settings, "BROCHURE_MEDIA_URL", None) or "").strip()
    elif tool == "floorplan":
        raw = (getattr(settings, "FLOORPLAN_MEDIA_URL", None) or "").strip()
    if not raw:
        return None
    if not raw.lower().startswith("https://"):
        logger.warning("rejecting non-HTTPS media URL for tool=%s", tool)
        return None
    return raw


def detect_tool_intent(message: str) -> Optional[str]:
    """Return 'brochure' | 'floorplan' | None based on the user message."""
    m = (message or "").lower()
    if any(k in m for k in ("brochure", "send details", "property details", "more info", "share details")):
        return "brochure"
    if any(k in m for k in ("floor plan", "floorplan", "layout", "floor map", "plan")):
        return "floorplan"
    return None


def _fmt_budget(budget: Optional[str]) -> str:
    return budget or "as per your preference"


def generate_brochure(lead: Lead) -> str:
    """Deterministic brochure text derived from captured lead fields."""
    pt = lead.property_type or "property"
    loc = lead.location or "Pune"
    budget = _fmt_budget(lead.budget)
    name = lead.name or "there"
    return (
        f"Hi {name}, here is the brochure for {pt} options in {loc}.\n"
        f"• Property type: {pt}\n"
        f"• Location: {loc}\n"
        f"• Budget range: {budget}\n"
        f"• Highlights: ready possession, gated community, Vastu-compliant, "
        f"clubhouse & parking.\n"
        f"Reply 'floor plan' to see the layout, or share a visit date to book a site tour."
    )


def generate_floorplan(lead: Lead) -> str:
    """Deterministic floor-plan description derived from captured lead fields."""
    pt = lead.property_type or "2BHK"
    match = _PROP_TYPE_RE.search(pt) or _PROP_TYPE_RE.search(lead.intent or "")
    label = (match.group(1).upper() if match else "2BHK").upper()
    area = _AREA_RE.search(lead.budget or "") or _AREA_RE.search(lead.intent or "")
    sqft = area.group(1) if area else ("950" if "1bhk" in label.lower() else "1250" if "2bhk" in label.lower() else "1800")
    name = lead.name or "there"
    return (
        f"Hi {name}, here is the {label} floor plan (~{sqft} sq ft):\n"
        f"• Entrance lobby → living/dining\n"
        f"• {label} bedrooms with attached baths\n"
        f"• Modular kitchen + utility\n"
        f"• Balcony facing the greens\n"
        f"Want me to share the brochure or lock a site-visit date?"
    )


def score_lead(lead: Lead) -> dict:
    """Compute lead scores (fast, deterministic, no LLM).

    * engagement_score: filled core fields (+ opt-in)
    * conversion_probability: completeness + temperature, with the same
      **floor boosts** as the chat path (``agent.py``): full qualify ≥88,
      visit date ≥82 — so Sales AI Confirm does not yank a chat/hot score
      down to a lower generic blend.
    * Never *decreases* a stored conversion_probability when the lead still
      has solid completeness (avoids "was 95% → now 80%" UX shocks on Confirm).
    * lead_temperature / urgency / budget_alignment as before
    """
    core = [lead.name, lead.phone, lead.budget, lead.location, lead.property_type, lead.visit_date]
    filled = sum(1 for c in core if c)
    engagement = min(100, filled * 16 + (lead.whatsapp_opt_in and 4 or 0))

    temp = (lead.lead_temperature or "cold").lower()
    temp_weight = {"hot": 60, "warm": 40, "cold": 15}.get(temp, 15)
    prob = min(98, int(engagement * 0.5 + temp_weight * 0.5))

    # Align floors with agent.py DB-aware overrides (chat path)
    has_visit = bool(lead.visit_date)
    fully_qualified = all([
        lead.name, lead.phone, lead.location, lead.budget, lead.property_type, lead.visit_date,
    ])
    if fully_qualified:
        prob = max(prob, 88)
    elif has_visit:
        prob = max(prob, 82)

    # Monotonic vs stored score when lead is still well-formed
    stored_raw = getattr(lead, "conversion_probability", None)
    try:
        stored = int(stored_raw) if stored_raw is not None else None
    except (TypeError, ValueError):
        stored = None
    if stored is not None and stored > prob and (filled >= 4 or has_visit or fully_qualified):
        prob = min(98, stored)

    # Temperature: match chat floors (full qualify / visit → hot)
    if fully_qualified or has_visit or prob >= 70:
        temperature = "hot"
    elif prob >= 45:
        temperature = "warm"
    else:
        temperature = "cold"

    if lead.visit_date:
        urgency = "high"
    elif lead.budget and lead.location:
        urgency = "medium"
    else:
        urgency = "low"

    if lead.budget and lead.location and lead.property_type:
        try:
            from app.intelligence.budget_alignment import evaluate_budget_alignment

            alignment_result = evaluate_budget_alignment(
                budget_text=lead.budget,
                location=lead.location.split(",")[0].strip(),
                property_type=lead.property_type,
                intent=getattr(lead, "intent", "buy") or "buy",
            )
            alignment = alignment_result.get("alignment_status", "unknown")
        except Exception:
            alignment = "unknown"
    elif lead.budget and lead.property_type:
        alignment = "unknown"
    else:
        alignment = "unknown"

    return {
        "engagement_score": engagement,
        "conversion_probability": prob,
        "lead_temperature": temperature,
        "urgency_level": urgency,
        "budget_alignment_status": alignment,
    }


class WhatsAppAgent:
    """v3 chat agent. Delegates qualification to the shared pipeline and adds
    brochure/floorplan tools + scoring + Neo4j graph context on the reply path."""

    def _upsert_lead_snapshot(self, lead: Optional[Lead], client_id: int) -> None:
        """Best-effort Neo4j Lead upsert from current ORM fields (never raises)."""
        if not lead or not getattr(lead, "id", None):
            return
        try:
            from app.knowledge_graph.neo4j_kg import knowledge_graph

            if not knowledge_graph.available:
                return
            knowledge_graph.upsert_lead(
                lead.id,
                client_id,
                {
                    k: v
                    for k, v in {
                        "name": lead.name,
                        "location": lead.location,
                        "property_type": lead.property_type,
                        "lead_temperature": lead.lead_temperature,
                        "intent": lead.intent,
                        "conversion_probability": getattr(
                            lead, "conversion_probability", None
                        ),
                    }.items()
                    if v is not None
                },
            )
        except Exception as e:  # noqa: BLE001
            logger.debug("graph upsert skipped: %s", e)

    def _graph_extra_context(self, lead: Optional[Lead], client_id: int) -> str:
        """BD-5: sync Neo4j context for the LLM (never raises). Prefer async wrapper."""
        if not lead or not getattr(lead, "id", None):
            return ""
        try:
            from app.clients.graph_client import format_graph_context_for_llm, graph_client

            # Ensure this lead exists in the graph so similarity queries can anchor.
            self._upsert_lead_snapshot(lead, client_id)

            ctx = graph_client.get_lead_context(lead.id, client_id)
            return format_graph_context_for_llm(ctx)
        except Exception as e:  # noqa: BLE001
            logger.debug("graph context skipped: %s", e)
            return ""

    async def _graph_extra_context_soft(self, lead: Optional[Lead], client_id: int) -> str:
        """BD-5 with hard budget so a slow Neo4j cannot burn the WA race window."""
        timeout = float(getattr(settings, "GRAPH_CONTEXT_TIMEOUT_SECONDS", 0.5))
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._graph_extra_context, lead, client_id),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.debug(
                "graph context soft-timeout after %ss lead=%s",
                timeout,
                getattr(lead, "id", None),
            )
            return ""
        except Exception as e:  # noqa: BLE001
            logger.debug("graph context soft path skipped: %s", e)
            return ""

    async def _post_turn_side_effects(
        self,
        *,
        lead_id: int,
        client_id: int,
        session_id: str,
        user_message: str,
    ) -> None:
        """Score + negotiation Layer 2 + graph upsert + memory (own DB session).

        Runs off the TwiML critical path in production (fire-and-forget).
        Awaited when TEST_MODE so unit tests see scores immediately.
        """
        try:
            with SessionLocal() as db:
                lead = db.query(Lead).filter(Lead.id == lead_id, Lead.client_id == client_id).first()
                if not lead:
                    return

                scores = score_lead(lead)
                for k, v in scores.items():
                    setattr(lead, k, v)
                db.commit()

                if scores.get("budget_alignment_status") and scores["budget_alignment_status"] not in (
                    "aligned",
                    "excellent",
                    "strong",
                    "unknown",
                ):
                    if not lead.is_negotiating:
                        lead.is_negotiating = True
                        db.commit()
                    try:
                        from app.events.negotiation import publish_negotiation_started

                        await publish_negotiation_started(
                            client_id=client_id,
                            lead_id=lead.id,
                            session_id=session_id,
                            trigger="budget_misaligned",
                            budget=lead.budget or "",
                            budget_alignment_status=scores["budget_alignment_status"],
                            source="whatsapp_agent_v3",
                        )
                    except Exception as e:  # noqa: BLE001
                        logger.debug("negotiation event publish skipped: %s", e)

                self._upsert_lead_snapshot(lead, client_id)

                try:
                    from app.memory.conversation_memory import conversation_memory

                    conversation_memory.extract_and_store(
                        db, lead=lead, client_id=client_id, user_message=user_message or ""
                    )
                except Exception as e:  # noqa: BLE001
                    logger.debug("memory auto-write skipped: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.debug("post-turn side effects skipped: %s", e)

    def _schedule_post_turn(
        self,
        *,
        lead_id: int,
        client_id: int,
        session_id: str,
        user_message: str,
    ) -> asyncio.Task:
        task = asyncio.create_task(
            self._post_turn_side_effects(
                lead_id=lead_id,
                client_id=client_id,
                session_id=session_id,
                user_message=user_message,
            )
        )
        _post_turn_tasks.add(task)
        task.add_done_callback(_post_turn_tasks.discard)
        return task

    async def process_chat(
        self,
        session_id: str,
        user_message: str,
        db: DBSession,
        client_id: int = 1,
        is_background: bool = False,
        dispatch_via_ae: bool = False,
    ) -> str:
        # Shared qualification core (app.agents.qualification → agent.process_chat).
        from app.agents.qualification import process_chat as qualify_chat

        lead_pre = db.query(Lead).filter(Lead.session_id == session_id).first()
        extra = await self._graph_extra_context_soft(lead_pre, client_id)

        reply = await qualify_chat(
            session_id,
            user_message,
            db,
            client_id=client_id,
            is_background=is_background,
            extra_context=extra or None,
        )

        lead = db.query(Lead).filter(Lead.session_id == session_id).first()
        if not lead:
            return reply

        _outbound_media_session_ctx.set(session_id)
        # Clear any stale staged media from a prior turn for this session.
        _stage_outbound_media_url(None, session_id=session_id)

        final_reply = reply

        # v3 tool routing stays on critical path (changes the user-visible reply).
        # Do NOT also AE-send here on the Twilio webhook path (double-deliver).
        intent = detect_tool_intent(user_message)
        if intent and lead.whatsapp_opt_in:
            media_url = resolve_tool_media_url(intent)
            if media_url:
                name = lead.name or "there"
                pt = lead.property_type or "property"
                loc = lead.location or ""
                label = "floor plan" if intent == "floorplan" else intent
                tool_reply = f"Hi {name}, here is the {label} for {pt} in {loc}."
            else:
                tool_reply = generate_brochure(lead) if intent == "brochure" else generate_floorplan(lead)
            db.add(Message(session_id=session_id, client_id=client_id, role="assistant", content=tool_reply))
            db.commit()
            if dispatch_via_ae:
                await self._dispatch_outbound(session_id, client_id, lead, tool_reply, tool=intent, media_url=media_url)
                if media_url:
                    try:
                        from app.clients.event_bus_client import event_bus

                        if getattr(event_bus, "_running", False):
                            await event_bus.publish(
                                f"{intent}.sent",
                                f"Client_{client_id}",
                                str(lead.id),
                                {
                                    "lead_id": lead.id,
                                    "session_id": session_id,
                                    "tool": intent,
                                    "media_url": media_url,
                                },
                                source="whatsapp_agent_v3",
                            )
                    except Exception as e:  # pragma: no cover
                        logger.debug("tool sent event publish skipped: %s", e)
            else:
                if media_url:
                    _stage_outbound_media_url(media_url, session_id=session_id)

                try:
                    from app.clients.event_bus_client import event_bus

                    if getattr(event_bus, "_running", False):
                        evt = f"{intent}.sent" if media_url else f"{intent}.generated"
                        await event_bus.publish(
                            evt,
                            f"Client_{client_id}",
                            str(lead.id),
                            {
                                "lead_id": lead.id,
                                "session_id": session_id,
                                "tool": intent,
                                "preview": tool_reply[:200],
                                "media_url": media_url,
                            },
                            source="whatsapp_agent_v3",
                        )
                except Exception as e:  # pragma: no cover
                    logger.debug("tool event publish skipped: %s", e)
            final_reply = tool_reply

        # Score / negotiation / graph / memory — off critical path in prod.
        post_task = self._schedule_post_turn(
            lead_id=lead.id,
            client_id=client_id,
            session_id=session_id,
            user_message=user_message or "",
        )
        if getattr(settings, "TEST_MODE", False):
            await post_task

        return final_reply

    async def _dispatch_outbound(self, session_id, client_id, lead, text, tool="brochure", media_url=None):
        try:
            params = {
                "to": lead.phone or session_id.split("_")[-1],
                "body": text,
                "source": "whatsapp_agent_v3",
                "tool": tool,
            }
            if media_url:
                params["media_url"] = media_url
            await ae_submit(
                {
                    "action_type": "send_whatsapp",
                    "tenant_id": f"Client_{client_id}",
                    "entity_id": session_id,
                    "parameters": params,
                    "source": "whatsapp_agent_v3",
                }
            )
        except Exception as e:
            logger.warning(f"v3 outbound dispatch failed (queued best-effort): {e}")


whatsapp_agent_v3 = WhatsAppAgent()
