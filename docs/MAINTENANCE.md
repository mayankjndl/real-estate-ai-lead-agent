# IREIOS — End-to-End Maintenance Guide

Operational runbook for the **current** codebase (FastAPI monolith + IREIOS 3.0 bus/agents/KG).  
Companion to `AGENTS.md` (agent-oriented facts), `plans/phase3/IREIOS_3.0_EVIDENCE_PACK.md` (3.0 release gates), and `plans/phase4/` (active Product Phase 4 queue).

**Last aligned:** July 2026 · Branch baseline: post–Phase 10 / BD closeout

---

## 1. System map (what you are maintaining)

```text
                    ┌──────────── Docker ────────────┐
Twilio/Web ──► FastAPI (main.py)                     │
                 │  PostgreSQL  ◄── source of truth  │
                 │  Redis Streams (event bus)        │
                 │  Neo4j (projected graph, optional)│
                 │  FAISS RAG (in-process / files)   │
                 ▼                                   │
            CEO → Agents/Workflows → AE → EE         │
                 │                                   │
                 ▼                                   │
         WhatsApp / CRM / Calendar / Notify          │
                    └────────────────────────────────┘
Frontend (Next.js) ── JWT cookie ──► /api/v1/*
```

| Store | Role | Lose it? |
|-------|------|----------|
| **PostgreSQL** | Leads, sessions, messages, approvals, DLQ, memory, clients | **Catastrophic** — restore from backup |
| **Redis** | Session locks, interim dedupe, **event bus stream** | Bus lag / lost unacked events; app mostly recovers |
| **Neo4j** | Lead/agent graph projection | **Safe** — rebuild via `project_leads_to_neo4j.py` |
| **FAISS / RAG files** | Property retrieval | Rebuild on next RAG init / reindex path |
| **`.env`** | Secrets & feature flags | Redeploy broken until restored |

---

## 2. Local day-2 startup

```powershell
# 1) Infra
docker compose up -d

# 2) Python env (uv or venv)
.\.venv\Scripts\Activate.ps1
# Prefer lock for reproducibility:
pip install -r requirements.lock
# Or fresh from directs: pip install -r requirements.txt  then  pip freeze > requirements.lock

# 3) Clients + agents
python seed.py

# 4) API
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 5) Optional frontend
cd frontend; npm run dev
```

**Smoke:**

| Check | Expect |
|-------|--------|
| `GET http://localhost:8000/health` | 200 |
| Uvicorn log | `EventBus started`, executors registered, agents registered, `Application startup complete` |
| Neo4j configured | `Neo4j schema v1 applied` (idempotent “already exists” INFO is OK) |
| `GET /api/v1/graph/health` | `available: true` when `NEO4J_*` set |

---

## 3. Environment & feature flags

| Flag | Dev default | Prod go-live |
|------|-------------|--------------|
| `IS_PRODUCTION` | `false` | `true` |
| `TEST_MODE` | `true` | `false` |
| `FOLLOW_UP_TEST_MODE` | `true` | `false` |
| `FOLLOW_UP_DLQ_TEST` | off | **must be false** |
| `FEATURE_WHATSAPP_V3` | `true` | `true` |
| `FOLLOWUP_ENGINE` | `v3` | `v3` (`legacy` = emergency only) |
| `NEO4J_URI` | `bolt://localhost:7687` | real or empty (no-op graph) |
| `N8N_*` | `http://localhost:5678` + webhook secret when `docker compose up -d n8n` | real host + secret; empty = `n8n_not_configured`. **Workflow still required** in UI or AE gets `n8n_http_404` |
| `GOOGLE_CALENDAR_*` | path with **forward slashes** on Windows (`D:/…/sa.json`) | SA must have calendar shared; empty = stub `visit_*` |
| `BROCHURE_MEDIA_URL` / `FLOORPLAN_*` | empty = text fallback (**incomplete** for PDF bubble) | public HTTPS only |
| `GOOGLE_CALENDAR_*` | empty OK | set for real Calendar events (else synthetic `visit_id`) |
| `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` | empty OK | public **HTTPS** PDFs; empty = text fallback |
| `CRM_API_*` | demo default OK | HubSpot skippable; real private-app token for live contacts |

