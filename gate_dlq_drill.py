from database import SessionLocal
from models import DLQEvent


def trigger_dlq_failure():
    print("--- STARTING DISASTER RECOVERY DLQ DRILL ---")
    db = SessionLocal()

    print("1. Simulating HubSpot CRM API Crash...")
    fake_failure = DLQEvent(
        client_id=1,
        target_endpoint="hubspot_crm",
        payload={"properties": {"firstname": "Test User", "phone": "+919999900000"}},
        error_trace="HTTP 502 Bad Gateway - HubSpot API Down",
        status="pending"
    )
    db.add(fake_failure)
    db.commit()
    print("✅ CRM Failure securely caught and written to Dead Letter Queue.")

    count = db.query(DLQEvent).filter_by(status="pending").count()
    print(f"Pending DLQ Events: {count}")
    print("\nTo complete the drill, run: python dlq_replay.py")
    db.close()


trigger_dlq_failure()