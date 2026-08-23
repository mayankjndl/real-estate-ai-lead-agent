# IREIOS 3.0 — Implementation Plan

Migration and build plan for expanding the current monolith into the Phase 3.0 architecture.

| This doc owns | Does not own |
|---|---|
| Phases, file tree, migration mapping, tests, risks, decommission | System diagrams / event catalog → `IREIOS_3.0_Architecture_Diagrams.md` |
| | Agent intent trees / workflow Mermaid → `IREIOS_3.0_AI_Automation_Workflows.md` |
| | Atomic tasks → `IREIOS_3.0_STEP_BY_STEP_EXPANSION.md` |
| | Serial program order → `UNIFIED_EXECUTION_ORDER.md` |

**Status:** Doc-synced (architecture decisions frozen)  
**Codebase baseline:** FastAPI monolith — `agent.py`, `main.py`, `follow_up.py`, `crm_sync.py`, `app/intelligence/*`, Next.js command-center (mostly mocks)

**Frozen decisions:**

1. CEO Orchestrator is real (registry, route, queue, health).  
2. Automation Engine and Execution Engine are separate.  
3. LangGraph + n8n are real dependencies.  
4. HITL (Path C) is early core, not deferred.  
5. Neo4j + Graph APIs live in this repo (backend).  
6. Frontend: wire existing mocks to real APIs/SSE (Mayank UI; backend owns contracts).  
7. Full agent logic for planned agents only; remaining “15” are CEO placeholders.  
8. Brochure/floor plan folded into WhatsApp agent phase (supersedes standalone FAQ doc patterns that used a stub HTTP bus).  
9. **Event Bus = Redis Streams from Day 1** — no in-process `asyncio.Queue` as the production bus (vetoed: crash data-loss + n8n needs an external broker).  
10. **API envelopes + SSE streams ship early** (Phase 1b, right after bus) with stub/dummy payloads allowed so FE can unmock immediately; Phase 9 is FE cutover to live producers, not first endpoint creation.

**Runtime rule:** `Event → CEO → Agent/Workflow → Automation Engine → Execution Engine → Event`

**Event catalog:** single source of truth in Architecture Diagrams §4. Must implement at least PDF business events: `lead.created`, `lead.assigned`, `whatsapp.sent`, `call.made`, `site_visit.scheduled`, `booking.confirmed`, `payment.received`, plus runtime events listed there.

---

## 1. Current state → target

| Today | Target |
|---|---|
| `process_chat()` does session, LLM, RAG, tools, scoring, matching | WhatsApp Agent + async scoring handler |
| Direct Twilio / HubSpot calls | Execution Engine executors |
| No bus | Event Bus (**Redis Streams**) + CEO routing |
| No HITL workflow engine | Automation Engine + LangGraph/n8n + approval queue |
| No Neo4j | Knowledge Graph module + async writers |
| FE MockSSE / mock chat | Real SSE + REST from backend |
| Monolith files at repo root | `app/orchestrator`, `agents`, `automation_engine`, `execution_engine`, `workflows`, `knowledge_graph`, `memory` |

Dual-path rule: **do not decommission** `agent.py` / `crm_sync.py` / `follow_up.py` until the new path is tested green for that slice.

---

## 2. Target file structure

```text
app/
├── clients/
│   ├── event_bus_client.py      # Redis Streams pub/sub (Day 1)
│   └── graph_client.py          # agent-facing KG access
├── orchestrator/
│   ├── ceo_orchestrator.py      # registry, route, queue, health
│   └── agent_registry.py
├── agents/
│   ├── base_agent.py            # fetch → analyze → decide
│   ├── whatsapp_agent.py
│   ├── sales_agent.py
│   ├── marketing_agent.py
│   ├── customer_success_agent.py
│   ├── lead_scoring_handler.py
│   └── placeholders.py          # remaining Layer-2 stubs
├── automation_engine/
│   ├── engine.py                # validate, template select, dispatch to EE
│   ├── hitl.py                  # approval queue, pause/resume
│   ├── langgraph_runner.py
│   ├── n8n_client.py
│   └── templates/               # linear + named workflows
├── execution_engine/
│   ├── base_executor.py
│   ├── execution_engine.py      # action_type → executor
│   ├── whatsapp_executor.py
│   ├── crm_executor.py
│   ├── calendar_executor.py
│   └── notification_executor.py
├── workflows/
│   ├── crm_automation.py
│   ├── followup_scheduler.py
│   └── competitor_monitor.py
├── knowledge_graph/
│   ├── schema/                  # versioned Cypher / migrations
│   ├── neo4j_client.py
│   ├── graph_api.py             # FastAPI router or mountable routes
│   └── event_writers.py         # bus → Neo4j async
├── memory/
│   ├── memory_store.py          # conversation / long-term / decision / action
│   └── retrieval.py
├── intelligence/                # EXISTING — keep; expose via prediction APIs
└── ...

# Root (evolve, don’t dump everything new here)
main.py                 # gateway, lifespan, mount routers, SSE
agent.py                # DECOMMISSION after Phase 5 validated
crm_sync.py             # DECOMMISSION after Phase 3 validated
follow_up.py            # DECOMMISSION after Phase 4 validated
models.py / database.py # extend for HITL, memory, graph metadata as needed
frontend/               # Mayank: wire mocks (Phase 9)
```