Full lists: `.env.example`, `AGENTS.md` → Config / Expansion env vars.

**Never commit** real Twilio, Gemini, admin, DB passwords, Calendar SA JSON, or personal calendar IDs (keep them in local `.env` only).

---

## 4. PostgreSQL maintenance

### Backup / restore

```powershell
python db_backup.py
python db_restore.py backups\backup_YYYYMMDD_HHMMSS.sql
```

- Run backup before migrations, bulk seeds, or deploys.
- Nightly backup job is scheduled in-app (2am) when scheduler is up — still keep off-box copies in prod.

### Migrations

```powershell
python migrate_db.py
```

Idempotent-ish additive SQL. After pull: migrate → restart uvicorn.

### Useful cleanup (dev)

| Goal | Approach |
|------|----------|
| Reset dummy graph load test | `python seed_dummy_leads.py --purge-only` |
| Soft / hard wipes | §4.1 below (canonical) |
| Full tenant wipe | Postgres **hard** + `seed.py`; or restore from backup |
| DLQ stuck events | `python dlq_replay.py` after fixing root cause |

### Multi-tenant rule

Every query on client data **must** filter `client_id`. Session ids are scoped `{client_id}_…` at the webhook boundary.

### 4.1 Soft / hard wipes (canonical — current schema)

Postgres and Neo4j are **independent**. Truncating Postgres does **not** clear Neo4j.

**Connect PG:** `psql postgresql://realestate:localpass@localhost:5432/realestate_db`  
**Neo4j Browser:** `http://localhost:7474` · bolt `bolt://localhost:7687` · user/pass `neo4j` / `localpass`

#### Postgres — soft (keep `clients` + `agents`)

```sql
TRUNCATE
  messages,
  event_logs,
  dlq_events,
  follow_up_states,
  lead_memories,
  agent_tasks,
  approval_requests,
  agent_learning,
  notification_logs,
  leads,
  sessions,
  webhook_logs
RESTART IDENTITY CASCADE;
```

#### Postgres — hard (wipe tenants too)

```sql
TRUNCATE
  messages,
  event_logs,
  dlq_events,
  follow_up_states,
  lead_memories,
  agent_tasks,
  approval_requests,
  agent_learning,
  notification_logs,
  leads,
  sessions,
  webhook_logs,
  agents,
  clients
RESTART IDENTITY CASCADE;
```

Then: `python seed.py`

#### Neo4j — soft (leads; keep `:SchemaVersion`)

```cypher
MATCH (n:Lead) DETACH DELETE n;
```

Optional orphan cleanup after soft lead delete:

```cypher
MATCH (n:Agent) DETACH DELETE n;
```

#### Neo4j — hard (all nodes except schema marker)

```cypher
MATCH (n) WHERE NOT n:SchemaVersion DETACH DELETE n;
```

#### Fresh WhatsApp retest

| Goal | Commands |
|------|----------|
| Chat/CRM only | Postgres **soft** → send WA |
| Chat + clean graph UI / similar-lead context | Postgres **soft** + Neo4j **soft** → send WA |
| Full local reset | Postgres **hard** + `seed.py` + Neo4j **hard** |

New WA traffic **upserts** into Neo4j; it does **not** remove old dummy nodes left from a prior bulk seed.

---

## 5. Redis & Event Bus

| Item | Detail |
|------|--------|
| Stream key | `EVENT_STREAM_KEY` (default `ireios:events`) |
| Consumer group | `EVENT_CONSUMER_GROUP` (default `ireios-cg`) |
| Runtime | `Event → CEO → Agent/Workflow → AE → EE → Event` |

**Ops tips:**

- Redis down → bus publish fails loud; WhatsApp path may degrade depending on lock fallback.
- After Redis volume wipe: groups recreate on `event_bus.start()`; in-flight PEL is gone.
- Do **not** treat Redis as durable business state; Postgres is.

### SSE smoke (Phase 1b)

