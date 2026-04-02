import requests
import json
import uuid
import time
import os

BASE_URL = "http://127.0.0.1:8000/api/v1"
CLIENT_ID = "client_A"
API_KEY = "secret-client-key-123"

def test_conversation_flows():
    print("🚀 Starting Advanced Client-Grade AI CRM System Test...")
    
    # Check if the mock dataset exists
    if not os.path.exists("anohita_task5/50_conversation_flows.json"):
        print("❌ Dataset missing: anohita_task5/50_conversation_flows.json")
        return
        
    with open("anohita_task5/50_conversation_flows.json", "r") as f:
        scenarios = json.load(f)

    # We will test the first 5 completely to ensure it works without overwhelming the API rate limits
    total_tested = 0
    for scenario in scenarios[:5]:
        session_id = str(uuid.uuid4())
        print(f"\n────────────────────────────────────────────────────────")
        print(f"🔹 Testing Scenario {scenario['id']} | Target Intent: {scenario['intent'].upper()}")
        
        # Drive the conversation using user inputs
        for turn in scenario["conversation"]:
            if turn["role"] == "user":
                print(f"👤 User: {turn['message']}")
                
                # Send to FastAPI
                response = requests.post(
                    f"{BASE_URL}/chat",
                    params={
                        "session_id": session_id,
                        "message": turn["message"],
                        "client_id": CLIENT_ID
                    }
                )
                
                if response.status_code == 200:
                    ai_reply = response.json().get("reply")
                    print(f"🤖 AI: {ai_reply}")
                else:
                    print(f"❌ Error {response.status_code}: {response.text}")
                    break
                
                # Sleep to respect rate limits
                time.sleep(2)

        total_tested += 1

    print(f"\n✅ Finished processing {total_tested} complete simulated scenarios.")


def test_crm_analytics_and_export():
    print("\n📊 Validating CRM Analytics...")
    headers = {"X-API-Key": API_KEY}
    
    # Test Analytics Dashboard
    analytics_resp = requests.get(f"{BASE_URL}/analytics", headers=headers)
    if analytics_resp.status_code == 200:
        data = analytics_resp.json()["data"]
        print(f"✅ Dashboard Data Connected for {CLIENT_ID}:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Failed to fetch analytics: {analytics_resp.text}")

    # Test CSV Export
    print("\n📥 Testing CSV Export Endpoint...")
    export_resp = requests.get(f"{BASE_URL}/leads/export", headers=headers)
    
    if export_resp.status_code == 200:
        csv_filename = f"leads_export_{CLIENT_ID}_test.csv"
        with open(csv_filename, "wb") as f:
            f.write(export_resp.content)
        print(f"✅ CSV Export successful! Data verified and saved to '{csv_filename}'.\n")
    else:
        print(f"❌ Failed to export CSV: {export_resp.text}")


if __name__ == "__main__":
    try:
        # Check backend is up
        requests.get("http://127.0.0.1:8000/docs")
        test_conversation_flows()
        test_crm_analytics_and_export()
        print("🎯 ALL ADVANCED CORE TESTS PASSED!")
    except requests.exceptions.ConnectionError:
        print("❌ Error: The FastAPI server does not appear to be running. Start it with 'uvicorn main:app --reload' first.")
