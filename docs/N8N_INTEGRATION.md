# n8n Integration (optional / config-later)

## Purpose

n8n is the **external workflow automation plane** for IREIOS 3.0. It is **not** required for core lead qualification. Use it when business processes leave the real-time chat path:

| Use case | Why n8n (not in-app code) |
|----------|---------------------------|
| Multi-step human approvals outside the dashboard | Visual BPM, Gmail/Slack nodes |
| Nightly CRM hygiene / spreadsheet exports | Cron + connectors without redeploying API |
| Marketing drip beyond WhatsApp follow-up FSM | Channel mix (email, SMS, ads) |
| Partner webhooks (portals, accounting) | Quick connector library |
| Ops alerts (Gmail primary) on `lead.hot` / DLQ depth | Bridge → webhook → Gmail |

**Primary ops channel: Gmail.** Slack is optional.

## Architecture fit (locked)

```text
Event Bus (Redis Streams: ireios:events)
    │
    ├─► consumer group ireios-cg  → CEO agents (scoring, CRM AE, KG, follow-up arm)
    │
    └─► consumer group ireios-n8n → N8NBridge (app/automation_engine/n8n_bridge.py)
              filter allowlisted event_type
              POST {N8N_BASE_URL}/webhook/{path}
              header Authorization: Bearer {N8N_API_KEY}
              body = full bus envelope
                    │
                    ▼
              n8n Webhook workflows (Active) → Gmail / CRM nodes / Drive

AutomationEngine (fallback only)
    template_type="n8n"  →  n8n_client.trigger_workflow
         → same POST /webhook/{workflow_id}
```

### Why not “n8n reads Redis Streams”?

Stock n8n **cannot** consume Redis Streams:

- **Redis Trigger** = Pub/Sub channels only  
- **Redis node** = get/set/publish — no `XREADGROUP`  
- Joining CEO group `ireios-cg` would **steal** messages from in-app agents  

**Primary delivery = Python bridge** with its **own** group `ireios-n8n`.  
AE `template_type=n8n` remains a **fallback** for explicit action requests — do **not** enable both for the same alert (double Gmail).

When `N8N_BASE_URL` / `N8N_API_KEY` are empty, client/bridge return/skip with  
`n8n_not_configured` and **never crash** the bus or API.

## Recommended workflows (Gmail-first)

Full step-by-step recipes: **`plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md`**.

| WF | Webhook path | Bus event | n8n action |
|----|--------------|-----------|------------|
| WF-1 P0 | `ireios_hot_lead_alert` | `lead.hot` | Gmail to admin (hot / handoff) |
| WF-2 P1 | `ireios_visit_fanout` | `site_visit.scheduled` | Gmail invite note (no 2nd GCal create) |
| WF-3 P1 | `ireios_hitl_notify` | `approval.requested` | Gmail manager + dashboard links |
| WF-4 P2 | `ireios_crm_append` | `lead.qualified` | Google Sheets append via HTTP Request |
| WF-5 P2 | `ireios_marketing_csv` | `marketing.report.generated` | CSV → Drive + Gmail link |
| WF-6 P2 | (cron) | — | DLQ depth Gmail |

### What n8n must NOT own

- WhatsApp TwiML race / 6-field gate / RAG  
- Follow-up Day0→7 FSM / 10m–30m escalation cron / competitor monitor  
- Tenant isolation / JWT issuance  
- Google Calendar **create** when Python already ran (`provider=google_calendar`)  
- Subscribing to both `lead.hot` **and** `lead.escalated` (double email)

## Dual-publish aliases (PR #10)

Backend dual-publishes catalog + review aliases. Bridge maps **catalog only**.

| Business signal | Catalog (bridge maps) | Alias (not in default map) | Code |
|-----------------|----------------------|----------------------------|------|
| Hot score or handoff | `lead.hot` (`payload.trigger`) | `lead.escalated` | `app/events/lead_hot.py` |
| Session closed | `lead.qualified` (+ `chat_context`) | `session.completed` | same + `main.py` |
| Site visit booked | `site_visit.scheduled` | — | EE after `CalendarExecutor` |

**n8n rule:** one event type per workflow. Prefer catalog names.

## Local Docker

```powershell
docker compose up -d n8n redis
# UI: http://localhost:5678  (create owner email/password on first visit)
```

| Item | Value |
|------|--------|
| Image | `n8nio/n8n:2.31.5` service `n8n` in `docker-compose.yml` |
| UI / API base | `http://localhost:5678` |
| Data volume | `n8ndata` |
| Webhooks | `http://localhost:5678/webhook/<path>` (workflow must be **Published/Active**) |

### Two keys (do not mix)

