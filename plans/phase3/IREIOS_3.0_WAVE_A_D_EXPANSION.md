# IREIOS 3.0 — Wave A–D Expansion Plan (Post-G2 Depth Fill)

**Status:** **Implemented (G3 code gates green 2026-07-21)** · **Target:** 31 July 2026 · **No FE demo polish required**  
**Living log:** `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` (task rows `[x]`/`[-]`). This plan remains the how-to reference; do not treat remaining `[ ]` task bullets below as “not built” without checking the changelog.  
**Owners:** Backend AI / Automation (Maitri + Aritro) · Integrations ops as noted  
**Does not replace:** Phases 0–10 in `IREIOS_3.0_STEP_BY_STEP_EXPANSION.md` (those are `[x]` at G2). This plan is the **next program block** after Gate G2.

| This doc owns | Does not own |
|---|---|
| Wave A–D tasks, file-level steps, integration signup guides, test IDs, per-wave benefits | Architecture topology → `IREIOS_3.0_Architecture_Diagrams.md` |
| | Agent intent diagrams → `IREIOS_3.0_AI_Automation_Workflows.md` |
| | Living implement log → `IREIOS_3.0_WAVE_A_D_CHANGELOG.md` |
| | FE MockSSE cutover → `docs/FRONTEND_BACKLOG.md` (deferred this block) |

**Companion files**

| File | Role |
|------|------|
| `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` | Status table + per-task entries (fill as you ship) |
| `tests/test_e14_wave_a.py` … `test_e17_wave_d.py` | Skeleton → real tests per wave |
| `plans/phase3/UNIFIED_EXECUTION_ORDER.md` | Append Steps **20–23** when starting (see §0.4) |

---

## 0. How to use this plan

### 0.1 Global rules (inherit from expansion)

1. Runtime remains: `Event → CEO → Agent/Workflow → Automation Engine → Execution Engine → Event`.
2. **No silent external I/O** — Twilio / HubSpot / Calendar / n8n only via EE (or AE → n8n client).
3. Tenant isolation never regresses: run `python gate_isolation_test.py` after any multi-tenant touch.
4. Dual-path monolith (`agent.py`, `crm_sync.py`, `follow_up.py`) stays until a future decommission window — **do not delete** in Waves A–D.
5. Prefer deterministic agents first; LLM only where it clearly beats rules (e.g. free-text objections later).
6. **One task at a time.** Mark done only when tests + docs checklist pass.

### 0.2 Mandatory after every task (no exceptions)

```text
# 1. Wave-local tests
python -m pytest tests/test_e14_wave_a.py -v   # or e15/e16/e17 for later waves

# 2. Related existing suites (pick what you touched)
python -m pytest tests/test_e2_automation.py tests/test_e3_executors.py tests/test_e6_sales_agent.py tests/test_e11_parity.py -v

# 3. Full regression (required at end of each wave, recommended after risky tasks)
python -m pytest tests/ -q

# 4. Tenant + DLQ when bus/CRM/EE touched
python gate_isolation_test.py
python gate_dlq_drill.py
python dlq_replay.py
```

**Docs to update every completed task** (same discipline as Phases 0–10):

