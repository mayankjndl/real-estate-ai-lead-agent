# Backend Stability Report — Real Estate Revenue OS

**Prepared by:** Aritro
**Date:** June 17, 2026
**Phase:** Pre-pilot handover (Phase 2)
**Status:** ✅ Ready for controlled paid pilot

---

## 1. Multi-Tenant Isolation — Confirmed

Every database read/write path is scoped by `client_id`. The auth layer resolves
`client_id` from the inbound API key or JWT before any query runs. SQLAlchemy
relationships are declared with `cascade="all, delete-orphan"` under each `Client`
entity, ensuring no orphaned cross-client records.

To guarantee strict multi-tenancy even during overlapping sandbox testing (e.g. two
clients' QA teams both using the same WhatsApp test number), `session_id`s are now
prefixed with the active `client_id` at the routing boundary: `{client_id}_{raw_phone}`.
This was added as a direct fix after a cross-tenant collision was found during
handover testing (see Section 8).

The one known exception — `/api/v1/roi/*` and `/api/v1/reports/pipeline` — is
protected by a separate Admin API key and is designated for internal ops use only. It
must not be exposed to clients without adding JWT auth and a `client_id` filter.

---

## 2. Auth Hardened — Dual-Layer in Production

| Layer                                          | Mechanism                                     | Scope                                                   |
|------------------------------------------------|-----------------------------------------------|---------------------------------------------------------|
| Ingestion (webhooks, WhatsApp, SMS)            | `X-API-Key` header or `?api_key=` query param | Per-client API key, now provisioned via `add_client.py` |
| Dashboard (analytics, leads, export, settings) | `Authorization: Bearer <JWT>`                 | 7-day token, issued on login                            |
| Internal ops                                   | `X-Admin-Key` header                          | Single shared key per deployment                        |

No sensitive route is reachable without one of these credentials. Public-only
endpoints are `/health`, `/metrics`, `/docs`, `/openapi.json`, `/api/v1/contact`, and
`/api/v1/webhook/stripe` (the latter two added since the original report — both are
intentionally public-facing and validated independently: Stripe via signature
verification, contact form via basic input validation).

---

## 3. Observability — Live

### Prometheus Metrics (available at `GET /metrics`)

| Metric                           | Type      | Labels                        | Purpose                                   |
|----------------------------------|-----------|-------------------------------|-------------------------------------------|
| `http_requests_total`            | Counter   | method, endpoint, http_status | Request volume by route and outcome       |
| `http_request_duration_seconds`  | Histogram | method, endpoint              | Latency distribution per endpoint         |
| `background_failures_total`      | Counter   | component                     | Coarse background task failures           |
| `scheduler_job_duration_seconds` | Histogram | job_name                      | Scheduler wall-clock time per tick        |
| `scheduler_job_failures_total`   | Counter   | job_name                      | Unhandled scheduler exceptions            |
| `integration_failure_total`      | Counter   | integration (crm, twilio)     | Permanent post-retry integration failures |
| `dlq_pending_events`             | Gauge     | —                             | Current DLQ backlog depth                 |

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

- `python db_backup.py` → `backups/backup_20260617_073805.sql` created ✅
- `python db_restore.py backups/backup_20260617_073805.sql` → completed without error ✅
- Post-restore row-count query → all 7 tables intact, including the newer
  `settings`, `stripe_customer_id`, and `event_logs` schema additions ✅

Full drill log in `docs/BACKUP_RESTORE_DRILL.md`.

---

## 6. Load & Stress Test Results

### Initial Soak Test (April 29, 2026)

**File:** `final_soak_test_log_20260429_201913.txt`

| Metric                   | Result                                   |
|--------------------------|------------------------------------------|
| Concurrent users         | 3                                        |
| Total messages           | 12                                       |
| Total errors             | 0                                        |
| Lead extraction accuracy | 3/3 (budget + intent captured correctly) |
| CRM sync after test      | 200 OK, all 3 leads confirmed            |

### Advanced Stress Test (Handover Freeze, June 17, 2026)

**File:** `test_task3_maitri_results_all.json`

| Metric                      | Result                                                                                                                |
|-----------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Total stress scenarios      | 126 multi-turn conversations simulating concurrent WhatsApp traffic                                                   |
| Dynamic inference pass rate | 91%+ (remaining ~9% validated as deliberate AI conversational deferral or Gemini 429 quota limits, not real failures) |
| DB thread-safety lock       | 100% — no database corruption or overlapping race conditions across rapid-fire messages                               |
| State machine integrity     | 100% — inactivity decay and funnel qualification gated correctly                                                      |
| ROI logging accuracy        | 100% — site visit and deal closure events correctly captured in `EventLog`                                            |

All sessions in both tests ran to completion. Background CRM sync and the follow-up
scheduler remained stable throughout.

---

## 7. Known Limitations

| Limitation                                    | Impact                                                                                                            | Mitigation                                                                                              |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| Single Uvicorn worker on Render free tier     | Under sustained high load (50+ concurrent users), p95 latency will rise                                           | Upgrade Render plan to add workers; Gunicorn config in `Procfile` supports this                         |
| Backup storage is local disk                  | Backups on Render ephemeral disk are lost on redeploy                                                             | Render managed PostgreSQL backup is the primary safety net; `db_backup.py` is a secondary layer         |
| No per-client rate limiting                   | A single high-volume client could starve others                                                                   | Redis-based per-session lock is in place; per-client hourly quota is the recommended next step          |
| `/metrics` is publicly accessible             | Internal metrics exposed without auth                                                                             | Firewall-restrict in production or add Prometheus basic auth                                            |
| Admin ROI routes query all clients            | No multi-tenant safety for internal ops routes                                                                    | Acceptable for pilot; add `client_id` filter before making client-facing                                |
| 429 ResourceExhausted API rate limits         | Free-tier API quotas prevent running 100+ concurrent tests at high speed                                          | System handles gracefully via Twilio fallback; upgrade to paid API tier before high-volume load testing |
| Partial visit date collection stalls DB write | If a user provides only a visit date without Name or Budget, the LLM asks for missing fields before writing to DB | Expected qualification-gate behaviour; date is not persisted until `is_fully_qualified` passes          |

---

## 8. Bugs Found and Fixed (Handover Freeze Update — through June 17, 2026)

| Bug                                                         | Root Cause                                                                                                                                  | Fix                                                                                                                                                    |
|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| 15s timeout never firing                                    | `asyncio.TimeoutError` was caught but `asyncio.wait_for()` was never actually called                                                        | Wrapped `process_unified_lead()` in `asyncio.wait_for(timeout=15.0)`                                                                                   |
| Assistant message saved twice to DB                         | Tool call block saved the message, then the final save block also ran                                                                       | Added a `message_saved` flag to skip the final save when the tool block already saved                                                                  |
| `INTENT_INTERCEPT` swallowing data                          | Intercept fired on messages like "I want to buy, budget is 90 lakhs" — no Gemini call, data never saved                                     | Added a `HAS_PERSONAL_DATA` guard; intercept now skips when the message contains name/budget/lakh/BHK keywords                                         |
| Score stuck at Low despite complete lead                    | ML scorer only reads current message text, missing DB-committed fields                                                                      | Added a DB-aware override after ML scoring; a fully booked lead (visit + phone + location + budget) forces High/hot                                    |
| Follow-up status showing "stopped / Day 0" after visit date | Unconditional `follow_up_status = "stopped"` ran even when a visit was already booked                                                       | Added a check: if `lead.visit_date` is set → status = "completed", `next_follow_up_at` cleared                                                         |
| Phone not auto-set when visit date given first              | Phone auto-set logic lived only inside the tool-call block — skipped if no tool call fired                                                  | Moved phone auto-set to the top of `process_chat()`, so it always runs on the first message                                                            |
| Cross-Tenant Leakage                                        | Users testing multiple clients with the same WhatsApp number collided in the DB                                                             | Prepended `client_id` to `session_id` inside `main.py`, ensuring strict DB row isolation                                                               |
| Budget Alignment Unrecognized                               | Asking for 1BHK or 5BHK returned `unknown` because the dictionary only stored 2BHK/3BHK                                                     | Updated `budget_alignment.py` to dynamically calculate non-standard BHKs using a scaled base ratio                                                     |
| Premature Visit Confirmation                                | AI confirmed site visits without first collecting Name, Budget, and Property Type                                                           | Implemented an `is_fully_qualified` strict gate and dynamic prompt injection to block confirmation until all required fields are present               |
| Phone Number Amnesia                                        | AI asked users for their number to schedule a call, even though the DB already had it                                                       | Injected `Phone: {lead.phone}` into the LLM system prompt context                                                                                      |
| Budget Auto-Calculation                                     | If a user switched intent from Rent to Buy, the AI falsely auto-generated a purchase budget                                                 | Added a strict prompt rule preventing budget assumption upon intent change                                                                             |
| "Byee" Typo Evasion                                         | Typos bypassed the natural session-closer script                                                                                            | Upgraded string matching to catch slang and typos (`"bye" in msg_clean`)                                                                               |
| Off-Hours Auto-Correction                                   | Gemini silently corrected "1 AM" visit requests to "11 AM" in the DB                                                                        | Added a strict `TIME TYPOS` rule forcing explicit conversational clarification from the user instead of silent correction                              |
| ML Inactivity Penalty Drift                                 | ML scorer's inactivity penalty ran independently of the scheduler's time-based decay, causing divergent scoring                             | Bridged the two systems so inactivity penalty state is shared and consistent across both paths                                                         |
| ROI Dashboard Missing Events                                | Manual CRM Stage PATCH endpoint did not write to the `EventLog` table; visit and deal events never appeared in ROI metrics                  | Wired the PATCH endpoint directly to `EventLog` — every stage update now emits the corresponding event                                                 |
| Multi-Location Overwrite                                    | Location normalizer used `next()` to grab the first matched area, discarding multiple locations                                             | Overhauled `normalize_lead_data` to loop through, sort, and join all extracted canonical locations                                                     |
| Multi-Location & Pricing Collision                          | Passing `"Baner, Wakad"` into budget alignment crashed the pricing lookup (no matching key)                                                 | Updated the Super-Fix block to extract only the **primary** location before passing it to the pricing evaluator                                        |
| RAG Context Contamination                                   | General queries triggered RAG, injecting random locations into the prompt                                                                   | Enforced an `is_rag_eligible` gate to only trigger RAG when a location is explicitly mentioned or already in context                                   |
| Class-vs-Instance Variable Bug                              | A typo in the ML rescoring block assigned to `Lead.urgency_level` (capital L, class-level) instead of `lead.urgency_level` (instance-level) | Corrected to the lowercase instance variable to prevent class-level pollution and guarantee proper DB persistence                                      |
| Event Log Latencies and Actions                             | Background events were logging `<null>` for latency and generic action types                                                                | Enforced a `latency_ms=0` default in `log_event_async`; explicit `action_type="lead_created"` on initial lead creation; added Day-X follow-up tracking |
| Rentals Budget Regex                                        | Missing "k"/"thousand" parsing broke rental-intent budgets (e.g. 25k)                                                                       | Updated `parse_budget_to_lakhs` in `budget_alignment.py` to safely convert values like 25k → 0.25 Lakhs                                                |

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

*Prepared by Aritro | Real Estate Revenue OS — Phase 2 Handover | June 17, 2026*