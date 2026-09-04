# Production Hardening Sprint — Backend + AI & Automation Certification

| This doc owns | Does not own |
|---|---|
| Piyush hardening sprint: Aritro backend cert, Maitri 100-eval, joint Twilio/n8n drill; exit = two cert reports | Order / gates → `UNIFIED_EXECUTION_ORDER.md` |
| | Atomic P4/QA/REL tasks → `IREIOS_4.0_STEP_BY_STEP.md` |
| | Locked 4.0 decisions → `TEAM_LEAD_QUESTIONNAIRE_ANSWERED.md` |
| | Prod flags/secrets/infra → `../../docs/PROD_READINESS_CHECKLIST.md` |

**Status legend:** `[ ]` pending · `[~]` in progress · `[x]` done · `[-]` skipped (reason required)
**Date:** 2026-09-04 · **Branch of record:** `phase4_tests` @ `89f0243` · **Do not certify on `main` (3.0) / `hotfix/rc2-hubspot` / `post_automation_fixes`**
**Owners:** PH-A Aritro · PH-B Maitri · PH-C joint · sign-off Mayank
**Exit gate:** Appendix A (Backend Production Certification) + Appendix B (AI & Automation Certification) filled with evidence → feeds UNIFIED **P4-QA / P4-REL**

**Prerequisite:** P4-0…P4-9 + **G5 green** (`IREIOS_4.0_EVIDENCE_PACK.md`). This sprint does **not** reopen 4.0 scope.

---

## 1. Hard rules

1. **Certify on `phase4_tests` only.** Clean tree, no local mixed-branch files. No merges/tags by Aritro/Maitri — `hotfix/rc2-hubspot` merge and `ireios4-rc1` tag are Mayank's call.
2. **Serial order:** PH-0 → PH-A.1 → PH-C → (PH-A.2 ∥ PH-B) → PH-A.3 → PH-A.4 → PH-R. PH-C before the 100-eval so duplicate/noise does not contaminate NLP evidence.
3. **No new n8n WFs** (locked Q4.2). Joint drill proves existing bridge + WF-1…6 do not double-fire.
4. **Gemini budget split** (G5 waived `task3_runner` for quota): load = HTTP concurrency at 25/50/100 (Twilio-shaped, mockable LLM); 100-eval = sequential fresh live conversations, rate-limited.
5. **Destructive work on staging only.** DR drill targets local `pg-staging` per `PROD_READINESS_CHECKLIST.md` §5.1, never the eval DB. Maitri's 100 uses soft wipe only (`docs/MAINTENANCE.md` §4.1).
6. **Tenant isolation never regresses** — `python gate_isolation_test.py` after load and after DR.

---

## 2. Locked decisions (summary)

| Topic | Decision |
|---|---|
| Cert branch | `phase4_tests` @ `89f0243`; `main` tag on current `main` is stale (3.0) |
| Load shape | 25 / 50 / 100+ concurrent chats → latency + drop + interim + duplicate-process counts |
| NLP shape | 100 **fresh** conversations (no `seed_dummy_leads.py` / demo reuse): Hindi, Hinglish, typos, budget changes, edge cases |
| Twilio drills | `TEST_MODE=true` (signature bypass); real Twilio only if Mayank/Piyush provide sandbox number |
| n8n proof | Live docker n8n if Mayank re-Publishes; else `test_e20_n8n_bridge.py` + execution-count evidence |
| DR target | Local `pg-staging` seeded from snapshot; Redis loss documented, not treated as durable |
| Logs | `tenant_id_ctx` on every job/API/queue before drills so cert lines carry `[Tenant: Client_N]` |

---

## 3. Master sequence

