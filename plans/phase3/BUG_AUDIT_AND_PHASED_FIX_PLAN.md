# Bug Audit & Phased Fix Plan

**Project:** Real Estate AI Lead Agent (IREIOS)  
**Date:** 2026-07-09  
**Status:** Planning only — implementation deferred by sprint  
**Branch context:** `phase3_initial` (includes universal qualification override fix)

---

## 1. Purpose and scope

This document is a full-codebase audit of **confirmed behavioral bugs**, with longer root-cause analysis and concrete fix plans. It is intended as the implementation backlog for multi-sprint delivery.

### In scope

- Agent assignment (`assigned_agent`, matcher, notifications, claim)
- Chat / session / follow-up state machines
- WhatsApp webhook concurrency and idempotency
- Notification escalation and delivery safety
- CRM sync completeness
- Funnel stage and frontend schema alignment
- Data quality (name interceptor, fake defaults)
- Reply language matching (English default vs Hinglish only when user initiates)

### Out of scope (for this plan)

- Greenfield multi-tenant RBAC product redesign (beyond removing mock filters)
- Full HubSpot custom-property provisioning in HubSpot UI
- Replacing Redis lock infrastructure wholesale
- Pure style / lint / performance nits without user-visible failure
- Full multilingual support beyond English + Latin-script Hinglish (no Devanagari product track in this plan)

### Product decisions locked in for this plan

| Decision | Choice | Implication |
|----------|--------|-------------|
| Assignment stickiness | **Rematch until claimed** | While `Lead.conversion_status != "claimed"`, rematch is allowed. Once claimed, never rematch. |
| Delivery order | Phase by **criticality** | Safety hotfixes first, then assignment, then FSM, then concurrency, then polish. |
| Scope of work | **Entire codebase** | Not assignment-only. |
| Reply language | **Strict English by default; Hinglish only when user initiates** | If the user writes standard English (including Indian place/property nouns like Hinjewadi, 2BHK), the bot must reply in natural English. Switch to Hinglish only after the user uses clear Hindi/Hinglish words (e.g. `mujhe`, `chahiye`, `kya hai`). Never open in Hinglish on pure-English messages. |

---

## 2. Executive summary

The system has six recurring failure themes:

1. **Assignment lifecycle is incomplete**  
   Matching only runs on the “happy” LLM path, often *after* hot notifications are fired. Handoff exits early with no assignee. Workload counters only increment. Re-matching every turn can thrash agents and inflate load.

2. **Session / follow-up FSM is not terminal**  
   Fully qualified and opted-out sessions can be reopened by later non-closing messages. Follow-up re-arm then restarts Day 0. Substring `"bye"` closes chats on words like **buyer**.

3. **Notification routing is unsafe under missing agents**  
   If no agent or manager resolves, the hot-lead WhatsApp can fall back to **the lead’s own phone**. Failed notification rows are re-alerted forever without status transition.

4. **WhatsApp timeout path double-processes**  
   On 15s timeout the in-flight work is cancelled, the session lock is released, and a background task re-runs the full pipeline without the lock—duplicate side effects and races.

5. **CRM and funnel data drift**  
   CRM sync fires once at lead create (often empty fields). Funnel stage strings diverge from frontend columns. Sales status (`conversion_status`) and chat status (`session.status`) are overloaded in product language.

6. **Reply language is prompt-only and drifts to Hinglish**  
   Product policy is strict English by default. In production WhatsApp, pure-English openers (e.g. `hi, need 2bhk in hinjewadi`) still receive Hinglish replies from Gemini (`conversational_reply`). There is no runtime language gate—only soft system-prompt rules that the model often ignores for Pune/real-estate context.

None of these are “SDK quirks” alone; most are ordering, state-machine, fallback, and missing hard-constraint bugs in application code.

---

## 3. System context (read before fixing)

### 3.1 Three different “status” fields

| Field | Model | Typical values | Meaning |
|-------|--------|----------------|---------|
| `Session.status` | Chat FSM | `active`, `closed` | Whether the AI conversation is open |
| `Lead.conversion_status` | Sales FSM | `open` (default), `claimed` | Whether a human has claimed the lead on the dashboard |
| `NotificationLog.status` | Alert FSM | `pending_ack`, `acknowledged`, `escalated_10m`, `escalated_30m`, `failed` | Escalation / ack state of a hot-lead alert |

**Important:** `pending_ack` is **not** a conversion status. It lives only on `NotificationLog`.

Today:

- Full qualification closes **session** and completes follow-up, but leaves `conversion_status = "open"`.
- Acknowledge sets `conversion_status = "claimed"` and acknowledges the notification log; it does **not** necessarily bind a real human agent identity to `assigned_agent`.

### 3.2 Where assignment is supposed to happen

Primary path: end of `process_chat` in `agent.py` after ML scoring:

1. Optionally fire hot notification when `prob >= 82`
2. Call `match_best_agent(...)`
3. If result has a name, set `lead.assigned_agent` and audit-log

Many early returns (instant greetings, property openers, guardrails, **human handoff**, LLM failure) **never reach** step 2–3.

### 3.3 Where notifications resolve the agent

`notification_service.trigger_hot_lead_notification`:

1. Opens a **new** DB session
2. Loads lead
3. Looks up `Agent` by exact name match to `lead.assigned_agent`
4. Falls back to manager (`is_manager == True`)
5. If still none, currently falls back to **`lead.phone`** (bug)

So assignment must be **committed before** the notification task runs, or the notifier will not see the assignee.

---

## 4. Phase 0 — Safety hotfixes

**Goal:** Stop irreversible / compliance / customer-facing damage with small diffs.  
**Sprint:** A  
**Risk:** Low if changes stay narrow.

---

### P0.1 — `"bye" in msg_clean` closes sessions on “buyer”

**Severity:** Critical  

**Problem**  
Closing detection uses a substring check:

```text
"bye" in msg_clean
```

Any message containing the letters `bye` as a substring matches—including:

- “I am a **buyer**”
- “**maybe** next week”
- “**byelaw** / society rules”

Those messages mark the session `closed` and stop follow-ups mid-qualification.

**Evidence**  
`agent.py` (closing-phrase block, ~309–311): closing condition includes `"bye" in msg_clean`.

**Impact**

- Core real-estate phrasing (“buyer looking for 2BHK…”) kills the conversation.
- Follow-ups stop; qualification funnel freezes.
- Hard to notice in demos that use “buy” without “buyer”.

**Root cause**  
Substring matching instead of token / exact-phrase matching.

