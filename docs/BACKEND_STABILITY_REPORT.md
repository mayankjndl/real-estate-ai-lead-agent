# Backend Stability Report — Real Estate Revenue OS

**Prepared by:** Aritro  
**Date:** June 5, 2026  
**Phase:** Pre-pilot handover  
**Status:** ✅ Ready for controlled paid pilot

---

## 1. Multi-Tenant Isolation — Confirmed

Every database read/write path is scoped by `client_id`. The auth layer resolves
`client_id` from the inbound API key or JWT before any query runs. SQLAlchemy
relationships are declared with `cascade="all, delete-orphan"` under each `Client`
entity, ensuring no orphaned cross-client records.

The one known exception — `/api/v1/roi/*` and `/api/v1/reports/pipeline` — is
protected by a separate Admin API key and is designated for internal ops use only.
It must not be exposed to clients without adding JWT auth and a `client_id` filter.

---

## 2. Auth Hardened — Dual-Layer in Production

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| Ingestion (webhooks, WhatsApp, SMS) | `X-API-Key` header or `?api_key=` query param | Per-client API key provisioned via `seed.py` |
| Dashboard (analytics, leads, export) | `Authorization: Bearer <JWT>` | 7-day token, issued on login |
| Internal ops | `X-Admin-Key` header | Single shared key per deployment |

No sensitive route is reachable without one of these credentials. Public-only
endpoints are `/health`, `/metrics`, `/docs`, and `/openapi.json`.

---

## 3. Observability — Live

### Prometheus Metrics (available at `GET /metrics`)

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `http_requests_total` | Counter | method, endpoint, http_status | Request volume by route and outcome |
| `http_request_duration_seconds` | Histogram | method, endpoint | Latency distribution per endpoint |
| `background_failures_total` | Counter | component | Coarse background task failures |
| `scheduler_job_duration_seconds` | Histogram | job_name | Scheduler wall-clock time per tick |
| `scheduler_job_failures_total` | Counter | job_name | Unhandled scheduler exceptions |
| `integration_failure_total` | Counter | integration (crm, twilio) | Permanent post-retry integration failures |
| `dlq_pending_events` | Gauge | — | Current DLQ backlog depth |

### Grafana Dashboard

`grafana_dashboard.json` contains panels for request rate, p95 latency,
background failure trends, and scheduler health. Import it into any Grafana instance
pointed at the Prometheus data source.

### Alert Rules

`prometheus_alerts.yml` defines:

- `HighErrorRate` — fires when 5xx rate exceeds 5% over 5 minutes
- `SlowResponseTime` — fires when p95 latency exceeds 2 seconds
- `DLQDepthHigh` — fires when `dlq_pending_events > 10` for 5 minutes
- `SchedulerStopped` — fires when no scheduler heartbeat log for 2 minutes

---

## 4. DLQ Tested and Documented

Three event types are covered: `hubspot_crm`, `twilio_outbound`,
`ml_followup_scheduler`. Replay was tested end-to-end:

- CRM failure injected → `dlq_events` row inserted with `status="pending"` ✅
- `python dlq_replay.py` executed → row updated to `status="resolved"` ✅

Full process documented in `docs/DLQ_REPLAY_PROCESS.md`.

---

## 5. Backup Verified with Drill Evidence

- `python db_backup.py` → `backups/backup_20260605_073805.sql` created ✅
- `python db_restore.py backups/backup_20260605_073805.sql` → completed without error ✅
- Post-restore row-count query → all 7 tables intact ✅

Full drill log in `docs/BACKUP_RESTORE_DRILL.md`.

---

## 6. Soak Test Results

**File:** `final_soak_test_log_20260429_201913.txt`

| Metric | Result |
|--------|--------|
| Concurrent users | 3 |
| Total messages | 12 |
| Total errors | 0 |
| Lead extraction accuracy | 3/3 (budget + intent captured correctly) |
| CRM sync after test | 200 OK, all 3 leads confirmed |

All sessions ran to completion with zero HTTP errors. Background CRM sync confirmed
leads written within 15 seconds of session close. Scheduler ran uninterrupted for the
full test window.

---

## 7. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|-----------|
| Single Uvicorn worker on Render free tier | Under sustained high load (50+ concurrent users), p95 latency will rise | Upgrade Render plan to add workers; Gunicorn config in `Procfile` supports this |
| Backup storage is local disk | Backups on Render ephemeral disk are lost on redeploy | Render managed PostgreSQL backup is the primary safety net; `db_backup.py` is a secondary layer |
| No per-client rate limiting | A single high-volume client could starve others | Redis-based per-session lock is in place; per-client hourly quota is the recommended next step |
| `/metrics` is publicly accessible | Internal metrics exposed without auth | Firewall-restrict in production or add Prometheus basic auth |
| Admin ROI routes query all clients | No multi-tenant safety for internal ops routes | Acceptable for pilot; add `client_id` filter before making client-facing |
| 429 ResourceExhausted API rate limits | Free-tier API quotas prevent running 100+ concurrent tests at high speed | System handles gracefully via Twilio fallback; upgrade to paid API tier before high-volume load testing |
| Partial visit date collection stalls DB write | If a user provides only a visit date without Name or Budget, the LLM asks for missing fields before writing to DB | Expected qualification-gate behaviour; date is not persisted until `is_fully_qualified` passes |

---

## 8. Bugs Found and Fixed (June 9, 2026)

| Bug | Root Cause | Fix |
|-----|------------|-----|
| ML Inactivity Penalty not syncing with Follow-up Scheduler | ML scorer's inactivity penalty ran independently of the scheduler's time-based decay, causing divergent scoring | Bridged the two systems so inactivity penalty state is shared and consistent across both paths |
| Premature Visit Confirmation | AI confirmed site visits without first collecting Name, Budget, and Property Type | Implemented `is_fully_qualified` strict gate and dynamic prompt injection to block confirmation until all required fields are present |
| ROI Dashboard missing `site_visit_done` and `deal_closed` events | Manual CRM Stage PATCH endpoint did not write to the `EventLog` table; visit and deal events never appeared in ROI metrics | Wired the PATCH endpoint directly to `EventLog` — every stage update now emits the corresponding event |

---

## 9. Recommended Next Steps (Post-Pilot)

1. **Per-client rate limiting** — Redis counter keyed by `client_id` + hour window.
2. **Render worker scale-up** — Switch `Procfile` from single Uvicorn to
   `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app` once usage justifies it.
3. **Metrics auth** — Restrict `/metrics` to the internal Prometheus scrape IP or add
   basic auth.
4. **Automated DLQ replay** — Add a second APScheduler job to run `dlq_replay.py`
   every 5 minutes instead of manually.
5. **ROI route client isolation** — Add JWT + `client_id` filter to
   `/api/v1/roi/*` routes before any client-facing exposure.
6. **S3 backup offload** — Ship `db_backup.py` output to an S3 bucket after each
   successful dump.

---

## Sign-Off

Backend is production-safe for a controlled paid pilot with monitoring enabled.
Do not deploy without setting all environment variables in the Render dashboard
and verifying `GET /health` returns healthy before updating the Twilio webhook URL.
