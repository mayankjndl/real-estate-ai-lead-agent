from prometheus_client import Counter

BACKGROUND_FAILURE_COUNT = Counter(
    "background_failures_total",
    "Total background task failures before DLQ push",
    ["component"]
)
