# IREIOS 3.0 — AI Automation Workflows

Per-agent and per-workflow **behavior** only.

| This doc owns | Does not own |
|---|---|
| Intents, context, decisions, action types, published events per workflow | System layers / Path A–E topology → `IREIOS_3.0_Architecture_Diagrams.md` |
| | File trees, phases, migration → `IREIOS_3.0_IMPLEMENTATION_PLAN.md` |

**Universal pattern (all workflows):**

```text
Trigger event → CEO routes → Agent/Workflow
  → fetch_context → analyze → decide (action_request)
  → Automation Engine (validate · template · HITL if needed)
  → Execution Engine (executor)
  → result event → Event Bus → Memory · KG · Dashboard · next agents
```

Event names must match the **Architecture Diagrams event catalog**.

---

## 1. WhatsApp AI Workflow

**Role:** Inbound WhatsApp (and website chat via same agent path): qualification, FAQ, brochure, floor plan, site visit, reminders handoff, escalation.

| | |
|---|---|
| **Inputs** | `whatsapp.received`, `chat.received` |
| **Context** | Lead, session messages, FollowUpState, FAISS RAG, Memory, Neo4j lead/project links |
| **Outputs (actions)** | `send_whatsapp`, `send_whatsapp`+media, `update_crm` / lead fields, `schedule_visit`, `escalate_to_human` |
| **Publishes** | Via EE: `whatsapp.sent`, `brochure.sent`, `floorplan.sent`, `site_visit.scheduled`; agent side: `whatsapp.response.generated`, `lead.qualified` when criteria met |

### Flow

```mermaid
flowchart TD
  W1[whatsapp.received / chat.received] --> W2[CEO → WhatsApp AI]
  W2 --> W3[fetch_context]
  W3 --> W4[Pre-checks: opt-out · guardrail · human handoff]
  W4 --> W5{Intent}
  W5 -->|FAQ| RAG[RAG / property context]
  W5 -->|Brochure| BRO[share_brochure tool]
  W5 -->|Floor plan| FP[share_floor_plan tool]
  W5 -->|Qualification| Q[Extract budget · location · BHK · intent]
  W5 -->|Site visit| SV[Visit requirements]
  W5 -->|Other| GEN[General reply]
  RAG & BRO & FP & Q & SV & GEN --> LLM[LLM + tools]
  LLM --> DEC[decide action_request]
  DEC --> AE[Automation Engine]
  AE --> EE[Execution Engine]
  EE --> RES[Result events → Bus]
  RES --> FAN[Memory · KG · Scoring · Follow-up · SSE]
```

### Intent rules (summary)

| Intent | Behavior |
|---|---|
| FAQ | Answer from RAG / property context; no document tool |
| Brochure | Explicit brochure/catalog/PDF ask → `share_brochure` → media send |
| Floor plan | Layout/map/dimensions ask → `share_floor_plan` → media send |
| Qualification | Extract fields; if incomplete, one clarifying question; if complete → qualify path |
| Site visit | Collect requirements → `schedule_visit` (HITL if policy requires) |
| Escalation | Opt-out / human request / guardrail → `escalate_to_human` |

### Multi-turn (Path B)

Same workflow; memory skips known fields until qualification complete.

---

## 2. Marketing AI Workflow

**Role:** Campaign performance, audience/budget suggestions, reports.

| | |
|---|---|
| **Inputs** | `campaign.completed`, `cron.weekly_report`, `market.alert.generated` (optional) |
| **Context** | Meta/Google metrics, CRM lead quality, conversions, KG |
| **Outputs** | `notify_admin`, ads API actions (when integrated), report publish |
| **Publishes** | `marketing.report.generated`, `campaign.updated` |
| **HITL** | Budget/campaign changes that spend money → `requires_approval` |

```mermaid
flowchart TD
  M1[Campaign / weekly trigger] --> M2[CEO → Marketing AI]
  M2 --> M3[Fetch Meta · Google · CRM · conversions · KG]
  M3 --> M4[CTR · CPL · quality · conversion analysis]
  M4 --> M5[Audience + budget + campaign recommendations]
  M5 --> M6{requires_approval?}
  M6 -->|Yes| HITL[HITL]
  M6 -->|No| AE[Automation Engine]
  HITL --> AE --> EE[Execution Engine]
  EE --> EVT[campaign.updated / marketing.report.generated]
  EVT --> FAN[Memory · Dashboard · KG]
```

---

## 3. Sales AI Workflow

**Role:** Objections, priority, next-best-action, hot-lead awareness.

| | |
|---|---|
| **Inputs** | `lead.scored`, `conversation.updated`, `lead.hot` |
| **Context** | Lead profile, history, prior objections, score, site visits |
| **Outputs** | `create_task`, `schedule_visit`, `send_whatsapp` (docs), `notify_agent` |
| **Publishes** | Sales action result events; may set `requires_approval` (e.g. discount) |
| **HITL** | High-risk commercial actions |

