# IREIOS 3.0 — Evidence Pack (Gate G2 + BD closeout + G3 Waves A–D)

## Architecture & cutover
- [x] Event Bus = Redis Streams; inbound chat/WA publishes lifecycle events (`main._emit_turn_events`)
- [x] CEO agents on real traffic: followup_arm, lead_scoring, crm_automation, kg_event_writer, …
- [x] **BD-1** CRM create path = bus only (`crm_automation` → AE→EE); no dual `sync_lead_to_crm` on chat
- [x] **BD-2** Follow-up default `FOLLOWUP_ENGINE=v3` (AE→EE); legacy flag rollback only
- [x] **BD-3** Qualification entry = `app.agents.qualification`; WhatsAppAgent is default orchestrator
- [x] **BD-4** Outbound purity: escalation + hot alerts + background via `outbound` / `WhatsAppExecutor` (not ad-hoc Twilio Client in those paths). `dlq_replay` / legacy `follow_up` retain direct Twilio for rollback/recovery tools.
- [x] **BD-5** Neo4j used on WhatsApp reply path (`extra_context` → LLM summary)
- [x] Brochure tools: Approach B — HTTPS `resolve_tool_media_url` + staged `take_outbound_media_url` → TwiML `<Media>` (no reply-text scrape); Sales NBA attaches media; empty env text fallback; no AE double-send on default path
- [~] Full deletion of root `agent.py` / `follow_up.py` / `crm_sync.py` modules — not required; they are libraries for EE/v3. Dead *call paths* removed.
- [ ] FE MockSSE cutover — see `docs/FRONTEND_BACKLOG.md` (Mayank)

## Gate G3 — Waves A–D depth fill (2026-07-21)

Detail: `plans/phase3/IREIOS_3.0_WAVE_A_D_CHANGELOG.md` · plan: `plans/phase3/IREIOS_3.0_WAVE_A_D_EXPANSION.md` · UNIFIED Steps 20–23 + G3.

- [x] **Wave A:** weekly marketing cron, lifecycle inject API, AE n8n/langgraph branch, expire_approvals job, NotificationExecutor real notify paths
- [x] **Wave B:** Sales bus + objections, CS WhatsApp, marketing market.alert, AE templates, competitor → NotificationLog; **B.7 create_task** (`agent_tasks` + EE)
- [x] **Wave C:** inventory/pricing models + seed; 6 agents active; placeholders empty
- [x] **Wave D:** prediction routes; brochure Approach B; **D.2 memory auto-write**; n8n workflows still ops
- [x] **pytest** full suite green after P0 stabilize (`ensure_test_client`, seed ASCII, e1b OpenAPI route check)
- [x] **gate_isolation_test.py** PASS
- [x] **gate_dlq_drill.py** + **dlq_replay.py** 1/1 recovered
### A.0 integrations (ops) — audit 2026-07-22
- [x] HubSpot — **skipped**; demo stub OK
- [x] Google Calendar — live smoke `provider=google_calendar` (fix SA JSON path with `/` on Windows)
- [x] n8n — Docker `n8n-local` **up** + `N8N_*` set; **6/6 workflows active** (webhook-verified: WF-1–WF-6)
- [x] Brochure HTTPS media — jsDelivr `docs/demo/*.pdf` GET 200 `application/pdf`; resolve_tool_media_url OK (2026-07-23)
- [x] Neo4j — `/api/v1/graph/health` available + schema v1
- [x] D.2 memory auto-write + B.7 create_task (2026-07-23)
- [ ] `task3_runner.py` live stress when Gemini quota allows
- [ ] Dual-path module delete 10.2/10.3 — **deferred**
- [x] n8n workflow automations (WF-1–WF-6 shipped + active)

## Data, graph, memory
- [x] Neo4j schema v1; `/api/v1/graph/health` available when configured
- [x] Graph writers + reply-path read
- [x] ConversationMemory APIs

## Integrations
- [x] n8n client + AE dispatch + purpose doc: `docs/N8N_INTEGRATION.md` (instance optional)
- [x] Google Calendar executor: real when env set; synthetic `visit_id` stub when empty
- [x] Twilio via WhatsAppExecutor for production send paths listed above
- [x] Brochure Approach B media path (HTTPS env optional)

## Quality gates
- [x] `tests/test_e12_bus_wiring.py`, `tests/test_e13_bd_closeout.py`
- [x] Expansion + bug unit suites (run before release)
- [ ] `python task3_runner.py` when Gemini quota allows (live server)
- [x] `gate_isolation_test.py` / `gate_dlq_drill.py` (run before deploy)

## Manual smoke
1. `docker compose up -d` + uvicorn
2. `/health` + `/api/v1/graph/health` (available=true with local Neo4j)
3. Chat or Twilio sandbox message
4. SSE stream shows `conversation.updated` / `lead.created` / `lead.scored`
5. Neo4j Browser optional: `MATCH (l:Lead) RETURN l LIMIT 25`
6. Optional: brochure PDF URLs + Calendar visit + n8n webhook

## Go-live flags
```env
IS_PRODUCTION=true
TEST_MODE=false
FOLLOW_UP_TEST_MODE=false
FOLLOW_UP_DLQ_TEST=false
FEATURE_WHATSAPP_V3=true
FOLLOWUP_ENGINE=v3
NEO4J_URI=bolt://...   # optional but recommended
# optional:
# GOOGLE_CALENDAR_*, N8N_*, BROCHURE_MEDIA_URL, FLOORPLAN_MEDIA_URL, CRM_API_*
```
