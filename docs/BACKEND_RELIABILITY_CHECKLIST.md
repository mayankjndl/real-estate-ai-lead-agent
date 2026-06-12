# Backend Reliability Checklist — Real Estate Revenue OS

**Prepared by:** Aritro  
**Date:** June 5, 2026  
**Reference:** Imperion Task PDF — Aritro Acceptance Criteria

---

## Acceptance Criteria Review

### ✅ No cross-client data leakage

Every read/write path in `main.py`, `follow_up.py`, `crm_sync.py`, and `dlq_replay.py`
scopes queries through `client_id`. The `get_client_by_api_key()` auth dependency
resolves `client_id` from the API key on every ingestion request before any DB
operation. Dashboard routes use `get_current_client()` (JWT) and filter all queries by
`current_client.id`. SQLAlchemy ORM relationships cascade deletes under client scope.

**Open caveat:** `/api/v1/roi/*` and `/api/v1/reports/pipeline` currently use an
admin API key (`X-Admin-Key`) and query globally across all clients with no
`client_id` filter. These are internal ops routes — not client-facing. If they are
ever exposed to clients, a JWT guard + `client_id` filter must be added first.

---

### ✅ Authenticated access on all sensitive routes

Two auth layers are in place:

| Layer                  | Mechanism                                     | Used on                                                                                           |
|------------------------|-----------------------------------------------|---------------------------------------------------------------------------------------------------|
| API Key (ingestion)    | `X-API-Key` header or `?api_key=` query param | `/api/v1/whatsapp`, `/api/v1/ingest`, `/api/v1/chat`, `/api/v1/webhook/*`, `/api/v1/incoming_sms` |
| JWT Bearer (dashboard) | `Authorization: Bearer <token>` via OAuth2    | `/api/v1/analytics`, `/api/v1/leads`, `/api/v1/leads/export`, `/api/v1/leads/{id}/stage`          |
| Admin API Key          | `X-Admin-Key` header                          | `/api/v1/reports/pipeline`, `/api/v1/roi/*`                                                       |

`/health` and `/metrics` are intentionally public. `/metrics` should be firewall-restricted in production if Prometheus is not behind an internal network.

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

Soak test log (`final_soak_test_log_20260429_201913.txt`) shows scheduler ran for
the full test window without crashing.

---

### ✅ Recovery procedure documented and reproducible

See `docs/BACKUP_RESTORE_DRILL.md`.

`db_backup.py` uses `pg_dump --clean --no-owner --no-privileges` — idempotent and
schema-only-safe. `db_restore.py` accepts any `.sql` artifact and runs `psql -f`.
Restore was run against the `backup_20260605_073805.sql` artifact and table integrity
was confirmed via row-count query on all 7 core tables.

---



## Additional Reliability Hardening (June 11, 2026)

- [x] RAG hallucination prevention guardrails implemented
- [x] CRM extraction contamination prevention validated
- [x] Budget alignment fallback recalculation enabled
- [x] Funnel stage synchronization implemented
- [x] Event logging null protection enabled
- [x] Follow-up scheduler state consistency verified
- [x] Multi-location lead normalization supported
- [x] Stripe webhook processing implemented
- [x] Contact form ingestion endpoint implemented
- [x] User settings persistence implemented
- [x] Frontend Docker integration completed


## Summary

| Criterion                      | Status   | Notes                                   |
|--------------------------------|----------|-----------------------------------------|
| No cross-client data leakage   | ✅        | ROI routes are admin-only (noted above) |
| Auth on all sensitive routes   | ✅        | Dual-layer: API key + JWT               |
| Retries + DLQ verified         | ✅        | 3 DLQ event types, replay tested        |
| Scheduler stability under load | ✅        | Soak test passed, metrics instrumented  |
| Recovery procedure documented  | ✅        | `BACKUP_RESTORE_DRILL.md`               |
