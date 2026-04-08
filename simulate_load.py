import requests
import time
import threading
import uuid

API_URL = "http://127.0.0.1:8000/api/v1/whatsapp"
TEST_PHONE = "whatsapp:+919800000000"

def send_webhook(body, delay=0, msg_sid=None):
    if delay:
        time.sleep(delay)
    
    if not msg_sid:
        msg_sid = f"SM{uuid.uuid4().hex[:32]}"
        
    data = {
        "From": TEST_PHONE,
        "Body": body,
        "MessageSid": msg_sid
    }
    
    print(f"[>] Sending: '{body}' with SID {msg_sid[:8]}...")
    start = time.time()
    try:
        response = requests.post(API_URL, data=data, timeout=10)
        elapsed = time.time() - start
        print(f"[<] Response ({elapsed:.2f}s): {response.text}")
    except Exception as e:
        print(f"[X] Request failed: {e}")

print("=== STARTING LOAD SIMULATION ===")

# TEST 1: Message Queue Handling
print("\n--- Test 1: Message Queue (Spamming 3 messages instantly) ---")
threads = []
for msg in ["Msg 1 (Queue Test)", "Msg 2 (Queue Test)", "Msg 3 (Queue Test)"]:
    t = threading.Thread(target=send_webhook, args=(msg,))
    threads.append(t)
    t.start()
    
for t in threads:
    t.join()

# TEST 2: Duplicate Prevention
print("\n--- Test 2: Duplicate Prevention ---")
fixed_sid = f"SM{uuid.uuid4().hex[:32]}"
print("Sending Original...")
send_webhook("Original Message", msg_sid=fixed_sid)
print("Sending exact duplicate instantly...")
send_webhook("Duplicate Message", msg_sid=fixed_sid)

# TEST 3: Timeout Handling (Requires server to be slow artificially, but we can just test if the queue stays responsive)
print("\n--- Test 3: Standard Message (Checking Speed) ---")
send_webhook("Hi, what properties do you have?")

print("\n=== SIMULATION COMPLETE ===")
