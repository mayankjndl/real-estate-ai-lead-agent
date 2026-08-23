# IREIOS 4.0 — Step-by-step tasks (implementation-ready)

| This doc owns | Does not own |
|---|---|
| Atomic tasks: Files / Steps / Test / Done / Rollback | Order → `UNIFIED_EXECUTION_ORDER.md` |
| | Locked decisions → `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` |

**Status legend:** `[ ]` · `[~]` · `[x]` · `[-]`  
**Test prefix:** `tests/test_f4_*.py`  
**Contracts:** `IREIOS_4.0_API_CONTRACTS.md` (FROZEN)

---

## P4-0 — Baseline & sprint re-baseline

### Task P4-0.1 — Apply lead §F amendments to sprint brief
- **Files:** `IREIOS_Phase_4_Master_Sprint_Plan.md`
- **Steps:**
  1. §6 progress → Backend ~75% / FE ~15% / HubSpot-ops ~10%.
  2. Rewrite DoD rows: Forecast = heuristic MVP; Sales AI = Python CEO→AE→EE; Marketing routing = Python; HubSpot = outbound complete (not bi-di).
  3. Dependency matrix → UI wiring / neighborhood contract / portal credentials (not greenfield APIs).
  4. Name product **IREIOS 4.0** in header.
- **Test:** N/A
- **Done:** Sprint doc matches answered questionnaire; no “0%” / “models trained” / “LangGraph-in-n8n” as active DoD
- **Rollback:** git revert doc only
- **Status:** `[x]`

### Task P4-0.2 — Evidence baseline sign-off
- **Files:** `IREIOS_4.0_EVIDENCE_PACK.md`
- **Steps:** Check all “already shipped” baseline boxes; note G4 n8n WF-1 ops-pending as non-blocking.
- **Done:** Baseline section complete
- **Status:** `[x]`

---

## P4-1 — Contract freeze & mocks

### Task P4-1.1 — Publish Day-1 FE mocks matching frozen contracts
- **Files:** `frontend/src/lib/api/mockGraphService.ts` (align ego shape), optional `mockTwinService.ts` seed shape, `IREIOS_4.0_API_CONTRACTS.md` (already frozen)
- **Steps:**
  1. Adjust mock graph generator to **ego** shape (center lead + agent + similars) matching §2 contract — not full Project/Tower/Comm storm as sole mock.
  2. Align twin mock to 1 project / 2 towers / 10 floors / 40 units.
  3. Document sales-ai preview response fixture for FE.
- **Test:** FE builds against mocks without live API
- **Done:** Mayank unblocked parallel to BE
- **Status:** `[x]` ego + twin mocks aligned 2026-08-10

### Task P4-1.2 — Capture live OpenAPI baseline
- **Files:** `openapi_ireios4.json`
- **Steps:** Dump `/openapi.json` from running app (pre-change); after P4-2/3 re-dump.
- **Status:** `[x]` regenerated 2026-08-10 from live `/openapi.json`

---

## P4-2 — Graph neighborhood API

### Task P4-2.1 — Implement `GET /api/v1/graph/neighborhood`
- **Files:**
  - Edit: `app/knowledge_graph/graph_api.py`
  - Edit: `app/knowledge_graph/neo4j_kg.py` and/or `app/clients/graph_client.py` (read helpers)
  - Create: `tests/test_f4_graph_neighborhood.py`
  - Optional: `config.py` / `.env.example` → `FEATURE_GRAPH_VIZ`
- **Steps:**
  1. JWT via existing graph/events auth (`get_events_client` or `get_current_client`).
  2. Require `lead_id`; 404 if `Lead.client_id` mismatch.
  3. Build nodes: center lead (hydrate name/score/temp from PG), assigned agent, similar leads from existing graph context helpers.
  4. Edges: `ASSIGNED_TO`, `SIMILAR_TO` (+ strength if available).
  5. Node ids stable: `lead:{id}`, `agent:{name}`.
  6. Colors per contract; `ai_summary` static string.
  7. Neo4j down → `available: false`, empty arrays, HTTP 200.
  8. Honor `FEATURE_GRAPH_VIZ=false` → same as unavailable.
  9. Soft latency: no hard fail; log if &gt;200ms.
