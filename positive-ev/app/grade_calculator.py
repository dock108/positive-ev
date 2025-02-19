import os
import sys
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'grade_calculator.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('grade_calculator')

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'betting_data.db')
    logger.debug(f"Connecting to database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        logger.debug("Successfully established database connection")
        conn.row_factory = sqlite3.Row
        yield conn
        logger.debug("Database connection yielded successfully")
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        try:
            conn.close()
            logger.debug("Database connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connection: {str(e)}")

def safe_float(value, strip_chars='%$'):
    """Safely convert string to float, handling N/A and other invalid values."""
    if not value or value == 'N/A':
        return None
    try:
        for char in strip_chars:
            value = value.replace(char, '')
        return float(value.strip())
    except (ValueError, TypeError, AttributeError):
        return None

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
    """Calculate score based on how early the bet was placed."""
    try:
        formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']
        event_dt = None
        placed_dt = None
        
        for fmt in formats:
            try:
                event_dt = datetime.strptime(event_time, fmt)
                break
            except ValueError:
                continue
                
        for fmt in formats:
            try:
                placed_dt = datetime.strptime(timestamp, fmt)
                break
            except ValueError:
                continue
        
        if not event_dt or not placed_dt:
            logger.error(f"Could not parse timestamps: event_time={event_time}, timestamp={timestamp}")
            return 0
            
        time_diff = event_dt - placed_dt
        hours_before = time_diff.total_seconds() / 3600
        if hours_before >= 24:
            return 100
        return (hours_before / 24) * 100
    except Exception as e:
        logger.error(f"Error calculating timing score: {str(e)}")
        return 0

def calculate_kelly_score(win_probability, odds):
    """Calculate score based on Kelly Criterion."""
    try:
        win_prob = safe_float(win_probability) / 100
        if win_prob is None:
            return 0
        
        odds = float(odds)
        if odds > 0:
            decimal_odds = (odds + 100) / 100
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        kelly = (win_prob * (decimal_odds - 1) - (1 - win_prob)) / (decimal_odds - 1)
        normalized_kelly = (kelly + 0.1) * 500
        return max(0, min(100, normalized_kelly))
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
    """Calculate grades for all ungraded bets."""
    logger.info("Starting grade calculation...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # First, get all timestamps for ungraded bets in order
        cursor.execute("""
            SELECT DISTINCT b.timestamp 
            FROM betting_data b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
            WHERE g.bet_id IS NULL
            ORDER BY b.timestamp ASC
        """)
        timestamps = [row[0] for row in cursor.fetchall()]
        
        if not timestamps:
            logger.info("No ungraded bets found in database")
            return
        
        logger.info(f"Found {len(timestamps)} unique timestamps with ungraded bets to process")
        total_bets_processed = 0
        total_grades_added = 0
        
        # Process each timestamp in order
        for timestamp in timestamps:
            logger.info(f"Processing ungraded bets from timestamp: {timestamp}")
            
            # Get all ungraded bets for this timestamp
            cursor.execute("""
                SELECT b.bet_id, b.ev_percent, b.event_time, b.odds, b.win_probability
                FROM betting_data b
                LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
                WHERE b.timestamp = ? AND g.bet_id IS NULL
            """, (timestamp,))
            bets = cursor.fetchall()
            
            if not bets:
                continue
            
            logger.info(f"Found {len(bets)} ungraded bets for timestamp {timestamp}")
            
            for bet in bets:
                try:
                    total_bets_processed += 1
                    bet_id, ev_percent, event_time, odds, win_probability = bet
                    
                    # Skip bets with missing critical data
                    if not all([ev_percent, odds, win_probability, event_time]):
                        logger.warning(f"Skipping bet {bet_id} due to missing data")
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
                    
                    # Delete existing grade if it exists
                    cursor.execute("DELETE FROM bet_grades WHERE bet_id = ?", (bet_id,))
                    
                    # Create new grade
                    cursor.execute("""
                        INSERT INTO bet_grades (
                            bet_id, grade, calculated_at, ev_score, timing_score,
                            historical_edge, composite_score, similar_bets_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        bet_id,
                        assign_grade(composite_score),
                        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        ev_score,
                        timing_score,
                        edge_score,
                        composite_score,
                        0  # Not using historical data yet
                    ))
                    
                    total_grades_added += 1
                    
                    # Commit every 100 grades to avoid memory issues
                    if total_grades_added % 100 == 0:
                        conn.commit()
                        logger.info(f"Processed {total_grades_added} grades...")
                    
                except Exception as e:
                    logger.error(f"Error grading bet {bet_id}: {str(e)}")
                    continue
            
            # Commit after each timestamp
            try:
                conn.commit()
                logger.info(f"Committed grades for timestamp {timestamp}")
            except Exception as e:
                conn.rollback()
                logger.error(f"Error committing grades for timestamp {timestamp}: {e}")
                continue
    
    logger.info(f"Grade calculation complete. Processed {total_bets_processed} bets, added {total_grades_added} grades.")

def main():
    """Main function to run grade calculations."""
    try:
        logger.info("Starting grade calculator job")
        start_time = datetime.now()
        
        calculate_grades()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Grade calculator job completed successfully in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error running grade calculator: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 