| Env var | What it is | Used by | n8n UI |
|---------|------------|---------|--------|
| `N8N_API_KEY` | Shared **webhook** secret | Backend `n8n_client` / bridge → `Authorization: Bearer {secret}` on `POST /webhook/*` | Header Auth credential **IREIOS API Key**: header name `Authorization`, value `Bearer {same secret}` |
| `N8N_MANAGEMENT_API_KEY` | JWT from **Settings → n8n API** | `import_n8n_workflows.py` only → header `X-N8N-API-KEY` on `/api/v1/*` | Create at http://localhost:5678/settings/api |

Putting the webhook secret in `N8N_MANAGEMENT_API_KEY` (or feeding it to the import script) always returns **401 unauthorized** on workflow create. That is expected.

**Do not** set container env `N8N_API_KEY` hoping it enables the Public API — n8n does not use that for `/api/v1`.

### Onboarding (Google Cloud + credentials + import)

**Full step-by-step (APIs, OAuth External + test users, OAuth client, Calendar service account,
Header Auth, management JWT, import, set To, Publish, smoke tests):**

→ **[`docs/N8N_GOOGLE_CREDENTIALS_SETUP.md`](N8N_GOOGLE_CREDENTIALS_SETUP.md)**

Short path after Cloud Console is done:

1. n8n owner setup at http://localhost:5678  
2. Credentials with **exact names**: `IREIOS API Key` (Header Auth), `Gmail account`, `Google Sheets account`  
3. Header Auth value = `Bearer {N8N_API_KEY}` (include `Bearer `)  
4. Settings → n8n API → JWT → `.env` `N8N_MANAGEMENT_API_KEY`  
5. `uv run python import_n8n_workflows.py`  
6. Set Gmail **To** (WF-1/2/3/6) + WF-5 Code `const to = '…'` + WF-4 sheet ID → **Save + Publish** all  
7. Restart uvicorn if `.env` changed  

Importer resolves credentials **by name**. Repo Gmail `sendTo` is empty on purpose.  
**Calendar create** = Python `GOOGLE_CALENDAR_*` (service account), not n8n.

### CLI fallback (no management JWT)

```powershell
docker cp n8n_workflows n8n-local:/tmp/n8n_workflows
docker exec -u node n8n-local n8n import:workflow --separate --input=/tmp/n8n_workflows
docker exec -u node n8n-local n8n list:workflow
# For each id:
docker exec -u node n8n-local n8n publish:workflow --id=<ID>
docker restart n8n-local
```

Then link credentials + set **To** in the UI (CLI import may not bind empty credential IDs).  
**Never wipe the `n8ndata` volume** just to fix credential ID mismatches — re-link in the UI or re-import with the Python script instead.

### Point IREIOS at the instance

```env
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=local-n8n-webhook-secret
N8N_MANAGEMENT_API_KEY=   # JWT — import only
N8N_BRIDGE_ENABLED=true
N8N_BRIDGE_GROUP=ireios-n8n
```

Restart uvicorn after changing `.env`. Bridge POSTs  
`{N8N_BASE_URL}/webhook/{path}` with header `Authorization: Bearer {N8N_API_KEY}` and the **full bus envelope**.

**From another container** (API in Compose): `N8N_BASE_URL=http://n8n:5678`.

## Env

```env
N8N_BASE_URL=http://localhost:5678
# Webhook Header Auth secret (backend bridge)
N8N_API_KEY=shared-secret-matching-n8n-header-auth
# JWT from n8n Settings → n8n API (import_n8n_workflows.py only)
N8N_MANAGEMENT_API_KEY=
N8N_BRIDGE_ENABLED=true
N8N_BRIDGE_GROUP=ireios-n8n
# Optional JSON override of event_type → webhook path
# N8N_WEBHOOK_MAP={"lead.hot":"ireios_hot_lead_alert"}
```

## Envelope every webhook receives

```json
{
  "event_id": "uuid",
  "event_type": "lead.hot",
  "tenant_id": "Client_1",
  "entity_id": "123",
  "source": "lead_scoring_handler",
  "timestamp": "2026-07-28T12:00:00+00:00",
  "correlation_id": "uuid",
  "payload": { }
}
```

n8n expressions: `{{ $json.payload.name }}`, `{{ $json.event_type }}`, `{{ $json.tenant_id }}`.

## Canonical payloads

### `lead.hot` (WF-1)

```json
{
  "event_type": "lead.hot",
  "tenant_id": "Client_1",
  "entity_id": "123",
  "source": "agent | lead_scoring_handler",
  "payload": {
    "lead_id": 123,
    "session_id": "1_+919999999999",
    "name": "John Doe",
    "phone": "+919999999999",
    "location": "Baner",
    "budget": "80L",
    "property_type": "2BHK",
    "lead_temperature": "hot",
    "conversion_probability": 85,
    "score": 85,
    "trigger": "hot_threshold | human_handoff",
    "reason": "HOT threshold crossed | Explicit human agent requested.",
    "assigned_agent": "Sneha",
    "chat_context": "User: ...\nAgent: ..."
  }
}
```

