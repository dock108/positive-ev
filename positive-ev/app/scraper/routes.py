from flask import Blueprint, jsonify
from app.scraper.services import ScraperService
from app.db_utils import get_db_connection

bp = Blueprint('scraper', __name__)

@bp.route('/scrape')
def scrape():
    """Endpoint to trigger scraping."""
    try:
        scraper = ScraperService()
        new_bets = scraper.scrape_odds()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully scraped {len(new_bets)} new bets'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/cleanup')
def cleanup():
    """Endpoint to trigger data cleanup."""
    try:
        scraper = ScraperService()
        archived_count = scraper.cleanup_old_data()
        
        return jsonify({
            'status': 'success',
            'message': f'Successfully archived {archived_count} old bets'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/stats')
def stats():
    """Get scraping statistics."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total bets count
            cursor.execute("SELECT COUNT(*) FROM betting_data")
            total_bets = cursor.fetchone()[0]
            
            # Get today's bets count
            cursor.execute("""
                SELECT COUNT(*) FROM betting_data 
                WHERE DATE(timestamp) = DATE('now')
            """)
            todays_bets = cursor.fetchone()[0]
            
            # Get active bets count
            cursor.execute("""
                SELECT COUNT(*) FROM betting_data 
                WHERE result NOT IN ('W', 'L', 'R') OR result IS NULL
            """)
            active_bets = cursor.fetchone()[0]
            
            return jsonify({
                'status': 'success',
                'stats': {
                    'total_bets': total_bets,
                    'todays_bets': todays_bets,
                    'active_bets': active_bets
                }
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 