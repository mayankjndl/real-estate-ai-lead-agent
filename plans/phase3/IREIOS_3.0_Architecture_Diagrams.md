# IREIOS 3.0 — Architecture Diagrams

Canonical **system architecture** for Imperion Real Estate Intelligence OS (Phase 3.0).

| This doc owns | Sibling docs own |
|---|---|
| Layers 1–11, components, Path A–E, event catalog, KG overview, tech map | **Workflows** → `IREIOS_3.0_AI_Automation_Workflows.md` |
| | **Implementation** → `IREIOS_3.0_IMPLEMENTATION_PLAN.md` |
| | **Step-by-step** → `IREIOS_3.0_STEP_BY_STEP_EXPANSION.md` |
| | **Execution order** → `UNIFIED_EXECUTION_ORDER.md` |

Sources: Phase 3 direction assignment (PDF), multi-agent overview (JPEG), refined Path A–E design.

Diagrams use [Mermaid](https://mermaid.js.org). Preview: VS Code **Markdown Preview Mermaid Support**, or [mermaid.live](https://mermaid.live).

---

## Legend

| Color | Meaning |
|---|---|
| Gray | Infrastructure / triggers / neutral |
| Blue | Data & execution (API gateway, engines, writes) |
| Teal | Events / message bus / memory bus |
| Purple | AI agents / CEO orchestrator |
| Amber | Decisions / scoring / approval gates |
| Coral | Fan-out, failure, escalation, HITL reject |

---

## 1. Canonical layers (PDF contract)

Joint deliverable layers. Numbers below are **authoritative** for planning and APIs.

| Layer | Name | Backend (this repo) | Frontend (Mayank) |
|---|---|---|---|
| **1** | CEO AI Orchestrator | Agent registry, scheduler, task queue, agent memory hooks, health, communication bus | — |
| **2** | AI Agents | Full: WhatsApp, Sales, Marketing, CRM automation, Customer Success, Competitor (+ handlers). Placeholders for remaining of “15” | Surfaces via dashboard / copilot |
| **3** | Knowledge Graph | Neo4j schema, relationships, Graph APIs, query engine, versioned schema, async writers | KG visualization |
| **4** | Forecast / Predictive Engine | Lead score, booking, revenue, cancel risk, cashflow, inventory APIs (build on `app/intelligence`) | Forecast widgets |
| **5** | Digital Twin MVP | Event/SSE feeds + graph snapshots | Digital Twin UI |
| **6** | Autonomous Execution | **Automation Engine** + **Execution Engine** (n8n, LangGraph, templates, retry, fallback, HITL) | Approval UI hooks |
| **7** | Negotiation AI (prototype) | Placeholder agent + workflow hook | — |
| **8** | Self-Learning | Feedback loops into models/playbooks (incremental) | — |
| **9** | Company / AI Memory | Conversation, long-term, decision, action memory + context retrieval | Timeline / memory views |
| **10** | Market Intelligence | Competitor monitoring + alerts | Market panels |
| **11** | Executive Command Interface | Prediction + SSE + chat APIs | Dashboard, AI Chat, Command Center |

**Product story flow (JPEG):** sources → lead in → qualify/store → CEO → actions → dashboard, with agents ↔ graph ↔ predictive ↔ execution ↔ memory ↔ market intel ↔ self-learning. Same system; PDF layer IDs above are used in code and docs.

---

## 2. System overview

```mermaid
flowchart TB
    subgraph SRC["External sources"]
        S1[WhatsApp / Twilio]
        S2[Website chat]
        S3[Meta / Google Ads]
        S4[CRM / Portals / Email]
    end

    GW[API Gateway<br/>RBAC · tenant · rate limit · audit]
    BUS[Event Bus]
    CEO[L1 CEO Orchestrator<br/>registry · route · queue · health]
    AG[L2 Agents & workflows<br/>WA · Sales · Mkt · CRM · CS · Competitor · placeholders]
    AE[L6 Automation Engine<br/>validate · LangGraph · n8n · linear · HITL]
    EE[L6 Execution Engine<br/>Twilio · CRM · Calendar · Notify · Ads…]
    KG[L3 Neo4j Knowledge Graph]
    MEM[L9 Company / AI Memory]
    PE[L4 Predictive Engine]
    MI[L10 Market Intelligence]
    SL[L8 Self-Learning]
    FE[L5/L11 SSE + APIs → Dashboard · Twin · Timeline · KG viz · Copilot]

    S1 & S2 & S3 & S4 --> GW --> BUS --> CEO --> AG
    AG --> AE --> EE
    EE -->|success / failure events| BUS
    BUS --> KG
    BUS --> MEM
    BUS --> PE
    BUS --> FE
    BUS --> MI
    KG --> PE
    MEM --> AG
    PE --> AG
    MI --> SL
    MEM --> SL
    SL --> AG
    AE -.->|requires_approval| HITL[HITL Approval Queue]
    HITL -->|approve / reject| AE

    classDef gray fill:#F1EFE8,stroke:#5F5E5A,color:#2C2C2A;
    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef purple fill:#EEEDFE,stroke:#534AB7,color:#3C3489;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;
    classDef coral fill:#FAECE7,stroke:#993C1D,color:#712B13;

    class S1,S2,S3,S4,SL gray
    class GW,AE,EE blue
    class BUS,MEM teal
    class CEO,AG purple
    class PE,HITL amber
    class KG,MI,FE coral
```

### Core runtime rule

```
Event → CEO routes → Agent decides → Automation Engine plans/HITL → Execution Engine acts → Event → fan-out
```

No silent side effects: external writes go through **Execution Engine** and publish result events.

---

## 3. Component inventory

| Component | Role | Tech (target) |
|---|---|---|
| API Gateway | Auth, RBAC, tenant, webhooks, public/prediction APIs | FastAPI `main.py` |
| Event Bus | Pub/sub nervous system (durable) | **Redis Streams from Day 1** (consumer groups; n8n-subscribable) |
| CEO Orchestrator | Registry, route by event/policy, task queue, health, agent comms | Python `app/orchestrator` |
| Agents (L2) | Stateless: fetch context → analyze → decide (action request) | `app/agents` |
| Workflows | Deterministic automations (CRM tags, follow-up poll, competitor cron) | `app/workflows` |
| Automation Engine | Validate action, load template, LangGraph / n8n / linear, HITL pause/resume | `app/automation_engine` + n8n + LangGraph |
| Execution Engine | Dumb executors: API call in → success/error out | `app/execution_engine` |
| Knowledge Graph | Entities + relationships; query APIs; async ingest from events | Neo4j + `app/knowledge_graph` |
| AI / Company Memory | Conversation, long-term, decision, action; retrieval for agents | Postgres + vectors (FAISS/embeddings) + graph context |
| Predictive Engine | Scoring & forecast APIs | `app/intelligence` + HTTP surface |
| Market Intelligence | Competitor / demand signals | Workflow + events |
| SSE / realtime | Pulse dashboard, timeline, twin | FastAPI SSE → frontend |
| DLQ + replay | Failed external calls | `dlq_events` + `dlq_replay.py` |
| Scheduler | Time-based work outside pure event path | APScheduler |

---

## 4. Event catalog (canonical)

Names are stable contracts across backend, AE/EE, Neo4j writers, and FE.

### 4.1 PDF-required business events

| Event | When | Typical consumers |
|---|---|---|
| `lead.created` | New lead row / first contact | CRM automation, Memory, KG, Follow-up |
| `lead.assigned` | Human/AI agent assignment | Sales, Dashboard, KG |
| `whatsapp.sent` | Outbound WA delivered/accepted by executor | Memory, Timeline, KG |
| `call.made` | Call logged | Memory, KG, Sales |
| `site_visit.scheduled` | Visit booked | Calendar result, Memory, KG, Sales |
| `booking.confirmed` | Booking done | CS, Memory, KG, Predictive |
| `payment.received` | Payment recorded | CS, Memory, KG, Predictive |

### 4.2 Runtime / pipeline events

| Event | When | Typical consumers |
|---|---|---|
| `whatsapp.received` | Inbound WA webhook accepted | CEO → WhatsApp AI |
| `chat.received` | Website chat message | CEO → WhatsApp/Chat AI |
| `lead.qualified` | Enough fields for qualification | CRM automation, Predictive, Sales |
| `lead.scored` | Score/temperature updated | Sales, Dashboard |
| `lead.hot` | High-intent threshold **or** explicit human handoff | Notification, Sales, n8n |
| `lead.negotiation.started` | User mentions negotiation OR budget misaligned | Negotiation agent, HITL, Dashboard |
| `lead.crm_synced` | CRM executor success | KG, Dashboard |
| `followup.sent` | Scheduled follow-up sent | Memory, Timeline |
| `whatsapp.response.generated` | Agent finished reply analysis (async side work) | Lead scoring handler |
| `brochure.sent` / `floorplan.sent` | Document media sent | Memory, Timeline, KG |
| `market.alert.generated` | Competitor/intel alert | Marketing, Sales, Dashboard |
| `approval.requested` / `approval.resolved` | HITL | AE resume, Memory, Dashboard |
| `*.failed` / DLQ write | Executor exhausted retries | Ops, replay |

Payload envelope (all events):

```text
event_id, event_type, tenant_id, entity_id, source, timestamp, correlation_id, payload
```

### 4.3 Payload conventions (automations closeout + negotiation)

Do **not** add parallel product event types for the same business signal. Prefer richer `payload` + dual-publish aliases where shipped:

| Event | Convention |
|-------|------------|
| `lead.hot` | `payload.trigger` = `hot_threshold` \| `human_handoff`; optional `chat_context`, `score`, `assigned_agent`. Dual-publish alias: `lead.escalated` (same payload). |
| `lead.qualified` / `conversation.updated` | Optional `chat_context` (transcript summary). Close also dual-publishes `session.completed`. |
| `site_visit.scheduled` | Merge EE result + schedule params: `visit_id`, `visit_date`, `name`, `phone`, `provider`, `html_link`. |
| `approval.requested` | Include `approval_id` + relative approve/reject paths for n8n. |
| `lead.negotiation.started` | `payload.trigger` = `user_phrase` \| `budget_misaligned`; includes `budget`, `budget_alignment_status`, `message[:200]`. Sets `lead.is_negotiating = True` (UI badge). No HITL pause — human agent claims from dashboard. |

### 4.4 PR #10 dual-publish aliases (n8n convenience)

Not separate long-term catalog entries — **mirrors** of primary events for workflows that used review names:

| Alias | Mirrors | Notes |
|-------|---------|--------|
| `lead.escalated` | `lead.hot` | Same payload; `payload.trigger` = `hot_threshold` \| `human_handoff` |
| `session.completed` | session close path (alongside `lead.qualified` for fields) | `close_reason` + `chat_context` |

`site_visit.scheduled` is published by the **Execution Engine** after `CalendarExecutor` success (`register_event`), not by the executor itself.

Full closeout: `plans/phase3/PHASE3_AUTOMATIONS_CLOSEOUT.md`. Ops detail: `docs/N8N_INTEGRATION.md` § Dual-publish aliases.

---

## 5. Knowledge Graph overview (Layer 3)

### 5.1 Entities (PDF)

Leads · Projects · Towers · Units · Customers · Payments · Salespersons · Inventory · Site Visits · Documents · Calls · WhatsApp Conversations · Emails

### 5.2 Core relationships (illustrative)

```text
(:Client/Tenant)-[:OWNS]->(:Lead|:Project|…)
(:Lead)-[:INTERESTED_IN]->(:Project|:Unit)
(:Lead)-[:ASSIGNED_TO]->(:Salesperson)
(:Lead)-[:HAS_CONVERSATION]->(:WhatsAppConversation|:Email)
(:Lead)-[:SCHEDULED]->(:SiteVisit)
(:Lead)-[:BECAME]->(:Customer)
(:Customer)-[:MADE]->(:Payment)
(:Project)-[:HAS_TOWER]->(:Tower)-[:HAS_UNIT]->(:Unit)
(:Unit)-[:IN_INVENTORY]->(:Inventory)
(:Document)-[:ABOUT]->(:Project|:Unit)
(:Call)-[:WITH]->(:Lead)
```

Postgres remains **transactional source of truth** for leads/sessions/messages. Neo4j is the **relationship & traversal** layer; writes from the bus are **async** so chat latency is protected.

### 5.3 Graph API surface (backend-owned)

- Schema version + migrate  
- Upsert entity / relationship  
- Query: lead context, project inventory, agent workload, conversation links  
- Used by agents via `GraphClient` and by FE KG visualization  

---

## 6. AI Memory (Layer 9)

| Memory type | Content | Used by |
|---|---|---|
| Conversation | Recent turns (Postgres messages + window) | WhatsApp AI |
| Long-term | Stable lead prefs, objections, outcomes | All agents |
| Decision | Why agent chose an action | Audit, self-learning |
| Action | What was executed + result | Timeline, DLQ context |
| Context retrieval | Ranked pull across memory + graph + RAG (FAISS) | Agent `fetch_context` |

---

## 7. Execution paths A–E

### Path A — Lead intake & qualification (part 1)

```mermaid
flowchart TD
    A1[WhatsApp message] --> A2[API Gateway<br/>RBAC + tenant]
    A2 --> A3[Event Bus<br/>whatsapp.received]
    A3 --> A4[CEO Orchestrator<br/>route to WhatsApp AI]
    A4 --> A5[Context fetch<br/>Postgres · FAISS · Memory · Neo4j]
    A5 --> A6{Enough info to qualify?}
    A6 -->|No| A7[Clarifying question<br/>via AE → EE → whatsapp.sent]
    A6 -->|Yes| B1

    classDef gray fill:#F1EFE8,stroke:#5F5E5A,color:#2C2C2A;
    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef purple fill:#EEEDFE,stroke:#534AB7,color:#3C3489;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;

    class A1,A7 gray
    class A2 blue
    class A3 teal
    class A4,A5 purple
    class A6 amber
    class B1 teal
```

### Path A — Qualified lead fan-out (part 2)

```mermaid
flowchart TD
    B1[Action request<br/>e.g. update_lead / qualify]
    B2[Automation Engine<br/>template · validate]
    B3[Execution Engine<br/>CRM / DB executor]
    B4[Event Bus<br/>lead.qualified]
    B5[Neo4j async write]
    B6[Company Memory]
    B7[SSE → Dashboard / Timeline]

    B1 --> B2 --> B3 --> B4
    B4 --> B5
    B4 --> B6
    B4 --> B7

    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef coral fill:#FAECE7,stroke:#993C1D,color:#712B13;

    class B1 teal
    class B2,B3 blue
    class B4,B6 teal
    class B5,B7 coral
```

### Path A — Scoring to confirmation (part 3)

```mermaid
flowchart TD
    C1[CRM automation<br/>tags · assign → lead.assigned]
    C2[Predictive Engine<br/>score / temperature]
    C3[Sales AI<br/>next best action]
    C4{requires_approval?}
    C5[AE → EE Calendar<br/>site_visit.scheduled]
    C6[WhatsApp confirm<br/>whatsapp.sent]
    C7[Path C HITL queue]

    C1 --> C2 --> C3 --> C4
    C4 -->|No| C5 --> C6
    C4 -->|Yes| C7

    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef purple fill:#EEEDFE,stroke:#534AB7,color:#3C3489;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;
    classDef coral fill:#FAECE7,stroke:#993C1D,color:#712B13;

    class C1,C3 purple
    class C2,C4 amber
    class C5 blue
    class C6 teal
    class C7 coral
```

WhatsApp AI may also: FAQ (RAG), **brochure**, **floor plan**, site-visit request, escalation — behavior detail in Workflows doc.

### Path B — Multi-turn conversation

Not a separate topology. Each new inbound message republishes `whatsapp.received` and re-enters Path A. Context fetch loads short-term conversation memory and long-term extracted intent so the agent only asks for missing fields until qualification succeeds.

### Path C — Human-in-the-loop (HITL)

```mermaid
flowchart TD
    D1[Agent / workflow sets<br/>requires_approval = true]
    D2[Automation Engine pauses<br/>LangGraph state / n8n wait]
    D3[Notify manager<br/>Dashboard / WhatsApp]
    D4{Manager decision}
    D5[Rejected → Memory]
    D6[Approved → resume plan]
    D7[EE executes · result event<br/>→ Neo4j · Memory · SSE]

    D1 --> D2 --> D3 --> D4
    D4 -->|Reject| D5 --> D7
    D4 -->|Approve| D6 --> D7

    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef purple fill:#EEEDFE,stroke:#534AB7,color:#3C3489;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;
    classDef coral fill:#FAECE7,stroke:#993C1D,color:#712B13;

    class D1 purple
    class D2 blue
    class D3,D4 amber
    class D5 coral
    class D6,D7 teal
```

HITL is a **core path**, not a late add-on. Sales discounts, campaign spend changes, and high-risk actions use it.

### Path D — Execution failure (disaster recovery)

```mermaid
flowchart TD
    E1[Executor API fails<br/>Twilio · HubSpot · Meta…]
    E2[Retry with backoff]
    E3{Retry limit?}
    E4[Fallback channel<br/>e.g. email]
    E5{Fallback ok?}
    E6[DLQ dlq_events]
    E7[dlq_replay when healthy]

    E1 --> E2 --> E3
    E3 -->|No| E2
    E3 -->|Yes| E4 --> E5
    E5 -->|No| E6 --> E7
    E5 -->|Yes| E1

    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;
    classDef coral fill:#FAECE7,stroke:#993C1D,color:#712B13;

    class E1,E6 coral
    class E2,E3,E5 amber
    class E4 blue
    class E7 teal
```

Owned by **Automation Engine + Execution Engine** (retry/fallback policy), not by individual agents.

### Path E — Scheduled / background work

```mermaid
flowchart TD
    F1[APScheduler]
    F2[Follow-up due check<br/>FollowUpState]
    F3{Due?}
    F4[AE → EE send<br/>followup.sent]
    F5[Sleep]
    F6[Midnight · Market intel<br/>rollups · forecasts]

    F1 --> F2 --> F3
    F3 -->|Yes| F4
    F3 -->|No| F5
    F1 -.->|cron| F6

    classDef gray fill:#F1EFE8,stroke:#5F5E5A,color:#2C2C2A;
    classDef blue fill:#E6F1FB,stroke:#185FA5,color:#0C447C;
    classDef teal fill:#E1F5EE,stroke:#0F6E56,color:#085041;
    classDef amber fill:#FAEEDA,stroke:#854F0B,color:#633806;

    class F1,F5,F6 gray
    class F2 blue
    class F3 amber
    class F4 teal
```

---

## 8. Automation Engine vs Execution Engine

| | Automation Engine (brain of actions) | Execution Engine (muscle) |
|---|---|---|
| Input | Action request from agent/workflow | Concrete executor call plan |
| Does | Validate, choose LangGraph / n8n / linear template, HITL, retry policy | Call Twilio, HubSpot, Calendar, email, ads APIs |
| Output | Plan + pause/resume | `{status: success\|error, …}` + trigger result event |
| Must not | Embed vendor SDK details in agents | Contain LLM business reasoning |

```mermaid
flowchart LR
    AR[Action request] --> AE[Automation Engine]
    AE -->|approved plan| EE[Execution Engine]
    EE --> X1[WhatsAppExecutor]
    EE --> X2[CRMExecutor]
    EE --> X3[CalendarExecutor]
    EE --> X4[NotificationExecutor]
    X1 & X2 & X3 & X4 --> EV[Result event → Bus]
```

---

## 9. CEO Orchestrator (Layer 1)

| Concern | Behavior |
|---|---|
| Agent registry | Name, subscriptions, health, placeholder vs active |
| Routing | `event_type` + tenant policy → agent/workflow handler |
| Task queue | Serialize/prioritize work per tenant/entity where needed |
| Agent memory hooks | Attach decision/action memory ids to tasks |
| Health | Heartbeat / last error / circuit for bad agents |
| Communication bus | Agents do not call each other directly; they publish events; CEO routes |

MVP CEO may be a **thin policy router** with full registry/queue/health. LLM-based multi-step planning can deepen later without changing event contracts.

---

## 10. Security & monitoring (platform)

| Area | Requirement |
|---|---|
| Tenant isolation | All queries and events carry `tenant_id` / `client_id` |
| RBAC + API keys | Existing gateway patterns extended to new routes |
| Audit | Action + decision memory; approval outcomes |
| Encryption | Secrets via env/AWS secrets; no secrets in events logs |
| Monitoring | Structured logs, request tracing, latency metrics, health endpoints, DLQ recovery |
| Failure recovery | Path D + replay |

---

## 11. Frontend consumers (contracts only)

Mayank owns UI. Backend owns:

| FE surface | Backend contract |
|---|---|
| Executive Dashboard | SSE KPI/alert pulses + REST analytics |
| AI Timeline | Event stream (`whatsapp.*`, `lead.*`, approvals, follow-ups) |
| Digital Twin | Graph snapshot + live events |
| Knowledge Graph viz | Graph query APIs |
| Sales Copilot | Lead context + NBA + timeline |
| Executive AI Chat | CEO / orchestrated agent channel (SSE or chat API) |

**Early delivery (expansion Phase 1b):** SSE + REST envelopes ship with **stable shapes** as soon as Redis Streams bus is up. Dummy/stub producers (`source: "stub"`) are allowed so frontend can replace mocks immediately; real producers fill the same contracts in later phases. No architecture redesign required in this doc.

---

## 12. Technology map

| Concern | Choice |
|---|---|
| API | FastAPI |
| OLTP | Postgres |
| Vectors / RAG | FAISS + embeddings (existing `rag.py`) |
| Graph | Neo4j |
| Event Bus | **Redis Streams from Day 1** (existing Redis; consumer groups for CEO/handlers; n8n can subscribe) |
| Workflow AI state | LangGraph |
| Integration workflows | n8n |
| Cron | APScheduler |
| Channels | Twilio WhatsApp, HubSpot CRM, Meta/Google (as integrated) |
| LLM | Existing Gemini client (`llm_client`) |
| Observability | Logging + Prometheus metrics (extend) |

---

## Appendix — Historical ASCII Path A–E

Preserved as the refined narrative source that Mermaid paths above formalize. Prefer Mermaid sections for new work.

```text
PATH A — New lead, straightforward qualification (Happy Path)
WhatsApp → API Gateway → whatsapp.received → CEO → WhatsApp AI
  → Context (Postgres, FAISS, Memory, Neo4j)
  → Qualify? NO → clarify via AE→EE; YES → action request
  → AE → EE → lead.qualified → async Neo4j + Memory + SSE
  → CRM automation → Predictive score → Sales NBA
  → requires_approval? YES → Path C; NO → schedule visit → whatsapp.sent

PATH B — Multi-turn: each message re-enters Path A with memory.

PATH C — HITL: AE pause → manager approve/reject → resume/reject → result event.

PATH D — Fail → retry → fallback → DLQ → dlq_replay.

PATH E — APScheduler follow-ups + midnight intel/rollups.
```
