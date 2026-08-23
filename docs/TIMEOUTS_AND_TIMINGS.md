# Timeouts & Timings Reference

Canonical map of every meaningful timeout, interval, TTL, backoff, and delay in this repo.  
Use this when debugging latency, interim WhatsApp messages, scheduler behavior, or changing budgets.

**Line numbers are approximate** (shift after edits). Prefer searching for the **symbol / constant name**.

**Last audited:** 2026-07-27 (P3.6 / P3.6b WA race + critical-path trim).

---

## How to change values

| Prefer | Where |
|--------|--------|
| Env-tunable (no code deploy if already wired) | `config.py` `Settings` + `.env` / `.env.example` |
| Code constant | Search symbol below; update constant + this doc + any tests asserting the value |
| Scheduler cadence | `main.py` lifespan `scheduler.add_job(...)` |

**Invariant (WhatsApp):**  
`WHATSAPP_WEBHOOK_TIMEOUT` < Twilio HTTP limit (~15s).  
`LLM_TIMEOUT_SECONDS` **may exceed** the race window (P3.6 await-inflight — Gemini is not cancelled when interim fires).  
Do **not** retry pure `TimeoutError` on the main LLM call.

---

## 1. Env / Settings (`config.py`)

| Name | Default | Unit | Purpose | Defined | Consumed |
|------|---------|------|---------|---------|----------|
| `WHATSAPP_WEBHOOK_TIMEOUT` | `13.0` | s | Race window for WA TwiML reply vs interim | `config.py` ~84 | `main.py` ~1091–1093 |
| `LLM_TIMEOUT_SECONDS` | `22.0` | s | Hard cap per Gemini `send_message` (may exceed race) | `config.py` ~88 | `agent.py` LLM loop |
| `CLIENT_SUPPORT_NUMBER` | `+91 9876543210` | str | Fatal fallback / escalate display number | `config.py` | `agent.py`, `main.py` |
| `RAG_TIMEOUT_SECONDS` | `2.0` | s | FAISS/RAG retrieve budget | `config.py` ~91 | `agent.py` ~1089–1091 |
| `GRAPH_CONTEXT_TIMEOUT_SECONDS` | `0.5` | s | Neo4j context soft-timeout on WA path | `config.py` ~92 | `whatsapp_agent.py` ~241–245 |
| `FOLLOW_UP_DELAY_MINUTES` | `30` | min | Prod Day-0 follow-up delay (also documented in comments) | `config.py` ~41 | follow-up arm / helpers |
| `FOLLOW_UP_TEST_MODE` | `false` | bool | Compress follow-up gaps + inactivity | `config.py` ~44 | `follow_up.py`, `agent.py`, v3 scheduler |
| `FOLLOW_UP_MAX_COUNT` | `2` | count | Max follow-up sends policy | `config.py` ~42 | follow-up engine |
| `TEST_MODE` | `false` | bool | Twilio sig bypass; **awaits** deferred post-turn tasks | `config.py` ~46 | many modules |

Also documented in `.env.example` (~66–73).

---

## 2. WhatsApp critical path (hot path)

Budget stack under one user message (typical order):

