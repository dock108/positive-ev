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

@app.route('/rankings')
def rankings():
    """Ranked Opportunities Page."""
    ranked_bets = query_db("""
        WITH LatestTimestamp AS (
            SELECT MAX(timestamp) AS latest_timestamp
            FROM betting_data
        )
        SELECT *, 
            ROUND((ev_percent * win_probability) / 100, 2) AS weighted_ev,
            ROUND((JULIANDAY(event_time) - JULIANDAY('now')) * 24 * 60, 2) AS time_to_event_minutes
        FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        AND timestamp = (SELECT latest_timestamp FROM LatestTimestamp)
        ORDER BY weighted_ev DESC
    """)
    return render_template('rankings.html', ranked_bets=ranked_bets)

@app.route('/trends')
def trends():
    """Trends and Visualization Page."""
    bets_df = pd.read_sql_query("SELECT * FROM betting_data", sqlite3.connect(DATABASE))
    trends_fig = px.line(bets_df, x='timestamp', y='ev_percent', color='result', title='EV Trends Over Time')
    trends_html = trends_fig.to_html(full_html=False)
    return render_template('trends.html', trends_html=trends_html)

if __name__ == '__main__':
    app.run(debug=True)
