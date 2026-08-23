#!/usr/bin/env python
"""IREIOS — WhatsApp → SSE live smoke (G5/QA gate).

Proves the full local production path end-to-end:

    Twilio POST /api/v1/whatsapp
        -> WhatsAppAgent (qualify + score + LLM reply)
        -> _emit_turn_events -> Redis Streams
        -> CEO agents -> SSE bridge -> browser stream

Requirements:
    - docker compose up -d  (pg, redis, neo4j, n8n)
    - uvicorn running with TEST_MODE=true (skips Twilio signature + outbound sends)
    - python seed.py ran (client keys exist)

Exit code: 0 on PASS, 1 on FAIL. Stdlib only (urllib) — no venv deps.

Usage:
    python wa_sse_smoke.py [--base-url http://localhost:8000]
                           [--api-key secret-client-key-123]
                           [--from whatsapp:+919000000001]
                           [--to whatsapp:+14155238886]
                           [--body "Hi, I want a 2BHK in Andheri under 1 crore"]
                           [--max-sse-ms 3000]
                           [--listen-secs 20]
"""

import argparse
import json
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

# Required on every run (fire for both new and existing leads).
EXPECTED_EVENTS = ["whatsapp.received", "conversation.updated", "lead.scored"]
# Required only with --new-lead (lead.created fires only on lead creation).
NEW_LEAD_EVENTS = ["lead.created"]


def http_get_text(url: str, headers: dict | None = None, timeout: int = 5) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def sse_listener(url: str, api_key: str, stop: threading.Event, out: list, timeout: int = 30) -> None:
    """Background thread: read the tenant SSE stream, capture envelopes + receipt ts."""
    stream_url = f"{url}/api/v1/events/stream?api_key={urllib.parse.quote(api_key)}"
    req = urllib.request.Request(stream_url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                out.append({"error": f"SSE non-200: {resp.status}"})
                return
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data: "):
                    continue
                receipt_ts = time.time()
                try:
                    env = json.loads(line[6:])
                except ValueError:
                    continue
                env["_receipt_ts"] = receipt_ts
                out.append(env)
                if stop.is_set():
                    return
    except Exception as exc:  # noqa: BLE001 - listener must never crash the smoke
        out.append({"error": f"SSE listener: {exc}"})


def main() -> int:
    ap = argparse.ArgumentParser(description="WhatsApp -> SSE live smoke")
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--api-key", default="secret-client-key-123")
    ap.add_argument("--from", dest="from_num", default="whatsapp:+919000000001")
    ap.add_argument("--to", default="whatsapp:+14155238886")
    ap.add_argument("--body", default="Hi, I want a 2BHK in Andheri under 1 crore")
    ap.add_argument("--max-sse-ms", type=int, default=3000,
                    help="max tolerated publish->SSE delivery delay (ms)")
    ap.add_argument("--listen-secs", type=float, default=20.0)
    ap.add_argument("--new-lead", action="store_true",
                    help="use a unique From number so a new lead is created (lead.created required)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    expected = list(EXPECTED_EVENTS)
    from_num = args.from_num
    if args.new_lead:
        expected += NEW_LEAD_EVENTS
        from_num = f"whatsapp:+91{int(time.time()) % 10**10:010d}"

    # 1. Health
    code, body = http_get_text(f"{base}/health")
    if code != 200 or "healthy" not in body:
        print(f"FAIL: /health returned {code} — is uvicorn up? ({body[:200]})")
        return 1

    # 2. SSE listener
    stop = threading.Event()
    events: list = []
    t = threading.Thread(target=sse_listener, args=(base, args.api_key, stop, events), daemon=True)
    t.start()
    time.sleep(1.5)
    if events and events[0].get("error"):
        print(f"FAIL: SSE stream unavailable — {events[0]['error']}")
        return 1

    # 3. WhatsApp webhook POST
    form = urllib.parse.urlencode({
        "MessageSid": f"SMf4smoke{int(time.time())}",
        "From": from_num,
        "To": args.to,
        "Body": args.body,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/api/v1/whatsapp",
        data=form,
        headers={
            "X-API-Key": args.api_key,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    turn_start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            twiml = resp.read().decode("utf-8", "replace")
            turn_ms = (time.time() - turn_start) * 1000
    except urllib.error.HTTPError as exc:
        turn_ms = (time.time() - turn_start) * 1000
        err = exc.read().decode("utf-8", "replace")
        print(f"FAIL: webhook HTTP {exc.code} ({turn_ms:.0f}ms) — {err[:300]}")
        if exc.code == 403:
            print("Hint: 403 = Twilio signature rejected. Requires TEST_MODE=true in .env + uvicorn restart.")
        return 1

    print(f"Webhook turn: {turn_ms:.0f}ms (13s window) | TwiML: {twiml[:160]}")

    # 4. Collect SSE until expected events seen (or timeout)
    deadline = time.time() + args.listen_secs
    seen = {name: None for name in expected}
    latencies = {}
    while time.time() < deadline and not all(v is not None for v in seen.values()):
        for env in events:
            etype = env.get("event_type")
            if etype in seen and seen[etype] is None:
                seen[etype] = env
                try:
                    published = datetime.fromisoformat(env["timestamp"]).timestamp()
                    latencies[etype] = (env["_receipt_ts"] - published) * 1000
                except (KeyError, ValueError):
                    latencies[etype] = None
        time.sleep(0.2)
    stop.set()

    # 5. Report
    received = [e.get("event_type") for e in events if e.get("event_type")]
    print(f"SSE received ({len(received)}): {', '.join(received) or '(none)'}")
    for name in expected:
        env = seen[name]
        if env is None:
            print(f"  MISSING: {name}")
        else:
            lag = latencies.get(name)
            lag_s = f"{lag:.0f}ms" if lag is not None else "n/a"
            print(f"  OK: {name}  (publish->SSE {lag_s})")

    missing = [n for n in expected if seen[n] is None]
    late = [n for n, v in latencies.items() if v is not None and v > args.max_sse_ms]
    if missing or late:
        print(f"FAIL: missing={missing} late_gt_{args.max_sse_ms}ms={late}")
        if missing == NEW_LEAD_EVENTS and not args.new_lead:
            print("Hint: lead.created only fires for NEW leads; re-run with --new-lead to verify the create path.")
        return 1
    print("PASS: WhatsApp -> SSE full loop live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