- **Test:**
  ```bash
  pytest tests/test_f4_graph_neighborhood.py -v
  python gate_isolation_test.py
  ```
- **Done:** Contract §2 satisfied; tenant 404 proven
- **Rollback:** Remove route; flag false
- **Status:** `[x]` 2026-08-10

### Task P4-2.2 — Stretch Unit nodes (optional, cut if freeze risk)
- **Files:** same + PG `InventoryUnit` query by location
- **Status:** `[-]` deferred (not required for G5)

---

## P4-3 — Twin inventory API + seed

### Task P4-3.1 — Floor field + twin endpoint
- **Files:**
  - Edit: `models.py` (`InventoryUnit` — add `floor = Column(Integer, nullable=True)` **or** use `meta_json["floor"]` only)
  - Create: `app/api/inventory.py` (or extend predictions router — prefer dedicated `inventory` router)
  - Edit: `main.py` mount router
  - Edit: `migrate_db.py` / migration path used by project
  - Create: `tests/test_f4_twin.py`
  - Edit: `config.py` → `FEATURE_TWIN_LIVE`
- **Steps:**
  1. Prefer `floor` column if migrate is cheap; else `meta_json.floor`.
  2. `GET /api/v1/inventory/twin` JWT client-scoped.
  3. Group rows: single project (first `project_name` or fixed demo name) → tower → floor level → units.
  4. Map status to lowercase `available|hold|sold`.
  5. `counts` aggregate; `price` = `list_price`; `currency` = `INR`.
  6. Empty inventory → empty towers + zeros zeros.
  7. Flag off → empty + `available`-style message or 200 empty.
- **Test:** `pytest tests/test_f4_twin.py -v`
- **Done:** Contract §3 JSON shape
- **Rollback:** Unmount router; flag false
- **Status:** `[x]` 2026-08-10 (`meta_json.floor`)

### Task P4-3.2 — Seed demo twin inventory
- **Files:** Edit `seed_inventory.py` or create `seed_twin_demo.py`
- **Steps:**
  1. For client_id=1 (seed client): 1 project **The Summit**, towers **Tower A/B**, floors 1–10, 2 units/floor = 40.
  2. unit_code pattern `A-101`, `A-102`, … status mix ~50/25/25 available/hold/sold.
  3. list_price in INR absolute (e.g. 1.2e7–2.5e7).
  4. Idempotent re-run (delete client inventory first or upsert by unit_code).
- **Test:** run seed → GET twin returns 40 units
- **Done:** Demo tenant ready for FE
- **Status:** `[x]` `seed_twin_demo.py`

---

## P4-4 — HubSpot outbound go-live

### Task P4-4.1 — Feature flag + credential wiring
- **Files:** `config.py`, `.env.example`, `crm_sync.py` (only if needed for email+phone identity notes), `AGENTS.md`
- **Steps:**
  1. Add `FEATURE_HUBSPOT_LIVE` default false.
  2. When false: existing demo stub behavior.
  3. When true + real `CRM_API_URL`/`CRM_API_KEY`: real push.
  4. Document identity match email+phone for portal property setup (ops/Piyush).
  5. No inbound webhook.
- **Test:** `gate_dlq_drill.py` with stub; live sandbox when key arrives
- **Done:** Flag documented; live path verified **or** UNIFIED note Sheets fallback until key
- **Status:** `[x]` flag + stub gate shipped 2026-08-10
- **Blocked externally:** HubSpot key from Piyush (Q11) — do not block G5 FE

### Task P4-4.2 — Maitri ops smoke (if live)
- **Files:** none code; DLQ replay runbook
- **Steps:** One real contact upsert; DLQ replay green
- **Status:** `[-]` key not delivered — Sheets/demo stub until portal

