import secrets
import argparse
from database import SessionLocal
import models
from auth import get_password_hash


def create_client(company_name: str, email: str):
    """
    Dynamically seeds a new SaaS Client into the PostgreSQL database.
    Generates a secure 32-character API key for webhook testing.
    """
    db = SessionLocal()
    try:
        # Check if Client already exists to prevent duplicate key violations
        existing = db.query(models.Client).filter_by(email=email).first()
        if existing:
            print(f"[*] Client '{email}' already exists in the database!")
            print(f"    API Key: {existing.api_key}")
            return

        # Generate secure credentials
        api_key = secrets.token_hex(32)
        hashed_password = get_password_hash("password123")

        # Insert new Tenant
        new_client = models.Client(
            company_name=company_name,
            email=email,
            hashed_password=hashed_password,
            api_key=api_key
        )
        db.add(new_client)
        db.commit()
        db.refresh(new_client)

        print("================================================================")
        print("  SUCCESS: NEW SAAS CLIENT PROVISIONED")
        print("================================================================")
        print(f"  Client ID      : {new_client.id}")
        print(f"  Company Name   : {new_client.company_name}")
        print(f"  Email Address  : {new_client.email}")
        print(f"  Password       : password123")
        print(f"  API Key (Header): {new_client.api_key}")
        print("================================================================")
        print("  Copy this API Key and use it in your Twilio webhook URL:")
        print(f"  https://your-ngrok.app/api/v1/whatsapp?api_key={new_client.api_key}")
        print("================================================================")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dynamically add a new SaaS Client.")
    parser.add_argument("--name", default="Apex Properties (Client 2)", help="Name of the company")
    parser.add_argument("--email", default="client2@revenueos.com", help="Email of the company admin")
    args = parser.parse_args()

    create_client(args.name, args.email)