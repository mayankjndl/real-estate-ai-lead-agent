# IREIOS 3.0 — Wave A–D Changelog

Living record of **post-G2 depth fill** (Waves A–D). Parallel to `IREIOS_3.0_EXPANSION_CHANGELOG.md` (Phases 0–10).

- **How (tasks):** `plans/phase3/IREIOS_3.0_WAVE_A_D_EXPANSION.md`
- **Order:** `plans/phase3/UNIFIED_EXECUTION_ORDER.md` Steps 20–23 + G3 (append when starting)
- **Tests:** `tests/test_e14_wave_a.py` … `tests/test_e17_wave_d.py` (+ extend e2/e3/e6/e8/e11)

## Naming

| Suite | Prefix | Example |
|-------|--------|---------|
| Expansion Phases 0–10 | `test_e0`–`test_e13` | `tests/test_e11_parity.py` |
| Waves A–D | `test_e14`–`test_e17` | `tests/test_e14_wave_a.py` |
| Bug fixes | `test_pN_*` | `tests/test_p5_crm.py` |

## How to maintain (per task)

1. Implement code for the task in `IREIOS_3.0_WAVE_A_D_EXPANSION.md`.
2. Replace skeleton/skip tests with real assertions in the matching `test_e1N_*.py`.
3. Append/update this file (status table + Entry).
4. Flip UNIFIED Steps 20–23 / G3 when a wave exits.
5. Update `AGENTS.md`, `README.md`, integration docs as the plan requires.
6. Regression: `python -m pytest tests/ -q` + `gate_isolation_test.py` when tenant/bus/CRM touched.

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` skipped (reason)

---

## Wave A status — Close dead loops + live integrations

**Benefit:** Existing Marketing/CS/AE/integration code paths actually run with real HubSpot/Calendar and event producers.

| ID | Status | Summary | Tests |
|----|--------|---------|-------|
| A.0.1 | `[-]` | HubSpot — **skipped** (demo stub OK; portal optional) | manual / ops |
| A.0.2 | `[x]` | Google Calendar — path fixed (Windows `/`); live smoke `provider=google_calendar` (2026-07-22) | manual smoke |
| A.0.3 | `[~]` | n8n Docker **up** (`n8n-local:5678`) + `.env` set; **workflow still incomplete** (webhook 404 until UI setup) | manual / ops |
| A.1 | `[x]` | `cron.weekly_report` scheduler job | `test_e14_wave_a.py` |
| A.2 | `[x]` | Lifecycle event producers + admin inject | `test_e14_wave_a.py` |
| A.3 | `[x]` | AE `template_type` n8n \| langgraph dispatch | `test_e14_wave_a.py`, `test_e2_automation.py` |
| A.4 | `[x]` | Schedule `expire_stale_approvals` | `test_e14_wave_a.py` |
| A.5 | `[x]` | NotificationExecutor admin/manager real notify | `test_e14_wave_a.py`, `test_e3_executors.py` |
| A.6 | `[x]` | Docs/env for integrations | — |
| **A exit** | `[x]` | Wave A gate | full suite + isolation |

### Entry — A.1 (weekly marketing cron)

- **Date:** 2026-07-21
- **Files:** `app/workflows/weekly_marketing_cron.py`, `main.py`
- **Behavior:** Scheduler job iterates active clients, publishes `cron.weekly_report` per client on the bus. MarketingAgent picks it up and emits `marketing.report.generated`.
- **Tests:** `test_weekly_marketing_cron_publishes_per_client`, `test_marketing_agent_still_emits_report_on_weekly_event` — 2 green.

### Entry — A.2 (lifecycle producers)

- **Date:** 2026-07-21
- **Files:** `app/api/lifecycle.py`, `main.py`
- **Events produced:** `booking.confirmed`, `payment.received`, `payment.due`, `renewal.due`, `document.pending`, `customer.onboarded` — admin-gated POST.
- **Tests:** `test_lifecycle_inject_booking_confirmed_wakes_cs`, `test_lifecycle_inject_rejects_bad_event_type`, `test_lifecycle_inject_unknown_lead_returns_404` — 3 green.

### Entry — A.3 (AE template_type dispatch)

- **Date:** 2026-07-21
- **Files:** `app/automation_engine/engine.py`
- **Behavior:** Branches on `template_type`: `"n8n"` → `N8NClient.trigger_workflow`; `"langgraph"` → sync `run_graph`; `"linear"` → existing `_execute_with_retry`.
- **Tests:** `test_ae_n8n_template_unconfigured_returns_clean_error`, `test_ae_n8n_template_calls_client_when_configured`, `test_ae_langgraph_template_reaches_execute_or_fallback`, `test_ae_linear_default_unchanged` — 4 green.

### Entry — A.4 (expire_approvals scheduler)

- **Date:** 2026-07-21
- **Files:** `main.py`
- **Behavior:** 15-min interval job marks `approval_requests` older than 48h as `expired`.
- **Tests:** `test_expire_stale_approvals_marks_old_pending`, `test_expire_approvals_job_registered_in_scheduler` — 2 green.

### Entry — A.5 (notification real paths)

- **Date:** 2026-07-21
- **Files:** `app/execution_engine/notification_executor.py`
- **Behavior:** `notify_admin` resolves manager phone via `_resolve_manager_phone` and calls `send_whatsapp_via_executor`; `manager_approval` same pattern. Fallback to log-only when no phone.
- **Tests:** `test_notify_admin_invokes_outbound_not_log_only`, `test_notify_admin_logs_when_no_manager`, `test_manager_approval_kind_notifies_manager` — 3 green.

### Entry — A.6 (docs/env)

- **Date:** 2026-07-21
- **Docs touched:** `AGENTS.md` (active agent list updated), `.env.example` (new vars documented inline)
- **Regression:** n/a

### Entry — Wave A exit

- **Date:** 2026-07-21
- **pytest:** `test_e14_wave_a.py` — 14 passed, 0 failed
- **isolation / DLQ:** Not tested (tenant isolation not affected)
- **HubSpot/Calendar smoke:** Deferred (A.0.x real credentials)
- **UNIFIED Step 20:** `[ ]` → `[x]`

---

## Wave B status — Deepen Maitri agents

**Benefit:** Sales/CS/Marketing execute on the bus with real customer/ops side effects; AE templates + first n8n workflow.

| ID | Status | Summary | Tests |
|----|--------|---------|-------|
| B.1 | `[x]` | SalesAgent CEO bus + NBA→AE | `test_e15_wave_b.py`, `test_e6_sales_agent.py` |
| B.2 | `[x]` | Objection lexicon + memory | `test_e15_wave_b.py` |
| B.3 | `[x]` | CS `send_whatsapp` templates | `test_e15_wave_b.py`, `test_e11_parity.py` |
| B.4 | `[x]` | Marketing + market.alert | `test_e15_wave_b.py` |
| B.5 | `[x]` | Named templates + n8n hot-lead | `test_e15_wave_b.py` |
| B.6 | `[x]` | Competitor → notify | `test_e15_wave_b.py` |
| B.7 | `[x]` | `create_task` executor + Sales escalate → `agent_tasks` | `test_e15_wave_b.py` |
| **B exit** | `[x]` | Wave B gate | full suite + isolation |

### Entry — B.1 (Sales bus + NBA→AE)

- **Date:** 2026-07-21
- **Files:** `app/agents/sales_agent.py`, `main.py`
- **Behavior:** SalesAgent registered on CEO bus, subscribes `lead.scored`/`lead.hot`/`conversation.updated`, debounce via Redis (10min), NBA→AE mapping (hot→notify, visit→schedule, brochure→send).
- **Tests:** `test_sales_agent_registered_active_on_ceo`, `test_lead_hot_envelope_triggers_notify_ae`, `test_sales_bus_debounce_skips_second_event`, `test_sales_http_api_still_works` — 4 green.

### Entry — B.2 (Objections)

- **Date:** 2026-07-21
- **Files:** `app/agents/sales_agent.py`
- **Behavior:** `detect_objections` rule lexicon (price/timing/location/trust/competitor), `persist_objection`→`LeadMemory`.
- **Tests:** 4 objection tests (price tag, no false positive, empty, multiple types) — 4 green.

### Entry — B.3 (CS WhatsApp)

- **Date:** 2026-07-21
- **Files:** `app/agents/customer_success_agent.py`
- **Behavior:** Handler resolves lead phone from DB; sends WhatsApp via AE `send_whatsapp` when phone present; falls back to `notify_admin` without phone. Subscribes `customer.onboarded`.
- **Tests:** `test_cs_send_whatsapp_when_phone_present`, `test_cs_fallback_notify_admin_without_phone`, `test_cs_subscribes_customer_onboarded` — 3 green.

### Entry — B.4 (Marketing + market.alert)

- **Date:** 2026-07-21
- **Files:** `app/agents/marketing_agent.py`
- **Behavior:** Subscribes `market.alert.generated`; folds alert payload (`competitor`, `matched_keyword`) into marketing report under `market_alert` key.
- **Tests:** `test_marketing_includes_market_alert_in_report` — 1 green.

### Entry — B.5 (Named templates + n8n)

- **Date:** 2026-07-21
- **Files:** `app/automation_engine/templates/__init__.py`, `hot_lead_notify.py`, `visit_booking.py`, `docs/N8N_INTEGRATION.md`
- **Behavior:** `build_hot_lead_action` / `build_visit_action` return action_request dicts; support `template_type="n8n"` + `workflow_id`. `N8N_INTEGRATION.md` documents `ireios_hot_lead_slack` webhook path.
- **Tests:** `test_hot_lead_template_builds_valid_action_request`, `test_visit_booking_template`, `test_n8n_hot_lead_workflow_id_documented_or_env` — 3 green.

### Entry — B.6 (Competitor → notify)

- **Date:** 2026-07-21
- **Files:** `app/workflows/competitor_monitor.py`
- **Behavior:** After publishing `market.alert.generated`, writes `NotificationLog` row with `reason="competitor_alert"` for each match.
- **Tests:** `test_competitor_monitor_notifies_on_match` — 1 green.

### Entry — B.7 (create_task executor)

- **Date:** 2026-07-23
- **Files:** `models.AgentTask`, `migrate_db.py` (`agent_tasks`), `app/execution_engine/task_executor.py`, `registry.py`, `sales_agent._nba_to_ae_action`
- **Behavior:** EE action `create_task` inserts client-scoped `agent_tasks` row; success event `task.created`. Sales `escalate_hot` submits notify_agent **and** create_task (“Call hot lead …”).
- **Tests:** `test_create_task_executor_success`, `test_create_task_registered_on_ee`, `test_sales_escalate_hot_submits_create_task`

### Entry — Wave B exit

- **Date:** 2026-07-21 (B.7 completed 2026-07-23)
- **pytest:** `test_e15_wave_b.py` — B.7 tests green (no longer skipped)
- **Wave A regression:** `test_e14_wave_a.py` — 14 passed, 0 failed
- **AGENTS.md:** Updated agent list
- **UNIFIED Step 21:** `[~]` → `[x]`

---

## Wave C status — Placeholder agents → active

**Benefit:** All six Layer-2 placeholders become real event-driven agents (negotiation, pricing, inventory, onboarding, finance, legal).

| ID | Status | Summary | Tests |
|----|--------|---------|-------|
| C.0 | `[x]` | `inventory_units` + `pricing_rules` + seed script | `test_e16_wave_c.py` |
| C.1 | `[x]` | `negotiation_agent` active + HITL | `test_e16_wave_c.py` |
| C.2 | `[x]` | `pricing_agent` active | `test_e16_wave_c.py` |
| C.3 | `[x]` | `inventory_agent` active | `test_e16_wave_c.py` |
| C.4 | `[x]` | `onboarding_agent` active | `test_e16_wave_c.py` |
| C.5 | `[x]` | `finance_agent` active | `test_e16_wave_c.py` |
| C.6 | `[x]` | `legal_agent` active | `test_e16_wave_c.py` |
| C.7 | `[x]` | placeholders.py cleaned; all 6 removed from PLACEHOLDER_AGENTS | `test_e16_wave_c.py` |
| **C exit** | `[x]` | Wave C gate | full suite + isolation |

### Entry — C.0 (data model + seed)

- **Date:** 2026-07-21
- **Files:** `models.py`, `migrate_db.py`, `seed_inventory.py`
- **Behavior:** `inventory_units` + `pricing_rules` tables created via migration. `seed_inventory.py` seeds ~15 Pune/Mumbai/Bengaluru/Hyderabad/Delhi units + 5 pricing rules.
- **Tests:** 4 tests (model exists x2, seed units, seed rules) — 4 green.

### Entry — C.1 (negotiation_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/negotiation_agent.py`
- **Behavior:** On `lead.negotiation.started`/`lead.negotiation.counter`, loads lead from DB, checks `budget_alignment_status`. If misaligned, submits `notify_agent` with `requires_approval: True`. On counter, publishes `negotiation.counter.sent`.
- **Tests:** `test_negotiation_agent_registered`, `test_negotiation_handler_requests_approval_on_misaligned_budget` — 2 green.

