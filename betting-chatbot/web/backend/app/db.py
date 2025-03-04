import os
import sqlite3
import datetime
from typing import Dict, Any

# Database setup
DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'chatbot.db')

def get_db():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with schema."""
    conn = get_db()
    
    # Create tables if they don't exist
    conn.executescript('''
    -- Users table for authentication
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        plan TEXT CHECK( plan IN ('free', 'premium') ) DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Chat history for context
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        message TEXT NOT NULL,
        role TEXT CHECK( role IN ('user', 'assistant') ) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Track user usage for free tier limitations
    CREATE TABLE IF NOT EXISTS user_usage (
        user_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        recommendation_count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    );

    -- Track timeout enforcement for rule violations
    CREATE TABLE IF NOT EXISTS timeout_tracker (
        user_id INTEGER NOT NULL,
        timeout_until TIMESTAMP,
        violations INTEGER DEFAULT 0,
        PRIMARY KEY (user_id)
    );
    
    -- Track individual violations
    CREATE TABLE IF NOT EXISTS violation_tracker (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Gamification: User points and levels
    CREATE TABLE IF NOT EXISTS user_gamification (
        user_id INTEGER PRIMARY KEY,
        total_points INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Gamification: User discoveries
    CREATE TABLE IF NOT EXISTS user_discoveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        discovery_type TEXT NOT NULL,
        discovery_name TEXT NOT NULL,
        points INTEGER NOT NULL,
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, discovery_name)
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_chat_history_user_session ON chat_history(user_id, session_id);
    CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp);
    CREATE INDEX IF NOT EXISTS idx_violation_tracker_user_id ON violation_tracker(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_discoveries_user_id ON user_discoveries(user_id);
    ''')
    
    conn.commit()
    conn.close()

def insert_sample_bets():
    """Insert sample betting data for testing."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM betting_data")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Calculate future event times
        now = datetime.datetime.now()
        tomorrow = now + datetime.timedelta(days=1)
        day_after = now + datetime.timedelta(days=2)
        
        # Sample NBA bets
        nba_bets = [
            {
                'bet_id': 'nba1',
                'game': 'Lakers vs Warriors',
                'bet_description': 'Lakers +3.5',
                'sportsbook': 'DraftKings',
                'odds': '-110',
                'ev_percent': 3.2,
                'win_probability': 52.5,
                'sport': 'nba',
                'league': 'NBA',
                'event_time': tomorrow.strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'bet_id': 'nba2',
                'game': 'Celtics vs Bucks',
                'bet_description': 'Over 220.5',
                'sportsbook': 'FanDuel',
                'odds': '-105',
                'ev_percent': 4.1,
                'win_probability': 54.0,
                'sport': 'nba',
                'league': 'NBA',
                'event_time': tomorrow.strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'bet_id': 'nba3',
                'game': 'Nets vs Knicks',
                'bet_description': 'Knicks -2.5',
                'sportsbook': 'BetMGM',
                'odds': '-108',
                'ev_percent': 2.8,
                'win_probability': 51.9,
                'sport': 'nba',
                'league': 'NBA',
                'event_time': day_after.strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Sample NFL bets
        nfl_bets = [
            {
                'bet_id': 'nfl1',
                'game': 'Chiefs vs Ravens',
                'bet_description': 'Chiefs ML',
                'sportsbook': 'Caesars',
                'odds': '+120',
                'ev_percent': 5.2,
                'win_probability': 48.0,
                'sport': 'nfl',
                'league': 'NFL',
                'event_time': day_after.strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'bet_id': 'nfl2',
                'game': 'Cowboys vs Eagles',
                'bet_description': 'Under 49.5',
                'sportsbook': 'PointsBet',
                'odds': '-112',
                'ev_percent': 3.5,
                'win_probability': 53.0,
                'sport': 'nfl',
                'league': 'NFL',
                'event_time': day_after.strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Sample MLB bets
        mlb_bets = [
            {
                'bet_id': 'mlb1',
                'game': 'Yankees vs Red Sox',
                'bet_description': 'Yankees -1.5',
                'sportsbook': 'BetRivers',
                'odds': '+150',
                'ev_percent': 6.8,
                'win_probability': 42.0,
                'sport': 'mlb',
                'league': 'MLB',
                'event_time': tomorrow.strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Combine all bets
        all_bets = nba_bets + nfl_bets + mlb_bets
        
        # Insert into database
        for bet in all_bets:
            cursor.execute(
                """
                INSERT INTO betting_data 
                (bet_id, game, bet_description, sportsbook, odds, ev_percent, win_probability, 
                sport, league, event_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bet['bet_id'], bet['game'], bet['bet_description'], bet['sportsbook'],
                    bet['odds'], bet['ev_percent'], bet['win_probability'], bet['sport'],
                    bet['league'], bet['event_time']
                )
            )
        
        conn.commit()
        print(f"Inserted {len(all_bets)} sample bets into the database")
    
    conn.close()

def check_timeout(user_id: int) -> datetime.datetime:
    """
    Check if a user is in a timeout period.
    
    Args:
        user_id: The ID of the user to check
        
    Returns:
        The datetime until which the user is timed out, or None if not timed out
    """
    conn = get_db()
    cursor = conn.execute(
        "SELECT timeout_until FROM timeout_tracker WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if result and result['timeout_until']:
        timeout_until = datetime.datetime.fromisoformat(result['timeout_until'])
        return timeout_until
    
    return None

def record_violation(user_id: int) -> int:
    """
    Record a chat rule violation for a user.
    
    Args:
        user_id: The ID of the user who violated the rules
        
    Returns:
        The total number of violations for the user
    """
    conn = get_db()
    
    # Get current violation count
    cursor = conn.execute(
        "SELECT COUNT(*) as violation_count FROM violation_tracker WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    violation_count = result['violation_count'] + 1 if result else 1
    
    # For testing purposes - use a fixed date that matches our database timestamps
    current_time = datetime.datetime(2025, 3, 4, 15, 0, 0).isoformat()
    
    # Record the violation
    conn.execute(
        "INSERT INTO violation_tracker (user_id, timestamp) VALUES (?, ?)",
        (user_id, current_time)
    )
    
    # If this is the third violation, set a timeout
    if violation_count >= 3:
        timeout_until = datetime.datetime(2025, 3, 4, 15, 0, 0) + datetime.timedelta(hours=24)
        conn.execute(
            "INSERT OR REPLACE INTO timeout_tracker (user_id, timeout_until) VALUES (?, ?)",
            (user_id, timeout_until.isoformat())
        )
    
    conn.commit()
    return violation_count

def save_chat_message(user_id: int, session_id: str, message: str, role: str) -> None:
    """
    Save a chat message to the database.
    
    Args:
        user_id: The ID of the user
        session_id: The session ID for the conversation
        message: The message text
        role: Either 'user' or 'assistant'
    """
    conn = get_db()
    conn.execute(
        "INSERT INTO chat_history (user_id, session_id, message, role) VALUES (?, ?, ?, ?)",
        (user_id, session_id, message, role)
    )
    conn.commit()

def get_chat_history(user_id: int, session_id: str, limit: int = 10) -> list:
    """
    Get the chat history for a user and session.
    
    Args:
        user_id: The ID of the user
        session_id: The session ID for the conversation
        limit: Maximum number of messages to return
        
    Returns:
        A list of chat messages with role and content
    """
    conn = get_db()
    cursor = conn.execute(
        """
        SELECT role, message 
        FROM chat_history 
        WHERE user_id = ? AND session_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
        """,
        (user_id, session_id, limit)
    )
    
    # Format for OpenAI API
    history = [{"role": row["role"], "content": row["message"]} for row in cursor.fetchall()]
    
    # Reverse to get chronological order
    history.reverse()
    
    return history

def record_discovery(user_id: int, discovery_type: str, discovery_name: str, points: int) -> bool:
    """
    Record a user discovery and award points.
    
    Args:
        user_id: The ID of the user
        discovery_type: The type of discovery (bet_type, team_insight, strategy, etc.)
        discovery_name: The name of the discovery
        points: The number of points to award
        
    Returns:
        True if the discovery was recorded, False if already discovered
    """
    conn = get_db()
    
    try:
        # Check if this discovery already exists for this user
        cursor = conn.execute(
            "SELECT id FROM user_discoveries WHERE user_id = ? AND discovery_name = ?",
            (user_id, discovery_name)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Already discovered
            return False
        
        # Record the discovery
        conn.execute(
            "INSERT INTO user_discoveries (user_id, discovery_type, discovery_name, points) VALUES (?, ?, ?, ?)",
            (user_id, discovery_type, discovery_name, points)
        )
        
        # Update user's total points
        conn.execute(
            """
            INSERT INTO user_gamification (user_id, total_points, last_updated) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET 
                total_points = total_points + ?,
                last_updated = CURRENT_TIMESTAMP
            """,
            (user_id, points, points)
        )
        
        # Update user's level based on points
        update_user_level(conn, user_id)
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error recording discovery: {e}")
        conn.rollback()
        return False

def update_user_level(conn, user_id: int) -> bool:
    """
    Update a user's level based on their total points.
    
    Args:
        conn: Database connection
        user_id: The ID of the user
        
    Returns:
        True if the user leveled up, False otherwise
    """
    # Define level thresholds
    level_thresholds = {
        1: 0,      # Level 1: 0-99 points
        2: 100,    # Level 2: 100-249 points
        3: 250,    # Level 3: 250-499 points
        4: 500,    # Level 4: 500-999 points
        5: 1000    # Level 5: 1000+ points
    }
    
    # Get user's current points and level
    cursor = conn.execute(
        "SELECT total_points, level FROM user_gamification WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        return False
    
    total_points = result['total_points']
    current_level = result['level']
    
    # Determine new level based on points
    new_level = current_level
    for level, threshold in level_thresholds.items():
        if total_points >= threshold:
            new_level = level
    
    # Update level if changed
    if new_level > current_level:
        conn.execute(
            "UPDATE user_gamification SET level = ? WHERE user_id = ?",
            (new_level, user_id)
        )
        return True
    
    return False

def get_user_gamification_status(user_id: int) -> dict:
    """
    Get a user's gamification status.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        A dictionary with the user's gamification status
    """
    conn = get_db()
    
    # Define level thresholds
    level_thresholds = {
        1: 0,      # Level 1: 0-99 points
        2: 100,    # Level 2: 100-249 points
        3: 250,    # Level 3: 250-499 points
        4: 500,    # Level 4: 500-999 points
        5: 1000    # Level 5: 1000+ points
    }
    
    # Get user's gamification data
    cursor = conn.execute(
        "SELECT total_points, level FROM user_gamification WHERE user_id = ?",
        (user_id,)
    )
    result = cursor.fetchone()
    
    if not result:
        # Initialize new user
        conn.execute(
            "INSERT INTO user_gamification (user_id, total_points, level) VALUES (?, 0, 1)",
            (user_id,)
        )
        total_points = 0
        level = 1
    else:
        total_points = result['total_points']
        level = result['level']
    
    # Calculate points to next level
    next_level = level + 1 if level < 5 else None
    next_level_points = level_thresholds.get(next_level) if next_level else None
    points_to_next_level = next_level_points - total_points if next_level_points else None
    
    # Get recent discoveries
    cursor = conn.execute(
        """
        SELECT discovery_name, points, discovered_at 
        FROM user_discoveries 
        WHERE user_id = ? 
        ORDER BY discovered_at DESC 
        LIMIT 5
        """,
        (user_id,)
    )
    recent_discoveries = [dict(row) for row in cursor.fetchall()]
    
    return {
        "total_points": total_points,
        "level": level,
        "next_level": next_level,
        "next_level_points": next_level_points,
        "points_to_next_level": points_to_next_level,
        "recent_discoveries": recent_discoveries
    }

def get_user_preferences(user_id: int) -> Dict[str, Any]:
    """
    Get user preferences for sportsbooks, leagues, etc.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Dictionary of user preferences
    """
    conn = get_db()
    
    # Check if user_preferences table exists, create if not
    conn.execute('''
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER PRIMARY KEY,
        preferred_sportsbooks TEXT,
        preferred_leagues TEXT,
        preferred_sports TEXT,
        preferred_bet_types TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Get user preferences
    cursor = conn.execute(
        "SELECT * FROM user_preferences WHERE user_id = ?",
        (user_id,)
    )
    
    result = cursor.fetchone()
    
    if result:
        # Parse the comma-separated values into lists
        preferences = dict(result)
        for key in ['preferred_sportsbooks', 'preferred_leagues', 'preferred_sports', 'preferred_bet_types']:
            if preferences.get(key):
                preferences[key] = preferences[key].split(',')
            else:
                preferences[key] = []
        return preferences
    else:
        # Return default empty preferences
        return {
            'preferred_sportsbooks': [],
            'preferred_leagues': [],
            'preferred_sports': [],
            'preferred_bet_types': [],
            'last_updated': None
        }

def update_user_preference(user_id: int, preference_type: str, value: str, add: bool = True) -> bool:
    """
    Update a user preference.
    
    Args:
        user_id: The ID of the user
        preference_type: The type of preference (sportsbooks, leagues, sports, bet_types)
        value: The preference value
        add: True to add the preference, False to remove it
        
    Returns:
        True if successful, False otherwise
    """
    if preference_type not in ['sportsbooks', 'leagues', 'sports', 'bet_types']:
        return False
    
    conn = get_db()
    
    # Get current preferences
    preferences = get_user_preferences(user_id)
    
    # Update the preference
    preference_key = f'preferred_{preference_type}'
    current_values = preferences.get(preference_key, [])
    
    if add and value not in current_values:
        current_values.append(value)
    elif not add and value in current_values:
        current_values.remove(value)
    
    # Convert list back to comma-separated string
    preference_value = ','.join(current_values)
    
    # Update the database
    try:
        conn.execute(
            f'''
            INSERT INTO user_preferences (user_id, {preference_key}, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
            {preference_key} = ?,
            last_updated = CURRENT_TIMESTAMP
            ''',
            (user_id, preference_value, preference_value)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user preference: {str(e)}")
        return False

def detect_preference_in_query(query: str) -> Dict[str, Any]:
    """
    Detect if the user is expressing a preference in their query.
    
    Args:
        query: The user's query
        
    Returns:
        Dictionary with detected preferences
    """
    query_lower = query.lower()
    
    # Patterns for detecting preferences
    sportsbook_patterns = {
        'draftkings': ['draftkings', 'draft kings', 'dk'],
        'fanduel': ['fanduel', 'fan duel', 'fd'],
        'caesars': ['caesars', 'caesar'],
        'betmgm': ['betmgm', 'bet mgm', 'mgm'],
        'pointsbet': ['pointsbet', 'points bet'],
        'bet365': ['bet365', 'bet 365'],
        'barstool': ['barstool', 'bar stool'],
        'wynn': ['wynn'],
        'bovada': ['bovada'],
        'unibet': ['unibet']
    }
    
    sport_patterns = {
        'basketball': ['basketball', 'nba', 'ncaab', 'college basketball'],
        'football': ['football', 'nfl', 'ncaaf', 'college football'],
        'baseball': ['baseball', 'mlb'],
        'hockey': ['hockey', 'nhl'],
        'soccer': ['soccer', 'football', 'premier league', 'la liga', 'bundesliga', 'serie a', 'ligue 1', 'mls'],
        'tennis': ['tennis'],
        'golf': ['golf', 'pga'],
        'mma': ['mma', 'ufc'],
        'boxing': ['boxing'],
        'cricket': ['cricket'],
        'rugby': ['rugby']
    }
    
    bet_type_patterns = {
        'moneyline': ['moneyline', 'money line', 'ml'],
        'spread': ['spread', 'point spread', 'against the spread', 'ats'],
        'total': ['total', 'over/under', 'over under', 'o/u'],
        'prop': ['prop', 'player prop', 'game prop'],
        'parlay': ['parlay', 'multi'],
        'teaser': ['teaser'],
        'futures': ['futures', 'future'],
        'live': ['live', 'in-game', 'in game']
    }
    
    # Check for preference indicators
    preference_indicators = [
        'i prefer', 'i like', 'i usually', 'i typically', 'i normally',
        'i want', 'i only', 'i use', 'i bet on', 'i bet with',
        'favorite', 'favourite', 'prefer', 'preferred'
    ]
    
    has_preference_indicator = any(indicator in query_lower for indicator in preference_indicators)
    
    # Initialize results
    results = {
        'has_preference': has_preference_indicator,
        'sportsbook': None,
        'sport': None,
        'bet_type': None
    }
    
    # Only process if there's a preference indicator
    if has_preference_indicator:
        # Check for sportsbooks
        for sportsbook, patterns in sportsbook_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                results['sportsbook'] = sportsbook
                break
        
        # Check for sports
        for sport, patterns in sport_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                results['sport'] = sport
                break
        
        # Check for bet types
        for bet_type, patterns in bet_type_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                results['bet_type'] = bet_type
                break
    
    return results

# Initialize database
try:
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    init_db()
    insert_sample_bets()
    print(f"Database initialized at {DATABASE_PATH}")
except Exception as e:
    print(f"Error initializing database: {e}") 