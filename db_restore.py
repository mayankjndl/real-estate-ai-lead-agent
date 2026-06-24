import logging
import os
import subprocess
import sys

from config import settings

logger = logging.getLogger("db_restore")
logging.basicConfig(level=logging.INFO)

def restore_postgres(backup_file: str):
    """
    Safely restores a PostgreSQL database from a pg_dump .sql artifact.
    WARNING: This will overwrite data in the target database.
    """
    db_url = settings.DATABASE_URL
    if not db_url or not db_url.startswith("postgres"):
        logger.error("DATABASE_URL is not configured for PostgreSQL. Aborting restore.")
        sys.exit(1)

    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        sys.exit(1)

    try:
        logger.warning(f"Starting PostgreSQL restore from: {backup_file}")
        logger.warning(f"Target Database: {db_url.split('@')[-1]}")  # Hide credentials in log
        
        # We pass the db_url directly to psql since pg_dump output is usually raw SQL.
        # If it was custom format (-Fc), we would use pg_restore. Our backup uses raw SQL.
        process = subprocess.run(
            ["psql", db_url, "-f", backup_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.error(f"Restore failed: {process.stderr}")
        else:
            logger.info(f"Restore completed successfully from {backup_file}")
            
    except Exception as e:
        logger.error(f"Failed to execute psql for restore: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db_restore.py <path_to_backup_file.sql>")
        sys.exit(1)
        
    backup_file_path = sys.argv[1]
    restore_postgres(backup_file_path)
