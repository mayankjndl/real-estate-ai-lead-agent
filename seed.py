import secrets
from database import SessionLocal, engine
import models
from auth import get_password_hash

def seed_db():
    # Ensure tables are created
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if admin already exists to prevent duplicates
    existing_client = db.query(models.Client).filter_by(email="admin@revenueos.com").first()
    if existing_client:
        print(f"Client already exists!")
        print(f"Email: {existing_client.email}")
        print(f"API Key: {existing_client.api_key}")
        return

    # Generate credentials
    api_key = "secret-client-key-123"
    hashed_password = get_password_hash("password123")
    
    # Insert new SaaS Client
    new_client = models.Client(
        company_name="Revenue OS HQ",
        email="admin@revenueos.com",
        hashed_password=hashed_password,
        api_key=api_key
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    print("Database seeded successfully!")
    print(f"Email: {new_client.email}")
    print(f"Password: password123")
    print(f"API Key: {new_client.api_key}")
    
    db.close()

if __name__ == "__main__":
    seed_db()