**Fix plan**

1. Remove bare `"bye" in msg_clean`.
2. Treat goodbye as:
   - exact token in `msg_clean.split()`: `bye`, `goodbye`, or
   - exact phrases already in `closing_phrases` (`goodbye`, etc.).
3. Prefer word-boundary regex if you need multi-word safety: `\b(bye|goodbye)\b`.
4. Add unit/regression tests:  
   - `"I am a buyer in Baner"` → **not** closed  
   - `"bye"` / `"goodbye"` → closed  
   - `"maybe tomorrow"` → **not** closed  

**Files:** `agent.py` only.

---

### P0.2 — Hot alert can WhatsApp the **customer**

**Severity:** Critical  

**Problem**  
When no `Agent` row matches `lead.assigned_agent` and no manager exists:

```text
agent_phone = target_agent.phone if target_agent else lead.phone
```

Twilio then sends the internal “Hot Lead Alert / contact within 10 minutes” template to **`lead.phone`**—the prospect.

**Evidence**  
`notification_service.py` (~98–125): fallback phone and Twilio `to=` construction.

**Impact**

- Process and internal ops text leaked to customers.
- Confusing / alarming UX for the lead.
- Potential compliance / trust damage.

**Root cause**  
Unsafe “always have a phone” fallback; prospect contact treated as agent contact.

**Fix plan**

1. Resolve `target_agent` (assigned name match → manager).
2. If still no agent:
   - Log critical error
   - Email `ADMIN_EMAIL` (or existing fallback email helper) with lead id + reason
   - Create `NotificationLog` with `status="failed"` (or skip log but never SMS lead)
   - **Return without Twilio WhatsApp**
3. Never assign `agent_phone = lead.phone`.
4. Regression: empty `agents` table + hot trigger → zero Twilio messages to lead number.

**Files:** `notification_service.py`.

---

### P0.3 — `agent_phone` can be `None` and crash

**Severity:** High  

**Problem**  
If both agent and `lead.phone` are missing, code later does `agent_phone.startswith(...)` → `AttributeError`. Outer try/except swallows it → silent notification failure.

**Evidence**  
`notification_service.py` (~98, ~125).

**Impact**  
Hot leads produce no alert and no clear operational signal beyond a generic exception log.

**Root cause**  
Missing null guard before string methods.

**Fix plan**

1. After resolution, if `not agent_phone`: same safe path as P0.2 (email admin, mark failed, return).
2. Only call `.startswith` on a non-empty string.
3. Cover with a unit test using a lead without phone and without agents.

**Files:** `notification_service.py` (same PR as P0.2).

---

### P0.4 — Closed / qualified sessions reopened by later messages

**Severity:** Critical  

**Problem**  
At the start of a turn, full qualification correctly sets:

- `session.status = "closed"`
- follow-up `completed`

Then closing detection runs:

- If message is **not** a closing phrase → `session.status = "active"` **unconditionally**

So a later `"hi"` or `"ok"` after a booked visit reopens the chat FSM. End-of-turn re-arm can then set follow-up back to Day 0 **active** because status is no longer closed.

**Evidence**  
`agent.py` (~285–288 close on qualify; ~324–325 force active; ~1041–1047 re-arm when not closed).

**Impact**

- Booked / finished deals get automated follow-ups again.
- Universal qualification close becomes non-durable.
- Product promise “session closed when deal done” is false.

**Root cause**  
“User replied ⇒ always active” overwrites terminal states. No terminal-state guard.

**Fix plan**

1. Define terminal conditions for chat:
   - `session.status == "closed"` already, **and**
   - `lead.whatsapp_opt_in is False`, **or**
   - fully qualified (all six fields), **or**
   - explicit handoff-closed (optional flag / funnel stage Human Handoff)
2. Replace the else branch:

   ```text
   else:
       if not is_terminal(...):
           session.status = "active"
       # else leave closed
   ```

3. Re-arm block must also refuse to activate follow-ups when opted out or fully qualified (even if status wrongly active—defense in depth).
4. Regression: fully qualify → `"hi"` → still closed, follow-up stays completed.

**Files:** `agent.py`; possibly shared helper used by `follow_up.py`.

---

### P0.5 — Opt-out is not durable

**Severity:** Critical  

**Problem**  
Opt-out sets `lead.whatsapp_opt_in = False` and closes the session. The follow-up scheduler only checks roughly:

```text
session.status == "closed" OR lead.visit_date
```

It never reads `whatsapp_opt_in`. Combined with P0.4, a later user message reopens the session and re-arms follow-ups → automated messages resume after “stop”.

**Evidence**  
`agent.py` (~318–320 write opt-out); `follow_up.py` (~353–356 skip conditions without opt-in check).

**Impact**  
Anti-spam / consent violation risk; users who opted out can be messaged again.

**Root cause**  
Opt-out flag is write-only in practice; scheduler and re-open logic ignore it.

**Fix plan**

1. In `check_and_send_followups`, skip (and mark stopped/completed) if `lead.whatsapp_opt_in is False`.
2. In `process_chat`, never force `active` when opted out (P0.4).
3. Never re-arm Day 0 when opted out.
4. Optional: early return polite “you’re unsubscribed” without restarting automation.
5. Regression: opt-out → `"hello"` → no follow-up row becomes active.

**Files:** `follow_up.py`, `agent.py`.

---

### P0.6 — Failed notifications alert forever

**Severity:** High  

**Problem**  
Escalation cron selects `NotificationLog.status == "failed"` older than 5 minutes, logs and `send_critical_alert`, but **never updates** the row. Every minute the same failures fire again.

**Evidence**  
`main.py` escalation job (~188–198).

**Impact**  
Alert fatigue; ops noise; real failures hard to see.

**Root cause**  
Missing terminal transition after handling.

**Fix plan**

1. After alerting, set `status = "failed_alerted"` (or `failed_exhausted`).
2. Optionally allow a single retry path before terminal status.
3. Metrics: count transitions to `failed_alerted`.

**Files:** `main.py`; document new status in `models.py` comment for `NotificationLog`.

---

### Phase 0 verification checklist

- [ ] `"I am a buyer in Baner"` does not close session  
- [ ] `"bye"` / `"goodbye"` still close  
- [ ] No agents → hot path does not WhatsApp lead phone  
- [ ] Missing agent phone does not crash  
- [ ] Fully qualified + later `"hi"` stays closed / follow-up completed  
- [ ] Opt-out + later message → no automated follow-up  
- [ ] Failed notification produces one ops alert, not infinite  

