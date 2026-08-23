# IREIOS 4.0 — Engineering freeze handoff (Mayank + Piyush)

**Date:** 2026-08-14  
**Branch / HEAD:** `post_automation_fixes` @ `127920e` (FE quality `4494307`, CC UX batch `127920e`)  
**Program status:** P4-0…P4-9 + **G5 green** · CC UX polish shipped · **no blocking code debt** · remaining = freeze ceremony (08-20) + secrets + deploy (09-03)  
**Authoritative queue:** `UNIFIED_EXECUTION_ORDER.md` · readiness: `docs/PROD_READINESS_CHECKLIST.md` · evidence: `IREIOS_4.0_EVIDENCE_PACK.md`

---

## 0. What engineering is freezing (done)

| Area | State | Proof |
|------|--------|--------|
| Backend APIs (sales-ai, neighborhood, twin, predictions) | Shipped | `2765de7`, `tests/test_f4_*` |
| FE cutover (Sales AI, forecast, graph, twin, JWT/SSE) | Shipped | P4-5…P4-9 |
| G5 gate | Green 2026-08-10 | Evidence Pack § G5 |
| FE lint / tsc / build | Exit 0 | `4494307` |
| Full pytest | 441 passed / 4 skipped | 2026-08-14 (`127920e` + auth unify) |
| Isolation + DLQ drills | PASS | 2026-08-10 |
| WA → SSE live smoke | PASS both modes | `wa_sse_smoke.py` 2026-08-11 |
| CC UX batch (twin Html labels, graph zoom freeze, sales-ai execute UX, terminal NBA) | Shipped | `127920e`, 2026-08-14 |
| n8n bridge **code** + unit tests | 14/14 | `tests/test_e20_n8n_bridge.py` |
| `task3_runner` | **Waived** (Gemini quota) | Mayank ack @ G5 |
| Flags / timeouts defaults | Correct in `config.py` | See §3 below |

**Not engineering’s job after this handoff:** new features, FE rewrites, n8n NBA, HubSpot bi-di, Approvals UI (all out of 4.0 / deferred 4.1).

---

## 1. Digital Twin — where it is (common miss)

Twin is **not** on the product Revenue OS sidebar (`/dashboard`, `/leads`, `/crm`).

| Surface | URL | Notes |
|---------|-----|--------|
| **Command Center** | **`/digital-twin`** | Nav: “Digital Twin” in command-center layout |
| API | `GET /api/v1/inventory/twin` | JWT cookie; `FEATURE_TWIN_LIVE=true` (default) |
| Seed | `python seed_twin_demo.py --client-id 1 --clear` | 1 project × 2 towers × 10 floors × 40 units |

Empty “Digital Twin empty / No inventory” = **no `InventoryUnit` rows for the logged-in tenant**, not missing code. After DB wipe/reset, re-run seed. Graph: **`/knowledge-graph`** + ego embed on **`/sales-copilot`**.

---

## 2. n8n — docker-hosted, deploy owner = Mayank

- Stack is **Compose n8n** (`n8n-local`), not cloud n8n SaaS.
- Workflow JSON is in repo: `n8n_workflows/wf1_…` … `wf6_…`.
- **Wiping docker volumes clears Publish state.** Fresh n8n logs: `0 published workflows` → production webhooks **404** until re-import + Publish.
- Live Gmail alerts **did work** on a prior setup; that does not persist across volume reset.
- Core chat/CRM path does **not** require n8n (degrades to `n8n_not_configured`).

### Re-activate after wipe (Mayank)

1. `docker compose up -d n8n redis` → http://localhost:5678 (create owner if first boot).
2. Credentials (exact names): `IREIOS API Key` = Header Auth `Authorization` = `Bearer {N8N_API_KEY}` (same as backend `.env`); plus Gmail / Sheets as needed.
3. Import: set `N8N_MANAGEMENT_API_KEY` from n8n **Settings → n8n API** (JWT — **not** the webhook secret) → `python import_n8n_workflows.py`  
   **or** CLI copy under `docs/N8N_INTEGRATION.md`.
4. Set Gmail **To** (WF-1/2/3/6), WF-5 Code `to`, WF-4 sheet id → **Save + Publish** all 6.
5. Backend `.env`: `N8N_BASE_URL=http://localhost:5678` (or `http://n8n:5678` in-compose), `N8N_API_KEY=…`, `N8N_BRIDGE_ENABLED=true`.
6. Smoke: publish `lead.hot` / curl webhook path `ireios_hot_lead_alert` — expect execution + Gmail (not 404).
7. Deploy hosts (Render/Vercel+API VM/etc.): **same Publish step on that environment’s n8n** — whoever deploys the compose stack owns this (Mayank).

Full: `docs/N8N_INTEGRATION.md`, `docs/N8N_GOOGLE_CREDENTIALS_SETUP.md`.

---

## 3. Flags & timings (verified 2026-08-13)

Defaults in `config.py` / `.env.example` — **do not lower** timeouts for prod.

| Flag / timing | Dev typical | **Prod** | Notes |
|---------------|-------------|----------|--------|
| `IS_PRODUCTION` | false | **true** | |
| `TEST_MODE` | true for local WA smoke | **false** | false = Twilio signature **on** |
| `FOLLOW_UP_TEST_MODE` | true local | **false** | true = 1‑min spam |
| `FOLLOW_UP_DLQ_TEST` | false | **false** | |
| `FEATURE_WHATSAPP_V3` | true | **true** | |
| `FOLLOWUP_ENGINE` | v3 | **v3** | `legacy` emergency only |
| `FEATURE_GRAPH_VIZ` | true | true | soft-empty if Neo4j down |
| `FEATURE_TWIN_LIVE` | true | true | empty if no inventory |
| `FEATURE_HUBSPOT_LIVE` | false | true **only** with real PAT | skippable |
| `WHATSAPP_WEBHOOK_TIMEOUT` | 13.0 | 13.0 | &lt; Twilio ~15s |
| `LLM_TIMEOUT_SECONDS` | 22.0 | 22.0 | may exceed race (inflight) |
| `RAG_TIMEOUT_SECONDS` | 2.0 | 2.0 | |
| `GRAPH_CONTEXT_TIMEOUT_SECONDS` | 0.5 | 0.5 | |