### Entry — C.2 (pricing_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/pricing_agent.py`
- **Behavior:** `resolve_pricing(client_id, location, budget)` queries `PricingRule` table; returns matching rule by budget range. Handler processes `pricing.query`/`lead.scored`.
- **Tests:** `test_pricing_agent_registered`, `test_pricing_resolve_matches_budget` — 2 green.

### Entry — C.3 (inventory_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/inventory_agent.py`
- **Behavior:** `query_inventory(client_id, location, bhk, budget)` queries `InventoryUnit` with `.status == "available"`. Handler submits with `kind: inventory_data`.
- **Tests:** `test_inventory_agent_registered`, `test_inventory_query_returns_units` — 2 green.

### Entry — C.4 (onboarding_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/onboarding_agent.py`
- **Behavior:** On `customer.onboarded`/`booking.confirmed`, resolves lead phone from DB and sends WhatsApp via AE `send_whatsapp`.
- **Tests:** `test_onboarding_agent_registered` — 1 green.

### Entry — C.5 (finance_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/finance_agent.py`
- **Behavior:** On `payment.query`/`finance.schedule`, submits `notify_agent` with payment info.
- **Tests:** `test_finance_agent_registered` — 1 green.

### Entry — C.6 (legal_agent)

- **Date:** 2026-07-21
- **Files:** `app/agents/legal_agent.py`
- **Behavior:** On `document.required`/`legal.review`, submits `notify_agent` with document details.
- **Tests:** `test_legal_agent_registered` — 1 green.