```text
Graph soft ≤ 0.5s  +  RAG ≤ 2s  +  Gemini ≤ 22s  +  tool routing
        race decision at WHATSAPP_WEBHOOK_TIMEOUT (13s)
        < Twilio ~15s HTTP for first TwiML
        (Gemini may finish after interim via EE push)
```

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| **Webhook race** | **13s** (env) | `asyncio.wait({task}, timeout=…)`. Fast → TwiML reply. Slow → interim + await same task (no cancel). | `main.py` ~1091–1123 |
| **Session turn lock TTL** | **45s** | Redis lock held for full turn (`_session_turn_locked`) | `main.py` ~640 |
| **Session turn lock wait** | **30s** | `blocking_timeout` acquiring lock | `main.py` ~640 |
| **Legacy background lock TTL** | **45s** | `background_process_and_push` | `main.py` ~723 |
| **Legacy background lock wait** | **10s** | Skip if another worker holds lock | `main.py` ~723 |
| **Interim dedup TTL** | **120s** | Redis `interim_sent:{MessageSid}` — one “Just checking…” per SID | `main.py` ~1133 |
| **LLM send** | **22s** (env) | `asyncio.wait_for(chat.send_message, …)`; may exceed race | `agent.py` LLM loop |
| **LLM retries** | **3** attempts for transient errors only | **No retry** on `TimeoutError` / `CancelledError` | `agent.py` LLM loop |
| **Name extract** | **2.0s** | Parallel Gemini call; skipped if `lead.name` set / TEST_MODE / short greets | `agent.py` ~1141–1155 |
| **RAG retrieve** | **2.0s** (env) | `to_thread(retrieve)` | `agent.py` ~1089–1091 |
| **Graph context soft** | **0.5s** (env) | `to_thread(_graph_extra_context)` | `whatsapp_agent.py` ~239–245 |
| **History window** | last **6 turns** (12 msgs) | Gemini chat history trim | `agent.py` ~968 |
| **Confidence gate** | **&lt; 75** | `requires_manual_review` | `agent.py` ~1282 |
| **Duplicate user msg (P3.3)** | **5 min** | Skip re-insert on legacy background re-run | `agent.py` ~225–233 |
| **Day-0 arm delay** | **30 min** prod / **1 min** test | New follow-up state | `agent.py` ~212–215 |
| **Post-turn side effects** | async (prod) | Score / negotiation L2 / graph / memory — fire-and-forget unless `TEST_MODE` | `whatsapp_agent.py` ~258–340 |
| **Bus turn events** | async (prod) | `_emit_turn_events_deferred` after reply | `main.py` ~822–940 |

### External constraint (not in code)

| Timing | Value | Notes |
|--------|-------|--------|
| Twilio webhook HTTP | ~**15s** | Must return TwiML before Twilio retries. Keep race &lt; 15s. |

---

## 3. SMS path

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| SMS session lock TTL | **20s** | `session_lock:{scoped_session_id}` | `main.py` ~1205 |
| SMS lock wait | **30s** | `blocking_timeout` | `main.py` ~1205 |

SMS does **not** use the WA race/interim pattern; it awaits `process_unified_lead` under the lock.

---

## 4. Redis debounces & TTLs

| Key pattern | TTL | Purpose | Location |
|-------------|-----|---------|----------|
| `interim_sent:{MessageSid}` | **120s** | One interim WA message per Twilio SID | `main.py` ~1133 |
| `negotiation_emitted:{client_id}:{lead_id}` | **300s** (5 min) | Negotiation event spam gate | `app/events/negotiation.py` ~30, ~48 |
| `lead_hot_emitted:{client_id}:{lead_id}:{trigger}` | **1800s** (30 min) | `lead.hot` / alias dual-publish debounce | `app/events/lead_hot.py` ~23, ~56 |
| Sales AI debounce lock | **600s** (10 min) | Per-lead sales agent debounce | `app/agents/sales_agent.py` ~197, ~291 |

---

## 5. APScheduler jobs (`main.py` lifespan)

| Job id | Cadence | Description | Location |
|--------|---------|-------------|----------|
| `follow_up_checker` | every **1 min** | `dispatch_followups` | `main.py` ~365 |
| `escalation_checker` | every **1 min** | Hot-lead ack escalation | `main.py` ~368 |
| `crm_resync` | every **5 min** | Debounced CRM field re-push | `main.py` ~369 |
| `expire_approvals` | every **15 min** | Stale HITL; arg **24h** max age | `main.py` ~380 |
| `nightly_backup` | cron **02:00** | Postgres backup | `main.py` ~366 |
| `nightly_cleanup` | cron **03:00** | Retention cleanup | `main.py` ~367 |
| `competitor_monitor` | cron **01:00** | Keyword market alerts | `main.py` ~372 |
| `weekly_marketing_report` | cron **Mon 08:00** | Marketing report event | `main.py` ~376 |