```mermaid
flowchart TD
  S1[lead.scored / conversation.updated] --> S2[CEO → Sales AI]
  S2 --> S3[Fetch sales context]
  S3 --> S4[Objection detection]
  S4 --> S5[Priority: hot / warm / cold]
  S5 --> S6[Next best action]
  S6 --> S7{requires_approval?}
  S7 -->|Yes| HITL[HITL]
  S7 -->|No| AE[Automation Engine]
  HITL --> AE --> EE[Task · Calendar · WhatsApp · Notify]
  EE --> FAN[CRM · Memory · Dashboard]
```

### Next-best-action examples

| Priority / signal | Action |
|---|---|
| Hot + engaged | Call task / site visit |
| Price objection | Negotiation path or human task (HITL if discount) |
| Warm | Brochure/floor plan or timed follow-up |
| Cold | Low-touch follow-up later |

---

## 4. Customer Success AI Workflow

**Role:** Lifecycle messaging after booking/payment.

| | |
|---|---|
| **Inputs** | `payment.due`, `payment.received`, `document.pending`, `booking.confirmed`, `customer.onboarded`, `renewal.due` |
| **Context** | Customer profile, payment/document status, booking history |
| **Outputs** | `send_whatsapp`, `update_crm` |
| **Publishes** | CS result events (e.g. reminder sent) |

```mermaid
flowchart TD
  T[Lifecycle event] --> CS[CEO → Customer Success AI]
  CS --> FC[Fetch customer context]
  FC --> LA{Action type}
  LA -->|Payment| PR[Payment reminder]
  LA -->|Document| DR[Document reminder]
  LA -->|Success| RR[Referral request]
  LA -->|Journey done| RC[Review collection]
  LA -->|Renewal| REN[Renewal reminder]
  PR & DR & RR & RC & REN --> MSG[Personalized message]
  MSG --> AE[Automation Engine] --> EE[WhatsApp · CRM]
  EE --> FAN[Memory · CRM · Dashboard]
```

---

## 5. CRM Automation Workflow

**Role:** Deterministic classification, tags, agent match, routing, CRM sync (not LLM-first).

| | |
|---|---|
| **Inputs** | `lead.created`, `lead.qualified`, `lead.scored` |
| **Context** | Lead fields, score, budget alignment, location, agent availability |
| **Outputs** | `update_crm`, `create_task`, assignment fields |
| **Publishes** | `lead.crm_synced`, `lead.assigned` |
| **Failure** | EE retry → DLQ (Path D) |

```mermaid
flowchart TD
  R1[lead.created / qualified / scored] --> R2[CRM Automation]
  R2 --> R3[Classify hot / warm / cold]
  R3 --> R4[Auto tags]
  R4 --> R5[match_best_agent · route]
  R5 --> R6[Build CRM / task actions]
  R6 --> AE[Automation Engine] --> EE[CRM Executor]
  EE -->|ok| EVT[lead.crm_synced · lead.assigned]
  EE -->|fail| DLQ[Retry · DLQ]
  EVT --> FAN[Sales · KG · Dashboard]
```

---

## 6. Competitor Monitoring Workflow

**Role:** Scheduled market intelligence (Layer 10).

| | |
|---|---|
| **Inputs** | APScheduler / cron (not bus-first) |
| **Context** | Pricing, projects, offers, inventory, news, infrastructure snapshots |
| **Outputs** | `notify_admin`, dashboard alert actions |
| **Publishes** | `market.alert.generated` |

```mermaid
flowchart TD
  P1[Cron] --> P2[Competitor Monitor]
  P2 --> P3[Fetch + normalize market data]
  P3 --> P4{Significant change?}
  P4 -->|No| STORE[Store snapshot]
  P4 -->|Yes| MI[Market intelligence + priority]
  MI --> AE[Automation Engine] --> EE[Notify · Dashboard]
  EE --> EVT[market.alert.generated]
  EVT --> FAN[Marketing · Sales · KG · Memory · Dashboard]
```

---

## 7. Follow-Up Scheduler Workflow

**Role:** Time-based Day 0→1→3→7 style follow-ups (Path E). Polling is intentional.

| | |
|---|---|
| **Inputs** | APScheduler every ~60s; also `lead.created` / activity to arm state |
| **Context** | `FollowUpState`, lead, quiet hours, intelligence payload builders |
| **Outputs** | `send_whatsapp` via AE→EE (never direct Twilio) |
| **Publishes** | `followup.sent` |

```mermaid
flowchart TD
  F1[APScheduler 60s] --> F2[Due FollowUpState?]
  F2 -->|No| SLEEP[Sleep]
  F2 -->|Yes| PAY[Build payload · quiet hours]
  PAY --> AE[Automation Engine] --> EE[WhatsApp Executor]
  EE --> EVT[followup.sent]
  EVT --> FAN[Memory · Timeline]
```

---

## 8. Automation Engine Workflow (shared)

**Role:** Layer 6 control plane for every action_request.

