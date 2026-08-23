# IREIOS 4.0 — Expansion changelog (living)

| This doc owns | Does not own |
|---|---|
| What shipped in Product Phase 4 + test evidence | Task specs → `IREIOS_4.0_STEP_BY_STEP.md` |

**Test naming:** `tests/test_f4_*.py`

---

## Status table

| ID | Status | Summary | Tests |
|---|---|---|---|
| P4-0 | `[x]` | Baseline + sprint re-baseline | doc |
| P4-1 | `[x]` | Contract freeze + Day-1 mocks + sales-ai preview | `test_f4_sales_ai*` |
| P4-2 | `[x]` | Graph neighborhood API | `test_f4_graph*` |
| P4-3 | `[x]` | Twin API + 40-unit seed | `test_f4_twin*` |
| P4-4 | `[x]` | HubSpot outbound flag (live key pending) | `test_f4_hubspot*` |
| P4-5 | `[x]` | FE Sales AI preview/confirm | lint + manual |
| P4-6 | `[x]` | FE Forecast ₹ Cr | lint + manual |
| P4-7 | `[x]` | FE Graph ego embed | lint + manual |
| P4-8 | `[x]` | FE Twin live | lint + manual |
| P4-9 | `[x]` | FE JWT/SSE/middleware | grep + lint |
| P4-10 | `[-]` | No new n8n WFs | n/a |
| G5 | `[x]` | MVP gate 2026-08-10 | 426 pytest; isolation; DLQ; task3 skip |
| Plans lock | `[x]` | Lead answers folded into all phase4 docs | n/a |

---

## Entries

### 2026-08-14 — Docs sync to HEAD `127920e` + 441/4 baseline verified

- Re-ran full suite on running stack: **441 passed / 4 skipped** (final CC UX baseline).
- Handoff (`HANDOFF_MAYANK_PIYUSH.md`) HEAD `8f5c38b` → **`127920e`**; pytest row 426 → **441/4**; added CC UX batch row (§0).
- `docs/PROD_READINESS_CHECKLIST.md` HEAD → `127920e`.
- `docs/COMMAND_CENTER_VERIFY.md` suite count 439 → **441/4**; twin hover row updated to shipped `distanceFactor={4}` + transform/sprite.
- `IREIOS_4.0_EVIDENCE_PACK.md` pre-freeze baseline: 426/439 → **441/4** + new CC UX batch checkbox.
- `IREIOS_4.0_STEP_BY_STEP.md` QA.1.2 baseline → **441/4**.
- `COMMAND_CENTER_UI_FIXES_PLAN.md` Issue 1 fix description corrected to shipped drei `Html` approach (was stale cursor-follow text).
- `IREIOS_4.0_API_CONTRACTS.md` sales-ai execute response documented (additive per freeze rules): `actions_executed`, `stage_before`, `scores_before`, `scores_unchanged`, `test_mode`, `note` + `deal_closed` enum entry.
- OpenAPI snapshot re-verified from running app — no route drift (only unicode-escape noise); file unchanged.

### 2026-08-13 — Terminal NBA gate + twin Html portal

- `recommend_next_action`: Closed Won/Lost/Lost → `deal_closed` (no brochure/visit AE).
- `_nba_to_ae_action` skips terminal/no-op NBA.
- Twin Html: `transform={false}` + `portal=document.body` + larger px (readable far camera).
- Timeline hot events: orange (not error-red); aria-label clarifies informational.
- Tests: `test_recommend_terminal_closed_won_no_outbound`.

### 2026-08-13 — Score floors + twin screen-stable labels

- `score_lead`: chat-aligned floors (full qualify ≥88, visit ≥82); **monotonic**
  vs stored conversion when lead stays complete (fixes 95→80 Confirm shock).
- Twin Html: drop `distanceFactor` + fixed px typography (readable without zoom).
- Modal copy: chat-aligned rescore / no drop note.
- Tests: `test_score_lead_visit_floor_and_no_drop`.

### 2026-08-13 — Sales AI UX clarity + brochure debounce + twin label size

- Twin Html: larger card (later superseded by screen-stable Html).
- Preview shows stored DB % vs recomputed; execute shows **Stored was X% → now Y%**.
- `send_brochure` 10 min Redis debounce; TEST_MODE banner + action note (no real Twilio).
- Docs: COMMAND_CENTER_VERIFY Sales AI section updated.

