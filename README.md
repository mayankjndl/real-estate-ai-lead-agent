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
asyncio.wait_for(process_unified_lead(), timeout=15s)
  ├── RAG context injection (rag.py + FAISS)
  ├── Gemini 3.1 Flash Lite
  └── extract_lead_info() tool → saves to Lead table
      ↓
TwiML response → WhatsApp reply
      ↓
BackgroundTask: crm_sync.py → HubSpot (5 retries + DLQ)
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

This starts PostgreSQL, Redis, ngrok, and the Next.js frontend in one command:

```powershell
docker compose up -d
```

Verify all containers are running:
```powershell
docker ps
```

You should see `pg-local`, `redis-local`, `ngrok-local`, and `frontend-local` all with status `Up`.

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
python seed.py
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

### Twilio Sandbox — Connect Your WhatsApp### Twilio Sandbox — Connect Your WhatsApp

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

# Internal admin key — any string for local dev
API_AUTH_KEY=anything

# PostgreSQL — matches the Docker container started above
DATABASE_URL=postgresql://realestate:localpass@localhost:5432/realestate_db

# Redis — matches the Docker container started above
REDIS_URL=redis://localhost:6379/0

# Twilio — Account SID and Auth Token from https://console.twilio.com
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886

# API key from seed.py output
CLIENT_KEY_A=paste_seed_output_here
CLIENT_KEY_B=

# ngrok — get from https://dashboard.ngrok.com/get-started/your-authtoken
NGROK_AUTHTOKEN=your_ngrok_auth_token

# Production flag — leave false for local dev, set true on Render
IS_PRODUCTION=false
```

---

## Fresh Session Restart

When returning after closing everything:

```powershell
# 1. Restart Docker services (postgres, redis, ngrok, frontend)
docker compose up -d

# 2. Reactivate venv and start the server
cd path\to\project
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> **ngrok URL changes on every restart** (free plan). After restarting, get the new URL from
> `http://localhost:4040` and update your Twilio sandbox webhook:
> ```
> https://<new-url>.ngrok-free.app/api/v1/whatsapp?api_key=<CLIENT_KEY_A>
> ```

---

## Resetting Test Data

To clear all lead data and start fresh without touching containers:

```sql
-- Connect first:
-- psql postgresql://realestate:localpass@localhost:5432/realestate_db

TRUNCATE messages, event_log, dlq_events, follow_up_states, leads, sessions
RESTART IDENTITY CASCADE;
```

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