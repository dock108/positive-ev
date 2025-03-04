#!/usr/bin/env python3
"""
Script to refresh betting data from the Positive EV database.
This script is intended to be run as a cron job.
"""

import os
import sys
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

# Add the parent directory to sys.path
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.config import POSITIVE_EV_DB_PATH, DATABASE_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(parent_dir, "logs", "refresh_data.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def refresh_data():
    """
    Refresh betting data from the Positive EV database.
    """
    try:
        # Ensure database directory exists
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        
        # Check if Positive EV database exists
        if not os.path.exists(POSITIVE_EV_DB_PATH):
            logger.error(f"Positive EV database not found at {POSITIVE_EV_DB_PATH}")
            return False
        
        # Connect to databases
        source_db = sqlite3.connect(POSITIVE_EV_DB_PATH)
        source_db.row_factory = sqlite3.Row
        
        target_db = sqlite3.connect(DATABASE_PATH)
        target_db.row_factory = sqlite3.Row
        
        # Get recent positive EV bets
        logger.info("Fetching recent positive EV bets...")
        cursor = source_db.execute(
            """
            SELECT 
                bet_id, 
                event_teams as game, 
                description as bet_description, 
                sportsbook, 
                odds, 
                ev_percent, 
                win_probability,
                sport,
                league,
                event_time,
                timestamp
            FROM betting_data
            WHERE ev_percent > 0
            AND event_time > datetime('now')
            ORDER BY ev_percent DESC
            LIMIT 1000
            """
        )
        
        bets = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(bets)} bets to import")
        
        # Clear old data
        target_db.execute("DELETE FROM positive_ev_bets WHERE event_time < datetime('now')")
        
        # Insert new data
        for bet in bets:
            target_db.execute(
                """
                INSERT OR REPLACE INTO positive_ev_bets 
                (bet_id, game, bet_description, sportsbook, odds, ev_percent, win_probability, 
                 sport, league, event_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bet['bet_id'], bet['game'], bet['bet_description'], bet['sportsbook'],
                    bet['odds'], bet['ev_percent'], bet['win_probability'], bet['sport'],
                    bet['league'], bet['event_time'], bet['timestamp']
                )
            )
        
        target_db.commit()
        logger.info(f"Successfully imported {len(bets)} bets")
        
        # Close connections
        source_db.close()
        target_db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting data refresh...")
    success = refresh_data()
    logger.info(f"Data refresh {'completed successfully' if success else 'failed'}")
    sys.exit(0 if success else 1)