### 2026-08-13 — CC polish v2: drei Html twin tip + force-graph camera freeze

- Twin: **pmndrs/drei `Html`** child of unit mesh (`center`, `distanceFactor`) — standard projected HTML; removed broken DOM pointer math.
- GraphWrapper: no `centerAt`/`zoom` on click (vasturiano click-to-focus is optional — breaks small panels); one `zoomToFit` per fingerprint; `minZoom`/`maxZoom`; ResizeObserver size; stable graphData copies.
- Prior: sales stage policy + modal UX (see below).

### 2026-08-13 — CC polish: twin tooltip, graph fit, sales stage policy

- Twin: R3F `clientX/Y` + container-relative absolute tooltip (superseded by Html).
- GraphWrapper: ResizeObserver width/height (superseded by camera freeze).
- `progress_deal_stage(lead, recommendation)`: no blind funnel +1; only New→Contacted on assign or Site Visit Booked when visit/NBA warrants.
- Sales modal: before/after stage, scores_unchanged note, clearer preview/execute copy.
- Tests: e6 progress_deal_stage expectations updated.

### 2026-08-13 — Command Center UI/UX batch (twin/graph/sales/timeline)

- Twin hover tooltip follows cursor (not fixed under Live twin badge).
- Graph: `_lead_node` adds phone/location/stage/type; FE rich tooltip + styled detail card.
- Sales AI HTTP execute calls `_nba_to_ae_action`, returns `actions_executed`; modal shows results; lead dropdown + timeline/graph refresh after confirm.
- EventLog: sales execute (scored/hot/assign/stage/nba); agent handoff, hot threshold, negotiation started.
- Timeline filters/icons expanded; dropdown shows temp/stage for sync.
- Seed via existing `seed_dummy_leads.py` (Neo4j) + `seed_twin_demo.py` only.
- Tests: f4 jwt/twin/graph/sales + e19 green; full suite **439 passed / 4 skipped** (no regression). FE lint exit 0.
- Docs: `COMMAND_CENTER_VERIFY.md` UI/sync section; `COMMAND_CENTER_UI_FIXES_PLAN.md` marked implemented.

### 2026-08-13 — Command Center JWT auth unify (twin/graph/predictions) + verify doc

- **Bug (confirmed live):** `/digital-twin` 401 (browser fetch + cookie vs `get_current_client` Bearer-only) and `/knowledge-graph`/copilot ego auth-empty (server action Bearer vs `get_events_client` cookie/api-key-only). `dashboard-mvp` predictions shared the twin 401 risk.
- **Fix (BE-only, no FE change):** `auth.py` now ships shared `_client_from_jwt_token` + `resolve_jwt_from_request`; `get_current_client` accepts `Authorization: Bearer` **or** HttpOnly `jwt` cookie (`OAuth2PasswordBearer(auto_error=False)`; missing/invalid still 401). `get_events_client` (`app/api/events.py`) order: API key → Bearer → cookie → 401. `app/api/predictions.py` fixed latent `client["id"]` → `client.id` (would 500 after auth pass).
- **Files:** `auth.py`, `app/api/events.py`, `app/api/predictions.py`, `tests/test_f4_jwt_auth.py` (new, 13 tests).
- **Tests:** f4 suite 35 passed; full suite **439 passed / 4 skipped** (services up) — baseline was 426/4 (+13 auth tests).
- **Manual:** twin Bearer/cookie 200 (40 units), no-auth 401; neighborhood Bearer/cookie/api-key 200 (5 nodes/4 edges on lead 23), no-auth 401; predictions cookie/bearer 200; sales-ai preview success; graph health available.
- **Docs:** NEW `docs/COMMAND_CENTER_VERIFY.md` (CC smoke single source — auth model, route map, manual checklist, failure matrix, Sales AI behavior); pointers added in `docs/FRONTEND_BACKLOG.md`, `docs/PROD_READINESS_CHECKLIST.md`, `AGENTS.md`, `IREIOS_4.0_API_CONTRACTS.md`, this changelog, Evidence Pack, HANDOFF doc.
- **Rollback:** revert `auth.py` + `app/api/events.py` (+ predictions.py) only.

### 2026-08-13 — Final audit + Mayank/Piyush handoff

