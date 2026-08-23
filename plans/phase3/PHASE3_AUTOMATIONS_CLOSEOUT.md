# Phase 3 Automations Closeout Plan

**Branch:** `phase3_automations` (off `phase3_expansion`)  
**Deadline:** 31 July 2026  
**Status:** Plan locked 2026-07-23 · **BA-1…BA-7 implemented 2026-07-23** (branch `phase3_automations`)  
**Owners:** Aritro (backend bus/hooks) · Maitri (n8n UI workflows + external connectors)  
**Mandate:** Production readiness · **no unapproved features** · HubSpot Python portal stays **skipped**

| This doc owns | Does not own |
|---|---|
| Remaining **automation** work after G3 (events, Calendar, n8n contracts) | PR/merge process into `main` |
| Exact event names, payloads, file touch-list, lane split | New product features outside Phase 3.0 / Waves A–D scope |
| Gap analysis vs third-party audit | FE MockSSE polish (Mayank — `docs/FRONTEND_BACKLOG.md`) |

**Canonical sources (do not override without updating these first):**

| Concern | Source of truth |
|---------|-----------------|
| Event names | `plans/phase3/IREIOS_3.0_Architecture_Diagrams.md` §4 |
| Runtime spine | `Event → CEO → Agent → AE → EE → Event` |
| n8n boundary | `docs/N8N_INTEGRATION.md` |
| Program order | `plans/phase3/UNIFIED_EXECUTION_ORDER.md` |
| Shipped state | `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` (post-G3 audit) |

---

## 0. Executive decision (audit vs codebase)

A third-party audit proposed new event types (`human.requested`, `lead.escalated`, `session.completed`) and greenfield calendar REST stubs. **Cross-check against the live tree rejects name invention and stub-only calendar APIs.**

| Audit proposal | Verdict | Why |
|----------------|---------|-----|
| Emit `human.requested` | **Reject as new type** | Not in catalog. Handoff already closes session + `trigger_hot_lead_notification` (`agent.py` ~846–882). Publish **canonical `lead.hot`** with `payload.trigger=human_handoff`. |
| Emit `lead.escalated` on prob≥82 | **Reject as new type** | Catalog + SalesAgent already use **`lead.hot`**. Score path today only calls notification service — **does not publish bus** (critical gap). Fix = publish `lead.hot`. |
| Emit `session.completed` + chat transcript | **Reject new type** | No catalog entry. Use **`lead.qualified`** / **`conversation.updated`** + optional `chat_context` field. Session close is already `session.status="closed"` on handoff. |
| Always-true `GET /calendar/availability` | **Reject as prod-ready** | Lies to n8n. Real booking is **`CalendarExecutor`** (`schedule_visit` → Google or stub) — already live when `GOOGLE_CALENDAR_*` set. |
| `POST /calendar/confirm` only updates `visit_date` | **Reject as sole path** | Bypasses AE→EE. Confirm must go **`ae_submit(schedule_visit)`** (or EE dispatch) so `site_visit.scheduled` + DLQ stay consistent. |
| n8n owns Google Calendar OAuth create | **Optional later** | SA path shipped (A.0.2 green). n8n may **fan-out** (pretty invite email / Slack) on `site_visit.scheduled`, not replace EE create for July 31. |
| Migrate follow-up / escalation crons to n8n | **Hard no** | `docs/N8N_INTEGRATION.md` — n8n is side-plane only. |
| HubSpot in Python CRMExecutor | **Stay skipped** | Mandate + A.0.1 `[-]`. External CRM upsert = **n8n** on `lead.qualified` if needed. |
| Enrich payloads + harden bus emits | **Accept** | Required for Maitri. |
| Live n8n workflows (Slack, HITL email, marketing CSV, DLQ) | **Accept (Maitri)** | Code path shipped; UI incomplete. |

**Rule:** Prefer **canonical event names + richer `payload`**. Do not fork the catalog for n8n convenience. n8n filters on `payload.trigger` / `payload.kind` when one event covers multiple business meanings.

---

## 1. Current state (verified on tree)

### 1.1 Already shipped (do not rebuild)