Full map: `docs/TIMEOUTS_AND_TIMINGS.md`.

---

## 4. Mayank — action list

### A. Before / at freeze 2026-08-20 (P4-QA)

| # | Action | Gate |
|---|--------|------|
| 1 | Declare feature freeze (bugfix only); tag **`ireios4-rc1`** | QA.1.1 |
| 2 | RC1 env: local `pg-staging` + snapshot **or** hosted staging if ready (`PROD_READINESS_CHECKLIST` §5) | QA.1.4 |
| 3 | Re-run on RC1: `pytest tests/ -q`, `gate_isolation_test.py`, `gate_dlq_drill.py` + `dlq_replay.py`, `wa_sse_smoke.py` (needs `TEST_MODE=true` for smoke), FE lint+build | QA.1.2–1.3 |
| 4 | Manual browser Q12: `/dashboard`, `/leads`, Sales AI, `/sales-copilot`, `/knowledge-graph`, **`/digital-twin`** (seed twin first) | QA.1.3 |
| 5 | Execute checklist ticks; draft runbook from checklist §5–§8 | QA.1.5 |
| 6 | Sign Evidence Pack QA + UNIFIED P4-QA `[x]` | QA.1.6 |
| 7 | Re-Publish docker n8n WFs if Gmail ops alerts desired (optional for core MVP) | §2 above |

### B. Production 2026-09-03 (P4-REL)

| # | Action | Gate |
|---|--------|------|
| 1 | Generate prod `JWT_SECRET_KEY`, `ADMIN_API_KEY`; confirm Gemini key | REL.1.1 |
| 2 | Receive Twilio (+ optional HubSpot) from Piyush; set flags per matrix §3 | REL.1.1 |
| 3 | Approve runbook; `db_backup.py` → `migrate_db.py` → deploy; Twilio webhook → prod URL; `TEST_MODE=false`; remove ngrok | REL.1.2 |
| 4 | Post-release: `/health`, `/metrics` (firewall), real WA, SSE, scheduler, escalation, bus | REL.1.3 |
| 5 | Name incident owner; own `/metrics`; document rollback | REL.1.4 |
| 6 | Evidence Pack Production + UNIFIED P4-REL `[x]` | REL.1.5 |

### C. Optional integrations (degrade if skipped)

Neo4j, Google Calendar SA, brochure/floorplan HTTPS URLs, `COMPETITOR_KEYWORDS`, n8n Gmail — each has enable/verify/rollback in `docs/PROD_READINESS_CHECKLIST.md` §6.

---

## 5. Piyush — action list (secrets / portal)

| # | Deliverable | Env | Required for 09-03? | How used |
|---|-------------|-----|---------------------|----------|
| 1 | Twilio Account SID | `TWILIO_ACCOUNT_SID` | **Yes** (live WA) | Outbound + signature validation |
| 2 | Twilio Auth Token | `TWILIO_AUTH_TOKEN` | **Yes** | |
| 3 | Twilio WhatsApp From number | `TWILIO_PHONE_NUMBER` | **Yes** | |
| 4 | HubSpot Private App Token | `CRM_API_KEY` (+ `CRM_API_URL`) | **No** — skippable | Contacts r/w; then Mayank sets `FEATURE_HUBSPOT_LIVE=true` |
| 5 | (If HS live) confirm portal + identity email/phone | — | Only if #4 | Outbound only; bi-di = 4.1 |

**Do not commit secrets.** Hand to Mayank via secure channel for prod `.env` only.

Without Twilio prod creds: code can deploy but **live WhatsApp production is blocked**.  
Without HubSpot: ship with `FEATURE_HUBSPOT_LIVE=false` (demo stub) — accepted for 4.0.

---

## 6. Local verify cheatsheet (Mayank)

```powershell
# Stack
docker compose up -d
# API (venv): uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# FE: cd frontend && npm run dev

python seed.py
python seed_twin_demo.py --client-id 1 --clear

# Health
curl http://localhost:8000/health

# Gates (freeze day)
pytest tests/ -q
python gate_isolation_test.py
python gate_dlq_drill.py
python dlq_replay.py
# WA smoke needs TEST_MODE=true in running uvicorn
python wa_sse_smoke.py

cd frontend
npm run lint
npm run build
```

**FE URLs after login:**  
Product home `/dashboard` · Command center twin `/digital-twin` · Graph `/knowledge-graph` · Copilot `/sales-copilot`

---

## 7. Explicit non-goals (do not reopen)

- HubSpot bi-directional · Approvals UI · LLM email draft · full multi-hop graph · twin write-back · new n8n WFs · trained ML · PG read/write routing (4.1)

---

## 8. Contacts / ownership

| Role | Person |
|------|--------|
| Tech lead, freeze, runbook, deploy, `/metrics`, docker n8n Publish | **Mayank** |
| Twilio + optional HubSpot PAT | **Piyush** |
| Program docs / evidence | `plans/phase4/*` + `docs/PROD_READINESS_CHECKLIST.md` |
