import requests
import uuid
import time
import json

RENDER_URL = "https://real-estate-ai-lead-agent-3.onrender.com"
# RENDER_URL = "http://127.0.0.1:8000" # Use this if testing locally

def print_result(channel, response):
    print(f"\n[{channel}] Status Code: {response.status_code}")
    try:
        print(f"[{channel}] Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"[{channel}] Response: {response.text}")
    print("-" * 50)

def test_meta_webhook():
    print("Testing Facebook/Instagram Meta Webhook...")
    url = f"{RENDER_URL}/api/v1/webhook/meta"
    payload = {
        "lead_id": f"FB_{uuid.uuid4().hex[:8]}",
        "full_name": "Priya Sharma (FB Test)",
        "phone_number": "+918800000001",
        "opt_in": True  # Set to True to test outbound WhatsApp message
    }
    response = requests.post(url, json=payload)
    print_result("Meta Webhook", response)

def test_website_ingest():
    print("Testing Custom Website Forms (/api/v1/ingest)...")
    url = f"{RENDER_URL}/api/v1/ingest"
    payload = {
        "session_id": f"WEB_{uuid.uuid4().hex[:8]}",
        "source": "website",
        "name": "Amit Kumar (Web Test)",
        "phone": "+918800000002",
        "location": "Baner",
        "budget": "1.2 Cr",
        "intent": "Buy",
        "whatsapp_opt_in": False
    }
    response = requests.post(url, json=payload)
    print_result("Website Ingest", response)

def test_portals_webhook():
    print("Testing Portals (Magicbricks/99acres) Webhook...")
    url = f"{RENDER_URL}/api/v1/webhook/portals"
    payload = {
        "lead_id": f"PORTAL_{uuid.uuid4().hex[:8]}",
        "portal": "portal",
        "name": "Sneha Gupta (Portal Test)",
        "phone": "+918800000003",
        "intent": "Rent"
    }
    response = requests.post(url, json=payload)
    print_result("Portals Webhook", response)

if __name__ == "__main__":
    print("================================================================")
    print("  MULTI-CHANNEL INGESTION TESTER")
    print("================================================================")
    
    test_meta_webhook()
    time.sleep(1) # Small delay to ensure sequential logs
    
    test_website_ingest()
    time.sleep(1)
    
    test_portals_webhook()
    
    print("\n✅ All tests executed. Check your CRM Dashboard to verify they appear correctly with the correct badges!")