| Piece | Location | Notes |
|-------|----------|--------|
| Event bus Redis Streams | `app/clients/event_bus_client.py` | Stream `ireios:events`, envelope: `event_id, event_type, tenant_id, entity_id, source, timestamp, correlation_id, payload` |
| Turn emits | `main.py` `_emit_turn_events` ~L91–125 | `whatsapp/chat.received`, `lead.created`, `conversation.updated`, `lead.qualified` — **no `chat_context` today** |
| Lead scoring → `lead.scored` | `app/agents/lead_scoring_handler.py` | Subscribes `conversation.updated` only |
| Sales on `lead.hot` | `app/agents/sales_agent.py` `SALES_BUS_EVENTS` | **Subscribed; production never publishes `lead.hot`** |
| Hot WA notify (direct) | `agent.py` handoff ~L874; prob≥82 ~L1404 | `trigger_hot_lead_notification` — **bus-blind** |
| Calendar create | `app/execution_engine/calendar_executor.py` | Google SA or stub; EE maps `schedule_visit` → `site_visit.scheduled` (`registry.py`) |
| Visit AE template | `app/automation_engine/templates/visit_booking.py` | Optional `template_type=n8n` |
| Hot-lead AE template | `app/automation_engine/templates/hot_lead_notify.py` | Optional n8n workflow id |
| AE n8n dispatch | `app/automation_engine/engine.py` + `n8n_client.py` | Empty env → `n8n_not_configured`; no workflow → `n8n_http_404` |
| HITL | `app/automation_engine/hitl.py` | Publishes `approval.requested` with `approval_id` |
| Approve APIs | `main.py` `/api/v1/approvals` | JWT list / approve / reject |
| Marketing report event | `app/agents/marketing_agent.py` | `marketing.report.generated` |
| Chat summary helper | `app/memory/conversation_memory.py` `summarize_recent` | Ready; not wired into bus base payload |
| n8n Docker | `docker-compose.yml` service `n8n` | UI http://localhost:5678 |
| GCal env | `.env` `GOOGLE_CALENDAR_*` | Audit: live smoke `provider=google_calendar` |

### 1.2 Critical gaps (backend)

| ID | Gap | Impact | Status |
|----|-----|--------|--------|
| **G-HOT** | `lead.hot` never published | Sales bus path + n8n Slack never fire from real traffic | **Closed BA-1** |
| **G-CTX** | No `chat_context` on turn events | n8n CRM/note workflows lack transcript | **Closed BA-2** |
| **G-VISIT-P** | EE success publish uses executor **result only** | thin `site_visit.scheduled` | **Closed BA-3** |
| **G-HITL-URL** | `approval.requested` payload lacks deep links | n8n buttons | **Closed BA-4** |
| **G-N8N-UI** | Webhook workflows not activated | bridge → `n8n_http_404` / no Gmail | **Open — Maitri** |
| **G-N8N-DELIVERY** | Stock n8n cannot read Redis Streams | “Redis primary” was invalid | **Closed** — `n8n_bridge` group `ireios-n8n` |
| **G-MEM** | D.2 memory auto-write still deferred | Optional polish | Deferred |

### 1.3 Explicit non-goals (this branch)

- HubSpot private-app live portal in Python  
- Replacing APScheduler follow-up / 10m–30m escalation / competitor monitor with n8n  
- Dummy calendar “always available” APIs  
- Dual-path delete of root `agent.py` / `crm_sync.py` / `follow_up.py` (still deferred 10.2/10.3)  
- Meta/Google Ads spend APIs  
- Opening/merging PRs (process lives outside this plan)

---

## 2. Lane split (locked)

```text
┌─────────────────────────────────────────────────────────────┐
│  Revenue OS Core (Python) — Aritro                          │
│  • Canonical bus emits + payload shape                      │
│  • CalendarExecutor / AE→EE schedule_visit                  │
│  • Tenant isolation, DLQ, WA 15s path                       │
│  • Optional thin REST only if it wraps EE (not stubs)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ Redis Streams ireios:events
                           │ and/or AE POST /webhook/{id}
┌──────────────────────────▼──────────────────────────────────┐
│  Extension plane (n8n) — Maitri                             │
│  • Slack/Teams, business email HTML, Drive CSV              │
│  • Optional external CRM upsert (HubSpot node)              │
│  • Pretty calendar invite email on site_visit.scheduled     │
│  • HITL manager email/Slack with approve links              │
│  • Does NOT own qualification, follow-up FSM, tenant DB     │
└─────────────────────────────────────────────────────────────┘
```

