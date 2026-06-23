import secrets
import argparse
import string
import re
from database import SessionLocal
import models
from auth import get_password_hash


def generate_email(company_name: str) -> str:
    """Strips spaces and special characters to generate a default admin email."""
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
    return f"admin@{clean_name}.com"


def create_client(company_name: str = None, email: str = None):
    """
    Interactive CLI tool to provision a real SaaS Client in production.
    """
    # 1. Interactive Prompts if arguments are missing
    print("\n" + "=" * 50)
    print("  REVENUE OS - CLIENT PROVISIONING TOOL")
    print("=" * 50)

    if not company_name:
        company_name = input("Enter Company Name: ").strip()
        if not company_name:
            print("Error: Company name cannot be empty.")
            return

    if not email:
        suggested_email = generate_email(company_name)
        email_input = input(f"Enter Admin Email [{suggested_email}]: ").strip()
        email = email_input if email_input else suggested_email

    # 2. Generate secure 12-character random password and 32-byte API Key
    alphabet = string.ascii_letters + string.digits
    raw_password = ''.join(secrets.choice(alphabet) for i in range(12))
    hashed_password = get_password_hash(raw_password)
    api_key = secrets.token_hex(32)

    # 3. Database Insertion
    db = SessionLocal()
    try:
        # Check for duplicates
        existing = db.query(models.Client).filter_by(email=email).first()
        if existing:
            print(f"\n❌ FAILED: Client '{email}' already exists!")
            print(f"Existing API Key: {existing.api_key}")
            return

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

        print("\n✅ SUCCESS: SAAS WORKSPACE PROVISIONED")
        print("-" * 50)
        print(f"  Client ID      : {new_client.id}")
        print(f"  Company Name   : {new_client.company_name}")
        print(f"  Login Email    : {new_client.email}")
        print(f"  Login Password : {raw_password}    <-- SHARE SECURELY ONCE")
        print(f"  Twilio API Key : {new_client.api_key}")
        print("-" * 50)
        print("  Twilio Webhook URL Setup:")
        print(f"  https://<your-domain>/api/v1/whatsapp?api_key={new_client.api_key}")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\n❌ DATABASE ERROR: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Provision a new SaaS Client Workspace.")
    parser.add_argument("--name", help="Name of the company")
    parser.add_argument("--email", help="Email of the company admin")
    args = parser.parse_args()

    create_client(args.name, args.email)