---

## 5. Phase 1 — Agent assignment (core product bug)

**Goal:** Correct, sticky-until-claimed assignment; notify only after assignee is committed; never page the customer.  
**Sprint:** B  
**Depends on:** P0.2–P0.3 ideally merged first (safe notify).

### Target behavior (product)

```text
if lead.conversion_status == "claimed":
    do not rematch; keep lead.assigned_agent
elif rematch allowed (status open):
    match_best_agent(...)
    if assignee changed:
        adjust workload counters
        set lead.assigned_agent
        audit log
    commit
if need hot notification:
    only after assignee commit
```

**Stickiness choice (locked):** rematch is allowed while `conversion_status == "open"`; **frozen after `claimed`**.

---

### P1.1 — Extract `ensure_lead_assignment`

**Severity:** High (architecture for other fixes)  

**Problem**  
Assignment logic is inline only at the bottom of `process_chat`. Handoff and other paths cannot reuse it without duplication.

**Fix plan**

1. Add something like:

   ```text
   ensure_lead_assignment(db, lead, client_id, query: str, *, force: bool = False) -> Optional[str]
   ```

2. Behavior:
   - If `conversion_status == "claimed"` and not `force`: return existing `assigned_agent`
   - Else call matcher (with P1.3 workload rules)
   - Set `lead.assigned_agent` when a non-null name is returned
   - Emit audit `EventLog` only when assignee **changes**
   - Commit or leave commit to caller consistently (prefer caller owns transaction)

3. Call from: main scoring path, handoff path, any future reassign API.

**Files:** `app/intelligence/agent_matcher.py` and/or small helper module; `agent.py`.

---

### P1.2 — Sticky after claim

**Severity:** High  

**Problem**  
Every full chat turn re-runs `match_best_agent` and can overwrite `assigned_agent` even after a human claimed the lead on the dashboard.

**Evidence**  
`agent.py` (~959–980) unconditional rematch when path is reached.

**Impact**  
Claimed ownership is unstable; CRM / ops “who owns this?” is wrong mid-conversation.

**Fix plan**

1. At start of assignment helper: if `lead.conversion_status == "claimed"`, return current assignee and skip matcher.
2. Document: only an explicit admin “reassign” API may pass `force=True`.
3. Tests: claim lead → further messages → assignee unchanged.

**Files:** `agent.py` / helper.

---

### P1.3 — Workload: rematch without infinite `active_leads` inflation

**Severity:** High  

**Problem**  
`match_best_agent` always does:

```text
best_agent.active_leads = (best_agent.active_leads or 0) + 1
db.commit()
```

Every message that rematches increments load—even if the **same** agent is re-selected. There is **no** decrement on close, claim, reassignment, or lost. Counters only grow → load balancing becomes meaningless and can push all traffic to under-penalized agents incorrectly over time.

**Evidence**  
`app/intelligence/agent_matcher.py` (~92–93).

**Impact**  
Wrong routing after a few days of traffic; “busy” agents stay busy forever in the model.

**Fix plan (preferred combination)**

1. **On match:**
   - If new assignee == previous: **do not** increment.
   - If new assignee != previous: increment new; decrement previous (floor at 0).
2. **Better long-term:** stop trusting mutable `active_leads` for scoring; compute:

   ```sql
   COUNT(*) FROM leads
   WHERE assigned_agent = :name
     AND client_id = :client_id
     AND conversion_status = 'open'
   ```

3. If keeping the column, recompute nightly or on claim/close.
4. Avoid `commit()` inside matcher if possible—return intended side effects to caller (easier testing).

**Files:** `agent_matcher.py`; claim/close paths if decrementing on claim.

---

### P1.4 — Order of operations: match → commit → notify

**Severity:** Critical  

**Problem**  
For `prob >= 82`, code schedules:

```text
asyncio.create_task(trigger_hot_lead_notification(...))
```

**before** `match_best_agent`. The notification task uses a new DB session and often reads `assigned_agent` still `NULL` on the first hot turn. Combined with P0.2, this can page the wrong party or manager-only.

**Evidence**  
`agent.py` (~941–965 order).

**Impact**  
First hot alert frequently has no real assignee; routing falls back to manager or worse.

**Fix plan**

1. Always: `ensure_lead_assignment` → `db.commit()` → then `create_task(notify)`.
2. Pass reason string correctly (P1.10).
3. Optionally pass `assigned_agent` into the notification function to avoid a race with concurrent writers (still re-read lead for other fields).

**Files:** `agent.py`, possibly `notification_service.py` signature.

---

### P1.5 — Human handoff never assigns

**Severity:** Critical  

**Problem**  
Handoff intercept (phrases like `"human"`, `"agent"`, `"call me"`):

1. Sets temperature hot, funnel `Human Handoff`
2. Closes session
3. Fires `trigger_hot_lead_notification`
4. Returns early

`match_best_agent` never runs. Assignee often null; notification relies on manager fallback (or P0.2 bug path).

**Evidence**  
`agent.py` (~456–482).

**Impact**  
The highest-intent “talk to a human” path is the *least* prepared for routing.

**Fix plan**

1. Before notify: `ensure_lead_assignment(...)` with history/query text.
2. Commit assignee + closed session + funnel stage together.
3. Then fire notification with reason `"Explicit human agent requested."`
4. Keep early return for LLM skip, but **not** without assignment attempt.

**Files:** `agent.py`.

---

### P1.6 — Speciality taxonomy mismatch

**Severity:** High  

**Problem**  
Classifier returns: `investor`, `tenant`, `luxury`, `buyer`.  
Agent / UI specialities often use: `luxury`, `mid_range`, `investment`, `rental`.

Comparisons like `lead_type == agent.speciality` fail for investor/investment and tenant/rental. The large speciality bonus almost never applies; routing ignores specialist skill.

**Evidence**  
`agent_matcher.py` (`classify_lead_type`, scoring ~67–70) vs agent seed / team settings UI.

**Impact**  
Investment and rental specialists under-matched; near-generic routing.

**Fix plan**

1. Introduce a single mapping table, e.g.:

   | Classifier | Agent speciality |
   |------------|------------------|
   | investor | investment |
   | tenant | rental |
   | luxury | luxury |
   | buyer | mid_range (or buyer if you add it) |

2. Compare using normalized values on both sides.
3. Align seed data and frontend dropdown to the same enum.
4. Add tests for each lead_type → preferred speciality wins when locations equal.

