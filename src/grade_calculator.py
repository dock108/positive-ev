import os
import sys
import time
import traceback
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import from new consolidated modules
try:
    # Try relative imports (when used as a module)
    from .config import (
        CALCULATOR_LOG_FILE, GRADE_BATCH_SIZE,
        setup_logging
    )
    from .common_utils import (
        safe_float, extract_date_from_timestamp,
        debug_print
    )
    from .supabase_client import (
        get_supabase_client, batch_upsert,
        get_filtered_bets_with_grades
    )
except ImportError:
    # Fall back to absolute imports (when run directly)
    from src.config import (
        CALCULATOR_LOG_FILE, GRADE_BATCH_SIZE,
        setup_logging
    )
    from src.common_utils import (
        safe_float, extract_date_from_timestamp,
        debug_print
    )
    from src.supabase_client import (
        get_supabase_client, batch_upsert,
        get_filtered_bets_with_grades
    )

# Initialize logger
logger = setup_logging(CALCULATOR_LOG_FILE, "grade_calculator")

# Flag to control full grading mode
# When False, skips games with past event times or start times more than 2 days prior
# When True, processes all games regardless of timing
FULL_MODE = False

def calculate_ev_score(ev_percent):
    """Calculate score based on Expected Value."""
    try:
        ev = safe_float(ev_percent)
        if ev is None:
            return 0
        normalized_ev = (ev + 10) * 5
        return max(0, min(100, normalized_ev))
    except Exception as e:
        logger.error(f"Error calculating EV score: {str(e)}")
        return 0

def calculate_timing_score(event_time, timestamp):
    """Calculate score based on time until event."""
    try:
        # Parse times
        if isinstance(event_time, str):
            try:
                # Try to parse ISO format
                event_dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
            except ValueError:
                # Try to parse with standard format
                event_dt = datetime.strptime(event_time, '%Y-%m-%d %H:%M:%S')
        else:
            event_dt = event_time
            
        if isinstance(timestamp, str):
            try:
                # Try to parse ISO format
                bet_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Try to parse with standard format
                bet_dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        else:
            bet_dt = timestamp
        
        # Calculate time difference in hours
        time_diff = (event_dt - bet_dt).total_seconds() / 3600
        
        if time_diff <= 0:
            return 0  # Event already started
        elif time_diff <= 1:
            return 100  # Less than 1 hour
        elif time_diff <= 3:
            return 90  # 1-3 hours
        elif time_diff <= 6:
            return 80  # 3-6 hours
        elif time_diff <= 12:
            return 70  # 6-12 hours
        elif time_diff <= 24:
            return 60  # 12-24 hours
        elif time_diff <= 48:
            return 50  # 24-48 hours
        elif time_diff <= 72:
            return 40  # 48-72 hours
        else:
            return 30  # More than 72 hours
    except Exception as e:
        logger.error(f"Error calculating timing score: {str(e)}")
        return 0

def calculate_kelly_score(win_probability, odds):
    """Calculate score based on Kelly Criterion."""
    try:
        win_prob = safe_float(win_probability)
        if win_prob is None:
            return 0
        
        win_prob = win_prob / 100  # Convert to decimal
        
        odds = float(odds)
        decimal_odds = None
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly formula: f* = (p * b - q) / b
        # where p = win probability, q = 1-p, b = decimal odds - 1
        b = decimal_odds - 1
        q = 1 - win_prob
        
        kelly = (win_prob * b - q) / b
        
        # Convert kelly to score (0-100)
        kelly_score = min(kelly * 500, 100)  # Cap at 100
        return max(0, kelly_score)  # Floor at 0
    except Exception as e:
        logger.error(f"Error calculating Kelly score: {str(e)}")
        return 0

def calculate_edge_score(win_probability, odds):
    """Calculate score based on edge over market implied probability."""
    try:
        win_prob = safe_float(win_probability)
        if win_prob is None:
            return 0
        
        odds = float(odds)
        market_implied_prob = None
        if odds > 0:
            market_implied_prob = 100 / (odds + 100) * 100
        else:
            market_implied_prob = abs(odds) / (abs(odds) + 100) * 100
        
        edge = win_prob - market_implied_prob
        normalized_edge = (edge + 10) * 5
        return max(0, min(100, normalized_edge))
    except Exception as e:
        logger.error(f"Error calculating edge score: {str(e)}")
        return 0

def assign_grade(composite_score):
    """Assign letter grade based on composite score."""
    if composite_score >= 90:
        return 'A'
    elif composite_score >= 80:
        return 'B'
    elif composite_score >= 70:
        return 'C'
    elif composite_score >= 60:
        return 'D'
    else:
        return 'F'

