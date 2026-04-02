# Core: Real Estate AI Assistant & CRM System

An advanced, client-grade AI backend that functions symmetrically as a Real Estate Sales Assistant, a CRM suite, and a Data Analytics engine. Built with FastAPI and powered by Gemini 2.5 Flash.

## 🚀 Major Features (V2 Update)

- **Multi-Tenant Client Architecture:** Secure `client_id` tracking ensures multiple vendor clients can utilize the AI agent while maintaining completely isolated, dedicated SQLite CRM environments via dynamic config dictionaries.
- **Dynamic NLP Execution:** Replaces traditional `if/else` chatbot bots; uses natively-prompted LLM function-calling to orchestrate objection handling, negotiation, and fallbacks.
- **Silent Data Extraction:** Real-time semantic extraction of customer profiles (Name, Phone, Budget, Location, Intent) while chatting.
- **Intelligent Lead Scoring:** Leads are auto-evaluated as High, Medium, or Low intent based on timeline metrics.
- **Advanced CSV Exporting:** Instantaneous `StreamingResponse` endpoints generate direct `.csv` downloads mapping full database CRM ledgers for frontend dashboard integration.
- **Robust 30+ Turn Memory Validation:** The orchestrator binds conversational contexts tightly across `session_ids` via persistent SQLAlchemy stores.

## 🛠️ Technology Stack
- **Framework:** FastAPI
- **AI Engine:** Google Generative AI (Gemini 2.5 Flash)
- **Database:** SQLAlchemy (SQLite)
- **Configuration & Typing:** Pydantic -> Pydantic Settings
- **Server Environment:** Uvicorn 

## 📦 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mayankjndl/real-estate-ai-lead-agent.git
   cd real-estate-ai-lead-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration (`.env`):**
   ```env
   GEMINI_API_KEY=your_google_ai_key
   ```

5. **Run the Application:**
   ```bash
   uvicorn main:app --reload
   ```

## 🔐 API Reference Overview

**Data Entry & Multi-Turn AI**
- `POST /api/v1/chat`
  - *Description:* Submit contextual user messages tracked via custom `{session_id}`. Includes backend parsing handling `client_id`.

**Secured Analytics Payload**
- `GET /api/v1/analytics`
  - *Headers:* `X-API-Key: {your_client_key}`
  - *Description:* Fetches unified stats tracking your active conversion rate, lifetime sessions, intent-routing (Rent/Buy/Browser counts).

**Targeted CRM Data Mapping**
- `GET /api/v1/leads`
  - *Headers:* `X-API-Key: {your_client_key}`
  - *Query Params:* `?intent=buy`, `?score=High`, `?location=Pune`

**CSV Streaming Extraction**
- `GET /api/v1/leads/export`
  - *Headers:* `X-API-Key: {your_client_key}`
  - *Description:* Instant CRM trigger generating full database tabular snapshots tailored for business-grade tools.

---
*Developed globally as part of the advanced LLM Automation track (Task 5).*