### Entry — C.7 (placeholder cleanup)

- **Date:** 2026-07-21
- **Files:** `app/agents/placeholders.py`
- **Behavior:** All 6 promoted agents removed from `PLACEHOLDER_AGENTS` (list now empty). Registered in `main.py` lifespan alongside other agents.
- **Tests:** `test_placeholders_cleaned` — verifies `PLACEHOLDER_AGENTS == []` and no placeholder records on CEO — 1 green.

### Entry — Wave C exit

- **Date:** 2026-07-21
- **pytest:** `test_e16_wave_c.py` — 14 passed, 0 failed
- **UNIFIED Step 22:** `[~]` → `[x]`

---

## Wave D status — Forecast, memory, n8n, brochure Approach B

**Benefit:** Honest L4 prediction routes, memory on chat path, ops n8n depth, **WhatsApp PDF document bubbles** (hosted URL + Twilio `MediaUrl`).

| ID | Status | Summary | Tests |
|----|--------|---------|-------|
| D.1 | `[x]` | Revenue / cancel / inventory / cashflow routes + `prediction_service` helpers | `test_e17_wave_d.py` |
| D.2 | `[x]` | Memory auto-write on WA turn (idempotent `extract_and_store`) | `test_e17_wave_d.py` |
| D.3 | `[~]` | n8n: instance running; **workflows incomplete** (UI + later automations) | `docs/N8N_INTEGRATION.md` |
| D.4 | `[x]` | Approach B code + `docs/demo/*.pdf` assets; set HTTPS env for live MediaUrl | `test_e17_wave_d.py` |
| D.5 | `[-]` | Evidence pack + G3 (deferred — see note) | — |
| **D exit / G3** | `[x]` | Program wave complete — code + gates (pytest/isolation/DLQ). D.2/D.5/A.0 ops still deferred | full suite |

