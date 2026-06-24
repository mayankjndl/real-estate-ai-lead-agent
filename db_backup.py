import logging
import os
import subprocess
from datetime import datetime

from config import settings

logger = logging.getLogger("db_backup")
logging.basicConfig(level=logging.INFO)

def backup_postgres():
    """
    Executes a pg_dump against the configured DATABASE_URL and securely
    stores the backup artifact in the backups/ directory.
    """
    db_url = settings.DATABASE_URL
    if not db_url or not db_url.startswith("postgres"):
        logger.error("DATABASE_URL is not configured for PostgreSQL. Aborting backup.")
        return

    # Ensure backups directory exists
    backup_dir = os.path.join(os.getcwd(), "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")

    # Run pg_dump
    # Note: On Render or in Docker, the pg_dump binary must be available.
    try:
        logger.info(f"Starting PostgreSQL backup: {backup_file}")
        
        # We pass the db_url directly to pg_dump. 
        # Using subprocess.run with check=True to raise an error if it fails.
        process = subprocess.run(
            ["pg_dump", db_url, "-f", backup_file, "--no-owner", "--no-privileges", "--clean"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.error(f"Backup failed: {process.stderr}")
        else:
            logger.info(f"Backup completed successfully. Saved to {backup_file}")
            
    except Exception as e:
        logger.error(f"Failed to execute pg_dump: {e}")

if __name__ == "__main__":
    backup_postgres()