| Step | Unit | Summary | Exit gate | Owner | Status |
|---:|---|---|---|---|---|
| **PH-0** | Prep | Merge answer, stack up, flags, quota note, wipe plan | Stack + flags recorded | Both | `[ ]` |
| **PH-A.1** | Tenant logs | `tenant_id_ctx` on all jobs / APIs / bus / EE | Every scheduler+bus path logs `[Tenant: …]` | Aritro | `[ ]` |
| **PH-C** | Joint drill | Duplicate / simultaneous / retry webhooks + n8n single-fire | Matrix §C all PASS | Aritro+Maitri | `[ ]` |
| **PH-A.2** | Load | 25 / 50 / 100 concurrent chats: latency + drop rates | Numbers table in Appendix A | Aritro | `[ ]` |
| **PH-B** | 100-eval | Fresh 100 convos + stop-on-reply / fallback / opt-in | JSON + summary in Appendix B | Maitri | `[ ]` |
| **PH-A.3** | DR | Backup → failure sim → restore → verify on `pg-staging` | Appendix A §DR | Aritro | `[ ]` |
| **PH-A.4** | Security | Secrets / flags / auth / `/metrics` audit | Appendix A §Security | Aritro | `[ ]` |
| **PH-R** | Reports | Fill Appendices A+B, Mayank sign-off | UNIFIED **PH** → `[x]` | Both | `[ ]` |

PH-A.2 ∥ PH-B allowed after PH-C. Everything else serial.

---

## 4. Dependency matrix

| Dependent | Blocked by | Clears |
|---|---|---|
| Joint drill PH-C | Tenant logs PH-A.1 (else logs uncertifiable) | PH-C |
| Load PH-A.2 | PH-C (dedupe proven first) | Appendix A load |
| 100-eval PH-B | PH-C + soft wipe (clean corpus) | Appendix B |
| DR PH-A.3 | PH-A.2 done (load artifacts kept) + staging ready | Appendix A DR |
| Reports PH-R | All above + isolation re-run | P4-QA input |

---

## 5. Day-to-day workflow

1. First non-`[x]` step in §3.
2. Implement per task below; log deltas in `IREIOS_4.0_CHANGELOG.md`.
3. Tick status here + `IREIOS_4.0_EVIDENCE_PACK.md` § Hardening.
4. Never edit frozen contracts (`IREIOS_4.0_API_CONTRACTS.md`) or restructure `PROD_READINESS_CHECKLIST.md` (additive rows only, §9).

---

## PH-0 — Prep

### Task PH-0.1 — Stack up + record flags
- **Files:** none (env only)
- **Steps:**
  1. `git status` clean on `phase4_tests`; record HEAD hash in both appendices.
  2. `docker compose up -d` → `python seed.py` → `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`.
  3. Smoke: `curl http://localhost:8000/health` → 200; log shows `EventBus started`.
  4. Record drill flags: `TEST_MODE=true` for webhook/duplicate hammer; `FOLLOW_UP_TEST_MODE=false` for opt-in / stop-on-reply tests; `FOLLOWUP_ENGINE=v3`; `FEATURE_WHATSAPP_V3=true`.
  5. Quota note: agree Gemini budget with Mayank (load = HTTP-shape, 100-eval = sequential live). Reference: Evidence Pack G5 `task3_runner` waiver.
- **Test:** `/health` 200
- **Done:** HEAD + flags pasted into Appendices A/B header
- **Rollback:** N/A
- **Status:** `[ ]`

### Task PH-0.2 — n8n + wipe readiness
- **Files:** none (ops)
- **Steps:**
  1. n8n: `docker compose up -d n8n redis` → http://localhost:5678. If `0 published workflows` (volume wipe), re-import + **Publish all 6** per `HANDOFF_MAYANK_PIYUSH.md` §2 and `docs/N8N_INTEGRATION.md`. Set `N8N_BASE_URL` / `N8N_API_KEY` / `N8N_BRIDGE_ENABLED=true`.
  2. Confirm bridge-only fan-out: catalog `lead.hot` mapped, alias `lead.escalated` **not** mapped (`app/automation_engine/n8n_bridge.py` `DEFAULT_WEBHOOK_MAP`; `docs/N8N_INTEGRATION.md` § Dual-publish).
  3. Maitri wipe (before PH-B only): PG **soft** + Neo4j soft per `docs/MAINTENANCE.md` §4.1. Do not hard-wipe tenants.
  4. DR staging (before PH-A.3 only): stand up `pg-staging` per `PROD_READINESS_CHECKLIST.md` §5.1.