| | |
|---|---|
| **Inputs** | Action requests from any agent/workflow |
| **Does** | Validate → load template → LangGraph \| n8n \| linear → HITL gate → call EE → retry/fallback/DLQ |
| **Publishes** | Success/failure/approval events; never skips EE for external I/O |

```mermaid
flowchart TD
  A1[action_request] --> A2[Validate]
  A2 --> A3{Template type}
  A3 -->|Stateful AI| LG[LangGraph]
  A3 -->|Integration| N8N[n8n]
  A3 -->|Deterministic| LIN[Linear]
  LG & N8N & LIN --> A4{requires_approval?}
  A4 -->|Yes| PAUSE[Pause · notify manager]
  PAUSE --> MD{Approve?}
  MD -->|Reject| REJ[Memory + approval.resolved]
  MD -->|Approve| EE[Execution Engine]
  A4 -->|No| EE
  EE --> OK{Success?}
  OK -->|Yes| OKS[Success event]
  OK -->|No| RETRY[Backoff retry]
  RETRY --> LIM{Limit?}
  LIM -->|No| EE
  LIM -->|Yes| FB[Fallback]
  FB --> FOK{Ok?}
  FOK -->|Yes| OKS
  FOK -->|No| DLQ[DLQ · replay later]
  OKS & REJ --> BUS[Event Bus fan-out]
```

---

## 9. Lead Scoring Handler (async)

**Role:** Non-blocking ML after chat (keeps WA latency low).

| | |
|---|---|
| **Inputs** | `whatsapp.response.generated` (and optionally `lead.qualified`) |
| **Does** | `calculate_lead_score`, budget alignment, related intelligence |
| **Publishes** | `lead.scored`; if threshold → `lead.hot` |

Not a conversational agent; registered handler under CEO/bus.

---

## 10. Former placeholders → active agents (Wave C)

`PLACEHOLDER_AGENTS` is **empty**. The six Layer-2 names are **active** bus agents (see `AGENTS.md`):

| Agent | Typical inputs | Notes |
|-------|----------------|--------|
| `negotiation_agent` | `lead.negotiation.*` | HITL when budget misaligned |
| `pricing_agent` | `pricing.query`, `lead.scored` | `PricingRule` lookup |
| `inventory_agent` | `inventory.query` / hold | `InventoryUnit` available |
| `onboarding_agent` | `booking.confirmed`, `customer.onboarded` | Welcome WA checklist |
| `finance_agent` | `payment.query`, `finance.schedule` | Payment info via AE |
| `legal_agent` | `document.required`, `legal.review` | Doc needs → notify |

Former `retention_agent` duties are covered by `customer_success_agent`.

---

## 11. Workflow ↔ event index

| Workflow | Primary inputs | Primary outputs / events |
|---|---|---|
| WhatsApp AI | `whatsapp.received`, `chat.received` | `whatsapp.sent`, `brochure.sent`, `floorplan.sent`, `lead.qualified`, `whatsapp.response.generated` |
| Marketing AI | `campaign.completed`, cron | `marketing.report.generated`, `campaign.updated` |
| Sales AI | `lead.scored`, `conversation.updated`, `lead.hot` | tasks, visits, notifications (+ HITL) |
| Customer Success | payment/booking/lifecycle events | reminders, CRM updates |
| CRM Automation | `lead.created`, `lead.qualified`, `lead.scored` | `lead.assigned`, `lead.crm_synced` |
| Competitor Monitor | cron | `market.alert.generated` |
| Follow-Up Scheduler | cron + lead activity | `followup.sent` |
| Automation Engine | action_request | success/fail/approval events |
| Lead Scoring | `whatsapp.response.generated` / `conversation.updated` | `lead.scored`, `lead.hot` (closeout: ensure `lead.hot` actually published) |

---

## 12. n8n side-plane (not CEO agents)

n8n is **outside** the in-process CEO table. Delivery = **`n8n_bridge`** (group `ireios-n8n` → webhooks) or AE `template_type=n8n` fallback — not stock Redis Streams.

| n8n workflow | Bus / trigger | Notes |
|--------------|---------------|-------|
| Hot lead **Gmail** | `lead.hot` via **bridge** → `ireios_hot_lead_alert` | `payload.trigger` = threshold \| handoff |
| Visit fan-out Gmail | `site_visit.scheduled` → `ireios_visit_fanout` | No 2nd Google create if `provider=google_calendar` |
| HITL notify Gmail | `approval.requested` → `ireios_hitl_notify` | Dashboard deep links |
| External CRM | `lead.qualified` → `ireios_crm_note` | `chat_context` (BA-2) |
| DLQ alert | n8n cron | Not a bus event |

**Delivery:** `n8n_bridge` (group `ireios-n8n`), not stock Redis Streams.  
**Do not** move follow-up FSM, escalation cron, or WA TwiML into n8n.  
Contracts: `docs/N8N_INTEGRATION.md`, `plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md`, `plans/phase3/PHASE3_AUTOMATIONS_CLOSEOUT.md`.
