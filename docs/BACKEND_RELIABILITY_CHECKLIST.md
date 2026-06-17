# Backend Reliability Checklist — Real Estate Revenue OS

**Prepared by:** Aritro
**Date:** June 17, 2026
**Reference:** Imperion Task PDF — Aritro Acceptance Criteria

---

## Acceptance Criteria Review

### ✅ No cross-client data leakage

Every read/write path in `main.py`, `follow_up.py`, `crm_sync.py`, and `dlq_replay.py`
scopes queries through `client_id`. The `get_client_by_api_key()` auth dependency
resolves `client_id` from the API key on every ingestion request before any DB
operation. Dashboard routes use `get_current_client()` (JWT) and filter all queries by
`current_client.id`. SQLAlchemy ORM relationships cascade deletes under client scope.

**Update (handover freeze):** to protect against identical phone numbers colliding
across tenants — e.g. two agencies both running sandbox tests from the same WhatsApp
number — `session_id`s are now actively prefixed with the tenant ID at the routing
layer: `{client_id}_{raw_phone}` (e.g. `1_+919163962356`). This closes a real
cross-tenant leakage bug caught during testing (see `BACKEND_STABILITY_REPORT.md`,
Bugs Found and Fixed).

**Open caveat:** `/api/v1/roi/*` and `/api/v1/reports/pipeline` currently use an
admin API key (`X-Admin-Key`) and query globally across all clients with no
`client_id` filter. These are internal ops routes — not client-facing. If they are
ever exposed to clients, a JWT guard + `client_id` filter must be added first. This
remains open as of this update.

---

### ✅ Authenticated access on all sensitive routes

Three auth layers are in place:

| Layer | Mechanism | Used on |
|-------|-----------|---------|
| API Key (ingestion) | `X-API-Key` header or `?api_key=` query param | `/api/v1/whatsapp`, `/api/v1/ingest`, `/api/v1/chat`, `/api/v1/webhook/meta`, `/api/v1/webhook/portals`, `/api/v1/incoming_sms` |
| JWT Bearer (dashboard) | `Authorization: Bearer <token>` via OAuth2 | `/api/v1/analytics`, `/api/v1/leads`, `/api/v1/leads/export`, `/api/v1/leads/{id}/stage`, `/api/v1/settings` (GET + PATCH) |
| Admin API Key | `X-Admin-Key` header | `/api/v1/reports/pipeline`, `/api/v1/roi/*` |

`/health`, `/metrics`, `/docs`, and `/openapi.json` are intentionally public.
Two additional public-by-design routes have been added since the original checklist:
`/api/v1/contact` (public contact form) and `/api/v1/webhook/stripe` (Stripe checkout
listener, verified via Stripe's own signature check rather than an app-level key).
`/metrics` should still be firewall-restricted in production if Prometheus is not
behind an internal network.

---

### ✅ Retries and DLQ handling verified with test failures

`crm_sync.py` wraps `_push_to_hubspot` with Tenacity: 5 attempts, exponential backoff
(2s → 30s). On permanent failure, the lead is flagged `crm_sync_status="failed"` and
a `DLQEvent` is inserted with `target_endpoint="hubspot_crm"`.

`follow_up.py` wraps `_send_twilio_msg()` with Tenacity (same config). On failure, a
`DLQEvent` is inserted with `target_endpoint="ml_followup_scheduler"`.

`main.py` handles the async agent timeout (15s) with a Twilio fallback push. If the
fallback also fails, a `DLQEvent` is inserted with `target_endpoint="twilio_outbound"`.

DLQ replay is run manually via `python dlq_replay.py`. It processes all `pending`
events and marks successfully replayed ones as `resolved`.

End-to-end DLQ test: confirmed by injecting a forced CRM failure in a local session
and verifying the `dlq_events` table received a row with `status="pending"`, then
replaying with `dlq_replay.py` and confirming it moved to `status="resolved"`.

---

### ✅ Scheduler jobs remain stable under load

`check_and_send_followups()` in `follow_up.py` runs every 60 seconds via APScheduler
(configured in `main.py` lifespan). The job:

- Opens its own DB session and closes it in `finally` — no session leak.
- Catches per-session exceptions individually so a single bad session does not abort
  the entire run.
- Pushes failures to DLQ rather than retrying inside the scheduler loop (avoids
  blocking the next tick).
- Emits `SCHEDULER_JOB_DURATION` (Histogram) and `SCHEDULER_JOB_FAILURES` (Counter)
  metrics for every execution, visible at `/metrics`.

Soak test log (`final_soak_test_log_20260429_201913.txt`) showed the scheduler ran for
the full test window without crashing under light load (3 concurrent users).

**Update (handover freeze):** a much larger stress run — `test_task3_maitri_results_all.json`,
126 multi-turn conversations simulating concurrent WhatsApp traffic — confirmed
continued stability at scale: 100% DB thread-safety lock (no corruption or
overlapping race conditions across rapid-fire messages), and 100% state-machine
integrity (inactivity decay and funnel qualification gated correctly throughout).

---

### ✅ Recovery procedure documented and reproducible

See `docs/BACKUP_RESTORE_DRILL.md`.

`db_backup.py` uses `pg_dump --clean --no-owner --no-privileges` — idempotent and
schema-only-safe. `db_restore.py` accepts any `.sql` artifact and runs `psql -f`.
Restore was most recently re-verified against the `backup_20260617_073805.sql`
artifact, and table integrity was confirmed via row-count query on all 7 core tables
(including the updated `event_logs`, `settings`, and `stripe_customer_id` schema
additions).

---

## Summary

| Criterion | Status | Notes |
|-----------|--------|-------|
| No cross-client data leakage | ✅ | Enhanced with `client_id`-prefixed `session_id`s; ROI routes remain admin-only (noted above) |
| Auth on all sensitive routes | ✅ | Three-layer: API key + JWT + Admin key; `/settings` now included under JWT |
| Retries + DLQ verified | ✅ | 3 DLQ event types, replay tested |
| Scheduler stability under load | ✅ | Soak test + 126-conversation stress test both passed |
| Recovery procedure documented | ✅ | `BACKUP_RESTORE_DRILL.md`, re-verified June 17, 2026 |