- **Test:** `python -m pytest tests/test_e20_n8n_bridge.py -q` → 14/14
- **Done:** n8n Publish state + wipe/staging plan noted in reports
- **Rollback:** `N8N_BRIDGE_ENABLED=false` if n8n blocks drills
- **Status:** `[ ]`

---

## PH-A.1 — Tenant-aware logs (Aritro)

### Task PH-A.1.1 — Close the `tenant_id_ctx` gaps
- **Files:**
  - Edit: `main.py` (`daily_cleanup_job`, scheduler section), `crm_sync.py` (`crm_resync_job`), `app/workflows/competitor_monitor.py`, weekly marketing cron, `expire_stale_approvals` path
  - Edit: `app/clients/event_bus_client.py` (`_consume_loop`), `app/orchestrator/ceo_orchestrator.py`, `app/automation_engine/n8n_bridge.py`, `app/execution_engine/execution_engine.py`
  - Reference: `config.py:186` (`tenant_id_ctx`), `main.py:198` (`SecurePIILogFilter` already prefixes `[Req: …] [Tenant: …]` + PII masking), `auth.py` + `follow_up.py:388` + escalation loop (already set — copy pattern)
- **Steps:**
  1. Grep every APScheduler registration in `main.py` (`follow_up_checker`, `nightly_backup`, `nightly_cleanup`, `escalation_checker`, `crm_resync`, `competitor_monitor`, `weekly_marketing_report`, `expire_approvals`) + bus `_consume_loop` + CEO handlers + bridge + EE `dispatch`.
  2. Per unit of work set `tenant_id_ctx.set(f"Client_{id}")`; global jobs (cleanup/backup/competitor scan) set `"ops"` and include entity id in the message.
  3. Keep PII masking intact (phone/email regex in filter); never log raw secrets.
  4. Verify: trigger each job once; assert one log line per job carries `[Tenant: Client_N]` / `[Tenant: ops]`.
- **Test:**
  ```powershell
  pytest tests/ -q
  python gate_isolation_test.py
  ```
- **Done:** Gap table (job → ctx source) in Appendix A; log excerpts attached
- **Rollback:** git revert file-by-file; filter unchanged so old lines still parse
- **Status:** `[ ]`

---

## PH-C — Joint Twilio + n8n drill (Aritro + Maitri, coordinate window)

### Task PH-C.1 — Duplicate / simultaneous / retry webhooks
- **Files:**
  - Reference: `main.py` (`WebhookLog` insert-first, `interim_sent:{MessageSid}` 120s TTL, `_session_turn_locked`, `_await_inflight_and_push`), `agent.py` (`_has_recent_duplicate_message`), `tests/test_p3_concurrency.py` (source-inspection baseline — now prove live)
- **Steps:**
  1. `TEST_MODE=true` in running uvicorn (bypass `X-Twilio-Signature`).
  2. Case 1 — duplicate `MessageSid`: POST same Sid twice to `/api/v1/whatsapp` (Twilio form: `From`, `Body`, `MessageSid`). Expect: first processes, second returns empty `<Response></Response>`, one Gemini turn, one `WebhookLog` row.
  3. Case 2 — simultaneous, same `From`, different Sids: fire N parallel POSTs (asyncio gather / parallel curl). Expect: `session_lock:{session_id}` serializes; no interleaved mid-Gemini replies; follow-up state consistent.
  4. Case 3 — Twilio retry: repeat same Sid after 5s. Expect: idempotent, no second turn.
  5. Count per case: HTTP code, TwiML vs empty vs interim, Gemini turns, `WebhookLog` rows, `Message` rows.
