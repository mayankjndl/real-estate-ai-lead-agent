# Agent Instructions — Real Estate Revenue OS

High-signal, repo-specific facts an agent would likely miss without help.

---

## Dev Commands

| Context | Command |
|---------|---------|
| Start API | `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (venv active) |
| Install deps | `pip install -r requirements.lock` (not `requirements.txt`) |
| Start frontend | `cd frontend && npm run dev` |
| Docker services | `docker compose up -d` (pg, redis, neo4j, ngrok, frontend, **n8n**) · n8n only: `docker compose up -d n8n` → http://localhost:5678 |
| Seed local test clients | `python seed.py` → keys `secret-client-key-123` / `secret-client-key-456` |
| Seed 1000 dummy leads + Neo4j | `python seed_dummy_leads.py` (`--count`, `--purge-only`, `--no-neo4j`) |
| Seed twin inventory (40 units) | `python seed_twin_demo.py --client-id 1` (`--clear`) |
| Project PG leads → Neo4j | `python project_leads_to_neo4j.py` (`--client-id`, `--source dummy_seed`) |
| Phase 4 API tests | `pytest tests/test_f4_sales_ai.py tests/test_f4_graph_neighborhood.py tests/test_f4_twin.py tests/test_f4_hubspot_flag.py -v` |
| Ops / maintenance runbook | `docs/MAINTENANCE.md` |
| Timeouts & timings map | `docs/TIMEOUTS_AND_TIMINGS.md` (all race/TTL/scheduler values + line anchors) |
| Provision production client | `python add_client.py` (interactive, generates secure keys) |
| Stress test (126 cases) | `python task3_runner.py` |
| Filter stress test | `python task3_runner.py --category HOT` (`--test-id R01`, `--skip-db`, `--base-url`, `--api-key`) |
| Tenant isolation drill | `python gate_isolation_test.py` |
| DLQ drill | `python gate_dlq_drill.py` then `python dlq_replay.py` |
| DB backup / restore | `python db_backup.py` / `python db_restore.py backups/backup_*.sql` |
| Frontend lint | `cd frontend && npm run lint` (ESLint, no TypeScript check) |
| Phase 3 concurrency tests | `pytest tests/test_p3_concurrency.py -v` (dependency-free source-inspection suite) |

---

## Architecture

- **Backend:** FastAPI + Gemini 3.1 Flash Lite + Twilio WhatsApp + PostgreSQL + Redis + FAISS RAG
- **Frontend:** Next.js 16.2.6 with React 19.2.4, Tailwind CSS v4, TypeScript. Route groups: `(public)` and `(dashboard)` with per-group layouts.
- **Static dashboard:** HTML/JS/CSS served by FastAPI at `/dashboard`
- **Scheduler (APScheduler):** follow-up checker (1min), nightly backup (2am), nightly cleanup (3am), escalation checker (1min), CRM resync (5min), competitor monitor (01:00), weekly marketing report (Mon 08:00), expire_approvals (15min)
- **App entrypoint:** `main.py` — FastAPI app, lifespan starts scheduler, webhook handlers, metrics
- **Event Bus (IREIOS 3.0):** Redis Streams (`EVENT_STREAM_KEY`, default `ireios:events`) with consumer-group delivery; client in `app/clients/event_bus_client.py` (`EventBusClient`). Runtime: `Event → CEO → Agent/Workflow → Automation Engine → Execution Engine → Event`. Wired into lifespan at Task 1.7.

---

## Multi-Tenant Isolation

- Session IDs prefixed with `{client_id}_` at the routing boundary (`main.py:329`, `agent.py:264`)
- Every DB query on client tables must filter by `client_id`
- **Exceptions:** `/api/v1/roi/*` and `/api/v1/reports/pipeline` — require `X-Admin-Key` header, query globally across all clients. Never expose to client dashboards without adding JWT + `client_id` filter.

---

## Auth Layers

| Layer | Mechanism | Applies to |
|-------|-----------|------------|
| API Key | `X-API-Key` header or `?api_key=` query param | `/api/v1/whatsapp`, `/api/v1/chat`, `/api/v1/ingest`, `/api/v1/webhook/meta`, `/api/v1/webhook/portals`, `/api/v1/incoming_sms` |
| JWT Bearer | `Authorization: Bearer <token>` (7-day, bcrypt) | Dashboard routes: `/api/v1/analytics`, `/api/v1/leads`, `/api/v1/leads/export`, `/api/v1/leads/*/stage`, `/api/v1/settings`, `/api/v1/agents`, `/api/v1/roi/*` |
| Admin Key | `X-Admin-Key` header | Internal ops only |
| **Public** | None | `/health`, `/metrics`, `/docs`, `/openapi.json`, `/api/v1/contact`, `/api/v1/webhook/stripe` |

- Frontend JWT stored as HttpOnly cookie named `jwt` by server action (`frontend/src/lib/auth.ts`)
- Middleware (`frontend/src/proxy.ts`) guards `/dashboard/*`, `/leads/*`, `/crm/*`, `/settings/*` — redirects to `/login` if no cookie
- Twilio webhook validates `X-Twilio-Signature` — **bypassed when `TEST_MODE=true`**
- `/metrics` is public — firewall-restrict in production

---

## LLM & Lead Qualification

- **6-field strict gate** before visit confirmation: `visit_date AND phone AND name AND location AND budget AND property_type`
- LLM must ask for missing details, cannot confirm booking until all present
- **RAG** fires only when `is_rag_eligible` (property keyword + location in message or lead context)
- **Confidence score** < 75 → `lead.requires_manual_review = True`
- **Class-vs-instance:** Assign `lead.urgency_level` (lowercase), never `Lead.urgency_level`
- **Budget normalization:** handles `lakhs`, `cr/crores`, `k/thousand` + `PERMONTH` suffix for rentals
- **Location normalization:** joins all canonical matches (sorted by length desc), with fallback mapping for near-miss areas
- **History window:** last 6 turns (12 messages); consecutive same-role messages auto-merged
- **Duplicate message saving:** `message_saved` flag prevents saving assistant message twice when tool-call block already saved

---

## Negotiation UI (Non-blocking)

- **Dual-layer detection:** Layer 1 (keyword intercept in `agent.py`) + Layer 2 (budget misalignment in `whatsapp_agent.py`)
- **No HITL pause:** AI continues chatting uninterrupted; lead flagged as `is_negotiating = True`
- **Frontend badge:** "🤝 Open for Negotiation" purple badge on CRM KanbanBoard
- **Claim button expanded:** Visible on ANY column (not just "New") when `is_negotiating = True`
- **Debounce:** 5-minute Redis debounce per lead (TTL 300s) to prevent event spam
- **Phrases:** `negotiate, negotiation, discount, reduce price, lower price, too expensive, can you reduce, final price, best price, cheaper, afford, budget is tight, change my budget, reduce my budget, lower my budget, budget is only, can only afford, stretch my budget` (expandable in `agent.py`)
- **Events:** `lead.negotiation.started` with `trigger` = `user_phrase` | `budget_misaligned`

---

## Follow-Up Scheduler

- State machine: `Day 0 → Day 1 → Day 3 → Day 7 → closure message`
- `FOLLOW_UP_TEST_MODE=true` compresses all inter-stage gaps to **1 minute**
- `FOLLOW_UP_DLQ_TEST=true` forces scheduler to throw at `follow_up.py:423` → writes to `dlq_events`
- **Quiet hours:** follow-ups shifted to 8AM IST if time falls between 10PM–8AM IST
- **Inactivity:** 60s in test mode, 7 days in production → applies penalty + temperature downgrade
- **CRM sync** runs as background task with `await asyncio.sleep(2)` delay to avoid race with `agent.py` DB writes

---

## Webhook Flow & Timeouts

- **WhatsApp race window:** `WHATSAPP_WEBHOOK_TIMEOUT` (default **13s**, under Twilio ~15s HTTP limit). Starts `_session_turn_locked` as an `asyncio.Task`, then `asyncio.wait({task}, timeout=…)`.
  - **Fast path:** task finishes in window → real Gemini reply as TwiML.
  - **Slow path:** returns interim `"Just checking that for you..."` and schedules `_await_inflight_and_push` — **does not cancel** the task and **does not** re-run `process_unified_lead` (single Gemini call; final reply via AE→EE).
- **LLM hard cap:** `LLM_TIMEOUT_SECONDS` (default **22s**) on `chat.send_message`. **May exceed** the race window so a slow Gemini can still finish after interim. Pure `TimeoutError` is **not** retried (avoids 3× budget burn).
- **Pre-LLM budgets:** `RAG_TIMEOUT_SECONDS` (default **2.0s**), `GRAPH_CONTEXT_TIMEOUT_SECONDS` (default **0.5s**, soft-timeout via `asyncio.to_thread` + `wait_for` in WhatsAppAgent).
- **Post-turn off critical path (prod):** After reply text is ready, score / negotiation Layer 2 / graph upsert / memory and `_emit_turn_events` run as fire-and-forget tasks with private `SessionLocal`. When `TEST_MODE=true` those tasks are awaited so unit tests stay deterministic.
- **`_session_turn_locked`:** owns a private `SessionLocal` + holds `session_lock:{session_id}` for the **full** turn (including after interim return) so concurrent messages cannot interleave mid-Gemini. Request-scoped `db` is only used for WebhookLog dedupe.
- **Idempotency (P3.4):** Both `/api/v1/whatsapp` and `/api/v1/incoming_sms` insert `WebhookLog(message_sid=MessageSid)` FIRST. On `IntegrityError` (PK race on `MessageSid`) it rolls back and returns empty `<Response></Response>` — duplicate `MessageSid`s are silently dropped.
- **Interim dedup (P3.1):** At most one interim "Just checking..." per `MessageSid`, gated by Redis key `interim_sent:{MessageSid}` (120s TTL).
- **Legacy re-run:** `background_process_and_push` still exists for full re-process + EE push (lock + `background=True`). WhatsApp webhook preferred path is await-inflight, not re-run.
- **Duplicate message guard (P3.3):** On the legacy background path (`is_background=True`), `agent.py` skips inserting a user message when `_has_recent_duplicate_message` finds identical content within the last 5 minutes.
- **SMS Redis lock:** SMS handler still uses `async with redis_client.lock(f"session_lock:{scoped_session_id}", …)` around `process_unified_lead`; falls back best-effort if Redis is down.

## SMS Follow-Up Scoping (P3.5)

- `incoming_sms_webhook` does NOT use the raw `From` number as the session id. It builds `scoped_session_id = f"{current_client.id}_{raw_from}"` and uses it for the `FollowUpState` lookup, the Redis lock, and the `process_unified_lead` payload — keeping SMS follow-up state isolated per tenant.
- `_stop_followups_for_session(db, scoped_session_id)` (`main.py:431`) stops follow-ups. It runs INSIDE the Redis lock (normal path) and again in the Redis-down fallback, so follow-ups are always stopped even if Redis is unavailable.

## Notifications & Escalation

- Hot-lead **10m** escalation targets an `Agent` where `is_manager == True`; **30m** critical escalation targets `is_director == True`, falling back to the first manager (with a `P4.1 ESCALATION FALLBACK` log) when no director exists for the tenant.
- Resolution helper: `resolve_escalation_recipient(db, client_id, tier)` in `notification_service.py`; pure selection in `pick_escalation_agent(agents, tier)`.
- `Agent.is_director` added via `migrate_db.py`; `/api/v1/agents` accepts `is_director` (flows through `AgentCreate`).
- **Alert severity / upgrade (P4.2):** `trigger_hot_lead_notification(lead_id, reason, severity=None)` ranks reasons — `SEVERITY_HANDOFF (2)` > `SEVERITY_SCORE_ALERT (1)`. An open lower-severity alert is *upgraded* (one extra "UPGRADED" message + in-place `NotificationLog.reason/severity` update) instead of being dropped by the idempotency guard. Equal/lower severity or terminal status still bypasses. `NotificationLog` has `reason` + `severity` columns.
- **Follow-up send backoff (P4.3):** `compute_send_failure_backoff(retry_count, ...)` in `follow_up.py` returns `(next_delay, exhausted)` (exp 15→30→60→120→cap 240m; test mode → 1m; ≥5 retries → stop). On dispatch failure the scheduler advances `next_follow_up_at` (via backoff) so it no longer retries every tick; `FollowUpState.send_retry_count` tracks attempts and resets on success.

---

## DLQ (Dead Letter Queue)

- 3 event types: `hubspot_crm`, `twilio_outbound`, `ml_followup_scheduler`
- CRM sync: 5 retries (exponential backoff 2s→30s) via Tenacity, DLQ on permanent failure
- Replay: `python dlq_replay.py` (processes all `pending` → `resolved`)
- HubSpot sync is **demo-stubbed** (returns fake UUID) unless real `CRM_API_URL` + `CRM_API_KEY` configured

## CRM Sync (P5)

- `crm_sync.py`: **create-time CRM is bus-owned** (`lead.created` → `crm_automation` → AE→EE `update_crm`). Helpers in `crm_sync` remain for `CRMExecutor` + `crm_resync_job` (debounced field re-sync every 5 min). Do not call `sync_lead_to_crm` from chat/webhook paths.
- **P5.1:** after a meaningful field change on an already-synced lead, `agent.py` sets `Lead.crm_resync_pending = True`; `crm_resync_job` (scheduler, every 5 min) re-pushes and clears the flag. Failed re-sync keeps the flag set for retry.
- **P5.2:** extended property map (location, intent, property_type, visit_date, assignee, budget_alignment_status, urgency_level, engagement_score, lead_temperature) gated by `CRM_SYNC_EXTENDED_PROPERTIES` (default True). A 4xx for an unknown custom property drops that property and retries once.
- **P5.3:** `decide_crm_status_after_poll` leaves `crm_sync_status = "pending"` (never "success") when both `phone` and `name` are still empty after the create-time poll, so the next field update re-syncs.

## Feedback learning (P6.1)

- Agent win/loss learning is **persisted** in the `agent_learning` table (client-scoped), not in-process memory, so multi-worker deployments converge. `record_feedback(... client_id=...)` persists; `get_agent_success_rate(name, client_id)` reads it first.
- `config.MIN_MATCH_SCORE` (default 0): below this dynamic match score, `ensure_lead_assignment` leaves the lead unassigned rather than forcing a poor routing (P6.3).
- `main.py` `serialize_lead` title-cases `lead_temperature` (`Hot`/`Warm`/`Cold`) so the dashboard's case-sensitive badge compares match the backend's lowercase storage (P6.5).
- `follow_up.py` `next_followup_stage(followups, current_stage)` derives the next stage + day-gap from the ML `followups` sequence, keeping the scheduler aligned with strategy B (P6.4).

---

## Testing Flags (`.env`)

```env
FOLLOW_UP_TEST_MODE=true   # compress timings
FOLLOW_UP_DLQ_TEST=true    # force DLQ entry (requires TEST_MODE)
TEST_MODE=true             # bypass Twilio sig validation, skip WhatsApp sends
IS_PRODUCTION=false
```

**Remove all before production deploy.**

---

## Key Database Schema

- Table `event_logs` (model `EventLog`), not `event_log`
- Core tables: `clients`, `sessions`, `leads`, `messages`, `event_logs`, `follow_up_states`, `dlq_events`, `agents`, `notification_logs`, `webhook_logs`
- Lead ML columns: `conversion_probability`, `lead_temperature`, `urgency_level`, `engagement_score`, `inactivity_penalty`, `confidence_score`, `requires_manual_review`, `budget_alignment_status`

---

## Config / Env Quirks

- Settings via `pydantic_settings` (`config.py` class `Settings`) — reads `.env`
- `contextvars`: `request_id_ctx` and `tenant_id_ctx` for structured logging
- RAG FAISS index built in **background thread** (`rag.py:75`) — first request may wait ≤5s for index to be ready
- Gemini embeddings LRU-cached (128 entries) via `@lru_cache` on `get_query_embedding_cached`
- `google.generativeai` SDK deprecation warning — known, still functional
- `GEMINI_MODEL` defaults to `gemini-3.1-flash-lite` — can revert to `gemini-2.5-flash` in `.env`

## IREIOS 3.0 Expansion Env Vars (added in Phase 0, consumed in later phases)

- `EVENT_STREAM_KEY` (default `ireios:events`) — Redis Streams key for the Phase 1 event bus.
- `EVENT_CONSUMER_GROUP` (default `ireios-cg`) — consumer group name for the bus.
- `FEATURE_WHATSAPP_V3` (**default `true`** — production) — WhatsApp/chat routes use `WhatsAppAgent`; set `false` to roll back to `app.agents.qualification.process_chat` only.
- `FOLLOWUP_ENGINE` (**default `v3`** — production) — `legacy|v3|shadow`. Prod = `v3` (AE→EE). `legacy` is emergency rollback only.
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` — Neo4j (Phase 7). Empty = graph no-op. Local: `bolt://localhost:7687` / `neo4j`/`localpass`.
- `N8N_BASE_URL` / `N8N_API_KEY` — n8n optional ops plane (webhook Header Auth secret; backend sends `Authorization: Bearer`). Empty = `n8n_not_configured`.  
- `N8N_MANAGEMENT_API_KEY` — JWT from n8n UI Settings → n8n API; **only** for `import_n8n_workflows.py` (`X-N8N-API-KEY` on `/api/v1/*`). Never reuse the webhook secret (always 401).  
- **Bus→n8n bridge:** `app/automation_engine/n8n_bridge.py` (group `ireios-n8n`, not CEO `ireios-cg`). Stock n8n cannot XREADGROUP Streams. Env: `N8N_BRIDGE_ENABLED`, `N8N_BRIDGE_GROUP`, optional `N8N_WEBHOOK_MAP`. Gmail-first recipes: **`plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md`**. See **`docs/N8N_INTEGRATION.md`**.
- `COMPETITOR_KEYWORDS` — comma-separated watch-list for the competitor monitor (empty = job no-ops).
- `GOOGLE_CALENDAR_ID` / `GOOGLE_CALENDAR_CREDENTIALS_JSON` / `GOOGLE_CALENDAR_TIMEZONE` — real Google Calendar for `CalendarExecutor`. Empty = synthetic `visit_id` stub fallback (AE contract unchanged).
- `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` — public **HTTPS** media for WhatsApp Approach B. Empty = plain-text brochure/floorplan. Non-HTTPS rejected.
- HubSpot: `CRM_API_URL` / `CRM_API_KEY` via `crm_sync` `os.getenv` (not Settings). **`CRM_API_KEY` = Private App Token** sent as `Authorization: Bearer …`. Contacts r/w scopes enough (no custom objects). Default demo key = fake UUID in non-prod. Live path also requires `FEATURE_HUBSPOT_LIVE=true`.

## IREIOS 4.0 APIs (Backend Wave 1 shipped)

- `POST /api/v1/leads/{id}/sales-ai` body `{ "mode": "preview"|"execute" }` — default **preview** (no DB/CRM writes). Execute = score+assign+stage+CRM AE. Bus SalesAgent path still auto-executes.
- `GET /api/v1/graph/neighborhood?lead_id=&limit=25` — ego `{nodes,edges}`; soft-empty if Neo4j down or `FEATURE_GRAPH_VIZ=false`. Keep `/graph/leads/{id}/context` for LLM.
- `GET /api/v1/inventory/twin` — project/towers/floors/units from PG `InventoryUnit` (`meta_json.floor`). Empty if `FEATURE_TWIN_LIVE=false`. Seed: `python seed_twin_demo.py --client-id 1`.
- Flags (Settings): `FEATURE_GRAPH_VIZ` (default true), `FEATURE_TWIN_LIVE` (default true), `FEATURE_HUBSPOT_LIVE` (default **false**).

## Production Go-Live Checklist (config-later flags)

**Single source + full matrix (flag matrix, secrets track, infra adoption, integration runbooks): `docs/PROD_READINESS_CHECKLIST.md`.** QA gate (P4-QA) = checklist executed; release gate (P4-REL) = runbook approved (Mayank).  
**Command Center smoke (auth/twin/graph/copilot/predictions): `docs/COMMAND_CENTER_VERIFY.md`** — dashboard JWT = Bearer **or** cookie on all JWT routes (twin/neighborhood included; unified 2026-08-13).  
**Eng freeze handoff (Mayank + Piyush):** `plans/phase4/HANDOFF_MAYANK_PIYUSH.md` — twin at `/digital-twin` (command-center); docker n8n Publish after volume wipe = Mayank; Twilio secrets = Piyush.

Flip these in `.env` at deploy (see `.env.example` footer): `IS_PRODUCTION=true`, `TEST_MODE=false`, `FOLLOW_UP_TEST_MODE=false`, `FOLLOW_UP_DLQ_TEST=false`, real `TWILIO_*`. Optional: `NEO4J_*`, `N8N_*`, `GOOGLE_CALENDAR_*`, `BROCHURE_*`/`FLOORPLAN_*`, `COMPETITOR_KEYWORDS`, real `CRM_API_*` + `FEATURE_HUBSPOT_LIVE=true` (HubSpot skippable). Everything degrades gracefully when an integration is left unconfigured.

**Dual-path note:** Expansion 10.2/10.3 module delete is **deferred**. Root `agent.py`, `crm_sync.py`, `follow_up.py` remain shared libraries for v3 wrappers (not a second product path).

**PR #10 bus hooks (n8n):** `app/events/lead_hot.py` dual-publishes catalog `lead.hot` + alias `lead.escalated`; `session.completed` on handoff/full-qualify close; turn events include `chat_context`. `site_visit.scheduled` is published by **EE** after `CalendarExecutor` (executor has no `event_bus.publish` — by design). See `docs/N8N_INTEGRATION.md` § Dual-publish aliases.

## IREIOS 3.0 — Active agents / workflows (full parity)

Registered on the CEO bus in `main.py` lifespan (`register_*(ceo)`), all `status="active"`:

- **`followup_arm`** (`app/workflows/followup_arm.py`) — arms `FollowUpState` on `lead.created`/`conversation.updated`.
- **`lead_scoring`** (`app/agents/lead_scoring_handler.py`) — rescoring on `conversation.updated`/`lead.created`/`whatsapp.received` → publishes `lead.scored`.
- **`crm_automation`** (`app/workflows/crm_automation.py`, Task 6.1) — on `lead.*` ensures sticky assignment + AE→EE `update_crm`, publishes `lead.assigned` (idempotent).
- **`marketing_agent`** (`app/agents/marketing_agent.py`, 8.2, Wave B.4) — on `cron.weekly_report`/`campaign.completed`/`market.alert.generated` builds segmentation report → `marketing.report.generated`. Folds competitor alerts into report under `market_alert` key.
- **`customer_success_agent`** (`app/agents/customer_success_agent.py`, 8.3, Wave B.3) — on `booking.confirmed`/`payment.*`/`renewal.due`/`document.pending`/`customer.onboarded` sends WhatsApp via AE (or fallback `notify_admin`). Covers former `retention_agent`.
- **`sales_agent`** (`app/agents/sales_agent.py`, Wave B.1) — on `lead.scored`/`lead.hot`/`conversation.updated` maps NBA→AE actions (notify/schedule/send). 10min Redis debounce. Objection detection lexicon (price/timing/location/trust/competitor); persists to `LeadMemory`.
- **`kg_event_writer`** (`app/knowledge_graph/event_writers.py`, 7.4) — async Neo4j projections on core events (no-op when Neo4j down).
- **AE templates** (`app/automation_engine/templates/`, Wave B.5) — `hot_lead_notify.py` / `visit_booking.py` return validated action_request dicts. Support `template_type="n8n"` + `workflow_id` for ops fan-out.
- **Direct-invoked (not bus):** `WhatsAppAgent` (via `FEATURE_WHATSAPP_V3`), `SalesAgent` (via `POST /api/v1/leads/{id}/sales-ai`).
- **Cron (scheduler):** `competitor_monitor_job` (`app/workflows/competitor_monitor.py`, 8.4, Wave B.6) nightly 01:00 → `market.alert.generated` on `COMPETITOR_KEYWORDS` matches + writes `NotificationLog` rows for admin visibility.
- **`negotiation_agent`** (`app/agents/negotiation_agent.py`, Wave C.1) — on `lead.negotiation.started`/`lead.negotiation.counter` checks budget alignment; submits `notify_admin` (no HITL pause) when misaligned; publishes `negotiation.counter.sent`. Sets `lead.is_negotiating = True` for frontend badge.
- **`pricing_agent`** (`app/agents/pricing_agent.py`, Wave C.2) — on `pricing.query`/`lead.scored` queries `PricingRule` by location/budget; submits match via AE.
- **`inventory_agent`** (`app/agents/inventory_agent.py`, Wave C.3) — on `inventory.query`/`inventory.hold` queries `InventoryUnit` (available status); submits inventory data via AE.
- **`onboarding_agent`** (`app/agents/onboarding_agent.py`, Wave C.4) — on `customer.onboarded`/`booking.confirmed` sends WhatsApp checklist via AE.
- **`finance_agent`** (`app/agents/finance_agent.py`, Wave C.5) — on `payment.query`/`finance.schedule` submits payment info via AE.
- **`legal_agent`** (`app/agents/legal_agent.py`, Wave C.6) — on `document.required`/`legal.review` notifies admin of document needs.
- **Placeholders (skipped by CEO):** none (all 6 promoted to active in Wave C).

## IREIOS 3.0 — Neo4j Knowledge Graph (Phase 7 + BD-5 reply path)

- `app/knowledge_graph/neo4j_client.py` (`neo4j_client`) — shared driver, `run()`, `health()`, `migrate_schema()` (idempotent constraints/indexes + `:SchemaVersion{version:1}`). `KnowledgeGraph` (`neo4j_kg.py`) delegates to it.
- Schema migrate runs in lifespan (no-op when unconfigured).
- **Writes:** `kg_event_writer` on bus (`lead.created`/`qualified`/`scored`/`conversation.updated`/`assigned`/`site_visit.scheduled`). Writer **hydrates props from live Postgres** before upsert so sparse `lead.scored` payloads cannot leave stale `location`/name. WhatsAppAgent best-effort `upsert_lead` **pre-turn** (similarity anchor) and **post-turn** (same-turn field sync after qualify+score).
- **Reads on reply path (BD-5):** `WhatsAppAgent._graph_extra_context` → `graph_client.get_lead_context` → `format_graph_context_for_llm` → injected into `process_chat(..., extra_context=...)` summary for Gemini. Never blocks hard if Neo4j down.
- **Routes:** `GET /api/v1/graph/health`, `GET /api/v1/graph/leads/{id}/context` (tenant-scoped), `POST /api/v1/graph/upsert` (admin).
- `neo4j==5.28.2` in `requirements.lock`; docker service `neo4j` (7474/7687).

## WhatsApp message path (current)

```text
Twilio → /api/v1/whatsapp → lock/dedupe → process_unified_lead
  → WhatsAppAgent (graph context + qualify + score + memory extract_and_store + tools)
  → TwiML reply
  → _emit_turn_events → Redis Streams → CEO agents (CRM/score/KG/arm/Sales)
Follow-ups: FOLLOWUP_ENGINE=v3 → AE → WhatsAppExecutor
Outbound (alerts/escalation/background): app/execution_engine/outbound.py → EE
Sales hot escalate: notify_agent + create_task → agent_tasks
```

## Docs pointers

- **Active program queue (Product Phase 4 / IREIOS 4.0):** `plans/phase4/UNIFIED_EXECUTION_ORDER.md` · **G5 green 2026-08-10** · next P4-QA freeze **2026-08-20** · release **2026-09-03** · locked answers `plans/phase4/TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` · contracts `plans/phase4/IREIOS_4.0_API_CONTRACTS.md` · evidence `plans/phase4/IREIOS_4.0_EVIDENCE_PACK.md`
- **Archived IREIOS 3.0 plans:** `plans/phase3/` (do not add new Phase 4 tasks there)
- **Timeouts & timings (all race/TTL/scheduler values):** `docs/TIMEOUTS_AND_TIMINGS.md`
- n8n: Compose + AE path + **bridge** shipped; **6/6 workflows** (Gmail + Sheets). Full Cloud Console + import runbook: `docs/N8N_GOOGLE_CREDENTIALS_SETUP.md`. Arch: `docs/N8N_INTEGRATION.md`. Brochure HTTPS URLs optional until set.
- **Post-G3 automations closeout (Step 24):** `plans/phase3/PHASE3_AUTOMATIONS_CLOSEOUT.md`. Canonical bus (`lead.hot` + `trigger`). HubSpot Python stays skipped.
- **BA-1…BA-7 + bridge:** `lead_hot.py`; `chat_context`; EE visit merge; HITL paths; calendar REST; **`n8n_bridge`** (not stock Redis→n8n). Tests: `tests/test_e18_*.py`, `tests/test_e20_n8n_bridge.py`.
- Frontend remaining work: `docs/FRONTEND_BACKLOG.md` (SSE live + JWT cookie + MockSSE purged + lint/tsc/build exit 0 as of 2026-08-11)
- Evidence (3.0): `plans/phase3/IREIOS_3.0_EVIDENCE_PACK.md` (G2 + G3) · Evidence (4.0): `plans/phase4/IREIOS_4.0_EVIDENCE_PACK.md`
- **Post-G2 Waves A–D (depth fill, G3 green):** living log `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md`; how-to `plans/phase3/IREIOS_3.0_WAVE_A_D_EXPANSION.md`; tests `tests/test_e14_wave_a.py`…`test_e17_wave_d.py`. UNIFIED Steps **20–23** + Gate **G3** = `[x]`.

## WhatsApp brochure / floor plan (Approach B — shipped + post-G3 polish)

- Trigger: `detect_tool_intent` on keywords (brochure / floor plan / layout…).
- **Media:** `resolve_tool_media_url` — HTTPS-only `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` (non-HTTPS rejected).
- **Default WA path:** short caption + `take_outbound_media_url()` → TwiML `<Media>` in `main.py` (no reply-text scrape; no AE double-send; e12).
- **Chat API:** `POST /api/v1/chat` may include `media_url` in JSON when staged.
- **Sales NBA / AE:** `send_brochure` attaches `media_url` when configured.
- **Fallback:** empty env → full plain-text generators.

## IREIOS 3.0 — Event Bus / CEO / Execution Engine (Phase 1)

- **Event Bus:** `app/clients/event_bus_client.py` (`EventBusClient`, `event_bus` singleton) — Redis Streams only. `start()` before scheduler, `stop()` after, in `main.py` lifespan. CEO subscribes as a single `"*"` wildcard handler.
- **CEO:** `app/orchestrator/ceo_orchestrator.py` (`ceo` singleton) routes events to `agent_registry` subscribers; skips `placeholder` agents; publishes `{agent_id}.failed` on handler error.
- **Execution Engine:** `app/execution_engine/execution_engine.py` (`execution_engine` singleton) + `BaseExecutor`/`NoopExecutor` in `base_executor.py`. `dispatch` returns `{"status":"error","error":"no_executor"}` for unknown actions and writes a `DLQEvent` (via injectable `session_factory`, default `database.SessionLocal`) on any failure. `resolve_client_id` maps `Client_<id>` tenant ids to integer `client_id`. Registered: `send_whatsapp`, `update_crm`, `schedule_visit`, `notify_agent`, **`create_task`** (`TaskExecutor` → `agent_tasks`).
- **BaseAgent:** `app/agents/base_agent.py` runs `fetch_context → analyze → decide`; `process_event` forwards any action to `app.automation_engine.engine.submit` (Phase 1 stub → EE; Phase 2 adds approval/retry).
- `EventBusClient.publish` raises loudly if called before `start()` or if Redis is down.
- **Bus resilience (P3.8):** `_consume_loop` retries on transient Redis errors (`TimeoutError`, `RedisError`, `ConnectionError`, `OSError`) with exponential backoff: **1s → 2s → 4s → … → cap 16s**. Counter resets on any successful fetch. Gives up after **10** consecutive failures (`_MAX_CONSUME_RETRIES`). Transient blips self-heal on the next successful read. Sustained Redis outage logs error and stops the loop (bus is dead; app continues without events).

## IREIOS 3.0 — Early API envelopes + SSE (Phase 1b, FE unblock)

- `GET /api/v1/events/stream` — tenant-scoped SSE bridge from the bus. Auth: `?api_key=` / `X-API-Key` **or** the `jwt` HttpOnly cookie. Filters events to the caller's `Client_<id>`; `: ping` heartbeat every 15s; `503` if bus down.
- `GET /api/v1/events/leads/{id}/timeline` — envelope-shaped events for a lead (sourced from `event_logs` via the lead's session); `404` if not owned by the caller's client.
- `POST /api/v1/events/stub` — admin-gated (`X-Admin-Token` == `ADMIN_API_KEY`) publisher of sample events; returns `event_id`.
- Routes live in `app/api/events.py` (`events_router`), mounted in `main.py`. `EventBusClient` has `subscribe`/`unsubscribe`.
- **Smoke:**
  ```powershell
  curl -N "http://localhost:8000/api/v1/events/stream?api_key=secret-client-key-123"
  python publish_stub_event.py --event-type lead.created --tenant-id Client_1 --payload "{\"name\":\"demo\"}"
  ```
- Contracts: `plans/phase3/IREIOS_3.0_API_SSE_CONTRACTS.md`. FE cutover: `docs/FRONTEND_BACKLOG.md`. Wipes / Neo4j ops: `docs/MAINTENANCE.md` §4.1.

## Dev data wipes (soft / hard)

Postgres ≠ Neo4j — clear both when testing graph + chat. Full SQL/Cypher: `docs/MAINTENANCE.md` §4.1 and `README.md` → Resetting Test Data.

| | Postgres | Neo4j |
|--|----------|--------|
| **Soft** | TRUNCATE traffic tables; keep `clients`/`agents` | `MATCH (n:Lead) DETACH DELETE n;` |
| **Hard** | + `agents`,`clients` then `python seed.py` | `MATCH (n) WHERE NOT n:SchemaVersion DETACH DELETE n;` |
| **WA retest + clean graph** | soft PG + soft Neo4j, then send message | |

---

## Frontend-Specific

- Next.js 16 — check `node_modules/next/dist/docs/` for breaking changes before writing code
- `NEXT_PUBLIC_API_URL` must point to backend (e.g. `http://localhost:8000`)
- JWT login via server action → `POST /api/v1/auth/login` with `application/x-www-form-urlencoded` body
- Theme persisted in localStorage key `dashboard-theme` (default: dark)
- Key deps: `recharts` (charts), `jspdf` (export), `lucide-react` (icons), `next-themes` (dark mode)