**Files:** `agent_matcher.py`, seed/`add_client` agents, frontend team settings if hardcoded.

---

### P1.7 — Location match too strict

**Severity:** Medium  

**Problem**  
Location scoring splits comma lists and requires **exact token equality** (`"wakad west"` ≠ `"wakad"`). Real user/CRM strings are messy.

**Fix plan**

1. Normalize: lower, strip, collapse spaces.
2. Score if either side contains the other as substring, or shared Pune-area alias.
3. Optionally reuse `PUNE_AREAS` aliases.
4. Keep a high bonus for strong match, smaller for partial.

**Files:** `agent_matcher.py`.

---

### P1.8 — Prefer live open-lead counts

**Severity:** Medium  

**Problem**  
Even with increment/decrement fixes, concurrent matches race on read-modify-write of `active_leads` without row locks.

**Fix plan**

1. Short term: `SELECT ... FOR UPDATE` on agent row when updating counters, or SQL `active_leads = active_leads + 1`.
2. Medium term: score using live COUNT of open leads (P1.3).
3. Document multi-worker behavior.

**Files:** `agent_matcher.py`.

---

### P1.9 — Fake default agent name in follow-ups

**Severity:** Medium  

**Problem**  
Follow-up path uses:

```text
lead.assigned_agent or "ABC Properties Team"
```

Day-0 copy can invent a brand/agent that does not exist for the tenant.

**Evidence**  
`follow_up.py` (~417); `followup_engine.py` appends agent sentence when provided.

**Fix plan**

1. Use `Client` company/display name if available.
2. Or omit the “X will assist you” sentence when unassigned.
3. Never hardcode a demo agency name in production paths.

**Files:** `follow_up.py`, `app/intelligence/followup_engine.py`.

---

### P1.10 — Wrong hot-notification reason for score-based fires

**Severity:** Medium  

**Problem**  
Score ≥ 82 uses reason `"Explicit human agent requested."` even when the user never asked for a human. Ops cannot distinguish handoff vs model score.

**Evidence**  
`agent.py` (~946–947) vs real handoff (~475–477).

**Fix plan**

1. Score path: `"Lead crossed HOT threshold (conversion_probability ≥ 82)"` (or include actual prob).
2. Handoff path: keep explicit human wording.
3. Optional: store reason on `NotificationLog` if schema allows later.

**Files:** `agent.py`.

---

### P1.11 — Acknowledge/claim does not bind assignee

**Severity:** High  

**Problem**  
`POST /api/v1/notifications/acknowledge`:

- Sets notification `acknowledged`
- Sets `conversion_status = "claimed"`
- Does **not** set `lead.assigned_agent` to the claiming human
- Any dashboard user can claim; ownership string may stay null or stale matcher result

After P1.2, claim freezes assignee—so if claim happens while still null, the lead can be **permanently unassigned**.

**Evidence**  
`main.py` (~535–557).

**Fix plan**

1. Extend acknowledge API with optional `agent_id` / `agent_name` (or map from authenticated user when real agent login exists).
2. On claim:
   - set `conversion_status = "claimed"`
   - if body provides agent (or current user maps to agent), set `assigned_agent`
   - if already assigned and no override, keep existing
3. Do not rematch after claim (P1.2).
4. Frontend claim button should send the acting agent identity when available.

**Files:** `main.py`, frontend `PriorityAlertCard` / `KanbanBoard` claim handlers.

---

### P1.12 — Frontend never shows assignee

**Severity:** Medium  

**Problem**  
API returns `assigned_agent`; types include it; Kanban/leads UI do not display it. Ops cannot see ownership.

**Fix plan**

1. Show assignee on Kanban cards, leads table, priority alert card.
2. Empty state: “Unassigned”.
3. Optional filter by assignee (real filter, not mock).

**Files:** frontend CRM/dashboard components; `api.ts` already typed.

---

### P1.13 — Mock sales-agent RBAC

**Severity:** Medium  

**Problem**  
Dashboard filters with hard-coded `"Jane Doe"` and `id % 2 == 0`, leaking half the leads and ignoring real assignee names.

**Evidence**  
`frontend/src/app/(dashboard)/dashboard/page.tsx` (~53–55).

**Fix plan**

1. Remove mock filter.
2. Until real agent auth exists, show all tenant leads for client login.
3. Later: filter `assigned_agent == currentAgent.name` from real identity.

**Files:** dashboard page only for removal; auth later.

---

### Phase 1 verification checklist

- [ ] Handoff: assignee non-null (when agents exist) before notify  
- [ ] First hot score turn: notification log shows real agent name, not only manager-by-accident  
- [ ] Rematch while open allowed; counters do not +1 on same agent every message  
- [ ] After claim: assignee frozen across messages  
- [ ] Claim can set assignee when provided  
- [ ] Speciality match: investment lead prefers investment specialist  
- [ ] UI shows assignee  
- [ ] No WhatsApp to customer when unassigned (P0)  

---

## 6. Phase 2 — Chat / follow-up state machine

**Goal:** Terminal states stay terminal; intercepts do not strand follow-ups; data quality for names/funnel; **strict English default with Hinglish only when the user initiates.**  
**Sprint:** C  
**Depends on:** Phase 0 (P0.1, P0.4, P0.5) as foundation.

---

### P2.1 — Early intercepts leave follow-up permanently stopped

**Severity:** High  

**Problem**  
Every turn sets `follow_up_status = "stopped"` early when not fully qualified. Re-arm to Day 0 **active** only runs at the end of the full LLM path. Instant reply, property-intent intercept, and guardrail returns exit **before** re-arm (and before ML / assignment).

**Evidence**  
`agent.py` early stop (~289–290); returns ~359, ~435, ~451; re-arm only ~1032+.

**Impact**  
After common openers (“hi”, “looking to buy…” without personal data path), automated Day 0 never schedules. Lead scores stay cold/default.

**Root cause**  
Split brain: “start of turn always stop” + “end of turn re-arm only on long path”.

**Fix plan**

1. Extract `finalize_turn(db, session, lead, f_state, ...)` that:
   - If opted out or fully qualified or session closed for handoff: complete/stop follow-up appropriately
   - Else: re-arm Day 0 with correct delay (test vs prod)
2. Call `finalize_turn` from:
   - end of main path
   - every intercept return (instant, intent, guardrail)
3. Do **not** re-arm on pure closing phrases if product wants silence after thanks (document choice).
4. Tests for “hi” from new lead → Day 0 scheduled.

**Files:** `agent.py`.

---

