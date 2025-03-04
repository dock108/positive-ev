from flask import Blueprint, jsonify
import sqlite3
import os
import logging
from app.auth import token_required

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/timestamps', methods=['GET'])
@token_required
def get_timestamps(current_user):
    """
    Get information about the timestamps in the betting database.
    This is a special admin endpoint only accessible to test@example.com.
    """
    logger.info(f"Timestamp endpoint accessed by user {current_user['id']} ({current_user['email']})")
    
    # Only allow access for test@example.com
    if current_user['email'] != 'test@example.com':
        logger.warning(f"Unauthorized access attempt by {current_user['email']}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'This endpoint is only accessible to admin users'
        }), 403
    
    try:
        # Connect to the database
        db_path = os.path.join('database', 'chatbot.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Get the most recent timestamp
        cursor = conn.execute(
            "SELECT MAX(timestamp) as latest_timestamp FROM betting_data WHERE ev_percent > 0"
        )
        result = cursor.fetchone()
        latest_timestamp = result['latest_timestamp'] if result else "No data found"
        
        # Get timestamp range
        cursor = conn.execute(
            "SELECT MIN(timestamp) as earliest_timestamp, MAX(timestamp) as latest_timestamp, "
            "COUNT(DISTINCT timestamp) as timestamp_count FROM betting_data"
        )
        result = cursor.fetchone()
        earliest_timestamp = result['earliest_timestamp'] if result else "No data found"
        timestamp_count = result['timestamp_count'] if result else 0
        
        # Get count of bets in most recent timestamp
        cursor = conn.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp = ?",
            (latest_timestamp,)
        )
        result = cursor.fetchone()
        latest_timestamp_bet_count = result['bet_count'] if result else 0
        
        # Get count of bets in recent context (within 6 hours but not most recent)
        cursor = conn.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp < ? AND timestamp > datetime(?, '-6 hours')",
            (latest_timestamp, latest_timestamp)
        )
        result = cursor.fetchone()
        recent_context_bet_count = result['bet_count'] if result else 0
        
        # Get count of historical bets (older than 6 hours)
        cursor = conn.execute(
            "SELECT COUNT(*) as bet_count FROM betting_data WHERE timestamp <= datetime(?, '-6 hours')",
            (latest_timestamp,)
        )
        result = cursor.fetchone()
        historical_bet_count = result['bet_count'] if result else 0
        
        # Get total bet count
        cursor = conn.execute("SELECT COUNT(*) as total_count FROM betting_data")
        result = cursor.fetchone()
        total_bet_count = result['total_count'] if result else 0
        
        # Close the connection
        conn.close()
        
        # Return the timestamp information
        return jsonify({
            'most_recent_timestamp': latest_timestamp,
            'earliest_timestamp': earliest_timestamp,
            'timestamp_count': timestamp_count,
            'latest_timestamp_bet_count': latest_timestamp_bet_count,
            'recent_context_bet_count': recent_context_bet_count,
            'historical_bet_count': historical_bet_count,
            'total_bet_count': total_bet_count
        })
        
    except Exception as e:
        logger.error(f"Error retrieving timestamp information: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(e)
        }), 500 