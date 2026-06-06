from prometheus_client import Counter, Histogram, Gauge

# ── Existing coarse-grained counter (kept for backward compat) ──────────────
BACKGROUND_FAILURE_COUNT = Counter(
    "background_failures_total",
    "Total background task failures before DLQ push",
    ["component"]
)

# ── Granular scheduler metrics ───────────────────────────────────────────────
SCHEDULER_JOB_DURATION = Histogram(
    "scheduler_job_duration_seconds",
    "Wall-clock time for each scheduler job execution",
    ["job_name"]
)

SCHEDULER_JOB_FAILURES = Counter(
    "scheduler_job_failures_total",
    "Number of times a scheduler job has raised an unhandled exception",
    ["job_name"]
)

# ── Integration-level failure counters ───────────────────────────────────────
INTEGRATION_FAILURES = Counter(
    "integration_failure_total",
    "Permanent (post-retry) failures broken out by integration target",
    ["integration"]   # values: crm, twilio, sms
)

# ── DLQ depth gauge ──────────────────────────────────────────────────────────
DLQ_PENDING_EVENTS = Gauge(
    "dlq_pending_events",
    "Number of DLQ events currently in 'pending' status awaiting replay"
)
