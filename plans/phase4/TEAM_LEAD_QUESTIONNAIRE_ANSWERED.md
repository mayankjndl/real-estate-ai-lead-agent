# Product Phase 4 — Team Lead Questionnaire

**To:** Technical Lead / Sprint author of `IREIOS_Phase_4_Master_Sprint_Plan.md`
**From:** Engineering (baseline audit against live repo)
**Date:** 2026-08-07
**Why:** Sprint DoD and status lines conflict with code already shipped in IREIOS 3.0. Answers below unlock implementation in `plans/phase4/`.

**How to answer:** For each question, pick an option or write a specific value. Where engineering has a Recommended default, accept with `ACK recommended` or override with an explicit alternative.

**Return format** (copy block per Q):
```
Q#: ACK recommended | OVERRIDE: <specific decision>
Notes: …
Owner: …  Due: …
```

---

## §F — False / Overstated Claims in the Sprint Plan

Engineering audited the repo against `IREIOS_Phase_4_Master_Sprint_Plan.md`. Lead replies True / False / Amend on each row.

| ID | Sprint claim (paraphrase) | Engineering finding | Impact if uncorrected | Lead: T/F/Amend |
|---|---|---|---|---|
| F1 | "Current Progress: 0% (Sprint Day 1)" | Backend already has Neo4j v1 + graph APIs, Sales AI NBA + HTTP, heuristic predictions, CRM outbound+DLQ, marketing/CS agents, bus/SSE, n8n bridge. FE has mock shells. 0% is false. | Week 1 rebuild waste; wrong exec reporting | **Amend:** Backend ~75%, FE ~15%, HubSpot/ops ~10%. |
| F2 | "Execution is entirely unblocked — foundational Phase 3 infrastructure is 100% live" | Largely true for spine; G4 n8n WF-1 may still be ops-pending; HubSpot portal still skipped; FE cutover incomplete | Overstates "100%" ops readiness | **True** |
| F3 | "Overall Project Completion: 70%" | Directionally plausible; needs shared definition (BE/FE/ops weighted?) | Status theater | **True** |
| F4 | Week 1: "Neo4j … schemas and ingestion APIs completed" as if greenfield | Already done in 3.0 Phase 7 + BD5. Missing is viz neighborhood payload for FE force-graph, not base schema | Fake Week 1 load on Aritro | **Amend:** Neo4j API payload for FE viz neighborhood completed. |
| F5 | Week 1: "Forecast Engine — models trained and serving endpoints finalized" | Endpoints exist; code states heuristic MVP, not ML accuracy. No training pipeline / model artifacts | Compliance risk if sold as trained ML | **Amend:** Forecast Engine heuristic MVP endpoints finalized. |
| F6 | Week 1: "Marketing AI routing workflows finalized on the automation plane" | Marketing agent + segments + WF5 report fan-out exist. Assignment/escalation is Python, not n8n router | Wrong owner/plane for "routing" | **True** |
| F7 | Week 2: "HubSpot CRM backend integration complete and fully exposed" / "Bi-directional webhook/API sync" | Outbound push+retry+DLQ code ready; live portal skipped; no inbound HubSpot webhook in codebase | Week 2 impossible without portal + greenfield inbound | **Amend:** HubSpot CRM outbound integration complete. |
| F8 | Week 2: "Sales AI logic (NBA) deployed" as Maitri Week 2 | Already deployed in Python (`sales_agent.py`, bus, `POST .../sales-ai`). FE button missing | Maitri overloaded; Mayank underscoped | **True** |
| F9 | Sales AI DoD: "LangGraph reasoning agents deployed to the n8n orchestrator" | NBA is deterministic Python, not LangGraph-in-n8n. n8n hard rules: must not own FSM/assignment (`docs/N8N_INTEGRATION.md`) | Architecture regression if forced | **Amend:** Sales AI logic (NBA) via Python-centric architecture (CEO→AE→EE). |
| F10 | Marketing DoD: "Automated routing … mapped in n8n. Inbound leads assigned and escalated based on predictive scores" | Assignment = `ensure_lead_assignment` + CRM/Sales automation in Python. n8n = Gmail/Sheets/ops | Conflicts with shipped design | **Amend:** Routing based on Python-centric architecture. |
| F11 | Dependency: Graph UI blocked by Neo4j APIs end of Week 1 | Context/health APIs already exist. Blocker is nodes/edges contract + FE wire, not "no Neo4j" | False critical path | **Amend:** Graph UI blocked by API nodes/edges contract + FE wire. |
| F12 | Dependency: Forecast widgets blocked by Prediction APIs Week 1 | `/api/v1/predictions/*` already live | False critical path | **Amend:** Forecast widgets blocked by UI wiring. |
| F13 | Dependency: Sales AI Logic blocked by Prediction APIs | Sales AI already runs scoring internally; HTTP API live | False critical path | **Amend:** Sales AI Button blocked by UI wiring. |
| F14 | Dependency: HubSpot Automation blocked by HubSpot CRM Integration APIs Week 2 | Python CRM path exists; portal credentials + bi-di are real blockers, not "no API code" | Partial truth — clarify | **Amend:** HubSpot Automation blocked by portal credentials. |
| F15 | Dependency: Sales AI Button blocked by "payload structure lock" Week 2 | Payload already returnable from live API; needs contract freeze doc + FE, not new Maitri agent | Mis-ordered dependency | **Amend:** Sales AI Button blocked by API payload contracts + FE wire. |
| F16 | Risk: "cascading backend bottlenecks centered on Aritro" for all Week 1 | Much of Aritro Week 1 is done. Real BE gaps: neighborhood API, twin layout API, HubSpot go-live/bi-di | Wrong risk focus; FE + HubSpot org blockers dominate | **True** |
| F17 | Mitigation: "Contract-First Day 1 mocks" | Still valid for new neighborhood/twin shapes; not needed to reinvent sales-ai/predictions | Keep mitigation; narrow scope | **True** |
| F18 | QA checklist: "Neo4j queries under 200ms" | Not instrumented as a gate today; context path is soft-timeout 0.5s on reply path | Need explicit measure job or relax | **True** |
| F19 | Forecast DoD: "200ms latency SLA" + "ML scoring algorithms deployed" | Heuristics are fast enough typically; "ML deployed" is overstated | Redefine DoD | **Amend:** Heuristic estimates fast enough typically. |
| F20 | Mayank Graph DoD: "parses Aritro's Week 1 API payload" + "real-time node updates" | FE mock expects Project/Tower/Unit/Comm graph; backend returns `similar_leads` + agent, not that shape. No graph SSE push | Need new API or reduce DoD | **True** |
| F21 | Digital Twin: "mocked/stubbed or event bus" | FE mock only; no twin bus API; inventory counts only | Specify live layout vs mock-OK | **True** |
| F22 | "Deviation from these milestones is strictly prohibited" vs 4-week compress of 5-week work | Several milestones already met early; blind adherence causes rebuild | Allow re-baseline | **True** |
| F23 | Naming: "Phase 4" | Repo already used Phase 4 for Bug P4 and Expansion follow-up Phase 4 | Call this Product Phase 4 / IREIOS 4.0 in comms | **True** |