- **Test:**
  ```powershell
  pytest tests/test_p3_concurrency.py -v
  python gate_isolation_test.py
  ```
- **Done:** Case table with counts in both appendices
- **Rollback:** N/A (read-only proof; soft-wipe noise sessions after)
- **Status:** `[ ]`

### Task PH-C.2 — n8n single-fire proof
- **Files:**
  - Reference: `app/automation_engine/n8n_bridge.py`, `app/events/lead_hot.py` (dual-publish), `docs/N8N_INTEGRATION.md` (bridge group `ireios-n8n`, never CEO `ireios-cg`), `tests/test_e20_n8n_bridge.py`
- **Steps:**
  1. Publish/trigger **one** `lead.hot` (catalog only). Assert n8n WF-1 executes **once** (n8n execution log count = 1).
  2. Assert alias `lead.escalated` does **not** fire a second workflow (default map excludes it).
  3. Assert AE `template_type="n8n"` fallback is **off** for the same alert when bridge is on (never both — else double Gmail).
  4. Repeat the duplicate-Sid case from PH-C.1 with bridge on; n8n execution count stays 1.
- **Test:**
  ```powershell
  python -m pytest tests/test_e20_n8n_bridge.py -q
  ```
- **Done:** n8n execution counts pasted into both appendices; double-fire = FAIL, stop and fix map before PH-A.2/PH-B
- **Rollback:** `N8N_BRIDGE_ENABLED=false` to isolate
- **Status:** `[ ]`

---

## PH-A.2 — Load 25 / 50 / 100 (Aritro)

### Task PH-A.2.1 — Concurrency hammer (HTTP shape)
- **Files:**
  - New harness (e.g. `load_chat_concurrency.py`, TEST tooling — keep out of `tests/`): POST Twilio form to `/api/v1/whatsapp` with unique `MessageSid` per request; N sessions for "concurrent chats"; reuse a Sid subset for drop-vs-dedupe
  - Reference: `task3_runner.py` (turn shape, `--base-url`, `--skip-db` flags), `docs/TIMEOUTS_AND_TIMINGS.md` (13s race, 22s LLM cap), `wa_sse_smoke.py` (turn 4.9–11.3s baseline)
- **Steps:**
  1. `TEST_MODE=true`; LLM mockable/stubbed for the 50/100 legs (quota rule §1.4). Optional ≤25-live Gemini sample for true p95.
  2. Run 25 → 50 → 100 concurrent chats. Per leg record: HTTP code, wall ms, TwiML vs interim (`Just checking…`) vs empty, 5xx count, drop count, duplicate-process count (same Sid processed twice = defect).
  3. Capture p50/p95, 5xx rate, interim rate, bus/DLQ depth (`/metrics`: `http_request_duration_seconds`, `dlq_pending_events`, scheduler health).
  4. Re-run `python gate_isolation_test.py` after the 100 leg.
- **Test:**
  ```powershell
  python gate_isolation_test.py
  python gate_dlq_drill.py
  python dlq_replay.py
  ```
- **Done:** Appendix A load table filled (draft pass: 25 → p95 < 13s, drop 0%; 50 → p95 < 15s, 5xx < 1%; 100 → document cliff + zero duplicate-Sid processing). Tune thresholds with Mayank if infra differs.
- **Rollback:** N/A; soft-wipe load sessions after
- **Status:** `[ ]`

---

## PH-B — Fresh 100-conversation eval (Maitri)

### Task PH-B.1 — Build + run the fresh corpus
- **Files:**
  - Extend `task3_runner.py` or sibling eval (e.g. `eval_100_fresh.py`): unique session ids, sequential + rate-limited live calls to `/api/v1/chat` (or WhatsApp path), JSON + summary artifacts like `task3_runner`
  - Reference: `task3_runner.py` dynamic checks (location/budget/BHK last-wins, HOT/WARM/COLD behavior), `tests/test_p2_fsm_language.py` (language gate), `tests/test_p0_safety.py` (opt-out)