### Nightly cleanup retention

| Timing | Value | Location |
|--------|-------|----------|
| Soft data cutoff | **90 days** | `main.py` ~226 (`daily_cleanup_job`) |

---

## 6. Follow-ups & inactivity

| Timing | Prod | Test (`FOLLOW_UP_TEST_MODE`) | Location |
|--------|------|------------------------------|----------|
| Day-0 delay | **30 min** | **1 min** | `agent.py` ~212; `config` comments |
| Stage gaps (typical) | Day1/3/7 → **24h / 48h / 96h**-class gaps | compressed to minutes | `follow_up.py` / ML payload |
| Quiet hours | shift to **08:00 IST** if target in **22:00–08:00 IST** | same | `follow_up.py` ~322–333 |
| Inactivity threshold | **7 days** no reply | **60 s** | `follow_up.py` ~430–444; `followup_scheduler.py` ~115–124 |
| Send failure backoff | exp **15 → 30 → 60 → 120 → cap 240 min**; stop after **5** | **1 min** each | `follow_up.py` `compute_send_failure_backoff` ~336–359 |
| Twilio/send Tenacity | **5** attempts, exp wait min **2s** max **30s** | same | `follow_up.py` ~580 |

---

## 7. Escalation & notifications

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| First escalate deadline | **+10 min** from notify | `NotificationLog.escalate_at` | `notification_service.py` ~162, ~344 |
| 10m → next check | **+20 min** (30m total wall) | After 10m manager alert | `main.py` ~280 |
| 30m critical | when `escalate_at` hit in `escalated_10m` | Director (fallback manager) | `main.py` ~282–307 |
| Failed delivery alert age | **≥5 min** after `sent_at` | One-shot critical alert | `main.py` ~312 |
| Notify sleep (legacy) | **1s** | Small pause in notification path | `notification_service.py` ~244 |

---

## 8. CRM sync

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| HubSpot HTTP | **10.0s** | per request | `crm_sync.py` ~135, ~147 |
| Tenacity | **5** attempts, wait exp min **2s** max **30s** | permanent fail → DLQ | `crm_sync.py` ~109–110 |
| Poll sleep | **0.5s** | between create-status polls | `crm_sync.py` ~177 |
| Resync job | every **5 min** | scheduler | `main.py` ~369 |

---

## 9. Automation Engine / Execution Engine

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| AE max attempts | **3** | `_MAX_ATTEMPTS` | `app/automation_engine/engine.py` ~29, ~136 |
| AE retry backoff | `0.5 * 2**(attempt-1)` s | 0.5s, 1s, … | `engine.py` ~139–144 |
| n8n HTTP | **15.0s** | `httpx.AsyncClient` | `app/automation_engine/n8n_client.py` ~55 |
| Outbound sync bridge | **45s** | thread pool `result(timeout=45)` | `app/execution_engine/outbound.py` ~93 |
| Calendar default slot | **+1 day**, duration **1h** | stub/real schedule helpers | `calendar_executor.py` ~50, ~73 |
| HITL expire job arg | **24 hours** | `expire_stale_approvals(..., 24)` | `main.py` ~380 |

---

## 10. Event bus / SSE

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| Handler task drain on stop | **2.0s** | `wait_for` per task | `event_bus_client.py` ~117 |
| Pending XREAD reclaim | block **10ms**, count **10**, outer wait **2s** | startup reclaim | `event_bus_client.py` ~208–212 |
| Live XREAD | block **250ms**, count **10** | main consumer loop | `event_bus_client.py` ~221 |
| Consume retry max | **10** consecutive | Bus gives up after N sustained failures | `event_bus_client.py` `_MAX_CONSUME_RETRIES` (P3.8) |
| Reconnect backoff | **1s → 2s → 4s → … → cap 16s** | Exponential between retries; resets on success | `event_bus_client.py` `_RECONNECT_BASE_DELAY`, `_RECONNECT_MAX_DELAY` (P3.8) |
| SSE heartbeat | **15s** | `: ping` | `app/api/events.py` `HEARTBEAT_SEC` ~39, ~127 |
| SSE queue max | **1000** | drop on full | `events.py` `SSE_QUEUE_MAX` ~40 |

