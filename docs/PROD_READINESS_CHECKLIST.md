# Production Readiness Checklist — IREIOS 4.0

| This doc owns | Does not own |
|---|---|
| Single source for prod-readiness requirements + adoption process | Day-to-day maintenance → `MAINTENANCE.md` |
| What must be true before 2026-08-20 (QA freeze) / 2026-09-03 (release) | Atomic QA/REL task steps → `plans/phase4/IREIOS_4.0_STEP_BY_STEP.md` |
| Flag matrix, secrets track, infra adoption path | Program status → `plans/phase4/UNIFIED_EXECUTION_ORDER.md` |

**Status:** Living document · **Freeze:** 2026-08-20 · **Release:** 2026-09-03 · **Owner:** Mayank
**Change rule:** all updates are **additive rows only** — never restructure existing sections (see §9).

---

## 1. Purpose & status

- QA freeze gate (`P4-QA`) = "Prod readiness checklist executed" per `UNIFIED_EXECUTION_ORDER.md`.
- Release gate (`P4-REL`) = "Runbook approved (Mayank)" — the runbook is drafted from §5–§8 below.
- Every row below has a **fallback behavior** so a missing integration degrades gracefully, never breaks chat.
- RC1 environment today = **local full-stack docker + separate staging Postgres** (Option B, `plans/phase4/TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` Q8.2/Q8.3). Hosted `staging-api.ireios` + read-replica adopted when ops delivers (see §5.2).

**Status summary (2026-08-13 audit):**

| Gate | Status |
|---|---|
| Backend + FE implementation (P4-0…P4-9) | `[x]` G5 green 2026-08-10 · HEAD `127920e` (CC UX batch 2026-08-14) |
| Command Center auth (twin/graph/predictions cookie+Bearer) | `[x]` fixed 2026-08-13 — verify via `docs/COMMAND_CENTER_VERIFY.md` |
| FE lint / tsc / build | `[x]` exit 0 — `4494307` (2026-08-11) |
| Full pytest + isolation + DLQ + WA→SSE smoke | `[x]` pre-freeze baseline (see Evidence Pack) |
| **Code debt for 4.0 MVP** | `[x]` none blocking — flags/timings at prod defaults in `config.py` |
| Secrets (Twilio, HubSpot PAT) | `[ ]` **Piyush** — Twilio required for live WA; HubSpot optional |
| Hosted staging / read-replica | `[ ]` ops TBD — local `pg-staging` fallback §5.1 |
| Docker n8n WF Publish (after volume wipe) | `[ ]` **Mayank** — JSON shipped; live webhooks 404 until re-import+Publish |
| Runbook draft + freeze tag + RC1 + REL | `[ ]` **Mayank** QA.1.1–1.6 / REL.1.1–1.5 |

---

## 2. Environment surface map

Every production-relevant variable: where it is read and what happens when it is empty. `Settings` = `config.py` (pydantic_settings); `env` = `os.getenv` at module import.

