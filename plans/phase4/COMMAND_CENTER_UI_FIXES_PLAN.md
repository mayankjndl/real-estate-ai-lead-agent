# Command Center UI/UX Fixes Plan

**Date:** 2026-08-13  
**Status:** Implemented — auth `9b9e3f7` (2026-08-13); UI batch `127920e` (2026-08-14)  
**Branch:** `post_automation_fixes`

---

## Issue 1 — Digital Twin: hover tooltip appears at fixed position, not next to unit

**Problem**: Tooltip at `top-6 right-[350px]` is fixed near the "Live twin" badge, not near the hovered unit.

**Root cause**: `digital-twin/page.tsx` used a DOM overlay (`absolute top-6 right-[350px]`), then cursor-follow math (`clientX`/`clientY`) — both unreliable in WebGL/OrbitControls space (tip landed far from the block).

**Fix (FE only) — shipped `127920e`**:
- **drei `Html` child of the unit mesh** (`transform` + `sprite` + `distanceFactor={4}`) — HTML billboard projects in 3D and rides the block, no DOM cursor math
- Compact card (CSS 14/13px) sits just above the unit (`y: 0.55`)
- Click-to-select side panel unchanged

**File**: `frontend/src/app/(command-center)/digital-twin/page.tsx`

---

## Issue 2 — Knowledge Graph: nodes show only "Lead: Lead 33", no useful details

**Problem**: `GraphWrapper.tsx:44` tooltip = `${node.label}: ${node.properties?.name}` — name is generic fallback ("Lead 33"). No phone, temperature, score, or location shown.

**Fix (BE + FE)**:
- **BE** (`graph_api.py`): enrich `_lead_node` properties to include `phone`, `location` (already has temp/score)
- **FE** (`GraphWrapper.tsx`): change `nodeLabel` to return HTML string with rich info — name, phone, temperature badge, score, location
- **FE** (`knowledge-graph/page.tsx`): format `selectedNode` panel (line 106-125) as styled card instead of raw `JSON.stringify`

**Files**: `app/knowledge_graph/graph_api.py`, `frontend/src/app/(command-center)/knowledge-graph/GraphWrapper.tsx`, `frontend/src/app/(command-center)/knowledge-graph/page.tsx`

---

## Issue 3 — Sales AI: "Confirm & Apply" only changes funnel stage, no visible side effects

**Problem**: The execute path DOES save scores + trigger AE actions (notify/send brochure/create task), but:
1. The modal doesn't show what was executed
2. Scores look unchanged because `score_lead` is deterministic (same input = same output)
3. The user sees only funnel stage change

**Root cause analysis** (`sales_agent.py:162-183`):
- Execute sets scores via `setattr(lead, k, v)` and commits — scores ARE saved
- `_nba_to_ae_action` fires AE actions (notify_agent, create_task, send_whatsapp) — but results are discarded (fire-and-forget)
- Response includes `scores` dict but modal doesn't refresh lead data

**Fix (BE + FE)**:
- **BE** (`sales_agent.py`): collect AE action results from `_nba_to_ae_action` and return `"actions_executed"` in response:
  ```python
  "actions_executed": [{"action": "notify_agent", "status": "ok"}, ...]
  ```
- **FE** (`SalesAiModal.tsx`): add "Actions Executed" section showing what happened after confirm (e.g., "Notified agent", "Task created", "Brochure sent")
- **FE** (`sales-copilot/page.tsx`): after execute, reload lead options to reflect any DB changes

**Files**: `app/agents/sales_agent.py`, `frontend/src/components/SalesAiModal.tsx`, `frontend/src/app/(command-center)/sales-copilot/page.tsx`

---

## Issue 4 — Timeline missing hot lead/negotiation/handoff events

**Problem**: Timeline reads from `EventLog` table (`events.py:166-189`). Most important bus events are published to Redis Streams but never written to `EventLog`:

| Event | Written to EventLog? | Where |
|-------|---------------------|-------|
| `tracking` (message_sent, qualified) | Yes | `agent.py:291` |
| `audit` (assignment changes) | Yes | `agent.py:856,1520`, `sales_agent.py:169` |
| `tracking` (lead_created) | Yes | `main.py:969` |
| `audit` (manual stage changes) | Yes | `main.py:1721` |
| `lead.hot` | **No** — bus only | `agent.py:1529` |
| `lead.scored` | **No** — bus only | `agent.py:1510` |
| `lead.assigned` | **No** — bus only | various |
| `lead.negotiation.started` | **No** — bus only | `negotiation_agent.py` |
| `lead.escalated` | **No** — bus only | `lead_hot.py` |
| `site_visit.scheduled` | **No** — bus only | AE executor |
| `followup.sent` | **No** — bus only | `follow_up.py` |

**Fix (BE)**: Write key events to EventLog:
- `sales_agent.py` execute path: log `lead.scored`, `lead.assigned`, NBA action events
- `agent.py` hot threshold: log `lead.hot` alongside existing notification
- `agent.py` human handoff: log `lead.handoff` alongside existing audit
- `main.py` `_emit_turn_events`: log `lead.created`, `conversation.updated`, `lead.qualified`
- `follow_up.py` / `followup_scheduler.py`: log `followup.sent`

**Files**: `app/agents/sales_agent.py`, `agent.py`, `main.py`, `follow_up.py`, `app/workflows/followup_scheduler.py`

---

## Issue 5 — Timeline filter doesn't recognize new event types

**Problem**: FE filter (line 219-232) only matches limited event types. Missing coverage for: `lead.hot`, `lead.negotiation`, `lead.handoff`, `lead.assigned`, `followup`, `lead.scored`.

**Current filter logic**:
```javascript
if (filter === 'communications') return e.type.includes('whatsapp') || e.type.includes('email') || e.type.includes('call');
if (filter === 'payments') return e.type === 'payment.received';
if (filter === 'system') return e.type === 'system.alert' || e.type === 'site_visit.scheduled' || e.type === 'lead.created';
if (filter === 'ai') return e.type === 'ai.insight' || e.type.includes('scored');
```

**Fix (FE)**: Expand filter categories and icon/background mappings:
- `system` filter: add `lead.hot`, `lead.assigned`, `lead.handoff`, `lead.created`, `site_visit.scheduled`
- `ai` filter: add `lead.scored`, `lead.qualified`
- Add new icon/background for `lead.hot` (red), `lead.negotiation` (amber), `lead.handoff` (purple)
- Add `negotiation` filter category or fold into `ai`

**File**: `frontend/src/app/(command-center)/sales-copilot/page.tsx`

---

## Implementation Order

| Step | What | Files | Risk |
|------|------|-------|------|
| 1 | Twin tooltip follows cursor | `digital-twin/page.tsx` | Low (FE only) |
| 2 | Graph node tooltip enrichment | `graph_api.py`, `GraphWrapper.tsx`, `knowledge-graph/page.tsx` | Low |
| 3 | Sales AI execute returns action results | `sales_agent.py`, `SalesAiModal.tsx`, `sales-copilot/page.tsx` | Medium (BE schema change) |
| 4 | Write key events to EventLog | `sales_agent.py`, `agent.py`, `main.py`, `follow_up.py`, `followup_scheduler.py` | Medium (data volume) |
| 5 | Timeline filter + display improvements | `sales-copilot/page.tsx` | Low (FE only) |

## Verification

- Manual: hover twin units → tooltip follows cursor; hover graph nodes → shows name/phone/temp/score; sales AI execute → modal shows actions; timeline → shows hot/negotiation/handoff events
- `cd frontend && npm run lint` (FE lint)
- `pytest tests/test_f4_*.py -q` (backend regression)
