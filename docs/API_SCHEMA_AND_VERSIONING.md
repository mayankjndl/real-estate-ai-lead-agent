# API Schema and Versioning Notes — Real Estate Revenue OS

**Prepared by:** Aritro
**Date:** June 17, 2026
**Base URL (local):** `http://localhost:8000`
**OpenAPI JSON:** `GET /openapi.json` (available while app is running)
**Interactive docs:** `GET /docs`

---

## Versioning Policy

- All current endpoints live under `/api/v1/`. This is the stable production version.
- **Additive changes** (new optional fields, new endpoints) are non-breaking and may
  be shipped without a version bump.
- **Removing or renaming** a field, changing a response shape, or modifying auth
  behaviour requires introducing `/api/v2/` alongside the existing route. The v1
  route stays live for a minimum deprecation window.
- The `api_version` field will be added to all v2 responses for unambiguous
  identification.

---

## Auth Reference

| Auth type     | How to send                                                   | Used on                                                                                      |
|---------------|---------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| API Key       | `X-API-Key: <key>` header **or** `?api_key=<key>` query param | Ingestion & webhook routes                                                                   |
| JWT Bearer    | `Authorization: Bearer <token>`                               | Dashboard routes                                                                             |
| Admin API Key | `X-Admin-Key: <key>` header                                   | Internal ops / ROI routes                                                                    |
| None          | —                                                             | `/health`, `/metrics`, `/docs`, `/openapi.json`, `/api/v1/contact`, `/api/v1/webhook/stripe` |

API keys are provisioned via `add_client.py` and stored hashed in the `clients` table.
JWT tokens are issued by `POST /api/v1/auth/login` and expire after 7 days.

---

## Endpoint Reference

### Public / Infrastructure

| Method | Path            | Auth | Description                                                                 |
|--------|-----------------|------|-----------------------------------------------------------------------------|
| GET    | `/health`       | None | Returns `{"status":"healthy","database":"connected","scheduler":"running"}` |
| GET    | `/metrics`      | None | Prometheus text-format metrics                                              |
| GET    | `/docs`         | None | Swagger UI                                                                  |
| GET    | `/openapi.json` | None | Raw OpenAPI 3.x schema                                                      |

> The `/health` response shape was updated from the earlier `{"status","db","redis"}`
> form to surface scheduler liveness directly alongside the database check.

---

### Authentication

#### `POST /api/v1/auth/login`

Auth: None (public)
Content-Type: `application/x-www-form-urlencoded`

**Request body:**
```
username=<client_email>&password=<password>
```

**Response `200`:**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

---

### Lead Ingestion

#### `POST /api/v1/ingest`

Auth: API Key
Content-Type: `application/json`

**Request body:**
```json
{
  "session_id": "string",
  "message":    "string",
  "source":     "whatsapp | sms | web | portal"
}
```

**Response `200`:**
```json
{
  "reply": "string",
  "session_id": "string"
}
```

---

#### `POST /api/v1/chat`

Auth: API Key (query param `?api_key=`)
Query params: `session_id`, `message`

**Response `200`:**
```json
{
  "reply": "string",
  "session_id": "string"
}
```

---

### WhatsApp & SMS Webhooks

#### `POST /api/v1/whatsapp`

Auth: API Key (`?api_key=` query param — sent by Twilio as part of the webhook URL)
Content-Type: `application/x-www-form-urlencoded` (Twilio standard)

Twilio fields used: `Body`, `From`, `To`
Response: TwiML `<Response>` XML

---

#### `POST /api/v1/incoming_sms`

Auth: API Key (`?api_key=` query param)
Same Twilio field structure as WhatsApp.
Response: TwiML `<Response>` XML

---

### Public Contact Form & Billing Webhook

#### `POST /api/v1/contact`

Auth: None (public)
Content-Type: `application/json`

**Request body:**
```json
{
  "name": "string",
  "email": "string",
  "message": "string"
}
```

Accepts public marketing-site contact form submissions independent of the lead-qualification pipeline.

---

#### `POST /api/v1/webhook/stripe`

Auth: None (Stripe signs and verifies the webhook itself; no API key/JWT layer)
Content-Type: `application/json`

Verifies `checkout.session.completed` events and activates the client's SaaS
subscription in the DB (sets the subscription/`stripe_customer_id` state on the
`clients` row).

---

### Meta & Portal Webhooks

#### `POST /api/v1/webhook/meta`

Auth: API Key
Content-Type: `application/json`

**Request body:**
```json
{
  "session_id": "string",
  "message":    "string",
  "source":     "meta"
}
```

---

#### `POST /api/v1/webhook/portals`

Auth: API Key
Same shape as `/webhook/meta` with `"source": "portal"`.

---

### Dashboard — Analytics, Settings & Leads

#### `GET /api/v1/analytics`

Auth: JWT
Response: client-scoped aggregate metrics (total sessions, leads, intents, conversion rate).

---

#### `GET /api/v1/settings`

Auth: JWT
Response: client-scoped workspace settings (display preferences, alert toggles).

---

#### `PATCH /api/v1/settings`

Auth: JWT
Content-Type: `application/json`
Saves and synchronizes workspace settings across devices for the authenticated client.

---

#### `GET /api/v1/leads`

Auth: JWT
Query params: `page` (int, default 1), `page_size` (int, default 20), `stage` (string, optional)

**Response `200`:**
```json
{
  "leads": [ { "id": 1, "name": "...", "phone": "...", "budget": "...", "funnel_stage": "..." } ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

#### `PATCH /api/v1/leads/{lead_id}/stage`

Auth: JWT
Content-Type: `application/json`

**Request body:**
```json
{ "stage": "Contacted | Appointment Scheduled | Site Visit Done | Closed Won" }
```

**Response `200`:** Updated lead object. This endpoint now also writes the
corresponding `EventLog` row on every stage update, so site-visit and deal-closure
events appear correctly in the ROI/reports dashboards (see bug fix log).

---

#### `GET /api/v1/leads/export`

Auth: JWT
Response: `text/csv` — all leads for the authenticated client.

---

### Internal / Ops (Admin Key Required)

> ⚠️ These routes query all clients globally. Not for client-facing use.

#### `GET /api/v1/reports/pipeline`

Auth: Admin Key
Returns: funnel stage breakdown + qualified/conversion rates across all clients.

#### `GET /api/v1/roi/funnel_metrics`

Auth: Admin Key
Returns: total leads, qualified, appointments, site visits, deal closed counts + conversion rates.

#### `GET /api/v1/roi/speed_intelligence`

Auth: Admin Key
Returns: average AI and human response latency in ms.

#### `GET /api/v1/roi/source_attribution`

Auth: Admin Key
Returns: per-source lead count, appointment count, and conversion rate.

---

## Known Issues / Open Questions

1. `/api/v1/roi/*` and `/api/v1/reports/pipeline` have no `client_id` filter. Confirm
   with team lead whether these are internal-only. If ever client-facing, they need
   JWT auth + `client_id` scoping before exposure.

2. `/metrics` is public. On Render, restrict access at the network level or add a
   basic auth layer before production launch.

3. `/api/v1/webhook/stripe` and `/api/v1/contact` are intentionally unauthenticated
   (Stripe webhooks are verified by Stripe's own signing scheme, and the contact
   form is public by design). Confirm rate limiting/spam protection is acceptable
   for pilot before launch.