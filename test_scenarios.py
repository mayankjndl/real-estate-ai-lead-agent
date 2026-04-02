import json
import requests
import uuid
import time
from config import settings

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-API-Key": settings.API_AUTH_KEY}

def test_chat():
    print("--- Testing Chat Endpoints ---")
    
    try:
        with open("conversation_starters.json", "r") as f:
            starters = json.load(f)
    except FileNotFoundError:
        print("Error: conversation_starters.json not found.")
        return False

    print(f"Loaded {len(starters)} conversation starters.")
    
    # We will simulate the first 3 random users rapidly testing the start sequence
    for i in range(min(3, len(starters))):
        session_id = str(uuid.uuid4())
        msg = starters[i]["starter"]
        print(f"\n[Scenario {i+1}] Starting Session: {session_id[:8]}...")
        print(f"User: {msg}")
        
        try:
            res = requests.post(f"{BASE_URL}/chat", params={"session_id": session_id, "message": msg})
            if res.status_code == 200:
                print(f"AI: {res.json().get('reply')}")
            else:
                print(f"Error: {res.status_code} - {res.text}")
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to API. Make sure 'uvicorn main:app --reload' is running on port 8000.")
            return False

        time.sleep(2) # Respect API rate limits
        
    print("\n--- Testing Multi-turn Context & Tool Calling ---")
    try:
        with open("real_estate_conversation_flows.json", "r") as f:
            flows = json.load(f)
    except FileNotFoundError:
        print("Error: real_estate_conversation_flows.json not found.")
        return False
        
    flow = flows[0]["conversation"]
    session_id = str(uuid.uuid4())
    print(f"\nStarting Deep Multi-turn Session: {session_id[:8]}...")
    
    for turn in flow:
        if turn["role"] == "user":
            msg = turn["message"]
            print(f"\nUser: {msg}")
            
            res = requests.post(f"{BASE_URL}/chat", params={"session_id": session_id, "message": msg})
            if res.status_code == 200:
                print(f"AI: {res.json().get('reply')}")
            else:
                print(f"Error: {res.status_code} - {res.text}")
            
            time.sleep(3) # Slow down for multi-turn Gemini API compliance

    return True

def test_secured_endpoints():
    print("\n\n--- Testing Secured Analytics & Leads Endpoints ---")
    
    # 1. Fetch Analytics Overview
    print("Fetching Analytics Dashboard...")
    res = requests.get(f"{BASE_URL}/analytics", headers=HEADERS)
    if res.status_code == 200:
        print("Analytics Dashboard Result:", json.dumps(res.json(), indent=2))
    else:
        print(f"Analytics Failed: {res.status_code} - {res.text}")
        
    print("-" * 30)
        
    # 2. Fetch Extracted Leads (demonstrating dynamic filtering logic)
    print("\nFetching High Quality 'Buy' Intent Leads Overview...")
    res = requests.get(f"{BASE_URL}/leads", headers=HEADERS, params={"intent": "buy"})
    if res.status_code == 200:
        data = res.json()
        print(f"Total Matches Found: {data.get('total_returned')}")
        print("Lead Details Extracted from DB:")
        for lead in data.get("leads", []):
            extracted_info = {
                "Phone": lead.get("phone"),
                "Budget": lead.get("budget"),
                "Location": lead.get("location"),
                "Intent": lead.get("intent")
            }
            print(f" - SessionID: {lead.get('session_id')[:8]}... | Data: {extracted_info}")
    else:
        print(f"Leads Endpoint Failed: {res.status_code} - {res.text}")

if __name__ == "__main__":
    print("Starting AI Real Estate Backend Test Suite...\n")
    success = test_chat()
    if success:
        time.sleep(1)
        test_secured_endpoints()
    print("\nTest Suite Completed.")
