# IREIOS 4.0 — Implementation Plan (macro)

| This doc owns | Does not own |
|---|---|
| Frozen decisions, phase overview, target surfaces, risks | Atomic steps → `IREIOS_4.0_STEP_BY_STEP.md` |
| Corrected program baseline | 3.0 history → `../phase3/` |

**Status:** **LOCKED** (2026-08-07) · **P4-0…P4-9 + G5 implemented** (2026-08-10) · next freeze/RC1/prod  
**Spine unchanged:** `Event → CEO → Agent/Workflow → AE → EE → Event`  
**Release:** 2026-09-03 · **Freeze:** 2026-08-20 · **Name:** IREIOS 4.0

---

## 1. Program intent

**Product Phase 4 = finish/integrate what exists** (Q0.1 = A).

| Area | Baseline (lead-amended) | Phase 4 work |
|---|---|---|
| Backend foundation | ~75% | Neighborhood API, twin API, HubSpot outbound go-live, sales-ai preview mode |
| FE integration | ~15% | Wire Sales AI, forecasts, graph embed, twin, JWT SSE |
| HubSpot/ops | ~10% | Portal key + outbound stability; bi-di deferred 4.1 |

**Not this phase:** rebuild Sales AI / KG / predictions; LangGraph-in-n8n; trained ML; Approvals UI; new n8n WFs.

---

## 2. Frozen decisions

| ID | Decision | Source |
|---|---|---|
| D1 | Integrate only — no greenfield agent rewrite | Q0.1 |
| D2 | CEO→AE→EE spine; n8n ops side-plane | F9, F10, Q4 |
| D3 | Sales NBA Python SoT | Q3.1 |
| D4 | Sales AI UI: **Preview + Confirm** (no auto side-effects on first click) | Q3.3, Q3.6 |
| D5 | Sales AI placement: **sales-copilot first**, then Leads table | Q3.2 |
| D6 | No LLM email draft | Q3.8 |
| D7 | Forecasts = heuristic MVP; UI label honest; INR ₹ crores | Q1 |
| D8 | 200ms = soft/aspirational | Q1.2, F19 |
| D9 | Graph = ego Lead network; embed Sales Copilot; SSE refetch | Q5 |
| D10 | Twin = live layout API; 1p/2t/10f/40u; read-only; 30s poll | Q6 |
| D11 | FE both surfaces; JWT on command-center; home `/dashboard` | Q7 |
| D12 | Approvals UI deferred 4.1 | Q7.4 |
| D13 | HubSpot outbound + prod portal; bi-di 4.1 best-effort; IREIOS wins | Q2 |
| D14 | Idempotency identity: email + phone | Q2.6 |
| D15 | Feature flags: `FEATURE_GRAPH_VIZ`, `FEATURE_TWIN_LIVE`, `FEATURE_HUBSPOT_LIVE` | Q8.4 |
| D16 | Tests: `tests/test_f4_*.py`; G5 includes `task3_runner` | Q9 |
| D17 | RC1 against read-replica | Q8.3 |
| D18 | Bug tracker: GitHub Issues | Q9.4 |
| D19 | Secrets: escalate Piyush/Mayank — not blocking design | Q11 |

---

## 3. Phase overview

| Step | Goal | Primary owner |
|---|---|---|
| P4-0 | Re-baseline sprint docs + evidence | Mayank |
| P4-1 | Freeze contracts + Day-1 mocks for graph/twin | Aritro |
| P4-2 | Neighborhood graph API | Aritro |
| P4-3 | Twin inventory API + seed | Aritro |
| P4-4 | HubSpot outbound live (flagged) | Aritro/Maitri |
| P4-5 | FE Sales AI preview/confirm | Mayank |
| P4-6 | FE Forecast widgets | Mayank |
| P4-7 | FE Graph embed | Mayank |
| P4-8 | FE Twin wire | Mayank |
| P4-9 | FE JWT/SSE harden | Mayank |
| P4-10 | n8n no-op (no new WFs) | Maitri |
| G5 → QA → REL | Gates + freeze + 2026-09-03 | Mayank |

---

## 4. Target surfaces

### Backend (build / extend)

| Surface | Action |
|---|---|
| `POST /api/v1/leads/{id}/sales-ai` | Add `mode=preview\|execute` (body or query). Preview = no CRM/AE/stage commit. Execute = full pipeline + optional NBA AE. |
| `GET /api/v1/graph/neighborhood` | **New.** Ego graph `{nodes,edges}` from Neo4j Lead/Agent + optional unit interest from PG. |
| `GET /api/v1/inventory/twin` | **New.** Group `InventoryUnit` → project/towers/floors/units. |
| `seed_inventory.py` or `seed_twin_demo.py` | Seed 40 units (2 towers × 10 floors × 2). May add `floor` column or `meta_json.floor`. |
| HubSpot | Flip `CRM_API_*` when key arrives; no inbound webhook in 4.0 |
| Predictions | **No logic change** — optional `disclaimer` + `currency` fields additive |