---

## 3. Phases overview

| Phase | Goal | Exit criteria |
|---|---|---|
| **0** | Docs frozen | Three docs + event catalog agreed |
| **1** | **Redis Streams** Event Bus + CEO + BaseAgent + EE skeleton + DLQ hook | Publish survives process restart; CEO handler runs; EE/DLQ unit tests |
| **1b** | **API envelopes + SSE early** (stub producers OK) | Authenticated SSE + timeline/KPI envelope routes live; FE can drop mocks |
| **2** | Automation Engine + HITL + LangGraph/n8n hooks | Approval pause/resume test; retry policy test |
| **3** | WhatsApp + CRM executors | TEST_MODE send; HubSpot retry preserved |
| **4** | Follow-up via AE→EE | State machine parity with old `follow_up.py` |
| **5** | WhatsApp Agent + brochure/floorplan + scoring handler | Chat parity; media tools; old path still available until cutover |
| **6** | CRM automation + Sales AI | Tags/assign/NBA/objections/hot path |
| **7** | Neo4j + Graph APIs + Memory APIs + event writers | Schema versioned; lead context query; async write on `lead.qualified` |
| **8** | Prediction APIs + Marketing + CS + Competitor | REST prediction surface; cron intel alert |
| **9** | FE cutover: mocks → **live** SSE/APIs | Dashboard/timeline/KG/twin/copilot/chat use real producers (not first endpoint creation) |
| **10** | Placeholders registered; decommission monolith; evidence pack | Gates green; dual-path removed |

Milestone mapping (assignment targets; adjust if schedule already slipped):

| Date | Aim |
|---|---|
| Architecture freeze | Phase 0 |
| Core backend + WhatsApp functional | Phases 1–5 |
| KG + forecasts + marketing + dashboard | Phases 6–9 |
| MVP close | Phase 10 |

---

## 4. Phase details

### Phase 0 — Doc freeze

- Architecture Diagrams, Workflows, this plan aligned.  
- Event catalog locked (see Architecture Diagrams §4).  
- No product code required beyond optional checklist file.

### Phase 1 — Infrastructure: Redis Streams bus, CEO, BaseAgent, EE skeleton

**Create:**

- `app/clients/event_bus_client.py` — **Redis Streams** (not asyncio.Queue):  
  - `publish` → `XADD` with full event envelope  
  - consumer group(s) for CEO/in-app handlers (`XREADGROUP` / ack)  
  - `start`/`stop` consumer loops in lifespan  
  - stream key(s) documented (e.g. `ireios:events` or per-type streams — pick one scheme and stick to it)  
  - env: existing Redis URL; optional `EVENT_STREAM_KEY`, `EVENT_CONSUMER_GROUP`  
- `app/orchestrator/agent_registry.py` — register agent id, subscriptions, active|placeholder, health.  
- `app/orchestrator/ceo_orchestrator.py` — on event: lookup subscribers → run handlers; health probes.  
- `app/agents/base_agent.py` — lifecycle → submit to Automation Engine (Phase 1 stub forwards to EE).  
- `app/execution_engine/base_executor.py`, `execution_engine.py` — register + `dispatch`; on error write `DLQEvent`.  
- Lifespan: bus consumers + CEO bootstrap.  
- **n8n:** document how external automation reads the same stream(s) or a documented bridge (no pure in-memory bus).

**Interfaces (minimal):**

