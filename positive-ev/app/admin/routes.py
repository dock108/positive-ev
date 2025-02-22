from flask import render_template, request, jsonify
from app.admin import bp
from app.db_utils import get_db_connection
import numpy as np
from datetime import datetime
import plotly.graph_objects as go
import logging

# Configure logging
logger = logging.getLogger(__name__)

@bp.route('/')
def index():
    """Admin Dashboard with Overview Stats."""
    logger.debug("Accessing admin dashboard index")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get total bets count
            cursor.execute("SELECT COUNT(*) FROM betting_data")
            total_bets = cursor.fetchone()[0]
            
            # Get active bets count
            cursor.execute("""
                SELECT COUNT(DISTINCT b.bet_id)
                FROM betting_data b
                LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
                WHERE boe.outcome IN ('WIN', 'LOSS')
            """)
            active_bets = cursor.fetchone()[0]
            
            stats = {
                'total_bets': total_bets,
                'active_bets': active_bets,
                'win_rate': calculate_win_rate(),
                'total_profit': calculate_total_profit(),
                'roi': calculate_roi()
            }
            
            # Recent performance graph
            performance_data = generate_performance_graph()
            
            return render_template(
                'admin/index.html',
                stats=stats,
                performance_graph=performance_data
            )
    except Exception as e:
        logger.error(f"Error in admin dashboard index: {str(e)}")
        raise

@bp.route('/data-explorer')
def data_explorer():
    """Interactive Data Explorer."""
    logger.debug("Accessing data explorer")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get distinct sports
            cursor.execute("SELECT DISTINCT sport_league FROM betting_data")
            sports = [row[0] for row in cursor.fetchall()]
            
            # Get distinct sportsbooks
            cursor.execute("SELECT DISTINCT sportsbook FROM betting_data")
            sportsbooks = [row[0] for row in cursor.fetchall()]
            
            return render_template(
                'admin/data_explorer.html',
                sports=sports,
                sportsbooks=sportsbooks
            )
    except Exception as e:
        logger.error(f"Error in data explorer: {str(e)}")
        raise

@bp.route('/api/data')
def get_data():
    """API endpoint for fetching filtered data."""
    sport = request.args.get('sport')
    sportsbook = request.args.get('sportsbook')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = "SELECT * FROM betting_data WHERE 1=1"
    params = []
    
    if sport:
        query += " AND sport_league = ?"
        params.append(sport)
    if sportsbook:
        query += " AND sportsbook = ?"
        params.append(sportsbook)
    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    if date_to:
        query += " AND timestamp <= ?"
        params.append(date_to)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        bets = cursor.fetchall()
        return jsonify([dict(bet) for bet in bets])

def calculate_win_rate():
    """Calculate overall win rate."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM betting_data WHERE result IN ('W', 'L')")
        total = cursor.fetchone()[0]
        
        if not total:
            return 0
            
        cursor.execute("SELECT COUNT(*) FROM betting_data WHERE result = 'W'")
        wins = cursor.fetchone()[0]
        return (wins / total) * 100

def calculate_total_profit():
    """Calculate total profit."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(profit_loss) FROM bet_results")
        result = cursor.fetchone()[0]
        return result if result else 0

def calculate_roi():
    """Calculate overall ROI."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(bet_size) FROM betting_data")
        total_bet_size = cursor.fetchone()[0]
        
        if not total_bet_size:
            return 0
            
        return (calculate_total_profit() / total_bet_size) * 100

def generate_performance_graph():
    """Generate performance over time graph."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(settlement_time) as date, SUM(profit_loss) as daily_profit
            FROM bet_results
            GROUP BY DATE(settlement_time)
            ORDER BY DATE(settlement_time)
        """)
        results = cursor.fetchall()
        
        if not results:
            return None
            
        dates = [row[0] for row in results]
        profits = [row[1] for row in results]
        cumulative_profits = np.cumsum(profits)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=cumulative_profits,
            mode='lines',
            name='Cumulative Profit'
        ))
        
        return fig.to_json() 