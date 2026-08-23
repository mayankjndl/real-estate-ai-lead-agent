# Command Center Verify — local/staging smoke

**Single source for smoke-testing the Command Center** (auth + twin + graph +
sales copilot + predictions) after backend auth or frontend changes.

## Purpose

After any auth/FE change (or before P4-QA freeze), run this page-by-page to
prove the whole Command Center works from the browser with a logged-in JWT.
Automated pytest covers the auth matrix; this doc covers the manual UI passes
plus curl checks.

## Auth model (unified 2026-08-13)

Dashboard JWT = `Authorization: Bearer <jwt>` **or** the HttpOnly `jwt` cookie
on **every** JWT route (including `/inventory/twin` and `/graph/neighborhood`).

| Caller style | How it authenticates | Backend dependency |
|--------------|----------------------|--------------------|
| Browser `fetch` / `EventSource` (`/digital-twin`, `/dashboard-mvp`, SSE, timeline) | `jwt` cookie via Next rewrite (`/api/v1/*`) | `get_current_client` / `get_events_client` → cookie branch |
| Server actions (sales-ai, neighborhood, leads list) | `Authorization: Bearer` directly to `:8000` | `get_current_client` / `get_events_client` → Bearer branch |
| curl / external | `X-API-Key` header or `?api_key=` (events/graph family only) | `get_events_client` → API key branch |

Resolution order:

- `get_current_client` (`auth.py`): Bearer header → cookie `jwt` → **401**
- `get_events_client` (`app/api/events.py`): API key → Bearer → cookie → **401**

Shared decode lives in `auth.py` (`_client_from_jwt_token` + `resolve_jwt_from_request`);
`app/api/events.py` reuses them. No anonymous access: invalid/expired tokens and
inactive clients still get 401.

## Prereqs

| Item | Command |
|------|---------|
| Postgres / Redis / Neo4j / n8n / frontend | `docker compose up -d` |
| Backend | `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (venv) |
| Frontend | `cd frontend && npm run dev` |
| Seed clients | `python seed.py` (`admin@revenueos.com` / `password123`, keys `secret-client-key-123`/`-456`) |
| Seed twin inventory (40 units) | `python seed_twin_demo.py --client-id 1 --clear` |
| Leads + Neo4j | `python seed_dummy_leads.py --count 25 --client-id 1` (projects Neo4j unless `--no-neo4j`); or `python project_leads_to_neo4j.py --client-id 1` |
| Flags (defaults OK) | `FEATURE_TWIN_LIVE=true`, `FEATURE_GRAPH_VIZ=true` |
| Graph check | `GET /api/v1/graph/health` → `"available": true` |

## Route map

| Route | What it proves | API(s) |
|-------|----------------|--------|
| `/dashboard-mvp` | Predictions fetch 200 (not 401) + SSE connects | `/predictions/revenue`, `/cashflow`, `/inventory`, `/cancellation-risk`, `/events/stream` |
| `/ai-chat` | Shell renders (live WhatsApp chat vs mock by env) | — |
| `/digital-twin` | Twin layout renders (no 401), 3D units + counts | `/inventory/twin` |
| `/knowledge-graph` | Lead list + ego neighborhood for selected lead | `/graph/neighborhood`, `/leads` |
| `/sales-copilot` | Sales AI preview + timeline + ego panel | `/leads/{id}/sales-ai`, `/events/leads/{id}/timeline`, `/graph/neighborhood` |

## Step-by-step manual checklist

Prereqs up + logged in (JWT cookie set).

| # | Check | Pass criteria |
|---|-------|----------------|
| 1 | Login → `/dashboard` | Product shell loads |
| 2 | `/digital-twin` | **No 401**; 3D units / counts visible; Network tab twin request **200** |
| 3 | `/knowledge-graph` | Select a lead; **not** auth-empty; ≥1 center node when lead in PG + graph available |
| 4 | `/sales-copilot` | Timeline loads; ego panel not auth-empty; **Get recommendation** (preview); Confirm (execute) optional |
| 5 | `/dashboard-mvp` | Predictions fetch **200** (not 401); SSE `data:` frames arrive |
| 6 | `/leads` → Sales AI modal | Preview modal still works |
| 7 | Curl Bearer (twin) | `curl -H "Authorization: Bearer $JWT" http://localhost:8000/api/v1/inventory/twin` → **200** |
| 8 | Curl cookie (twin) | `curl -H "Cookie: jwt=$JWT" http://localhost:8000/api/v1/inventory/twin` → **200** |
| 9 | Curl graph Bearer | `curl -H "Authorization: Bearer $JWT" "http://localhost:8000/api/v1/graph/neighborhood?lead_id=<id>"` → **200**, `available` true if Neo4j up |
| 10 | No auth | Same endpoints without any credential → **401** |