- **Steps:**
  1. Soft-wipe traffic tables (PH-0.2). Confirm zero reused demo sessions.
  2. 100 fresh conversations across: Hindi (Devanagari) · Hinglish · typos · budget change mid-thread (last-wins) · location switch · visit-date vagueness · STOP / "don't message" · empty / greeting-only · mixed-language · escalation-worthy HOT.
  3. Per convo record: turns, replies, `Lead` extraction (location/budget/property_type/name/phone/visit_date), temperature, fallback hits, error phrases (`task3_runner.FAILURE_PHRASES`).
  4. Language rule (locked): English by default; Hinglish only after user initiates (`plans/phase3/BUG_AUDIT_AND_PHASED_FIX_PLAN.md` §1).
- **Test:**
  ```powershell
  pytest tests/test_p0_safety.py tests/test_p2_fsm_language.py -v
  ```
- **Done:** Pass-rate table by category + failure triage in Appendix B; corpus + JSON artifact paths recorded
- **Rollback:** N/A; corpus kept for regression
- **Status:** `[ ]`

### Task PH-B.2 — Stop-on-reply + fallback + opt-in proof
- **Files:**
  - Reference: `app/intelligence/push_wait_engine.py` (`replied` → `stop_followups`), `follow_up.py:419-423` (opt-out skip), `app/workflows/followup_scheduler.py:108`, `agent.py:137-183` (`is_opt_out_message`, opt-out reply + close)
- **Steps:**
  1. Stop-on-reply: arm Day-0 follow-up, then user replies → assert scheduler skips/stops (no further auto nudges; cooldown respected).
  2. Fallback: force Gemini failure/timeout → assert safe template reply, no error-phrase leak, DLQ row only where specified (`twilio_outbound` / `ml_followup_scheduler`).
  3. Opt-in: send STOP variants (`stop`, `unsubscribe`, `don't message`) → assert `whatsapp_opt_in=False`, session closed, follow-ups stopped; re-arm never fires while opted out.
  4. Assert portal ingest defaults (`main.py` ingest `whatsapp_opt_in=False`) vs interactive chat opt-in path.
- **Test:**
  ```powershell
  pytest tests/test_p0_safety.py tests/test_e4_followup.py -v
  ```
- **Done:** Three mini-tables (stop-on-reply / fallback / opt-in) with DB evidence in Appendix B
- **Rollback:** N/A
- **Status:** `[ ]`

---

## PH-A.3 — Disaster recovery drill (Aritro, on `pg-staging`)

### Task PH-A.3.1 — Backup → fail → restore → verify
- **Files:**
  - Reference: `docs/BACKUP_RESTORE_DRILL.md` (procedure + 7-table check), `docs/MAINTENANCE.md` §4–5 (wipes, scheduler, bus), `db_backup.py`, `db_restore.py`, `project_leads_to_neo4j.py`
- **Steps:**
  1. Seed staging → `python db_backup.py` → record artifact name + size + timestamp.
  2. Failure sim, one at a time: `docker stop` postgres → record `/health` + chat behavior; restart. Then redis (bus/locks degraded; document lost unacked stream events). Then neo4j (graph soft-empty; chat unaffected).
  3. Restore: `python db_restore.py backups/backup_*.sql` against staging → 7-table count check (`clients`, `sessions`, `leads`, `messages`, `event_logs`, `follow_up_states`, `dlq_events`).
  4. Rebuild graph if used: `python project_leads_to_neo4j.py`; re-run one WA turn + `gate_isolation_test.py` + DLQ drill.
  5. Record RTO/RPO observed + off-box backup gap (`BACKUP_RESTORE_DRILL.md` §5: local disk lost on redeploy).