---

## P4-5 — FE Sales AI (Preview + Confirm)

### Task P4-5.1 — API helper + sales-copilot UI
- **Files:**
  - `frontend/src/app/(command-center)/sales-copilot/page.tsx`
  - Optional helper `frontend/src/lib/api/salesAi.ts`
- **Steps:**
  1. Lead selector (not hard-coded id `1`).
  2. Button **Get recommendation** → `POST .../sales-ai` `{mode:"preview"}` with JWT.
  3. Render: `recommendation.action`, `rationale`, `scores`, `funnel_stage`, `assigned_agent`.
  4. Button **Confirm & apply** → `{mode:"execute"}`; loading + error boundary; disable double-submit.
  5. Refresh timeline after execute.
  6. No “Generate Email Draft” (out of scope).
- **Test:** `cd frontend && npm run lint`; manual with seeded lead
- **Done:** Q12 Sales AI demo path works on copilot
- **Status:** `[x]` 2026-08-10

### Task P4-5.2 — Leads table button (second priority)
- **Files:** `frontend/src/app/(dashboard)/leads/LeadsTable.tsx` (+ modal/drawer for preview/confirm)
- **Steps:** Same preview/confirm pattern; compact UI
- **Done:** Second surface live
- **Status:** `[x]`
- **Note:** CRM Kanban **not** required (Q3.2 override vs older DoD draft)

---

## P4-6 — FE Forecast widgets

### Task P4-6.1 — dashboard-mvp live predictions
- **Files:** `frontend/src/app/(command-center)/dashboard-mvp/page.tsx`, `frontend/src/lib/api/mockService.ts`
- **Steps:**
  1. Fetch revenue, cashflow, inventory, cancellation-risk with JWT.
  2. Format money as **₹ X.XX Cr** (`value / 1e7`).
  3. Show disclaimer badge: “Heuristic estimate (not a trained model)”.
  4. Stop using `mockForecastData` as sole source; remove demo `+150000` KPI math where replaced.
- **Test:** lint + network tab
- **Done:** FRONTEND_BACKLOG forecast item
- **Status:** `[x]`

### Task P4-6.2 — Product dashboard forecast strip
- **Files:** `frontend/src/app/(dashboard)/dashboard/page.tsx`, `Charts.tsx` as needed
- **Steps:** Add compact forecast cards from same endpoints (home is `/dashboard`)
- **Status:** `[x]`

---

## P4-7 — FE Graph embed

### Task P4-5 depends P4-2 for live data; mocks OK until then

### Task P4-7.1 — Ego graph on Sales Copilot
- **Files:** reuse `GraphWrapper.tsx` or extract shared component; `sales-copilot/page.tsx`
- **Steps:**
  1. Fetch `/api/v1/graph/neighborhood?lead_id=` for selected lead.
  2. Handle `available:false` empty state.
  3. On SSE events `lead.scored|lead.assigned|lead.hot` for that lead → refetch.
  4. Desktop-first layout.
- **Test:** lint; manual with Neo4j up/down
- **Done:** Q12 graph demo
- **Status:** `[x]`

### Task P4-7.2 — knowledge-graph page optional
- **Files:** `knowledge-graph/page.tsx`
- **Steps:** Lead id query param or selector; same API; or link “open in copilot”
- **Status:** `[x]`

---

## P4-8 — FE Digital Twin

### Task P4-8.1 — Wire R3F to twin API
- **Files:** `frontend/src/app/(command-center)/digital-twin/page.tsx`, `mockTwinService.ts`
- **Steps:**
  1. Fetch `/api/v1/inventory/twin` JWT.
  2. Map towers/floors/units to existing R3F scene.
  3. Status colors available/hold/sold; read-only (no hold writes).
  4. Poll every **30s**.
  5. Empty state if no inventory / flag off.
  6. Cap client render at 500 units.