Get a JWT: `curl -X POST http://localhost:8000/api/v1/auth/login -d "username=admin@revenueos.com&password=password123"` → `access_token`.

## Automated

```powershell
pytest tests/test_f4_jwt_auth.py tests/test_f4_twin.py tests/test_f4_graph_neighborhood.py tests/test_f4_sales_ai.py -q
```

Coverage: Bearer + cookie + no-auth on `get_current_client` (twin), API key +
Bearer + cookie + no-auth on `get_events_client` (neighborhood), helper unit
tests. Full suite: `pytest tests/ -q` (441 passed / 4 skipped as of 2026-08-14).

## Failure matrix

| Symptom | Cause | Fix |
|---------|-------|-----|
| **401** on any CC route | Auth failure (bad/expired JWT, wrong client, inactive tenant) | Re-login; check `JWT_SECRET_KEY` stable; check tenant id matches seeded client |
| Twin 200 but **empty** | No `InventoryUnit` rows for the logged-in client | `python seed_twin_demo.py --client-id 1 --clear`; login as client 1 |
| Graph **empty + `available:false`** | Neo4j down / `FEATURE_GRAPH_VIZ=false` | `docker compose up -d neo4j`; flag true; `/api/v1/graph/health` |
| Graph **`available:true` + 1 center node only** | Sparse ego (no relationships) — **not an auth failure** | Normal for raw nodes; optional `python project_leads_to_neo4j.py` backfill |
| Predictions **500** (not 401) | Service/DB error (auth already passed) | Check backend logs; DB up |
| SSE no frames | Bus down (`503`) | `GET /api/v1/events/stream` with key; check Redis |

## Sales AI behavior

- **preview** (default): fresh `score_lead` + NBA; **does not write DB**. Modal
  shows computed % and **“Stored in DB: X%”** if different. May show `proposed_stage`.
- **execute**: writes scores/assignee/stage (policy) + EventLog + NBA AE.
  Modal: **“Stored was X% → now Y%”** (X = Postgres before Confirm).
- **Scoring (UX)**: same **floors as chat** (full qualify ≥88, visit ≥82);
  **does not drop** a higher stored conversion while the lead stays complete
  (no more surprise 95→80 on Confirm). Incomplete leads still recompute low.
- **`send_brochure`**: AE `send_whatsapp`; **10 min Redis debounce** per lead.
  **`TEST_MODE=true`**: no real Twilio — amber banner + delivery note.
- Twin hover: screen-stable **Html** label (no `distanceFactor` shrink).
- NBA: **Closed Won/Lost → `deal_closed`** (no AE); missing fields →
  `request_info`; hot → `escalate_hot`; visit → `schedule_site_visit`;
  warm+assigned → `send_brochure`; else nurture/assign.
- Timeline **orange** `!` on `lead.hot` = hot alert styling (not an error).

## UI smoke (post 2026-08-13 UX batch)

| Check | Pass |
|-------|------|
| Twin hover | **drei `Html` on mesh** (`transform` + `sprite`, `distanceFactor={4}`) — card sits on the unit; CSS 14/13px, readable at default zoom |
| Graph hover | Label shows name, phone, temp, score, location |
| Graph fit | One `zoomToFit` per graph identity; **click = select only** (no `centerAt`/`zoom`); `minZoom`/`maxZoom` clamp |
| Graph click panel | Styled fields (not raw JSON) |
| Sales AI Confirm | Modal stays open; **Actions Executed**; stage before→after; scores unchanged note; dropdown/timeline/graph refresh |
| Timeline filters | system/ai/comms include hot, negotiation, handoff, sales_ai, scored |
| Sync | Same `lead_id` in URL, dropdown, ego graph, timeline after switch |

## CC surface sync

1. Changing lead on KG or copilot updates graph + timeline + `?lead_id=`  
2. “Open in Sales Copilot” preserves `lead_id`  
3. After Sales AI execute: options reload (temp/stage in label); timeline/graph refetch  
4. SSE still refetches graph/timeline on `lead.scored` / `lead.assigned` / `lead.hot`

## Refs

- `auth.py` — `_client_from_jwt_token`, `resolve_jwt_from_request`, `get_current_client`
- `app/api/events.py` — `get_events_client`
- `app/api/inventory.py` — `/inventory/twin`
- `app/knowledge_graph/graph_api.py` — `/graph/neighborhood`
- `app/api/predictions.py` — `/predictions/*`
- `frontend/src/app/(command-center)/` — digital-twin, knowledge-graph, sales-copilot, dashboard-mvp, ai-chat pages
