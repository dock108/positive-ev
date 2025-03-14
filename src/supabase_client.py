import time
import sys
import os
import json
from typing import List, Dict, Any
from supabase import create_client, Client
from datetime import datetime, timedelta

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    # Try relative imports (when used as a module)
    from .config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_LOG_FILE, setup_logging
except ImportError:
    # Fall back to absolute imports (when run directly)
    from src.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_LOG_FILE, setup_logging

# Initialize logger
logger = setup_logging(SUPABASE_LOG_FILE, "supabase")

def get_supabase_client() -> Client:
    """
    Create and return a Supabase client instance.
    
    Returns:
        Client: A Supabase client instance.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and key must be set in environment variables")
    
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client created successfully")
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        raise

def get_all_records(table: str, select="*", filter_col=None, filter_val=None):
    """Get all records from a table with pagination."""
    all_records = []
    page_size = 1000  # Maximum records per request
    has_more = True
    start = 0
    
    logger.info(f"Fetching all records from table {table} with pagination...")
    
    # Connect to Supabase
    supabase_client = get_supabase_client()
    
    while has_more:
        query = supabase_client.table(table).select(select)
        
        # Apply filter if provided
        if filter_col and filter_val:
            query = query.eq(filter_col, filter_val)
        
        # Apply pagination
        query = query.range(start, start + page_size - 1)
        
        try:
            result = query.execute()
            records = result.data
            logger.info(f"Retrieved {len(records)} records from {table} (offset {start})")
            
            if records:
                all_records.extend(records)
                
                # If we got a full page, there might be more records
                if len(records) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
                
        except Exception as e:
            logger.error(f"Error fetching records from {table}: {e}")
            import traceback
            traceback.print_exc()
            break
    
    logger.info(f"Total records fetched from {table}: {len(all_records)}")
    return all_records

def batch_upsert(table: str, records: List[Dict[str, Any]], on_conflict="betid_timestamp", batch_size=100):
    """
    Upsert records in batches to avoid API limitations.
    
    Args:
        table: Table name
        records: List of record dictionaries
        on_conflict: Column to use for conflict resolution
        batch_size: Number of records per batch
        
    Returns:
        int: Number of successful batches
    """
    if not records:
        logger.info("No records to upsert")
        return 0
        
    # Connect to Supabase
    supabase_client = get_supabase_client()
    
    logger.info(f"Upserting {len(records)} records to {table} in batches of {batch_size}")
    
    # Process data in batches
    successful_batches = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            supabase_client.table(table).upsert(
                batch,
                on_conflict=on_conflict
            ).execute()
            successful_batches += 1
            logger.info(f"Successfully upserted batch {successful_batches} ({len(batch)} records)")
            # Small pause to prevent rate limiting
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error upserting batch to Supabase: {e}")
            
            # Attempt individual upserts on failure
            for record in batch:
                try:
                    supabase_client.table(table).upsert(
                        [record],
                        on_conflict=on_conflict
                    ).execute()
                    logger.info("Successfully upserted individual record")
                except Exception as e_inner:
                    logger.error(f"Error upserting individual record: {e_inner}")
    
    logger.info(f"Completed upserting {len(records)} records in {successful_batches} batches")
    return successful_batches

def get_filtered_bets(full_mode=False):
    """
    Get filtered betting data records from the database.
    
    When full_mode is False (default), only returns:
    - Bets with event_time in the future
    - Bets with event_time not more than 2 days in the past
    
    Args:
        full_mode: If True, returns all bets regardless of timing
        
    Returns:
        List of betting records that match the filter criteria
    """
    logger.info(f"Getting filtered betting data (full_mode={full_mode})")
    
    supabase_client = get_supabase_client()
    
    if full_mode:
        # If in full mode, get all records (still using pagination)
        logger.info("Running in FULL mode - retrieving all betting records")
        return get_all_records("betting_data")
    
    # ===== DEBUGGING EVENT TIME FORMAT FIRST =====
    # Get a small sample of records to analyze how event_time is stored
    logger.info("DEBUGGING: Fetching a small sample of records to analyze event_time format")
    try:
        sample_query = supabase_client.table("betting_data").select("event_time, timestamp").limit(5)
        sample_result = sample_query.execute()
        sample_records = sample_result.data
        
        logger.info(f"DEBUGGING: Sample records: {json.dumps(sample_records, indent=2)}")
        
        # Analyze each record's event_time
        for i, record in enumerate(sample_records):
            event_time = record.get("event_time", "")
            timestamp = record.get("timestamp", "")
            logger.info(f"DEBUGGING: Record {i+1} - event_time: '{event_time}' (type: {type(event_time).__name__})")
            logger.info(f"DEBUGGING: Record {i+1} - timestamp: '{timestamp}' (type: {type(timestamp).__name__})")
            
            # Try to parse it
            if event_time and isinstance(event_time, str):
                try:
                    parsed_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    logger.info(f"DEBUGGING: Successfully parsed event_time as: {parsed_time}")
                except ValueError as e:
                    logger.info(f"DEBUGGING: Failed to parse event_time: {e}")
    except Exception as e:
        logger.error(f"DEBUGGING: Error analyzing sample records: {e}")
    
    # ===== TESTING FILTERING APPROACHES =====
    logger.info("DEBUGGING: Testing different filtering approaches")
    
    # Get current time
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=2)
    
    # Format for database comparison
    now_str = now.isoformat()
    cutoff_str = cutoff_date.isoformat()
    
    logger.info(f"DEBUGGING: Current time (UTC): {now_str}")
    logger.info(f"DEBUGGING: Cutoff date (2 days ago): {cutoff_str}")
    
    # Test query 1: Filter for events in the future using gte with now
    try:
        logger.info(f"DEBUGGING: Test query 1 - future events only")
        test_query1 = supabase_client.table("betting_data").select("count").gte("event_time", now_str)
        test_result1 = test_query1.execute()
        count1 = len(test_result1.data)
        logger.info(f"DEBUGGING: Future events count (event_time >= '{now_str}'): {count1}")
        logger.info(f"DEBUGGING: Query 1 URL: {test_query1._url}")
        logger.info(f"DEBUGGING: Query 1 params: {test_query1._params}")
    except Exception as e:
        logger.error(f"DEBUGGING: Test query 1 error: {e}")
    
    # Test query 2: Filter for events not older than 2 days ago
    try:
        logger.info(f"DEBUGGING: Test query 2 - events not older than 2 days")
        test_query2 = supabase_client.table("betting_data").select("count").gte("event_time", cutoff_str)
        test_result2 = test_query2.execute()
        count2 = len(test_result2.data)
        logger.info(f"DEBUGGING: Recent events count (event_time >= '{cutoff_str}'): {count2}")
        logger.info(f"DEBUGGING: Query 2 URL: {test_query2._url}")
        logger.info(f"DEBUGGING: Query 2 params: {test_query2._params}")
    except Exception as e:
        logger.error(f"DEBUGGING: Test query 2 error: {e}")
    
    # Test query 3: Filter on timestamp instead of event_time
    # Get recent records based on when they were added, not when the event occurs
    recent_date = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        logger.info(f"DEBUGGING: Test query 3 - recent additions using timestamp")
        test_query3 = supabase_client.table("betting_data").select("count").gte("timestamp", recent_date)
        test_result3 = test_query3.execute()
        count3 = len(test_result3.data)
        logger.info(f"DEBUGGING: Recent additions count (timestamp >= '{recent_date}'): {count3}")
        logger.info(f"DEBUGGING: Query 3 URL: {test_query3._url}")
        logger.info(f"DEBUGGING: Query 3 params: {test_query3._params}")
    except Exception as e:
        logger.error(f"DEBUGGING: Test query 3 error: {e}")
    
    # ===== USE THE MOST RELIABLE APPROACH BASED ON DEBUGGING =====
    # For now, we'll fetch records by timestamp as a fallback
    logger.info(f"DEBUGGING: Using timestamp-based filtering as the reliable approach")
    seven_days_ago = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    
    all_records = []
    page_size = 1000
    has_more = True
    start = 0
    
    logger.info(f"Fetching records with timestamp >= {seven_days_ago}")
    
    while has_more:
        try:
            query = supabase_client.table("betting_data").select("*")
            query = query.gte("timestamp", seven_days_ago)
            query = query.range(start, start + page_size - 1)
            
            logger.info("DEBUGGING: Query URL: {}".format(query._url))
            logger.info("DEBUGGING: Query params: {}".format(query._params))
            
            result = query.execute()
            records = result.data
            
            if records:
                logger.info(f"Retrieved {len(records)} records (offset {start})")
                all_records.extend(records)
                
                if len(records) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
                
        except Exception as e:
            logger.error(f"Error fetching records: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Filter the records in Python
    logger.info(f"Filtering {len(all_records)} records based on event time")
    filtered_records = []
    filtered_out_count = 0
    
    for record in all_records:
        event_time = record.get("event_time", "")
        if not event_time:
            continue
            
        try:
            # Parse the event time
            if isinstance(event_time, str):
                event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
            else:
                event_dt = event_time
                
            # Debug the event time
            logger.debug(f"DEBUGGING: Record {record.get('bet_id', 'unknown')} - event_time: {event_time} parsed as {event_dt}")
            logger.debug(f"DEBUGGING: Comparing with cutoff {cutoff_date} - Is future/recent? {event_dt >= cutoff_date}")
                
            # Keep records with event times in the future or not older than 2 days
            if event_dt >= cutoff_date:
                filtered_records.append(record)
            else:
                filtered_out_count += 1
                if filtered_out_count <= 5:  # Log just a few examples
                    logger.info(f"DEBUGGING: Filtered out bet_id={record.get('bet_id', 'unknown')} with event_time={event_time} (parsed as {event_dt})")
        except (ValueError, TypeError) as e:
            logger.info(f"DEBUGGING: Could not parse event_time '{event_time}' for bet_id={record.get('bet_id', 'unknown')}: {e}")
            # If we can't parse the date, include the record to be safe
            filtered_records.append(record)
    
    logger.info(f"Total records: {len(all_records)}, Filtered records: {len(filtered_records)}, Excluded: {filtered_out_count}")
    return filtered_records

def get_filtered_bets_with_grades(full_mode=False):
    """
    Get filtered betting data records and necessary grades in a single function.
    This optimizes data fetching by only getting recent records.
    
    Args:
        full_mode: If True, returns all bets regardless of timing
        
    Returns:
        Tuple containing (filtered_bets, existing_grades_dict)
    """
    logger.info(f"Getting filtered betting data with grades (full_mode={full_mode})")
    
    supabase_client = get_supabase_client()
    
    # Get current time for filtering
    now = datetime.utcnow()
    logger.info(f"Current UTC time: {now.isoformat()}")
    
    # STEP 1: Get recent betting data
    if full_mode:
        # In full mode, get all betting data (using pagination)
        logger.info("Running in FULL mode - retrieving all betting records")
        all_bets = get_all_records("betting_data")
    else:
        # Calculate cutoff dates for database filtering
        # We'll use the database to do most of the filtering
        two_days_ago = now - timedelta(days=2)
        two_days_ago_str = two_days_ago.strftime("%Y-%m-%d")
        
        logger.info(f"Using database filtering for events not older than {two_days_ago_str}")
        logger.info(f"Cutoff datetime: {two_days_ago.isoformat()}")
        
        # Get only records with event_time >= two_days_ago OR timestamp within last 7 days
        all_bets = []
        page_size = 1000
        has_more = True
        start = 0
        
        while has_more:
            try:
                # Build a query that filters directly in the database
                # This is much more efficient than fetching everything and filtering in Python
                query = supabase_client.table("betting_data").select("*")
                
                # Filter for events that haven't happened yet or happened recently
                # We use the ISO format string for consistent comparison
                query = query.gte("event_time", two_days_ago_str)
                
                # Apply pagination
                query = query.range(start, start + page_size - 1)
                
                # Execute the query
                result = query.execute()
                records = result.data
                
                if records:
                    logger.info(f"Retrieved {len(records)} betting records (offset {start})")
                    logger.info(f"Sample record timestamps:")
                    for i, record in enumerate(records[:5]):  # Log first 5 records
                        logger.info(f"  Record {i+1}: event_time={record.get('event_time')}, timestamp={record.get('timestamp')}")
                    all_bets.extend(records)
                    
                    if len(records) == page_size:
                        start += page_size
                    else:
                        has_more = False
                else:
                    has_more = False
                    
            except Exception as e:
                logger.error(f"Error fetching betting records: {e}")
                import traceback
                traceback.print_exc()
                break
    
    logger.info(f"Total betting records after database filtering: {len(all_bets)}")
    
    # Get unique bet IDs from filtered bets
    bet_ids = set()
    timestamps_by_id = {}  # New dict to track timestamps
    for bet in all_bets:
        bet_id = bet.get("bet_id")
        timestamp = bet.get("timestamp")
        if bet_id:
            bet_ids.add(bet_id)
            if bet_id not in timestamps_by_id or timestamp > timestamps_by_id[bet_id]:
                timestamps_by_id[bet_id] = timestamp
    
    logger.info(f"Found {len(bet_ids)} unique bet IDs to check for existing grades")
    logger.info("Sample of bet IDs and their latest timestamps:")
    sample_ids = list(bet_ids)[:5]  # Take first 5 bet IDs
    for bet_id in sample_ids:
        logger.info(f"  {bet_id}: {timestamps_by_id[bet_id]}")
    
    # STEP 2: Only get grades for the bet IDs we need to check
    # Instead of fetching all grades, we'll use an "in" filter to just get what we need
    existing_grades = {}
    
    # Check if we have any bet IDs to look up
    if bet_ids:
        # Supabase can handle up to 100 items in an "in" filter, so we'll batch
        batch_size = 100
        bet_id_batches = [list(bet_ids)[i:i + batch_size] for i in range(0, len(bet_ids), batch_size)]
        
        logger.info(f"Fetching existing grades in {len(bet_id_batches)} batches of up to {batch_size} bet IDs")
        
        for batch_idx, bet_id_batch in enumerate(bet_id_batches):
            try:
                logger.info(f"Fetching grades batch {batch_idx + 1}/{len(bet_id_batches)} ({len(bet_id_batch)} bet IDs)")
                
                query = supabase_client.table("bet_grades").select("*")
                query = query.in_("bet_id", bet_id_batch)
                result = query.execute()
                
                for record in result.data:
                    bet_id = record.get("bet_id")
                    if bet_id:
                        existing_grades[bet_id] = record
                        logger.info(f"Found existing grade for {bet_id}: calculated_at={record.get('calculated_at')}")
                
                logger.info(f"Retrieved {len(result.data)} grade records in batch {batch_idx + 1}")
                
            except Exception as e:
                logger.error(f"Error fetching grades for batch {batch_idx + 1}: {e}")
                
    logger.info(f"Total existing grades found: {len(existing_grades)}")
    
    # Log some sample comparisons
    logger.info("Sample timestamp comparisons for first 5 bets:")
    for bet_id in sample_ids:
        bet_timestamp = timestamps_by_id.get(bet_id)
        grade_timestamp = existing_grades.get(bet_id, {}).get('calculated_at')
        logger.info(f"  Bet {bet_id}:")
        logger.info(f"    Latest bet timestamp: {bet_timestamp}")
        logger.info(f"    Grade calculated_at:  {grade_timestamp}")
    
    return all_bets, existing_grades

def get_existing_grades():
    """
    Get all existing bet grades from the database.
    
    Returns:
        Dictionary of graded records with bet_id as the key
    """
    logger.info("Fetching existing bet grades")
    
    existing_grades = {}
    graded_records = get_all_records("bet_grades", select="*")
    
    for record in graded_records:
        bet_id = record.get("bet_id")
        if bet_id:
            existing_grades[bet_id] = record
    
    logger.info(f"Found {len(existing_grades)} existing graded bet IDs")
    return existing_grades 