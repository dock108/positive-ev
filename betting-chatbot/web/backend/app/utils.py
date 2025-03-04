from datetime import datetime
from .db import get_db

def get_current_datetime():
    """
    Get the current datetime.
    
    Returns:
        Current datetime object
    """
    return datetime.now()

def get_timestamp_info():
    """
    Get information about timestamps in the betting_data table.
    
    Returns:
        Formatted string with timestamp information
    """
    conn = get_db()
    
    try:
        # Get the most recent timestamp
        cursor = conn.execute("SELECT MAX(timestamp) as latest FROM betting_data")
        result = cursor.fetchone()
        latest_timestamp = result['latest'] if result else "No data"
        
        # Get the oldest timestamp
        cursor = conn.execute("SELECT MIN(timestamp) as oldest FROM betting_data")
        result = cursor.fetchone()
        oldest_timestamp = result['oldest'] if result else "No data"
        
        # Get the count of distinct timestamps
        cursor = conn.execute("SELECT COUNT(DISTINCT timestamp) as count FROM betting_data")
        result = cursor.fetchone()
        timestamp_count = result['count'] if result else 0
        
        # Get the most recent 10 timestamps
        cursor = conn.execute(
            "SELECT DISTINCT timestamp FROM betting_data ORDER BY timestamp DESC LIMIT 10"
        )
        recent_timestamps = [row['timestamp'] for row in cursor.fetchall()]
        
        # Format the output
        output = "Timestamp Information:\n\n"
        output += f"Latest timestamp: {latest_timestamp}\n"
        output += f"Oldest timestamp: {oldest_timestamp}\n"
        output += f"Number of distinct timestamps: {timestamp_count}\n\n"
        
        output += "Most recent timestamps:\n"
        for i, ts in enumerate(recent_timestamps, 1):
            output += f"{i}. {ts}\n"
            
        # Get count per timestamp
        output += "\nBets per timestamp:\n"
        cursor = conn.execute(
            """
            SELECT timestamp, COUNT(*) as count 
            FROM betting_data 
            GROUP BY timestamp 
            ORDER BY timestamp DESC 
            LIMIT 10
            """
        )
        for row in cursor.fetchall():
            output += f"{row['timestamp']}: {row['count']} bets\n"
            
        return output
        
    except Exception as e:
        return f"Error retrieving timestamp information: {str(e)}" 
 
 
 