- **Code audit:** no blocking 4.0 code debt. Flags/timings match prod defaults (`FEATURE_*`, `FOLLOWUP_ENGINE=v3`, WA 13s / LLM 22s). Twin/graph/Sales AI FE present.
- **Twin UX note:** live page is command-center **`/digital-twin`** (not product dashboard nav). Empty = missing seed/tenant inventory — re-seed `seed_twin_demo.py --client-id 1 --clear`.
- **n8n:** bridge code + WF JSON shipped; unit 14/14. Live Publish is **docker volume state** — wipe → 0 published WFs / webhook 404. Owner = **Mayank** (compose deploy host), not cloud-n8n. Prior Gmail success does not survive volume reset.
- **Evidence Pack:** pre-freeze baseline checkboxes `[x]` (pytest/isolation/DLQ/WA smoke/FE quality); freeze ceremony QA.1.1–1.6 still `[ ]`.
- **Handoff:** `plans/phase4/HANDOFF_MAYANK_PIYUSH.md` (Mayank freeze/RC1/REL + n8n Publish; Piyush Twilio required / HubSpot optional).
- **No commit required for release engineering** beyond this docs batch when lead chooses.

### 2026-08-11 — Docs verification + P4-QA / P4-REL planning

- **FE quality gate green end-to-end:** `npm run lint` exit 0 (23e/17w baseline cleared), `tsc --noEmit` clean (command-center fixes), `npm run build` exit 0 (incl. knowledge-graph Suspense prerender) — committed `4494307`. Root cause of prior build failure: corrupt `node_modules` (missing `.cmd` shims + `lightningcss-win32-x64-msvc` optional binary) → clean `npm ci` reinstall; `frontend/.env.local` (gitignored) supplies `NEXT_PUBLIC_API_URL` build guard.
- **Regression:** full pytest re-run **426 passed / 4 skipped** (2026-08-11, services up).
- **Docs verification pass:** stale lint/tsc references updated across `FRONTEND_BACKLOG.md`, `MAINTENANCE.md` §11.1, `IREIOS_4.0_EVIDENCE_PACK.md`, `IREIOS_4.0_STEP_BY_STEP.md` (G5 status), `AGENTS.md` (backlog line + go-live pointer), `IREIOS_Phase_4_Master_Sprint_Plan.md`.
- **NEW `docs/PROD_READINESS_CHECKLIST.md`:** single source for prod readiness — env surface map (var → consumer → fallback), go-live flag matrix, secrets track (owners), infra + implementation process (RC1 staging fallback §5.1, hosted read-replica adoption §5.2, prod topology §5.3), integration adoption runbooks (§6), monitoring (§7), release/rollback (§8), additive-only change process (§9).
- **P4-QA plan (freeze 2026-08-20):** STEP_BY_STEP QA.1.1–QA.1.6 — freeze mechanics + RC1 `ireios4-rc1`; full regression re-run; **`task3_runner` waived at QA (Gemini quota, Mayank ack — consistent with G5)**; FE gate; RC1 on local `pg-staging` snapshot (hosted read-replica adopted when ops delivers, tracked 4.1 otherwise); readiness checklist execution; sign-off.
- **P4-REL plan (2026-09-03):** STEP_BY_STEP REL.1.1–REL.1.5 — flags flip, runbook approval + deploy, post-release verification, telemetry/incident/rollback, evidence.
- **Note (read-replica reality):** `database.py` has a single engine with no read/write routing — a literal read-only replica would break app writes. "RC1 on read-replica" is implemented as staging primary seeded from a prod snapshot; true write-routing is deferred to IREIOS 4.1.

### 2026-08-11 — G5 follow-ups (pre-QA)

- **WA → SSE live smoke:** `wa_sse_smoke.py` added (stdlib, repo root). Live local run PASS in
  both modes — turn 4.9–11.3s (13s window), SSE publish→delivery 10–2183ms; events
  `whatsapp.received` → `conversation.updated` → `lead.crm_synced` → `lead.scored` (+
  `lead.created` with `--new-lead`). Evidence Pack Q12 WA→SSE → `[x]`.
- **Bus resilience note:** a Redis blip can kill the `EventBusClient._consume_loop`
  (`_running=False`, SSE 503s) — restart uvicorn to recover; documented in MAINTENANCE §5.
- **n8n bridge:** `tests/test_e20_n8n_bridge.py` **14/14 green** (2026-08-11); live delivery
  still pending n8n UI WF activation (`ireios-n8n` group PEL growing — Maitri ops).
- **FE lint runbook:** full fix recipe (23e/17w baseline, per-file steps, shim gotcha)
  documented in `docs/MAINTENANCE.md` §11.1 — pre-freeze triage batch.