```python
# Event publish (Redis Streams)
await EventBusClient.publish(event_type, tenant_id, entity_id, payload, source=...)

# CEO
CEOOrchestrator.register(agent_id, handler, subscriptions: list[str], status="active"|"placeholder")
await CEOOrchestrator.handle_event(event)

# Agent lifecycle
class BaseAgent(ABC):
    async def process_event(self, event: dict): ...
    async def fetch_context(self, event) -> dict: ...
    async def analyze(self, event, context) -> dict: ...
    async def decide(self, event, analysis, context) -> dict | None:  # action_request

# EE
await ExecutionEngine.dispatch(action_request) -> dict  # status success|error
```

**Tests:** handler receives published event after restart (durable); EE missing executor → error; DLQ row on forced failure. Redis required for bus tests (docker-compose redis).

### Phase 1b — Early API envelopes + SSE (FE unblock)

**Goal:** Mayank can hot-swap frontend mocks **immediately** after Phase 1. Endpoints use Architecture §4 envelope shapes even if producers are stubs.

**Create / mount in `main.py`:**

- `GET /api/v1/events/stream` — tenant-auth SSE; bridge from Redis Streams (or fan-out queue fed by bus consumer) to connected clients.  
- `GET /api/v1/leads/{id}/timeline` (or equivalent) — list-shaped events for copilot; may return stub rows with `source: "stub"`.  
- Optional thin KPI/pulse JSON if dashboard needs REST in addition to SSE.  
- Stub publisher (cron or admin endpoint) that `XADD`s sample `lead.created` / `whatsapp.sent` / pulse events for FE demos.

**Rules:**

- Stable field names from day one; do not rename later without versioning.  
- Stub payloads clearly marked; swap to real producers in Phases 3–8 without changing FE contract.  
- Auth + tenant isolation required (same as production).

**Exit:** `curl -N` SSE receives a published test event; FE can point `NEXT_PUBLIC_USE_MOCKS=false` at these routes.

### Phase 2 — Automation Engine + HITL + LangGraph/n8n

**Create:**

- `app/automation_engine/engine.py` — validate action_request; select template type; call EE; apply retry/fallback policy.  
- `app/automation_engine/hitl.py` — store pending approvals; `approval.requested` / `approval.resolved`; resume/reject.  
- `app/automation_engine/langgraph_runner.py` — stateful graphs for multi-step + pause.  
- `app/automation_engine/n8n_client.py` — trigger/wait n8n workflows for integrations.  
- `models` (or tables): `approval_requests` (tenant, entity, action snapshot, status, manager).  
- API: approve/reject endpoints (manager auth).  
- Wire `BaseAgent.decide` → `AutomationEngine.submit` (not direct EE).

**Tests:** action with `requires_approval=true` does not call executor until approve; reject writes memory event; retry count respected.

### Phase 3 — Executors (WhatsApp, CRM)

**Create:**

- `whatsapp_executor.py` — from Twilio usage in `agent.py` / `main.py` / follow-up.  
- `crm_executor.py` — migrate `_push_to_hubspot` + tenacity from `crm_sync.py` as-is.  
- Register: `send_whatsapp`, `update_crm`.  
- Map success → `whatsapp.sent`, `lead.crm_synced`.

**Tests:** `TEST_MODE` success; CRM 429 retries; failure → DLQ.

### Phase 4 — Follow-up scheduler

**Create:** `app/workflows/followup_scheduler.py`

- Port state machine + payload builder + quiet hours from `follow_up.py`.  
- Replace direct Twilio with AE→EE `send_whatsapp`.  
- Emit `followup.sent`.  
- Subscribe/create state on `lead.created` / activity as designed.  
- Keep APScheduler job in `main.py` lifespan pointing at new entrypoint.  
- Run old and new in shadow mode until parity, then cut over.

**Tests:** stage transitions; quiet hours; no direct Twilio import in workflow module.

### Phase 5 — WhatsApp Agent + documents + scoring

**Create:** `whatsapp_agent.py`, `lead_scoring_handler.py`

**Migrate from `agent.py` (by concern):**

| Concern | Destination |
|---|---|
| Session/lead/FollowUpState | `fetch_context` |
| Opt-out, guardrail, handoff, instant reply, property intent | `analyze` helpers |
| History + lead summary + RAG | `analyze` |
| Gemini + retries + tools | `analyze` / `_llm_chat` |
| `extract_lead_info` | tool path |
| **Brochure / floor plan** | tools `share_brochure`, `share_floor_plan` + system_prompt rules (from FAQ doc) → media via EE |
| Message persist | analyze/decide |
| ML score + agent match | **LeadScoringHandler** on `whatsapp.response.generated` |
| Re-arm Day 0 | event → follow-up workflow |

