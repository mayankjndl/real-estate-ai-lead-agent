# Enterprise Real Estate AI Agent & CRM System

A full-stack, production-ready AI Real Estate Assistant and autonomous CRM. Built utilizing **FastAPI**, **Gemini 2.5 Flash**, **Twilio (WhatsApp)**, and **FAISS Vector Search (RAG)**, this service functions symmetrically as an automated sales agent, an intent-scoring lead generator, and a real-time data analytics dashboard.

---

## 🚀 System Architecture & Major Features

### 🟢 Multi-Channel Interoperability (WhatsApp + Web)
- **Twilio Webhook Engine:** Synchronously parses inbound Meta/WhatsApp traffic via `POST /api/v1/whatsapp`.
- **Contextual Routing:** Bypasses manual friction by stripping payload tags (`whatsapp:+91...`) and injecting the user's secure smartphone identifier instantly into the SQLite backend as the unified `session_id`.
- **Latency Optimization:** Standard benchmarking maintains sub-3-second synchronous dispatch utilizing native `TwiML` payload bridging.

### 🧠 Anti-Hallucination Framework (RAG)
- **FAISS Vector Encoding:** Leverages `models/gemini-embedding-001` sub-L2 arrays to map an internal corporate inventory dictionary (`data/faq.json`).
- **Dynamic Prompt Engineering:** Exact pricing, inventory availability (e.g., *Wakad 2BHKs*), and locations are proactively grounded into the Gemini prompt pipeline (`agent.py`) via similarity search prior to any LLM generation. 
- **Strict Boundary Escalation:** The engine natively catches semantic confusion and executes human-fallback loops (`+91 9876543210`) preventing the AI from generating hallucinatory promises.

### 📊 Real-Time CRM Web Dashboard
- **FastAPI Native Mount:** A pristine, dark-mode GUI (`/dashboard`) operates entirely native to the Python backend; no heavy Node layers required.
- **Dynamic Telemetry:** JavaScript polling autonomously pulls live `Total Sessions`, `Capture Rates`, and `Intent Sorting` filtering directly from secured `X-API-Key` analytics nodes.

### ⏱️ Automated Re-Engagement Subsystem
- **Chronological APScheduler:** A background thread passively monitors SQLite state. If any customer session remains idle for exactly 120 minutes, the orchestrator triggers.
- **Physical Outbound Push:** Leverages the `twilio.rest.Client` to actively execute an outbound API bridge, pinging the AI-personalized follow-up message to the customer's physical device.
- **Graceful Termination:** Closes the session after 2 outbound attempts to prevent harassment block-listing.

---

## 🛠️ Technology Stack
- **Framework:** FastAPI / Uvicorn
- **AI Core:** Google Generative AI (Gemini 2.5 Flash)
- **Database Architecture:** SQLAlchemy (SQLite)
- **Vector Search:** FAISS / Numpy
- **Asynchronous Tasks:** APScheduler
- **Communications:** Twilio Python Client / `python-multipart`
- **Configuration:** Pydantic Core

---

## 📦 Setup & Installation

### 1. Clone & Environment
```bash
git clone https://github.com/mayankjndl/real-estate-ai-lead-agent.git
cd real-estate-ai-lead-agent
python -m venv venv

# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
# Core AI Keys
GEMINI_API_KEY=your_google_gemini_key

# CRM Security Keys
API_AUTH_KEY=secret-client-key-123

# Twilio WhatsApp Sandbox (Optional for Outbound Pushes)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
```

### 4. Boot Sequence
```bash
uvicorn main:app --reload
```
---

## 🧭 Navigating the System

**1. The Application Endpoints**
- Swagger UI / API Testing: `http://127.0.0.1:8000/docs`
- CRM Web Interface: `http://127.0.0.1:8000/dashboard/index.html`

**2. Simulation Testing**
To observe the multi-turn memory matrix and RAG grounding locally:
```bash
python test_advanced_scenarios.py
```

**3. Database Extraction**
Navigating to `GET /api/v1/leads/export` instantly generates and downloads raw `.csv` accounting of all active/past captured data tables for cross-platform importation.
