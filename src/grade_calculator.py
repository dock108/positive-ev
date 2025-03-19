"""
Grade Calculator Module
=====================

This module calculates grades for betting opportunities based on multiple factors
including expected value, timing, and market edge.

Key Features:
    - Multi-factor grade calculation (EV, timing, edge)
    - Batch processing of bets
    - CSV export functionality
    - Supabase integration for data storage
    - Configurable date range processing

Grade Calculation Weights:
    - Expected Value (EV): 55%
    - Market Edge: 30%
    - Timing Score: 15%

Grade Scale:
    A: >= 90
    B: >= 80
    C: >= 70
    D: >= 65
    F: < 65

Dependencies:
    - pandas: For data manipulation and CSV export
    - supabase-py: For database operations
    - python-dotenv: For environment variables

Usage:
    # Process last 24 hours
    python src/grade_calculator.py

    # Process specific date range
    python src/grade_calculator.py --start-date 2024-03-01 --end-date 2024-03-14

Author: highlyprofitable108
Created: March 2025
Updated: March 2025 - Removed Kelly criterion, adjusted weights, improved timing granularity
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta

# Add the project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Try relative imports first, fall back to absolute
try:
    from .config import (
        CALCULATOR_LOG_FILE,
        CSV_DIR,
        setup_logging
    )
    from .common_utils import safe_float
    from .supabase_client import (
        get_supabase_client,
        batch_upsert,
        get_most_recent_timestamp
    )
except ImportError:
    # When running as script
    from src.config import (
        CALCULATOR_LOG_FILE,
        CSV_DIR,
        setup_logging
    )
    from src.common_utils import safe_float
    from src.supabase_client import (
        get_supabase_client,
        batch_upsert,
        get_most_recent_timestamp
    )

# Initialize logger and supabase client
logger = setup_logging(CALCULATOR_LOG_FILE, "grade_calculator")
supabase = get_supabase_client()

def calculate_ev_score(ev_percent):
    """Calculate score based on Expected Value, with max cap and decay for high values."""
    try:
        ev = safe_float(ev_percent)
        if ev is None:
            return 0
        
        # Cap EV at 15%
        if ev > 15:
            # Apply decay for values above 15%
            normalized_ev = 15 - (ev - 15) * 0.5  # Adjust decay factor as needed
        else:
            normalized_ev = ev
        
        # Normalize to a score between 0 and 100
        return max(0, min(100, (normalized_ev + 10) * 5))
    except Exception as e:
        logger.error(f"Error calculating EV score: {str(e)}")
        return 0

def calculate_timing_score(event_time, timestamp):
    """
    Calculate score based on time until event with more granular ranges.
    
    The closer to game time, the more valuable a bet with an edge becomes,
    as it's more likely to represent Closing Line Value (CLV).
    """
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
        
        # More granular scoring system emphasizing CLV
        if time_diff <= 0:
            return 0  # Event already started
        elif time_diff <= 0.5:
            return 100  # Less than 30 minutes
        elif time_diff <= 1:
            return 95  # 30-60 minutes
        elif time_diff <= 2:
            return 90  # 1-2 hours
        elif time_diff <= 3:
            return 85  # 2-3 hours
        elif time_diff <= 4:
            return 80  # 3-4 hours
        elif time_diff <= 6:
            return 75  # 4-6 hours
        elif time_diff <= 8:
            return 70  # 6-8 hours
        elif time_diff <= 12:
            return 65  # 8-12 hours
        elif time_diff <= 18:
            return 60  # 12-18 hours
        elif time_diff <= 24:
            return 55  # 18-24 hours
        elif time_diff <= 36:
            return 50  # 24-36 hours
        elif time_diff <= 48:
            return 45  # 36-48 hours
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
        
        # Implement a threshold for minimum edge score
        if normalized_edge < 49:
            return 0  # Discard low edge scores
        
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
    elif composite_score >= 65:
        return 'D'
    else:
        return 'F'

def clean_numeric(value):
    """Clean numeric values by removing percentage signs and other non-numeric characters.
    
    Args:
        value: The value to clean
        
    Returns:
        Cleaned numeric value as float or None if conversion fails
    """
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

def check_and_store_initial_details(bet):
    """Check if bet_id exists in initial_bet_details and store if not."""
    try:
        bet_id = bet.get('bet_id')
        if not bet_id:
            return
            
        # Check if bet_id exists in initial_bet_details
        response = supabase.table("initial_bet_details").select("bet_id").eq("bet_id", bet_id).execute()
        
        if not response.data:
            # Store initial details if bet_id not found
            initial_details = {
                "bet_id": bet_id,
                "initial_ev": clean_numeric(bet.get('ev_percent')),
                "initial_odds": clean_numeric(bet.get('odds')),  # Ensure odds are cleaned and assigned
                "initial_line": bet.get('bet_line'),
                "first_seen": bet.get('timestamp')  # Use bet's timestamp instead of current time
            }
            
            # Log the data being inserted for debugging
            logger.info(f"Adding new initial details for bet_id: {bet_id}, EV: {initial_details['initial_ev']}, "
                        f"Odds: {initial_details['initial_odds']}, Line: {initial_details['initial_line']}, First seen: {bet.get('timestamp')}")
            
            # Insert the record
            supabase.table("initial_bet_details").insert(initial_details).execute()
            logger.info(f"Successfully stored initial details for bet_id: {bet_id}")
    except Exception as e:
        logger.error(f"Error storing initial bet details for {bet_id}: {str(e)}")
        logger.error(f"Bet data: {bet}")

def calculate_bet_grade(bet):
    """Calculate grade for a single bet."""
    try:
        # Extract required fields
        bet_id = bet.get('bet_id')
        ev_percent = bet.get('ev_percent')
        event_time = bet.get('event_time')
        odds = bet.get('odds')
        win_probability = bet.get('win_probability')
        
        # Skip bets with missing critical data
        if not all([bet_id, ev_percent, odds, win_probability, event_time]):
            logger.debug(f"SKIPPED: Bet {bet_id} - Missing required data")
            return None
        
        # Check and store initial bet details
        check_and_store_initial_details(bet)
        
        # Calculate individual scores
        ev_score = calculate_ev_score(ev_percent)
        timing_score = calculate_timing_score(event_time, bet.get('timestamp'))
        edge_score = calculate_edge_score(win_probability, odds)
        
        # Calculate composite score with updated weights
        composite_score = (
            0.55 * ev_score +
            0.30 * edge_score +
            0.15 * timing_score
        )

        # Log individual scores and composite score
        logger.info(f"Bet ID: {bet_id}, EV Score: {ev_score}, Timing Score: {timing_score}, Edge Score: {edge_score}, Composite Score: {composite_score}")

        # Log the contributions to composite score
        logger.info(f"Composite Score Calculation: (0.55 * {ev_score}) + (0.30 * {edge_score}) + (0.15 * {timing_score}) = {composite_score}")

        # Assign grade
        grade = assign_grade(composite_score)
        
        # Log the assigned grade
        logger.info(f"Assigned Grade for Bet ID {bet_id}: {grade}")
        
        # Create grade record
        return {
            "bet_id": bet_id,
            "grade": grade,
            "calculated_at": datetime.now().isoformat(),
            "ev_score": ev_score,
            "timing_score": timing_score,
            "historical_edge": edge_score,
            "composite_score": composite_score
        }
    except Exception as e:
        logger.error(f"Error calculating grade for bet {bet.get('bet_id', 'unknown')}: {e}")
        return None

def get_bets_last_24h():
    """Get bets added in the last 24 hours with only the most recent version of each bet_id."""
    supabase = get_supabase_client()
    
    # Calculate 24 hours ago
    cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
    
    try:
        # Get all unique bet_ids from the last 24 hours with pagination
        all_bet_ids = set()
        page_size = 1000
        offset = 0
        
        while True:
            query = (
                supabase.table("betting_data")
                .select("bet_id")
                .gte("timestamp", cutoff_time)
                .limit(page_size)
                .offset(offset)
            )
            
            response = query.execute()
            current_page = response.data
            
            if not current_page:
                break
                
            bet_ids = [record.get('bet_id') for record in current_page if record.get('bet_id')]
            all_bet_ids.update(bet_ids)
            logger.info(f"Retrieved {len(current_page)} bet IDs (offset {offset}), total unique IDs: {len(all_bet_ids)}")
            
            if len(current_page) < page_size:
                break
                
            offset += page_size
        
        logger.info(f"Found {len(all_bet_ids)} unique bet IDs from the last 24 hours")
        
        # Now get the most recent record for each bet_id
        unique_bets = []
        for bet_id in all_bet_ids:
            # Get the most recent record for this bet_id
            response = supabase.table("betting_data").select("*").eq("bet_id", bet_id).order("timestamp", desc=True).limit(1).execute()
            if response.data:
                unique_bets.append(response.data[0])
        
        logger.info(f"Retrieved {len(unique_bets)} unique bets from the last 24 hours")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from last 24 hours: {e}")
        # Fall back to the pagination method if the approach fails
        logger.info("Falling back to pagination method")
        return get_bets_last_24h_paginated()

def get_bets_by_date_range(start_date, end_date):
    """Get bets within a specific date range with only the most recent version of each bet_id."""
    supabase = get_supabase_client()
    
    # Format end_date to include the entire day
    if end_date:
        end_date = f"{end_date}T23:59:59"
    
    try:
        # Get all unique bet_ids in the date range with pagination
        all_bet_ids = set()
        page_size = 1000
        offset = 0
        
        while True:
            query = (
                supabase.table("betting_data")
                .select("bet_id")
            )
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            query = query.limit(page_size).offset(offset)
            
            response = query.execute()
            current_page = response.data
            
            if not current_page:
                break
                
            bet_ids = [record.get('bet_id') for record in current_page if record.get('bet_id')]
            all_bet_ids.update(bet_ids)
            logger.info(f"Retrieved {len(current_page)} bet IDs (offset {offset}), total unique IDs: {len(all_bet_ids)}")
            
            if len(current_page) < page_size:
                break
                
            offset += page_size
        
        logger.info(f"Found {len(all_bet_ids)} unique bet IDs in date range")
        
        # Now get the most recent record for each bet_id within the date range
        unique_bets = []
        total_processed = 0
        for bet_id in all_bet_ids:
            # Get the most recent record for this bet_id within the date range
            query = (
                supabase.table("betting_data")
                .select("*")
                .eq("bet_id", bet_id)
            )
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            response = query.order("timestamp", desc=True).limit(1).execute()
            if response.data:
                unique_bets.append(response.data[0])
            
            total_processed += 1
            if total_processed % 100 == 0:  # Log progress every 100 bets
                logger.info(f"Processed {total_processed}/{len(all_bet_ids)} bet IDs")
        
        logger.info(f"Retrieved {len(unique_bets)} unique bets from date range {start_date} to {end_date}")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from date range: {e}")
        # Fall back to the pagination method if the approach fails
        logger.info("Falling back to pagination method")
        return get_bets_by_date_range_paginated(start_date, end_date)

# Keep the original methods as fallbacks
def get_bets_last_24h_paginated():
    """Get bets added in the last 24 hours using pagination."""
    supabase = get_supabase_client()
    
    # Calculate 24 hours ago
    cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
    
    try:
        # Query bets from the last 24 hours with pagination
        all_bets = []
        page_size = 1000
        has_more = True
        start = 0
        
        while has_more:
            # Build query with pagination
            query = supabase.table("betting_data").select("*").gte("timestamp", cutoff_time)
            query = query.range(start, start + page_size - 1)
            
            # Execute query
            response = query.execute()
            bets = response.data
            
            if bets:
                all_bets.extend(bets)
                logger.info(f"Retrieved {len(bets)} bets from the last 24 hours (offset {start})")
                
                if len(bets) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
        
        # Get only the most recent version of each bet
        unique_bets = get_most_recent_bets(all_bets)
        logger.info(f"Retrieved {len(all_bets)} total bets, filtered to {len(unique_bets)} unique bets")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from last 24 hours with pagination: {e}")
        return []

def get_bets_by_date_range_paginated(start_date, end_date):
    """Get bets within a specific date range using pagination."""
    supabase = get_supabase_client()
    
    # Format end_date to include the entire day
    if end_date:
        end_date = f"{end_date}T23:59:59"
    
    try:
        # Query bets with pagination
        all_bets = []
        page_size = 1000
        has_more = True
        start = 0
        
        while has_more:
            # Build query with date filters and pagination
            query = supabase.table("betting_data").select("*")
            if start_date:
                query = query.gte("timestamp", start_date)
            if end_date:
                query = query.lte("timestamp", end_date)
            
            # Apply pagination
            query = query.range(start, start + page_size - 1)
            
            # Execute query
            response = query.execute()
            bets = response.data
            
            if bets:
                all_bets.extend(bets)
                logger.info(f"Retrieved {len(bets)} bets from date range (offset {start})")
                
                if len(bets) == page_size:
                    start += page_size
                else:
                    has_more = False
            else:
                has_more = False
        
        # Get only the most recent version of each bet
        unique_bets = get_most_recent_bets(all_bets)
        logger.info(f"Retrieved {len(all_bets)} total bets, filtered to {len(unique_bets)} unique bets from date range {start_date} to {end_date}")
        return unique_bets
    except Exception as e:
        logger.error(f"Error retrieving bets from date range with pagination: {e}")
        return []

def get_most_recent_bets(bets):
    """
    Filter a list of bets to get only the most recent version of each bet_id.
    
    Args:
        bets: List of bet records
        
    Returns:
        List of the most recent betting records for each bet_id
    """
    if not bets:
        return []
    
    # Group by bet_id and keep only the most recent
    latest_bets_by_id = {}
    for record in bets:
        bet_id = record.get("bet_id")
        timestamp = record.get("timestamp", "")
        
        if not bet_id or not timestamp:
            continue
            
        if bet_id not in latest_bets_by_id or timestamp > latest_bets_by_id[bet_id].get("timestamp", ""):
            latest_bets_by_id[bet_id] = record
    
    return list(latest_bets_by_id.values())

def process_bets(bets):
    """Process a list of bets and calculate grades."""
    if not bets:
        logger.info("No bets to process")
        return []
    
    logger.info(f"Processing {len(bets)} bets")
    
    # Calculate grades for all bets
    grades = []
    for bet in bets:
        grade_record = calculate_bet_grade(bet)
        if grade_record:
            grades.append(grade_record)
    
    logger.info(f"Calculated grades for {len(grades)} bets")
    return grades

def save_grades_to_csv(grades, filename):
    """Save grades to a CSV file."""
    if not grades:
        logger.info("No grades to save to CSV")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(grades)
    
    # Ensure directory exists
    os.makedirs(CSV_DIR, exist_ok=True)
    
    # Save to CSV
    csv_path = os.path.join(CSV_DIR, filename)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved {len(grades)} grades to {csv_path}")

def upload_grades_to_supabase(grades):
    """Upload grades to Supabase in bulk."""
    if not grades:
        logger.info("No grades to upload to Supabase")
        return
    
    logger.info(f"Uploading {len(grades)} grades to Supabase")
    
    # Ensure we have unique bet_ids to avoid conflicts
    unique_grades = {}
    for grade in grades:
        bet_id = grade.get("bet_id")
        if bet_id:
            unique_grades[bet_id] = grade
    
    unique_grade_list = list(unique_grades.values())
    logger.info(f"Filtered to {len(unique_grade_list)} unique grades by bet_id")
    
    # Use batch_upsert with the unique list
    batch_upsert("bet_grades", unique_grade_list, "bet_id")
    logger.info("Upload complete")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Calculate grades for betting data.')
    parser.add_argument('--start-date', type=str, help='Start date for date range (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date for date range (YYYY-MM-DD)')
    return parser.parse_args()

def main():
    """Main function to run grade calculations."""
    try:
        logger.info("Starting grade calculator main function")
        # Parse command line arguments
        args = parse_arguments()
        start_time = datetime.now()
        
        # Debug log the arguments
        logger.info(f"Arguments received: start_date={args.start_date}, end_date={args.end_date}")
        
        # Determine which mode to run in
        if args.start_date:
            # Date range mode
            logger.info(f"Running in date range mode: {args.start_date} to {args.end_date or 'now'}")
            bets = get_bets_by_date_range(args.start_date, args.end_date)
        else:
            # Get most recent timestamp from database
            most_recent = get_most_recent_timestamp()
            if most_recent:
                logger.info(f"Running for most recent timestamp: {most_recent}")
                bets = get_bets_by_date_range(most_recent, most_recent)
            else:
                # Fallback to last 24 hours if no data exists
                logger.info("No existing bets found, falling back to last 24 hours mode")
                bets = get_bets_last_24h()
        
        # Process bets
        grades = process_bets(bets)
        
        if args.start_date:
            # Save to CSV with datestamp for date range mode
            datestamp = datetime.now().strftime("%Y%m%d")
            filename = f"full_grades_{datestamp}.csv"
            save_grades_to_csv(grades, filename)
        
        # Upload to Supabase
        upload_grades_to_supabase(grades)
        
        # Log completion
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Completed in {duration:.2f} seconds. Processed {len(bets)} bets, created {len(grades) if 'grades' in locals() else 0} grades.")
        
    except Exception as e:
        logger.error(f"Error in grade calculator: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Script running as __main__")
    main()