### Frontend

| Surface | Action |
|---|---|
| `sales-copilot` | Lead picker; Sales AI Preview/Confirm; ego graph panel; timeline JWT |
| `(dashboard)/leads` | Sales AI button (second priority) |
| `dashboard-mvp` + `(dashboard)/dashboard` | Forecast from live APIs; ₹ Cr formatting; heuristic badge |
| `digital-twin` | Live twin API; read-only; 30s refresh |
| `knowledge-graph` | Optional full-page; primary embed is copilot |
| `proxy.ts` | Guard command-center routes with JWT |
| Auth | Zero `secret-client-key-123` in client bundles |

### Explicit non-goals (Q9.3)

- LangGraph-in-n8n NBA rewrite  
- Full multi-model ML training  
- HubSpot bi-di (unless portal unblocks early — still 4.1 default)  
- Monolith `agent.py` deletion  
- Mobile native apps  
- Multi-region  
- Approvals UI  
- New n8n workflows  
- Generate Email Draft  

---

## 5. Engineering design notes (no further lead Qs)

### 5.1 Sales AI Preview + Confirm

Today `run_sales_ai(..., sync_crm=True)` always scores, may assign, may advance stage, commits, optionally CRM.

**Contract:**

```http
POST /api/v1/leads/{id}/sales-ai
Content-Type: application/json
{ "mode": "preview" }   // default for FE first click
{ "mode": "execute" }   // Confirm button
```

| mode | score in response | DB write scores | assign | stage progress | CRM AE | NBA→AE side effects |
|---|---|---|---|---|---|---|
| `preview` | yes (computed) | **no** | no | no | no | no |
| `execute` | yes | yes | yes | yes | yes | yes (existing bus mapping) |

Bus-driven SalesAgent path **unchanged** (still auto-executes on events) — only HTTP manual path is preview/confirm.

### 5.2 Graph neighborhood

- Center: requested `lead_id` (required for embed).  
- Nodes: center Lead, assigned Agent, up to N similar leads (from existing `get_similar_leads` / context).  
- Optional stretch: Unit nodes from PG inventory matching lead location/property_type (not full Project/Tower/Comm mock).  
- Soft SLA; max graph size sized for ≤500 leads/tenant sampling similar only.  
- On SSE `lead.scored` | `lead.assigned` | `lead.hot` → FE refetches neighborhood.

### 5.3 Twin layout

`InventoryUnit` has `project_name`, `tower`, `unit_code`, `status`, `list_price`, `bhk`, `meta_json` — **no floor column today**.

**Plan:** Prefer additive `floor Integer nullable` on `inventory_units` (migrate) **or** encode floor in `meta_json.floor` for zero-migrate MVP. Seed script creates:

- project: e.g. `The Summit`  
- towers: `Tower A`, `Tower B`  
- floors 1–10, 2 units each → 40 units  
- statuses mix available/hold/sold  

API groups by project → tower → floor → units. Read-only FE.

### 5.4 Forecast display

| Widget | Endpoint | Format |
|---|---|---|
| Expected revenue | `GET /predictions/revenue` → `total_expected_revenue` | ₹ X.XX Cr (divide by 1e7) |
| Cashflow | `GET /predictions/cashflow` → `expected_30pct_cashflow` | ₹ Cr |
| Inventory mix | `GET /predictions/inventory` | counts by status |
| Cancellation / at-risk | `GET /predictions/cancellation-risk` | list length / table |
| Per-lead (copilot) | `GET /leads/{id}/prediction` | % + days |

Always show disclaimer: **Heuristic estimate (not a trained model)**.

### 5.5 HubSpot

- Outbound only via existing EE path.  
- When `CRM_API_KEY` real + `FEATURE_HUBSPOT_LIVE=true`, live upsert.  
- Else demo stub / Sheets fallback (ops).  
- No inbound webhook in 4.0.  
- Conflict policy documented for 4.1: IREIOS wins.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| HubSpot key late (Q11 N/A) | Flag off; demo Sheets; don’t block G5 FE |
| Floor column migrate | Prefer `meta_json.floor` if migrate risk |
| Preview vs bus dual behavior | Document; HTTP-only preview |
| Freeze 2026-08-20 slip | Cut twin/graph to flag-off before freeze |
| Secrets all N/A | Mayank→Piyush track parallel; not design blocker |

---

## 7. Success metrics

- All Q12 required demos pass on staging/read-replica  
- G5 evidence green  
- Zero High/Critical GitHub Issues at RC1  
- No hard-coded client keys in FE  
- Sprint §6 shows ~75/15/10 not 0%  
