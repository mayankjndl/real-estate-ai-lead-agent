# IREIOS 4.0 — Architecture delta (locked)

| This doc owns | Does not own |
|---|---|
| New/changed layers for Product Phase 4 | Full 3.0 diagrams → `../phase3/IREIOS_3.0_Architecture_Diagrams.md` |

**Spine (unchanged):**

```text
Event → CEO → Agent/Workflow → Automation Engine → Execution Engine → Event
```

n8n remains ops side-plane via `n8n_bridge` — **no new workflows in 4.0** (Q4.2).

---

## 1. Unchanged (do not re-litigate)

Event bus, CEO, AE, EE, SalesAgent bus NBA, Neo4j writers + context API, heuristic predictions, CRM outbound path, marketing/CS agents, SSE stream/timeline.

---

## 2. Deltas

### 2.1 Sales AI HTTP preview/execute

```text
FE Confirm flow
  POST /sales-ai {mode:preview}  → compute only → UI
  POST /sales-ai {mode:execute} → run_sales_ai + AE side effects → UI refresh
Bus path (lead.scored/hot/…) → unchanged auto execute
```

### 2.2 Graph neighborhood

```text
Sales Copilot embed
  → GET /api/v1/graph/neighborhood?lead_id=
  → Neo4j similar + agent (+ optional PG units stretch)
  → {nodes, edges}
  → SSE lead.* → refetch
```

### 2.3 Twin layout

```text
Digital Twin page
  → GET /api/v1/inventory/twin
  → Postgres InventoryUnit grouped project/tower/floor/unit
  → R3F read-only · poll 30s
```

### 2.4 HubSpot

Outbound only when flagged live. No inbound webhook node in 4.0 architecture.

### 2.5 FE auth

Command-center routes JWT-guarded like product dashboard. Browser EventSource uses cookie, not query api_key.

---

## 3. Event catalog

**No new event types required for 4.0 MVP.**

Optional later (not MVP): `sales.nba.executed` for timeline audit — only if execute path needs explicit bus publish; can log `EventLog` instead.

---

## 4. Diagram

```text
WhatsApp/Twilio → FastAPI agents (3.0)
        │
        ▼ bus
   CEO → agents → AE → EE ──► Twilio / CRM / Calendar / Tasks
        │
        ├── Neo4j ◄── neighborhood read (new)
        ├── PG InventoryUnit ──► twin read (new)
        └── predictions read (existing)

Next.js
  /dashboard          KPIs + forecast (live)
  /leads              Sales AI button (2nd)
  /sales-copilot      Sales AI preview/confirm + graph embed + timeline
  /digital-twin       twin API
  /dashboard-mvp      forecast + SSE pulse
```

---

## 5. Rejected

| Idea | Reason |
|---|---|
| LangGraph NBA in n8n | Lead F9 amend + hard rules |
| Full Project/Tower/Comm force-graph | Q5.1 ego only |
| Twin write-back / holds from UI | Q6.4 read-only |
| HubSpot inbound | Q2.8 → 4.1 |
| Approvals UI | Q7.4 → 4.1 |
