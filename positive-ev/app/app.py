from flask import Flask, render_template
import os
import sqlite3
import pandas as pd
import plotly.express as px

app = Flask(__name__)

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
    unresolved_bets = query_db("""
        SELECT * FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        ORDER BY timestamp DESC
        LIMIT 10
    """)
    return render_template('index.html', unresolved_bets=unresolved_bets)

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

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(debug=debug_mode)