| Doc | What to flip/add |
|-----|------------------|
| `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` | Status row → `[x]` + Entry block |
| `plans/phase3/UNIFIED_EXECUTION_ORDER.md` | Step 20–23 row when wave exits |
| `AGENTS.md` | New env vars, agents, events, degrade notes |
| `README.md` | `.env` reference + any new seed/scripts |
| `docs/N8N_INTEGRATION.md` | When n8n workflows go live |
| `docs/MAINTENANCE.md` | Ops runbook if new cron/tables |
| `docs/FRONTEND_BACKLOG.md` | New APIs FE can consume later (note only) |
| `plans/phase3/IREIOS_3.0_AI_Automation_Workflows.md` | Agent I/O when behavior changes |
| `plans/phase3/IREIOS_3.0_EVIDENCE_PACK.md` | Checkboxes for wave exit |

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` skipped (reason required)

### 0.3 Answers to planning questions

#### Q1 — Is n8n more practical here than LangGraph?

**Yes for IREIOS ops integrations. No as a replacement for in-process agent logic.**

| Dimension | **n8n** | **LangGraph** |
|-----------|---------|---------------|
| **Best for** | Side-plane: Slack/Teams, email, Drive CSV, partner webhooks, ops alerts | In-process multi-step AI state (plan → tool → approve → tool) inside Python |
| **Already in repo** | `app/automation_engine/n8n_client.py` → `POST {N8N_BASE_URL}/webhook/{id}` | `langgraph_runner.py` (linear fallback if package missing) |
| **Wired into `engine.submit` today?** | **No** — `template_type` stamped only (`engine.py` ~63–71) | **No** — same |
| **Needs external service?** | Yes (Docker / n8n Cloud) | Optional pip package only |
| **Touches WA 15s path?** | Must **not** — keep off hot path | Must **not** on TwiML critical path |
| **Practicality this sprint** | **Higher** — one Slack-on-hot-lead workflow proves Layer 6 “integration templates” and unblocks Marketing/CS ops without more Python | **Lower** — until you have a real multi-node graph (e.g. negotiate → HITL → CRM → WA); linear AE already covers 90% of actions |
| **Recommendation** | **Wave A/B: wire + ship 1–2 n8n workflows** | **Wave B optional:** dispatch `run_graph` for HITL multi-step only; keep `langgraph` optional dep |

**Rule of thumb:**  
- Deterministic single action → `template_type=linear` (default).  
- Human-in-the-loop multi-step **inside** IREIOS → LangGraph (or HITL pause already in AE).  
- Anything that needs Slack/email/Drive/non-Python connectors → **n8n**.

#### Q2 — Brochure / floor plan (WhatsApp) — **AS SHIPPED (post-G3)**

| Item | Detail |
|------|--------|
| **Module** | `app/agents/whatsapp_agent.py` |
| **Trigger** | `detect_tool_intent` after qualify path |
| **Keywords** | brochure / send details / … ; floor plan / layout / … |
| **Gate** | Intent + `lead.whatsapp_opt_in` |
| **Media** | `resolve_tool_media_url` → HTTPS-only `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` |
| **Default delivery** | Short caption + `take_outbound_media_url()` → TwiML `<Media>` in `main.py` (no reply-text scrape; **no** AE double-send — e12) |
| **Out-of-band / Sales** | AE `send_whatsapp` with `media_url` when configured; Sales NBA `send_brochure` attaches media |
| **Fallback** | Empty env → full plain-text `generate_brochure` / `generate_floorplan` |
| **Chat API** | May return `media_url` in JSON |
| **Events** | `brochure.sent` / `floorplan.sent` when media present |
| **Historical design notes** | Full Approach B task detail remains in §4.4 (implementation reference). |

### 0.4 UNIFIED_EXECUTION_ORDER append (when starting Wave A)

Add after Gate G2:

| Step | Unit | Exit gate |
|---:|---|---|
| **20** | Wave A — close dead loops + live integrations | A exit gate §1.9 |
| **21** | Wave B — deepen Maitri agents + AE templates | B exit gate §2.9 |
| **22** | Wave C — promote 6 placeholders → active agents | C exit gate §3.9 |
| **23** | Wave D — forecast/memory/n8n + brochure Approach B media | D exit gate §4.7 |
| **G3** | Waves A–D complete | Full `pytest` + isolation + DLQ + evidence pack Wave section |

---

## 1. Wave A — Close dead loops + live integrations

### 1.0 Benefit over current codebase

> **Today:** Marketing/CS agents are registered but mostly idle (no producers). HubSpot returns demo UUIDs. Calendar returns synthetic `visit_*`. AE accepts `template_type=n8n|langgraph` but always runs linear EE. HITL approvals never auto-expire. Admin notifications are log-only.  
> **After Wave A:** Real contacts in HubSpot, real calendar events on visit book, weekly marketing reports fire without manual bus inject, booking confirms wake CS, AE can hand off to n8n, managers get real notify paths, stale approvals clear. **Existing agents finally execute in production-shaped loops.**

### 1.1 Task A.0 — Integration credentials (ops, parallel)

Do **before or alongside** A.1–A.4 code. No app behavior change until env is set.

#### A.0.1 HubSpot (CRM) — highest ROI (code already complete)

**Why it helps:** `lead.created` → `crm_automation` → AE → `CRMExecutor` → `crm_sync._push_to_hubspot` already runs. Demo key returns fake UUID (`crm_sync.py` ~126–129). Real token = sales team sees WA-qualified leads with phone/name/budget/temperature in HubSpot without a second data entry.

**Signup / credentials (current HubSpot private apps, 2025–2026):**

1. HubSpot account (any paid tier that allows private apps; free CRM often enough for Contacts API).
2. Super Admin → **Development** → **Legacy apps** → **Create legacy app** → **Private**.  
   Docs: [HubSpot private apps](https://developers.hubspot.com/docs/api/private-apps).
3. **Scopes** (minimum):
   - `crm.objects.contacts.write`
   - `crm.objects.contacts.read`
   - Optional later: `crm.objects.deals.write`, `tickets` if you add tasks/deals.
4. Create app → **Auth** → **Show token** → copy access token (**once**; rotate if leaked).
5. **Custom properties** (if `CRM_SYNC_EXTENDED_PROPERTIES=true`, default): create contact properties in HubSpot settings matching snake_case used in `crm_sync._EXTENDED_CRM_PROPERTIES`:
   - `location`, `intent`, `property_type`, `visit_date`, `assignee`, `budget_alignment_status`, `urgency_level`, `engagement_score`, `lead_temperature`
   - Type: Single-line text (or number for scores). Internal name must match.
   - **Simpler first smoke:** set `CRM_SYNC_EXTENDED_PROPERTIES=false` so only base `firstname`, `phone`, `budget`, `lifecyclestage` push; enable extended after props exist (4xx unknown property already retries without that field — P5.2).

**`.env`:**

```env
CRM_API_URL=https://api.hubapi.com/crm/v3/objects/contacts
CRM_API_KEY=pat-na1-xxxxxxxx   # private app access token
CRM_SYNC_EXTENDED_PROPERTIES=true   # or false for first smoke
IS_PRODUCTION=false                 # keep false until go-live; demo key hard-fails if true
```

**Smoke:**

```text
# 1. WA/chat create lead with name+phone
# 2. Check HubSpot Contacts — new contact
# 3. Change location on lead → wait ≤5m crm_resync_job → property updates
# 4. logs: no "demo-hubspot" short-circuit
```

**Code refs (no change required for basic live CRM):**

- `crm_sync.py` — `_push_to_hubspot`, `build_crm_properties`
- `app/execution_engine/crm_executor.py`
- `app/workflows/crm_automation.py`
- Scheduler: `main.py` `crm_resync_job` every 5 min

---

#### A.0.2 Google Calendar — site visits become real

**Why it helps:** When `schedule_visit` runs, `CalendarExecutor` creates a real Calendar event instead of `provider: "stub"` synthetic id (`calendar_executor.py` L5–10, L93+). Sales/ops see visits on a shared calendar.

**Credentials (service account — matches existing code):**

Docs: [Create credentials](https://developers.google.com/workspace/guides/create-credentials) · [Calendar API](https://developers.google.com/calendar/api/guides/overview)

1. [Google Cloud Console](https://console.cloud.google.com/) → create/select project.
2. **APIs & Services → Enable APIs** → enable **Google Calendar API**.
3. **IAM & Admin → Service Accounts → Create** (e.g. `ireios-calendar`).
4. Service account → **Keys → Add key → JSON** → download; store **outside git** e.g. `secrets/gcal-sa.json` (add `secrets/` to `.gitignore` if not already).
5. Create or pick a Google Calendar (personal or Workspace) → **Settings → Integrate calendar → Calendar ID** (often email-like).
6. **Share calendar** with the service account email (`…@….iam.gserviceaccount.com`) as **Make changes to events**.  
   (Service accounts have no inbox — uncheck “Notify”.)
7. No domain-wide delegation needed if the calendar is shared directly to the SA.

**`.env`:**

```env
GOOGLE_CALENDAR_ID=primary_or_full_calendar_id@group.calendar.google.com
GOOGLE_CALENDAR_CREDENTIALS_JSON=D:/path/to/secrets/gcal-sa.json
GOOGLE_CALENDAR_TIMEZONE=Asia/Kolkata
```

**Deps:** `google-api-python-client`, `google-auth` (confirm in `requirements.lock`; add if missing and lock).

**Smoke:** AE/EE `schedule_visit` with `visit_date` ISO → Calendar UI shows event; response `provider: "google_calendar"`, `html_link` present.

**Code refs:** `app/execution_engine/calendar_executor.py` (`_create_google_event`, scopes `calendar`).

---

#### A.0.3 n8n — external workflow plane

**Why it helps:** Slack/email/Drive without redeploying FastAPI. Complements AE; does **not** replace CEO or WA path. See `docs/N8N_INTEGRATION.md`.

**Install options (pick one):**

| Option | Notes |
|--------|-------|
| **n8n Cloud** | Fastest: [n8n.io](https://n8n.io) signup → instance URL |
| **Docker (self-host)** | Official image `n8nio/n8n`; expose port 5678; set webhook URL reachable from API host |

Example compose service (add only if not present; document in MAINTENANCE):

```yaml
# illustrative — merge carefully into docker-compose.yml
n8n:
  image: n8nio/n8n:latest
  ports: ["5678:5678"]
  environment:
    - N8N_HOST=localhost
    - WEBHOOK_URL=http://localhost:5678/
  volumes: ["n8n_data:/home/node/.n8n"]