### P2.2 — Document and enforce terminal states

**Severity:** High (policy + code)  

**Problem**  
`closed` is overloaded: polite thanks, opt-out, full qualification, handoff, and accidental “buyer” all use the same flag. Reopen logic is ad hoc.

**Fix plan**

1. Document in this plan and in code comments:

   | Event | session.status | follow_up | whatsapp_opt_in | conversion_status |
   |-------|----------------|-----------|-----------------|-------------------|
   | Normal chat | active | stopped mid-turn, re-arm end | true | open |
   | Full qualify | closed | completed | true | open (until human claims) |
   | Opt-out | closed | stopped/completed | **false** | unchanged |
   | Handoff | closed | stopped | true | open until claim |
   | Claim on dashboard | unchanged chat | unchanged | unchanged | **claimed** |

2. Only an explicit “reopen conversation” admin action may set active after terminal qualify/opt-out/handoff.
3. Align product copy with this table.

**Files:** `agent.py`, `follow_up.py`, short note in README or this plan (source of truth).

---

### P2.3 — Concurrent name interceptor can commit garbage

**Severity:** High  

**Problem**  
For short messages (≤12 words) when name is empty, a parallel Gemini call extracts “a name” and commits immediately. No validation against property keywords, times, or affirmations. Can save `"2BHK"`, `"tomorrow"`, `"yes please"`, etc. Races with `extract_lead_info` (related to the qualification override fix already shipped).

**Evidence**  
`agent.py` (~635–680).

**Impact**  
Polluted CRM names; false full qualification; wrong personalization in follow-ups and closing templates.

**Fix plan**

1. Accept only if:
   - 1–3 tokens
   - mostly alphabetic
   - not in blocklist (bhk, budget, lakhs, tomorrow, okay, yes, areas list, etc.)
2. Prefer not committing until end-of-turn merge with tool args.
3. If tool also returns name, tool wins.
4. Log rejected extractions at debug.
5. Keep timeout so latency stays bounded.

**Files:** `agent.py`.

---

### P2.4 — Funnel stage enum diverges from frontend

**Severity:** Medium  

**Problem**  
Backend writes stages such as `"Human Handoff"`, `"Site Visit Done"`, `"Appointment Scheduled"`.  
Kanban primary columns: `New`, `Contacted`, `Appointment Scheduled`, `Closed Won`, `Lost`.  
Dashboard sometimes counts `"Qualified"` which backend never sets.

Handoff / site-visit leads land in **Other**; KPI “Qualified” stays 0.

**Fix plan**

1. Define a single shared enum (Python constants + TS const or OpenAPI).
2. Map handoff → e.g. `Contacted` or add a real Kanban column.
3. On full qualify keep `Appointment Scheduled` (already aligned).
4. Remove phantom `"Qualified"` or map backend to set it intentionally.
5. Update dashboard aggregations to real stages.

**Files:** `agent.py`, frontend `KanbanBoard.tsx`, dashboard KPI code, docs.

---

### P2.5 — `session.status` vs `conversion_status` product confusion

**Severity:** Medium  

**Problem**  
Fully qualified leads are “done” in chat but still `conversion_status=open`. Claim UI only looks at conversion. Ops language “open lead” is ambiguous.

**Fix plan**

1. Keep two FSMs (do not merge fields).
2. Document clearly in API docs.
3. Optional: on full qualification set funnel only; leave claim for humans.
4. Optional later: add `won`/`lost` to conversion FSM without overloading session close.
5. Frontend: show both “Chat: closed” and “Sales: open/claimed”.

**Files:** docs, light UI labels; avoid silent auto-claim on qualify unless product insists.

---

### P2.6 — English user gets Hinglish reply (language match failure)

**Severity:** High (user-facing product quality; very common first-message path)

**Intended product behavior (locked)**

| User message language | Required bot language |
|----------------------|------------------------|
| Standard English (including Indian place names / BHK / budget in Latin script) | **English only** |
| Clear Hindi/Hinglish words initiated by the user | **Hinglish** (Latin script; Devanagari only if user types Devanagari) |
| Mixed (English + one Hindi word) | Prefer treating as Hinglish **only if** Hindi/Hinglish keywords are present; otherwise English |
| Session so far English, user switches mid-chat to Hinglish | May switch to Hinglish from that turn |
| Session Hinglish, user switches back to pure English | Prefer return to English (match latest user turn) |

**Default is always English.** The bot must **never** open a conversation in Hinglish when the user’s message is pure English.

---

#### Observed production failure (WhatsApp)

| Role | Message |
|------|---------|
| User | `hi, need 2bhk in hinjewadi` |
| Bot | `Got it! Hinjewadi mein 2BHKs ke liye options hain. Aapka budget kya hai aur may I know your name?` |

User is pure English. Bot is mixed Hinglish (`mein`, `ke liye`, `Aapka`, `kya hai`) with a trailing English fragment. This violates intended behavior.

---

#### Why this is not a local-template bug

For `hi, need 2bhk in hinjewadi`:

1. `HAS_PERSONAL_DATA` is true because of `2bhk` and `hinjewadi` ∈ `PUNE_AREAS` (`agent.py` property-intent intercept skip logic).
2. Local English property-opener templates are **bypassed**.
3. Message goes to Gemini with `extract_lead_info`.
4. User-visible text is taken from tool arg `conversational_reply` (or `response.text`) and sent as-is.

So the failure is **LLM generation + lack of runtime language enforcement**, not the instant-reply / English intercept strings.

---

#### Root causes (ordered)

1. **Prompt-only policy, no hard gate**  
   `system_prompt.py` already says DEFAULT TO ENGLISH and “If the user types in standard English… MUST reply in natural English.” Nothing in `agent.py` detects user language or rewrites/rejects a Hinglish `final_text` when the user wrote English. Soft instructions are frequently ignored by flash-class models.

2. **Hinglish-heavy few-shots bias the model**  
   The same system prompt includes many Hinglish good/bad examples, objection templates, and tool `conversational_reply` Hinglish samples. For a “Pune real estate” persona, the model over-weights Hinglish even on English inputs.

3. **Domain prior (Indian location + BHK)**  
   Tokens like `hinjewadi` / `2bhk` push the model toward “Indian user → Hinglish” even when grammar is English.

4. **Tool schema does not encode language**  
   `conversational_reply` schema description is only “natural response… MUST NOT BE EMPTY” (`agent.py` FunctionDeclaration). No “must match user language / English if user English.”