### 2026-08-10 — G5 MVP gate

- **Evidence:** `pytest` f4 22 passed; full suite 426 passed / 4 skipped; `gate_isolation_test.py` PASS; `gate_dlq_drill.py` PASS; `task3_runner` skipped (Mayank); `/health` healthy.
- **FE lint:** repo-wide residual errors pre-existing — not G5 blocker; freeze triage.
- **HubSpot live:** deferred note (PAT pending); flag path green.
- **UNIFIED G5:** `[x]`

### 2026-08-10 — FE Wave (P4-5…P4-9)

- **Files:** `frontend/next.config.ts` (rewrite `/api/v1/*`), `proxy.ts` (guard CC routes), `sales-copilot/*`, `SalesAiModal.tsx`, `LeadsTable.tsx`, `dashboard-mvp`, `dashboard/page.tsx`, `digital-twin`, `knowledge-graph`, `lib/format.ts`, `lib/api.ts` predictions helpers
- **Behavior:**
  - Same-origin proxy so EventSource/fetch send HttpOnly `jwt` (zero `secret-client-key-123` in `frontend/src`)
  - Sales AI preview then Confirm execute on copilot + Leads table
  - Forecasts from live `/predictions/*` with ₹ Cr + heuristic disclaimer
  - Ego neighborhood embed + SSE refetch; KG page lead selector
  - Twin live API, 30s poll, read-only; seed `seed_twin_demo.py`
- **Tests:** Backend suite still **426 passed, 4 skipped**. FE touched files eslint clean. Full `npm run lint` still has pre-existing errors outside this wave.
- **HubSpot PAT:** Backend already `Authorization: Bearer {CRM_API_KEY}`; contacts scopes sufficient; live flip remains ops when token arrives.

### 2026-08-10 — Backend Wave 1 (P4-0…P4-4)

- **Files:** `app/agents/sales_agent.py` (preview|execute + `SalesAiBody`), `main.py` sales-ai body, `app/knowledge_graph/graph_api.py` (`GET /neighborhood`), `app/api/inventory.py` (`GET /twin`), `seed_twin_demo.py`, `config.py` + `.env.example` (`FEATURE_GRAPH_VIZ`/`FEATURE_TWIN_LIVE`/`FEATURE_HUBSPOT_LIVE`), `crm_sync.py` hubspot live gate, FE Day-1 mocks (`mockGraphService.ts` ego, `mockTwinService.ts` 40u), `tests/test_f4_*.py`
- **Behavior:**
  - HTTP sales-ai defaults to `mode=preview` (no DB/CRM writes); `execute` keeps Phase 6 pipeline. Bus path unchanged (execute).
  - Neighborhood ego graph soft-empty when Neo4j down or flag off; tenant 404.
  - Twin groups `InventoryUnit` via `meta_json.floor`; seed 1×2×10×40 The Summit.
  - HubSpot live only when `FEATURE_HUBSPOT_LIVE=true` + non-demo key; else stub.
- **Tests:** Full suite with docker+uvicorn up: **`426 passed, 4 skipped`** (2026-08-10). f4_* + e3 green. Fixed stale path in `test_e20_n8n_bridge` → `plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md` (post-archive).
- **OpenAPI:** `plans/phase4/openapi_ireios4.json` regenerated from live app (neighborhood, twin, sales-ai present).
- **Follow-up (same day):** FE P4-5…P4-9 + **G5** also shipped; live HubSpot portal key still pending (flag ready).

### 2026-08-07 — Lead questionnaire locked → plans filled

- **Files:** All `plans/phase4/*` implementation docs; `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` (source)
- **Behavior:** No runtime code. Decisions locked: integrate-only; heuristic forecasts INR Cr; Sales AI preview+confirm on copilot→leads; ego graph embed; live twin 40 units read-only; HubSpot outbound; no new n8n; freeze 2026-08-20; release 2026-09-03; Mayank tech lead.
- **Tests:** n/a
- **Follow-up questionnaire:** **Not required** — remaining gaps are ops secrets (Q11 N/A → Piyush) and engineering design choices documented in Implementation Plan §5.

### 2026-08-07 — Plans folder restructure + Phase 4 skeletons

- **Files:** `plans/phase3/*`, `plans/phase4/*` initial skeletons
- **Behavior:** Archive 3.0; create 4.0 queue
- **Tests:** n/a
