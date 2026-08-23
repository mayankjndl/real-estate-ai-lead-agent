# Unified Execution Order — Product Phase 4 (IREIOS 4.0)

| This doc owns | Does not own |
|---|---|
| Which Phase 4 work unit runs next; exit gates | Task file lists / code steps → `IREIOS_4.0_STEP_BY_STEP.md` |
| Status for Product Phase 4 only | IREIOS 3.0 history → `../phase3/UNIFIED_EXECUTION_ORDER.md` |
| | Lead decisions (locked) → `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` |

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` skipped (reason required)

**Decisions locked:** 2026-08-07 via `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md`  
**Release:** 2026-09-03 · **Hard freeze:** 2026-08-20 · **Tech lead / status owner:** Mayank  
**Program name:** IREIOS 4.0

**Prerequisite:** IREIOS 3.0 G2/G3 complete (`../phase3/`). G4 n8n WF-1 ops-pending does not block P4-0.

---

## 1. Hard rules

1. **Serial only** within this table unless a step explicitly allows parallel FE/BE against **frozen contracts**.
2. **Contract-first:** P4-1 before binding FE to new shapes (neighborhood, twin, sales-ai preview).
3. **No dual brains:** Sales NBA / assignment / FSM stay Python CEO→AE→EE. n8n = ops side-plane only.
4. **Tenant isolation never regresses** — `python gate_isolation_test.py` after data-plane changes.
5. **Do not rebuild** shipped 3.0 modules (Sales AI, predictions heuristics, Neo4j v1, CRM outbound path).
6. **Feature-flag** anything that threatens 2026-08-20 freeze: `FEATURE_GRAPH_VIZ`, `FEATURE_TWIN_LIVE`, `FEATURE_HUBSPOT_LIVE`.
7. Path references to Phase 3 docs use `../phase3/…`.

---

## 2. Locked product decisions (summary)

| Topic | Decision |
|---|---|
| Intent | **(A)** Finish/integrate existing spine — no greenfield rebuild |
| Forecast | Heuristic MVP; INR ₹ crores UI; soft 200ms; label “Heuristic estimate…” |
| HubSpot | Outbound + prod portal (Piyush); bi-di **best-effort / 4.1**; IREIOS wins; idempotency email+phone; DLQ keep |
| Sales AI | Python SoT; **Preview + Confirm**; place: **sales-copilot first**, then Leads table; no email draft; 10m debounce |
| Marketing | Python routing; **no new n8n WFs**; leave unassigned if low match |
| Graph | **Ego Lead network**; Postgres inventory for unit stretch; SSE refetch; **embed Sales Copilot**; static `ai_summary` |
| Twin | **Live**; 1 project / 2 towers / 10 floors / 40 units; read-only; single-project; poll 30s; max 500 units |
| FE surface | Both product + command-center; JWT guard CC; home **`/dashboard`**; no Approvals UI (4.1); zero hard-coded api keys |
| Staging | Local docker W1–2; hosted by W3 QA; RC1 on **read-replica** |
| Non-goals | LangGraph-n8n NBA, full ML train, HubSpot bi-di unless unblocked, monolith delete, mobile native, multi-region |

---

## 3. Master sequence

| Step | Unit | Summary | Exit gate | Owner | Status |
|---:|---|---|---|---|---|
| **P4-0** | Baseline | Apply §F amendments to sprint brief; freeze non-goals; sign evidence baseline | Evidence Pack § Baseline | Mayank | `[x]` |
| **P4-1** | Contracts | Freeze OpenAPI/human contracts: sales-ai preview/execute, predictions display, neighborhood, twin | `IREIOS_4.0_API_CONTRACTS.md` all MVP sections **FROZEN** | Aritro | `[x]` |
| **P4-2** | Graph API | `GET /api/v1/graph/neighborhood` ego `{nodes,edges}` JWT; soft-fail | pytest `test_f4_graph*` | Aritro | `[x]` |
| **P4-3** | Twin API | `GET /api/v1/inventory/twin` + seed 1×2×10×40 | pytest `test_f4_twin*` + seed | Aritro | `[x]` |
| **P4-4** | HubSpot outbound | Live `CRM_API_*` when Piyush delivers key; outbound only; flag `FEATURE_HUBSPOT_LIVE` | Contact upsert demo or `[-]` Sheets fallback | Aritro/Maitri | `[x]` flag shipped; live upsert pending Piyush key |
| **P4-5** | FE Sales AI | Preview+Confirm on **sales-copilot**, then Leads table | No mock NBA; lint | Mayank | `[x]` |
| **P4-6** | FE Forecast | Live `/predictions/*` on dashboard-mvp + product dashboard; ₹ Cr; heuristic label | FRONTEND_BACKLOG §7 | Mayank | `[x]` |
| **P4-7** | FE Graph | Ego graph embed on **Sales Copilot** (+ optional knowledge-graph page) | SSE refetch; empty state | Mayank | `[x]` |
| **P4-8** | FE Twin | Wire R3F to twin API; read-only; 30s poll | Seeded colors/status | Mayank | `[x]` |
| **P4-9** | FE SSE/JWT | JWT cookie only; guard command-center; purge MockSSE + hard-coded keys; home `/dashboard` | grep clean + backlog acceptance | Mayank | `[x]` |
| **P4-10** | Ops/n8n | **No new WFs** — smoke existing bridge only if time | Evidence ops N/A or smoke | Maitri | `[-]` default no-op unless ops asks |
| **G5** | Gate | Phase 4 MVP complete | Evidence G5 + pytest + isolation + DLQ-if-HS + lint + `task3_runner` | Team | `[x]` 2026-08-10 (task3_runner skipped Mayank ack; FE lint/tsc/build exit 0 2026-08-11) |
| **P4-QA** | Freeze | Hard freeze 2026-08-20; RC1 `ireios4-rc1` (local `pg-staging` snapshot; hosted read-replica adopted when ops delivers — `docs/PROD_READINESS_CHECKLIST.md` §5). **Pre-freeze eng baseline already green** (Evidence Pack § QA). | Prod readiness checklist + QA evidence · handoff `HANDOFF_MAYANK_PIYUSH.md` | Mayank | `[x]` ceremony — **Next Step: P4-REL (Mayank)** |
| **P4-REL** | Release | 2026-09-03 prod + telemetry · Twilio from Piyush · docker n8n Publish on deploy host (Mayank, optional) | Runbook approved (Mayank) · `HANDOFF_MAYANK_PIYUSH.md` | Mayank | `[ ]` |

---

## 4. Dependency matrix (corrected — lead F11–F15)

| Dependent | Blocked by | Clears |
|---|---|---|
| Forecast widgets | **UI wiring only** (APIs live) | P4-6 |
| Sales AI button | **Preview API contract + FE** (NBA live) | P4-1 + P4-5 |
| Graph UI | **Neighborhood API + FE wire** | P4-2 + P4-7 |
| Twin UI | **Twin API + seed + FE** | P4-3 + P4-8 |
| HubSpot automation | **Portal credentials (Piyush)** | P4-4 |
| FE parallel after P4-1 | Frozen contracts + mocks | Day-1 of P4-1 |

---

## 5. Day-to-day workflow

1. First non-`[x]` / non-`[-]` step in §3.  
2. Implement via `IREIOS_4.0_STEP_BY_STEP.md`.  
3. Log `IREIOS_4.0_CHANGELOG.md`.  
4. Flip status here + Evidence Pack.  
5. Update `docs/FRONTEND_BACKLOG.md` / `AGENTS.md` when paths change.

---

## 6. Rollback / emergency

| Problem | Action |
|---|---|
| FE broken | Feature-flag graph/twin/hubspot; keep `(dashboard)` core |
| Neo4j down | Neighborhood `available:false` + empty nodes |
| HubSpot failing | DLQ; `FEATURE_HUBSPOT_LIVE=false`; Sheets fallback |
| Preview regression | Default FE to preview-only; disable Confirm |

---

## 7. Pointers

| Need | Path |
|---|---|
| Atomic tasks | `IREIOS_4.0_STEP_BY_STEP.md` |
| Locked answers | `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` |
| API shapes | `IREIOS_4.0_API_CONTRACTS.md` |
| FE checklist | `../../docs/FRONTEND_BACKLOG.md` |
| n8n rules | `../../docs/N8N_INTEGRATION.md` |
