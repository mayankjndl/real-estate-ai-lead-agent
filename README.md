# Real Estate Revenue OS — Backend

> Production-ready WhatsApp AI lead agent: qualifies leads, maintains conversation context, syncs to CRM, and automates follow-ups — with multi-tenant isolation, DLQ fault recovery, and Prometheus observability.

[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-3.1--Flash--Lite-orange?logo=google)](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-red?logo=twilio)](https://twilio.com)
[![Render](https://img.shields.io/badge/Deploy-Render.com-purple)](https://render.com)

---

## Architecture

```
WhatsApp message
      ↓
POST /api/v1/whatsapp?api_key=CLIENT_KEY_A
      ↓
Auth → get_client_by_api_key() → resolves client_id
      ↓
Fast-path intercepts (instant replies, guardrails)
      ↓
asyncio.create_task(_session_turn_locked) + race WHATSAPP_WEBHOOK_TIMEOUT (default 13s)
  ├── session_lock + private DB session (full turn)
  ├── Neo4j graph context (soft ≤0.5s) + RAG (≤2s) + Gemini (LLM_TIMEOUT default 22s)
  └── extract_lead_info() tool → saves to Lead table
      ↓
Fast: TwiML reply  |  Slow: interim "Just checking…" + await same task → EE push
      ↓
Off-path: score / memory / graph upsert + bus events (lead.created → CRM, etc.)
      ↓
APScheduler (every 60s): follow_up.py → timed follow-up messages
      ↓
DLQ: any permanent failure → dlq_events table → python dlq_replay.py
```

---

## Prerequisites — Install These First

Install the following in order before touching any code.

### 1. Python 3.13

Download from https://www.python.org/downloads/  
During install on Windows: ✅ check **"Add Python to PATH"**

Verify:
```powershell
python --version   # Python 3.13.x
```

### 2. PostgreSQL 18 Client Tools (EDB Installer — Windows)

You need `pg_dump` and `psql` for backup/restore. You do **not** need the PostgreSQL
server — Docker handles that. Install the client tools only:

1. Go to https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Download **PostgreSQL 18** for Windows
3. Run the installer — check **only:**
   - ✅ **Command Line Tools**
   - ❌ Uncheck pgAdmin, Stack Builder, Server
4. Default install path: `C:\Program Files\PostgreSQL\18\bin`

**Add to PATH (run PowerShell as Administrator):**
```powershell
[System.Environment]::SetEnvironmentVariable(
  "Path",
  $env:Path + ";C:\Program Files\PostgreSQL\18\bin",
  [System.EnvironmentVariableTarget]::Machine
)
```
Close and reopen terminal after running this.

Verify:
```powershell
psql --version    # psql (PostgreSQL) 18.x
pg_dump --version # pg_dump (PostgreSQL) 18.x
```

> **If you already have a local PostgreSQL server running**, it will conflict with
> the Docker container on port 5432. Disable it:
> ```powershell
> # Run as Administrator
> Stop-Service -Name "postgresql*" -Force
> Set-Service -Name "postgresql*" -StartupType Disabled
> ```

### 3. Docker Desktop 4.7.x

Download from https://www.docker.com/products/docker-desktop/  
Install and start Docker Desktop before running any `docker` command.  
Requires Docker Engine 29.5.x (included with Docker Desktop 4.7.x).

Verify:
```powershell
docker --version        # Docker version 4.7.x
docker engine version   # 29.5.x
```

### 4. ngrok

ngrok runs as a Docker container — no local install required. You only need a free account and auth token:

1. Sign up at https://ngrok.com (free account)
2. Copy your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
3. Add it to your `.env` file as `NGROK_AUTHTOKEN=your_token_here`

Docker Compose will start ngrok automatically alongside the other services.

### 5. Twilio Account Setup

1. Go to https://www.twilio.com and click **Sign Up** to create a free account
2. Verify your email and phone number
3. From the **Console Dashboard**, copy:
   - **Account SID** — starts with `AC...`
   - **Auth Token** — click the eye icon to reveal
4. Go to **Messaging → Try it out → Send a WhatsApp message**
5. Note the sandbox number: `+14155238886`

You will add these values to `.env` in the setup steps below.

> **Trial account limit:** Free Twilio accounts have a daily outbound message limit
> (error 63038). Upgrade your account at **Console → Billing → Upgrade** to remove
> this limit before production testing.

### 6. Gemini API Key

1. Go to https://aistudio.google.com
2. Click **Get API key → Create API key**
3. Copy the key — you will add it to `.env`

This project uses **Gemini 3.1 Flash Lite**. See:
https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite

---

## Local Setup — Step by Step

---

### Step 1 — Clone the Repository

```powershell
git clone https://github.com/your-org/real-estate-ai-lead-agent.git
cd real-estate-ai-lead-agent
```

> Replace the URL with your actual repository URL.

---

### Step 2 — Configure Environment Variables

```powershell
copy .env.example .env
```

Open `.env` in any editor and fill in all values — see the [.env Reference](#env-reference) section below.
Pay special attention to:
- `GEMINI_API_KEY` — from https://aistudio.google.com
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — from https://console.twilio.com
- `NGROK_AUTHTOKEN` — from https://dashboard.ngrok.com/get-started/your-authtoken
- `CLIENT_KEY_A` — generated by `seed.py` in Step 4

---

### Step 3 — Start Docker Services

This starts PostgreSQL, Redis, Neo4j, ngrok, the Next.js frontend, and **n8n** in one command:

```powershell
docker compose up -d
# n8n only: docker compose up -d n8n  →  http://localhost:5678
```

Verify all containers are running:
```powershell
docker ps
```

You should see `pg-local`, `redis-local`, `neo4j-local`, `ngrok-local`, `frontend-local`, and `n8n-local` all with status `Up`. n8n UI: http://localhost:5678 (owner setup on first visit). See `docs/N8N_INTEGRATION.md`.

Get your ngrok public URL (needed for Twilio webhook):
```powershell
# Open in browser — ngrok inspector shows the live forwarding URL
start http://localhost:4040
```

Or fetch it directly:
```powershell
curl http://localhost:4040/api/tunnels
```

Copy the **https** forwarding URL, e.g. `https://abc123.ngrok-free.app`

> **Container already exists error:** `docker compose down` then re-run `docker compose up -d`

---

### Step 4 — Python Environment + App

Open a PowerShell terminal in the project root:

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate it — you should see (venv) in your prompt
venv\Scripts\activate

# 3. Install dependencies from lock file (exact versions for reproducibility)
pip install -r requirements.lock

# 4. Seed the database — creates tables and generates your API key
python add_client.py (for production)/seed.py (for local testing)
# Output example:
#   Database seeded successfully!
#   Email: admin@revenueos.com
#   Password: password123
#   API Key: a3f8d2...c91b   <-- COPY THIS

# 5. Update CLIENT_KEY_A in .env with the API key from the step above

# 6. Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server is ready when you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify:
```powershell
curl -UseBasicParsing http://localhost:8000/health
```

---

### Twilio Sandbox — Connect Your WhatsApp

1. On your WhatsApp, send `join <word>-<word>` to `+14155238886`
   (the exact words are shown in your Twilio console under Messaging → Try it out → Send a WhatsApp message)
2. You'll receive a confirmation from the sandbox
3. Go to **Twilio Console → Messaging → Try it out → Send a WhatsApp message**
4. Under **"When a message comes in"**, paste:
   ```
   https://abc123.ngrok-free.app/api/v1/whatsapp?api_key=YOUR_CLIENT_KEY_A
   ```
   Replace `abc123.ngrok-free.app` with your current ngrok URL  
   Replace `YOUR_CLIENT_KEY_A` with the key from `seed.py`
5. Set method to **HTTP POST**
6. Click **Save**
7. Send any message to `+14155238886` to test

---

### Frontend (Optional)

The Next.js frontend starts automatically via Docker Compose on port 3000. No separate terminal needed.

Open `http://localhost:3000` in your browser.  
Login: `admin@revenueos.com` / `password123`

> The frontend container mounts `./frontend` and runs `npm install && npm run dev` on startup.
> First boot may take ~2 minutes while npm installs dependencies.

---

## .env Reference

```env
# Gemini AI — get from https://aistudio.google.com
GEMINI_API_KEY=your_gemini_api_key

# Security & Encryption Keys (CRITICAL: Must not be empty in Production)
JWT_SECRET_KEY=your_secure_random_64_char_string
ADMIN_API_KEY=your_secure_admin_passphrase
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_secret

# PostgreSQL — matches the Docker container started above
DATABASE_URL=postgresql://realestate:localpass@127.0.0.1:5432/realestate_db

# Redis — matches the Docker container started above
REDIS_URL=redis://127.0.0.1:6379/0

# Twilio — Account SID and Auth Token from https://console.twilio.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886

# Per-Client API keys (provisioned by seed.py)
CLIENT_KEY_A=paste_seed_output_here
CLIENT_KEY_B=

# ngrok — get from https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTHTOKEN=your_ngrok_auth_token

# Application Modes
IS_PRODUCTION=false
FOLLOW_UP_TEST_MODE=false
FOLLOW_UP_DLQ_TEST=false
TEST_MODE=false

# --- IREIOS 3.0 (production-oriented defaults; flip TEST_* off for real Twilio) ---
# Redis Streams event bus
EVENT_STREAM_KEY=ireios:events
EVENT_CONSUMER_GROUP=ireios-cg

# WhatsApp Agent v3 + follow-up via Automation Engine → Execution Engine
FEATURE_WHATSAPP_V3=true
FOLLOWUP_ENGINE=v3

# Neo4j knowledge graph — host API + docker Neo4j
# Leave NEO4J_URI empty for graceful no-op (chat still works).
# Setup: docker compose up -d neo4j  →  http://localhost:7474  · bolt://localhost:7687
# Auth must match docker-compose NEO4J_AUTH (default neo4j/localpass)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=localpass

# n8n automation (optional — empty = n8n_not_configured; see docs/N8N_INTEGRATION.md)
# Local: docker compose up -d n8n → http://localhost:5678
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=local-n8n-webhook-secret

# Competitor monitor (comma-separated; empty = job no-ops)
COMPETITOR_KEYWORDS=

# Google Calendar (empty = synthetic visit_id stub)
GOOGLE_CALENDAR_ID=
GOOGLE_CALENDAR_CREDENTIALS_JSON=
GOOGLE_CALENDAR_TIMEZONE=Asia/Kolkata

# WhatsApp brochure / floor plan PDF (public HTTPS; empty = plain-text fallback)
BROCHURE_MEDIA_URL=
FLOORPLAN_MEDIA_URL=

# HubSpot CRM optional (crm_sync os.getenv; default demo key = fake UUID in non-prod)
# CRM_API_URL=https://api.hubapi.com/crm/v3/objects/contacts
# CRM_API_KEY=
```

Full template: `.env.example`. Ops notes: `docs/MAINTENANCE.md`.

After API start with Neo4j up: `GET http://localhost:8000/api/v1/graph/health` → `available: true`.

### Event bus SSE smoke (Phase 1b)

```powershell
# Terminal A — live stream (seed client key from seed.py)
curl.exe -N "http://localhost:8000/api/v1/events/stream?api_key=secret-client-key-123"

# Terminal B — inject a demo event (no WhatsApp/LLM required)
python publish_stub_event.py --event-type lead.created --tenant-id Client_1 --payload "{\"name\":\"demo\"}"
```

Auth alternatives: `X-API-Key` header, or browser `EventSource` with HttpOnly `jwt` cookie.  
Timeline: `GET /api/v1/events/leads/{id}/timeline`. Admin stub HTTP: `POST /api/v1/events/stub` + `X-Admin-Token`.  
Contracts: `plans/phase3/IREIOS_3.0_API_SSE_CONTRACTS.md`, FE checklist: `docs/FRONTEND_BACKLOG.md`.  
Full ops runbook: `docs/MAINTENANCE.md`.  
Timeouts & timings map: `docs/TIMEOUTS_AND_TIMINGS.md`.

---

## n8n Automation Workflows (Optional)

n8n is the **external ops plane** for IREIOS — Gmail alerts, Google Sheets CRM logging, HITL notifications, and marketing report emails. It runs as a sidecar and does **not** affect the WhatsApp chat reply path.

### Quick start

```powershell
# 1. Start n8n
docker compose up -d n8n redis
# UI: http://localhost:5678 (create owner account on first visit)

# 2. Full Google Cloud + n8n credentials (one-time) — follow the guide:
#    docs/N8N_GOOGLE_CREDENTIALS_SETUP.md
#    (Gmail/Sheets/Drive/Calendar APIs, OAuth + test users, Header Auth,
#     management JWT, Calendar service account for Python)

# 3. .env: N8N_API_KEY (webhook secret) + N8N_MANAGEMENT_API_KEY (JWT from Settings → n8n API)
# 4. Import workflows
uv run python import_n8n_workflows.py

# 5. In n8n UI: set Gmail To + Publish all 6 workflows (repo ships empty sendTo)
# 6. Smoke webhook (use webhook secret, not management JWT):
curl -X POST "http://localhost:5678/webhook/ireios_hot_lead_alert" `
  -H "Authorization: Bearer local-n8n-webhook-secret" `
  -H "Content-Type: application/json" `
  -d "{\"event_type\":\"lead.hot\",\"tenant_id\":\"Client_1\",\"entity_id\":\"1\",\"payload\":{\"name\":\"Demo\",\"trigger\":\"hot_threshold\",\"score\":90}}"
```

### Active workflows

| WF | Webhook Path | Event | Action |
|----|-------------|-------|--------|
| WF-1 | `ireios_hot_lead_alert` | `lead.hot` | Gmail — hot lead alert with handoff prefix |
| WF-2 | `ireios_visit_fanout` | `site_visit.scheduled` | Gmail — site visit booked (includes Calendar link) |
| WF-3 | `ireios_hitl_notify` | `approval.requested` | Gmail — HITL approval request to manager |
| WF-4 | `ireios_crm_append` | `lead.qualified` | Google Sheets — append lead row |
| WF-5 | `ireios_marketing_csv` | `marketing.report.generated` | Gmail — CSV attachment (Gmail API) |
| WF-6 | (cron 15min) | — | Gmail — DLQ depth monitor |

### Key docs

- **Credential setup:** [`docs/N8N_GOOGLE_CREDENTIALS_SETUP.md`](docs/N8N_GOOGLE_CREDENTIALS_SETUP.md) — full Google Cloud Console walkthrough
- **Architecture:** [`docs/N8N_INTEGRATION.md`](docs/N8N_INTEGRATION.md) — bridge, envelope, workflow details
- **Workflow JSONs:** `n8n_workflows/` — 6 workflow definitions
- **Import script:** `import_n8n_workflows.py` — deploy via n8n REST API

---

## Fresh Session Restart

When returning after closing everything:

```powershell
# 1. Restart Docker services (postgres, redis, neo4j, ngrok, frontend)
docker compose up -d

# 2. Reactivate venv and start the server
cd path\to\project
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **ngrok URL changes on every restart** (free plan). After restarting, get the new URL from
> `http://localhost:4040` and update your Twilio sandbox webhook:
> ```
> https://<new-url>.ngrok-free.app/api/v1/whatsapp?api_key=<CLIENT_KEY_A>
> ```

---

## Resetting Test Data

Postgres and Neo4j are **separate**. Truncating Postgres does **not** clear the graph.  
Connect PG: `psql postgresql://realestate:localpass@localhost:5432/realestate_db`  
Neo4j Browser: `http://localhost:7474` (or cypher-shell).

### Postgres — soft (keep tenants / login)

Wipes CRM traffic; keeps `clients` + `agents` (no need to re-run `seed.py`).

```sql
TRUNCATE
  messages,
  event_logs,
  dlq_events,
  follow_up_states,
  lead_memories,
  approval_requests,
  agent_learning,
  notification_logs,
  leads,
  sessions,
  webhook_logs
RESTART IDENTITY CASCADE;
```

### Postgres — hard (full tenant wipe)

```sql
TRUNCATE
  messages,
  event_logs,
  dlq_events,
  follow_up_states,
  lead_memories,
  approval_requests,
  agent_learning,
  notification_logs,
  leads,
  sessions,
  webhook_logs,
  agents,
  clients
RESTART IDENTITY CASCADE;
```

Then: `python seed.py`

### Neo4j — soft (leads only; keep schema)

```cypher
MATCH (n:Lead) DETACH DELETE n;
```

Optional: drop orphan agent nodes left after lead delete:

```cypher
MATCH (n:Agent) DETACH DELETE n;
```

### Neo4j — hard (all graph data except schema marker)

```cypher
MATCH (n) WHERE NOT n:SchemaVersion DETACH DELETE n;
```

### Fresh WhatsApp test

| Goal | Run |
|------|-----|
| Clean chat/CRM only | Postgres **soft** → send WA |
| Clean chat + clean Browser / similar-lead context | Postgres **soft** + Neo4j **soft** → send WA |
| Nuclear local reset | Postgres **hard** + `seed.py` + Neo4j **hard** |

Dummy bulk load only: `python seed_dummy_leads.py --purge-only` (or full reseed).  
Re-project PG → Neo4j anytime: `python project_leads_to_neo4j.py`.

---

## Project Structure

```
real-estate-ai-lead-agent/
│
├── main.py              # FastAPI app, webhook handler, scheduler, metrics
├── agent.py             # Gemini conversation engine, lead extraction
├── rag.py               # FAISS index, semantic search, context injection
├── follow_up.py         # APScheduler job, follow-up state machine
├── crm_sync.py          # HubSpot sync with retries + DLQ
├── dlq_replay.py        # Dead-letter queue replay runner
├── models.py            # SQLAlchemy ORM models
├── database.py          # DB engine + session factory
├── auth.py              # JWT and API key auth dependencies
├── config.py            # Environment variable loading
├── metrics.py           # Prometheus metrics definitions
├── system_prompt.py     # Agent persona definition
├── seed.py              # DB table creation + client provisioning
├── db_backup.py         # pg_dump wrapper
├── db_restore.py        # psql restore from .sql artifact
│
├── app/intelligence/    # ML scoring, agent matching, follow-up engine
├── data/faq.json        # Property FAQ knowledge base for RAG
├── dashboard/           # Static HTML/CSS/JS CRM dashboard
├── frontend/            # Next.js SaaS dashboard
│   ├── .env.example     # Copy to .env.local for local dev
│   └── src/
│
├── docs/                # All documentation
│   ├── BACKUP_RESTORE_DRILL.md
│   ├── BACKEND_RELIABILITY_CHECKLIST.md
│   ├── API_SCHEMA_AND_VERSIONING.md
│   ├── DLQ_REPLAY_PROCESS.md
│   └── BACKEND_STABILITY_REPORT.md
│
├── prometheus_alerts.yml
├── grafana_dashboard.json
├── final_soak_test_log_20260429_201913.txt
├── requirements.txt         # Unpinned — for local dev / onboarding
├── requirements.lock        # Fully pinned — use this for production deploys
├── Procfile                 # Render start command
├── .env.example             # Variable names only — copy to .env and fill values
└── README.md
```

---

## Key URLs (Local)

| URL                               | Description                       |
|-----------------------------------|-----------------------------------|
| `http://localhost:8000/health`    | Health check                      |
| `http://localhost:8000/docs`      | Swagger UI                        |
| `http://localhost:8000/metrics`   | Prometheus metrics                |
| `http://localhost:8000/dashboard` | Static CRM dashboard              |
| `http://localhost:3000`           | Next.js SaaS dashboard (frontend) |

---

## Observability

Prometheus metrics at `GET /metrics`:
- `http_request_duration_seconds` — latency per endpoint
- `scheduler_job_duration_seconds` — scheduler tick timing
- `scheduler_job_failures_total` — unhandled scheduler crashes
- `integration_failure_total` — permanent CRM/Twilio failures
- `dlq_pending_events` — current DLQ backlog

LLM token cost logged per message in uvicorn:
```json
{"event": "llm_token_usage", "model": "gemini-3.1-flash-lite",
 "input_tokens": 842, "output_tokens": 97, "estimated_cost_usd": 0.000358}
```

Import `grafana_dashboard.json` into Grafana for visual dashboards.

---

## Test Mode (Follow-up Timing Compression)

For testing follow-up sequences without waiting 24h+, add to `.env`:

```env
FOLLOW_UP_TEST_MODE=true
```

This compresses all timings to 1 minute:
- Day 0 fires after 1 minute of silence (instead of 30 minutes)
- Day 0 → Day 1 → Day 3 → Day 7 each advance after 1 minute

For DLQ testing, also add:
```env
FOLLOW_UP_DLQ_TEST=true
```
This forces the scheduler to throw an exception before the ML call, writing a test
entry to `dlq_events`. Remove after testing.

**Always remove both flags before production deploy.**

---

## DLQ Recovery

```powershell
python dlq_replay.py
```

Check depth:
```sql
SELECT target_endpoint, COUNT(*)
FROM dlq_events WHERE status='pending'
GROUP BY target_endpoint;
```

---

## Backup and Restore

```powershell
# Create backup
python db_backup.py
# Output: backups/backup_YYYYMMDD_HHMMSS.sql

# Restore
python db_restore.py backups/backup_YYYYMMDD_HHMMSS.sql
```

See `docs/BACKUP_RESTORE_DRILL.md` for post-restore verification.

---

## Deploying to Render

1. Push codebase to a GitHub repo
2. Go to https://render.com → **New Web Service** → connect your repo
3. Set all environment variables in Render dashboard (same as `.env` but with production values for `DATABASE_URL`, `REDIS_URL`)
4. Render uses `Procfile` automatically:
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
   ```
5. After deploy, verify: `GET https://your-service.onrender.com/health`
6. Update Twilio webhook:
   ```
   https://your-service.onrender.com/api/v1/whatsapp?api_key=YOUR_CLIENT_KEY_A
   ```
7. For the frontend, set `NEXT_PUBLIC_API_URL=https://your-service.onrender.com` in the Render frontend environment variables

> Add a keep-alive cron job at https://cron-job.org to ping `/health` every 10 minutes on free Render tier.

---

## Known Limitations

| Limitation                             | Notes                                                                     |
|----------------------------------------|---------------------------------------------------------------------------|
| `google.generativeai` SDK deprecated   | Warning on startup, API still works. Migrate to `google.genai` post-pilot |
| Single worker on Render free tier      | Upgrade plan for `--workers 2+` under load                                |
| Backup storage is local disk on Render | Render managed DB backups are primary safety net                          |
| `/metrics` is public                   | Restrict at network level in production                                   |
| ROI routes query all clients           | Admin-only — add JWT + client_id filter before client-facing use          |
| A/B follow-up timing always Strategy A | No historical data yet to activate Strategy B                             |

---

## Documentation Index

| File                                    | Contents                                                                                       |
|-----------------------------------------|------------------------------------------------------------------------------------------------|
| `docs/ARITRO_DELIVERABLES.md`           | Complete backend deliverables: checklist, API schema, monitoring, DLQ, backup, bugs fixed      |
| `docs/MAITRI_DELIVERABLES.md`           | Complete automation deliverables: flow map, trigger logic, testing evidence, known limitations |
| `docs/BACKEND_RELIABILITY_CHECKLIST.md` | Acceptance criteria audit                                                                      |
| `docs/API_SCHEMA_AND_VERSIONING.md`     | Full endpoint reference                                                                        |
| `docs/DLQ_REPLAY_PROCESS.md`            | DLQ event types, replay, escalation                                                            |
| `docs/BACKUP_RESTORE_DRILL.md`          | Backup/restore procedure                                                                       |
| `docs/BACKEND_STABILITY_REPORT.md`      | Pilot-readiness sign-off                                                                       |

---

*Real Estate Revenue OS — Phase 1 Backend | Imperion Data Systems*