### F-follow-ups (required)

1. **May engineering edit the sprint doc §6 to replace 0% with a corrected split (e.g. Backend foundation ~75%, FE integration ~15%, HubSpot/ops ~10%)?** Yes/No
   → **Yes.** Edit §6 to replace 0% with: Backend ~75%, FE ~15%, HubSpot/ops ~10%.

2. **May engineering rewrite DoD rows F9/F10/F5/F7 to match CEO→AE→EE architecture?** Yes/No
   → **Yes.** Rewrite DoD rows F9/F10/F5/F7 to match the shipped Python-centric architecture (CEO→AE→EE).

3. **Which dependency rows (F11–F15) stay as executive fiction vs get corrected publicly?**
   → **Correct publicly.** Update the Dependency Matrix (F11–F15) to reflect the true API contract and UI wiring blockers.

---

## Q0 — Program Intent

- **Q0.1:** OVERRIDE — (A) Finish/integrate what exists.
- **Q0.2:** OVERRIDE — 2026-09-03. Envs: `staging-api.ireios`, `prod-api.ireios`.
- **Q0.3:** OVERRIDE — 2026-08-20 (Start of Week 3).
- **Q0.4:** OVERRIDE — Mayank.
- **Q0.5:** OVERRIDE — Mayank.

**Notes:** We will use the existing backend spine.
**Owner:** Mayank **Due:** Immediate

---

## Q1 — Forecast / ML / 200ms

- **Q1.1:** ACK recommended (Accept heuristic MVP).
- **Q1.2:** OVERRIDE — (c) aspirational (soft SLA).
- **Q1.3:** OVERRIDE — INR (₹) / Crores.
- **Q1.4:** ACK recommended ("Heuristic estimate (not a trained model)").
- **Q1.5:** OVERRIDE — No (tenant isolated only).

**Notes:** No ML training pipelines for Phase 4. We ship the heuristic MVP.
**Owner:** Aritro **Due:** End of Week 1

---

## Q2 — HubSpot

