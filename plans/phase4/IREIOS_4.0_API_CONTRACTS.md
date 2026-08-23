# IREIOS 4.0 — API contracts (FROZEN for MVP)

| This doc owns | Does not own |
|---|---|
| Human-readable contracts for Phase 4 surfaces | 3.0 SSE history → `../phase3/IREIOS_3.0_API_SSE_CONTRACTS.md` |
| Freeze rules | Runtime dump → regen `openapi_ireios4.json` after code |

**Status:** **FROZEN** for MVP per lead answers 2026-08-07 (implement against this doc)  
**Compat:** Additive fields OK after freeze. Renames require coordinated FE+BE PR.

Auth: **JWT** (Bearer or HttpOnly `jwt` cookie). Prefer cookie for browser. No hard-coded api_key in FE bundles. **All JWT routes accept both styles** — `Authorization: Bearer <jwt>` or cookie `jwt` — including `/inventory/twin`, `/graph/neighborhood`, and `/predictions/*` (BE unify 2026-08-13; see `docs/COMMAND_CENTER_VERIFY.md`). Events/graph family additionally accept `X-API-Key` / `?api_key=`.

---

## 0. Sales AI — FROZEN

### `POST /api/v1/leads/{lead_id}/sales-ai`

| | |
|---|---|
| Auth | JWT · tenant-scoped lead |
| Body | `{ "mode": "preview" \| "execute" }` — default **`preview`** if omitted |
| Errors | `404` · `401` · `422` invalid mode |

### Response (both modes)

```json
{
  "status": "success",
  "lead_id": 1,
  "mode": "preview",
  "scores": {
    "conversion_probability": 72.0,
    "lead_temperature": "hot",
    "engagement_score": 60.0,
    "urgency_level": "high",
    "confidence_score": 80.0
  },
  "assigned_agent": "Agent Name or null",
  "recommendation": {
    "action": "schedule_site_visit",
    "rationale": "string",
    "missing_fields": []
  },
  "funnel_stage": "Contacted",
  "crm_sync": null,
  "applied": false,
  "actions_executed": [],
  "stage_before": "New",
  "scores_before": {
    "conversion_probability": 47.0,
    "lead_temperature": "cold"
  },
  "scores_unchanged": false,
  "test_mode": false,
  "note": "string"
}
```

| Field | preview | execute |
|---|---|---|
| `mode` | `"preview"` | `"execute"` |
| `applied` | `false` | `true` |
| `scores` | computed, **not persisted** | computed **and persisted** |
| `assigned_agent` | current or would-be (no write) | after `ensure_lead_assignment` |
| `funnel_stage` | current (no advance) | after `progress_deal_stage` |
| `crm_sync` | `null` | AE result object or error |
| `actions_executed` | `[]` | AE action results `[{"action": str, "status": "ok"\|"skipped", "note": str?}]` |
| `stage_before` | — (execute only) | DB funnel stage before Confirm |
| `scores_before` | — (execute only) | DB `conversion_probability` + `lead_temperature` before Confirm |
| `scores_unchanged` | — (execute only) | `true` when stored scores equal recomputed (no drop applied) |
| `test_mode` | `false` | `settings.TEST_MODE` — `true` = WhatsApp not delivered to real phones |
| `note` | (execute only) | human-readable summary (score floors / TEST_MODE warning) |
| side effects (WhatsApp/notify/task) | **none** | yes via existing NBA→AE path |

**`recommendation.action` enum (frozen):**  
`request_info` | `schedule_site_visit` | `escalate_hot` | `send_brochure` | `assign_agent` | `nurture_followup` | `deal_closed` (terminal stage — **no AE**; execute `actions_executed` may contain a single `{"action": "deal_closed", "status": "skipped"}` entry)

**FE flow:**  
1. User clicks Sales AI → `mode=preview` → render action/rationale/scores/stage.  
2. User clicks Confirm → `mode=execute` → refresh lead row/timeline.  
3. Placement: **sales-copilot first**, then Leads table.  
4. Rate limit: reuse Redis `sales_ai_lock:{client}:{lead}` TTL 600s on **execute** (and bus path); preview may be unbound or soft-limited (e.g. 30/min) — implement soft limit optional.

**Bus path:** unchanged auto-execute (not preview).

---

## 1. Predictions — FROZEN (existing + display rules)

All JWT · client-scoped · **heuristic** (not ML).

| Route | Key response fields | FE display |
|---|---|---|
| `GET /api/v1/predictions/revenue` | `total_expected_revenue` (INR absolute), `open_lead_count` | ₹ `(value/1e7).toFixed(2) Cr` |
| `GET /api/v1/predictions/cashflow` | `expected_30pct_cashflow`, `open_lead_count` | ₹ Cr |
| `GET /api/v1/predictions/inventory` | map `status → count` | chips/bars |
| `GET /api/v1/predictions/cancellation-risk` | `[{lead_id, temperature, stale}, …]` | count + optional table |
| `GET /api/v1/leads/{id}/prediction` | `conversion_probability`, `temperature`, `expected_closure_days`, `confidence` | copilot panel |

**Additive (optional BE):** `"disclaimer": "Heuristic estimate (not a trained model)"`, `"currency": "INR"`.  
**FE must show disclaimer even if BE omits field.**  
**No cross-tenant admin forecast.**  
**Latency:** soft aspirational &lt;200ms — not a release blocker.

---

## 2. Graph neighborhood — FROZEN (new)

### `GET /api/v1/graph/neighborhood?lead_id={id}&limit=25`

| | |
|---|---|
| Auth | JWT |
| Query | `lead_id` **required** · `limit` default 25 max 50 (similar leads) |
| Errors | `404` lead not owned · `401` |
| Down | HTTP 200 + `available: false` + empty arrays |

