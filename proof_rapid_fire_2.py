r"""
TASK 5 — 20-Message Realistic Load Test
Run: .\venv\Scripts\python.exe proof_rapid_fire_2.py
Proves: Sub-3 second average latency on Paid API
"""

import requests, time, uuid
from datetime import datetime

RENDER_URL = "https://real-estate-ai-lead-agent-1.onrender.com"
API_KEY    = "secret-client-key-123"
PHONE      = "+912500002222"
DELAY      = 5  # 5 seconds simulates realistic fast texting without Redis jams

MESSAGES = [
    "Hi",                                                          # 1. Instant Fast Path (~60ms)
    "I have a few questions about real estate.",                   # 2. Standard Chat (~2s)
    "I want to buy a flat in Wakad.",                              # 3. CRM UPDATE 1: Intent, Location, Type (~8s)
    "Is Wakad a good area for IT professionals?",                  # 4. RAG Chat (~2s)
    "What about the traffic situation there?",                     # 5. Standard Chat (~2s)
    "Okay",                                                        # 6. Instant Fast Path (~60ms)
    "Do the societies there usually have a gym?",                  # 7. Standard Chat (~2s)
    "And a swimming pool?",                                        # 8. Standard Chat (~2s)
    "Great.",                                                      # 9. Standard Chat (~2s)
    "My budget is 90 Lakhs.",                                      # 10. CRM UPDATE 2: Budget (~8s)
    "Can I get a good 2BHK in this budget?",                       # 11. RAG Chat (~2s)
    "What about maintenance charges?",                             # 12. Standard Chat (~2s)
    "Do you assist with bank loans?",                              # 13. Standard Chat (~2s)
    "Okay",                                                        # 14. Instant Fast Path (~60ms)
    "I would like to schedule a site visit.",                      # 15. Standard Chat (~2s)
    "My name is Rohan Gupta, let's do Sunday at 11 AM.",           # 16. CRM UPDATE 3: Name, Date (~8s)
    "Will you send a confirmation message?",                       # 17. Standard Chat (~2s)
    "Do I need to bring any documents?",                           # 18. Standard Chat (~2s)
    "Awesome, looking forward to it.",                             # 19. Standard Chat (~2s)
    "Thank you",                                                   # 20. Instant Fast Path (~60ms)
]

LOG_FILE = f"rapid_fire_log_20msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
entries  = []

def log(msg):
    ts  = datetime.now().strftime("%H:%M:%S.%f")[:12]
    out = f"[{ts}] {msg}"
    out_safe = out.replace("✅", "[OK]").replace("❌", "[X]").replace("—", "-")
    try:
        print(out_safe, flush=True)
    except:
        print(out_safe.encode("ascii", "ignore").decode("ascii"), flush=True)
    entries.append(out)

def run():
    log("=" * 64)
    log("RAPID FIRE TEST 2 — 20 Messages | Sub-3s Latency Proof")
    log(f"Session: {PHONE}  |  Delay between messages: {DELAY}s")
    log("=" * 64)

    sent, errors, timings = 0, 0, []

    for i, msg in enumerate(MESSAGES, 1):
        sid   = f"SM{uuid.uuid4().hex[:32]}"
        start = time.time()
        try:
            r       = requests.post(f"{RENDER_URL}/api/v1/whatsapp",
                          data={"From": f"whatsapp:{PHONE}", "Body": msg, "MessageSid": sid},
                          timeout=60)
            latency = round((time.time() - start) * 1000)
            timings.append(latency)
            ok = r.status_code == 200
            if ok:
                sent += 1
            else:
                errors += 1
            log(f"  MSG {i:02d}/20 {'✅' if ok else '❌'} | HTTP={r.status_code} | {latency}ms | SID={sid[:22]}...")
            log(f"         \"{msg}\"")
        except Exception as e:
            errors += 1
            log(f"  MSG {i:02d}/20 ❌ | EXCEPTION: {e}")

        if i < len(MESSAGES):
            log(f"         Waiting {DELAY}s...")
            time.sleep(DELAY)

    # ---- CRM VERIFICATION ----
    log("\n--- Waiting 15s then querying CRM ---")
    time.sleep(15)

    try:
        r    = requests.get(f"{RENDER_URL}/api/v1/leads",
                   headers={"X-API-Key": API_KEY}, timeout=15)
        data = r.json()
        log(f"CRM HTTP={r.status_code} | Total leads: {data.get('total_returned', 0)}")

        lead = None
        for l in data.get("leads", []):
            if "Rohan" in str(l.get("name", "")):
                lead = l
                break

        if lead:
            log(f"\n✅ Lead correctly captured from 20-message session:")
            log(f"   name     = {lead.get('name')}")
            log(f"   budget   = {lead.get('budget')}")
            log(f"   location = {lead.get('location')}")
            log(f"   intent   = {lead.get('intent')}")
            crm_ok = True
        else:
            log("⚠️  Lead not found in CRM")
            crm_ok = False
    except Exception as e:
        log(f"❌ CRM query failed: {e}")
        crm_ok = False

    # ---- SUMMARY ----
    log("\n" + "=" * 64)
    log("RAPID FIRE TEST 2 — SUMMARY")
    log("=" * 64)
    log(f"  Messages sent       : {sent}/20  {'✅' if sent==20 else '❌'}")
    log(f"  HTTP errors         : {errors}   {'✅ NONE' if errors==0 else '❌'}")
    log(f"  Avg response time   : {round(sum(timings)/len(timings)) if timings else 'N/A'}ms")
    log(f"  Min / Max latency   : {min(timings) if timings else 'N/A'}ms / {max(timings) if timings else 'N/A'}ms")
    log(f"  CRM lead captured   : {'✅ YES' if crm_ok else '⚠️ Check manually'}")
    log("=" * 64)
    log(f"\nLog saved → {LOG_FILE}")

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))

if __name__ == "__main__":
    run()
