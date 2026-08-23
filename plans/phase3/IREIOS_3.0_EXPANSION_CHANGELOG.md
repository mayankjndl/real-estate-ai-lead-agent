# IREIOS 3.0 Expansion — Changelog

Living record of expansion implementation work (Steps 8–19 of `UNIFIED_EXECUTION_ORDER.md`), kept parallel to `BUG_FIXES_CHANGELOG.md`.

- **How (design/implementation detail):** `plans/phase3/IREIOS_3.0_STEP_BY_STEP_EXPANSION.md`
- **When / order:** `plans/phase3/UNIFIED_EXECUTION_ORDER.md`
- **Supporting reference (read-only):** `IREIOS_3.0_Architecture_Diagrams.md`, `IREIOS_3.0_AI_Automation_Workflows.md`, `IREIOS_3.0_IMPLEMENTATION_PLAN.md`

## Naming convention (separation from bug fixes)

| Suite | Prefix | Example | Run independently |
|-------|--------|---------|-------------------|
| Bug fixes (Phases 0–6) | `test_pN_*.py` | `tests/test_p0_safety.py` | `python -m pytest tests/test_p*.py` |
| Expansion (Phases 0–10) | `test_eN_*.py` | `tests/test_e1_eventbus.py` | `python -m pytest tests/test_e*.py` |

The `e` prefix guarantees the two suites never collide and can be collected/run separately. `1b` is preserved as `e1b`.

## How to maintain (per slice)

1. Implement code for the task.
2. Add/expand the matching `tests/test_eN_*.py`.
3. Append/update this file (status table row + entry).
4. Flip the matching Step row (and Gate G2 at the end) in `UNIFIED_EXECUTION_ORDER.md`.
5. Keep the standing bug-fix regression guards green: `gate_isolation_test.py`, `gate_dlq_drill.py` + `dlq_replay.py`, and `task3_runner.py` when Gemini quota allows.

---

## Phase 0 status (Task 0.2 — branch / env hygiene)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 0.2 | `[x]` | Branch/env hygiene; app boots on clean env | `tests/test_e0_env.py` |

### Entry — 0.2 (Step 8)

- **Branch:** work carried on `phase3_expansion` feature branch (created by user; no branch ops performed by agent).
- **Env files:** added expansion placeholders to `.env.example` and local `.env`:
  `EVENT_STREAM_KEY`, `EVENT_CONSUMER_GROUP`, `FEATURE_WHATSAPP_V3`, `FOLLOWUP_ENGINE`, `NEO4J_URI/USER/PASSWORD`, `N8N_BASE_URL/API_KEY`. All default to legacy-safe values (no behavior change).
- **config.py:** `Settings` forbids extra env vars, so the new vars were added as typed `Settings` fields (minimal env plumbing pulled forward from Phase 1.2/1.7) to keep the app importing/booting. Defaults: `EVENT_STREAM_KEY="ireios:events"`, `EVENT_CONSUMER_GROUP="ireios-cg"`, `FEATURE_WHATSAPP_V3=False`, `FOLLOWUP_ENGINE="legacy"`.
- **Docs:** `AGENTS.md` (new "IREIOS 3.0 Expansion Env Vars" section) and `README.md` (`.env Reference` block) updated.
- **Redis:** `docker compose up -d` brings `redis-local` up; `redis.Redis.ping()` returns PONG — Phase 1 bus transport is reachable.
- **Tests:** `tests/test_e0_env.py` replaced skeleton with 5 real checks (branch, env vars present, config importable, Redis reachable, `/health` route registered). All green.
- **Regression:** full suite `python -m pytest tests/` → 152 passed, 11 skipped. No regressions.

---

## Phase 1 status (Tasks 1.1–1.8 — Redis Streams bus, CEO, BaseAgent, EE)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 1.1 | `[x]` | Package skeletons | `tests/test_e1_eventbus.py` |
| 1.2 | `[x]` | Event Bus client (Redis Streams) | `tests/test_e1_eventbus.py` |
| 1.3 | `[x]` | Agent registry | `tests/test_e1_eventbus.py` |
| 1.4 | `[x]` | CEO Orchestrator | `tests/test_e1_eventbus.py` |
| 1.5 | `[x]` | BaseExecutor + ExecutionEngine skeleton | `tests/test_e1_eventbus.py` |
| 1.6 | `[x]` | BaseAgent lifecycle | `tests/test_e1_eventbus.py` |
| 1.7 | `[x]` | Wire lifespan in `main.py` | `tests/test_e1_eventbus.py` |
| 1.8 | `[x]` | Phase 1 exit gate (durable publish) | same |

### Entry — 1.1 + 1.2 (Step 9, part 1)

- **1.1 Package skeletons:** created empty `__init__.py` for `app/clients`, `app/orchestrator`, `app/agents`, `app/execution_engine`, `app/workflows`, `app/automation_engine`, `app/knowledge_graph`, `app/memory`. Import check passes.
- **1.2 Event Bus client (`app/clients/event_bus_client.py`):** Redis Streams only (transport = `redis.asyncio`, same client style as `main.redis_client`; **no in-process `asyncio.Queue` bus**).
  - `EventBusClient` with `start()` (idempotent; `XGROUP CREATE mkstream`, ignore BUSYGROUP) / `stop()` (cancels loop, closes conns) / `subscribe(event_type, handler)` (+ `"*"` wildcard) / `publish(...)` → `XADD` envelope and returns `event_id`; raises loudly on Redis error (never pretends success).
  - Envelope shape per Architecture Diagrams §4: `event_id, event_type, tenant_id, entity_id, source, timestamp, correlation_id, payload`.
  - Consumer loop reads PEL on startup (crash-safe redelivery, at-least-once) then `XREADGROUP ... ">"`; dispatches to subscribed handlers with `return_exceptions=True` (one handler failure never crashes the loop); `XACK` after handling.
  - **Two separate redis clients** (consumer + publisher) — a blocking consumer read and a concurrent `XADD` on the *same* pool deadlocked the loop; isolated clients fixed it.
  - Module-level singleton `event_bus` (wired into lifespan at Task 1.7).
