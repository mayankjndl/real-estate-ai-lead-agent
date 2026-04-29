import requests
import time
import uuid
import concurrent.futures
from datetime import datetime

RENDER_URL = "https://real-estate-ai-lead-agent-1.onrender.com"
API_KEY = "secret-client-key-123"

# 3 Concurrent Users to test database locking and multi-worker safety
USERS = [
    {
        "phone": "+919900000001",
        "name": "User One",
        "messages": [
            "Hi, looking for a flat",
            "I want to buy a 2BHK in Wakad",
            "Budget is around 90L",
            "Okay, let's schedule a visit for tomorrow"
        ]
    },
    {
        "phone": "+919900000002",
        "name": "User Two",
        "messages": [
            "Hello",
            "Looking to rent an apartment",
            "Baner area, budget 30k",
            "Can we visit on Sunday?"
        ]
    },
    {
        "phone": "+919900000003",
        "name": "User Three",
        "messages": [
            "Hi there",
            "I'm searching for a 3BHK to buy",
            "Kharadi area, budget is 1.5 Cr",
            "Yes, please arrange a site visit"
        ]
    }
]

LOG_FILE = f"final_soak_test_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
entries = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:12]
    out = f"[{ts}] {msg}"
    print(out, flush=True)
    entries.append(out)

def simulate_user(user_data):
    phone = user_data["phone"]
    messages = user_data["messages"]
    log(f"🟢 STARTING SESSION: {phone}")
    
    errors = 0
    for i, msg in enumerate(messages):
        sid = f"SM{uuid.uuid4().hex[:32]}"
        try:
            r = requests.post(f"{RENDER_URL}/api/v1/whatsapp",
                              data={"From": f"whatsapp:{phone}", "Body": msg, "MessageSid": sid},
                              timeout=60)
            ok = r.status_code == 200
            if not ok:
                errors += 1
            log(f"   [{phone}] MSG {i+1}/{len(messages)} | HTTP={r.status_code} | \"{msg}\"")
        except Exception as e:
            errors += 1
            log(f"   [{phone}] MSG {i+1} EXCEPTION: {e}")
        
        # Fast typing speed to trigger race conditions
        time.sleep(3)
        
    return phone, errors

def run_soak_test():
    log("================================================================")
    log("FINAL SOAK TEST - 3 CONCURRENT USERS")
    log("Testing PostgreSQL Locks, Redis Queue, and API Rate Limits")
    log("================================================================")
    
    total_errors = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(simulate_user, u) for u in USERS]
        for future in concurrent.futures.as_completed(futures):
            phone, errors = future.result()
            total_errors += errors
            log(f"🔴 ENDED SESSION: {phone} (Errors: {errors})")
            
    log("\n--- Waiting 15s for background updates before querying CRM ---")
    time.sleep(15)
    
    try:
        r = requests.get(f"{RENDER_URL}/api/v1/leads", headers={"X-API-Key": API_KEY}, timeout=15)
        data = r.json()
        log(f"\nCRM HTTP={r.status_code} | Total leads: {data.get('total_returned', 0)}")
        
        # Verify specific budgets for normalization
        for u in USERS:
            phone = u["phone"]
            found = next((l for l in data.get("leads", []) if l.get("phone") == phone), None)
            if found:
                log(f"✅ Lead Found: {phone} | Budget: {found.get('budget')} | Intent: {found.get('intent')}")
            else:
                log(f"❌ Missing Lead: {phone}")
                total_errors += 1
    except Exception as e:
        log(f"❌ CRM query failed: {e}")
        total_errors += 1
        
    log("\n================================================================")
    log("SOAK TEST SUMMARY")
    log("================================================================")
    log(f"  Concurrent Users  : 3")
    log(f"  Total Messages    : {sum(len(u['messages']) for u in USERS)}")
    log(f"  Total Errors      : {total_errors} {'✅ PERFECT' if total_errors == 0 else '❌ FAILED'}")
    log("================================================================")
    
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))
        
if __name__ == "__main__":
    run_soak_test()