```powershell
# Terminal A — tenant-filtered live stream (seed.py key for client 1)
curl -N "http://localhost:8000/api/v1/events/stream?api_key=secret-client-key-123"

# Terminal B — publish without WhatsApp/LLM
python publish_stub_event.py --event-type lead.created --tenant-id Client_1 --payload "{\"name\":\"demo\"}"
```

| Route | Auth | Notes |
|-------|------|--------|
| `GET /api/v1/events/stream` | `?api_key=` / `X-API-Key` **or** `jwt` cookie | `: ping` every 15s; `503` if bus down |
| `GET /api/v1/events/leads/{id}/timeline` | same | From `event_logs`; 404 cross-tenant |
| `POST /api/v1/events/stub` | `X-Admin-Token` = `ADMIN_API_KEY` | Returns `event_id` |

Envelope fields (bus): `event_id`, `event_type`, `tenant_id`, `entity_id`, `source`, `timestamp`, `correlation_id`, `payload`.  
Contracts: `plans/phase3/IREIOS_3.0_API_SSE_CONTRACTS.md`.

#### WhatsApp → SSE smoke (G5 / QA gate)

Full loop proof: Twilio-format POST → WhatsAppAgent (LLM turn) → `_emit_turn_events` → Redis
Streams → CEO agents → tenant SSE stream.

**Prereqs:** docker + uvicorn up, `TEST_MODE=true` (bypasses Twilio signature + skips outbound
sends), `python seed.py` ran. **Revert `TEST_MODE=false` after the smoke.**

Two-command recipe:

```powershell
# Terminal A — watch the tenant stream
curl -N "http://localhost:8000/api/v1/events/stream?api_key=secret-client-key-123"

# Terminal B — send one WhatsApp webhook (13s turn window; LLM reply)
curl -X POST "http://localhost:8000/api/v1/whatsapp" -H "X-API-Key: secret-client-key-123" `
  -F "MessageSid=SMf4smoke01" -F "From=whatsapp:+919000000001" -F "To=whatsapp:+14155238886" `
  -F "Body=Hi, I want a 2BHK in Andheri under 1 crore"
```

Expect on the stream: `whatsapp.received` → (`lead.created` only for **new** leads) →
`conversation.updated` → `lead.crm_synced` → `lead.scored`, each arriving ≤~2s after publish.

One-shot script (same checks + timing + exit code, stdlib only):

```powershell
python wa_sse_smoke.py              # existing lead (reuses From number)
python wa_sse_smoke.py --new-lead   # unique From → forces lead.created path
```

**Result log (2026-08-11, live local stack):** turn 4.9–11.3s (LLM-bound, within 13s);
SSE publish→delivery 10–2183ms across both modes — PASS.

Troubleshooting:
- SSE `503 Event bus not available` → bus consumer loop died (Redis blip). Restart uvicorn (or
  touch `main.py` with `--reload`); verify via `docker exec redis-local redis-cli XLEN ireios:events`.
- Webhook `403` → `TEST_MODE` not true in the running process; set + restart uvicorn.
- Gemini quota / missing key → turn fails before events are emitted.

---

## 6. Neo4j maintenance

### Model (current)

- **Postgres = source of truth** for leads.
- Neo4j = **async projection** (`kg_event_writer` on bus) + WhatsApp pre/post-turn upsert + optional batch project.
- Similarity today: same `client_id` + same `location` string (not vector layout in Browser).
- Local: `NEO4J_URI=bolt://localhost:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=localpass` (see `.env.example`).

### Health

```text
GET http://localhost:8000/api/v1/graph/health
GET /api/v1/graph/leads/{id}/context   # tenant-scoped
```

Browser (`http://localhost:7474`): use filtered Cypher only:

```cypher
MATCH (l:Lead {client_id: 1}) RETURN count(l);
MATCH (l:Lead {client_id: 1, location: 'Baner'}) RETURN l LIMIT 25;
MATCH (l:Lead)-[:ASSIGNED_TO]->(a:Agent) WHERE l.client_id = 1 RETURN l, a LIMIT 50;
```

**Avoid** `MATCH (n) RETURN n` on large graphs — Browser will choke; the DB may still be fine.

### Rebuild projection from Postgres