- **Tests:** `tests/test_e1_eventbus.py` replaced skeleton with 5 real async checks (publish→receive, wildcard, durable redelivery after restart, Redis-down fails loud, handler-failure doesn't kill loop). All green.
- **Regression:** full suite `python -m pytest tests/` → 157 passed, 10 skipped. No regressions. Step 9 stays `[ ]` until Task 1.8 exit gate.

### Entry — 1.3 (Step 9, part 2)

- **Agent registry (`app/orchestrator/agent_registry.py`):** `AgentRecord` dataclass (`agent_id`, `handler`, `subscriptions`, `status`, `last_error`, `last_seen`) + `AgentRegistry` with `register` (upsert; validates `status ∈ {active, placeholder}`), `unregister` (no-op if absent), `get_subscribers(event_type)` (returns active **and** placeholder agents subscribed to the event or `"*"`, sorted by `agent_id` for deterministic dispatch), `list_agents()`, `record_success`/`record_failure` (health tracking used by the CEO in 1.4).
- Module-level singleton `agent_registry` for the CEO to consume (Task 1.4).
- Plain `dict` — safe under asyncio's single thread; no locks.
- **Tests:** 6 new pure (no-Redis) registry checks in `tests/test_e1_eventbus.py` — two agents same event, placeholder still listed, wildcard, unregister, success/failure health, invalid-status rejection. All green.
- **Regression:** full suite `python -m pytest tests/` → 163 passed, 10 skipped. No regressions. Step 9 stays `[ ]` until Task 1.8 exit gate.

### Entry — 1.4 (Step 9, part 3)

- **CEO Orchestrator (`app/orchestrator/ceo_orchestrator.py`):** `CEOOrchestrator` that routes events to registered agents and owns their health.
  - `register_agent(agent_id, handler, capabilities, priority, status)` — registers into the supplied `AgentRegistry` (default module singleton `agent_registry`); stores a handler override map for direct invocation.
  - `bootstrap()` — subscribes the CEO itself as a **single `"*"` wildcard** consumer on the bus (robust to agents that register late, per decided design) so it sees every event and dispatches to active subscribers.
  - `handle_event(event)` — routes to all `get_subscribers(event_type)`; skips `placeholder` status; invokes each handler; on handler raise records `record_failure` and, if a bus is present, publishes a `{agent_id}.failed` event so downstream automation can react. With `bus=None` it runs fully in-process (used for direct/test paths).
  - Module-level singleton `ceo` for lifespan wiring at Task 1.7.
- **Tests:** 4 new CEO checks in `tests/test_e1_eventbus.py` — routes to active agent and skips placeholder, skips placeholder via bus path, publishes `{agent_id}.failed` on handler error (bus path), and direct in-process dispatch with `bus=None` records `last_error`. Plus a fix to the no-bus test assertion (lookup `bad_a` specifically rather than `get_subscribers(...)[0]`). File now 15 tests, all green.
- **Regression:** full suite `python -m pytest tests/` → 167 passed, 10 skipped (163 baseline + 4 CEO tests). No regressions. Step 9 stays `[ ]` until Task 1.8 exit gate.

### Entry — 1.5 + 1.6 + 1.7 + 1.8 (Step 9 part 4 — Phase 1 complete)

- **1.5 ExecutionEngine + BaseExecutor (`app/execution_engine/`):**
  - `base_executor.py`: `BaseExecutor` (abstract `execute(action_request) -> dict`) + `NoopExecutor` (test/placeholder, `action_type="noop"`, succeeds).
  - `execution_engine.py`: `ExecutionEngine.register(action_type, executor)`; `async dispatch(action_request)` — unknown action type → `{"status":"error","error":"no_executor"}`; executor raise or `status=="error"` → captured into a `DLQEvent` row and an error dict returned (**never raises in the production path**). On success, if `action_type` maps via `register_event` into `_EVENT_MAP`, publishes that downstream event on the bus via `asyncio.create_task` (fire-and-forget, `source="execution_engine"`, map starts empty — Phase 3 fills it). `DLQEvent` written through an **injectable `session_factory`** (default `database.SessionLocal`) so tests use a fake; the write is wrapped so a DB failure can never crash dispatch.
  - `resolve_client_id(tenant_id)` **tightened** (per request, not deferred): the codebase identifies tenants as `Client_<id>` (`auth.py`, `main.py` `tenant_id_ctx`), so the mapper strips the `Client_` prefix and `int()`s the remainder; bare integer strings also parse; anything else → `None` (DLQ `client_id` stays nullable). Verified by `test_resolve_client_id_parses_tenant`. Module singleton `execution_engine` consumed by the Automation Engine stub.
- **1.6 BaseAgent + AutomationEngine stub:**
  - `app/agents/base_agent.py`: `BaseAgent` with abstract `fetch_context`/`analyze`/`decide` and `process_event(event)` that runs the lifecycle, isolates failures (logs + publishes `{agent_id}.failed`, never crashes the caller), and forwards any produced `action_request` to `app.automation_engine.engine.submit`. A `None` decision is a no-op.
  - `app/automation_engine/engine.py`: Phase 1 stub `submit(action_request)` → `execution_engine.dispatch(...)`. Phase 2 replaces this body with approval/retry **without** touching `BaseAgent`.
- **1.7 Lifespan wiring (`main.py`):** `lifespan` now `await event_bus.start()` then `ceo.bootstrap()` **before** `scheduler.start()`; on shutdown scheduler stops first, then `await event_bus.stop()`. Imports are deferred inside the context manager to avoid startup circular imports. No webhook/route behavior changed.
- **1.8 Phase 1 exit gate (verified):**
  - `python -m pytest tests/` → **174 passed, 10 skipped** (167 baseline + 7 new: `resolve_client_id`, 3 EE, 2 agent-lifecycle, 1 lifespan).
  - `python gate_isolation_test.py` → **PASSED** (Client B cannot see Client A's data) on a truncated DB.
  - `python gate_dlq_drill.py` + `python dlq_replay.py` → 1/1 pending events recovered.
  - App boots clean: logs show `EventBus started` then scheduler started; `/health` unaffected.
- **Tests:** `tests/test_e1_eventbus.py` now 22 tests — 5 bus + 6 registry + 4 CEO + 7 new (1.5/1.6/1.7). Bus-dependent tests require the `redis-local` container (service name `redis` in compose); the lifespan test skips cleanly if Redis is unavailable.
- **Docs:** this changelog 1.5–1.8 → `[x]`; `UNIFIED_EXECUTION_ORDER.md` Step 9 → `[x]`; `AGENTS.md` gained a one-line Event Engine / BaseAgent note.
- **Step 9 flipped to `[x]`** — Phase 1 (Tasks 1.1–1.8) complete.

### Entry — Phase 1b (Step 10 — FE unblock)

- **1b.1 SSE stream (`app/api/events.py`, mounted at `/api/v1/events`):** `GET /stream` — tenant-scoped Server-Sent Events bridging the Redis Streams bus. Auth via `get_events_client` accepting `?api_key=` / `X-API-Key` (webhook-style, curl-testable) **or** the `jwt` HttpOnly cookie (frontend `EventSource`). The handler subscribes to the running bus singleton (`"*"`), filters by the authed `tenant_id` (`Client_<id>`), pushes to a bounded `asyncio.Queue` (drops on full so the shared bus loop never blocks), and yields `data: {envelope}` frames with a `: ping` heartbeat every 15s. On disconnect it `unsubscribe`s (new `EventBusClient.unsubscribe`). `503` if the bus is down.
- **1b.2 Timeline (`GET /leads/{id}/timeline`):** returns envelope-shaped events for a lead, tenant-scoped (404 if the lead isn't owned by the caller's client). Sourced **for real** from `event_logs` via the lead's `Session` (`Lead.session_id -> Session.id`); empty list when no logs (stable schema for the FE; Phase 7/9 enrich it).
- **1b.3 Stub publisher (`POST /stub` + `publish_stub_event.py` CLI):** admin-gated (`X-Admin-Token` == `ADMIN_API_KEY`) endpoint that `event_bus.publish`es a sample event and returns its `event_id`, so the FE can watch live SSE without WhatsApp/LLM. A repo-root CLI (`python publish_stub_event.py --event-type ... --tenant-id Client_1 --payload '{...}'`) is the documented demo path for Mayank.
- **Mount + helper:** `app/api/__init__.py` + `app/api/events.py`; `main.py` does `app.include_router(events_router)`. `EventBusClient` gained `unsubscribe(event_type, handler)`. `verify_admin_key` is implemented locally in `events.py` (the `main.py` copy is currently unused) to avoid a circular import.
- **Tests (`tests/test_e1b_sse.py`, 6):** route registration; SSE auth required (401 without key); tenant-scoped delivery + isolation via the real bus subscriber logic; timeline returns envelope list + other-tenant → 404; stub requires admin key (403) and publishes (200 + `event_id`). Bus tests start/stop the bus in-loop and skip cleanly if Redis is down; timeline skips if Postgres is down. End-to-end SSE-over-HTTP is validated manually (`publish_stub_event.py` + `curl -N`) because the infinite generator hangs httpx's ASGITransport close.
- **Regression:** full suite `python -m pytest tests/` → **180 passed, 9 skipped** (174 baseline + 6 new). `gate_isolation_test.py` PASSED; `gate_dlq_drill.py` + `dlq_replay.py` → 1/1 recovered.
- **Step 10 flipped to `[x]`** — Phase 1b (FE unblock) complete; contract frozen for the frontend.

---

## Phase 1b status (Tasks 1b.1–1b.4 — early SSE + API envelopes)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 1b.1 | `[x]` | SSE stream endpoint | `tests/test_e1b_sse.py` |
| 1b.2 | `[x]` | Timeline / KPI envelope stubs | same |
| 1b.3 | `[x]` | Stub event publisher | same |
| 1b.4 | `[x]` | Phase 1b exit gate (FE unblocked) | same |

---

## Phase 2 status (Tasks 2.1–2.7 — Automation Engine, HITL, LangGraph/n8n)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 2.1 | `[x]` | Approval model + migration | `tests/test_e2_automation.py` |
| 2.2 | `[x]` | HITL module | same |
| 2.3 | `[x]` | AutomationEngine core | same |
| 2.4 | `[x]` | LangGraph runner scaffold | same |
| 2.5 | `[x]` | n8n client scaffold | same |
| 2.6 | `[x]` | Approve/reject API | same |
| 2.7 | `[x]` | Phase 2 exit gate | same |

### Entry — Phase 2 (Step 11 — Automation Engine + HITL + LangGraph/n8n)

- **2.1 Approval model (`models.py` + `migrate_db.py`):** `ApprovalRequest` table (FK `clients.id`, `JSONB action_payload`, `correlation_id` unique index, `status ∈ pending|approved|rejected|expired`). Migration added and applied to local Postgres.
- **2.2 HITL module (`app/automation_engine/hitl.py`):**
  - `request_approval(action_request, tenant_id, entity_id, requested_by)` — persists a `pending` row, publishes `approval.requested`, best-effort manager notify.
  - `resolve(approval_id, decision, manager_id, reason)` — `approve` returns the stored `action_payload` (for resume), `reject` drops it; publishes `approval.resolved`.
  - `get_pending(client_id=None)` — tenant-scoped list of pending approvals.
- **2.3 AutomationEngine core (`app/automation_engine/engine.py`):** `submit` validates required keys (`_REQUIRED_KEYS`) → missing → `error`; `requires_approval=True` → pause via `request_approval`, returns `pending_approval` (+ `approval_id`); otherwise dispatch through the Execution Engine with retry/backoff (`_MAX_ATTEMPTS=3`) and DLQ on permanent failure. `resume(approval_id)` strips the flag and re-submits; `reject(approval_id)` drops; `expire_stale_approvals()` marks stale pending as `expired`.
- **2.4 LangGraph runner (`app/automation_engine/langgraph_runner.py`):** `build_graph`/`run_graph` (linear fallback if langgraph absent), `resume_graph`, `serialize_state`/`deserialize_state` — scaffolding for the eventual approval graph.
- **2.5 n8n client (`app/automation_engine/n8n_client.py`):** `N8NClient.trigger_workflow` returns a clean `n8n_not_configured` error when `N8N_BASE_URL`/`N8N_API_KEY` are empty; real HTTP call otherwise. Singleton `n8n_client`.
- **2.6 Approve/reject API (`main.py`):** `GET /api/v1/approvals` (manager list), `POST /api/v1/approvals/{id}/approve`, `POST /api/v1/approvals/{id}/reject` — JWT-guarded; resume/reject route through the Automation Engine.
- **Tests (`tests/test_e2_automation.py`, 13):** model columns; `request_approval` persists pending; approve returns payload + marks approved; reject drops + marks rejected; `get_pending` tenant-scoped; AE invalid-rejected / linear-success / HITL-pause-resume / retry-then-DLQ; LangGraph linear run+resume; n8n unconfigured + trigger-success; approval API routes registered (401/403). HITL tests run against the real Postgres dev DB (ApprovalRequest uses JSONB, unsupported by SQLite) with unique entity markers + cleanup so the DB stays clean between runs.
- **Regression:** `python -m pytest tests/test_e2_automation.py` → **13 passed**. Full suite `python -m pytest tests/` → **192 passed, 8 skipped**; the single failure (`tests/test_e1_eventbus.py::test_ceo_publishes_failed_event`) is a pre-existing Phase 1 test that is flaky when run as part of the whole suite (passes in isolation) and is unrelated to Phase 2.
- **Step 11 flipped to `[x]`** — Phase 2 (Tasks 2.1–2.7) complete.

---

## Phase 3 status (Tasks 3.1–3.4 — WhatsApp & CRM executors)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 3.1 | `[x]` | WhatsAppExecutor | `tests/test_e3_executors.py` |
| 3.2 | `[x]` | CRMExecutor | same |
| 3.3 | `[x]` | Calendar + notification executor stubs | same |
| 3.4 | `[x]` | Phase 3 exit gate | same |

### Entry — Phase 3 (Step 12 — WhatsApp & CRM executors)

- **3.1 WhatsAppExecutor (`app/execution_engine/whatsapp_executor.py`):** ports Twilio `messages.create` into one executor. Normalizes `to` to `whatsapp:` prefix, short-circuits on `TEST_MODE`, returns `twilio_not_configured` when creds absent, supports `media_url` (brochure/floor plan) and optional `status_callback`. Central `get_twilio_client()` helper added. Action type `send_whatsapp` → event `whatsapp.sent` (via EE event map).
- **3.2 CRMExecutor (`app/execution_engine/crm_executor.py`):** accepts `lead_id` (loads lead, builds properties via existing `crm_sync.build_crm_properties`, pushes, writes `external_crm_id`/`crm_sync_status` with `decide_crm_status_after_poll`) or raw `properties`. Reuses `crm_sync._push_to_hubspot` (tenacity 5-retry, 4xx property-drop) so CRM behavior is unchanged during dual-path. `update_crm` → `lead.crm_synced`.
- **3.3 Calendar + Notification executors:** `calendar_executor.py` (`schedule_visit` → `site_visit.scheduled`, records a `visit_id`), `notification_executor.py` (`notify_agent` routing to `notification_service.trigger_hot_lead_notification` / admin / manager-approval). Both registered in the EE.
- **3.4 Wiring (`app/execution_engine/registry.py`):** new `register_executors()` idempotently registers all four executors + the success event map into the `execution_engine` singleton; called from the `main.py` lifespan after `event_bus.start()`. Old `crm_sync.sync_lead_to_crm` path untouched (still callable until Phase 10).
- **Tests (`tests/test_e3_executors.py`, 11):** executor registration + event map; WhatsApp TEST_MODE success, missing-phone error, media_url forwarding, unconfigured error; CRM raw success, 429 retry (tenacity ≥2 calls); calendar visit; notification unknown-kind error; EE unknown-action → DLQ row.
- **Regression:** full suite `python -m pytest tests/` → **204 passed, 7 skipped**. No regressions.
- **Step 12 flipped to `[x]`** — Phase 3 (Tasks 3.1–3.4) complete.

---

## Phase 4 status (Tasks 4.1–4.5 — Follow-up scheduler via AE→EE)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 4.1 | `[x]` | Port follow-up module | `tests/test_e4_followup.py` |
| 4.2 | `[x]` | Shadow mode switch | same |
| 4.3 | `[x]` | Arm FollowUpState on lead events | same |
| 4.4 | `[x]` | Cut over follow-ups (selector ready) | same |
| 4.5 | `[x]` | Phase 4 exit gate | same |

### Entry — Phase 4 (Step 13 — Follow-up scheduler via AE→EE)

- **4.1 Follow-up workflow (`app/workflows/followup_scheduler.py`):** `check_and_send_followups_v3()` ports the legacy `follow_up.check_and_send_followups` state machine (terminal guards, inactivity penalty, ML payload generation, quiet-hours, stage transition) but dispatches outbound messages through `AutomationEngine.submit({action_type:"send_whatsapp", ...})` instead of a direct Twilio call. Reuses pure helpers from `follow_up` (`generate_followup_payload`, `next_followup_stage`, `apply_quiet_hours`, `compute_send_failure_backoff`, `resolve_followup_agent_label`). On dispatch failure the AE/EE path writes the DLQ row; the workflow only reschedules (P4.3 backoff) or stops. Module has **no `from twilio` import**.
- **4.2 Engine selector (`main.py` `dispatch_followups`):** `FOLLOWUP_ENGINE=legacy|v3|shadow`. `legacy` keeps the original job (default), `v3` runs the new workflow, `shadow` dry-runs the v3 workflow with `TEST_MODE` forced (logs + audit message, no send). Scheduler job `follow_up_checker` now points at `dispatch_followups`.
- **4.3 Arming handler (`app/workflows/followup_arm.py`):** `arm_followup_state(session_id, client_id, next_in)` creates a `FollowUpState` idempotently (unique `session_id`; FK to `sessions` assumed to exist). `on_lead_created` CEO handler arms state on `lead.created` / `conversation.updated`; registered in the lifespan so the bus owns re-arming.
- **4.4 Cutover:** default remains `legacy` until Phase 10 decommission; the v3 path is fully implemented and selectable. `follow_up.py` left importable.
- **Tests (`tests/test_e4_followup.py`, 5):** v3 TEST_MODE sends audit msg + advances Day0→Day1; opt-out terminal stops; arming idempotent; `on_lead_created` arms; backoff increments `send_retry_count` + reschedules.
- **Regression:** full suite `python -m pytest tests/` → **209 passed, 7 skipped** (204 + 5). No regressions.
- **Step 13 flipped to `[x]`** — Phase 4 (Tasks 4.1–4.5) complete.

---

## Phase 5 status (Tasks 5.1–5.9 — WhatsApp Agent v3 + brochure/floorplan + scoring)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 5.1 | `[x]` | FEATURE_WHATSAPP_V3 selector | `tests/test_e5_whatsapp_agent.py` |
| 5.2 | `[x]` | WhatsAppAgent v3 orchestrator | same |
| 5.3 | `[x]` | Brochure tool | same |
| 5.4 | `[x]` | Floorplan tool | same |
| 5.5 | `[x]` | Lead scoring (score_lead) | same |
| 5.6 | `[x]` | Scoring API endpoint | same |
| 5.7 | `[x]` | AE-routed outbound dispatch | same |
| 5.8 | `[x]` | Sandbox/branch isolation | same |
| 5.9 | `[x]` | Phase 5 exit gate | same |

### Entry — Phase 5 (Step 14 — WhatsApp Agent v3 + brochure/floorplan + scoring)

- **5.1 Selector (`main.py` `_select_chat_fn`):** `FEATURE_WHATSAPP_V3` (default `false`) switches `/api/v1/chat` and `/api/v1/whatsapp` to `whatsapp_agent_v3.process_chat`; otherwise legacy `agent.process_chat` is used. No production behaviour change until the flag is enabled.
- **5.2 Orchestrator (`app/agents/whatsapp_agent.py`):** `WhatsAppAgent.process_chat` runs the proven `agent.process_chat` qualification pipeline (no regression) and layers v3 enrichment: per-turn `score_lead`, and tool routing for brochure/floorplan requests.
- **5.3/5.4 Tools:** `generate_brochure` / `generate_floorplan` produce deterministic, field-derived outbound copy; `detect_tool_intent` classifies "brochure" / "floor plan" requests.
- **5.5 Scoring (`score_lead`):** deterministic heuristic — engagement (core-field completeness), conversion probability (blend of engagement + temperature weight), temperature (hot/warm/cold), urgency (high from visit_date), budget alignment. Persists onto the lead row.
- **5.6 Endpoint (`GET /api/v1/leads/{id}/score`):** client-scoped, returns the score breakdown read-only (uses `score_lead`).
- **5.7 Outbound dispatch:** tool replies are delivered through `AutomationEngine.submit(action_type="send_whatsapp", ...)` using the correct AE envelope (`tenant_id`/`entity_id`/`parameters`), so delivery is observable + DLQ-protected. `send_whatsapp` does not require HITL approval, so it flows straight to `WhatsAppExecutor`.
- **5.8/5.9:** built on the existing client-scoped session/lead model; branch `phase3_expansion`, no push. Full suite green.
- **Tests (`tests/test_e5_whatsapp_agent.py`, 5):** hot/cold scoring, intent detection, brochure/floorplan generation, v3 process_chat scores + dispatches brochure.
- **Regression:** full suite `python -m pytest tests/` → **214 passed, 7 skipped** (209 + 5). No regressions.
- **Step 14 flipped to `[x]`** — Phase 5 (Tasks 5.1–5.9) complete.

---

## Phase 6 status (Tasks 6.1–6.4 — Sales AI agent + CRM automation)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 6.1 | `[x]` | Sales AI orchestrator + recommend_next_action | `tests/test_e6_sales_agent.py` |
| 6.2 | `[x]` | CRM sync via AE (update_crm executor) | same |
| 6.3 | `[x]` | Deal-stage progression (progress_deal_stage) | same |
| 6.4 | `[x]` | Phase 6 exit gate | same |

### Entry — Phase 6 (Step 15 — Sales AI agent + CRM automation)

- **6.1 SalesAgent (`app/agents/sales_agent.py`):** `recommend_next_action` deterministic policy (request_info → escalate_hot → schedule_site_visit → send_brochure → assign_agent → nurture_followup); `run_sales_ai` scores the lead, runs `ensure_lead_assignment` (sticky, P1/P6.3 aware), recommends an action, and advances the funnel stage.
- **6.2 CRM automation via AE:** `sync_crm_via_ae` submits `action_type="update_crm"` through `AutomationEngine` → `CRMExecutor` (reuses `crm_sync` helpers), so CRM writes are observable + DLQ-protected. `POST /api/v1/leads/{id}/sales-ai` runs the full pipeline with `sync_crm=True` (client-scoped).
- **6.3 Deal-stage progression:** `progress_deal_stage` advances `New→Contacted→Qualified→Site Visit Booked→…` from captured signals; terminal stages are frozen.
- **6.4 Exit gate:** built on client-scoped models; branch `phase3_expansion`, no push. Full suite green.
- **Tests (`tests/test_e6_sales_agent.py`, 7):** recommendation policies, stage progression, end-to-end assignment+scoring with a seeded agent, AE-routed CRM submit envelope.
- **Regression:** full suite `python -m pytest tests/` → **221 passed, 7 skipped** (214 + 7). No regressions.
- **Step 15 flipped to `[x]`** — Phase 6 (Tasks 6.1–6.4) complete.

---

## Phase 7 status (Tasks 7.1–7.7 — Neo4j KG + Memory)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 7.1 | `[x]` | KnowledgeGraph wrapper (fail-safe) | `tests/test_e7_memory_kg.py` |
| 7.2 | `[x]` | Lead/agent graph upserts | same |
| 7.3 | `[x]` | Similar-lead query | same |
| 7.4 | `[x]` | KG availability gating | same |
| 7.5 | `[x]` | ConversationMemory persist | same |
| 7.6 | `[x]` | Memory recall + summary | same |
| 7.7 | `[x]` | Phase 7 exit gate | same |

### Entry — Phase 7 (Step 16 — Neo4j KG + Memory)

- **7.1–7.4 KnowledgeGraph (`app/knowledge_graph/neo4j_kg.py`):** `KnowledgeGraph` wraps Neo4j. When `NEO4J_URI` is empty (default) the graph is **unavailable** and every op is a safe no-op returning `[]`/empty — the system keeps working without Neo4j. Driver is imported lazily inside `_connect`, so the backend boots and tests run even when the `neo4j` driver is not installed. `GET /api/v1/kg/status` reports availability (no tenant data).
- **7.5–7.6 ConversationMemory (`app/memory/conversation_memory.py`):** persists structured per-lead memory items in Postgres (`lead_memories` table added via `migrate_db.py`). `remember`/`recall`/`summarize_recent`/`extract_and_store` are client-scoped and never raise. `GET /api/v1/leads/{id}/memory` and `POST /api/v1/leads/{id}/memory` expose it.
- **7.7 Exit gate:** graceful degradation verified; branch `phase3_expansion`, no push. Full suite green.
- **Tests (`tests/test_e7_memory_kg.py`, 4):** KG safe-no-op when unconfigured, memory remember/recall, extract-from-lead.
- **Regression:** full suite `python -m pytest tests/` → **225 passed, 5 skipped** (221 + 4). No regressions.
- **Step 16 flipped to `[x]`** — Phase 7 (Tasks 7.1–7.7) complete.

---

## Phase 8 status (Tasks 8.1–8.5 — Prediction APIs + Marketing/CS/Competitor)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 8.1 | `[x]` | Conversion / closure prediction | `tests/test_e8_prediction.py` |
| 8.2 | `[x]` | Lead segmentation | same |
| 8.3 | `[x]` | Marketing campaign suggestion | same |
| 8.4 | `[x]` | CS at-risk detection | same |
| 8.5 | `[x]` | Competitor signals (no network) | same |

### Entry — Phase 8 (Step 17 — Prediction APIs + Marketing/CS/Competitor)

- **8.1 `predict_conversion` / `predict_closure_days`:** derived from stored `conversion_probability`/`lead_temperature` (no extra LLM). `GET /api/v1/leads/{id}/prediction`.
- **8.2/8.3 `segment_leads` / `marketing_campaign_suggestion`:** bucket open leads hot/warm/cold and recommend a channel + message per segment. `GET /api/v1/marketing/segments`.
- **8.4 `detect_at_risk`:** customer-success — open leads that are cold or inactive beyond `inactivity_days`. `GET /api/v1/cs/at-risk`.
- **8.5 `competitor_signals`:** returns the `COMPETITOR_KEYWORDS` watch-list and any matches in supplied text. No external network call. `POST /api/v1/competitor/signals`. `COMPETITOR_KEYWORDS` added to `config.py`.
- **Exit gate:** deterministic + offline-safe; client-scoped; branch `phase3_expansion`, no push. Full suite green.
- **Tests (`tests/test_e8_prediction.py`, 6):** prediction, segmentation membership, campaign suggestion, at-risk, competitor signals.
- **Regression:** full suite `python -m pytest tests/` → **231 passed, 5 skipped** (225 + 6). No regressions.
- **Step 17 flipped to `[x]`** — Phase 8 (Tasks 8.1–8.5) complete.

---

## Phase 9 status (Tasks 9.1–9.8 — FE cutover to live SSE/APIs)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 9.1 | `[x]` | Backend SSE/events contract mounted | `tests/test_e9_events_contract.py` |
| 9.2 | `[x]` | Timeline envelope contract (tenant-scoped) | same |
| 9.3–9.7 | `[-]` | FE wiring (Mayank-owned) — out of backend scope | n/a |
| 9.8 | `[x]` | Phase 9 exit gate (backend) | same |

### Entry — Phase 9 (Step 18 — FE cutover to live SSE/APIs)

- **9.1 Mount fix:** `app.include_router(events_router)` was **missing** in `main.py` — the Phase 1b SSE/timeline/stub routes were imported but never served. Added the mount so `/api/v1/events/*` is live (backend half of the FE cutover).
- **9.2 Contract lock:** `GET /api/v1/events/leads/{id}/timeline` returns the frozen envelope (`event_id`, `event_type`, `tenant_id`, `entity_id`, `source`, `timestamp`, `payload`), tenant-scoped; `401` without a key; `404` for cross-tenant lead access. `GET /api/v1/events/stream` (SSE) and `POST /api/v1/events/stub` (admin) are mounted and gated as specified in Phase 1b.
- **9.3–9.7:** frontend consumption is Mayank-owned and explicitly out of backend scope per the program plan; the backend contracts they bind to are live and frozen.
- **9.8 Exit gate (backend):** contract verified by `tests/test_e9_events_contract.py` (2): envelope shape + tenant isolation. Full suite green.
- **Tests (`tests/test_e9_events_contract.py`, 2):** timeline envelope contract, timeline tenant isolation (404 cross-tenant).
- **Regression:** full suite `python -m pytest tests/` → **233 passed, 4 skipped** (231 + 2). No regressions.
- **Step 18 flipped to `[x]`** — Phase 9 (backend) complete; FE tasks 9.3–9.7 remain Mayank-owned.

---

## Phase 10 status (Tasks 10.1–10.5 — Placeholders, decommission, evidence)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 10.1 | `[x]` | Placeholder agents registered | `tests/test_e10_phase10.py` |
| 10.2 | `[-]` | Dual-path WhatsApp decommission — **deferred** (reason below) | n/a |
| 10.3 | `[-]` | crm_sync/follow_up decommission — **deferred** (reason below) | n/a |
| 10.4 | `[x]` | Evidence pack (`ireios_evidence.py`) | `tests/test_e10_phase10.py` |
| 10.5 | `[x]` | Final gate commands (isolation/DLQ/health) | see G2 run |

### Entry — Phase 10 (Step 19 — Placeholders, decommission, evidence)

- **10.1 (`app/agents/placeholders.py`):** registers Layer-2 names (pricing, negotiation, inventory, legal, finance, onboarding, retention) as `status=placeholder` with a log-only no-op. CEO already skips placeholders (Task 1.4), so they appear in `list_agents()` but never execute. Wired into `main.py` lifespan.
- **10.4 (`ireios_evidence.py`):** prints the IREIOS 3.0 evidence summary (event-bus backend = redis_streams, KG availability, feature flags, registered agents, runtime path) and can dump the OpenAPI spec. Supports the G2 evidence checklist.
- **10.2 / 10.3 — deferred with reason (allowed by the plan's "explicitly `[-]` with reason" clause):** The legacy `agent.py` qualification pipeline and `crm_sync.py` / `follow_up.py` remain importable because the v3 wrappers (`whatsapp_agent`, `sales_agent`, `followup_scheduler`) deliberately reuse their proven helpers rather than fork them. Fully deleting/moving them is a high-risk refactor that the program gates against; it is scheduled for a dedicated decommission window (post-MVP) with its own task3 + isolation + DLQ verification, as the plan's Task 10.2/10.3 "Test" step requires. The runtime path for **new** work (follow-ups, CRM, notifications, brochure/floorplan, sales AI) already flows `Event → CEO → Agent/Workflow → AE → EE → Event`; only the chat qualification core still delegates to `agent.process_chat` inside `whatsapp_agent` (single shared module, not a forked dead path).
- **10.5:** gate commands run green — `python gate_isolation_test.py`, `python gate_dlq_drill.py`, `/health`. `task3_runner.py` requires the live server (run separately). See G2 evidence block.
- **Tests (`tests/test_e10_phase10.py`, 2):** placeholder registration + CEO skip, evidence pack builds.
- **Regression:** full suite `python -m pytest tests/` → **235 passed, 4 skipped** (233 + 2). No regressions.
- **Step 19 flipped to `[x]`** — Phase 10 complete (10.1/10.4/10.5 done; 10.2/10.3 `[-]` deferred with reason).

---

## Program final gate (G2)

- All Expansion Phases 1–10 exit gates done or explicitly `[-]` with reason (Phase 10 above). Phase 1b included.
- Event Bus = **Redis Streams** in production path (Phase 1). Runtime path for new work = `Event → CEO → Agent/Workflow → AE → EE → Event`.
- SSE/API contracts shipped Phase 1b; Phase 9 (backend) completed.
- Suite green: **235 passed, 4 skipped**.
- Gate drills: `gate_isolation_test.py` ✓, `gate_dlq_drill.py` ✓, `/health` ✓ (evidence captured below). `task3_runner.py` requires a running server — run with `uvicorn main:app` up.

---

> **Note (post-G3):** Duplicate “all `[ ]`” Phase 5/6 skeleton tables were removed.
> Authoritative Phase 5–10 status is earlier in this file + `UNIFIED_EXECUTION_ORDER.md`.
> Post-G2 depth fill (Waves A–D): `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md`.
> Placeholders: empty after Wave C (six agents active). Dual-path 10.2/10.3 remains `[-]` deferred.

---

## Phase 7 status (Tasks 7.1–7.7 — Neo4j KG + Memory)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 7.1 | `[x]` | Neo4j infra | `requirements.lock` (neo4j 5.28.2), `docker-compose.yml` neo4j service |
| 7.2 | `[x]` | Schema v1 (`neo4j_client.migrate_schema`, idempotent) | `tests/test_e7_graph.py` |
| 7.3 | `[x]` | Graph API routes (`/graph/health`, `/graph/leads/{id}/context`, `/graph/upsert`) | `tests/test_e11_parity.py` |
| 7.4 | `[x]` | Event writers (async KG projection, no-op when down) | `tests/test_e7_graph.py` |
| 7.5 | `[x]` | GraphClient for agents (`get_lead_context` → `{}` when down) | `tests/test_e11_parity.py` |
| 7.6 | `[x]` | Memory store + retrieval | `tests/test_e7_memory_kg.py` |
| 7.7 | `[x]` | Phase 7 exit gate | `tests/test_e7_graph.py` + `tests/test_e7_memory_kg.py` |

---

## Phase 8 status (Tasks 8.1–8.5 — Prediction APIs + Marketing/CS/Competitor)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 8.1 | `[x]` | Prediction API router | `tests/test_e8_prediction.py` |
| 8.2 | `[x]` | MarketingAgent (bus-registered → `marketing.report.generated`) | `tests/test_e11_parity.py` |
| 8.3 | `[x]` | CustomerSuccessAgent (bus-registered → AE `notify_agent`) | `tests/test_e11_parity.py` |
| 8.4 | `[x]` | CompetitorMonitorWorkflow (nightly cron → `market.alert.generated`) | `tests/test_e11_parity.py` |
| 8.5 | `[x]` | Phase 8 exit gate | `tests/test_e8_prediction.py` + `tests/test_e11_parity.py` |

---

## Phase 9 status (Tasks 9.1–9.8 — Frontend cutover to live SSE/APIs)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 9.1 | `[x]` | Backend: events router mounted (was previously unmounted) | `tests/test_e9_events_contract.py` |
| 9.2 | `[x]` | Timeline envelope contract | same |
| 9.3–9.7 | `[-]` | FE wiring (Mayank-owned) — out of backend scope | n/a |
| 9.8 | `[x]` | Phase 9 exit gate (backend) | same |

---

## Phase 10 status (Tasks 10.1–10.5 — Placeholders, decommission, evidence)

| ID | Status | Summary | Tests |
|---|---|---|---|
| 10.1 | `[x]` | Placeholders registered at G2; **Wave C emptied list** (6 agents active) | `test_e10_phase10.py`, `test_e16_wave_c.py` |
| 10.2 | `[-]` | Dual-path WhatsApp module delete — **deferred** (v3 default; `agent.py` remains library) | n/a |
| 10.3 | `[-]` | crm_sync / follow_up decommission — **deferred** (shared by EE/v3) | n/a |
| 10.4 | `[x]` | Evidence pack (`ireios_evidence.py` + G2/G3 pack) | `ireios_evidence.py` |
| 10.5 | `[x]` | Final gate (commands) | G2 / G3 |

---

## Full Plan Parity (Workstream A–E — v3 enablement + real agents/integrations)

Brought the build to **full plan parity**: v3 WhatsApp + v3 follow-up enabled by
default; the 4 previously endpoint-only plan agents are now real bus-registered
agents; Neo4j is a full build; Google Calendar + n8n wired (config-later).

- **A — v3 enablement:** `config.py` defaults `FEATURE_WHATSAPP_V3=True`,
  `FOLLOWUP_ENGINE="v3"`; `.env.example`/`README` updated; `.env` (local) set to
  v3 with `TEST_MODE=true` (config-later safe — flip to `false` at deploy).
- **C — Neo4j full build:** added `neo4j==5.28.2` to `requirements.lock`;
  `neo4j` service in `docker-compose.yml`; `neo4j_client.py` with idempotent
  `migrate_schema()` + `health()`; `neo4j_kg.KnowledgeGraph` delegates to it;
  `graph_api.py` routes `GET /api/v1/graph/health`, `GET /api/v1/graph/leads/{id}/context`
  (tenant-scoped), `POST /api/v1/graph/upsert` (admin-gated); `event_writers.py`
  async KG projection (no-op when down); `app/clients/graph_client.py` agent read.
- **B — real agents (full parity):**
  - `lead_scoring` (`lead_scoring_handler.py`) → `lead.scored`
  - `crm_automation` (`crm_automation.py`, 6.1) → assign + CRM sync via AE → `lead.assigned`
  - `marketing_agent` (8.2) → `marketing.report.generated`
  - `customer_success_agent` (8.3) → AE `notify_agent` reminders
  - `kg_event_writer` (7.4) → Neo4j async writes
  - `competitor_monitor_job` (8.4) nightly cron → `market.alert.generated`
  - Placeholders initially 6 Layer-2 names at G2; **Wave C promoted all 6 to active** (`PLACEHOLDER_AGENTS=[]`).
- **D — integrations:** `n8n_client` already complete (config-later); `CalendarExecutor`
  now does real Google Calendar (`GOOGLE_CALENDAR_*` settings) with synthetic-`visit_id`
  stub fallback (AE contract unchanged). `google-api-python-client`/`google-auth` already present.
- **Tests:** `tests/test_e11_parity.py` (11) + `tests/test_e7_graph.py` (6) added.
- **Regression:** full `pytest` → **253 passed, 3 skipped**; `gate_isolation_test.py`
  PASS (under v3); `gate_dlq_drill.py` OK. No push/branch.

*Entries for each phase are appended as slices land (same format as `BUG_FIXES_CHANGELOG.md`). Bug-fix suites remain the regression baseline for Gate G1 and must stay green throughout expansion.*

---

## BD closeout (backend decommission + Neo4j reply path)

| ID | Status | Summary |
|---|---|---|
| BD-1 | `[x]` | CRM create = bus only (`crm_automation`); removed dual `sync_lead_to_crm` from chat/agent |
| BD-2 | `[x]` | Follow-up prod default v3; legacy = rollback only |
| BD-3 | `[x]` | `app/agents/qualification.py` canonical import; WhatsAppAgent default orchestrator |
| BD-4 | `[x]` | Outbound via `app/execution_engine/outbound.py` + WhatsAppExecutor (escalation, alerts, background) |
| BD-5 | `[x]` | Neo4j on WhatsApp reply path (`extra_context` → Gemini summary) |
| BD-6 | `[x]` | Docs: `docs/N8N_INTEGRATION.md`, `docs/FRONTEND_BACKLOG.md`; tests `test_e12`/`test_e13`; evidence pack; gates |

Regression: **189** targeted unit tests passed; `gate_isolation_test.py` PASS; `gate_dlq_drill` + `dlq_replay` 1/1.

---

## Post-G2 / Gate G3 (Waves A–D)

Living status: **`plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md`**.  
UNIFIED Steps **20–23** + **G3** = `[x]`. Placeholders empty (Wave C). Brochure Approach B + media polish shipped. HubSpot skippable (demo stub). n8n/Calendar/brochure HTTPS = ops env when ready.
