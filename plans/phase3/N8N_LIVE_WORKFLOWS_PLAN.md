# n8n Live Workflows Plan (Gmail-first)

**Status:** Bridge shipped · UI workflows incomplete until activated  
**Owners:** Backend bridge = Aritro · n8n UI + Gmail OAuth = Maitri / ops  
**Canonical ops doc:** `docs/N8N_INTEGRATION.md`  
**Delivery path (locked):** Python `N8NBridge` consumer group `ireios-n8n` → `POST /webhook/{path}`  

Do **not** configure n8n Redis Trigger on `ireios:events` (stock n8n has no Streams support; CEO group must not be shared).

---

## 0. Prerequisites

```powershell
docker compose up -d redis n8n
# API (host): set N8N_* in .env, restart uvicorn
```

```env
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=local-n8n-webhook-secret
N8N_BRIDGE_ENABLED=true
N8N_BRIDGE_GROUP=ireios-n8n
```

1. Open http://localhost:5678 → create owner account.  
2. **Credentials → Gmail OAuth2** (workspace or personal).  
3. Create one **Header Auth** credential: name `X-N8N-API-KEY`, value = `N8N_API_KEY`.  
4. Reuse that credential on every Webhook node below.  
5. Workflows must be **Active** (production webhook URL, not test).

**Code refs**

| Piece | Path |
|-------|------|
| Bridge | `app/automation_engine/n8n_bridge.py` |
| HTTP client | `app/automation_engine/n8n_client.py` |
| Lifespan start/stop | `main.py` lifespan |
| Hot publish | `app/events/lead_hot.py` |
| Turn + `chat_context` | `main.py` `_emit_turn_events` |
| Visit event | EE `_publish_success` + `CalendarExecutor` |
| HITL | `app/automation_engine/hitl.py` |
| Stub publish | `publish_stub_event.py` |

---

## 1. Envelope contract (all WFs)

Every bridge POST body:

```json
{
  "event_id": "uuid",
  "event_type": "<type>",
  "tenant_id": "Client_<id>",
  "entity_id": "<lead id or entity>",
  "source": "<producer>",
  "timestamp": "<iso8601>",
  "correlation_id": "uuid",
  "payload": { }
}
```

n8n field paths:

- `{{ $json.event_type }}`
- `{{ $json.tenant_id }}`
- `{{ $json.payload.name }}`
- `{{ $json.payload.chat_context }}`

---

## 2. Default map (do not double-map aliases)

| event_type | webhook path | WF |
|------------|--------------|-----|
| `lead.hot` | `ireios_hot_lead_alert` | WF-1 |
| `site_visit.scheduled` | `ireios_visit_fanout` | WF-2 |
| `approval.requested` | `ireios_hitl_notify` | WF-3 |
| `lead.qualified` | `ireios_crm_note` | WF-4 |
| `marketing.report.generated` | `ireios_marketing_csv` | WF-5 |

**Never map** `lead.escalated` if `lead.hot` is mapped (dual-publish alias).  
**Prefer** `lead.qualified` over `session.completed` for CRM fields.

---

## 3. WF-1 P0 — Hot lead / handoff → Gmail

### Purpose (team-lead loop 1)

Admin email when lead is hot (score) or human handoff requested.

### Build in n8n UI

1. **Webhook**
   - HTTP Method: `POST`
   - Path: `ireios_hot_lead_alert`
   - Authentication: Header Auth → `X-N8N-API-KEY`
   - Respond: Immediately (or “When Last Node Finishes”)
2. **Optional IF**
   - Branch A: `{{ $json.payload.trigger }}` equals `human_handoff` → subject prefix `[HANDOFF]`
   - Branch B: else → `[HOT]`
3. **Gmail → Send Email**
   - To: ops/admin inbox (fixed or env)
   - Subject:  
     `{{ $json.payload.trigger === 'human_handoff' ? '[HANDOFF]' : '[HOT]' }} Lead {{ $json.payload.name }} ({{ $json.tenant_id }})`
   - Message (HTML or text):

```text
Trigger: {{ $json.payload.trigger }}
Reason: {{ $json.payload.reason }}
Name: {{ $json.payload.name }}
Phone: {{ $json.payload.phone }}
Location: {{ $json.payload.location }}
Budget: {{ $json.payload.budget }}
Type: {{ $json.payload.property_type }}
Score: {{ $json.payload.score }}
Agent: {{ $json.payload.assigned_agent }}
Lead ID: {{ $json.payload.lead_id }}
Session: {{ $json.payload.session_id }}

--- Chat ---
{{ $json.payload.chat_context }}
```

4. **Activate** workflow.

### Smoke

```powershell
python publish_stub_event.py --event-type lead.hot --tenant-id Client_1 --entity-id 1 --payload "{\"lead_id\":1,\"name\":\"Demo\",\"phone\":\"+919999999999\",\"trigger\":\"hot_threshold\",\"score\":90,\"reason\":\"stub hot\",\"assigned_agent\":\"Sneha\",\"chat_context\":\"User: hi\\nAgent: hello\"}"
```

Pass: API log contains `n8n_bridge_forwarded` · n8n Executions shows success · Gmail received.

Real traffic: score ≥ 82 or `lead_temperature=hot` → scoring handler; handoff phrase → `agent.py` → `publish_lead_hot`.

### Team-lead name map

| Said in chat | Actual bus |
|--------------|------------|
| `human.requested` | `lead.hot` + `trigger=human_handoff` |
| `lead.escalated` | alias only — not bridged by default |

---

## 4. WF-2 P1 — Site visit fan-out → Gmail

### Purpose (team-lead loop 2)

Notify ops/lead after visit is booked. **Python already creates Google Calendar** when `GOOGLE_CALENDAR_*` set.