```powershell
python project_leads_to_neo4j.py
python project_leads_to_neo4j.py --client-id 1 --source dummy_seed
python project_leads_to_neo4j.py --dry-run
```

Use after: Neo4j volume reset, schema change, bulk SQL seed without bus events. Wipes: §4.1.

### Schema

Lifespan runs `neo4j_client.migrate_schema()` (idempotent). INFO notifications “constraint already exists” are **normal**.

### Scale notes

| Leads | Engine | Browser “show all” | App similar-lead query |
|------:|--------|--------------------|-------------------------|
| ≤1k–10k | Easy | OK if filtered | Fine |
| 100k+ | Fine with indexes | Never global draw | Keep `client_id` + indexed props |
| 1M+ | Capacity planning | App ego-graphs only | Cache context; archive cold nodes |

Indexes already cover lead key, `client_id`, `location`. Later: shared `:Location` nodes, Redis cache on `get_lead_context`, CDC if write volume explodes.

### WhatsApp path (ops awareness)

Graph context is **LLM-only** (not sent as a WhatsApp bubble):

```text
Knowledge graph signal: N similar prior lead(s) in graph near Baner (2BHK). …
```

If Neo4j is down, chat continues with empty context.

---

## 7. Dummy data load (dev / graph demos)

```powershell
# 1000 full leads → Postgres + Neo4j (client 1). source=dummy_seed
python seed_dummy_leads.py

python seed_dummy_leads.py --count 100 --client-id 1
python seed_dummy_leads.py --no-neo4j
python seed_dummy_leads.py --purge-only
```

- Requires `python seed.py` clients first.
- Does **not** create 1000 follow-up scheduler storms by default (no FollowUpState rows).
- Purge before re-seed is default (idempotent dev loop).

---

## 8. Application processes & scheduler

| Job | When | Notes |
|-----|------|--------|
| `dispatch_followups` | ~1 min | `FOLLOWUP_ENGINE=v3` → AE→WhatsAppExecutor |
| `backup_postgres` | 2am | Local backup helper |
| `daily_cleanup_job` | 3am | Retention-style cleanup |
| `escalation_cron_job` | ~1 min | Hot lead manager/director |
| `crm_resync_job` | ~5 min | Debounced CRM field push |
| `competitor_monitor_job` | 01:00 | No-op if `COMPETITOR_KEYWORDS` empty |
| `weekly_marketing_report` | Mon 08:00 | Publishes `cron.weekly_report` per active client |
| `expire_approvals` | ~15 min | Marks stale HITL `approval_requests` expired |

Restart uvicorn to pick up code; scheduler lives in the API process (not a separate worker today).

---

## 9. Integrations checklist

| Integration | Config | Failure mode |
|-------------|--------|--------------|
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` | Chat fails / quota errors |
| Twilio WA | `TWILIO_*`; `TEST_MODE` skips send | DLQ / logs |
| HubSpot CRM | `CRM_API_URL` + key; else demo stub (skippable) | DLQ `hubspot_crm` |
| Neo4j | `NEO4J_*` | Graph no-op |
| n8n | `N8N_*` | `n8n_not_configured` (code path shipped; instance ops-pending) |
| Google Calendar | `GOOGLE_CALENDAR_*` set → real events; empty → synthetic `visit_id` stub |
| Brochure / floor plan PDF | `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` (public **HTTPS**) | Text-only fallback when empty |
| Stripe | webhook + keys | Billing routes only |
| AWS secrets | optional boto path in `config` | Falls back to env |

### Brochure / floor plan media (Approach B)

1. Host a lean PDF or image on CDN/S3 (or FastAPI static behind HTTPS tunnel).
2. Set env:
   ```env
   BROCHURE_MEDIA_URL=https://cdn.example.com/brochure.pdf
   FLOORPLAN_MEDIA_URL=https://cdn.example.com/floorplan.pdf
   ```
3. Non-HTTPS URLs are rejected by `resolve_tool_media_url`.
4. Smoke: Twilio sandbox message “send brochure” → caption + document bubble (TwiML `<Media>`). Empty env → plain-text brochure.
5. Sales NBA `send_brochure` also attaches `media_url` when configured (AE path).

DLQ drill:

```powershell
python gate_dlq_drill.py
python dlq_replay.py
```

---

## 10. Testing & gates (before deploy)

```powershell
python -m pytest tests/ -q
python gate_isolation_test.py
python gate_dlq_drill.py
python dlq_replay.py
# Live conversation stress (server up + Gemini quota):
python task3_runner.py
python task3_runner.py --category HOT
```

| Suite | Prefix |
|-------|--------|
| Bug regressions | `tests/test_p*.py` |
| Expansion / IREIOS 3.0 | `tests/test_e*.py` |

Evidence: `plans/phase3/IREIOS_3.0_EVIDENCE_PACK.md`, `python ireios_evidence.py`.

---

## 11. Frontend maintenance

```powershell
cd frontend
npm install
npm run dev
npm run lint
```

- `NEXT_PUBLIC_API_URL` → backend (e.g. `http://localhost:8000`)
- Auth: HttpOnly `jwt` cookie via server login action
- FE SSE: partial cutover (`dashboard-mvp` EventSource); remaining work: `docs/FRONTEND_BACKLOG.md`

