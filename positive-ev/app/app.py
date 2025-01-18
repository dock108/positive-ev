from flask import Flask, render_template, request
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

app = Flask(__name__)

DATABASE = 'betting_data.db'

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
        ORDER BY event_time ASC
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
        SELECT *, 
            (ev_percent * win_probability) AS weighted_ev
        FROM betting_data
        WHERE result NOT IN ('W', 'L', 'R')
        ORDER BY weighted_ev DESC
        LIMIT 20
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