### Build

1. Webhook path: `ireios_visit_fanout` + Header Auth  
2. **IF** `{{ $json.payload.provider }}` equals `google_calendar`  
   - Then: Gmail only (include `html_link`)  
   - Else (stub): Gmail note “stub visit — no calendar link”  
3. **Never** add Google Calendar **Create** node when provider is already `google_calendar`.

### Gmail body

```text
Site visit scheduled
Lead: {{ $json.payload.name }} · {{ $json.payload.phone }}
When: {{ $json.payload.visit_date }}
Location: {{ $json.payload.location }}
Provider: {{ $json.payload.provider }}
Visit ID: {{ $json.payload.visit_id }}
Calendar: {{ $json.payload.html_link }}
```

### Smoke

```powershell
python publish_stub_event.py --event-type site_visit.scheduled --tenant-id Client_1 --entity-id 1 --payload "{\"lead_id\":1,\"name\":\"Demo\",\"phone\":\"+9199\",\"visit_date\":\"2026-08-01T10:00:00+05:30\",\"location\":\"Baner\",\"provider\":\"google_calendar\",\"html_link\":\"https://calendar.google.com/\",\"visit_id\":\"evt_demo\"}"
```

Real: complete 6 fields + visit_date → Sales/AE `schedule_visit` → CalendarExecutor → EE `site_visit.scheduled` → bridge.

---

## 5. WF-3 P1 — HITL manager notify → Gmail

### Purpose

Manager email when AE pauses on `requires_approval`.

### Build

1. Webhook: `ireios_hitl_notify`  
2. Gmail to manager inbox  
3. Body includes dashboard deep links (JWT required — do **not** unauthenticated POST approve):

```text
Approval #{{ $json.payload.approval_id }}
Action: {{ $json.payload.action_type }}
Entity: {{ $json.payload.entity_id }}
Correlation: {{ $json.payload.correlation_id }}

Open dashboard to approve/reject.
Relative paths (append to public API or dashboard base):
Approve: {{ $json.payload.approve_path }}
Reject: {{ $json.payload.reject_path }}
Base hint: {{ $json.payload.api_base_hint }}
```

### Smoke

Publish stub `approval.requested` or trigger a real HITL action in app.

---

## 6. WF-4 P2 — CRM note → external CRM (optional Gmail audit)

### Purpose (team-lead loop 3)

On qualify, push summary + transcript to external CRM via n8n nodes. Python HubSpot stays skipped.

### Build

1. Webhook: `ireios_crm_note`  
2. HubSpot / Salesforce / Sheets node: upsert contact from `name`, `phone`, fields  
3. Note/body: `{{ $json.payload.chat_context }}`  
4. Optional: Gmail audit “CRM note pushed for {{ $json.payload.name }}”

### Prefer event

`lead.qualified` (bridge default). Do not also map `session.completed` unless WF-4 uses only the alias.

### Smoke

```powershell
python publish_stub_event.py --event-type lead.qualified --tenant-id Client_1 --entity-id 1 --payload "{\"lead_id\":1,\"name\":\"Demo\",\"phone\":\"+9199\",\"location\":\"Baner\",\"budget\":\"80L\",\"property_type\":\"2BHK\",\"intent\":\"buy\",\"chat_context\":\"User: ready\\nAgent: booked\"}"
```

---

## 7. WF-5 P2 — Marketing report → Drive + Gmail

1. Webhook: `ireios_marketing_csv`  
2. Convert `payload` JSON → CSV (Code or Spreadsheet File)  
3. Google Drive upload  
4. Gmail link to ops  

---

## 8. WF-6 P2 — DLQ depth (cron, no bridge)

1. n8n Cron every 15m  
2. HTTP request to admin metrics or internal check  
3. IF pending DLQ > N → Gmail alert  

No bus event required.

---

## 9. Implementation order for any LLM / ops

| Step | Action | Done when |
|------|--------|-----------|
| 1 | Confirm bridge in code + env | `N8N_BRIDGE_ENABLED=true`, uvicorn logs “n8n bridge started” |
| 2 | n8n up + Gmail credential | Can send test Gmail from n8n |
| 3 | Activate WF-1 | Stub `lead.hot` → Gmail |
| 4 | Activate WF-2 | Stub visit → Gmail; real visit does not double-create GCal |
| 5 | Activate WF-3 | HITL Gmail |
| 6 | Activate WF-4 | qualify → CRM/Gmail |
| 7 | WF-5/6 optional | — |
| 8 | Joint smoke | WA/chat hot + visit path |

---

## 10. Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| No n8n execution | Workflow inactive / wrong path | Path must match map exactly; Active on |
| `n8n_http_404` | Path mismatch or inactive | Fix path / activate |
| `n8n_not_configured` | Empty `N8N_*` | Set env, restart API |
| Double Gmail | Mapped alias + primary or AE n8n + bridge | Map one path only |
| CEO agents silent | n8n joined `ireios-cg` | Never; only `ireios-n8n` |
| Bridge silent, no log | `N8N_BRIDGE_ENABLED=false` | Enable |
| PEL stuck | 5xx n8n down | Fix n8n; restart API drains pending |

---

## 11. Tests

```powershell
pytest tests/test_e20_n8n_bridge.py tests/test_e18_automations_closeout.py -v
```

---

## 12. Exit criteria (G4 n8n slice)

- [x] Bridge code + separate consumer group  
- [x] Docs: bridge-primary, Gmail-first  
- [ ] WF-1 Active + stub/real Gmail proof  
- [ ] WF-2 Active + no double Google create  
- [ ] WF-3/4 as needed for ops  

Backend delivery path is complete; remaining work is n8n UI + Gmail OAuth activation.