| Variable | Read by | Prod requirement | Fallback when unset/empty |
|---|---|---|---|
| `GEMINI_API_KEY` | Settings → `agent.py` | **Required** | No AI replies |
| `DATABASE_URL` | `database.py` engine | **Required** | App fails to start |
| `REDIS_URL` | Settings → bus/locks | **Required** | Bus dead; locks best-effort |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` | Settings → outbound | **Required for live WA** | Sends skipped |
| `IS_PRODUCTION` | Settings | `true` | — |
| `TEST_MODE` | Settings | `false` | `true` = Twilio signature bypassed |
| `FOLLOW_UP_TEST_MODE` | Settings | `false` | `true` = 1-min follow-up gaps |
| `FOLLOW_UP_DLQ_TEST` | Settings | `false` | `true` = forced DLQ entries |
| `JWT_SECRET_KEY` | Settings → dashboard auth | **Required** | Logins fail |
| `ADMIN_API_KEY` | Settings → admin routes | Generate | Admin endpoints closed |
| `CLIENT_KEY_A` / `CLIENT_KEY_B` / `API_AUTH_KEY` | Settings → auth | Per-tenant keys | No webhook access |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | env → `neo4j_client` | Optional | Graph no-op; chat unaffected |
| `N8N_BASE_URL` / `N8N_API_KEY` | env/bridge | Optional | `n8n_not_configured` no-op |
| `N8N_MANAGEMENT_API_KEY` | env → `import_n8n_workflows.py` | Only for import script | Import unavailable |
| `N8N_BRIDGE_ENABLED` / `N8N_BRIDGE_GROUP` | env → bridge | `true` if n8n used | Bridge off; no n8n fan-out |
| `GOOGLE_CALENDAR_ID` / `GOOGLE_CALENDAR_CREDENTIALS_JSON` / `GOOGLE_CALENDAR_TIMEZONE` | Settings → CalendarExecutor | Optional | Synthetic `visit_id` stub (AE contract unchanged) |
| `BROCHURE_MEDIA_URL` / `FLOORPLAN_MEDIA_URL` | Settings → `resolve_tool_media_url` | Optional | Plain-text brochure/floorplan; non-HTTPS rejected |
| `COMPETITOR_KEYWORDS` | Settings → competitor monitor | Optional | Job no-ops |
| `CRM_API_URL` / `CRM_API_KEY` | env → `crm_sync` | Optional (HubSpot skippable) | Demo stub (fake UUID) |
| `FEATURE_GRAPH_VIZ` / `FEATURE_TWIN_LIVE` | Settings | `true` (prod values) | Feature hidden/empty state |
| `FEATURE_HUBSPOT_LIVE` | Settings | `true` **only** with real key | `false` = stub path |
| `FEATURE_WHATSAPP_V3` / `FOLLOWUP_ENGINE` | Settings | `true` / `v3` | `legacy` = emergency rollback |
| `SMTP_*` / `ADMIN_EMAIL` / `ADMIN_EMAIL` | Settings → escalation email | Optional | WhatsApp escalation only |
| `WEBHOOK_BASE_URL` | Settings | Set to public Twilio URL | Webhook URL resolution degraded |
| `STRIPE_WEBHOOK_SECRET` | Settings | Optional | Stripe webhook unauthenticated |
| `CLIENT_SUPPORT_NUMBER` | Settings | Prod value | Default demo number |

Timeouts (prod defaults): `WHATSAPP_WEBHOOK_TIMEOUT=13`, `LLM_TIMEOUT_SECONDS=22`, `RAG_TIMEOUT_SECONDS=2.0`, `GRAPH_CONTEXT_TIMEOUT_SECONDS=0.5` — do not lower; full map: `docs/TIMEOUTS_AND_TIMINGS.md`.

---

## 3. Go-live flag matrix (must-flip before release)

| Flag | Dev | **Prod** | Effect if wrong |
|---|---|---|---|
| `IS_PRODUCTION` | `false` | **`true`** | Missed prod-only paths |
| `TEST_MODE` | `true` | **`false`** | Twilio signature bypassed (security) |
| `FOLLOW_UP_TEST_MODE` | `true` | **`false`** | 1-min follow-up spam |
| `FOLLOW_UP_DLQ_TEST` | off | **`false`** | Forced DLQ noise |
| `FEATURE_WHATSAPP_V3` | `true` | **`true`** | Rolls back to legacy agent |
| `FOLLOWUP_ENGINE` | `v3` | **`v3`** | `legacy` only as emergency |
| `FEATURE_GRAPH_VIZ` | `true` | `true` | Graph hidden (acceptable degrade) |
| `FEATURE_TWIN_LIVE` | `true` | `true` | Twin hidden (acceptable degrade) |
| `FEATURE_HUBSPOT_LIVE` | `false` | `true` **iff** real PAT | Stub CRM (acceptable degrade) |

---

## 4. Secrets track

| Secret | Env var | Source / owner | Required at 2026-09-03? | Status |
|---|---|---|---|---|
| Twilio Account SID + Auth Token + From number | `TWILIO_*` | Piyush track | **Yes** | `[ ]` |
| Gemini API key | `GEMINI_API_KEY` | Mayank | Yes | `[x]` local |
| JWT secret | `JWT_SECRET_KEY` | Generate | Yes | `[ ]` |
| Admin API key | `ADMIN_API_KEY` | Generate | Yes | `[ ]` |
| HubSpot Private App Token | `CRM_API_KEY` | Piyush track | Optional (skippable) | `[ ]` |
| Neo4j creds | `NEO4J_*` | Mayank/ops | Optional | `[ ]` |
| n8n webhook secret + management JWT | `N8N_API_KEY`, `N8N_MANAGEMENT_API_KEY` | **Mayank** (docker compose host; re-Publish after volume wipe) | Optional | `[ ]` |
| Google Calendar SA JSON + calendar id | `GOOGLE_CALENDAR_*` | Mayank | Optional | `[ ]` |
| Stripe webhook secret | `STRIPE_WEBHOOK_SECRET` | Mayank | Optional | `[ ]` |
| SMTP creds | `SMTP_*` | Ops | Optional | `[ ]` |

**Rule:** never commit real secrets — local `.env` only (`.env*` gitignored; `.env.example` holds blanks/demo values).

---

## 5. Infra requirements & implementation process

### 5.1 Current staging / RC1 (Option B — local fallback, in use from QA)

RC1 target per locked Q8.3 is a read-replica; until ops delivers hosted infra, RC1 runs on a **separate staging Postgres seeded from a prod-data snapshot** — this honors the Q8.3 intent (QA never touches prod) without code changes. Setup:

1. Add a second postgres service to `docker-compose.yml` (e.g. `pg-staging`, own volume `pgdata-staging`, port 5433, same image) — additive, prod compose untouched.
2. Seed: `python db_backup.py` on prod → `python db_restore.py backups/backup_*.sql` against the staging DB (or `seed.py` for clean data).
3. Staging app run: `DATABASE_URL=postgresql://…@127.0.0.1:5433/realestate_staging_db` (override env) + `docker compose up -d` (rest of stack).
4. QA evidence records the RC1 env + snapshot date in `IREIOS_4.0_EVIDENCE_PACK.md` § QA freeze/RC1.