**Email distinction (keep):**

| Kind | Owner | When |
|------|--------|------|
| Disaster / Twilio crash fallback | Python (`notification_service` / critical paths) | Integration failure |
| Business ops digests, Slack, manager HITL formatting | n8n | `lead.hot`, `approval.requested`, `marketing.report.generated`, etc. |

---

## 3. Canonical event contracts (for Maitri)

All events use the bus envelope from `EventBusClient.build_envelope`.  
`tenant_id` format: `Client_<int>`.

### 3.1 Notification & escalation → use `lead.hot`

**Publish sites (to implement):**

1. **Score / temperature** — after hot threshold (align with existing `prob >= 82` in `agent.py` ~L1404 **and/or** after `lead_scoring_handler` when `lead_temperature == "hot"` / prob ≥ 82). Prefer **one** authoritative publisher to avoid double Slack (see BA-1).  
2. **Human handoff** — inside HUMAN HANDOFF INTERCEPT after commit (`agent.py` ~L871).

**Envelope payload (target shape):**

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
    "intent": "buy",
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

| Field | Notes |
|-------|--------|
| `trigger` | n8n IF node: `human_handoff` vs `hot_threshold` |
| `score` | Mirror of `conversion_probability` for Slack templates |
| `chat_context` | From `conversation_memory.summarize_recent(db, session_id=..., turns=10)` — truncate if >4k chars |

**Catalog rule:** do not invent `human.requested` as a standalone type.  
**PR #10:** code dual-publishes alias `lead.escalated` (same payload). Bridge maps **`lead.hot` only** — never both (double Gmail).

**Idempotency guidance:** Redis key `lead_hot_emitted:{client_id}:{lead_id}:{trigger}` TTL 30m so score path does not spam n8n every turn while still hot.

### 3.2 CRM / transcript → enrich `lead.qualified` (+ `conversation.updated`)

Existing emit in `main.py` `_emit_turn_events` when `_is_lead_qualified(lead)`.

**Add to `base` dict:**

```json
{
  "lead_id": 123,
  "session_id": "1_+919999999999",
  "source": "whatsapp",
  "name": "John Doe",
  "phone": "+919999999999",
  "location": "Baner",
  "budget": "80L",
  "property_type": "2BHK",
  "intent": "buy",
  "lead_temperature": "hot",
  "conversion_probability": 85,
  "budget_alignment_status": "...",
  "chat_context": "User: Hi...\nAgent: ..."
}
```

**n8n CRM workflow** listens to `lead.qualified` (primary) and optionally `lead.assigned`.  
No `session.completed` type.

### 3.3 Calendar → `site_visit.scheduled` (EE-owned)

**Producer today:** EE after successful `CalendarExecutor.execute` → `register_event("schedule_visit", "site_visit.scheduled")`.

**Problem:** `_publish_success` publishes `result` only (`visit_id`, `provider`, …), not lead demographics.

**Target payload (merge action_request.parameters + result):**

```json
{
  "event_type": "site_visit.scheduled",
  "tenant_id": "Client_1",
  "entity_id": "123",
  "source": "execution_engine",
  "payload": {
    "lead_id": 123,
    "visit_id": "google_or_stub_id",
    "visit_date": "2026-08-01T10:00:00+05:30",
    "name": "John Doe",
    "phone": "+919999999999",
    "location": "Baner",
    "provider": "google_calendar | stub",
    "html_link": "https://calendar.google.com/..."
  }
}
```

**n8n:** On `site_visit.scheduled` → optional Gmail/Slack “invite sent” formatting.  
**Python:** Remains system of record for creating the Google event when `GOOGLE_CALENDAR_*` configured.