```

**First workflow (after A.3 wires AE):**

1. n8n UI → Workflow → **Webhook** node (path e.g. `ireios-hot-lead`, method POST).
2. Add **Slack** (or Discord/email) node → message from body JSON.
3. Activate workflow → copy production webhook path id.
4. `.env`:

```env
N8N_BASE_URL=http://localhost:5678   # or https://your.app.n8n.cloud
N8N_API_KEY=                          # if you enforce header auth on webhook; else use a shared secret in payload validation
```

**Note:** Current client sends header `X-N8N-API-KEY` (`n8n_client.py` L48). Either configure n8n Header Auth on the webhook or extend client later to match n8n’s default. Prefer documenting the exact auth mode you choose in `docs/N8N_INTEGRATION.md`.

**Client call shape (already coded):**

```text
POST {N8N_BASE_URL}/webhook/{workflow_id}
Header: X-N8N-API-KEY, Content-Type: application/json
Body: action payload / event envelope
```

Empty config → `{"error":"n8n_not_configured"}` (never crash).

---

#### A.0.4 Already configured (verify only)

| Service | Verify |
|---------|--------|
| Twilio | Real `TWILIO_*`; `TEST_MODE=false` only when ready to send |
| Postgres / Redis | `docker compose up -d`; app lifespan EventBus start |
| Neo4j | `GET /api/v1/graph/health`; WA reply path graph context |

---

### 1.2 Task A.1 — Publish `cron.weekly_report` (unlock Marketing)

- **Benefit:** Marketing agent stops being dead code.
- **Files:**
  - Create `app/workflows/weekly_marketing_cron.py` (or add to existing workflows package)
  - `main.py` lifespan — `scheduler.add_job(..., id="weekly_marketing_report")`
- **Steps:**
  1. Job loads active `Client` rows (or distinct `client_id` from leads).
  2. For each client, short-lived Redis/`event_bus` publish:
     - `event_type="cron.weekly_report"`
     - `tenant_id=f"Client_{id}"`
     - `entity_id="marketing"`
     - `payload={"source":"scheduler"}`
     - `source="weekly_marketing_cron"`
  3. Cron: e.g. Monday 08:00 IST — or interval 1h under `FOLLOW_UP_TEST_MODE` / new `MARKETING_CRON_TEST=true` for dev.
  4. Mirror competitor_monitor pattern for thread-safe bus publish from APScheduler thread (see `app/workflows/competitor_monitor.py`).
- **Code refs to mirror:**
  - `app/agents/marketing_agent.py` `MARKETING_EVENTS` L22
  - `main.py` L348–355 scheduler jobs
- **Tests (`test_e14_wave_a.py`):**
  - Job publishes one event per client (mock bus).
  - Handler `marketing_agent_handler` still emits `marketing.report.generated` (existing e11).
- **Done:** With Redis up, after job tick, stream contains `cron.weekly_report` and `marketing.report.generated`.
- **Rollback:** Remove scheduler job id.
- **Status:** `[ ]`

### 1.3 Task A.2 — Lifecycle event producers (unlock CS)

- **Benefit:** CS handler receives real work after booking / ops inject.
- **Files:**
  - Emit `booking.confirmed` where visit is scheduled successfully (prefer EE success path or WhatsAppAgent/qualification after visit fields complete + `schedule_visit` success).
  - Create `app/api/lifecycle.py` or admin routes under `main.py`:
    - `POST /api/v1/lifecycle/events` (JWT or `X-Admin-Key`) body: `{event_type, lead_id, payload}` for `payment.due|payment.received|document.pending|renewal.due|booking.confirmed|customer.onboarded`
  - Optionally: after CalendarExecutor success, EE event map already may publish `site_visit.scheduled` — **also** publish `booking.confirmed` with lead_id for CS (document distinction: site visit ≠ full booking; for MVP treat confirmed visit as booking signal **or** name payload `kind=site_visit`).
- **Code refs:**
  - `app/agents/customer_success_agent.py` `CS_EVENTS` L23–29
  - EE `register_event` map in `execution_engine.py` / registry
- **Tests:**
  - Inject `booking.confirmed` → CS calls `ae_submit` with `notify_agent`.
  - Unknown event_type → 400.
  - Other tenant lead_id → 404.
- **Done:** Manual inject wakes CS without waiting for Stripe.
- **Status:** `[ ]`

### 1.4 Task A.3 — AE dispatches `template_type` n8n | langgraph

- **Benefit:** Scaffold runners become reachable; Layer 6 claim becomes honest.
- **Files:** `app/automation_engine/engine.py` (`submit` after L63–71)
- **Steps:**
  1. After HITL check, branch:
     ```python
     if template_type == "n8n":
         wf = action_request["parameters"].get("workflow_id") or action_request.get("workflow_id")
         result = await n8n_client.trigger_workflow(wf, action_request)
         # optional: still EE for dual-write; default: n8n-only result
         return result
     if template_type == "langgraph":
         from app.automation_engine.langgraph_runner import run_graph
         state = await run_graph({"action_request": action_request})
         if state.get("ready_to_execute"):
             return await _execute_with_retry(action_request, attempt)
         return {"status": "error", "error": "langgraph_not_ready", "state": state}
     # linear default
     return await _execute_with_retry(...)
     ```
  2. On `n8n_not_configured`, honor `fallback_action` if present (already partially supported for EE errors).
  3. Never use n8n on WhatsApp TwiML critical path.
- **Tests (`test_e2_automation.py` extend + e14):**
  - `template_type=n8n` + unconfigured → `n8n_not_configured`.
  - `template_type=n8n` + mock client success → success.
  - `template_type=langgraph` → reaches execute path or linear fallback when package missing.
  - Default linear unchanged (regression).
- **Done:** Branch coverage in tests green.
- **Status:** `[ ]`

### 1.5 Task A.4 — Schedule `expire_stale_approvals`

- **Files:** `main.py` scheduler; already implemented `engine.expire_stale_approvals` L134–158
- **Steps:** `scheduler.add_job(lambda: expire_stale_approvals(24), "interval", minutes=15, id="expire_approvals")`
- **Tests:** Create old pending `ApprovalRequest` → call expire → status `expired`.
- **Status:** `[ ]`

### 1.6 Task A.5 — NotificationExecutor real paths for admin/manager

- **Benefit:** CS/marketing notify_admin and HITL manager_approval leave the log sink.
- **Files:** `app/execution_engine/notification_executor.py` L42–54
- **Steps:**
  1. `notify_admin`: resolve manager/director Agent phone for `client_id` (reuse `resolve_escalation_recipient` / `pick_escalation_agent` from `notification_service.py`) → Twilio via `app/execution_engine/outbound.py` or `send_whatsapp` nested AE call carefully (prefer direct outbound helper to avoid recursion).
  2. `manager_approval`: WhatsApp body with approval id + deep link text to dashboard approvals (FE may still be mock — SMS still valuable).
  3. Keep `hot_lead` path unchanged.
- **Tests:** monkeypatch outbound; assert called for `notify_admin` with message.
- **Status:** `[ ]`

### 1.7 Task A.6 — Docs + env example for Wave A integrations

- Update `.env.example`, `AGENTS.md`, `README.md`, `docs/N8N_INTEGRATION.md` (auth mode + first workflow), `docs/MAINTENANCE.md` § integrations.
- **Status:** `[ ]`

### 1.8 Wave A test skeleton ID

| Suite | File |
|-------|------|
| Wave A | `tests/test_e14_wave_a.py` |

### 1.9 Wave A exit gate

- [ ] HubSpot smoke: real contact created (or documented skip if no token in CI)
- [ ] Calendar smoke: `provider=google_calendar` when creds set
- [ ] `cron.weekly_report` → `marketing.report.generated` in tests
- [ ] Lifecycle inject → CS `ae_submit`
- [ ] AE n8n/langgraph branches unit-tested
- [ ] `expire_stale_approvals` scheduled + tested
- [ ] `python -m pytest tests/ -q` green
- [ ] `gate_isolation_test.py` PASS
- [ ] Changelog Wave A all `[x]`

---

## 2. Wave B — Deepen Maitri agents (Sales, CS, Marketing, AE templates)

### 2.0 Benefit over current codebase

> **Today:** Sales AI is on-demand HTTP only; CS only log-notifies admins; Marketing suggestions are static and never scheduled; competitor alerts have no consumer; AE has no named templates.  
> **After Wave B:** Hot/scored leads auto-trigger Sales NBA → real AE actions; customers get WhatsApp lifecycle messages; marketing reports include competitor signals; named workflow templates + optional n8n Slack on hot lead. **Automation matches the Workflows doc intent, not just registry names.**

### 2.1 Task B.1 — SalesAgent on CEO bus + action dispatch

- **Files:** `app/agents/sales_agent.py`, `main.py` register, optionally `app/agents/sales_bus_handler.py`
- **Subscriptions:** `lead.scored`, `lead.hot`, `conversation.updated` (debounce: skip if same lead acted &lt; N minutes — Redis key `sales_ai_lock:{lead_id}` TTL 10m)
- **Steps:**
  1. Extract `lead_id` / tenant from envelope (mirror `lead_scoring_handler.py`).
  2. Load lead tenant-scoped; `run_sales_ai` (existing).
  3. Map `recommendation.action` → AE:
     | action | AE |
     |--------|-----|
     | `escalate_hot` | `notify_agent` kind=`hot_lead` |
     | `schedule_site_visit` | `schedule_visit` if `visit_date` else skip |
     | `send_brochure` | **Do not** double-send if chat just did; publish `sales.nba.suggested` only **or** out-of-band WA if phone and not recent brochure |
     | `nurture_followup` | no-op (followup_arm owns timing) |
     | `assign_agent` | already in `run_sales_ai` |
     | `request_info` | optional WA template via AE |
  4. Keep `POST /api/v1/leads/{id}/sales-ai` as sync API.
  5. Keyword objections (B.2 can land same PR): scan last user message for price/delay/competitor phrases → `LeadMemory` type `objection`.
- **Code refs:**
  - `sales_agent.py` `recommend_next_action` L41–78
  - `main.py` Sales route ~1435
  - Registration pattern: `register_marketing_agent`
- **Tests (`test_e15_wave_b.py` + extend `test_e6_sales_agent.py`):**
  - Bus envelope hot lead → `ae_submit` called with `notify_agent`.
  - Bad tenant → no-op.
  - Debounce: second event within TTL → no second notify.
- **Status:** `[ ]`

### 2.2 Task B.2 — Objection detection (lightweight)

- **Files:** `app/agents/sales_agent.py` or `app/services/objection_service.py`; `app/memory/conversation_memory.py` if storing
- **Steps:** Rule lexicon → tags `price`, `timing`, `location`, `trust`, `competitor`. Persist memory. Feed Sales NBA (price → hand off event `negotiation.requested` for Wave C).
- **Tests:** Message “too expensive” → tag `price`.
- **Status:** `[ ]`

### 2.3 Task B.3 — Customer Success → `send_whatsapp` templates

- **Files:** `app/agents/customer_success_agent.py`
- **Steps:**
  1. Resolve lead phone from `entity_id` / payload `lead_id`.
  2. If phone: `ae_submit(send_whatsapp, body=template[event_type])`.
  3. Else fallback `notify_admin` (A.5 real path).
  4. Add `customer.onboarded` to `CS_EVENTS`.
  5. Templates: payment due, document, referral ask, review ask, renewal, booking welcome (short, opt-in respectful).
- **Tests:** Mock AE; assert `action_type=send_whatsapp` when phone present.
- **Status:** `[ ]`

### 2.4 Task B.4 — Marketing: competitor + richer suggestions

- **Files:** `app/agents/marketing_agent.py`, `app/services/prediction_service.py`
- **Steps:**
  1. Subscribe also `market.alert.generated`.
  2. Fold alert payload into report.
  3. Suggestions: use segment counts + top locations from DB (still no Meta/Google Ads API).
  4. Optional: `notify_admin` summary after weekly report.
- **Do not** claim live ad spend.
- **Status:** `[ ]`

### 2.5 Task B.5 — Named AE templates + first n8n workflow

- **Create:** `app/automation_engine/templates/hot_lead_notify.py`, `visit_booking.py` (functions returning action_request dicts)
- **n8n:** Workflow “IREIOS Hot Lead → Slack”; document webhook id in `docs/N8N_INTEGRATION.md`
- **Sales/CS** may set `template_type="n8n"` + `workflow_id` for ops fan-out **in addition to** linear notify (or fallback chain).
- **Status:** `[ ]`

### 2.6 Task B.6 — Competitor alert → notify managers

- **Files:** `app/workflows/competitor_monitor.py`
- After publish `market.alert.generated`, optional AE `notify_agent` if matches non-empty.
- **Status:** `[ ]`

### 2.7 Task B.7 — Optional `create_task` executor

- **Model:** `Task` table or HubSpot engagement API (if HubSpot token has scope).
- **EE:** `TaskExecutor` action `create_task`.
- **Sales** NBA escalate can create task “Call lead X”.
- **If HubSpot tasks too heavy:** PG `agent_tasks` table is enough for MVP.
- **Status:** `[ ]`

### 2.8 Wave B tests

| Suite | File |
|-------|------|
| Wave B | `tests/test_e15_wave_b.py` |

Also extend: `test_e6_sales_agent.py`, `test_e11_parity.py`.

### 2.9 Wave B exit gate

- [ ] Sales registered active on CEO; list_agents shows active
- [ ] lead.scored/hot → AE action in tests
- [ ] CS WhatsApp path unit-tested
- [ ] Marketing consumes weekly + market.alert
- [ ] n8n workflow doc + AE trigger test (mock HTTP)
- [ ] Full pytest + isolation green
- [ ] Changelog + AGENTS.md agent list updated

---

## 3. Wave C — Promote 6 placeholders to real agents

### 3.0 Benefit over current codebase

> **Today:** `pricing_agent`, `negotiation_agent`, `inventory_agent`, `legal_agent`, `finance_agent`, `onboarding_agent` are CEO `status=placeholder` log-only no-ops (`app/agents/placeholders.py`). Layer 2 “15 agents” is incomplete.  
> **After Wave C:** All six are **active**, event-driven, thin but real domain logic, producing AE actions and bus events. Negotiation + pricing close the commercial loop with HITL; inventory feeds WA/Sales context; onboarding/finance/legal feed CS lifecycle producers. **PDF Layer 2 / L7 claims become defensible.**

### 3.1 Shared agent implementation pattern

Every agent:

```text
1. Create app/agents/{name}.py with async handler(envelope)
2. _resolve_client_id + load Lead tenant-scoped
3. decide() deterministic dict
4. ae_submit(...) and/or event_bus.publish(...)
5. register_{name}(ceo) status="active", specific subscriptions (NOT "*")
6. Remove id from PLACEHOLDER_AGENTS in placeholders.py
7. Register in main.py lifespan next to other register_* calls
8. tests/test_e16_wave_c.py cases
```

### 3.2 Minimal data model (ship with C.1–C.3)

**Create migration via `migrate_db.py` or SQLAlchemy create:**

```text
inventory_units
  id, client_id, project_name, tower, unit_code, bhk, location,
  list_price, status (available|held|sold), carpet_sqft, meta_json

