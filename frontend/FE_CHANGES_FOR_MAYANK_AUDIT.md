# Frontend Changes for Mayank — Audit Handoff

**Audience:** Mayank (frontend owner)
**Branch:** `post_automation_fixes` → PR into `main`
**Author of these changes:** Macmill-340
**Companion docs:** `docs/COMMAND_CENTER_VERIFY.md` (smoke/auth matrix) · `plans/phase4/HANDOFF_MAYANK_PIYUSH.md` (eng freeze handoff)

This doc summarizes every recent frontend change shipped on this branch, flags the
known issues and sync risks found during the Command Center polish pass, and lists the
sections worth auditing before release (P4-QA freeze 2026-08-20, release 2026-09-03).

---

## 1. Recent frontend commits (file-level)

| Commit | What changed (FE) |
|---|---|
| `2765de7` | **Phase 4 FE cutover.** New `(command-center)` route group: `sales-copilot`, `knowledge-graph`, `digital-twin`, `dashboard-mvp`, `ai-chat`; server actions; store. |
| `87c76dd` | **Sales AI secured.** `sales-copilot/actions.ts` — `runSalesAi` moved to a JWT server action (`Authorization: Bearer <jwt cookie>`), no public API exposure. |
| `1ba81fd` | **Sales AI preview mapping.** Fixed nested-property mapping in the preview modal (`recommendation`, `scores`, `assigned_agent`). |
| `8b4b3bf` | **Confidence source.** Preview modal uses `conversion_probability` (not `confidence_score`) for the Conversion widget. |
| `4494307` | **Build hygiene.** ESLint + `tsc` exit 0, fixed `NEXT_PUBLIC_API_URL` build-env handling, graph page moved off prerender (client-only). |
| `127920e` | **Command Center UX batch (biggest FE commit).** See §2. Also gated terminal NBA on the backend (`sales_agent.py`: closed/deal-lost leads get no outbound actions). |
| `9b9e3f7` | **Auth unify.** All JWT routes accept Bearer **or** the `jwt` HttpOnly cookie (twin/neighborhood included). |
| `19b35e0` | **Cleanup.** Deleted dead FE files: `src/lib/api/mockGraphService.ts`, `mockTimelineService.ts`, 5 unused SVGs (`public/{next,vercel,file,globe,window}.svg`), one-time scaffold scripts, stale FE docs. |

`127920e` files: `digital-twin/page.tsx`, `knowledge-graph/GraphWrapper.tsx`,
`knowledge-graph/page.tsx`, `sales-copilot/page.tsx`, `sales-copilot/actions.ts`,
`components/SalesAiModal.tsx` (+ backend `agent.py`, `sales_agent.py`,
`whatsapp_agent.py`, `graph_api.py`).

### 1.1 What `127920e` did (FE detail)

- **Digital twin:** hover labels now use drei `<Html transform sprite>` billboards locked to
  each unit mesh (previously floated/drifted in screen space). Blur mitigation via
  `scale(0.5)` outer × `scale(2)` inner.
- **Knowledge graph:** camera policy in `GraphWrapper.tsx` — click is **selection only**
  (no `centerAt`/`zoom`), one `zoomToFit` per graph fingerprint, `minZoom={0.35}` /
  `maxZoom={4}` clamp. `key={leadId}` remount per lead.
- **Sales AI modal:** before/after score deltas ("Stored was X% → now Y%"), per-action
  status list (`actions_executed`), stage-change hint, `TEST_MODE` banner, no-outbound
  messaging on closed deals.
- **Terminal NBA gating (backend, but UX-visible):** terminal-stage leads render
  "Deal closed — no outbound" in the modal action list.

---

## 2. Known issue — digital twin hover card too small (not fixed)

**Status:** known/conscious — needs Mayank UX pass.

- Anchor: `digital-twin/page.tsx:59-120` — `distanceFactor={4}`, font 14px title / 13px body.
- Symptom: at default `OrbitControls` distance the billboard renders small and the price
  line is hard to read.
- Why it is like this: `distanceFactor` was tuned against blur at far zoom; the
  `scale(0.5)`/`scale(2)` pair is a compensation hack that keeps the DOM card crisp but
  magnifies the sizing problem at default distance.
- Proposed fix (pick one): raise `distanceFactor` to ~6–8 (bigger at default distance,
  slightly blurrier when zoomed out), or bump font to 16px/14px with a wider `minWidth`,
  or replace the compensation scales with a single calibrated transform.

---

## 3. Audit item A — Knowledge-graph: node click shows sparse/empty info panel

**Reported:** a hot lead node, when clicked, shows no details in the bottom-right panel
even though Postgres has the full lead record.

**Verified code behavior:**

- Click → `onNodeClick` → `setSelectedNode(node)` (`knowledge-graph/page.tsx:146`); the
  panel (`knowledge-graph/page.tsx:106-140`) always renders — it cannot "not appear".
  So the symptom is a **sparse card** (dashes), not a missing card.