**Gateway:** `main.py` WhatsApp webhook publishes `whatsapp.received`; preserve **15s TwiML** pattern (sync wait or background push). CEO routes to WhatsApp Agent. Chat endpoint same pattern with `chat.received`.

**Cutover:** feature flag or traffic split; keep `agent.process_chat` until gates pass.

**Tests:** task3 suite; brochure/floorplan tool paths; guardrail; handoff; scoring async (response not blocked).

### Phase 6 — CRM automation + Sales AI

- `workflows/crm_automation.py` — tags, `match_best_agent`, tasks, `update_crm` / assign → `lead.assigned`.  
- `agents/sales_agent.py` — objections, priority, NBA; HITL for commercial risk.  
- Subscribe via CEO to `lead.qualified`, `lead.scored`, etc.

**Tests:** hot lead assign; objection → task; approval-gated action.

### Phase 7 — Neo4j Knowledge Graph + Memory

**Create:** `app/knowledge_graph/*`, `app/memory/*`

- Versioned schema for PDF entities (Leads, Projects, Towers, Units, Customers, Payments, Salespersons, Inventory, Site Visits, Documents, Calls, WhatsApp Conversations, Emails).  
- `neo4j_client`, Graph REST routes (upsert, query lead context, project inventory).  
- `event_writers` subscribed to bus (`lead.created`, `lead.qualified`, `lead.assigned`, visits, payments, …) — **async only**.  
- Memory store: conversation window bridge, long-term, decision, action; retrieval API for agents.  
- `GraphClient` used in WhatsApp/Sales `fetch_context`.

**Infra:** Neo4j via docker-compose or configured URI; document env vars.

**Tests:** schema migrate; upsert lead; query relationships; event writer does not block publisher.

### Phase 8 — Prediction APIs + remaining agents/workflows

- REST under gateway: lead score, booking prediction, revenue forecast, cancellation risk, cashflow, inventory forecast — wrap/extend `app/intelligence` (stub honest 501/heuristic where model missing; no fake accuracy claims).  
- `marketing_agent.py`, `customer_success_agent.py`, `competitor_monitor.py`.  
- Cron: competitor + midnight rollups.  
- CS on `payment.*` / `booking.confirmed`.

**Tests:** each prediction route authenticated + tenant-scoped; competitor publishes `market.alert.generated`.

### Phase 9 — Frontend cutover (Mayank UI)

**Backend already delivered in Phase 1b** (SSE + envelopes). Phase 9 is **not** first creation of those routes.

Backend polish for cutover:

- Graph query APIs stable (Phase 7).  
- Chat/orchestrator API for executive AI chat (if not earlier).  
- Prediction + analytics REST (Phase 8).  
- Replace stub producers with live bus events for dashboard/timeline.

Frontend (Mayank): replace `MockSSEService`, `simulateSSEStream`, mock graph/forecast with real clients. Pages: dashboard-mvp, digital-twin, knowledge-graph, ai-chat, sales-copilot, command-center.

**Exit:** demo path without mock services for MVP surfaces.

### Phase 10 — Placeholders, decommission, evidence

- `placeholders.py` + CEO registry entries for non-MVP agents.  
- Remove dual-path; delete or archive dead imports of old modules.  
- Package: API docs, graph schema export, test logs, integration notes, deployment report checklist (assignment deliverables).

---

## 5. Migration mapping (existing → new)

| Existing | New home | Phase |
|---|---|---|
| Twilio send (scattered) | `WhatsAppExecutor` | 3 |
| `crm_sync.py` | `CRMExecutor` | 3 |
| `follow_up.py` | `FollowUpSchedulerWorkflow` | 4 |
| `agent.py` chat core | `WhatsAppAgent` | 5 |
| `agent.py` scoring/match | `LeadScoringHandler` | 5 |
| FAQ/brochure/floorplan guide | tools + prompt + EE media | 5 |
| `agent_matcher` / scoring intelligence | CRM workflow + scoring handler (call existing modules) | 5–6 |
| `notification_service` | `NotificationExecutor` + Sales/hot path | 3/6 |
| `main.py` webhooks | publish events + TwiML timeout | 5 |
| `main.py` scheduler | call new workflows | 4/8 |
| `EventLog` / tracking | Memory action + bus (keep EventLog as needed) | 1–7 |
| `DLQEvent` / `dlq_replay.py` | EE/AE failure path (keep replay) | 1–2 |
| FE mocks | SSE/API stubs (1b) then live producers (9) | 1b / 9 |