pricing_rules  (optional JSON file per client if table heavy)
  client_id, location, bhk, min_budget, max_budget, list_price, notes
```

**Seed:** `python seed_inventory.py --client-id 1` (new script, ~15 dummy Pune units).

**Neo4j (optional same wave):** upsert `:Unit` / `:Project` on inventory write for twin/graph later.

### 3.3 Task C.1 — `negotiation_agent` (do first — L7)

- **Subscriptions:** `negotiation.requested`, `conversation.updated` (filter objections), `lead.scored`
- **Logic:**
  - If objection tag `price` and budget vs list_price gap known → draft counter message (text).
  - If proposed discount_pct &gt; `settings.MAX_AUTO_DISCOUNT_PCT` (new, default 2) → `requires_approval=True` AE action (send_whatsapp or notify).
  - Else AE `send_whatsapp` nurture script **or** publish only `negotiation.offer.suggested` for human (safer default: suggest + notify manager, auto-send only low-risk).
- **HITL:** Use existing AE approval APIs.
- **Publish:** `negotiation.offer.suggested` / `negotiation.escalated`
- **Tests:** high discount → pending_approval; low → success path.
- **Status:** `[ ]`

### 3.4 Task C.2 — `pricing_agent`

- **Subscriptions:** `lead.qualified`, `conversation.updated`, `pricing.quote.requested`
- **Logic:** Match `pricing_rules` / inventory median by location+bhk → quote dict.
- **Publish:** `pricing.quote.generated` with `{list_price, emi_hint, currency:"INR"}`
- **Consume:** WhatsAppAgent `_graph_extra_context` or new `extra_context` hook can append last quote (best-effort read from Redis cache `pricing:{lead_id}` TTL 1h set by agent).
- **No** external pricing API required.
- **Status:** `[ ]`

### 3.5 Task C.3 — `inventory_agent`

- **Subscriptions:** `lead.qualified`, `site_visit.scheduled`, `inventory.sync_requested`
- **Logic:** SQL match available units by location/property_type/budget band; rank top 3.
- **Publish:** `inventory.match.generated`
- **KG:** best-effort unit upsert.
- **API (optional):** `GET /api/v1/inventory/match?lead_id=`
- **Status:** `[ ]`

### 3.6 Task C.4 — `onboarding_agent`

- **Subscriptions:** `booking.confirmed`
- **Logic:** checklist (welcome WA, document list, assign CS owner); publish `customer.onboarded`; AE `send_whatsapp` welcome; `update_crm` lifecycle note.
- **Bridges** booking → CS.
- **Status:** `[ ]`

### 3.7 Task C.5 — `finance_agent`

- **Subscriptions:** `booking.confirmed`, `cron.payment_scan` (new weekly/daily cron)
- **Logic:** If booking payload has `amount`/`due_date` or stub schedule (+7/+30 days), publish `payment.due` for CS.
- **API:** `GET /api/v1/finance/cashflow-summary?client_id` heuristic (sum due − received stubs).
- **Not** full accounting.
- **Status:** `[ ]`

### 3.8 Task C.6 — `legal_agent`

- **Subscriptions:** `booking.confirmed`, `cron.document_scan`
- **Logic:** Required docs list (Aadhaar, PAN, agreement); missing → `document.pending` events for CS.
- **No** contract generation LLM required.
- **Status:** `[ ]`

### 3.9 Task C.7 — Remove empty placeholders + registry proof

- `PLACEHOLDER_AGENTS` empty or only future names.
- `ceo.list_agents()` shows 6 new `active`.
- Update Workflows doc §10.
- **Status:** `[ ]`

### 3.10 Wave C tests

| Suite | File |
|-------|------|
| Wave C | `tests/test_e16_wave_c.py` |

Per-agent: handler happy path, bad tenant, publish/AE mock.

### 3.11 Wave C exit gate

- [ ] Zero of the six remain `placeholder` (unless explicitly `[-]` with reason)
- [ ] Inventory seed works; match returns ≥1 unit in test DB
- [ ] Negotiation HITL path green
- [ ] Onboarding emits `customer.onboarded` → CS test chain
- [ ] Full pytest + isolation
- [ ] Docs: AGENTS.md agent table, Workflows §10, changelog

---

## 4. Wave D — Forecast depth, memory, n8n polish, brochure Approach B

### 4.0 Benefit over current codebase

> **Today:** Forecast Engine is score + conversion only; FE still mocks revenue; conversation memory API exists but is not auto-written on chat; brochure/floor plan is **plain text only**; n8n may have only one workflow.  
> **After Wave D:** Honest heuristic prediction routes; memory on WA turns; **real PDF/image document bubbles on WhatsApp** (Approach B); 2–3 n8n ops workflows; G3 evidence. **Joint L4/L9 depth + credible brochure sharing without fake ML claims.**

### 4.1 Task D.1 — Forecast / prediction routes (honest heuristics)

- **Files:** `app/services/prediction_service.py`, `main.py` routes
- **Add (JWT, client-scoped):**
  - `GET /api/v1/predictions/revenue` — sum over open leads of `f(budget) * conversion_probability/100`
  - `GET /api/v1/predictions/cancellation-risk` — wrap/extend `detect_at_risk`
  - `GET /api/v1/predictions/inventory` — counts by status from `inventory_units`
  - `GET /api/v1/predictions/cashflow` — finance_agent stub schedule aggregate
- **Document** as heuristic MVP in OpenAPI note — not “ML accuracy”.
- **Tests:** `test_e17_wave_d.py` + extend `test_e8_prediction.py`
- **FE backlog note:** replace `mockForecastData` when Mayank ready.
- **Status:** `[ ]`

### 4.2 Task D.2 — Conversation memory auto-write on WA turn

- **Files:** `app/agents/whatsapp_agent.py`, `app/memory/conversation_memory.py`
- **Steps:** After successful turn, best-effort `extract_and_store` (never block reply hard; try/except).
- **Tests:** process_chat → memory row exists (mock extract).
- **Status:** `[ ]`

### 4.3 Task D.3 — n8n workflows 2–3

| Workflow | Trigger | Action |
|----------|---------|--------|
| Hot lead Slack | AE n8n or Redis (doc both) | Slack channel |
| Weekly marketing | `marketing.report.generated` via n8n webhook from marketing_agent optional second publish | Email/Drive CSV |
| DLQ depth | cron in n8n calling admin metrics or stub | Alert |

Update `docs/N8N_INTEGRATION.md` status → workflows provisioned.

- **Status:** `[ ]`

### 4.4 Task D.4 — Brochure / floor plan media (**Approach B** — required for Wave D exit)

**Benefit over current codebase:**  
Buyers receive a **WhatsApp document attachment** (PDF/image opens in-chat) instead of canned plain text. Matches original Phase 5.5 / Workflows intent (`share_brochure` → media). Reuses existing `WhatsAppExecutor.media_url` — no new executor.

#### 4.4.0 Decision (locked)

| Option | Description | Chosen? |
|--------|-------------|---------|
| **A** | Put HTTPS link in message `body` only | No — extra tap, weaker UX |
| **B** | Host static PDF/image once; Twilio **`MediaUrl`** = same HTTPS URL → in-chat document bubble + short caption | **Yes** |
| **C** | Generate personalized PDF per lead (ReportLab etc.) | No — out of scope for Waves A–D |
| **D** | Upload raw bytes via Twilio Media Content API each send | No — more moving parts than B |

**Twilio reality:** Approach B still uses a **public HTTPS URL** under the hood. Twilio fetches that URL and delivers the file as a WhatsApp media message. Backend does **not** need to stream PDF bytes on the hot path.

#### 4.4.1 Current code map (read before editing)

| Concern | File | Notes |
|---------|------|--------|
| Intent detect | `app/agents/whatsapp_agent.py` `detect_tool_intent` ~L39–46 | Keep keywords; expand only if needed |
| Text generators | same `generate_brochure` / `generate_floorplan` ~L53–85 | **Keep as fallback** when no media URL |
| Tool branch | same `WhatsAppAgent.process_chat` ~L221–251 | Today returns plain `tool_reply` string |
| AE outbound | same `_dispatch_outbound` ~L255–277 | `ae_submit(send_whatsapp)` — **add `media_url` to parameters** when resolved |
| Executor | `app/execution_engine/whatsapp_executor.py` ~L47, L60–66, L99–100 | Already: `kwargs["media_url"] = [url]`; body optional if media present (`L65–66`) |
| WA webhook TwiML | `main.py` ~L898–927 | Builds `MessagingResponse()` + message body from chat reply — **media not set today** |
| Double-send guard | `tests/test_e12_bus_wiring.py` | Must stay green: default path must not AE **and** TwiML-deliver the same payload twice |
| EE event map | `app/execution_engine/execution_engine.py` / registry | Add/confirm `brochure.sent` / `floorplan.sent` after successful media send if missing |
| Config pattern | `config.py` `Settings` | Add URL fields (forbid_extra requires explicit fields) |

#### 4.4.2 Config / hosting (ops + code)

**`.env` / `config.py` / `.env.example`:**

```env
# Approach B — public HTTPS URLs Twilio can GET (PDF or image). Empty = text fallback.
BROCHURE_MEDIA_URL=https://cdn.example.com/clients/1/brochure.pdf
FLOORPLAN_MEDIA_URL=https://cdn.example.com/clients/1/floorplan.pdf
# Optional later (Wave C inventory): per-project override in DB; global env is MVP.
```

**Hosting options (pick one):**

| Host | Notes |
|------|--------|
| S3 / GCS / Cloudflare R2 + public read | Best for prod |
| FastAPI `StaticFiles` mount e.g. `/static/brochures/...` behind HTTPS ngrok/prod domain | Fine for local Twilio sandbox if URL is publicly reachable |
| Existing CDN | Prefer |

**Constraints (Twilio WhatsApp media):**

- URL must be **HTTPS**, publicly reachable (no localhost unless tunnel).
- Prefer PDF or JPEG/PNG within Twilio WhatsApp media size limits (check current Twilio docs; typically low tens of MB — keep brochures lean).
- Content-Type should be correct (`application/pdf` / `image/jpeg`).
- Sandbox vs production WhatsApp senders may differ; smoke on sandbox first with `TEST_MODE=false` only when ready.

**Do not** commit large binary PDFs to git if avoidable — document path in `docs/MAINTENANCE.md` or store under `static/brochures/.gitkeep` + README.

#### 4.4.3 Resolve media URL (pure helper)

**Create** (or add to `whatsapp_agent.py`):

```python
def resolve_tool_media_url(tool: str, lead: Lead | None = None, client_id: int | None = None) -> str | None:
    """Return public HTTPS URL for brochure|floorplan, or None → text fallback.

    MVP: settings.BROCHURE_MEDIA_URL / FLOORPLAN_MEDIA_URL.
    Later: client row / inventory_units.meta_json override by location.
    """