def calculate_grades():
    """Calculate grades for all ungraded bets in Supabase."""
    debug_print("Starting grade calculation...", logger)
    
    try:
        # Connect to Supabase - this is only used for get_all_records calls, not for batch_upsert
        debug_print("About to connect to Supabase...", logger)
        get_supabase_client()  # Just ensure the connection is valid
        debug_print("Supabase client created successfully", logger)
        
        # Step 1: Get filtered bets and their existing grades in a single optimized call
        debug_print("Fetching filtered betting data and grades from Supabase...", logger)
        all_bets, existing_grades = get_filtered_bets_with_grades(full_mode=FULL_MODE)
        
        if not all_bets:
            debug_print("No bets found in Supabase after filtering", logger)
            return
            
        debug_print(f"Total betting records retrieved after filtering: {len(all_bets)}", logger)
        debug_print(f"Total existing grade records retrieved: {len(existing_grades)}", logger)
        
        # Group bets by bet_id and keep only the newest record for each
        debug_print("Grouping bets by bet_id and identifying the newest records...", logger)
        
        # Dictionary to store the latest bet for each bet_id
        latest_bets_by_id = {}
        
        for bet in all_bets:
            bet_id = bet.get("bet_id")
            timestamp = bet.get("timestamp", "")
            
            if not bet_id or not timestamp:
                continue
            
            # If we haven't seen this bet_id yet, or if this timestamp is newer
            if bet_id not in latest_bets_by_id or timestamp > latest_bets_by_id[bet_id].get("timestamp", ""):
                latest_bets_by_id[bet_id] = bet
        
        debug_print(f"Found {len(latest_bets_by_id)} unique bet IDs", logger)
        
        # Determine which bets need grading (either new or need regrading)
        bets_to_grade = []
        new_bets = 0
        regraded_bets = 0
        
        for bet_id, bet in latest_bets_by_id.items():
            # Normal grading logic - the time filtering is now done at the database level
            if bet_id not in existing_grades:
                # New bet that has never been graded
                bets_to_grade.append(bet)
                new_bets += 1
            else:
                # Compare timestamps to see if this bet needs regrading
                existing_timestamp = existing_grades[bet_id].get("calculated_at", "")
                bet_timestamp = bet.get("timestamp", "")
                
                if bet_timestamp > existing_timestamp:
                    # This bet has newer data than when it was last graded
                    bets_to_grade.append(bet)
                    regraded_bets += 1
        
        debug_print(f"Found {len(bets_to_grade)} bets to grade (New: {new_bets}, Regrade: {regraded_bets})", logger)
        
        if not bets_to_grade:
            debug_print("No bets need grading or regrading", logger)
            return
            
        # Sort bets by timestamp for consistent processing
        debug_print("Sorting bets by timestamp...", logger)
        bets_to_grade.sort(key=lambda x: x.get("timestamp", ""))
        
        # Group bets by day for batch processing (instead of exact timestamp)
        bets_by_day = {}
        for bet in bets_to_grade:
            timestamp = bet.get("timestamp", "")
            day = extract_date_from_timestamp(timestamp)
            
            if day not in bets_by_day:
                bets_by_day[day] = []
            bets_by_day[day].append(bet)
        
        debug_print(f"Grouped {len(bets_to_grade)} bets to grade into {len(bets_by_day)} day groups", logger)
        
        # Process each day group
        total_bets_processed = 0
        total_grades_added = 0
        total_batches_uploaded = 0
        
        # Use a smaller chunk size to prevent API timeouts
        chunk_size = GRADE_BATCH_SIZE  # Now using the config value
        
        debug_print(f"Beginning to process day groups with chunk size {chunk_size}...", logger)
        
        for day_idx, (day, bets) in enumerate(bets_by_day.items()):
            debug_print(f"Processing day group {day_idx + 1}/{len(bets_by_day)}: {day} ({len(bets)} bets)", logger)
            
            # Collection for this batch
            batch_grade_records = []
            
            for bet_idx, bet in enumerate(bets):
                try:
                    total_bets_processed += 1
                    bet_id = bet["bet_id"]
                    timestamp = bet.get("timestamp", "")
                    
                    # Log progress for every bet with detailed counter
                    if bet_idx % 10 == 0:
                        debug_print(f"Processing bet {bet_idx + 1}/{len(bets)} for day {day} (Total: {total_bets_processed}/{len(bets_to_grade)})", logger)
                        # Force logs to flush
                        for handler in logger.handlers:
                            handler.flush()
                    
                    # Extract required fields for grade calculation
                    ev_percent = bet.get("ev_percent")
                    event_time = bet.get("event_time")
                    odds = bet.get("odds")
                    win_probability = bet.get("win_probability")
                    
                    # Skip bets with missing critical data
                    if not all([ev_percent, odds, win_probability, event_time]):
                        debug_print(f"Skipping bet {bet_id} due to missing data", logger)
                        continue
                    
                    # Calculate individual scores
                    ev_score = calculate_ev_score(ev_percent)
                    timing_score = calculate_timing_score(event_time, timestamp)
                    kelly_score = calculate_kelly_score(win_probability, odds)
                    edge_score = calculate_edge_score(win_probability, odds)
                    
                    # Calculate composite score with weights
                    composite_score = (
                        0.60 * ev_score +
                        0.30 * edge_score +
                        0.05 * timing_score +
                        0.05 * kelly_score
                    )
                    
                    # Create new grade record
                    grade_record = {
                        "bet_id": bet_id,
                        "grade": assign_grade(composite_score),
                        "calculated_at": datetime.utcnow().isoformat(),
                        "ev_score": ev_score,
                        "timing_score": timing_score,
                        "historical_edge": edge_score,
                        "composite_score": composite_score,
                        "similar_bets_count": 0  # Not using historical data yet
                    }
                    
                    # Add to batch collection
                    batch_grade_records.append(grade_record)
                    total_grades_added += 1
                    
                    # Upload smaller batches as we go to prevent memory issues and keep logs updating
                    if len(batch_grade_records) >= chunk_size:
                        upload_batch_to_supabase(batch_grade_records, f"{day}-batch-{total_batches_uploaded}", chunk_size)
                        total_batches_uploaded += 1
                        batch_grade_records = []  # Clear batch after upload
                        
                        # Small pause to prevent rate limiting
                        time.sleep(0.5)
                    
                except Exception as e:
                    debug_print(f"Error processing bet {bet.get('bet_id', 'unknown')}: {str(e)}", logger)
            
            # Upload any remaining records for this day
            if batch_grade_records:
                upload_batch_to_supabase(batch_grade_records, f"{day}-batch-{total_batches_uploaded}", chunk_size)
                total_batches_uploaded += 1
                batch_grade_records = []
        
        # Final summary
        debug_print(f"Completed grade calculation: {total_grades_added} grades added/updated in {total_batches_uploaded} batches", logger)
        debug_print(f"New grades: {new_bets}, Regraded: {regraded_bets}, Total processed: {total_bets_processed}", logger)
        
    except Exception as e:
        debug_print(f"ERROR running grade calculator: {str(e)}", logger)
        traceback.print_exc()
        sys.exit(1)