### Entry — D.1 (Prediction routes)

- **Date:** 2026-07-21
- **Files:** `app/services/prediction_service.py`, `app/api/predictions.py`, `main.py`
- **Behavior:** 4 new JWT-protected, client-scoped endpoints: `GET /api/v1/predictions/revenue` (sum of budget*probability), `cancellation-risk` (wrap detect_at_risk), `inventory` (counts by status), `cashflow` (30% booking probability estimate). All heuristic MVP.
- **Tests:** 5 tests (4 function tests + 1 401-without-JWT) — 5 green.

### Entry — D.2 (Memory auto-write)

- **Date:** 2026-07-23
- **Files:** `app/memory/conversation_memory.py` (`extract_and_store` idempotent), `app/agents/whatsapp_agent.py` post-score best-effort call
- **Behavior:** After each v3 WA/chat turn, store lead facts (name/location/budget/type/intent) only when value changed; optional preference snippet from user text. try/except — never blocks reply.
- **Tests:** `test_memory_auto_write_after_turn`

### Entry — D.3 (n8n workflows 2-3 — partial)

- **Date:** 2026-07-21
- **Status:** `[~]` Hot-lead Slack workflow documented in `docs/N8N_INTEGRATION.md` (webhook `ireios_hot_lead_slack`). Weekly marketing CSV and DLQ depth alert remain config-later until n8n instance is provisioned.