```

- Validate scheme `https://` (reject empty / `http://` in production if desired).
- Unit-test pure function without Twilio.

#### 4.4.4 Caption + fallback body

When media URL present:

- **Caption `body`:** short personalized line (reuse name/location/type), e.g.  
  `Hi {name}, here is the {tool} for {pt} in {loc}.`  
  Do **not** dump the full multi-line plain-text brochure when media is attached (redundant).
- When media URL **absent:** keep full `generate_brochure` / `generate_floorplan` text (today’s behavior).

#### 4.4.5 Delivery architecture (critical — pick one primary path)

**Recommended primary path for inbound WhatsApp (avoids double-send, uses existing EE purity):**

```text
User: "send brochure"
  → detect_tool_intent == brochure
  → resolve_tool_media_url
  → IF media URL:
       1. Save assistant Message row (caption or "Sent brochure PDF")
       2. Return a structured result from process_chat OR side-channel
          that main.py understands — see Option W below
       3. Single outbound with media_url (TwiML Media XOR AE send — not both)
  → ELSE:
       return plain generate_* text as today (TwiML body only, no AE)
```

**Option W — WhatsApp webhook (choose one; document in PR):**

| Option | How | Pros | Cons |
|--------|-----|------|------|
| **W1 (preferred)** | Change tool path to always `dispatch_via_ae=True` when `media_url` set; TwiML reply = short ack only (`"Sending the brochure now…"`) **or** empty `<Response/>` if AE is fast enough — **never** put the PDF in TwiML and AE | Reuses EE/DLQ/observability; `media_url` already on executor | Two messages if ack + media (acceptable) or need careful single-message design |
| **W2** | Extend TwiML in `main.py`: `msg = twiml.message(caption); msg.media(media_url)` when chat layer returns media | One WhatsApp message | Must plumb `media_url` out of `process_chat` return type; no EE DLQ on that send |
| **W3** | TwiML body = caption + link only | Easy | **Rejected** — not Approach B UX |

