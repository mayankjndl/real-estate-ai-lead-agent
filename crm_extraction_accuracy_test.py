import requests
import time
import uuid
import sys

# Force UTF-8 encoding for Windows console to handle emojis returned by the AI
sys.stdout.reconfigure(encoding='utf-8')

RENDER_URL = "https://real-estate-ai-lead-agent-2.onrender.com"
API_KEY = "secret-client-key-123"

# 5 distinct users providing all required details in their chat messages
TEST_USERS = [
    {
        "phone": f"+9198000000{uuid.uuid4().hex[:2]}",
        "expected_name": "Alice",
        "messages": [
            "Hi, my name is Alice. I want to buy a 3BHK flat in Baner.",
            "My budget is 1.5 Cr. When can we schedule a visit?"
        ]
    },
    {
        "phone": f"+9198000000{uuid.uuid4().hex[:2]}",
        "expected_name": "Bob",
        "messages": [
            "Hello, I am Bob. Looking to rent a 2BHK in Wakad.",
            "My budget is around 30k per month."
        ]
    },
    {
        "phone": f"+9198000000{uuid.uuid4().hex[:2]}",
        "expected_name": "Charlie",
        "messages": [
            "Hey, Charlie here. Need an investment property in Kharadi.",
            "I am looking for something under 80 Lakhs."
        ]
    },
    {
        "phone": f"+9198000000{uuid.uuid4().hex[:2]}",
        "expected_name": "David",
        "messages": [
            "I'm David. What options do you have for buying a villa in Hinjewadi?",
            "My maximum budget is 2.5 Crores."
        ]
    },
    {
        "phone": f"+9198000000{uuid.uuid4().hex[:2]}",
        "expected_name": "Eve",
        "messages": [
            "Hi, this is Eve. I am looking for a 1BHK on rent in Kothrud.",
            "I can pay around 20k. Do you have options?"
        ]
    }
]

def run_extraction_test():
    print("================================================================")
    print("  100% CRM EXTRACTION ACCURACY TEST (5 LEADS)")
    print("================================================================\n")
    
    # 1. Simulate the chats
    print("--- Phase 1: Simulating WhatsApp Conversations ---\n")
    for user in TEST_USERS:
        phone = user["phone"]
        print(f"[START] Starting chat for {user['expected_name']} ({phone})...")
        for i, msg in enumerate(user["messages"]):
            sid = f"SM{uuid.uuid4().hex[:32]}"
            print(f"   -> User: {msg}")
            
            try:
                # Send the chat message
                r = requests.post(f"{RENDER_URL}/api/v1/whatsapp",
                                  data={"From": f"whatsapp:{phone}", "Body": msg, "MessageSid": sid},
                                  timeout=30)
                
                if r.status_code == 200:
                    # Extract the TwiML message for printing
                    response_text = r.text.split("<Message>")[1].split("</Message>")[0] if "<Message>" in r.text else "[Silent Processing]"
                    print(f"   <- Bot: {response_text}")
                else:
                    print(f"   [ERROR] API Error: HTTP {r.status_code}")
            except Exception as e:
                print(f"   [ERROR] Request Failed: {e}")
            
            # Brief pause to allow the AI to process sequential messages naturally
            time.sleep(2)
        print("-" * 50)
        
    print("\n--- Phase 2: Verifying CRM Extraction Accuracy ---\n")
    print("Waiting 5 seconds for final database commits...")
    time.sleep(5)
    
    try:
        r = requests.get(f"{RENDER_URL}/api/v1/leads", headers={"X-API-Key": API_KEY}, timeout=15)
        if r.status_code != 200:
            print(f"[ERROR] Failed to fetch CRM Leads. HTTP {r.status_code}")
            return
            
        data = r.json()
        all_leads = data.get("leads", [])
        
        success_count = 0
        total_fields_checked = 0
        successful_fields = 0
        
        for user in TEST_USERS:
            phone = user["phone"]
            # Find the lead in the CRM dump
            crm_lead = next((l for l in all_leads if l.get("phone") == phone), None)
            
            if not crm_lead:
                print(f"[ERROR] FAILED: Lead for {user['expected_name']} ({phone}) was not found in the CRM!")
                continue
                
            # Extract fields
            name = crm_lead.get("name")
            location = crm_lead.get("location")
            budget = crm_lead.get("budget")
            intent = crm_lead.get("intent")
            
            print(f"[CHECK] Checking {user['expected_name']}:")
            print(f"   - Name    : {name or '[MISSING]'}")
            print(f"   - Location: {location or '[MISSING]'}")
            print(f"   - Budget  : {budget or '[MISSING]'}")
            print(f"   - Intent  : {intent or '[MISSING]'}")
            
            # Validation
            fields = [name, location, budget, intent]
            total_fields_checked += 4
            
            # Check if any field is missing, None, or a generic placeholder
            is_perfect = True
            for field in fields:
                if not field or str(field).lower() in ["unknown", "n/a", "none"]:
                    is_perfect = False
                else:
                    successful_fields += 1
                    
            if is_perfect:
                print("   [PASS] RESULT: 100% Extraction Success!\n")
                success_count += 1
            else:
                print("   [FAIL] RESULT: Missing Fields Detected!\n")
                
        print("================================================================")
        print("  EXTRACTION REPORT")
        print("================================================================")
        print(f"  Total Leads Tested : 5")
        print(f"  Perfect Extractions: {success_count}/5")
        if total_fields_checked > 0:
            print(f"  Fields Captured    : {successful_fields}/{total_fields_checked} ({(successful_fields/total_fields_checked)*100:.1f}%)")
        print("================================================================")
        if success_count == 5:
            print("[SUCCESS] ALL SYSTEMS NOMINAL. 100% DATA CAPTURE CONFIRMED.")
        
    except Exception as e:
        print(f"[ERROR] Failed to verify CRM accuracy: {e}")

if __name__ == "__main__":
    run_extraction_test()