### 3.4 HITL → `approval.requested` (already published)

Enrich payload in `hitl.py`:

```json
{
  "approval_id": 42,
  "correlation_id": "...",
  "action_type": "send_whatsapp",
  "entity_id": "123",
  "parameters_summary": { },
  "approve_path": "/api/v1/approvals/42/approve",
  "reject_path": "/api/v1/approvals/42/reject",
  "api_base_hint": "https://api.example.com"
}
```

n8n builds absolute URLs from ops-configured public API base + paths. Buttons call existing JWT or document that manager uses dashboard (do not invent new public unauthenticated approve links without auth design).

### 3.5 Marketing → `marketing.report.generated` (shipped)

Unchanged. n8n CSV/Drive on this event (Workflow E).

### 3.6 Alias map (for humans reading old audit text)

| Audit / chat wording | Canonical |
|----------------------|-----------|
| `human.requested` | `lead.hot` + `trigger=human_handoff` |
| `lead.escalated` | `lead.hot` + `trigger=hot_threshold` |
| `session.completed` | `lead.qualified` (+ `chat_context`); handoff also `lead.hot` |
| Calendar availability REST | Optional BA-5 freebusy **or** AI already negotiated `visit_date` → `schedule_visit` |
| Calendar confirm REST | Must wrap AE `schedule_visit`, not raw SQL-only |

---

## 4. Backend execution plan (Aritro) — ordered

Implement on `phase3_automations`. One task at a time; mark done only with tests.

### BA-0 — Freeze contracts (docs only)

- [x] This file + UNIFIED Step 24 + N8N_INTEGRATION payload section  
- [x] Architecture §4.3: `lead.hot` payload may include `trigger`

### BA-1 — Publish `lead.hot` (G-HOT) — **P0** — `[x]` 2026-07-23

**Shipped:**

| Piece | Path |
|-------|------|
| Shared helper | `app/events/lead_hot.py` — `is_hot`, `publish_lead_hot`, Redis debounce TTL 30m |
| Score path | `app/agents/lead_scoring_handler.py` → `trigger=hot_threshold` |
| Handoff path | `agent.py` HUMAN HANDOFF → `trigger=human_handoff` (ORM snapshot for create_task) |
| Rule | `conversion_probability >= 82` **or** `lead_temperature == "hot"` |
| WA notify | Unchanged direct `trigger_hot_lead_notification` (no double WA from bus) |

**Tests:** `tests/test_e18_automations_closeout.py` (is_hot, debounce, scoring publish, handoff source)

### BA-2 — `chat_context` on turn base payload (G-CTX) — **P0** — `[x]` 2026-07-23

**Shipped:** `main.py` `_emit_turn_events(..., db=)` → `conversation_memory.summarize_recent` → `base["chat_context"]` (max 4000). Call sites chat + `process_unified_lead` pass `db`. No `session.completed`.

### BA-3 — Rich `site_visit.scheduled` payload (G-VISIT-P) — **P0** — `[x]` 2026-07-23

**Shipped:** `execution_engine._publish_success` merges `parameters` + `result`; fills `lead_id` from `entity_id` when missing.

### BA-4 — HITL payload deep-link fields (G-HITL-URL) — **P1** — `[x]` 2026-07-23

**Shipped:** `hitl.request_approval` publishes `approve_path`, `reject_path`, `parameters_summary`, optional `api_base_hint`.

### BA-5 — Calendar REST — **P2** — `[x]` 2026-07-23

**Shipped:** `app/api/calendar.py` mounted in `main.py`

| Route | Behavior |
|-------|----------|
| `GET /api/v1/calendar/availability` | API key; Google freebusy or **labeled** `provider=stub` heuristic slots |
| `POST /api/v1/calendar/confirm` | Tenant lead update + **`ae_submit(build_visit_action)`** |

### BA-6 — n8n primary ingest mode — **P2** — `[x]` 2026-07-23 · **revised 2026-07-28**

**Original (invalid for stock n8n):** “Redis Streams primary” — n8n has no Streams trigger.