- **Test:** lint; seeded 40 units visible
- **Done:** Q12 twin demo
- **Status:** `[x]`

---

## P4-9 — FE SSE / JWT / routing harden

### Task P4-9.1 — Remove hard-coded api_key
- **Files:** all FE `EventSource` / fetch callers (`dashboard-mvp`, `sales-copilot`, …)
- **Steps:** Cookie credentials / same-origin proxy; grep must find **zero** `secret-client-key-123` under `frontend/src`
- **Done:** Q7.5
- **Status:** `[x]` rewrite + purge

### Task P4-9.2 — MockSSE quarantine
- **Files:** `frontend/src/lib/api/mockService.ts`
- **Steps:** Delete class or move to dev-only path; no prod imports
- **Status:** `[x]` no MockSSE; mock chart series only

### Task P4-9.3 — Middleware guard command-center
- **Files:** `frontend/src/proxy.ts` (Next middleware)
- **Steps:** Protect `/dashboard-mvp`, `/sales-copilot`, `/knowledge-graph`, `/digital-twin`, `/ai-chat` like `/dashboard/*`; redirect `/login`
- **Status:** `[x]`

### Task P4-9.4 — Post-login home `/dashboard`
- **Files:** login redirect / middleware default
- **Steps:** Ensure successful login lands on `/dashboard` not mvp
- **Status:** `[x]`

### Task P4-9.5 — Timeline selected lead only
- **Files:** `sales-copilot/page.tsx`
- **Steps:** Bind timeline to selected lead id; 404 handling
- **Status:** `[x]`

---

## P4-10 — Ops / n8n

### Task P4-10.1 — No new workflows
- **Steps:** Confirm Q4.2 None; do not add WF-7+. Optional smoke existing bridge if env ready.
- **Status:** `[-]` no-op default

---

## G5 — MVP gate

### Task G5.1 — Full gate
- **Steps:**
  1. `pytest tests/test_f4_*.py -v` and `pytest tests/ -q` (or agreed matrix)
  2. `python gate_isolation_test.py`
  3. `python gate_dlq_drill.py` (+ replay if HubSpot live)
  4. `python task3_runner.py` (Q9.2) — or document quota skip with Mayank ack
  5. `cd frontend && npm run lint`
  6. Q12 demos on local/staging
  7. Evidence Pack G5 all checked
  8. Zero High/Critical on GitHub Issues
- **Done:** UNIFIED G5 → `[x]`
- **Status:** `[x]` 2026-08-10 — 22 f4 + 426 full pytest; isolation PASS; DLQ drill PASS; task3_runner skipped (Mayank); FE lint repo-wide exit 0 + `tsc` clean + `npm run build` exit 0 (2026-08-11, `4494307`)

---

## P4-QA — Hard freeze (2026-08-20)

**Exit gate:** `docs/PROD_READINESS_CHECKLIST.md` executed → UNIFIED P4-QA `[x]`. **Owner:** Mayank

### Task QA.1.1 — Freeze mechanics
- Zero new features after freeze; bugfix-only, serial, logged in changelog
- Tag RC1: `ireios4-rc1` on `main` at freeze; freeze-period fixes noted in evidence
- **Status:** `[ ]`

### Task QA.1.2 — Full regression re-run (at freeze)
- **Pre-freeze baseline already green** (2026-08-10/11 + CC UX batch `127920e` 2026-08-14) — see Evidence Pack § QA pre-freeze. This task = **re-confirm on freeze day / RC1**, not first-time execution.
- `pytest tests/ -q` — expect ≥ baseline **441 passed / 4 skipped**
- `python gate_isolation_test.py`
- `python gate_dlq_drill.py` + `python dlq_replay.py`
- `python wa_sse_smoke.py` both modes (`TEST_MODE=true` for smoke)
- `python -m pytest tests/test_e20_n8n_bridge.py -q` — 14/14 unit; live Gmail path optional (Mayank re-publishes docker n8n WFs after volume wipe)
- **`task3_runner.py` waived** — Gemini quota (Mayank ack)
- **Status:** `[ ]` ceremony open · baseline `[x]`

