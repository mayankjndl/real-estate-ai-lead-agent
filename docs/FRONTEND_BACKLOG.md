# Frontend Backlog (Post–Backend IREIOS 3.0 + G3 → IREIOS 4.0)

Backend Waves A–D / Gate G3 are **code-complete**. FE cutover under **IREIOS 4.0** (`plans/phase4/`).

**Last reviewed:** 2026-08-13 (Command-Center JWT auth unified BE-side: Bearer **or** cookie on twin/neighborhood/predictions; verify doc `docs/COMMAND_CENTER_VERIFY.md`)  
**Home route:** `/dashboard` · **Freeze:** 2026-08-20 · **Release:** 2026-09-03

---

## Already available from backend

| Endpoint / signal | Auth | Purpose |
|-------------------|------|---------|
| `GET /api/v1/events/stream` | JWT cookie (same-origin rewrite) or api_key | SSE envelopes |
| `GET /api/v1/events/leads/{id}/timeline` | JWT cookie / Bearer | Timeline |
| `POST /api/v1/leads/{id}/sales-ai` | JWT | `{mode: preview\|execute}` |
| `GET /api/v1/predictions/*` | JWT | Heuristic forecasts |
| `GET /api/v1/graph/neighborhood?lead_id=` | JWT | Ego graph |
| `GET /api/v1/inventory/twin` | JWT | Digital twin layout |

Same-origin: Next `rewrites` `/api/v1/:path*` → `NEXT_PUBLIC_API_URL` so browser cookies work.

---

## Progress (Mayank)

| Item | Status | Evidence |
|------|--------|----------|
| Real SSE on command-center dashboard | **Done** | `dashboard-mvp` EventSource `/api/v1/events/stream` + credentials |
| Lead timeline API | **Done** | Selected lead; JWT via rewrite |
| Delete / stop using MockSSE | **Done** | No MockSSE class; mock forecast not sole KPI source |
| Forecast widgets → real predictions API | **Done** | mvp + product dashboard ₹ Cr + disclaimer |
| JWT cookie auth for SSE | **Done** | No hard-coded api_key in `frontend/src` |
| Approvals UI | **Deferred 4.1** | Lead Q7.4 |
| Sales AI button | **Done** | Copilot preview/confirm + Leads table |
| Graph panel | **Done** | Ego embed on copilot + knowledge-graph page |
| Digital Twin live | **Done** | Route **`/digital-twin`** under **command-center** (sidebar “Digital Twin”) — **not** on product `/dashboard` nav. API `GET /api/v1/inventory/twin` + 30s poll. Seed: `python seed_twin_demo.py --client-id 1 --clear` (40 units). Empty page = no inventory for JWT tenant, not missing FE. |
| Command-center JWT middleware | **Done** | `proxy.ts` guards CC routes |
| Login home `/dashboard` | **Done** | `auth.ts` redirect |
| **Twin / graph / predictions JWT auth gap** | **Fixed 2026-08-13** | BE unify: `get_current_client` + `get_events_client` accept Bearer **or** cookie `jwt` (`auth.py` helpers `_client_from_jwt_token` / `resolve_jwt_from_request`). Twin (cookie fetch) no longer 401; neighborhood (Bearer server action) no longer auth-empty; `/predictions/*` cookie works. No FE changes needed. Verify: `docs/COMMAND_CENTER_VERIFY.md` + `tests/test_f4_jwt_auth.py` |

---

## Acceptance (production FE / G5)

- [x] No `secret-client-key-123` in `frontend/src`
- [x] Dashboard SSE without query api_key
- [x] Timeline for selected owned lead
- [x] Forecast widgets from `/predictions/*` + heuristic label
- [x] Sales AI preview+confirm on copilot + leads
- [x] Graph ego (`/knowledge-graph` + copilot embed) + twin live at **`/digital-twin`** (or empty when flag/Neo4j/inventory off) — runtime auth mismatch (cookie vs Bearer) **fixed 2026-08-13** (BE unify; no FE change)
- [x] Full `npm run lint` exit 0 + `tsc --noEmit` clean + `npm run build` exit 0 (resolved 2026-08-11 — 23 errors + 17 warnings cleared per `docs/MAINTENANCE.md` §11.1; command-center tsc errors + Suspense prerender fixed in `4494307`)
- [x] G5 automated demos / API evidence 2026-08-10; WA → SSE live smoke PASS 2026-08-11 (`wa_sse_smoke.py`, both modes)

---

## Out of scope (IREIOS 4.0)

- Approvals UI, HubSpot bi-di UI, twin write-back, LangGraph-in-n8n, new n8n WFs