- The card is fed only by `node.properties`. Backend `/api/v1/graph/neighborhood`
  (`app/knowledge_graph/graph_api.py`) builds three node kinds with different richness:
  1. **Lead node** (`graph_api.py:63` `_lead_node`) — rich: name, phone, location, score,
     temperature, funnel stage, property type. Hot leads here always show full info.
  2. **Agent node** (`graph_api.py:88` `_agent_node`) — **only `{name}`**. Clicking the
     purple assigned-agent node yields "Name: <agent>" and dashes for everything else.
  3. **Graph-only stub** (`graph_api.py:170-185`) — when Neo4j returns a similar lead
     whose PG row misses at query time (race between bus writer and the DB read, or a
     cross-client lead), the node carries only name/score/temperature.

**Most likely causes, in order:**
1. The clicked node was the **assigned-agent node** (looks like a lead at a glance; purple,
   same size) → sparse by design.
2. The clicked node was a **graph-only stub** — Neo4j has the node (and it reads hot)
   but `/neighborhood`'s PG lookup missed the row at that moment.

**Proposed fix:**
- Backend: add `node_type` ("lead" | "agent" | "stub") to every node; enrich the agent
  node with a `role`/`lead_id` hint; for stubs, attempt a PG re-query instead of the
  bare stub.
- FE: card shows a node-type badge and a "No extended data for this node" hint instead
  of silent dashes; for Agent nodes show "Assigned agent" semantics.

---

## 4. Audit item B — Sales Copilot: sync / refresh risks

**B1. SSE live-refresh is narrow and payload-shape dependent.**
`sales-copilot/page.tsx:159-189` — only `lead.scored | lead.assigned | lead.hot` trigger a
graph reload, and the entity match relies on `entity_id || payload.lead_id` matching the
selected `leadId`. Event payload shapes vary per emitter, so a hot-promotion or rescore
can pass silently with no UI refresh.
*Proposed fix:* treat any `lead.*` / `conversation.updated` event whose `lead_id` (or
`entity_id`) equals the selected lead as a refetch trigger; debounce 2–3s.

**B2. Lead-switch mid-execute race.**
`handleConfirm` (`sales-copilot/page.tsx:216-234`) awaits `runSalesAi(leadId, 'execute')`
then reloads timeline/graph/options. If the user switches lead while the request is
in flight, the modal can land a result for the **previous** lead while the page shows the
new one (no abort, no stale-guard).
*Proposed fix:* capture `executedLeadId` at confirm time; on resolve, ignore the result if
`leadId` changed; disable the dropdown while `isExecuting`.

**B3. Stale dropdown metadata.**
`refreshLeadOptions` runs on mount and after Confirm only — temperature/stage badges in
the lead dropdown go stale after live rescore events.
*Proposed fix:* refresh options on `lead.scored` SSE (same debounce as B1).

**B4 — Green before/after deltas inaccurate or one execution late (reported).**
The modal's "Stored was X% → now Y%" / stage-delta lines are computed from
`result.scores_before` vs `result.scores`. In the execute path the backend snapshots
`scores_before`/`stage_before` straight off the request-scoped ORM object **with no fresh
DB read** (`app/agents/sales_agent.py:191-195`; `_preview_sales_ai` does `db.refresh`
at `sales_agent.py:304`, the execute path does not). If the in-memory object is stale
(loaded earlier, or updated by another worker — WhatsAppAgent, SSE, a previous execute),
the displayed delta is wrong and can surface one execution later.
*Proposed fix:* `db.refresh(lead)` (or re-query) immediately before capturing
`scores_before`/`stage_before` in the execute path; keep preview/execute recompute aligned.

---

## 5. Other frontend sections Mayank should audit

- `(command-center)/dashboard-mvp` — widgets vs live analytics; verify JWT cookie path.
- `(command-center)/ai-chat` — chat-only page, check against `FEATURE_WHATSAPP_V3`.
- `(dashboard)/` group — `dashboard`, `leads` (KanbanBoard + negotiation badge),
  `crm`, `settings` — untouched by this branch; flag anything broken by the auth unify
  (`9b9e3f7`) or the mock-service removals (`19b35e0`).
- Auth: `src/lib/auth.ts` (HttpOnly `jwt` cookie), `src/proxy.ts` middleware guards.
- **Not in PR (intentionally untracked):** `session-ses_0052.md`, `explanations/`,
  `reports/`, `Aritro_Internship_Resume_Section.md`, `Maitri_Internship_Resume_Section.md`.

---

## 6. Verification baselines (already green on this branch)

- `pytest tests/test_f4_sales_ai.py tests/test_f4_graph_neighborhood.py tests/test_f4_twin.py tests/test_f4_hubspot_flag.py -v` → **441 passed / 4 skipped**.
- `cd frontend && npm run lint` → exit 0 · `tsc` → exit 0 · `npm run build` → exit 0.
- Smoke matrix: `docs/COMMAND_CENTER_VERIFY.md` (auth on twin/neighborhood via Bearer and cookie).