### 11.1 Repo-wide lint runbook (ESLint, no TS check)

**Baseline (2026-08-11, pre-freeze):** `23 errors / 17 warnings` — all **pre-existing** (Phase 3
product/public pages); **none** introduced by the Phase 4 FE wave. Freeze 2026-08-20 requires
Exit Code 0, so this is a pre-freeze triage batch (see `plans/phase4/IREIOS_4.0_EVIDENCE_PACK.md`
G5 FE lint item).

**Status (2026-08-11): RESOLVED** — `npm run lint` (ESLint) exits 0 (0 problems, 0 warnings).
All 23 errors + 17 warnings cleared in this batch; fix patterns below kept for reference.
`tsc --noEmit` also clean (3 command-center errors fixed in `4494307`) and
`npm run build` exits 0 (incl. knowledge-graph Suspense prerender fix).

#### Run it

```powershell
cd frontend
npm run lint
```

**Known env gotcha:** on some machines `npm run lint` / `npx eslint` fail with
`'eslint' is not recognized` even though `node_modules\eslint` exists — the
`node_modules\.bin\eslint.cmd` shim is missing. Workaround (no reinstall):

```powershell
node node_modules\eslint\bin\eslint.js .
```

Proper fix (regenerates all `.bin` shims; takes a few minutes):

```powershell
npm install   # or: Remove-Item node_modules -Recurse -Force; npm install
```

#### Error inventory (23 errors — historical, all resolved 2026-08-11)

| Rule | Count | Locations |
|------|-------|-----------|
| `react/no-unescaped-entities` | 11 | `src/app/(public)/privacy/page.tsx:14` ×6, `contact/page.tsx:57`, `demo/page.tsx:24`, `features/page.tsx:39`, `login/page.tsx:72` |
| `@typescript-eslint/no-explicit-any` | 8 | `src/app/(dashboard)/dashboard/Charts.tsx` ×6 (20, 25, 36, 58, 87, 108), `PriorityAlertCard.tsx:8`, `src/lib/auth.ts:10` |
| `react-hooks/set-state-in-effect` | 3 | `src/components/Header.tsx:14`, `src/components/ThemeToggle.tsx:12`, `src/app/(dashboard)/dashboard/OnboardingWalkthrough.tsx:16` |
| `react-hooks/immutability` | 1 | `src/app/(dashboard)/settings/team/page.tsx:41` (`fetchAgents` used before declared) |
| `@typescript-eslint/ban-ts-comment` | 1 | `src/app/(dashboard)/dashboard/ExportReport.tsx:65` (`@ts-ignore` → `@ts-expect-error`) |

#### Warnings (17 — historical, all resolved 2026-08-11)

- Unused imports: `src/app/(dashboard)/layout.tsx:1-2` ×7, `src/app/(public)/page.tsx:1` ×2,
  `features/page.tsx:1`, `pricing/page.tsx:3`, `contact/page.tsx:4` ×2, `crm/page.tsx:1`,
  `src/app/layout.tsx:4` ×1, `src/lib/auth.ts:47`