- **Test:**
  ```powershell
  python gate_isolation_test.py
  python gate_dlq_drill.py
  python dlq_replay.py
  ```
- **Done:** Appendix A §DR filled (artifact, kill log, restore log, counts, RTO/RPO)
- **Rollback:** Restore is the rollback; keep pre-drill snapshot
- **Status:** `[ ]`

---

## PH-A.4 — Security / secrets audit (Aritro)

### Task PH-A.4.1 — Audit + flag matrix
- **Files:**
  - Reference: `docs/PROD_READINESS_CHECKLIST.md` §2–§4 (env map, flag matrix, secrets track), `docs/BACKEND_RELIABILITY_CHECKLIST.md` (auth layers), `.env.example` footer
- **Steps:**
  1. Grep for committed secrets / demo keys in tracked files; confirm `.env*` gitignored; `frontend/src` free of `secret-client-key-123`.
  2. Verify three auth layers live: API key (ingest), JWT Bearer-or-cookie (dashboard + twin/neighborhood/predictions), `X-Admin-Key` on ROI/pipeline (still admin-only, no client exposure).
  3. Verify `TEST_MODE=false` enables Twilio signature; drill flags (`FOLLOW_UP_TEST_MODE`, `FOLLOW_UP_DLQ_TEST`) recorded off for prod.
  4. `/metrics` public → firewall/allow-list note + owner (Mayank).
  5. Default `ADMIN_API_KEY` (`real-estate-super-secret-key`) rejected at boot (`main.py:verify_admin_key`); prod JWT/admin secrets marked generate-before-REL.
- **Test:** `pytest tests/test_f4_jwt_auth.py -v` + manual 401-unauth check
- **Done:** Appendix A §Security checklist ticked with evidence
- **Rollback:** N/A (audit only; flag flips happen at P4-REL)
- **Status:** `[ ]`

---

## PH-R — Reports + sign-off

### Task PH-R.1 — Fill certs, hand to Mayank
- **Files:** this doc Appendices A+B; mirror checkboxes into `IREIOS_4.0_EVIDENCE_PACK.md` § Hardening
- **Steps:**
  1. Aritro fills Appendix A; Maitri fills Appendix B (numbers, not adjectives).
  2. Both record branch HEAD, env, artifact paths, FAIL triage with file:line.
  3. Mayank signs; UNIFIED **PH** → `[x]`; open FAILs become GitHub Issues (no zero-day hiding).
- **Done:** Two reports complete; P4-QA unblocked
- **Status:** `[ ]`

---

## 6. Rollback / emergency

| Problem | Action |
|---|---|
| Load melts Gemini quota | Stop live legs; finish HTTP-shape legs; note in Appendix A |
| n8n double-fires | `N8N_BRIDGE_ENABLED=false`; fix map (catalog only); re-run PH-C.2 |
| DR restore fails | Keep pre-drill snapshot; `db_restore.py` retry; escalate Mayank |
| 100-eval pollutes DB | Soft-wipe traffic tables; rebuild corpus ids; re-run affected slice |
| Freeze conflict | This sprint yields to Mayank's P4-QA tag; resume on RC env if ordered |

---

## 7. Pointers

| Need | Path |
|---|---|
| Order / gates | `UNIFIED_EXECUTION_ORDER.md` |
| QA/REL atoms | `IREIOS_4.0_STEP_BY_STEP.md` QA/REL |
| Flags/secrets/infra | `../../docs/PROD_READINESS_CHECKLIST.md` |
| Timeouts map | `../../docs/TIMEOUTS_AND_TIMINGS.md` |
| Wipes / scheduler ops | `../../docs/MAINTENANCE.md` |
| Backup/restore base | `../../docs/BACKUP_RESTORE_DRILL.md` |
| Reliability baseline | `../../docs/BACKEND_RELIABILITY_CHECKLIST.md` |
| n8n arch + publish | `../../docs/N8N_INTEGRATION.md`, `../../docs/N8N_GOOGLE_CREDENTIALS_SETUP.md` |
| Freeze handoff | `HANDOFF_MAYANK_PIYUSH.md` |
| Evidence | `IREIOS_4.0_EVIDENCE_PACK.md` § Hardening |