**Locked recommendation: W1** for media; keep **plain-text path** as today (TwiML body, `dispatch_via_ae=False`) for fallback so e12 stays meaningful.

Concrete W1 steps:

1. Extend `WhatsAppAgent.process_chat` return **or** use a small result object / thread-local / response dict:

   ```python
   # Preferred clean API (breaking callers carefully):
   # return str | ToolReply(body=str, media_url=str|None, tool=str|None)
   ```

   If keeping `str` return for chat JSON compatibility: return caption string, and when media present set `dispatch_via_ae=True` always for that branch with parameters:

   ```python
   await ae_submit({
       "action_type": "send_whatsapp",
       "tenant_id": f"Client_{client_id}",
       "entity_id": session_id,
       "parameters": {
           "to": lead.phone or ...,
           "body": caption,           # short
           "media_url": media_url,  # Approach B
           "source": "whatsapp_agent_v3",
           "tool": intent,            # brochure | floorplan
       },
       "source": "whatsapp_agent_v3",
   })
   ```

2. TwiML in `main.py`: if tool media was AE-dispatched, return **ack-only** body (same caption or `"I've sent the brochure PDF."`) — **do not** attach Media in TwiML.

3. `_dispatch_outbound` (~L255): add `media_url` kw into `parameters` when provided.