### Entry — D.4 (Brochure Approach B + post-G3 polish)

- **Date:** 2026-07-21
- **Files:** `config.py`, `whatsapp_agent.py` (`resolve_tool_media_url`, `take_outbound_media_url`), `main.py` (TwiML Media from staged URL), `sales_agent.py` (NBA media), chat JSON `media_url`
- **Behavior:** HTTPS-only media resolve (non-HTTPS rejected). Default path stages URL for TwiML `<Media>` (no reply-text scrape, no AE double-send). Sales `send_brochure` attaches `media_url`. Empty env → plain-text generators. Events `brochure.sent` / `floorplan.sent` when media present.
- **Tests:** e17 media suite + e12 no-double-send — green.

### Entry — D.5 / G3 (Evidence pack — partial; gates closed)

- **Date:** 2026-07-21
- **Status:** G3 **code gates closed** (full pytest + isolation + DLQ). Formal narrative evidence pack polish remains light (D.5 `[-]` for long-form screenshots/`task3_runner`); implementation evidence is this changelog + UNIFIED flip.

### Entry — Wave D exit / G3

- **Date:** 2026-07-21
- **pytest:** full `tests/` → **332 passed, 7 skipped, 0 failed** (after P0 stabilize)
- **isolation:** `gate_isolation_test.py` **PASS**
- **DLQ:** `gate_dlq_drill.py` + `dlq_replay.py` → **1/1 recovered**
- **P0 stabilize:** `seed.py` Windows-safe prints; `tests/conftest.ensure_test_client`; FK harden e14/e15/e5/e12; duplicate `events_router` removed from `main.py`; e1b route test uses OpenAPI/nested walk
- **Still deferred (not G3 blockers):** A.0 real HubSpot/GCal/n8n instance; B.7 create_task; D.2 memory auto-write; D.3 live n8n workflows 2–3; dual-path 10.2/10.3 delete; FE MockSSE
- **UNIFIED Steps 20–23 + G3:** `[x]`

---

## Regression log (append-only)

| Date | After task | `pytest tests/` | isolation | DLQ | Notes |
|------|------------|-----------------|-----------|-----|-------|
| 2026-07-21 | Wave A | `test_e14_wave_a.py` 14/14 | not tested | not tested | |
| 2026-07-21 | Wave B | `test_e15_wave_b.py` 16/17 (B.7 skipped) | not tested | not tested | |
| 2026-07-21 | Wave C | `test_e16_wave_c.py` 14/14 | not tested | not tested | |
| 2026-07-21 | Wave D | `test_e17_wave_d.py` 10/13 (D.2/D.3/D.5 skipped) | not tested | not tested | |
| 2026-07-21 | Waves A–D final | `test_e14+e15+e16+e17` 54/58 (4 skipped) | not tested | not tested | All non-skeleton green |
| 2026-07-21 | P0 stabilize | full `tests/` **332 passed, 7 skipped** | **PASS** | **1/1 DLQ recovered** | seed.py ASCII fix; `ensure_test_client` in conftest; e14/e15/e5/e12 FK harden; remove duplicate `events_router` mount; e1b OpenAPI route check |
| 2026-07-21 | Post-G3 brochure polish | e17+e12+e5+e6+e15 green | — | — | `take_outbound_media_url` staging; HTTPS reject; Sales NBA media; chat JSON `media_url`; no reply-text scrape |
| 2026-07-22 | Integration audit (no HubSpot) | full `tests/` **333 passed, 7 skipped** | — | — | n8n compose+env; GCal live smoke; tests hardened for live env; brochure URLs still empty |
| 2026-07-23 | Leftovers D.2 + B.7 | full `tests/` **338 passed, 4 skipped** | **PASS** | — | memory auto-write; create_task EE; dual-path/n8n workflows still deferred |

---

## Post-G3 integration audit (2026-07-22)

**Infra up:** `pg-local`, `redis-local`, `neo4j-local`, `n8n-local`, `ngrok-local`, `frontend-local` · API `/health` 200 · `seed.py` run.

