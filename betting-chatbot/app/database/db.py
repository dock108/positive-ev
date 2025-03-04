import sqlite3
import os
import datetime
from typing import Dict, List, Any, Optional, Tuple
from flask import g, current_app

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database/chatbot.db')

def get_db():
    """Get a database connection, creating one if it doesn't exist."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    
    return g.db

def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with schema."""
    db = get_db()
    
    with current_app.open_resource('database/schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    db.commit()

def get_bet_recommendations(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Get bet recommendations based on user query.
    Only returns bets from the most recent timestamp in the database.
    """
    db = get_db()
    
    # First, get the most recent timestamp
    cursor = db.execute(
        "SELECT MAX(timestamp) as latest_timestamp FROM betting_data WHERE ev_percent > 0"
    )
    result = cursor.fetchone()
    latest_timestamp = result['latest_timestamp'] if result else None
    
    if not latest_timestamp:
        return []
    
    # Extract keywords from query
    keywords = query.lower().split()
    sport_keywords = {
        'nba': ['nba', 'basketball'],
        'nfl': ['nfl', 'football'],
        'mlb': ['mlb', 'baseball'],
        'nhl': ['nhl', 'hockey'],
        'soccer': ['soccer', 'football', 'epl', 'premier', 'liga', 'bundesliga', 'serie a']
    }
    
    # Determine sport from keywords
    target_sport = None
    for sport, terms in sport_keywords.items():
        if any(term in keywords for term in terms):
            target_sport = sport
            break
    
    # Base query - get only the most recent timestamp data with positive EV
    sql = """
        SELECT 
            id,
            bet_id,
            event_teams as game,
            description as bet_description,
            sportsbook,
            odds,
            ev_percent,
            win_probability,
            sport,
            league,
            event_time,
            timestamp
        FROM betting_data 
        WHERE ev_percent > 0
        AND event_time > datetime('now')
        AND timestamp = ?
    """
    params = [latest_timestamp]
    
    # Add sport filter if detected
    if target_sport:
        sql += " AND sport LIKE ?"
        params.append(f"%{target_sport}%")
    
    # Add team filter if detected
    team_keywords = [word for word in keywords if len(word) > 3 and word not in ['what', 'best', 'good', 'recommend', 'should', 'could', 'would', 'bet', 'bets', 'betting', 'wager', 'game', 'games', 'match', 'matches', 'team', 'teams', 'player', 'players']]
    
    if team_keywords:
        team_conditions = []
        for keyword in team_keywords:
            team_conditions.append("event_teams LIKE ?")
            params.append(f"%{keyword}%")
        
        if team_conditions:
            sql += " AND (" + " OR ".join(team_conditions) + ")"
    
    # Add ordering and limit
    sql += " ORDER BY ev_percent DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    cursor = db.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    
    return results

def get_recent_context_bets(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get recent bets (within last 6 hours but not the most recent timestamp) for chatbot context.
    These are not shown directly to the user but help the chatbot provide better responses.
    """
    db = get_db()
    
    # First, get the most recent timestamp
    cursor = db.execute(
        "SELECT MAX(timestamp) as latest_timestamp FROM betting_data WHERE ev_percent > 0"
    )
    result = cursor.fetchone()
    latest_timestamp = result['latest_timestamp'] if result else None
    
    if not latest_timestamp:
        return []
    
    # Extract keywords from query
    keywords = query.lower().split()
    sport_keywords = {
        'nba': ['nba', 'basketball'],
        'nfl': ['nfl', 'football'],
        'mlb': ['mlb', 'baseball'],
        'nhl': ['nhl', 'hockey'],
        'soccer': ['soccer', 'football', 'epl', 'premier', 'liga', 'bundesliga', 'serie a']
    }
    
    # Determine sport from keywords
    target_sport = None
    for sport, terms in sport_keywords.items():
        if any(term in keywords for term in terms):
            target_sport = sport
            break
    
    # Base query - get data within last 6 hours but not the most recent timestamp
    sql = """
        SELECT 
            id,
            bet_id,
            event_teams as game,
            description as bet_description,
            sportsbook,
            odds,
            ev_percent,
            win_probability,
            sport,
            league,
            event_time,
            timestamp
        FROM betting_data 
        WHERE ev_percent > 0
        AND event_time > datetime('now')
        AND timestamp < ?
        AND timestamp > datetime(?, '-6 hours')
    """
    params = [latest_timestamp, latest_timestamp]
    
    # Add sport filter if detected
    if target_sport:
        sql += " AND sport LIKE ?"
        params.append(f"%{target_sport}%")
    
    # Add team filter if detected
    team_keywords = [word for word in keywords if len(word) > 3 and word not in ['what', 'best', 'good', 'recommend', 'should', 'could', 'would', 'bet', 'bets', 'betting', 'wager', 'game', 'games', 'match', 'matches', 'team', 'teams', 'player', 'players']]
    
    if team_keywords:
        team_conditions = []
        for keyword in team_keywords:
            team_conditions.append("event_teams LIKE ?")
            params.append(f"%{keyword}%")
        
        if team_conditions:
            sql += " AND (" + " OR ".join(team_conditions) + ")"
    
    # Add ordering and limit
    sql += " ORDER BY timestamp DESC, ev_percent DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    cursor = db.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    
    return results

def get_historical_bets(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get historical betting data for informational purposes.
    Uses data older than 6 hours from the most recent timestamp.
    """
    db = get_db()
    
    # First, get the most recent timestamp
    cursor = db.execute(
        "SELECT MAX(timestamp) as latest_timestamp FROM betting_data WHERE ev_percent > 0"
    )
    result = cursor.fetchone()
    latest_timestamp = result['latest_timestamp'] if result else None
    
    if not latest_timestamp:
        return []
    
    # Extract keywords from query
    keywords = query.lower().split()
    sport_keywords = {
        'nba': ['nba', 'basketball'],
        'nfl': ['nfl', 'football'],
        'mlb': ['mlb', 'baseball'],
        'nhl': ['nhl', 'hockey'],
        'soccer': ['soccer', 'football', 'epl', 'premier', 'liga', 'bundesliga', 'serie a']
    }
    
    # Determine sport from keywords
    target_sport = None
    for sport, terms in sport_keywords.items():
        if any(term in keywords for term in terms):
            target_sport = sport
            break
    
    # Base query - get historical data (older than 6 hours from the most recent timestamp)
    sql = """
        SELECT 
            id,
            bet_id,
            event_teams as game,
            description as bet_description,
            sportsbook,
            odds,
            ev_percent,
            win_probability,
            sport,
            league,
            event_time,
            timestamp
        FROM betting_data 
        WHERE ev_percent > 0
        AND timestamp <= datetime(?, '-6 hours')
    """
    params = [latest_timestamp]
    
    # Add sport filter if detected
    if target_sport:
        sql += " AND sport LIKE ?"
        params.append(f"%{target_sport}%")
    
    # Add team filter if detected
    team_keywords = [word for word in keywords if len(word) > 3 and word not in ['what', 'best', 'good', 'recommend', 'should', 'could', 'would', 'bet', 'bets', 'betting', 'wager', 'game', 'games', 'match', 'matches', 'team', 'teams', 'player', 'players']]
    
    if team_keywords:
        team_conditions = []
        for keyword in team_keywords:
            team_conditions.append("event_teams LIKE ?")
            params.append(f"%{keyword}%")
        
        if team_conditions:
            sql += " AND (" + " OR ".join(team_conditions) + ")"
    
    # Add ordering and limit
    sql += " ORDER BY timestamp DESC, ev_percent DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    cursor = db.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    
    return results

def track_recommendation_usage(user_id: int) -> Tuple[int, bool]:
    """
    Track recommendation usage for a user.
    Returns (count, is_allowed) tuple.
    """
    db = get_db()
    today = datetime.date.today().isoformat()
    
    # Get current usage
    cursor = db.execute(
        "SELECT recommendation_count FROM user_usage WHERE user_id = ? AND date = ?",
        (user_id, today)
    )
    row = cursor.fetchone()
    
    if row:
        count = row['recommendation_count']
    else:
        # Create new record for today
        db.execute(
            "INSERT INTO user_usage (user_id, date, recommendation_count) VALUES (?, ?, 0)",
            (user_id, today)
        )
        count = 0
    
    # Check if user is allowed more recommendations (free tier limit is 3)
    user_plan = get_user_plan(user_id)
    is_allowed = True
    
    if user_plan == 'free' and count >= 3:
        is_allowed = False
    else:
        # Increment usage count
        db.execute(
            "UPDATE user_usage SET recommendation_count = recommendation_count + 1 WHERE user_id = ? AND date = ?",
            (user_id, today)
        )
        db.commit()
        count += 1
    
    return count, is_allowed

def get_user_plan(user_id: int) -> str:
    """Get the subscription plan for a user."""
    db = get_db()
    cursor = db.execute("SELECT plan FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        return row['plan']
    return 'free'  # Default to free plan

def check_timeout(user_id: int) -> Optional[datetime.datetime]:
    """
    Check if a user is currently timed out.
    Returns the timeout expiry time if timed out, None otherwise.
    """
    db = get_db()
    cursor = db.execute(
        "SELECT timeout_until FROM timeout_tracker WHERE user_id = ? AND timeout_until > datetime('now')",
        (user_id,)
    )
    row = cursor.fetchone()
    
    if row:
        return row['timeout_until']
    return None

def record_violation(user_id: int) -> int:
    """
    Record a rule violation for a user.
    Returns the updated violation count.
    """
    db = get_db()
    
    # Check if user exists in timeout tracker
    cursor = db.execute("SELECT violations FROM timeout_tracker WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        # Update existing record
        violations = row['violations'] + 1
        
        # Calculate timeout duration based on violation count
        timeout_duration = None
        if violations >= 4:
            # 4th violation: 24 hours
            timeout_duration = datetime.timedelta(days=1)
        elif violations >= 5:
            # 5th violation: 3 days
            timeout_duration = datetime.timedelta(days=3)
        elif violations >= 6:
            # 6th violation: 1 week
            timeout_duration = datetime.timedelta(days=7)
        elif violations >= 7:
            # 7th+ violation: 1 month
            timeout_duration = datetime.timedelta(days=30)
        
        if timeout_duration:
            timeout_until = datetime.datetime.now() + timeout_duration
            db.execute(
                "UPDATE timeout_tracker SET violations = ?, timeout_until = ? WHERE user_id = ?",
                (violations, timeout_until, user_id)
            )
        else:
            db.execute(
                "UPDATE timeout_tracker SET violations = ? WHERE user_id = ?",
                (violations, user_id)
            )
    else:
        # Create new record
        violations = 1
        db.execute(
            "INSERT INTO timeout_tracker (user_id, violations) VALUES (?, ?)",
            (user_id, violations)
        )
    
    db.commit()
    return violations

def save_chat_message(user_id: int, session_id: str, message: str, role: str) -> int:
    """
    Save a chat message to the history.
    Returns the ID of the inserted message.
    """
    db = get_db()
    cursor = db.execute(
        "INSERT INTO chat_history (user_id, session_id, message, role) VALUES (?, ?, ?, ?)",
        (user_id, session_id, message, role)
    )
    db.commit()
    return cursor.lastrowid

def get_chat_history(user_id: int, session_id: str, limit: int = 25) -> List[Dict[str, Any]]:
    """
    Get recent chat history for a user session.
    Limited to the most recent messages (default 25).
    """
    db = get_db()
    cursor = db.execute(
        """
        SELECT * FROM chat_history 
        WHERE user_id = ? AND session_id = ? 
        ORDER BY timestamp DESC LIMIT ?
        """,
        (user_id, session_id, limit)
    )
    
    # Return in chronological order (oldest first)
    results = [dict(row) for row in cursor.fetchall()]
    return list(reversed(results))

def migrate_from_positive_ev(source_db_path: str):
    """
    Migrate data from the Positive EV database to the chatbot database.
    This is a one-time operation for initial setup.
    """
    source_db = sqlite3.connect(source_db_path)
    source_db.row_factory = sqlite3.Row
    
    target_db = get_db()
    
    # Get recent positive EV bets
    cursor = source_db.execute(
        """
        SELECT 
            bet_id, 
            event_teams as game, 
            description as bet_description, 
            sportsbook, 
            odds, 
            ev_percent, 
            win_probability,
            sport,
            league,
            event_time,
            timestamp
        FROM betting_data
        WHERE ev_percent > 0
        AND event_time > datetime('now')
        ORDER BY ev_percent DESC
        LIMIT 1000
        """
    )
    
    bets = [dict(row) for row in cursor.fetchall()]
    
    # Insert into our database
    for bet in bets:
        target_db.execute(
            """
            INSERT OR IGNORE INTO betting_data 
            (bet_id, game, bet_description, sportsbook, odds, ev_percent, win_probability, 
             sport, league, event_time, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bet['bet_id'], bet['game'], bet['bet_description'], bet['sportsbook'],
                bet['odds'], bet['ev_percent'], bet['win_probability'], bet['sport'],
                bet['league'], bet['event_time'], bet['timestamp']
            )
        )
    
    target_db.commit()
    source_db.close()
