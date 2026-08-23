# IREIOS 4.0 — Master Sprint Plan & Execution Matrix

> **Authoritative engineering queue:** [`plans/phase4/`](plans/phase4/)  
> **Locked lead decisions:** [`plans/phase4/TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md`](plans/phase4/TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md)  
> **Archived IREIOS 3.0 plans:** [`plans/phase3/`](plans/phase3/)  
>
> **Naming:** **Product Phase 4 / IREIOS 4.0** (not Bug P4 or Expansion follow-up Phase 4).  
> **Re-baselined:** 2026-08-07 per tech lead (Mayank). DoD and dependencies below match shipped architecture (CEO→AE→EE).

---

## 1. Sprint Milestones & Delivery Dates

4-week timeline. Scope cuts prefer feature flags over silent DoD fiction. **Hard freeze: 2026-08-20.** **Prod release: 2026-09-03.**

### Week 1 — Contracts + remaining backend surfaces
- **Aritro:** Freeze API contracts (sales-ai preview/execute, graph neighborhood, twin layout). Day-1 mocks for FE.
- **Aritro:** `GET /api/v1/graph/neighborhood` (ego Lead network) + `GET /api/v1/inventory/twin` + 40-unit seed.
- **Aritro:** Forecast = **heuristic MVP** endpoints already live — display contract + optional disclaimer only (no ML training).
- **Maitri:** No new n8n WFs; Python routing remains SoT; prepare HubSpot outbound go-live when portal key arrives (Piyush).

### Week 2 — FE cutover + HubSpot outbound
- **Mayank:** Sales AI **Preview + Confirm** on sales-copilot, then Leads table; forecast widgets (₹ Cr); graph embed; twin live read-only; JWT SSE; command-center auth.
- **Aritro/Maitri:** HubSpot **outbound** live when credentials ready (`FEATURE_HUBSPOT_LIVE`); bi-di deferred to 4.1.

### Week 3 — QA & Testing (from 2026-08-20)
- Hard code freeze. Zero new development.
- Internal QA + E2E. RC1 `ireios4-rc1` — local full-stack docker + `pg-staging` seeded from prod snapshot (`docs/PROD_READINESS_CHECKLIST.md` §5.1); hosted read-replica adopted when ops delivers (§5.2).
- Gate G5: **passed 2026-08-10** (pytest 426, isolation, DLQ; `task3_runner` skipped Mayank ack). FE lint/tsc/build **exit 0 resolved 2026-08-11** (`4494307`).

### Week 4 — Production Release (2026-09-03)
- IREIOS 4.0 MVP to production. Telemetry via `/metrics`. Runbook approved by **Mayank**.

---

## 2. Task Ownership & Definition of Done (DoD) — rewritten

### Mayank — Frontend Lead / Tech Lead

| Task | Definition of Done |
|---|---|
| Knowledge Graph Visualization | Ego-network UI (center lead + agent + similars) on **Sales Copilot**, driven by `GET /api/v1/graph/neighborhood`. SSE refetch on `lead.scored` / `lead.assigned` / `lead.hot`. Zero console errors. Desktop-first. |
| Predictive Forecast Widgets | Widgets on `/dashboard` + dashboard-mvp use live `/api/v1/predictions/*`. Display **₹ crores**. Label: **Heuristic estimate (not a trained model)**. |
| Digital Twin MVP UI | R3F page loads `GET /api/v1/inventory/twin` (seeded 1 project / 2 towers / 10 floors / 40 units). **Read-only.** Poll 30s. |
| Sales AI | **Preview + Confirm** on sales-copilot first, then Leads table. Calls `POST .../sales-ai` with `mode=preview\|execute`. Renders action, rationale, scores, stage, assignee. Error boundaries. No email draft. |
| Auth / SSE | JWT on product + command-center routes. Home **`/dashboard`**. Zero hard-coded `secret-client-key-123`. MockSSE unused. |

### Aritro — Backend Lead