5. **`is_hinglish()` is closing-template only**  
   Helper added for universal qualification override; **not** used to choose language for normal turns or to validate model output.

6. **No session language memory**  
   Even a correct “match this turn” rule is fragile without remembering that the user has been speaking English (or switched). Sticky session language with “user initiates switch” is the product rule.

---

#### Impact

- First impression on WhatsApp is wrong language for English-speaking buyers.
- Mixed EN/HI replies look unprofessional and harder to scan.
- Undermines the explicit language section already written into the system prompt.
- Cannot be fixed by prompt tweaks alone with reliable production guarantees.

---

#### Fix plan (layered defense)

**A. Detect user language (deterministic, cheap)**

1. Extend or pair `is_hinglish(text)` with a clear policy:
   - **Hinglish/Hindi initiated** if message contains known Hindi/Hinglish keywords (existing set: `kya`, `hai`, `mujhe`, `chahiye`, `mein`, `ka`, `ki`, …) or Devanagari script.
   - **English** otherwise (including pure English + place names / BHK / numbers).
2. Do **not** treat place names or `2bhk` as Hinglish signals.
3. Optionally store `session.preferred_language` or `lead.reply_language` ∈ `{english, hinglish}`:
   - Default `english`
   - Set to `hinglish` only when user message is classified Hinglish
   - Set back to `english` when user sends a pure-English turn (match latest user initiation)

**B. Inject a hard turn-level instruction into the model**

Before `chat.send_message`, append a short, high-priority directive, e.g.:

```text
LANGUAGE LOCK (MANDATORY):
User language this turn: ENGLISH.
You MUST reply in natural English only. Do NOT use Hinglish words
(mein, hain, aapka, kya, ke liye, etc.). conversational_reply must be English.
```

or for Hinglish users:

```text
LANGUAGE LOCK (MANDATORY):
User language this turn: HINGLISH.
Reply in natural Hinglish (Latin script). Keep RE nouns in English.
```

This is stronger than a buried system-prompt bullet because it is adjacent to the user turn.

**C. Tighten system prompt + schema (still keep A/B)**

1. Move Hinglish examples into a clearly labeled “ONLY when user already used Hinglish” section; reduce Hinglish few-shot density for the default path if possible.
2. Update `conversational_reply` schema description:
   - Must match user language.
   - English user → English only.
3. Reaffirm: never open in Hinglish on English openers.

**D. Runtime output guard (fail-closed for English users)**

After model/`conversational_reply` is chosen as `final_text` (and before save/send):

1. If user (or session) language is English **and** `is_hinglish(final_text)` is true:
   - Log `LANGUAGE_MISMATCH | session=... | user=en | reply=hinglish`
   - Prefer one of:
     - **(Preferred)** Replace with a safe English fallback built from known lead fields (location, property_type), e.g.  
       `Got it — {property_type} options in {location} are available. What's your approximate budget, and may I know your name?`
     - Or a single cheap rewrite call with a strict English-only instruction (cost/latency tradeoff)
2. Do **not** block Hinglish replies when user initiated Hinglish.
3. Apply the same guard to non-tool `response.text` paths.
4. Universal qualification override already branches on `is_hinglish(user_message)` — keep that aligned with the same detector (user language, not model language).

**E. Tests / regression**

| Input | Expected reply language |
|-------|-------------------------|
| `hi, need 2bhk in hinjewadi` | English (no `mein`/`aapka`/`ke liye`) |
| `I need a 2BHK in Baner` | English |
| `mujhe hinjewadi me 2bhk chahiye` | Hinglish allowed |
| `budget 60L hai` | Hinglish allowed |
| English then later `mujhe visit karna hai` | May switch to Hinglish |
| Hinglish then pure English follow-up | Prefer English again (match latest) |

**Files:** `agent.py` (detect, inject lock, output guard), `system_prompt.py` (policy + example hygiene), tool schema in `agent.py`, optional column on `Session`/`Lead` if sticky language is persisted, unit tests for detector + guard.

**Suggested PR:** Can ship as Sprint C PR after P2.1–P2.3, or earlier as a focused quality PR if product prioritizes WhatsApp first impressions (still after Phase 0 safety if possible).

---

### Phase 2 verification checklist

- [ ] Instant “hi” still allows Day 0 scheduling when appropriate  
- [ ] Guardrail intercept does not permanently kill follow-ups for active leads  
- [ ] Name interceptor rejects “2BHK” / “tomorrow”  
- [ ] Handoff / Appointment Scheduled appear correctly on Kanban  
- [ ] Qualified KPI matches real data  
- [ ] `hi, need 2bhk in hinjewadi` → **English** reply (no Hinglish connectors)  
- [ ] `mujhe 2bhk dekhna hai` → Hinglish reply allowed  
- [ ] English user never receives Hinglish-only `conversational_reply` after guard  

---

## 7. Phase 3 — WhatsApp / webhook concurrency

**Goal:** At-most-once processing per MessageSid; no double pipeline on timeout; SMS scoping correct.  
**Sprint:** D  

---

### P3.1 / P3.2 — Timeout cancels work, releases lock, full reprocess

**Severity:** Critical  

**Problem**  
WhatsApp webhook:

1. Acquires Redis `session_lock`
2. `wait_for(process_unified_lead, 15s)`
3. On timeout: schedules `background_process_and_push` with the **same body**, returns interim TwiML
4. Leaving `async with` **releases the lock**
5. Background runs **full** `process_unified_lead` again without lock

The cancelled first run may have already committed user messages, partial tool writes, CRM tasks, etc. Second run duplicates side effects. Concurrent second inbound messages can interleave.

**Evidence**  
`main.py` (~604–633 timeout path; ~353–375 background helper).

**Impact**

- Duplicate user/assistant rows  
- Double extraction / double CRM fire  
- Race corruption of lead fields  
- Extra LLM cost  

**Root cause**  
Timeout policy is “abandon and restart” instead of “continue same unit of work under a longer lease”.

**Fix plan (recommended)**

1. On timeout: do **not** cancel the in-flight coroutine if avoidable; move it to a background task that **owns** the lock/lease until completion.
2. If cancellation is required, mark a processing token so background **resumes** rather than full re-ingest (idempotent by MessageSid).
3. Background must re-acquire `session_lock:{session_id}` (or extend lock TTL for long jobs).
4. Return interim “Just checking…” only once per MessageSid.
5. Load / chaos test: artificial 20s sleep in process → one final user-visible reply, one user message row.

**Files:** `main.py` primarily.

---