---

## 6. main.py integration points

| Area | Change |
|---|---|
| Lifespan | `EventBusClient.start()`, CEO register agents, scheduler jobs, shutdown order |
| `/api/v1/whatsapp` | Validate → dedupe → `publish(whatsapp.received)` → CEO/agent with 15s timeout / background push |
| `/api/v1/chat` | `chat.received` same agent path |
| Approvals | `POST` approve/reject → HITL resume |
| Graph | Mount `knowledge_graph` routes |
| Memory / predictions | Mount routers |
| SSE | `/api/v1/events/stream` tenant-scoped — **Phase 1b** (stubs OK) |
| Health | Include bus, Neo4j, CEO agent health |

---

## 7. Testing strategy

| Gate | Command / method | When |
|---|---|---|
| Unit bus/CEO/EE/AE | pytest + Redis Streams publish/consume | 1–2 |
| Bus durability | publish → restart consumer → message still deliverable / acked correctly | 1 |
| SSE + envelope stubs | curl stream + auth tenant | 1b |
| Executor TEST_MODE | unit | 3 |
| Follow-up transitions | integration | 4 |
| Conversation suite | `python task3_runner.py` | 5+ |
| Tenant isolation | `python gate_isolation_test.py` | every phase touching data |
| DLQ | `python gate_dlq_drill.py` + `dlq_replay.py` | 2–3+ |
| Graph | schema + query integration | 7 |
| FE cutover | mocks off; live producers | 9 |

**Rule:** Until a slice cutover, existing tests must pass on the **old** path. New path gets additive tests first.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| WhatsApp extraction regresses LLM quality | Dual-path + task3 before cutover |
| Redis/Streams outage blocks bus | Health check; fail publish loud; DLQ for downstream; document Redis HA |
| HITL deadlocks workflows | Timeouts + expire pending approvals + Memory log |
| Neo4j latency on chat | Async writers only; agents read with timeouts/fallback to Postgres |
| n8n/LangGraph ops complexity | LangGraph in-app; n8n reads Redis Streams / webhook bridge |
| Circular agent↔EE waits | One-way: agents → AE → EE → events only |
| FE blocked on backend | **Phase 1b** SSE + envelope stubs (PR review requirement) |
| Scope vs 25 Jul | MVP = planned agents + CEO + Streams bus + AE/EE + HITL + WA + KG core + FE wire; placeholders for rest |

---

## 9. Dependencies to add (expected)

| Package / service | Purpose |
|---|---|
| **Redis** (existing) + Streams API | **Event Bus Day 1** |
| `neo4j` (Python driver) | Graph |
| `langgraph` (+ langchain core as required) | Stateful AE |
| n8n (service) | Integration workflows (subscribe via Streams/bridge) |
| Neo4j (Docker/service) | Graph DB |
| Existing: redis, twilio, httpx, tenacity, google genai | redis now also bus backbone |

Pin versions in `requirements.txt` when implementing phases.

---

## 10. Explicit non-goals (for later planning)

- Full production accuracy for every prediction model on day one (honest APIs + progressive models).  
- Deep Negotiation AI (L7) beyond placeholder + hook.  
- Full self-learning (L8) automation — incremental hooks only.  
- Frontend visual redesign.  
- Kafka (not required; **Redis Streams is the Day-1 bus**).  
- In-process `asyncio.Queue` as the production Event Bus (explicitly vetoed).

---

## 11. Next artifact after this plan

`IREIOS_3.0_STEP_BY_STEP_EXPANSION.md` — atomic tasks (one change → test → next).  
`UNIFIED_EXECUTION_ORDER.md` — serial order vs bug-audit plan.

---

## 12. Key decisions (aligned, not contradictory)

1. **CEO is required** — thin policy router first; registry holds placeholders for future agents.  
2. **AE before fat agents** — HITL and retry live in AE so agents stay simple.  
3. **Postgres SoT, Neo4j relationships** — dual store with async projection.  
4. **Follow-ups stay on APScheduler** — time-based by nature; they only change *how* they send (AE→EE).  
5. **Brochure/floorplan in Phase 5** — same Event Bus as everything else; no separate mock HTTP bus.  
6. **Backend owns Neo4j in this repo**; Mayank consumes Graph/SSE APIs only for UI.  
7. **Redis Streams Event Bus from Day 1** — durable, multi-consumer, n8n-friendly.  
8. **SSE/API contracts early (Phase 1b)** — stubs first, live producers later; Phase 9 is FE cutover.