### Task QA.1.3 — FE gate
- lint/tsc/build **already exit 0** (`4494307`) — re-confirm at freeze
- Manual browser E2E on staging: product `/dashboard` + `/leads` + `/crm`; command-center `/sales-copilot`, `/knowledge-graph`, **`/digital-twin`** (seed: `python seed_twin_demo.py --client-id 1 --clear`)
- **Status:** `[ ]` ceremony open · lint/build baseline `[x]`

### Task QA.1.4 — RC1 against staging
- Per `docs/PROD_READINESS_CHECKLIST.md` §5.1: RC1 = tagged build + full-stack docker + separate `pg-staging` seeded from prod snapshot (`db_backup.py` → `db_restore.py`)
- Hosted `staging-api.ireios` read-replica adopted if ops delivers pre-freeze (§5.2); else tracked as 4.1 ops item; evidence records env + snapshot date
- **Status:** `[ ]`

### Task QA.1.5 — Prod readiness checklist
- Execute `docs/PROD_READINESS_CHECKLIST.md` (§3 flags, §4 secrets track, §5 infra, §6 integrations)
- Zero High/Critical GitHub Issues
- Runbook draft (deploy sequence, backup/restore drill, webhook switch, rollback — checklist §5.3/§8)
- **Status:** `[ ]`

### Task QA.1.6 — Sign-off
- Evidence Pack § QA freeze/RC1 all `[x]`; UNIFIED P4-QA → `[x]`
- **Status:** `[ ]`

---

## P4-REL — Production (2026-09-03)

**Exit gate:** runbook approved (Mayank) → UNIFIED P4-REL `[x]`. **Owner:** Mayank

### Task REL.1.1 — Go-live flags
- Flip per `docs/PROD_READINESS_CHECKLIST.md` §3: `IS_PRODUCTION=true`, `TEST_MODE=false`, `FOLLOW_UP_TEST_MODE=false`, `FOLLOW_UP_DLQ_TEST=false`, real `TWILIO_*`
- Secrets from §4 track must be filled before flip (Piyush: Twilio required; HubSpot optional)
- **Status:** `[ ]`

### Task REL.1.2 — Runbook approval + deploy
- Mayank approves QA runbook (from QA.1.5)
- Pre-release `python db_backup.py` snapshot; `python migrate_db.py`
- Deploy on prod host; switch Twilio console webhook URL → prod; verify `X-Twilio-Signature` path (TEST_MODE off); remove ngrok
- **Status:** `[ ]`

### Task REL.1.3 — Post-release verification
- `/health` + `/metrics` (firewall-restricted) healthy
- Real-Twilio WA turn; SSE smoke (`wa_sse_smoke.py`); follow-up scheduler real timings; 10m/30m escalation; 2am backup + 3am cleanup jobs; event-bus consume loop healthy
- **Status:** `[ ]`

### Task REL.1.4 — Telemetry / incident / rollback
- `/metrics` owner: Mayank; alert thresholds per `docs/TIMEOUTS_AND_TIMINGS.md`; incident owner named
- Rollback documented (checklist §8): revert + flags off + webhook back + restore
- **Status:** `[ ]`

### Task REL.1.5 — Evidence
- Evidence Pack § Production all `[x]`; UNIFIED P4-REL → `[x]`
- **Status:** `[ ]`

---

## Suggested calendar (compressed)

| Window | Focus |
|---|---|
| Through Week 1 EOW | P4-0, P4-1, P4-2, P4-3 seed, P4-4 flag prep |
| Week 2 | P4-5…P4-9 FE + HubSpot live if key |
| 2026-08-20+ | Freeze / G5 / RC1 |
| 2026-09-03 | Prod release |