- `react-hooks/exhaustive-deps`: `src/app/(dashboard)/settings/page.tsx:105`

#### Fix steps (mechanical, no behavior change)

1. **Unescaped entities** — in JSX text replace `'` → `&apos;`, `"` → `&quot;`
   (privacy page quotes → `&quot;`; apostrophes elsewhere → `&apos;`).
2. **Unused imports/warnings** — delete the import (keep the alias where re-exported;
   `layout.tsx` icons are genuinely unused — remove them).
3. **`@ts-ignore` → `@ts-expect-error`** — `ExportReport.tsx:65`, only if the next line
   is expected to error.
4. **`settings/team/page.tsx:41`** — move the `fetchAgents` const above the `useEffect`
   (or wrap in `useCallback` and add to the dep array).
5. **`set-state-in-effect` ×3** — React 19 rule. Patterns:
   - `ThemeToggle.tsx` (`setMounted(true)` in effect): the standard hydration guard —
     replace with `useSyncExternalStore` for theme or move the mounted flag into the
     `useEffect` that paints; simplest compliant option: derive from a lazy initial state
     + skip the mounted gate when not needed.
   - `Header.tsx` (close mobile menu on pathname change): move the reset into the click
     handler / nav effect that changes pathname, or keep state in a keyed component.
   - `OnboardingWalkthrough.tsx` (localStorage read → `setIsOpen`): initialize from the
     storage key with a lazy `useState` initializer instead of reading inside the effect.
   - Add `// eslint-disable-next-line react-hooks/set-state-in-effect` **only** where a
     true hydration guard is required and note why.
6. **`no-explicit-any` (8)** — replace with concrete types:
   - `Charts.tsx`: type recharts `payload`/`props` as `PayloadType`/`TooltipProps` from
     `recharts` instead of `any`.
   - `PriorityAlertCard.tsx:8` and `auth.ts:10`: use `unknown` + narrowing, or an
     interface for the props/server-action return.
7. **Re-verify:**

```powershell
node node_modules\eslint\bin\eslint.js .    # expect 0 problems
git diff --stat                             # confirm only intended files touched
npm run lint                                # also confirms the shim is back
```

**Do not** run this after 2026-08-20 unless the freeze is lifted (bugfix only from QA).
Also note the script is ESLint-only — a `tsc --noEmit` pass is recommended separately
before Vercel build.

---

## 12. Dependency maintenance

| File | Purpose |
|------|---------|
| `requirements.txt` | Direct runtime deps, **unpinned** |
| `requirements.lock` | Full pinned tree for install/deploy (**UTF-8**) |

Refresh lock after changing `.txt`:

```powershell
# clean venv recommended
pip install -r requirements.txt
pip freeze | Out-File -Encoding utf8 requirements.lock
pip check
```

AGENTS.md install command: **`pip install -r requirements.lock`**.

Do not bulk “Optimize Imports” in IDE across `main.py` / lazy import modules without restart smoke — import order can change startup logs and circular-import safety.

---

## 13. Logging, metrics, health

| Endpoint | Auth | Use |
|----------|------|-----|
| `/health` | public | Liveness |
| `/metrics` | public | Prometheus — **firewall in prod** |
| `/docs` | public (dev) | OpenAPI — restrict in prod |

Structured logs use `request_id` / `tenant_id` contextvars when set.

---

## 14. Security maintenance

- Rotate `ADMIN_API_KEY`, client API keys, JWT secret, DB passwords on schedule / incident.
- Production: `TEST_MODE=false`, real Twilio signature validation.
- Never expose admin ROI/global routes to tenant dashboards without JWT + `client_id`.
- `/metrics` and OpenAPI: network policy in production.

---

## 15. Incident cheat sheet

| Symptom | Check |
|---------|--------|
| App won’t start | `.env`, Postgres up, `pip check`, traceback on import |
| EventBus errors | Redis container, `EVENT_STREAM_*` |
| No WA send | `TEST_MODE`, Twilio creds, EE WhatsAppExecutor logs, DLQ |
| CRM not updating | bus `crm_automation`, `crm_sync_status`, DLQ `hubspot_crm` |
| Graph empty | `NEO4J_URI`, `project_leads_to_neo4j.py`, writer logs |
| Wrong tenant data | isolation gate; missing `client_id` filter |
| Double messages | webhook MessageSid / Redis locks (P3) |
| Follow-ups stuck | `FollowUpState`, quiet hours, `FOLLOWUP_ENGINE`, send_retry backoff |
| Gemini 429 | quota; pause `task3_runner`; backoff |

