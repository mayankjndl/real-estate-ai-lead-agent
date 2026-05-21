import sqlite3
import os

DB_PATH = "real_estate_agent.db"

def alter_database():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} does not exist.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    columns_to_add = [
        ("funnel_stage", "VARCHAR DEFAULT 'New'"),
        ("external_crm_id", "VARCHAR"),
        ("crm_sync_status", "VARCHAR DEFAULT 'pending'")
    ]

    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_def}")
            print(f"Successfully added {col_name} to leads table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists. Skipping.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_database()
