"""
Initial Bet Details Rebuild Script
================================

This script rebuilds the initial_bet_details table from scratch by:
1. Dropping the existing table
2. Creating a new table with the correct schema
3. Processing all bet_ids from betting_data to get their initial states

Usage:
    python src/rebuild_initial_details.py

Author: highlyprofitable108
Created: March 2025
"""

import os
import sys
from datetime import datetime

# Add the project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from .config import setup_logging
    from .supabase_client import get_supabase_client
except ImportError:
    from src.config import setup_logging
    from src.supabase_client import get_supabase_client

# Initialize logger and supabase client
logger = setup_logging("rebuild_initial_details.log", "rebuild_initial_details")
supabase = get_supabase_client()

def recreate_table():
    """Drop and recreate the initial_bet_details table."""
    try:
        logger.info("Dropping initial_bet_details table...")
        # Using raw SQL to drop and recreate table
        supabase.table("initial_bet_details").delete().neq("bet_id", "dummy").execute()
        
        logger.info("Creating new initial_bet_details table...")
        # Note: Table creation is handled by Supabase migrations, 
        # we just need to clear the data
        
        logger.info("Table recreation complete")
    except Exception as e:
        logger.error(f"Error recreating table: {str(e)}")
        raise

def process_all_bets():
    """Process all bets from betting_data to get their initial states."""
    try:
        logger.info("Starting full initial bet details rebuild")
        
        # Step 1: Get all unique bet_ids from betting_data
        logger.info("Getting all unique bet_ids...")
        all_bet_ids = set()
        page_size = 1000
        last_timestamp = None
        page_count = 0
        
        while True:
            page_count += 1
            logger.info(f"Fetching page {page_count} (max {page_size} records per page)...")
            
            # Build query with timestamp-based pagination
            query = supabase.table("betting_data").select("bet_id,timestamp").order("timestamp")
            
            if last_timestamp:
                # Use timestamp for pagination (get records after the last timestamp)
                query = query.gt("timestamp", last_timestamp)
                
            query = query.limit(page_size)
            response = query.execute()
                
            current_batch = response.data
            if not current_batch:
                break
                
            # Add bet_ids from this page to our set
            bet_ids = [record.get('bet_id') for record in current_batch if record.get('bet_id')]
            all_bet_ids.update(bet_ids)
            
            # Update the timestamp for next page
            last_timestamp = current_batch[-1]["timestamp"]
            
            logger.info(f"Retrieved {len(current_batch)} records, total unique bet_ids so far: {len(all_bet_ids)}")
            
            if len(current_batch) < page_size:
                break
        
        logger.info(f"Found {len(all_bet_ids)} unique bet_ids in betting_data")
        
        if not all_bet_ids:
            logger.info("No bet_ids found to process")
            return
        
        # Helper function to clean numeric values
        def clean_numeric(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return value
            if isinstance(value, str):
                # Remove percentage signs and other non-numeric characters
                # except for decimal points and minus signs
                clean_value = value.replace('%', '')
                try:
                    return float(clean_value)
                except ValueError:
                    logger.warning(f"Could not convert value '{value}' to numeric, defaulting to None")
                    return None
            return None
        
        # Step 2: For each bet_id, get the earliest record
        initial_details_records = []
        total_processed = 0
        
        # Process in batches to avoid overwhelming the database
        batch_size = 100
        all_bet_ids_list = list(all_bet_ids)
        
        for i in range(0, len(all_bet_ids_list), batch_size):
            batch_bet_ids = all_bet_ids_list[i:i + batch_size]
            
            for bet_id in batch_bet_ids:
                # Get the earliest record for this bet_id
                response = supabase.table("betting_data") \
                    .select("bet_id, ev_percent, odds, bet_line, timestamp") \
                    .eq("bet_id", bet_id) \
                    .order("timestamp", desc=False) \
                    .limit(1) \
                    .execute()
                    
                if response.data:
                    earliest_record = response.data[0]
                    record = {
                        "bet_id": bet_id,
                        "initial_ev": clean_numeric(earliest_record.get('ev_percent')),
                        "initial_odds": earliest_record.get('odds'),  # Store odds as-is without conversion
                        "initial_line": earliest_record.get('bet_line'),  # Store as-is, no conversion
                        "first_seen": earliest_record.get('timestamp')
                    }
                    
                    # Debug log for odds values
                    if record["initial_odds"] is None:
                        logger.warning(f"Odds value is NULL for bet_id: {bet_id}, original value: {earliest_record.get('odds')}")
                    
                    initial_details_records.append(record)
            
            total_processed += len(batch_bet_ids)
            logger.info(f"Processed {total_processed}/{len(all_bet_ids)} bet_ids")
        
        logger.info(f"Prepared {len(initial_details_records)} initial details records")
        
        # Step 3: Upsert the records to handle both inserts and updates
        batch_size = 100
        total_upserted = 0
        
        for i in range(0, len(initial_details_records), batch_size):
            batch = initial_details_records[i:i + batch_size]
            
            try:
                # Use upsert with on_conflict parameter to handle duplicates
                supabase.table("initial_bet_details") \
                    .upsert(batch, on_conflict="bet_id") \
                    .execute()
                    
                total_upserted += len(batch)
                logger.info(f"Upserted {total_upserted}/{len(initial_details_records)} records")
            except Exception as e:
                logger.error(f"Error upserting batch {i//batch_size + 1}: {str(e)}")
                for j, record in enumerate(batch):
                    logger.error(f"Record {j}: {record}")
                raise
        
        logger.info(f"Rebuild complete. Upserted {total_upserted} initial bet details records.")
        
    except Exception as e:
        logger.error(f"Error during rebuild: {str(e)}")
        raise

def main():
    """Main function to rebuild initial bet details table."""
    try:
        start_time = datetime.now()
        logger.info("Starting initial bet details rebuild")
        
        # Step 1: Recreate table
        recreate_table()
        
        # Step 2: Process all bets
        process_all_bets()
        
        # Log completion
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Rebuild completed in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in rebuild script: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 