---

## 16. Production deploy checklist

1. `IS_PRODUCTION=true`, all test flags **false**  
2. Real `DATABASE_URL`, Redis, Twilio, Gemini  
3. `pip install -r requirements.lock`  
4. `python migrate_db.py`  
5. Optional: Neo4j + `migrate_schema` via app start  
6. `gate_isolation_test` / DLQ drill against staging  
7. Backup before cutover  
8. Smoke: health, one chat/WA, SSE event, CRM stub/real  
9. Firewall `/metrics`, lock down `/docs`  
10. Monitor logs + DLQ depth first 24h  

---

## 17. Script index

| Script | Purpose |
|--------|---------|
| `seed.py` | Test clients + agents |
| `seed_dummy_leads.py` | Bulk full leads + Neo4j project (`dummy_seed`) |
| `project_leads_to_neo4j.py` | PG → Neo4j backfill anytime |
| `add_client.py` | Production client provisioning |
| `migrate_db.py` | SQL additive migrations |
| `db_backup.py` / `db_restore.py` | DB snapshots |
| `gate_isolation_test.py` | Tenant isolation |
| `gate_dlq_drill.py` / `dlq_replay.py` | DLQ path |
| `task3_runner.py` | Live conversation matrix |
| `publish_stub_event.py` | Bus/SSE demo events |
| `wa_sse_smoke.py` | WhatsApp → SSE live smoke (G5/QA; §5) |
| `ireios_evidence.py` | Architecture evidence dump |
| `dlq_replay.py` | Replay pending DLQ |

---

## 18. Related docs

| Doc | Contents |
|-----|----------|
| `AGENTS.md` | Agent/dev high-signal facts |
| `README.md` | Product overview & setup |
| `docs/TIMEOUTS_AND_TIMINGS.md` | All race/TTL/scheduler/backoff values + code anchors |
| `docs/FRONTEND_BACKLOG.md` | FE SSE/API cutover |
| `docs/N8N_INTEGRATION.md` | n8n config-later |
| `docs/PROD_READINESS_CHECKLIST.md` | Prod readiness: flag matrix, secrets track, infra adoption, integration runbooks |
| FE lint runbook | `docs/MAINTENANCE.md` §11.1 (23e/17w baseline → **resolved 2026-08-11**, exit 0) |
| `plans/phase4/UNIFIED_EXECUTION_ORDER.md` | **Active** Product Phase 4 order / gates (**G5 green 2026-08-10**) |  
| `plans/phase4/IREIOS_4.0_EVIDENCE_PACK.md` | Phase 4 gate evidence (G5 filled) |  
| `plans/phase4/TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` | Locked lead decisions (blank template removed 2026-08-14 — answered copy is canonical) |  
| `plans/phase3/UNIFIED_EXECUTION_ORDER.md` | Archived IREIOS 3.0 order / gates |
| `plans/phase3/IREIOS_3.0_EVIDENCE_PACK.md` | 3.0 release evidence |
| `plans/phase4/IREIOS_4.0_EVIDENCE_PACK.md` | 4.0 release evidence |
| `plans/phase3/IREIOS_3.0_API_SSE_CONTRACTS.md` | 3.0 realtime contracts |
| `plans/phase4/IREIOS_4.0_API_CONTRACTS.md` | 4.0 FE/API contracts |

---

## 19. What not to do

- Do not delete dual-path helpers (`agent` qualification core, `crm_sync` helpers, `follow_up` pure helpers) without a dedicated decommission window — v3 **reuses** them.
- Do not use Neo4j Browser as the production observability UI for full graphs.
- Do not run `FOLLOW_UP_DLQ_TEST` or `TEST_MODE` in production.
- Do not install from an outdated lock after editing `requirements.txt` without regenerating the lock.