**Important:** a *literal read-only* replica would break the app — chat, follow-ups, CRM and scoring all write to the same engine (`database.py` has no read/write routing). "RC1 on read-replica" is therefore implemented as *staging primary populated from replica/backup data*. True write-routing is deferred to IREIOS 4.1 (do not add code for it before freeze).

### 5.2 Hosted adoption path (when ops delivers `staging-api.ireios`)

Implementation process, in order:

1. **Receive** from ops: staging URL, staging PG endpoint (replica or restored copy), TLS cert, and Twilio console webhook target.
2. **Validate:** `python -c "from database import SessionLocal; s=SessionLocal(); print(s.execute(text('select 1')).scalar())"` against staging `DATABASE_URL`; `curl https://staging-api.ireios/health`.
3. **Point staging at the copy** — env-only change (`DATABASE_URL`, `REDIS_URL`, feature flags); **no code change** unless a gap is found (then log as 4.1 deferral, not pre-freeze code).
4. **Re-run RC1 evidence** (QA.1.2/QA.1.3) against the hosted env and update the evidence pack + this doc's status row.
5. **Promote:** the same env set (minus staging DB) becomes §5.3's prod template.

### 5.3 Production deploy topology

| Item | Requirement | Fallback |
|---|---|---|
| Host | Prod host with docker compose (postgres, redis, neo4j, n8n, frontend) | Render.com single-app (README badge) — env-same |
| TLS / domain | `prod-api.ireios` HTTPS | — |
| Twilio console | WhatsApp webhook URL → `https://prod-api.ireios/api/v1/whatsapp` | Signature validation `ON` (TEST_MODE=false) |
| ngrok | **Removed** in prod (dev tunnel only) | — |
| `/metrics` | Firewall-restrict (public today) | Allow-list admin IPs |
| Frontend | `NEXT_PUBLIC_API_URL` = prod API; same-origin rewrite keeps JWT cookie flow | — |
| DB | Migrate (`migrate_db.py`) + `db_backup.py` snapshot pre-release | Restore drill `MAINTENANCE.md` §4 |

---

## 6. Integration adoption runbooks (each optional; enable → configure → verify → rollback)