4. Chat REST `/api/v1/chat`: return JSON including optional `media_url` for FE preview (document in OpenAPI / FRONTEND_BACKLOG).

#### 4.4.6 Sales NBA + bus path

- When Wave B Sales maps `send_brochure` → AE, include `resolve_tool_media_url("brochure", lead)`.
- Same for floorplan if NBA ever adds it.
- Idempotency: skip if identical media sent to same lead in last N minutes (optional Redis key `brochure_sent:{lead_id}`).

#### 4.4.7 Events

| Event | When |
|-------|------|
| `brochure.generated` / `floorplan.generated` | Keep for text-only or pre-send signal (existing) |
| `brochure.sent` / `floorplan.sent` | After EE success with `media_url` (or TwiML media if W2) — payload `{lead_id, media_url, tool, sid?}` |

Wire EE `register_event` map if `send_whatsapp` currently only emits `whatsapp.sent` — either enrich `whatsapp.sent` payload with `tool`+`media_url` **or** publish specific events from agent after AE success.

#### 4.4.8 Files to touch (checklist)

| File | Change |
|------|--------|
| `config.py` | `BROCHURE_MEDIA_URL: str = ""`, `FLOORPLAN_MEDIA_URL: str = ""` |
| `.env.example` | Document both + HTTPS requirement |
| `app/agents/whatsapp_agent.py` | `resolve_tool_media_url`; tool branch W1; caption; `_dispatch_outbound` media |
| `app/execution_engine/whatsapp_executor.py` | Confirm only — already supports media; optional log tool name |
| `main.py` | Ack-only TwiML when media AE path; optional chat JSON `media_url` |
| `app/agents/sales_agent.py` | NBA send_brochure parameters include media when Wave B dispatches |
| `AGENTS.md` | Update brochure section to Approach B |
| `docs/MAINTENANCE.md` | Hosting + Twilio media smoke |
| `docs/FRONTEND_BACKLOG.md` | Chat may return `media_url` |
| `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` | D.4 entry |
| `tests/test_e17_wave_d.py` | Real tests (below) |
| Keep green | `tests/test_e12_bus_wiring.py`, `tests/test_e5_whatsapp_agent.py`, `tests/test_e3_executors.py` |

#### 4.4.9 Implementation steps (ordered)

1. Add Settings + `.env.example`; no behavior change when empty.
2. Implement `resolve_tool_media_url` + unit tests (empty → None; set → URL).
3. Extend `_dispatch_outbound` to pass `media_url`.
4. Tool branch: if URL → caption + AE send with media (W1); else plain text return (no AE).
5. Adjust `main.py` WhatsApp handler so media path does not TwiML-duplicate the PDF.
6. Publish `brochure.sent` / `floorplan.sent` (or enriched `whatsapp.sent`).
7. Smoke: Twilio sandbox, real PDF URL, user asks “send brochure” → document bubble.
8. Docs: AGENTS.md, MAINTENANCE, FRONTEND_BACKLOG, Workflows §1 note “media via MediaUrl”.
9. Regression suite full + e12.

