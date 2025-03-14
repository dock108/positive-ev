import os
import logging
import hashlib
from datetime import datetime, timedelta
from config import LOG_RETENTION_HOURS

def safe_float(value, strip_chars='%$'):
    """Safely convert string to float, handling N/A and other invalid values."""
    if not value or value == 'N/A':
        return None
    try:
        if isinstance(value, str):
            for char in strip_chars:
                value = value.replace(char, '')
        return float(value.strip() if isinstance(value, str) else value)
    except (ValueError, TypeError, AttributeError):
        return None

def cleanup_logs(log_file, retention_hours=LOG_RETENTION_HOURS):
    """Keep only the log entries from the past specified hours."""
    try:
        if os.path.exists(log_file):
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            with open(log_file, "r") as file:
                lines = file.readlines()

            recent_lines = []
            for line in lines:
                try:
                    log_time_str = line.split(" - ")[0]
                    log_time = datetime.strptime(log_time_str, "%Y-%m-%d %H:%M:%S,%f")
                    if log_time >= cutoff_time:
                        recent_lines.append(line)
                except Exception as e:
                    logging.warning(f"Malformed log line ignored: {line.strip()} - Error: {e}")

            with open(log_file, "w") as file:
                file.writelines(recent_lines)
            logging.info("Log file cleaned up. Only recent entries retained.")
    except Exception as e:
        logging.error(f"Failed to clean up log file: {e}", exc_info=True)

def fix_event_time(event_time, timestamp=None):
    """
    Convert event time from format like 'Wed, Feb 5 at 2:30 PM' to '2025-02-05 14:30'
    
    Args:
        event_time (str): Event time string from scraping
        timestamp (str): Current timestamp (optional)
    
    Returns:
        str: Formatted datetime string 'YYYY-MM-DD HH:MM'
    """
    try:
        # Use provided timestamp or current time
        if timestamp:
            if isinstance(timestamp, str):
                if 'T' in timestamp:  # Handle ISO format
                    timestamp = timestamp.replace('Z', '+00:00')
                    now = datetime.fromisoformat(timestamp)
                else:
                    now = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            else:
                now = timestamp
        else:
            now = datetime.now()
        
        # First convert relative dates to absolute
        if "Today at" in event_time:
            event_time = event_time.replace("Today", now.strftime("%a, %b %d"))
        elif "Tomorrow at" in event_time:
            tomorrow = now + timedelta(days=1)
            event_time = event_time.replace("Tomorrow", tomorrow.strftime("%a, %b %d"))

        # Extract components
        date_part = event_time.split(" at ")[0].strip()
        time_part = event_time.split(" at ")[1].strip()
        
        # Parse time
        time_obj = datetime.strptime(time_part, "%I:%M %p")
        time_str = time_obj.strftime("%H:%M")
        
        # Parse date
        date_obj = datetime.strptime(f"{date_part}, {now.year}", "%a, %b %d, %Y")
        
        # Handle year rollover
        if date_obj.month < now.month:
            date_obj = date_obj.replace(year=now.year + 1)
            
        return f"{date_obj.strftime('%Y-%m-%d')} {time_str}"
        
    except Exception as e:
        logging.error(f"Failed to fix Event Time: {event_time} due to {e}")
        return event_time

def generate_bet_id(event_time, event_teams, sport_league, bet_type, description):
    """Generate a hash-based bet ID."""
    unique_string = f"{event_time}|{event_teams}|{sport_league}|{bet_type}|{description}"
    return hashlib.md5(unique_string.encode()).hexdigest()

def extract_date_from_timestamp(timestamp_str):
    """Extract just the date part from a timestamp string."""
    try:
        if not timestamp_str:
            return "unknown_date"
            
        # Try to parse ISO format
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            # Try to parse with standard format
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            
        # Return just the date part as a string
        return dt.strftime('%Y-%m-%d')
    except Exception as e:
        logging.error(f"Error extracting date from timestamp {timestamp_str}: {str(e)}")
        return "unknown_date"

def debug_print(message, logger=None):
    """Print directly to stdout and log"""
    print(f"DEBUG: {message}")
    if logger:
        logger.info(message)
        # Force flush logger handlers
        for handler in logger.handlers:
            handler.flush()
    # Force flush stdout
    import sys
    sys.stdout.flush() 