| Task | Definition of Done |
|---|---|
| Graph neighborhood API | `GET /api/v1/graph/neighborhood` returns FROZEN `{nodes,edges}` ego payload; tenant-scoped; Neo4j-down soft-empty; OpenAPI updated. |
| Twin layout API | `GET /api/v1/inventory/twin` + seed script for demo tenant; status `available\|hold\|sold`. |
| Forecast Engine | Heuristic MVP endpoints remain authenticated + documented. Soft &lt;200ms aspirational. **No** “models trained” claim. |
| HubSpot CRM | **Outbound** push via existing EE path + DLQ when `FEATURE_HUBSPOT_LIVE` + real key. Identity: email + phone. **Not** bi-directional in 4.0. |
| Sales AI HTTP | Support `mode=preview` (no side effects) and `mode=execute` (full pipeline). Bus path unchanged. |

### Maitri — AI Automation Lead

| Task | Definition of Done |
|---|---|
| Sales AI Logic (NBA) | **Python** `SalesAgent` remains source of truth (CEO→AE→EE). **No** LangGraph-in-n8n NBA. |
| Marketing AI Routing | **Python** assignment/escalation remains SoT. Leave unassigned if match score low. **No new n8n workflows.** n8n = ops notifications only. |
| HubSpot CRM Automation | Outbound stability when portal live; verified idempotency via existing path + DLQ. No bi-di n8n ownership of FSM. |

---

## 3. Dependency Matrix (corrected)

| Dependent Task | Owner | Blocked By | Blocking Owner | Clears By |
|---|---|---|---|---|
| Knowledge Graph Visualization UI | Mayank | Neighborhood API + FE wire | Aritro | Week 1 API / Week 2 FE |
| Predictive Forecast Widgets | Mayank | **UI wiring only** (APIs live) | — | Week 2 |
| Sales AI Button | Mayank | Preview/execute contract + FE wire | Aritro (mode) / Mayank (UI) | Week 2 |
| HubSpot Automation | Maitri/Aritro | **Portal credentials (Piyush)** | Piyush/Mayank | Week 2 best-effort |
| Twin UI | Mayank | Twin API + seed | Aritro | Week 1–2 |

---

## 4. Risk Assessment & Mitigation

**Critical residual risks:** FE cutover density before freeze; HubSpot org/email key delay; new neighborhood/twin surfaces.

**Mitigations:**
1. **Contract-first** — FROZEN contracts in `plans/phase4/IREIOS_4.0_API_CONTRACTS.md`; Day-1 mocks.
2. **Parallelization** — FE builds against mocks immediately after P4-1.
3. **Feature flags** — `FEATURE_GRAPH_VIZ`, `FEATURE_TWIN_LIVE`, `FEATURE_HUBSPOT_LIVE` cut incomplete work at freeze.
4. **No rebuild** of shipped Python agents.

---

## 5. Production Readiness Checklist (Week 3 QA)

**Single source:** `docs/PROD_READINESS_CHECKLIST.md` (flag matrix, secrets track, infra adoption, integration runbooks). Executive summary:

- [ ] All required Phase 4 tickets closed or feature-flagged off
- [ ] Zero High/Critical bugs on **GitHub Issues**
- [ ] E2E demos (Q12) pass on staging
- [ ] Redis bus healthy under smoke load
- [ ] Graph neighborhood soft-latency acceptable (200ms aspirational)
- [ ] Frontend lint + build Exit 0 (resolved 2026-08-11)
- [ ] RC1 `ireios4-rc1` on staging (local `pg-staging` snapshot; hosted read-replica adopted when delivered)
- [ ] Runbook approved by **Mayank**
- [ ] `task3_runner` **waived** at QA — Gemini quota (Mayank ack, consistent with G5)

---

## 6. Project Status & Release Metrics

- **Current Progress (2026-08-13):** P4-0…P4-9 **implementation complete** · G5 **green** · FE quality + full regression **baseline green** · **code audit: no blocking debt**. Twin UI at command-center `/digital-twin` (seed required). n8n JSON shipped; live Publish = deploy-host ops after docker wipe (**Mayank**). Handoff: `plans/phase4/HANDOFF_MAYANK_PIYUSH.md`. Remaining: freeze ceremony **2026-08-20**, Piyush Twilio (+ optional HS), prod **2026-09-03**.
- **Overall Project Completion:** ~90% toward Phase 4 MVP (eng done; freeze/secrets/deploy left).
- **Expected IREIOS 4.0 Release Date:** **2026-09-03**.
- **Hard freeze:** **2026-08-20**.
- **Weekly status owner / runbook approver:** **Mayank**.
- **Envs (names):** `staging-api.ireios`, `prod-api.ireios` (hosted URLs still ops TBD).