- **Q2.1:** ACK recommended (A - Outbound + portal).
- **Q2.2:** OVERRIDE — Prod portal. Admin: Piyush. API Key due: End of Week 1.
- **Q2.3:** OVERRIDE — Owner: Mayank to escalate to Piyush. Fallback: Sheets until resolved.
- **Q2.4:** ACK recommended.
- **Q2.5:** OVERRIDE — IREIOS wins.
- **Q2.6:** OVERRIDE — email + phone.
- **Q2.7:** ACK recommended (Yes).
- **Q2.8:** OVERRIDE — Best-effort. (Bi-di pushed to 4.1 if portal email issues persist.)

**Notes:** Focus strictly on outbound stability first.
**Owner:** Aritro/Maitri **Due:** Week 2

---

## Q3 — Sales AI / NBA

- **Q3.1:** ACK recommended (Yes, Python remains SoT).
- **Q3.2:** OVERRIDE — (C) sales-copilot timeline first, then (B) Leads table.
- **Q3.3:** OVERRIDE — No (Preview + Confirm required).
- **Q3.4:** ACK recommended.
- **Q3.5:** ACK recommended.
- **Q3.6:** OVERRIDE — Preview + confirm.
- **Q3.7:** OVERRIDE — 10 min Redis.
- **Q3.8:** OVERRIDE — No. Keep out of scope for Phase 4 MVP.

**Notes:** n8n will not own NBA reasoning. Python handles it, UI renders it.
**Owner:** Mayank (UI) / Aritro (API) **Due:** Week 2

---

## Q4 — Marketing "Routing in n8n"

- **Q4.1:** ACK recommended (Yes, Python owns routing).
- **Q4.2:** OVERRIDE — None.
- **Q4.3:** OVERRIDE — Leave unassigned (current policy).
- **Q4.4:** OVERRIDE — No changes.

**Notes:** Keep n8n strictly for ops/notifications.
**Owner:** Maitri **Due:** Week 1

---

## Q5 — Knowledge Graph Viz

- **Q5.1:** ACK recommended (A - Ego Lead network).
- **Q5.2:** OVERRIDE — Postgres inventory.
- **Q5.3:** ACK recommended.
- **Q5.4:** OVERRIDE — (B) SSE refetch.
- **Q5.5:** OVERRIDE — Soft SLA. Expected max leads: 500/tenant.
- **Q5.6:** OVERRIDE — Embed on lead detail (Sales Copilot).
- **Q5.7:** OVERRIDE — Static string OK.

**Notes:** Keep the graph UI scope tight. Ego network is plenty for RC1.
**Owner:** Mayank (UI) / Aritro (API) **Due:** Week 2

---

## Q6 — Digital Twin

- **Q6.1:** ACK recommended (Yes live).
- **Q6.2:** OVERRIDE — 1 project, 2 towers, 10 floors, 40 units.
- **Q6.3:** ACK recommended.
- **Q6.4:** OVERRIDE — Read-only.
- **Q6.5:** OVERRIDE — Single-project MVP.
- **Q6.6:** OVERRIDE — 30s.
- **Q6.7:** OVERRIDE — 500 units.

**Notes:** Basic visual mapping only. No complex write-backs for MVP.
**Owner:** Mayank **Due:** Week 2

---

## Q7 — Frontend Surface of Truth

- **Q7.1:** ACK recommended (Both).
- **Q7.2:** ACK recommended (Yes).
- **Q7.3:** OVERRIDE — `/dashboard`.
- **Q7.4:** OVERRIDE — No. (Defer to 4.1).
- **Q7.5:** ACK recommended (Yes, zero hardcoded keys).
- **Q7.6:** OVERRIDE — Desktop first for graph/twin.
- **Q7.7:** OVERRIDE — None.

**Notes:** Strict JWT implementation is required for RC1.
**Owner:** Mayank **Due:** Week 2

---

## Q8 — Contract-First & Staging

- **Q8.1:** OVERRIDE — Owner: Aritro. Date: End of Week 1.
- **Q8.2:** OVERRIDE — Local docker for Week 1/2, hosted URL by Week 3 QA.
- **Q8.3:** OVERRIDE — Read-replica.
- **Q8.4:** ACK recommended.
- **Q8.5:** ACK recommended.

**Notes:** Mocks for graph/twin must be published Day 1.
**Owner:** Aritro **Due:** Week 1

---

## Q9 — QA Gates & Non-Goals

- **Q9.1:** ACK recommended.
- **Q9.2:** ACK recommended (Yes).
- **Q9.3:** ACK recommended (All 6 non-goals are confirmed as non-goals).
- **Q9.4:** OVERRIDE — GitHub Issues.
- **Q9.5:** ACK recommended (Yes).

**Notes:** Strict alignment on what we are NOT building.
**Owner:** Mayank **Due:** Week 3

---

## Q10 — Ownership & Comms

- **Q10.1:** ACK recommended.
- **Q10.2:** OVERRIDE — Mayank.
- **Q10.3:** OVERRIDE — Slack daily.
- **Q10.4:** OVERRIDE — Re-baseline to reflect shipped work.
- **Q10.5:** OVERRIDE — IREIOS 4.0.

