# IREIOS 3.0 — API & SSE Contracts

Source of truth for the realtime + API envelopes the frontend consumes.  
Implemented in `app/api/events.py`, mounted at `/api/v1/events`.

> Status: **LIVE** (Phase 1b + Phase 9 backend mount). Producers are real bus events and/or `event_logs`; stub publisher remains for demos.

---

## 1. SSE stream

| | |
|--|--|
| **Route** | `GET /api/v1/events/stream` |
| **Auth** | `?api_key=` **or** `X-API-Key` **or** HttpOnly `jwt` cookie (same login as dashboard) |
| **Transport** | `text/event-stream` |
| **Filter** | Only envelopes where `tenant_id == Client_<authed_client.id>` |
| **Heartbeat** | `: ping` comment every 15s |
| **Errors** | `401` unauthenticated; `503` if event bus not running |

### Smoke

```powershell
curl -N "http://localhost:8000/api/v1/events/stream?api_key=secret-client-key-123"

python publish_stub_event.py --event-type lead.created --tenant-id Client_1 --payload "{\"name\":\"demo\"}"
```

### Frame shape

Each event is one SSE `data:` line with a JSON **bus envelope**:

```json
{
  "event_id": "string",
  "event_type": "lead.created",
  "tenant_id": "Client_1",
  "entity_id": "string",
  "source": "stub | whatsapp_agent | execution_engine | …",
  "timestamp": "ISO-8601",
  "correlation_id": "string | null",
  "payload": { }
}
```

Common `event_type` values (non-exhaustive): `lead.created`, `lead.scored`, `lead.hot`, `lead.escalated` (alias of `lead.hot`), `lead.qualified`, `lead.assigned`, `conversation.updated`, `session.completed` (PR #10 alias on close), `whatsapp.sent`, `approval.requested`, `site_visit.scheduled`, `marketing.report.generated`.

n8n dual-publish / alias rules: `docs/N8N_INTEGRATION.md`. Prefer catalog names long-term; pick one of `lead.hot`|`lead.escalated` per workflow. Closeout payloads: `docs/N8N_INTEGRATION.md` § Canonical payloads and `plans/phase3/PHASE3_AUTOMATIONS_CLOSEOUT.md`.

---

## 2. Lead timeline

| | |
|--|--|
| **Route** | `GET /api/v1/events/leads/{lead_id}/timeline` |
| **Auth** | Same as SSE (`get_events_client`) |
| **Source** | Postgres `event_logs` for the lead's session |
| **Errors** | `401`; `404` if lead not owned by caller |

### Response

```json
{
  "lead_id": 123,
  "events": [
    {
      "event_id": "evt_1",
      "event_type": "string",
      "tenant_id": "Client_1",
      "entity_id": "123",
      "source": "event_log",
      "timestamp": "ISO-8601 | null",
      "correlation_id": null,
      "payload": {
        "action_type": "string | null",
        "agent_type": "string | null",
        "latency_ms": 0
      }
    }
  ]
}
```

Empty `events` list when no logs (stable schema).

---

## 3. Stub publisher

| | |
|--|--|
| **Route** | `POST /api/v1/events/stub` |
| **Auth** | Header `X-Admin-Token: <ADMIN_API_KEY>` |
| **Body** | `{ "event_type": str, "tenant_id"?: str, "entity_id"?: str, "payload"?: object }` |
| **Returns** | `{ "event_id": "…" }` |
| **CLI** | `python publish_stub_event.py --event-type lead.created --tenant-id Client_1 --payload "{}"` |

Use for FE demos without WhatsApp/LLM. Prefer CLI when the API process already owns the bus consumer.

---

## 4. Related APIs (FE backlog)

See `docs/FRONTEND_BACKLOG.md`:

| Route | Purpose |
|-------|---------|
| `GET /api/v1/leads/{id}/score` | Score breakdown |
| `GET /api/v1/leads/{id}/prediction` | Conversion / closure |
| `GET /api/v1/graph/leads/{id}/context` | Neo4j similar-lead context |
| `GET /api/v1/graph/health` | Graph availability |
| `GET /api/v1/approvals` + approve/reject | HITL |
| `POST /api/v1/leads/{id}/sales-ai` | Sales copilot |

---

## 5. Compatibility rules

- Do not rename envelope top-level fields without versioning this doc + FE.
- Tenant isolation is mandatory on stream and timeline.
- Stub/`source: "stub"` is for demos only; production UI should tolerate real `source` values.
- OpenAPI dump: `plans/phase3/openapi_ireios3.json` (regenerate via app OpenAPI if drifted).
