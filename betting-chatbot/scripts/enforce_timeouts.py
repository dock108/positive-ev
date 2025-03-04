#!/usr/bin/env python3
"""
Script to enforce timeouts for rule violations.
This script is intended to be run as a cron job.
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path

# Add the parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.config import DATABASE_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, "logs", "enforce_timeouts.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def enforce_timeouts():
    """
    Enforce timeouts for rule violations.
    This function clears expired timeouts.
    """
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get users with expired timeouts
        cursor = conn.execute(
            """
            SELECT user_id, timeout_until
            FROM timeout_tracker
            WHERE timeout_until < datetime('now')
            AND timeout_until IS NOT NULL
            """
        )
        
        expired_timeouts = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(expired_timeouts)} expired timeouts")
        
        # Clear expired timeouts
        if expired_timeouts:
            user_ids = [timeout['user_id'] for timeout in expired_timeouts]
            placeholders = ','.join(['?'] * len(user_ids))
            
            conn.execute(
                f"""
                UPDATE timeout_tracker
                SET timeout_until = NULL
                WHERE user_id IN ({placeholders})
                """,
                user_ids
            )
            
            conn.commit()
            logger.info(f"Cleared {len(expired_timeouts)} expired timeouts")
        
        # Close connection
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error enforcing timeouts: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting timeout enforcement...")
    success = enforce_timeouts()
    logger.info(f"Timeout enforcement {'completed successfully' if success else 'failed'}")
    sys.exit(0 if success else 1)