### P3.3 — Dead `is_background` parameter

**Severity:** Medium (enables P3.1 fix)  

**Problem**  
`process_chat(..., is_background=False)` accepts the flag; callers pass it; body never reads it. Background retries cannot skip duplicate inserts.

**Fix plan**

1. When `is_background` (or better: idempotency key = MessageSid):
   - Skip inserting the same user message if already stored for that sid/body+timestamp window
   - Skip organic lead-created CRM double fire
2. Or remove the parameter and implement idempotency solely via WebhookLog / message keys— but then timeout design must not need it.

**Files:** `agent.py`, `main.py`.

---

### P3.4 — Webhook MessageSid check-then-insert race

**Severity:** High  

**Problem**  
Duplicate protection:

```text
existing = query MessageSid
if existing: return
insert WebhookLog
process
```

Two concurrent Twilio retries can both observe “missing” and both process. PK helps on insert, but lack of IntegrityError handling means one request can 500 while both may have started work depending on timing.

**Evidence**  
`main.py` (~590–598); `WebhookLog.message_sid` uniqueness.

**Fix plan**

1. Insert first.
2. On unique violation / IntegrityError: return empty TwiML (already processed).
3. Only the insert winner processes the message.
4. Test with concurrent posts of same MessageSid.

**Files:** `main.py`.

---

### P3.5 — SMS follow-up stop uses unscoped session id

**Severity:** High  

**Problem**  
Chat sessions are stored as `{client_id}_+91...`. SMS webhook looks up `FollowUpState` with raw `From` (`+91...`) → miss → follow-ups not stopped on that path.

**Evidence**  
`main.py` SMS handler (~695–703) vs scoped id in `process_unified_lead` (~429–430).

**Fix plan**

1. Always use `f"{client_id}_{normalized_from}"` for Session / FollowUpState / Lead lookups.
2. Share a `scope_session_id(client_id, raw)` helper.
3. Test SMS reply stops active follow-up.

**Files:** `main.py`, small util if useful.

---

### Phase 3 verification checklist

- [ ] Forced slow LLM → interim message + single final push; no double user row  
- [ ] Background holds lock  
- [ ] Parallel same MessageSid → single process  
- [ ] SMS stop follow-up works with tenant prefix  

---

## 8. Phase 4 — Notifications and escalation polish

**Goal:** Multi-tier escalation is real; failures terminate; reasons supersede sensibly.  
**Sprint:** E (with Phase 5 or after D)  

---

### P4.1 — 10m and 30m both page the same manager

**Severity:** High  

**Problem**  
Both escalations query `Agent.is_manager == True`. Log text says “Director” at 30m but code is identical. No second-line role.

**Evidence**  
`main.py` (~142 and ~171).

**Fix plan**

1. Add `is_director` or `role` enum on `Agent`.
2. 10m → manager; 30m → director (fallback manager only if no director, and log that).
3. Prefer different phone/email when possible.
4. Seed at least one director for demo tenants.

**Files:** `models.py` (migration), `main.py`, seed scripts, team UI.

---

### P4.2 — Idempotency blocks better handoff after score alert

**Severity:** Medium  

**Problem**  
If a score-based hot alert already created `pending_ack`, a later explicit handoff returns early (“already has active escalation”) and never updates reason or urgency.

**Evidence**  
`notification_service.py` (~75–82).

**Fix plan**

1. Severity ranking: handoff > score threshold.
2. If existing log and new reason is higher severity: update reason field (if added) or send a second “handoff upgrade” message once.
3. Do not create unbounded duplicate pending rows.

**Files:** `notification_service.py`, possibly schema for reason column.

---

### P4.3 — Follow-up Twilio failures retry every minute

**Severity:** Medium  

**Problem**  
On send failure, some paths raise to DLQ without advancing `next_follow_up_at`, so the scheduler retries every tick → spam risk during outages.

**Fix plan**

1. On dispatch failure: set `next_follow_up_at = now + backoff` (e.g. 15m, exponential cap).
2. Cap retries; then stop and DLQ permanently.
3. Day-7 path should use the same policy as other stages.

**Files:** `follow_up.py`.

---

## 9. Phase 5 — CRM and data quality

**Goal:** HubSpot (or CRM) reflects the lead after qualification, not only at empty create.  
**Sprint:** E  

---

### P5.1 — CRM sync only at create

**Severity:** High  

**Problem**  
Sync is fired when the lead row is first created—often with empty name/budget. A short poll waits for phone+name (~5s) then pushes whatever exists. Later `extract_lead_info` fills fields with **no** re-sync.

**Evidence**  
`crm_sync.py` poll/payload; create hooks in `agent.py` / `main.py`.

**Impact**  
CRM stuck at “Unknown” / empty budget forever.

**Fix plan**

1. Trigger re-sync on meaningful changes after tool commit (name, phone, budget, location, property_type, visit_date, assigned_agent).
2. Debounce (e.g. 2–5s) to batch multi-field turns.
3. Keep create-time sync for early phone-only if needed.
4. Track `crm_sync_status` transitions carefully.

**Files:** `crm_sync.py`, `agent.py` after lead field commits.

---

### P5.2 — Incomplete CRM property map

**Severity:** Medium  

**Problem**  
Payload roughly maps firstname, phone, budget, lifecyclestage—omits location, intent, property_type, visit_date, assignee.

**Fix plan**

1. Expand property map to match HubSpot custom properties (document required HubSpot setup).
2. Feature-flag properties that may not exist on all portals.
3. Log rejected properties without failing whole sync when appropriate.

**Files:** `crm_sync.py`, CRM docs.

---

### P5.3 — “Success” with empty identity

**Severity:** Medium  

**Problem**  
Sync can succeed with `firstname: Unknown` and empty phone after poll timeout.

**Fix plan**

1. If still missing phone (and optionally name) after poll: leave `crm_sync_status=pending`, do not mark success.
2. Retry on next field update (P5.1).

**Files:** `crm_sync.py`.

---

## 10. Phase 6 — Structural backlog

**Sprint:** F — important but not first-fire.

| ID | Item | Notes |
|----|------|--------|
| P6.1 | Persist feedback-loop success rates | Today in-process memory; multi-worker diverge |
| P6.2 | `Lead.assigned_agent` → FK to `agents.id` | Stops rename breakage; migration required |
| P6.3 | Min match score threshold | Avoid assigning totally unrelated first agent |
| P6.4 | AB follow-up stage timing vs strategy B day units | `follow_up.py` hour_map vs sequence days mismatch |
| P6.5 | Temperature badge casing | Backend `hot`/`warm` vs UI `Hot`/`Warm` |
| P6.6 | Atomic workload updates | Complements P1.3/P1.8 |