---

## 11. Database / infra

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| Pool size | **20** | SQLAlchemy | `database.py` ~16 |
| Max overflow | **40** | | `database.py` ~17 |
| Pool timeout | **30s** | wait for connection | `database.py` ~18 |
| Pool recycle | **1800s** (30 min) | drop stale conns | `database.py` ~19 |
| RAG index ready wait | **5.0s** | first retrieve may block | `rag.py` ~76–78 |
| Embedding LRU | **128** entries | `@lru_cache(maxsize=128)` | `rag.py` ~27 |
| JWT access token | **7 days** | `60 * 24 * 7` minutes | `auth.py` `ACCESS_TOKEN_EXPIRE_MINUTES` ~22; used `main.py` ~574 |

---

## 12. Customer success / prediction

| Timing | Value | Description | Location |
|--------|-------|-------------|----------|
| At-risk inactivity | **7 days** | cold/inactive open leads | `prediction_service.py` ~98–113; `customer_success_agent.py` ~100 |

---

## 13. Dev / test tooling only

| Timing | Value | Location |
|--------|-------|----------|
| Stress chat HTTP | **45s** | `task3_runner.py` `CHAT_TIMEOUT` ~49 |
| Stress typing delay | **4.0s** | `MSG_DELAY` ~47 |
| Isolation gate HTTP | **90s** | `gate_isolation_test.py` ~31 |
| Env probe Redis connect | **3s** | `tests/test_e0_env.py` |
| Prometheus p95 alert | **&gt; 3.0s** over 2m | `prometheus_alerts.yml` |

---

## 14. Tuning cheatsheet

### “Just checking that for you…” fires too often
1. Check logs: `TIMEOUT | … action=await_inflight_push` and `llm_main_call` latency.  
2. Raise `WHATSAPP_WEBHOOK_TIMEOUT` carefully (stay **&lt; 15**).  
3. Raise `LLM_TIMEOUT_SECONDS` if Gemini often needs 12–20s (default 22s; inflight can finish after interim).  
4. Confirm graph/RAG soft budgets not stuck (Neo4j down should soft-timeout, not hang).  
5. Remember: slow path **awaits same Gemini call** (P3.6) — interim is UX only, not a second bill. TimeoutError is not retried.

### Follow-ups too fast/slow
- Prod: `FOLLOW_UP_TEST_MODE=false`, `FOLLOW_UP_DELAY_MINUTES=30`.  
- Local QA: `FOLLOW_UP_TEST_MODE=true` (1-minute gaps + 60s inactivity).

### Negotiation / hot-lead spam
- Negotiation debounce: `NEGOTIATION_DEBOUNCE_TTL` in `app/events/negotiation.py`.  
- Hot lead debounce: `DEBOUNCE_TTL_SEC` in `app/events/lead_hot.py`.

### CRM flaky
- HTTP 10s + Tenacity 5× (2s–30s) in `crm_sync.py`; resync every 5 min.

---

## 15. Related docs

| Doc | What it covers |
|-----|----------------|
| `AGENTS.md` → Webhook Flow & Timeouts | Agent-oriented WA path summary |
| `plans/phase3/BUG_FIXES_CHANGELOG.md` → P3.6 / P3.6b | Race + critical-path change history |
| `docs/BACKEND_RELIABILITY_CHECKLIST.md` | Ops reliability including WA race |
| `.env.example` | Env knobs for WA/LLM/RAG/graph |

When you change a timing, update **this file**, **`.env.example`** (if env-backed), and any **tests** that assert the constant (e.g. `tests/test_p3_concurrency.py`, `tests/test_e19_negotiation_ui.py`).
