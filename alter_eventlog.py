import asyncio
from database import SessionLocal
from sqlalchemy import text

def alter_eventlog_table():
    db = SessionLocal()
    try:
        commands = [
            "ALTER TABLE event_logs ADD COLUMN IF NOT EXISTS action_type VARCHAR;",
            "ALTER TABLE event_logs ADD COLUMN IF NOT EXISTS latency_ms INTEGER;",
            "ALTER TABLE event_logs ADD COLUMN IF NOT EXISTS agent_type VARCHAR DEFAULT 'AI';"
        ]
        for cmd in commands:
            db.execute(text(cmd))
            print(f"Executed: {cmd}")
        db.commit()
        print("Successfully altered event_logs table.")
    except Exception as e:
        print(f"Error altering table: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    alter_eventlog_table()