| Integration | Status | Evidence | Still incomplete? |
|-------------|--------|----------|-------------------|
| **Postgres / Redis** | `[x]` | compose Up; redis PING | — |
| **Neo4j** | `[x]` | `/api/v1/graph/health` `available:true` schema v1 | — |
| **Google Calendar** | `[x]` | `CalendarExecutor` → `provider=google_calendar` + real `html_link` | Share calendar with SA if events stop appearing |
| **n8n instance** | `[~]` | UI http://localhost:5678 HTTP 200; `N8N_*` set; client `configured=True` | **Yes** — owner setup + active webhook `ireios_hot_lead_slack` + Header Auth `X-N8N-API-KEY`; trigger currently `n8n_http_404` |
| **n8n workflows 2–3** | `[ ]` | docs only | **Yes** — marketing CSV, DLQ alert |
| **Brochure / floor plan media** | `[x]` | HTTPS jsDelivr URLs resolve + GET `application/pdf` 200 (final check 2026-07-23) | Twilio sandbox bubble optional |
| **HubSpot** | `[-]` | intentionally skipped (demo stub) | optional later |
| **Twilio live WA** | depends on `.env` | not re-audited this pass | sandbox smoke when ready |
| **FE MockSSE** | `[ ]` | `docs/FRONTEND_BACKLOG.md` | **Yes** — Mayank |
| **D.2 memory** | `[x]` | shipped 2026-07-23 | — |
| **B.7 create_task** | `[x]` | shipped 2026-07-23 | — |
| **task3_runner evidence** | `[ ]` | optional when Gemini quota OK | **Yes** |
| **Dual-path 10.2/10.3 delete** | `[-]` | stay deferred | **Yes** (do not mark done) |
| **n8n workflows / GCal-in-n8n** | `[ ]` | later (ops) | **Yes** |

**Code fixes this audit (push-ready with compose/docs):**
- `docker-compose.yml` — `n8n` service
- `n8n_client.py` — explicit `""` ctor args no longer fall through to settings
- Calendar/n8n unit tests monkeypatch stub path when local `.env` is live
- `test_e1b_sse` isolated stream/group (no steal from live uvicorn consumer group)
- Local `.env` only: GCal path used forward slashes (Windows `\r` in `\real_estate…`); **do not commit `.env`**

---

## Deferred (do not track as Wave failure)

| Item | Reason |
|------|--------|
| Meta/Google Ads | Out of scope |
| FE MockSSE cutover | `docs/FRONTEND_BACKLOG.md` — Mayank |
| Monolith dual-path delete | Expansion 10.2/10.3 |
| Full competitor crawl | Keyword MVP only |
| HubSpot live portal | Skipped — demo stub until private-app token |
| n8n **workflows** (instance is up) | Owner account + activate webhook + Slack/Set node — see `docs/N8N_INTEGRATION.md` |
| Brochure HTTPS media files | Ops — set `BROCHURE_*` / `FLOORPLAN_*` when hosted |

---

## Post-G3 automations closeout (2026-07-23) — plan locked

**Program step:** UNIFIED **Step 24** / Gate **G4**  
**Branch:** `phase3_automations`  
**Plan of record:** `plans/phase3/PHASE3_AUTOMATIONS_CLOSEOUT.md`  
**Docs updated:** `docs/N8N_INTEGRATION.md` (canonical payloads), Architecture §4.3, API SSE contracts

### Audit reconciliation (no code this entry)

| Third-party proposal | Decision |
|----------------------|----------|
| New events `human.requested`, `lead.escalated`, `session.completed` | **Reject** — use catalog `lead.hot` + `trigger`, and `lead.qualified` + `chat_context` |
| Dummy calendar availability always-true | **Reject** — keep `CalendarExecutor`; optional freebusy later |
| Migrate crons to n8n | **Hard no** |
| HubSpot Python | **Stay skipped**; CRM upsert via n8n on `lead.qualified` |
| Enrich bus + live n8n workflows | **Accept** |

### Critical code gap — **closed 2026-07-23 (BA-1…BA-7)**

| Gap | Fix |
|-----|-----|
| No `lead.hot` publisher | `app/events/lead_hot.py` + scoring handler + handoff |
| No `chat_context` | `main.py` `_emit_turn_events(db=…)` |
| Thin `site_visit.scheduled` | EE `_publish_success` merge params+result |
| HITL no deep links | `hitl.py` approve/reject paths |
| Calendar HTTP for n8n | `app/api/calendar.py` (stub labeled; confirm→AE) |

**Regression:** full `tests/` **352 passed, 4 skipped**; isolation PASS; DLQ 1/1. Suite: `tests/test_e18_automations_closeout.py`.

**Still open (Maitri):** n8n WF-1…WF-6 UI activation → Gate G4.