```json
{
  "status": "success",
  "available": true,
  "lead_id": 123,
  "data": {
    "nodes": [
      {
        "id": "lead:123",
        "label": "Lead",
        "properties": {
          "name": "…",
          "score": 82,
          "temperature": "Hot",
          "lead_id": 123
        },
        "val": 24,
        "color": "#ef4444"
      },
      {
        "id": "agent:Jane",
        "label": "Agent",
        "properties": { "name": "Jane" },
        "val": 18,
        "color": "#8b5cf6"
      },
      {
        "id": "lead:456",
        "label": "Lead",
        "properties": { "name": "…", "score": 60, "temperature": "Warm", "lead_id": 456 },
        "val": 16,
        "color": "#f59e0b"
      }
    ],
    "edges": [
      { "source": "lead:123", "target": "agent:Jane", "type": "ASSIGNED_TO", "properties": {} },
      { "source": "lead:123", "target": "lead:456", "type": "SIMILAR_TO", "properties": { "strength": 0.72 } }
    ]
  },
  "ai_summary": "Ego network: center lead, assigned agent, and similar leads."
}
```

**MVP labels:** `Lead`, `Agent` only (required).  
**Stretch (if time):** `Unit` + `INTERESTED_IN` from PG inventory match — not required for G5.  
**Colors (defaults):** Hot `#ef4444` · Warm `#f59e0b` · Cold `#3b82f6` · Agent `#8b5cf6`.  
**ai_summary:** static string OK (Q5.7).  
**Realtime:** FE refetches on SSE `lead.scored` | `lead.assigned` | `lead.hot` for that lead.  
**Embed:** Sales Copilot lead detail (primary). Full `/knowledge-graph` page optional consumer of same API (may require lead selector).

**Keep:** existing `GET /graph/leads/{id}/context` for LLM path — do not break.

---

## 3. Digital twin layout — FROZEN (new)

### `GET /api/v1/inventory/twin`

| | |
|---|---|
| Auth | JWT |
| Query | none for single-project MVP (ignore unknown `project_id` or accept if matches sole project) |
| Errors | `401` · empty inventory → 200 empty towers |

```json
{
  "status": "success",
  "disclaimer": "Demo inventory layout",
  "project": {
    "id": "prj:the-summit",
    "name": "The Summit",
    "location": "Downtown"
  },
  "towers": [
    {
      "id": "tw:tower-a",
      "name": "Tower A",
      "floors": [
        {
          "level": 1,
          "units": [
            {
              "id": "unit:12",
              "unit_number": "A-101",
              "status": "available",
              "price": 15000000,
              "currency": "INR",
              "bhk": "3",
              "lead_id": null
            }
          ]
        }
      ]
    }
  ],
  "counts": { "available": 20, "hold": 8, "sold": 12 }
}
```

**Status enum:** `available` | `hold` | `sold` (lowercase in API; FE may title-case).  
**Seed target:** 1 project, 2 towers, 10 floors, 40 units.  
**FE:** read-only; poll **30s**; hide/filter sold per existing UX; max render 500 units.  
**Price display:** ₹ / Cr consistent with forecasts.

**Keep:** `GET /predictions/inventory` counts for dashboard chips.

---

## 4. SSE / timeline — FROZEN (existing; auth policy)

| Route | Auth for FE |
|---|---|
| `GET /api/v1/events/stream` | **JWT cookie only** in shipped FE (api_key allowed server-side/dev tools) |
| `GET /api/v1/events/leads/{id}/timeline` | JWT · selected lead id (never hard-code `1`) |

Heartbeat `: ping` — ignore in client. Reconnect with backoff.

---

## 5. HubSpot — CONDITIONAL (outbound only)

| Mode | Contract |
|---|---|
| Outbound live | No new public REST; EE `update_crm` + `crm_sync` when `FEATURE_HUBSPOT_LIVE` + real `CRM_API_*` |
| Bi-di | **Out of 4.0** — no `/webhook/hubspot` |
| Identity | Match/update by email + phone (Q2.6) |
| DLQ | `hubspot_crm` + `dlq_replay.py` |

Field map (unchanged ACK): firstname, phone, budget, location, intent, property_type, visit_date, assignee, budget_alignment_status, urgency_level, engagement_score, lead_temperature.

---

## 6. Feature flags

| Env | Default | Effect |
|---|---|---|
| `FEATURE_GRAPH_VIZ` | `true` in staging | If false, neighborhood returns `available:false` or FE hides panel |
| `FEATURE_TWIN_LIVE` | `true` in staging | If false, twin page uses empty/mock banner |
| `FEATURE_HUBSPOT_LIVE` | `false` until key | If false, keep demo stub behavior |

---

## 7. Smoke

```powershell
# Preview NBA
curl -X POST "http://localhost:8000/api/v1/leads/1/sales-ai" -H "Authorization: Bearer <jwt>" -H "Content-Type: application/json" -d "{\"mode\":\"preview\"}"

# Execute NBA
curl -X POST "http://localhost:8000/api/v1/leads/1/sales-ai" -H "Authorization: Bearer <jwt>" -H "Content-Type: application/json" -d "{\"mode\":\"execute\"}"

curl "http://localhost:8000/api/v1/predictions/revenue" -H "Authorization: Bearer <jwt>"
curl "http://localhost:8000/api/v1/graph/neighborhood?lead_id=1" -H "Authorization: Bearer <jwt>"
curl "http://localhost:8000/api/v1/inventory/twin" -H "Authorization: Bearer <jwt>"
curl -N "http://localhost:8000/api/v1/events/stream" -H "Cookie: jwt=<token>"
```

After routes land:

```powershell
curl -o plans/phase4/openapi_ireios4.json http://localhost:8000/openapi.json
```
