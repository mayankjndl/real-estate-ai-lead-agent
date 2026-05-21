import asyncio
import time
from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import Lead, FollowUpState

def run_demo():
    print("==============================================", flush=True)
    print("  FINAL CLIENT READINESS DEMO RUNNER", flush=True)
    print("==============================================\n", flush=True)
    
    client = TestClient(app)
    
    test_phone = "+19998887777"
    session_id = test_phone
    
    print("1. SIMULATING LEAD CREATION (/api/v1/ingest)", flush=True)
    print("   This triggers DB insertion, CRM Sync (Background), and Twilio Outbound.", flush=True)
    ingest_payload = {
        "session_id": session_id,
        "source": "website",
        "name": "Demo User",
        "phone": test_phone,
        "whatsapp_opt_in": True,
        "budget": "1.5 Cr",
        "location": "Bavdhan"
    }
    
    res = client.post("/api/v1/ingest", json=ingest_payload)
    print(f"   Response Status: {res.status_code}", flush=True)
    
    # Wait slightly to allow the background CRM task to run
    print("   Waiting 2 seconds for background CRM sync...", flush=True)
    time.sleep(2)
    
    print("\n2. VERIFYING CRM SYNC AND FUNNEL STATE IN DATABASE", flush=True)
    db = SessionLocal()
    lead = db.query(Lead).filter(Lead.session_id == session_id).first()
    if lead:
        print(f"   Lead Found: ID={lead.id}, Name={lead.name}", flush=True)
        print(f"   Funnel Stage: {lead.funnel_stage}", flush=True)
        print(f"   External CRM ID: {lead.external_crm_id}", flush=True)
        print(f"   CRM Sync Status: {lead.crm_sync_status}", flush=True)
    else:
        print("   [!] Lead not found in DB!", flush=True)
    
    # Check FollowUpState
    f_state = db.query(FollowUpState).filter(FollowUpState.session_id == session_id).first()
    if not f_state:
        # Create a mock followup state to simulate scheduler readiness
        f_state = FollowUpState(session_id=session_id, follow_up_status="active")
        db.add(f_state)
        db.commit()
    print(f"   Current FollowUp Status: {f_state.follow_up_status}", flush=True)

    print("\n3. FIRING MOCK INBOUND TWILIO WEBHOOK (/api/v1/incoming_sms)", flush=True)
    webhook_data = {
        "From": session_id,
        "Body": "Yes, I am looking for a 2BHK.",
        "MessageSid": f"SM_DEMO_{int(time.time())}"
    }
    
    res_webhook = client.post("/api/v1/incoming_sms", data=webhook_data)
    print(f"   Webhook Response Status: {res_webhook.status_code}", flush=True)
    print(f"   Webhook TwiML Reply: {res_webhook.text.strip()[:60]}...", flush=True)
    
    print("\n4. VERIFYING FOLLOW-UP STOPPAGE", flush=True)
    db.refresh(f_state)
    print(f"   Updated FollowUp Status: {f_state.follow_up_status}", flush=True)
    
    print("\n5. PIPELINE REPORT VERIFICATION (/api/v1/reports/pipeline)", flush=True)
    admin_headers = {"X-Admin-Token": "real-estate-super-secret-key"}
    res_pipeline = client.get("/api/v1/reports/pipeline", headers=admin_headers)
    print(f"   Pipeline Status: {res_pipeline.status_code}", flush=True)
    if res_pipeline.status_code == 200:
        print(f"   Pipeline Data: {res_pipeline.json()}", flush=True)
    
    db.close()
    print("\n==============================================", flush=True)
    print("  DEMO RUNNER COMPLETE", flush=True)
    print("==============================================", flush=True)

if __name__ == "__main__":
    run_demo()