#### 4.4.10 Tests (`tests/test_e17_wave_d.py` — replace skeletons)

```text
test_resolve_tool_media_url_empty_fallback
test_resolve_tool_media_url_https_brochure
test_tool_branch_with_media_calls_ae_with_media_url   # monkeypatch ae_submit
test_tool_branch_without_media_returns_plain_text_no_ae  # e12-compatible
test_dispatch_outbound_forwards_media_url
test_whatsapp_executor_forwards_media_url_to_twilio     # may already exist e3 — assert still
test_sales_send_brochure_includes_media_when_configured  # if B.1 done
```

**Mandatory regression after D.4:**

```text
python -m pytest tests/test_e17_wave_d.py tests/test_e12_bus_wiring.py tests/test_e5_whatsapp_agent.py tests/test_e3_executors.py -v
python -m pytest tests/ -q
```

#### 4.4.11 Done criteria

- [ ] Empty media env → behavior identical to today (plain text, no AE on default path)
- [ ] Configured HTTPS PDF URL → user receives WhatsApp **document** (MediaUrl), not link-only
- [ ] No double delivery (e12 green)
- [ ] TEST_MODE still short-circuits send without Twilio
- [ ] AGENTS.md + changelog D.4 `[x]`
- [ ] Evidence pack notes Approach B brochure

- **Rollback:** clear `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` → instant text fallback.
- **Status:** `[ ]`

### 4.5 Task D.5 — Evidence + G3

- Fill `IREIOS_3.0_EVIDENCE_PACK.md` Wave A–D section (include brochure Approach B smoke)
- Run `task3_runner.py` when Gemini quota allows (non-blocking if quota)
- Progress report update optional
- **Status:** `[ ]`

### 4.6 Wave D tests

| Suite | File |
|-------|------|
| Wave D | `tests/test_e17_wave_d.py` |

### 4.7 Wave D exit gate / G3

- [ ] Prediction routes return 200 + stable schema
- [ ] Memory auto-write tested
- [ ] n8n docs reflect live workflows
- [ ] **D.4 Approach B:** media send path + text fallback + e12 green
- [ ] Full pytest, isolation, DLQ
- [ ] UNIFIED step 23 + G3 `[x]`
- [ ] FRONTEND_BACKLOG updated with prediction URLs + optional chat `media_url`

---

## 5. Implementation order calendar (suggested)

| Days | Focus |
|------|--------|
| 1 | A.0 HubSpot + Calendar creds smoke; A.1 weekly cron |
| 2 | A.2 lifecycle producers; A.3 AE template branch; A.4 expire approvals |
| 3 | A.5 notifications; A exit gate |
| 4–5 | B.1 Sales bus + B.2 objections |
| 5–6 | B.3 CS WhatsApp; B.4 Marketing; B.5 templates + n8n #1 |
| 7 | B exit; start C.1 negotiation + C.2 pricing + seed |
| 8 | C.3 inventory + C.4 onboarding |
| 9 | C.5 finance + C.6 legal + C.7 cleanup |
| 10 | D.1–D.3 + **D.4 Approach B brochure** + D.5 G3 |

---

## 6. Explicit non-goals (Waves A–D)

| Non-goal | Reason |
|----------|--------|
| Meta / Google Ads APIs | No code surface; major product |
| FE MockSSE / Digital Twin live data | Mayank; deferred |
| Delete monolith `agent.py` / dual-path | 10.2/10.3 still deferred |
| Full autonomous discounting without HITL | Legal/commercial risk |
| Web-scale competitor crawl | Keyword MVP enough |
| LangGraph as default for all actions | Linear AE sufficient |
| Production ML forecast accuracy | Heuristics only |

---

## 7. Risk register

| Risk | Mitigation |
|------|------------|
| HubSpot custom prop 4xx | Start extended=false; P5.2 already strips unknown props |
| Calendar SA cannot write | Share calendar with SA email Make changes |
| n8n webhook auth mismatch | Align header with n8n Header Auth; test with curl first |
| Sales bus storm | Debounce Redis lock per lead |
| CS spam WhatsApp | Templates + respect opt-in; rate limit per lead/day |
| Double brochure send | W1: media only via AE **or** only via TwiML Media — never both (e12 guard) |
| Twilio cannot fetch media URL | Public HTTPS only; smoke with curl GET before WA test; no localhost without tunnel |
| Oversized PDF | Compress brochure; stay within Twilio WhatsApp media limits |
| Placeholder “real” but empty | Exit gate requires AE or publish side effect in tests |

---

## 8. Quick code reference index

| Concern | Path |
|---------|------|
| Event bus | `app/clients/event_bus_client.py` |
| CEO | `app/orchestrator/ceo_orchestrator.py` |
| AE submit | `app/automation_engine/engine.py` |
| n8n | `app/automation_engine/n8n_client.py` |
| LangGraph | `app/automation_engine/langgraph_runner.py` |
| EE registry | `app/execution_engine/registry.py` |
| WhatsApp tools + Approach B media | `app/agents/whatsapp_agent.py` (`detect_tool_intent`, `generate_*`, `resolve_tool_media_url` TBD, `_dispatch_outbound`) |
| WA MediaUrl send | `app/execution_engine/whatsapp_executor.py` (`media_url` → Twilio) |
| WA TwiML response | `main.py` WhatsApp webhook (`MessagingResponse`) |
| Sales | `app/agents/sales_agent.py` |
| Marketing | `app/agents/marketing_agent.py` |
| CS | `app/agents/customer_success_agent.py` |
| Placeholders | `app/agents/placeholders.py` |
| CRM push | `crm_sync.py` |
| Calendar | `app/execution_engine/calendar_executor.py` |
| Notifications | `app/execution_engine/notification_executor.py`, `notification_service.py` |
| Scheduler | `main.py` lifespan ~348–355 |
| Prediction | `app/services/prediction_service.py` |

---

## 9. Per-task documentation checklist (copy into PR description)

```markdown
## Task ID: _
- [ ] Code complete
- [ ] tests/test_e1N_*.py updated (not skeleton skip)
- [ ] python -m pytest tests/test_e1N_*.py -v
- [ ] python -m pytest tests/ -q
- [ ] gate_isolation_test.py (if tenant/bus)
- [ ] WAVE_A_D_CHANGELOG entry
- [ ] AGENTS.md / README / N8N / FRONTEND_BACKLOG as needed
- [ ] No secrets committed
```

---

**End of Wave A–D expansion plan.**  
Implement starting at **Task A.0 + A.1**. Do not mark G3 until Wave D exit gate passes.