| Chat wording | Bus emits |
|--------------|-----------|
| `human.requested` | `lead.hot` + alias `lead.escalated`, `trigger=human_handoff` |
| `lead.escalated` | Alias of `lead.hot` — bridge ignores alias by default |
| `session.completed` | Alias on close; prefer `lead.qualified` for CRM fields |

**Shipped:** `app/events/lead_hot.py` · debounce 30m · scoring + handoff.

### `lead.qualified` (WF-4 CRM)

Emitted from `main.py` `_emit_turn_events` when 6-field gate complete (`chat_context` attached).

### `site_visit.scheduled` (WF-2)

Python owns Google create when `GOOGLE_CALENDAR_*` set. n8n = Gmail/ops fan-out only.

```json
{
  "payload": {
    "lead_id": 123,
    "visit_id": "...",
    "visit_date": "2026-08-01T10:00:00+05:30",
    "name": "John Doe",
    "phone": "+919999999999",
    "location": "Baner",
    "provider": "google_calendar | stub",
    "html_link": "https://calendar.google.com/..."
  }
}
```

**Do not** create a second Google event if `provider=google_calendar`.

### `approval.requested` (WF-3)

From `app/automation_engine/hitl.py`: `approve_path`, `reject_path`, optional `api_base_hint`.  
Approve APIs need JWT — Gmail links should open the **dashboard**, not unauthenticated POST.

### `marketing.report.generated` (WF-5)

From `marketing_agent`.

## Smoke (bridge + WF-1)

```powershell
docker compose up -d redis n8n
# Activate WF-1 in n8n UI (path ireios_hot_lead_alert + Header Auth + Gmail or Set)
# uvicorn with N8N_* set, then:
python publish_stub_event.py --event-type lead.hot --tenant-id Client_1 --entity-id 1 --payload "{\"lead_id\":1,\"name\":\"Demo\",\"phone\":\"+9199\",\"trigger\":\"hot_threshold\",\"score\":90,\"reason\":\"stub\",\"chat_context\":\"User: hi\"}"
```

Expect: API log `n8n_bridge_forwarded` · n8n execution · Gmail (or Set node output).

## Default webhook map

Code: `app/automation_engine/n8n_bridge.py` → `DEFAULT_WEBHOOK_MAP`

| event_type | path |
|------------|------|
| `lead.hot` | `ireios_hot_lead_alert` |
| `site_visit.scheduled` | `ireios_visit_fanout` |
| `approval.requested` | `ireios_hitl_notify` |
| `lead.qualified` | `ireios_crm_append` |
| `marketing.report.generated` | `ireios_marketing_csv` |

Legacy path name `ireios_hot_lead_slack` is **retired** (Gmail-first). Override via `N8N_WEBHOOK_MAP` if needed.

## Status

| Piece | Status |
|-------|--------|
| Client scaffold | **Shipped** — `n8n_client.py` |
| AE `template_type=n8n` | **Shipped** |
| **Bus → webhook bridge** | **Shipped** — `n8n_bridge.py`, group `ireios-n8n` |
| Docker Compose `n8n` | **Shipped** — `n8nio/n8n:2.31.5` |
| Bus emits (`lead.hot`, `chat_context`, visit merge, HITL paths) | **Shipped** |
| Google OAuth2 credentials | **Shipped** — Gmail + Google Sheets via custom OAuth2 |
| Live n8n **workflows** (6/6 Active) | **Shipped** — webhook-verified, import via `import_n8n_workflows.py` |
| WF-1 `ireios_hot_lead_alert` | **Shipped** — Hot Lead → Gmail (IF handoff → prefix) |
| WF-2 `ireios_visit_fanout` | **Shipped** — Site Visit → Gmail (IF google_calendar → event link) |
| WF-3 `ireios_hitl_notify` | **Shipped** — HITL → Gmail (approval request) |
| WF-4 `ireios_crm_append` | **Shipped** — CRM → Google Sheets via HTTP Request |
| WF-5 `ireios_marketing_csv` | **Shipped** — Marketing Report → Gmail + CSV attachment via Gmail API |
| WF-6 DLQ cron (15min) | **Shipped** — DLQ Depth Monitor → Gmail |
| Credential setup guide | **Shipped** — `docs/N8N_GOOGLE_CREDENTIALS_SETUP.md` |

## What must stay in IREIOS (not n8n)

- WhatsApp TwiML reply path  
- 6-field qualification gate + RAG  
- Tenant isolation / JWT  
- Follow-up Day0→7 state machine  
- Multi-tenant `client_id` enforcement  
- Google Calendar **create** via `CalendarExecutor`

n8n is **orchestration around** the OS, not a replacement for the CEO/AE/EE spine.

## Python email vs n8n Gmail

| Kind | Owner | Purpose |
|------|--------|---------|
| Critical / Twilio failure fallback | Python notification paths | Disaster recovery |
| Business ops (hot lead, visit fan-out, HITL, digests) | n8n Gmail | Day-to-day ops routing |
