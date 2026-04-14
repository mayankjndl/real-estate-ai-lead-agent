# 🏠 Real Estate AI Lead Agent

> A production-ready, WhatsApp-native AI agent that qualifies real estate leads, maintains contextual conversations, extracts structured CRM data, and automates follow-ups — handling 90–95% of real-world customer interactions without human intervention.

[![Python](https://img.shields.io/badge/Python-3.11.9-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5--Flash-orange?logo=google)](https://ai.google.dev)
[![Twilio](https://img.shields.io/badge/Twilio-WhatsApp-red?logo=twilio)](https://twilio.com)
[![Render](https://img.shields.io/badge/Deployed-Render.com-purple)](https://render.com)

---

## What It Does

A customer messages your WhatsApp number. The AI agent:

1. **Greets and qualifies** — understands what they're looking for (buy/rent/invest), where, and at what budget
2. **Holds full context** — remembers everything said in the conversation, refines recommendations as the user changes their mind
3. **Extracts structured data** — name, phone, location, budget, intent, lead score — and saves it to the CRM automatically using Gemini function calling
4. **Uses a property knowledge base** — answers FAQ questions (locations served, property types, process) using a RAG (Retrieval-Augmented Generation) system backed by FAISS
5. **Follows up automatically** — if the user goes quiet, sends up to 2 follow-up messages on a timer before closing the session
6. **Handles failures gracefully** — retries on AI errors, dispatches slow responses to a background thread, never crashes

---

## Live Demo

| Resource | URL |
|---|---|
| Health Check | `https://real-estate-ai-lead-agent-1.onrender.com/health` |
| CRM Dashboard | `https://real-estate-ai-lead-agent-1.onrender.com/dashboard` |
| Leads API | `https://real-estate-ai-lead-agent-1.onrender.com/api/v1/leads` |
| Analytics API | `https://real-estate-ai-lead-agent-1.onrender.com/api/v1/analytics` |

---

## Architecture

```
WhatsApp (User)
      │
      ▼
Twilio WhatsApp Sandbox
      │  POST /api/v1/whatsapp
      ▼
FastAPI Webhook (main.py)
      │
      ├── Duplicate MessageSid check  ──► ignore if already seen
      │
      ├── asyncio.wait_for(process_chat, timeout=15s)
      │         │
      │    ┌────┴────────────────────────────┐
      │    │ < 15s                           │ > 15s (timeout)
      │    ▼                                 ▼
      │  Gemini 2.5 Flash              Return interim TwiML
      │  (with RAG context)            + background_dispatch()
      │    │                                 │
      │    ├── extract_lead_info()           │ (continues in background)
      │    │   └── Save to SQLite CRM        │
      │    │                                 │
      │    └── Return TwiML reply ◄──────────┘
      │
      ▼
APScheduler (every 60s)
      └── check inactive sessions → send follow-up #1 → #2 → close
```

---

## Features

### 🤖 AI Conversation Engine
- Powered by **Google Gemini 2.5 Flash** for fast, accurate, contextual responses
- Full conversation memory within a session — the AI understands context changes ("actually, I want to rent instead")
- Persona-driven: acts as a professional real estate advisor named "Anohita" from ABC Properties
- Operates within a defined scope — politely declines out-of-area requests (e.g., Delhi when only serving Pune)

### 📚 RAG (Retrieval-Augmented Generation)
- A FAISS vector index is built from a curated FAQ dataset at startup
- Every user message is semantically matched against the knowledge base using Gemini embeddings
- Relevant context is injected into the AI's prompt before each response
- Falls back gracefully if the index is unavailable (lazy initialization)

### 🧠 Automatic Lead Extraction
- Gemini uses **native function calling** to call `extract_lead_info()` when qualifying data is detected
- Extracts: `name`, `phone`, `budget`, `location`, `intent` (buy/rent/invest), `lead_score` (High/Medium/Low)
- Scores leads based on intent urgency and budget signals
- Stored to a persistent SQLite database via SQLAlchemy

### 🔔 Automated Follow-up System
- **APScheduler** runs every 60 seconds on the server
- If a session is inactive for > N minutes, sends a follow-up WhatsApp message via Twilio REST API
- Sends at most 2 follow-ups — session is permanently closed after 2 unanswered messages
- State tracked via `follow_up_count` in the database — **never sends a duplicate follow-up**

### 🛡️ Reliability & Fault Tolerance
- **Duplicate protection**: every `MessageSid` is stored; duplicate webhook calls are silently ignored
- **Gemini retry logic**: exponential backoff retry (up to 2 attempts) on API errors
- **Timeout handling**: 15-second async timeout — slow responses fall back to background thread dispatch
- **Fallback messaging**: if all AI retries fail, a coherent fallback message is returned — never an empty or broken response
- **Structured logging**: every request emits a `LATENCY`, `FALLBACK`, or `TIMEOUT` log entry for full observability

### 📊 Real-Time CRM Dashboard
- Built with Vanilla HTML/CSS/JS, served directly by FastAPI as a static mount
- Displays total sessions, leads captured, conversion rate, and follow-up system status
- Full leads table: name, phone, location, budget, intent, score, last updated timestamp
- Filter by intent (buy/rent/invest) and score (high/medium/low)
- One-click CSV export

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Engine | Google Gemini 2.5 Flash |
| Function Calling | Gemini Native Tool Use |
| Vector Search | FAISS + Gemini Embedding-001 |
| Backend API | FastAPI + Uvicorn |
| Messaging | Twilio WhatsApp API |
| Scheduler | APScheduler |
| Database | SQLite + SQLAlchemy ORM |
| Frontend Dashboard | Vanilla HTML / CSS / JS |
| Deployment | Render.com |
| Language | Python 3.11.9 |

---

## Project Structure

```
real-estate-ai-lead-agent/
│
├── main.py              # FastAPI app, webhook handler, timeout logic, structured logging
├── agent.py             # Gemini conversation engine, retry logic, lead extraction
├── rag.py               # FAISS index builder, semantic search, context injection
├── follow_up.py         # APScheduler, follow-up logic, Twilio outbound push
├── models.py            # SQLAlchemy ORM models (Session, Lead, WebhookLog)
├── database.py          # Database engine and session factory
├── config.py            # Environment variable loading and configuration
├── system_prompt.py     # Agent persona, scope, and tone definition
│
├── data/                # FAQ knowledge base for RAG
│   └── faq.json
│
├── dashboard/           # CRM frontend
│   ├── index.html
│   ├── styles.css
│   └── script.js
│
├── requirements.txt     # Python dependencies
├── Procfile             # Render.com start command
└── .python-version      # Python version pin (3.11.9)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://ai.google.dev)
- A [Twilio account](https://twilio.com) with WhatsApp Sandbox enabled

### 1. Clone the Repository

```bash
git clone https://github.com/mayankjndl/real-estate-ai-lead-agent.git
cd real-estate-ai-lead-agent
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
API_AUTH_KEY=your_dashboard_api_key_here

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### 5. Run Locally

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Expose your local server to Twilio using [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Set the ngrok HTTPS URL as your Twilio WhatsApp Sandbox webhook:
```
https://<your-ngrok-id>.ngrok.io/api/v1/whatsapp
```

---

## Deploying to Render

1. Push this repository to GitHub
2. Create a new **Web Service** on [Render.com](https://render.com)
3. Connect your GitHub repo
4. Set all environment variables in the Render dashboard
5. Render will auto-detect the `Procfile` and deploy

The `Procfile` contains:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

For production stability, configure a free keep-alive ping at [cron-job.org](https://cron-job.org) to hit `GET /health` every 10 minutes.

---

## API Reference

All protected endpoints require the header: `X-API-Key: <your_api_auth_key>`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/whatsapp` | Twilio signature | Main webhook — handles all inbound WhatsApp messages |
| `GET` | `/health` | None | Health check — confirms DB connectivity |
| `GET` | `/api/v1/leads` | ✅ | Returns all captured leads with optional `intent` and `score` filters |
| `GET` | `/api/v1/leads/export` | ✅ | Downloads all leads as a CSV file |
| `GET` | `/api/v1/analytics` | ✅ | Returns session count, lead count, and conversion rate |
| `GET` | `/dashboard` | None | Serves the real-time CRM dashboard |

---

## Observability

Every processed request emits one of three structured log entries:

```
# Successful response
INFO:main: LATENCY | session=+91XXXXXXXXXX | 5243ms | status=delivered

# AI failure → graceful fallback
WARNING:main: FALLBACK | session=+91XXXXXXXXXX | reason=ResourceExhausted | detail=429...

# Response exceeded 15s → background dispatch
INFO:main: TIMEOUT | session=+91XXXXXXXXXX | exceeded=15000ms | action=background_dispatch
```

These are visible in the Render log stream in real time.

---

## Performance

Tested under real production conditions with live WhatsApp messages:

| Metric | Value |
|---|---|
| Typical response time | 3 – 8 seconds |
| Max observed latency | ~14.5 seconds (within 15s threshold) |
| Fallback trigger | < 5% of requests under normal quota |
| Follow-up accuracy | 100% — no duplicate triggers observed |
| Duplicate webhook protection | 100% — all re-delivered SIDs correctly ignored |
| CRM extraction accuracy | Name, budget, location, intent, score from natural language |

---

## Configuration Reference

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `FOLLOW_UP_DELAY_MINUTES` | `3` | Minutes of inactivity before first follow-up |
| `MAX_FOLLOW_UPS` | `2` | Maximum follow-up messages per session |
| `WEBHOOK_TIMEOUT_SECONDS` | `15` | Max seconds before background dispatch |
| `GEMINI_MAX_RETRIES` | `2` | Retry attempts on Gemini API failure |

---

## License

MIT License. See `LICENSE` for details.

---

*Built with FastAPI, Google Gemini, and Twilio WhatsApp API.*
