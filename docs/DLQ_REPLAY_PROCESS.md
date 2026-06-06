# DLQ / Replay Process — Real Estate Revenue OS

**Prepared by:** Aritro  
**Date:** June 5, 2026

---

## What is the DLQ?

The Dead Letter Queue (DLQ) is a `dlq_events` table in PostgreSQL that captures
integration failures after all retry attempts have been exhausted. Instead of silently
dropping failed events, the system records them for manual or scheduled replay.

This prevents data loss when third-party services (HubSpot CRM, Twilio) are
temporarily unavailable, and decouples failure recovery from the hot path.

---

## Event Types

The DLQ handles three event types, identified by the `target_endpoint` column:

| `target_endpoint` | Triggered by | Replay action |
|-------------------|-------------|---------------|
| `hubspot_crm` | `crm_sync.py` after 5 failed HubSpot pushes | Re-calls `_push_to_hubspot(payload)` |
| `twilio_outbound` | `main.py` after both primary agent send and Twilio fallback fail | Re-calls `client.messages.create(...)` |
| `ml_followup_scheduler` | `follow_up.py` when the ML engine or Twilio send fails for a session | Re-generates follow-up message and sends via Twilio |

---

## DLQ Record Structure

```sql
CREATE TABLE dlq_events (
    id              SERIAL PRIMARY KEY,
    client_id       INTEGER REFERENCES clients(id),
    target_endpoint VARCHAR NOT NULL,           -- one of the 3 values above
    payload         JSONB,                      -- original request payload
    error_trace     TEXT,                       -- last exception message
    status          VARCHAR DEFAULT 'pending',  -- 'pending' | 'resolved'
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

---

## How to Run Replay

```powershell
python dlq_replay.py
```

The script:

1. Opens a DB session.
2. Fetches all rows where `status = 'pending'`.
3. Dispatches each event to the appropriate handler function.
4. On success → sets `status = 'resolved'` and commits.
5. On failure → logs the error, leaves `status = 'pending'` for the next run.
6. Prints a summary: `X/Y events recovered successfully`.

Run it from the project root with the virtualenv active and `.env` loaded.

---

## How to Check DLQ Depth

Connect to the database and run:

```sql
-- Total pending events
SELECT COUNT(*) FROM dlq_events WHERE status = 'pending';

-- Breakdown by type
SELECT target_endpoint, COUNT(*) 
FROM dlq_events 
WHERE status = 'pending' 
GROUP BY target_endpoint;

-- Inspect a specific pending event
SELECT id, target_endpoint, error_trace, created_at 
FROM dlq_events 
WHERE status = 'pending' 
ORDER BY created_at DESC 
LIMIT 10;
```

The Prometheus gauge `dlq_pending_events` also exposes this count at `/metrics`
(updated each time `dlq_replay.py` runs or can be wired to a scheduled probe).

---

## Status Meanings

| Status | Meaning |
|--------|---------|
| `pending` | Event has not been successfully replayed. Either not yet attempted or last attempt failed. |
| `resolved` | Event was replayed successfully. No further action needed. |

There is no `failed` terminal state — events stay `pending` until they succeed. This
is intentional: it allows indefinite retry with no data loss.

---

## When to Escalate Manually

Escalate to the team lead if:

- More than **20 pending events** accumulate within a 1-hour window (indicates an
  ongoing third-party outage, not transient failures).
- Any `hubspot_crm` events remain `pending` after **3 manual replay attempts** (may
  indicate API key rotation or schema change on the HubSpot side).
- Any `twilio_outbound` events remain `pending` for more than **30 minutes** (check
  Twilio console for account suspension or number health).
- `dlq_replay.py` itself crashes (check logs — usually a DB connectivity issue).

Prometheus alert rule `DLQDepthHigh` in `prometheus_alerts.yml` fires when
`dlq_pending_events > 10` for more than 5 minutes.

---

## Replay Safety

- **Idempotency:** HubSpot replay may create duplicate contacts if the first push
  partially succeeded. Check for duplicates by `phone` in HubSpot after replay.
- **Twilio replay:** Messages are sent regardless of whether the original was
  received. Notify the lead only once where possible — check `messages` table before
  manual escalation.
- **ML followup replay:** Regenerates the message payload via the ML engine on each
  replay. Output may differ slightly from the original attempt.
