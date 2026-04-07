import requests
import time

BASE = "http://127.0.0.1:8000/api/v1"

# Step 1: Send a chat message (this starts the timer)
print("--- Sending chat message ---")
r = requests.post(f"{BASE}/chat", params={
    "session_id": "followup-test-1",
    "message": "I want a 3BHK in Hinjewadi, budget 1.2 Cr",
    "client_id": "client_A"
})
data = r.json()
print(f"AI Reply: {data.get('reply', 'ERROR')[:120]}...")
print()
print("Now waiting ~75 seconds for the follow-up scheduler to detect this stale session...")
print("(Delay is set to 1 minute for testing)")
time.sleep(75)

# Step 2: Check conversation history for the auto follow-up
print()
print("--- Checking for auto follow-up messages in the database ---")
r2 = requests.post(f"{BASE}/chat", params={
    "session_id": "followup-test-1",
    "message": "Show me the conversation so far",
    "client_id": "client_A"
})
print(f"AI Reply after follow-up: {r2.json().get('reply', 'ERROR')[:200]}")
print()
print("SUCCESS: If the AI references a follow-up message it sent, the system is working!")