**Revised (locked):** **Python `N8NBridge`** joins separate consumer group `ireios-n8n`, filters allowlisted `event_type`, POSTs full envelope to n8n webhooks. AE `template_type=n8n` = fallback only. Do **not** dual-fanout bridge + AE for the same alert (double Gmail). See `docs/N8N_INTEGRATION.md`, `app/automation_engine/n8n_bridge.py`, `plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md`.

### BA-7 — Validation gate — **P0** — `[x]` 2026-07-23

```text
pytest tests/ → 352 passed, 4 skipped
gate_isolation_test.py → PASS
gate_dlq_drill.py + dlq_replay.py → 1/1 recovered
```

### BA-8 — Docs flip after code — `[x]` 2026-07-23

---

## 5. n8n workflows (Maitri) — detailed

**Prereq:** `docker compose up -d n8n` · owner account · `N8N_BASE_URL` / `N8N_API_KEY` match Header Auth.

**Ingest options (document both; pick one per workflow):**

1. **Redis Streams** trigger on `ireios:events` (filter `event_type`) — preferred for bus-native events.  
2. **Webhook** `POST /webhook/<path>` + Header Auth — preferred when AE `template_type=n8n`.

### WF-1 — `ireios_hot_lead_alert` (P0) — Gmail-first

| | |
|--|--|
| **Trigger** | Bridge POST on `lead.hot` → path `ireios_hot_lead_alert` |
| **Filter** | All hot; optional branch on `payload.trigger` |
| **Actions** | **Gmail** to admin: name, score, location, assigned_agent, reason, chat_context |
| **Backend dependency** | BA-1 + BA-2 + n8n_bridge |
| **Status today** | Bridge shipped; workflow UI **not** activated → 404 until Maitri |

### WF-2 — Site visit fan-out (P1)

| | |
|--|--|
| **Trigger** | `site_visit.scheduled` |
| **Actions** | Slack “visit booked”; optional Gmail to lead with `html_link` / time |
| **Do not** | Create a second Google event if Python SA already created one (`provider=google_calendar`) — invite email only |
| **Backend dependency** | BA-3 |

### WF-3 — HITL manager notify (P1)

| | |
|--|--|
| **Trigger** | `approval.requested` |
| **Actions** | Email/Slack with approve/reject links (dashboard or API base + paths from BA-4) |
| **Backend dependency** | BA-4; APIs already exist |

### WF-4 — External CRM note (P2, replaces “session.completed CRM”)

| | |
|--|--|
| **Trigger** | `lead.qualified` (and/or `lead.assigned`) |
| **Actions** | HubSpot/Salesforce **n8n nodes** upsert contact + note from `chat_context` |
| **Backend dependency** | BA-2; Python HubSpot stays skipped |

### WF-5 — Weekly marketing CSV (P2)

| | |
|--|--|
| **Trigger** | `marketing.report.generated` |
| **Actions** | JSON → CSV → Google Drive + email link |
| **Backend dependency** | None (event shipped) |

### WF-6 — DLQ depth alert (P2)

| | |
|--|--|
| **Trigger** | n8n cron every 15m |
| **Actions** | HTTP GET admin metrics or DB check; Slack if pending DLQ > N |
| **Backend dependency** | Existing DLQ tables / metrics — no new event required |

### WF — Must NOT implement in n8n

- Day0→7 follow-up FSM  
- 10m/30m escalation cron  
- Competitor monitor core  
- WhatsApp TwiML reply / 6-field gate  
- Tenant JWT issuance  

---

## 6. Google Calendar — ownership (final)

```text
AI negotiates visit_date on Lead
        │
        ▼
AE action_type=schedule_visit  (visit_booking template or Sales NBA)
        │
        ▼
CalendarExecutor
  ├─ GOOGLE_CALENDAR_* set → Google Calendar API insert → visit_id, html_link
  └─ else → stub visit_*
        │
        ▼
EE publishes site_visit.scheduled (rich payload after BA-3)
        │
        ├─► KG writer, Memory, SSE dashboard
        └─► n8n WF-2 (email/Slack fan-out only)
```

