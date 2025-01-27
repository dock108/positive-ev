# Flask UI for Mega-Plan Positive EV Utility

This guide provides the implementation plan for the Flask-based UI as part of the Mega-Plan Positive EV Utility. The UI integrates new modeling features, trend visualizations, and a ranking system to enhance usability and decision-making.

---

## Prerequisites

1. **Install Python**: Ensure Python 3.11+ is installed.
2. **Dependencies**:
   Install the required libraries:
   ```
   pip install Flask==2.3.2 requests==2.28.1 plotly==5.14.1 pandas==1.5.2
   ```
3. **SQLite Database**:
   - Set up `betting_data.db` with required schemas (`betting_data`, `nba_box_scores`, etc.).

---

## Directory Structure

```plaintext
/app
├── app.py                    # Flask app for UI
├── scraper.py                # Bet scraping logic
├── scrape_boxscores.py       # Fetch NBA boxscores
├── update_results.py         # Match bets to results
├── modeling.py               # Ranking and trends logic
├── templates/
│   ├── index.html            # Home dashboard
│   ├── results.html          # Resolved bets
│   ├── rankings.html         # Ranked opportunities
│   ├── trends.html           # Betting trends
├── static/                   # CSS/JS for Flask UI
│   └── styles.css            # Styling for the UI
├── betting_data.db           # SQLite database
├── requirements.txt          # Python dependencies
└── logs/                     # Log files
```

---

## Flask App: `app.py`

```python
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
```

---

## Templates

### `index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Positive EV Dashboard</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h1>Recent Bets</h1>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Event</th>
            <th>EV%</th>
            <th>Odds</th>
            <th>Bet Type</th>
            <th>Sportsbook</th>
        </tr>
        {% for bet in unresolved_bets %}
        <tr>
            <td>{{ bet['timestamp'] }}</td>
            <td>{{ bet['event_teams'] }}</td>
            <td>{{ bet['ev_percent'] }}</td>
            <td>{{ bet['odds'] }}</td>
            <td>{{ bet['bet_type'] }}</td>
            <td>{{ bet['sportsbook'] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

---

### `rankings.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Ranked Opportunities</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h1>Top Ranked Bets</h1>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Event</th>
            <th>EV%</th>
            <th>Win Probability</th>
            <th>Weighted EV</th>
        </tr>
        {% for bet in ranked_bets %}
        <tr>
            <td>{{ bet['timestamp'] }}</td>
            <td>{{ bet['event_teams'] }}</td>
            <td>{{ bet['ev_percent'] }}</td>
            <td>{{ bet['win_probability'] }}</td>
            <td>{{ bet['weighted_ev'] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

---

### `trends.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Betting Trends</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h1>EV Trends</h1>
    <div>
        {{ trends_html | safe }}
    </div>
</body>
</html>
```

---

## Next Steps

1. **Test Locally**:
   - Run Flask locally with `python app.py`.
   - Validate UI elements and data accuracy.

2. **Enhance Functionality**:
   - Add filtering and sorting options.
   - Implement additional visualizations for better insights.

3. **Prepare for Docker**:
   - Ensure all scripts are container-ready for deployment.
  
---

## Future Enhancements

As the Mega-Plan Positive EV Utility evolves, consider these additional features for the Flask UI:

1. **Advanced Filters**:
   - Allow users to filter bets by:
     - Event Time Range
     - Sportsbook
     - Bet Type
     - EV% Thresholds

2. **Real-Time Updates**:
   - Implement WebSocket-based updates for live odds and bet changes.

3. **Custom Rankings**:
   - Enable users to customize ranking weights (e.g., prioritize EV%, win probability, or time to event).

4. **Bet History Analysis**:
   - Provide a detailed page for historical performance, showing:
     - Profit/Loss trends.
     - Hit/Miss ratio for specific sportsbooks or bet types.

5. **Integration with Modeling**:
   - Expose modeling outputs directly in the UI:
     - Show "Adjusted EV" for current bets.
     - Display predicted win percentages and their trends.

6. **User Authentication**:
   - Add basic login functionality for tracking personalized metrics or limiting access to specific users.

7. **Mobile-First Design**:
   - Optimize the UI for mobile devices to enable on-the-go analysis.

---

## Deployment Considerations

While running locally provides flexibility during development, transitioning to a production environment requires additional steps:
   
1. **Set Up Environment Variables**:
   - Secure sensitive data like database paths or API keys with `.env` files.

2. **Scalability**:
   - Use a lightweight web server like Gunicorn to handle production-level traffic:
     ```bash
     gunicorn -w 4 -b 0.0.0.0:5000 app:app
     ```

3. **Logging**:
   - Implement robust logging and monitoring solutions (e.g., ELK stack, Fluentd).

4. **Error Handling**:
   - Ensure all errors are logged and presented with user-friendly messages in the UI.

With these enhancements, the Flask UI will be a comprehensive and scalable tool for analyzing and ranking positive EV betting opportunities.