### Neo4j (graph)
- Enable: `NEO4J_URI/USER/PASSWORD` + `docker compose up -d neo4j` → **verify** `GET /api/v1/graph/health`, `python project_leads_to_neo4j.py` → **rollback:** empty URI (no-op graph).
### n8n + bridge (optional ops plane — docker-hosted)
- **Owner on this stack:** **Mayank** (compose/deploy host). Not a separate cloud-n8n operator role.
- **Shipped in repo:** `n8n_workflows/wf1…wf6.json`, Python bridge (`ireios-n8n` group), `import_n8n_workflows.py`, unit tests 14/14.
- **Volume wipe resets Publish state** — after `docker compose down -v` / new `n8ndata`, n8n starts with **0 published workflows**; production `POST /webhook/*` returns 404 until re-import + **Publish**. Prior successful Gmail automation does not survive a wiped volume.
- Enable: `N8N_BASE_URL`/`N8N_API_KEY` + Header Auth credential + **Publish all 6 WFs** in UI (or CLI `n8n publish:workflow`) → set Gmail **To** / sheet id → **verify** live `lead.hot` → Gmail + unit `tests/test_e20_n8n_bridge.py` → **rollback:** `N8N_BRIDGE_ENABLED=false` or empty URL. Never point n8n Redis Trigger at `ireios:events`.
- Full steps: `docs/N8N_INTEGRATION.md`, `docs/N8N_GOOGLE_CREDENTIALS_SETUP.md`, `plans/phase4/HANDOFF_MAYANK_PIYUSH.md`.
### Google Calendar
- Enable: service-account JSON (forward slashes on Windows) + calendar shared with SA → **verify** `site_visit.scheduled` shows real event id → **rollback:** empty vars (synthetic `visit_id` stub).
### Brochure / floorplan
- Enable: public **HTTPS** URLs → **verify** TwiML `<Media>` + FE staged `media_url` → **rollback:** empty vars (plain-text generators).
### HubSpot (optional)
- Enable: `CRM_API_URL`/`CRM_API_KEY` (Private App Token, contacts r/w scope) + `FEATURE_HUBSPOT_LIVE=true` → **verify** contact upsert + DLQ on failure → **rollback:** `FEATURE_HUBSPOT_LIVE=false` (stub) — HubSpot is skippable at release.
### Competitor monitor
- Enable: `COMPETITOR_KEYWORDS=a,b,c` → **verify** nightly 01:00 `market.alert.generated` + `NotificationLog` rows → **rollback:** empty (job no-op).

---

## 7. Monitoring & telemetry

- **`/metrics`** (public today — firewall-restrict in prod). Owner: **Mayank**. Watch: request latency p95, webhook 13s race-window hit rate, DLQ row count, event-bus consume-loop health.
- **Scheduler jobs** (in-app APScheduler): follow-up checker 1min · escalation 10m/30m (1min checker) · CRM resync 5min · expire_approvals 15min · nightly backup 2am · nightly cleanup 3am · competitor monitor 01:00 · weekly marketing report Mon 08:00. Keep off-box copies of backups (`MAINTENANCE.md` §4).
- **Alert thresholds / timings map:** `docs/TIMEOUTS_AND_TIMINGS.md` (all race/TTL/scheduler values + line anchors).
- **Incident owner:** ________ (fill at REL.1.4).
- **Post-release smoke set:** `/health`, `/metrics`, real-Twilio WA turn, SSE (`wa_sse_smoke.py`), follow-up real timings, escalation, backup job, bus consume loop.

---

## 8. Release & rollback runbook pointer

- Deploy sequence, migrations, backups/restore, wipes: `docs/MAINTENANCE.md` (§4 PG, §5 Redis/bus, §8 scheduler).
- Stress: `python task3_runner.py` — **waived at G5 and P4-QA** (Gemini quota, Mayank ack; see evidence).
- **Rollback:** 1) git revert of deploy commit; 2) flags off (`TEST_MODE` stays false; feature flags to degrade paths); 3) Twilio webhook URL back to previous host; 4) `python db_restore.py` from pre-release snapshot. `FEATURE_HUBSPOT_LIVE=false` + `FOLLOWUP_ENGINE=legacy` are emergency-only toggles.

---

## 9. Change process (how to update this doc)

1. **Additive only:** new requirement = new row in the relevant table + fallback behavior + owner. Do not merge/rename existing rows.
2. New env var → update §2 row **and** the `.env.example` footer go-live comment **and** `AGENTS.md` go-live checklist pointer (this doc).
3. Integration adoption → add a mini-runbook in §6 (enable/configure/verify/rollback), mirroring existing entries.
4. Flag flips at release → tick §3; secrets filled → tick §4; RC1 env changed → tick §1 status row + evidence pack.
5. After every change: keep `plans/phase4/UNIFIED_EXECUTION_ORDER.md` P4-QA/P4-REL rows in sync.