---

## 11. Sprint map

| Sprint | Phase | Theme | Primary outcome |
|--------|-------|--------|-----------------|
| **A** | 0 | Safety | No buyer-close, no SMS-to-lead, durable close/opt-out, failed-alert terminal |
| **B** | 1 | Assignment | Match before notify; sticky after claim; workload fix; handoff assigns |
| **C** | 2 | FSM / data / language | Intercept finalize; name quality; funnel alignment; **strict English default + Hinglish only when user initiates** |
| **D** | 3 | Concurrency | Timeout/idempotency/SMS scope fixed |
| **E** | 4–5 | Notif + CRM | Real escalation tiers; CRM re-sync |
| **F** | 6 | Structural | FK assignee, persisted learning, AB timing |

### Suggested PR slicing (Sprint A example)

1. PR-A1: P0.1 bye token fix  
2. PR-A2: P0.2 + P0.3 notification phone safety  
3. PR-A3: P0.4 + P0.5 terminal session + opt-out in scheduler  
4. PR-A4: P0.6 failed_alerted status  

Keep PRs small for safer rollback.

---

## 12. File ownership matrix

| Area | Primary files |
|------|----------------|
| Chat orchestration | `agent.py` |
| Language policy / prompt | `system_prompt.py`, `agent.py` (`is_hinglish`, turn lock, output guard) |
| Matcher / assignment | `app/intelligence/agent_matcher.py` |
| Follow-ups | `follow_up.py`, `app/intelligence/followup_engine.py` |
| Hot notify | `notification_service.py` |
| HTTP / webhooks / escalation cron | `main.py` |
| Models | `models.py` (+ Alembic migrations when needed) |
| CRM | `crm_sync.py` |
| Frontend claim / display | `frontend/src/app/(dashboard)/crm/*`, `dashboard/*` |
| Types | `frontend/src/lib/api.ts` |

---

## 13. Master regression checklist

Use after each sprint; full run before production.

### Safety (Phase 0)

1. Message containing `"buyer"` must **not** close session.  
2. Fully qualified lead + later `"hi"` stays closed; follow-up remains completed.  
3. Opt-out then `"hello"` must not re-arm follow-ups or clear opt-out.  
4. No `Agent` rows → hot notify must **not** Twilio `lead.phone`.  
5. Failed notification → single ops alert then terminal status.

### Assignment (Phase 1)

6. Handoff → `assigned_agent` set (when agents exist) before/with notify.  
7. First hot score turn → notification log agent is not blank solely due to race.  
8. Rematch while open allowed; same agent re-select does not inflate `active_leads`.  
9. After claim → rematch does not change assignee.  
10. UI shows assignee; mock Jane Doe filter removed.

### FSM / quality / language (Phase 2)

11. `"hi"` on new lead still schedules Day 0 when product expects it.  
12. Name interceptor does not save property keywords as names.  
13. Funnel stages appear on Kanban without dumping handoffs only into Other.  
14. Pure English opener (`hi, need 2bhk in hinjewadi`) → English reply only.  
15. User-initiated Hinglish (`mujhe … chahiye`) → Hinglish allowed.  
16. Output guard logs/fixes English→Hinglish mismatches; never blocks true Hinglish users.

### Concurrency (Phase 3)

17. WhatsApp forced timeout → one user message, one final assistant reply path, lock held for background.  
18. Parallel webhook same `MessageSid` → single process.  
19. SMS reply stops follow-ups with tenant-scoped session id.

### CRM / notif (Phase 4–5)

20. After name+budget extraction, CRM reflects updates (not only create-time Unknown).  
21. 30m escalation targets director role when configured.

---

## 14. Related recent fix (already shipped)

**Universal qualification override** (`agent.py`):

- Problem: concurrent name interceptor could fill the last field *before* tool-path snapshot `initial_was_fully_qualified`, so the closing template never fired.
- Fix: gate on `is_fully_qualified_now and session.status != "closed"`; re-read live lead fields; optional Hinglish template via `is_hinglish(user_message)`.
- Removed dead snapshots `was_fully_qualified_initial` / `initial_was_fully_qualified`.

This fix is necessary but **not sufficient**: P0.4 can still reopen closed sessions afterward. Phase 0 must make closed durable.

**Language note:** Closing-template Hinglish branching is correct only when **the user** is Hinglish. Mid-chat Hinglish drift on English openers is a separate bug — see **P2.6**. Do not use model reply language to decide the closing template; always use user (or session) language.

---

## 15. Severity legend

| Level | Meaning |
|-------|---------|
| **Critical** | Data loss, compliance risk, customer receives internal ops traffic, or core funnel broken for common phrases |
| **High** | Wrong routing, silent automation failure, double processing under realistic load |
| **Medium** | Wrong UX/metrics, weak matching, recoverable ops noise |
| **Low** | Edge polish, structural debt without immediate user harm |

---

## 16. Implementation notes for agents / developers

1. **Do not** start Phase 3 refactors before Phase 0 session/opt-out fixes—timeout races amplify bad state machines.  
2. **Do not** implement claim stickiness (P1.2) without claim-time assignee binding (P1.11), or you freeze `null` forever.  
3. Prefer small PRs with the regression bullets for that phase only.  
4. When adding statuses (`failed_alerted`, director flags), update `models.py` comments and any admin queries.  
5. Keep TEST_MODE behavior: no real Twilio; still assert that lead phone is never selected as destination in code paths (unit-level).  
6. **Language (P2.6):** Never treat place names / BHK / budget numerals as Hinglish signals. Strict English default; Hinglish only when the **user** initiates. Prompt changes alone are not enough—require turn-level lock and/or output guard.

---

## 17. Document history

| Date | Change |
|------|--------|
| 2026-07-09 | Initial full audit and phased plan from codebase review; stickiness = rematch until claimed |
| 2026-07-09 | Added **P2.6** language match failure from WhatsApp evidence; product policy = **strict English default, Hinglish only when user initiates**; updated scope, exec summary, sprint C, checklists |

---

*End of plan. Implementation should proceed sprint-by-sprint starting with Phase 0 unless product prioritizes assignment (Phase 1) immediately after P0.2/P0.3. Language quality (P2.6) may be pulled forward as a focused PR if WhatsApp first-message UX is prioritized, still preferably after Phase 0 safety.*
