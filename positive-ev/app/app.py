from flask import Flask, render_template, jsonify, request
import os
import sqlite3
import pandas as pd
import plotly.express as px
from app.parlay_utils import ParlayUtils
from collections import Counter
from app import create_app

app = create_app()

# Define folder structure
base_dir = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app"
DATABASE = os.path.join(base_dir, "betting_data.db")

def query_db(query, args=(), one=False):
    """Helper function to query the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(query, args)
    rows = cur.fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows

@app.route('/')
def index():
    """Home Dashboard: Summary of recent activity."""
    # Get all unresolved bets
    unresolved_bets = query_db("""
        SELECT * FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        ORDER BY timestamp DESC
    """)
    
    # Count sportsbooks for parlay button visibility
    sportsbook_counts = Counter(bet['sportsbook'] for bet in unresolved_bets) if unresolved_bets else Counter()
    
    # Get summary stats
    summary_stats = {
        'total_bets': len(unresolved_bets) if unresolved_bets else 0,
        'avg_ev': sum(bet['ev_percent'] for bet in unresolved_bets) / len(unresolved_bets) if unresolved_bets else 0,
        'avg_edge': sum(bet['edge'] for bet in unresolved_bets) / len(unresolved_bets) if unresolved_bets else 0,
        'latest_timestamp': unresolved_bets[0]['timestamp'] if unresolved_bets else None,
        'time_distribution': {'Early': 0, 'Mid': 0, 'Late': 0},
        'sportsbook_distribution': dict(sportsbook_counts),
        'grade_distribution': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
    }
    
    # Calculate time and grade distributions
    if unresolved_bets:
        for bet in unresolved_bets:
            if bet['bet_time_category']:
                summary_stats['time_distribution'][bet['bet_time_category']] += 1
            if bet['grade']:
                summary_stats['grade_distribution'][bet['grade']] += 1
    
    # Convert to list of dicts for template
    current_bets = [dict(bet) for bet in unresolved_bets]
    
    return render_template(
        'index.html',
        current_bets=current_bets,
        sportsbook_counts=dict(sportsbook_counts),
        summary_stats=summary_stats
    )

@app.route('/results')
def results():
    """Resolved Bets Page: Display resolved bets."""
    resolved_bets = query_db("""
        SELECT * FROM betting_data
        WHERE result IN ('W', 'L', 'R')
        ORDER BY event_time DESC
        LIMIT 50
    """)
    return render_template('results.html', resolved_bets=resolved_bets)

@app.route("/rankings")
def rankings():
    """Ranked Opportunities Page."""
    ranked_bets = query_db("""
        WITH LatestTimestamp AS (
            SELECT MAX(timestamp) AS latest_timestamp
            FROM betting_data
        ),
        RankedBets AS (
            SELECT *,
                -- Odds Multiplier: Scale odds into a value for prioritization
                CASE
                    WHEN odds > 0 THEN (odds / 100.0) + 1 -- Positive odds: scale proportionally
                    WHEN odds < 0 THEN (100.0 / ABS(odds)) + 1 -- Negative odds: scale inversely
                    ELSE 1.0 -- Fallback for unexpected cases
                END AS odds_multiplier,
                
                -- Priority Rank: Combines EV% and odds multiplier
                ROUND(ev_percent * 
                      (CASE
                           WHEN odds > 0 THEN (odds / 100.0) + 1
                           WHEN odds < 0 THEN (100.0 / ABS(odds)) + 1
                           ELSE 1.0
                       END), 2) AS priority_rank
            FROM betting_data
            WHERE result NOT IN ('W', 'L', 'R')
              AND timestamp = (SELECT latest_timestamp FROM LatestTimestamp)
        )
        SELECT *
        FROM RankedBets
        ORDER BY priority_rank DESC, ev_percent DESC, odds_multiplier DESC
    """)
    return render_template("rankings.html", ranked_bets=ranked_bets)

@app.route('/trends')
def trends():
    """Trends and Visualization Page."""
    bets_df = pd.read_sql_query("SELECT * FROM betting_data", sqlite3.connect(DATABASE))
    trends_fig = px.line(bets_df, x='timestamp', y='ev_percent', color='result', title='EV Trends Over Time')
    trends_html = trends_fig.to_html(full_html=False)
    return render_template('trends.html', trends_html=trends_html)

@app.route('/api/calculate_parlay', methods=['POST'])
def calculate_parlay():
    """API endpoint to calculate parlay odds and metrics."""
    data = request.get_json()
    bet_ids = data.get('bet_ids', [])
    
    # Fetch bet data
    bets = []
    for bet_id in bet_ids:
        bet = query_db("SELECT * FROM betting_data WHERE bet_id = ?", (bet_id,), one=True)
        if bet:
            bets.append(dict(bet))
    
    if not bets:
        return jsonify({'error': 'No valid bets found'}), 400
    
    # Calculate parlay metrics
    try:
        parlay_result = ParlayUtils.compute_parlay_odds(bets)
        return jsonify({
            'decimal_odds': parlay_result.decimal_odds,
            'american_odds': parlay_result.american_odds,
            'implied_probability': parlay_result.implied_prob_from_odds,
            'true_probability': parlay_result.true_win_prob,
            'ev_percent': parlay_result.ev,
            'kelly_fraction': parlay_result.kelly_fraction,
            'total_edge': parlay_result.total_edge,
            'correlated_warning': parlay_result.correlated_warning
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sportsbook_bets/<sportsbook>')
def get_sportsbook_bets(sportsbook):
    """Get all active bets for a specific sportsbook."""
    bets = query_db("""
        SELECT * FROM betting_data 
        WHERE sportsbook = ? 
        AND result NOT IN ('W', 'L', 'R')
        ORDER BY timestamp DESC
    """, (sportsbook,))
    return jsonify([dict(bet) for bet in bets])

if __name__ == '__main__':
    debug_mode = app.config.get('DEBUG', False)
    app.run(debug=debug_mode)