---

## Appendix A — Backend Production Certification Report (Aritro)

**Branch HEAD:** ________ · **Env:** ________ · **Date:** ________

### A.1 Tenant-aware logs
| Job / path | ctx source | Log excerpt `[Tenant: …]` |
|---|---|---|
| `follow_up_checker` / `follow_up.py` | `state.client_id` (existing) | |
| `escalation_checker` | `log.client_id` (existing) | |
| `daily_cleanup_job` | `ops` | |
| `nightly_backup` | `ops` | |
| `crm_resync` | per-lead `client_id` | |
| `competitor_monitor` | `ops` | |
| `weekly_marketing_report` | `ops` | |
| `expire_approvals` | per-row tenant | |
| bus `_consume_loop` / CEO / bridge / EE | envelope `tenant_id` | |

### A.2 Load — 25 / 50 / 100 concurrent chats
| Leg | p50 | p95 | 5xx | Drops | Interim rate | Dup-Sid processed | Verdict |
|---|---|---|---|---|---|---|---|
| 25 | | | | | | 0 required | |
| 50 | | | | | | 0 required | |
| 100+ | | | | | (document cliff) | 0 required | |
Isolation after load: `gate_isolation_test.py` ________ · Artifacts: ________

### A.3 Disaster recovery (`pg-staging`)
| Step | Evidence |
|---|---|
| Backup artifact + size + time | |
| PG kill → `/health` + chat behavior | |
| Redis kill → bus/lock behavior | |
| Neo4j kill → graph degrade | |
| Restore log + 7-table counts | |
| Post-restore WA turn + isolation + DLQ | |
| Observed RTO / RPO + off-box gap | |

### A.4 Security / secrets
| Check | Result |
|---|---|
| No secrets / demo keys in git; `.env*` ignored; `frontend/src` clean | |
| API-key / JWT / Admin-key layers live; ROI admin-only | |
| Twilio sig enforced at `TEST_MODE=false`; drill flags off for prod | |
| `/metrics` firewall note + owner | |
| Prod secrets (JWT/admin/Twilio) track status | |

**Aritro sign:** ________

---

## Appendix B — AI & Automation Certification Report (Maitri)

**Branch HEAD:** ________ · **Env:** ________ · **Date:** ________ · **Corpus:** ________ (fresh, no demo reuse)

### B.1 Fresh 100 — pass by category
| Category | n | Pass | Notes / FAIL ids |
|---|---|---|---|
| Hindi (Devanagari) | | | |
| Hinglish | | | |
| Typos / noisy input | | | |
| Budget change mid-thread (last-wins) | | | |
| Location switch / vague visit date | | | |
| STOP / opt-out | | | |
| Empty / greeting-only | | | |
| Mixed-language | | | |
| HOT escalation-worthy | | | |
| Edge (other) | | | |
| **Total** | **100** | | |

### B.2 Stop-on-reply / fallback / opt-in
| Check | Proof (DB/log) | Verdict |
|---|---|---|
| Reply after Day-0 arm → no further nudges | | |
| Gemini fail → safe template, no error-phrase leak | | |
| STOP → `whatsapp_opt_in=False`, closed, no re-arm | | |
| Portal ingest default `False` vs chat opt-in | | |

### B.3 Joint n8n (with Aritro)
| Case | n8n executions | Verdict |
|---|---|---|
| Single `lead.hot` → WF-1 | 1 required | |
| `lead.escalated` alias → no 2nd fire | 0 required | |
| Duplicate-Sid turn → n8n count unchanged | +0 required | |

Artifacts (JSON + summary): ________ · FAIL triage (file:line): ________

**Maitri sign:** ________ · **Mayank sign:** ________