def upload_batch_to_supabase(records, batch_number, batch_size):
    """Helper function to upload a batch of records to Supabase with retries."""
    if not records:
        return
        
    debug_print(f"Uploading batch #{batch_number} with {len(records)} records", logger)
    
    try:
        # Use the batch_upsert function from supabase module
        batch_upsert("bet_grades", records, "bet_id", batch_size)
        debug_print(f"Successfully uploaded {len(records)} records in batch #{batch_number}", logger)
        
        # Force logs to flush
        for handler in logger.handlers:
            handler.flush()
    except Exception as e:
        debug_print(f"Failed to upload batch: {str(e)}", logger)
        # Try to upload smaller batches if the whole batch fails
        if len(records) > 10:
            debug_print("Attempting to upload in smaller chunks...", logger)
            mid = len(records) // 2
            # Split batch in half and try each half
            upload_batch_to_supabase(records[:mid], f"{batch_number}-A", batch_size)
            time.sleep(1)  # Pause between uploads
            upload_batch_to_supabase(records[mid:], f"{batch_number}-B", batch_size)
        else:
            # If batch is already small, log IDs of failed records
            for record in records:
                debug_print(f"Failed to upload record for bet_id: {record.get('bet_id', 'unknown')}", logger)

def main():
    """Main function to run grade calculations."""
    try:
        # Check for command-line argument to enable FULL_MODE
        global FULL_MODE
        if len(sys.argv) > 1 and sys.argv[1].lower() in ('--full', '-f'):
            FULL_MODE = True
            debug_print("FULL_MODE enabled: Will process all bets regardless of timing", logger)
        
        debug_print("Starting grade calculator job", logger)
        start_time = datetime.now()
        
        # Calculate grades for all ungraded bets
        calculate_grades()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        debug_print(f"Grade calculator job completed successfully in {duration:.2f} seconds", logger)
        
    except Exception as e:
        debug_print(f"ERROR running grade calculator: {str(e)}", logger)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    debug_print("Grade calculator script started", logger)
    main()
    debug_print("Grade calculator script finished", logger)
