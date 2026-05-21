from sqlalchemy import text
from database import engine

def alter_pg_db():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE leads ADD COLUMN funnel_stage VARCHAR DEFAULT 'New'"))
            print("Added funnel_stage")
        except Exception as e:
            print(f"Skipping funnel_stage: {e}")
            
        try:
            conn.execute(text("ALTER TABLE leads ADD COLUMN external_crm_id VARCHAR"))
            print("Added external_crm_id")
        except Exception as e:
            print(f"Skipping external_crm_id: {e}")
            
        try:
            conn.execute(text("ALTER TABLE leads ADD COLUMN crm_sync_status VARCHAR DEFAULT 'pending'"))
            print("Added crm_sync_status")
        except Exception as e:
            print(f"Skipping crm_sync_status: {e}")
            
        conn.commit()
    print("PostgreSQL DB altered successfully.")

if __name__ == "__main__":
    alter_pg_db()