**Notes:** Engineering management is locked.
**Owner:** Mayank **Due:** Ongoing

---

## Q11 — Secrets & Env (fill or N/A)

| Item | Value or N/A | Owner | Due |
|---|---|---|---|
| Staging base URL | N/A | Mayank | Immediate |
| Prod base URL | N/A | Mayank | Immediate |
| HubSpot portal + key | N/A | Mayank | Immediate |
| `NEO4J_*` prod | N/A | Mayank | Immediate |
| `N8N_*` / bridge | N/A | Mayank | Immediate |
| `CRM_API_*` | N/A | Mayank | Immediate |
| `GOOGLE_CALENDAR_*` | N/A | Mayank | Immediate |
| Brochure/floorplan HTTPS URLs | N/A | Mayank | Immediate |
| Twilio prod | N/A | Mayank | Immediate |
| Admin key rotation | N/A | Mayank | Immediate |
| Go-live flag flips checklist owner | N/A | Mayank | Immediate |

**Notes:** Escalate HubSpot portal credentials to Piyush today. **Owner:** Mayank **Due:** Immediate

---

## Q12 — Acceptance Demos (Required / Optional / Cut)

| Demo | Engineering default | Lead |
|---|---|---|
| WA → SSE dashboard alert <2s | Required | ACK recommended |
| Sales AI button → NBA render | Required | ACK recommended |
| Forecast widgets from `/predictions/*` | Required | ACK recommended |
| Graph neighborhood hot lead | Required if Q5≠C | ACK recommended |
| Twin seeded units + colors | Required if Q6=Yes live | ACK recommended |
| HubSpot contact upsert | Per Q2 | ACK recommended |
| n8n Gmail on `lead.hot` | Optional ops | ACK recommended |
| Isolation drill green | Required | ACK recommended |
| DLQ replay green | Required if HubSpot live | ACK recommended |

**Notes:** These are the exact demos we will show Piyush in Week 4. **Owner:** Team **Due:** Week 4

---

## Q13 — Blockers Called Out in Sprint "Risk / Dependency" — Validate Each

For each, lead marks: Still a blocker / Not a blocker (already shipped) / Different blocker: …

| Sprint blocker narrative | Engineering view | Lead |
|---|---|---|
| Mayank Graph UI blocked on Aritro Neo4j Week 1 | APIs exist; need neighborhood shape | ACK recommended |
| Mayank Forecast blocked on Prediction APIs Week 1 | APIs exist; FE wire only | ACK recommended |
| Maitri Sales AI blocked on Prediction APIs | Sales AI already live | ACK recommended |
| Maitri HubSpot automation blocked on Aritro HubSpot Week 2 | Code path exists; portal + bi-di policy are real | ACK recommended |
| Mayank Sales AI button blocked on Maitri payload lock Week 2 | Lock = document existing JSON; Maitri not on critical path for button | ACK recommended |
| Aritro is single point of failure for all Week 1 | Overstated; FE + HubSpot org are equal/larger risks | ACK recommended |
| 4-week compress → stability risk | Valid residual risk for new twin/graph/FE/HubSpot, not full stack rewrite | ACK recommended |

**Notes:** True blocker is API payload contracts + UI wiring. Backend is largely unblocked. **Owner:** Aritro **Due:** Week 1

---

## Q14 — Definition of Done Rewrite Permission

May engineering treat the following as official Phase 4 DoD unless you override?

| Owner | Rewritten DoD (recommended) | ACK? |
|---|---|---|
| Mayank | Sales AI button live on CRM/leads; forecast widgets on live predictions; graph on neighborhood API (or accepted mock); twin on layout API (or accepted mock/defer); JWT SSE; no hard-coded client keys; lint clean | ACK recommended |
| Aritro | Neighborhood graph API + twin layout API + latency smoke; HubSpot per Q2; no fake "models trained" claim; OpenAPI updated | ACK recommended |
| Maitri | No NBA rewrite; n8n remains ops; only agreed WF deltas; HubSpot automation only if Q2 says so; Python routing remains SoT | ACK recommended |

**Notes:** Official permission granted to rewrite DoDs to reflect these decisions. **Owner:** Aritro **Due:** Immediate

---

## After You Answer

Engineering will:

1. Remove `BLOCKED ON LEAD` / `[?]` from `UNIFIED` + `STEP_BY_STEP`
2. Freeze `IREIOS_4.0_API_CONTRACTS.md`
3. Implement P4-0→G5 in order
4. Optionally patch root sprint §6 status with your approved numbers

**Active plans path:** `plans/phase4/`
**Archived 3.0 plans:** `plans/phase3/`
