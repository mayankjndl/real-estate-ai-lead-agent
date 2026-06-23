from database import SessionLocal, engine
import models
from auth import get_password_hash


def seed_test_clients():
    print("=" * 50)
    print("  SEEDING DEVELOPMENT / TEST DATABASE")
    print("=" * 50)

    # Ensure tables are created
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # --- CLIENT 1: Primary Test / Admin Account ---
        client_1_email = "admin@revenueos.com"
        client_1 = db.query(models.Client).filter_by(email=client_1_email).first()
        if not client_1:
            client_1 = models.Client(
                company_name="Revenue OS HQ (Test Client A)",
                email=client_1_email,
                hashed_password=get_password_hash("password123"),
                api_key="secret-client-key-123"
            )
            db.add(client_1)
            print(f"✅ Created Client 1: {client_1_email}")
        else:
            print(f"[*] Client 1 already exists: {client_1_email}")

        # --- CLIENT 2: Secondary Test Account (For Isolation Drills) ---
        client_2_email = "client2@revenueos.com"
        client_2 = db.query(models.Client).filter_by(email=client_2_email).first()
        if not client_2:
            client_2 = models.Client(
                company_name="Apex Properties (Test Client B)",
                email=client_2_email,
                hashed_password=get_password_hash("password123"),
                api_key="secret-client-key-456"
            )
            db.add(client_2)
            print(f"✅ Created Client 2: {client_2_email}")
        else:
            print(f"[*] Client 2 already exists: {client_2_email}")

        db.commit()

        print("-" * 50)
        print("  DEVELOPMENT CREDENTIALS READY")
        print("-" * 50)
        print("  Client A (Main Dashboard & Test Script):")
        print("  Email   : admin@revenueos.com")
        print("  Password: password123")
        print("  API Key : secret-client-key-123")
        print("")
        print("  Client B (Isolation Drill Testing):")
        print("  Email   : client2@revenueos.com")
        print("  Password: password123")
        print("  API Key : secret-client-key-456")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_clients()