| Item | Decision |
|------|----------|
| Service account create | **Keep** (shipped, live smoke done) |
| n8n OAuth multi-tenant calendar create | **Post–July 31** unless SA blocked |
| Availability API | Optional BA-5; not blocking if AI already collects concrete slot |
| Dummy `available: true` only | **Forbidden** without `provider: stub` label |

---

## 7. Suggested implementation order (calendar week)

| Day | Owner | Work |
|-----|-------|------|
| D0 | Both | Read this plan; agree Redis vs AE for WF-1 |
| D1 | Aritro | BA-1 + BA-2 + tests |
| D1–D2 | Maitri | Activate WF-1 against stub `lead.hot` |
| D2 | Aritro | BA-3 + BA-4 |
| D2–D3 | Maitri | WF-2, WF-3 |
| D3 | Aritro | BA-7 full gate; optional BA-5/6 only if blocked |
| D4 | Maitri | WF-5, WF-6; evidence screenshots |
| D5 | Both | Joint smoke: WA/chat → bus → n8n Slack; visit → calendar + Slack |

---

## 8. Exit criteria (Step 24 / automations closeout)

- [x] Backend publishes **`lead.hot`** with `trigger` ∈ {`hot_threshold`,`human_handoff`} (unit + source proofs)  
- [x] `lead.qualified` / `conversation.updated` include **`chat_context`** when history exists  
- [x] `site_visit.scheduled` merge includes lead identity + visit_date (+ html_link when Google)  
- [x] Bus→n8n **bridge** (`ireios-n8n`) ships and is documented (2026-07-28)  
- [ ] n8n WF-1 **Active** and receives at least one real or stub hot event via Gmail (screenshot) — **Maitri ops**  
- [x] Full `pytest` green + isolation + DLQ (2026-07-23)  
- [x] No new non-catalog event types in code  
- [x] HubSpot Python still skipped; no cron migration to n8n  
- [x] Docs in §BA-8 updated  

**Backend Step 24 code:** **done**. Gate G4 fully green only after Maitri WF-1 smoke.

---

## 9. Code reference index (quick)

| Concern | Path |
|---------|------|
| Turn events | `main.py` `_emit_turn_events`, `_publish_bus_event` |
| Handoff | `agent.py` ~L846–882 |
| Hot score notify | `agent.py` ~L1404–1414 |
| Scoring bus | `app/agents/lead_scoring_handler.py` |
| Sales `lead.hot` | `app/agents/sales_agent.py` |
| Calendar EE | `app/execution_engine/calendar_executor.py` |
| EE event map | `app/execution_engine/registry.py`, `execution_engine.py` `_publish_success` |
| n8n client | `app/automation_engine/n8n_client.py` |
| n8n bridge | `app/automation_engine/n8n_bridge.py` (group `ireios-n8n`) |
| n8n WF recipes | `plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md` |
| Hot template | `app/automation_engine/templates/hot_lead_notify.py` |
| Visit template | `app/automation_engine/templates/visit_booking.py` |
| HITL | `app/automation_engine/hitl.py` |
| Summarize | `app/memory/conversation_memory.py` `summarize_recent` |
| Envelope | `app/clients/event_bus_client.py` `build_envelope` |
| SSE | `app/api/events.py` |
| n8n ops | `docs/N8N_INTEGRATION.md` |

---

## 10. Changelog of plan decisions

| Date | Decision |
|------|----------|
| 2026-07-23 | Locked closeout plan from Mayank mandate + third-party audit **reconciled** to catalog and tree. Rejected invented events and stub calendar-only APIs. Elevated `lead.hot` publish gap to P0. |
| 2026-07-23 | Implemented BA-1…BA-7: `app/events/lead_hot.py`, scoring+handoff publish, chat_context, EE merge, HITL paths, calendar REST, Redis-primary n8n. Tests e18 (14). pytest 352 pass. |
| 2026-07-28 | **BA-6 revised:** stock n8n cannot XREADGROUP. Shipped `n8n_bridge` (group `ireios-n8n`) + Gmail-first recipes `plans/phase3/N8N_LIVE_WORKFLOWS_PLAN.md`. Path rename `ireios_hot_lead_alert`. |
