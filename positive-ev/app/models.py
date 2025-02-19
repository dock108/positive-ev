from datetime import datetime
from app.db_utils import get_db_connection

class BetUtils:
    """Utility functions for bet operations."""
    
    @staticmethod
    def safe_float(value, strip_chars='%$'):
        """Safely convert string to float, handling N/A and other invalid values."""
        if not value or value == 'N/A':
            return None
        try:
            for char in strip_chars:
                value = value.replace(char, '')
            return float(value.strip())
        except (ValueError, TypeError, AttributeError):
            return None
    
    @staticmethod
    def format_odds(odds):
        """Format the odds for display."""
        try:
            if not odds or odds == 'N/A':
                return None
            odds_val = int(float(odds))
            return f'+{odds_val}' if odds_val > 0 else str(odds_val)
        except (ValueError, TypeError):
            return odds
    
    @staticmethod
    def extract_player_name(bet_type, description):
        """Extract player name from bet description."""
        if "Player" not in bet_type:
            return None
        try:
            if "Double Double" in description:
                return description.replace("Player Double Double", "").strip()
            elif "Triple Double" in description:
                return description.replace("Player Triple Double", "").strip()
            else:
                # For regular prop bets, player name is everything before the last two parts
                # Example: "LeBron James Points Over 25.5" -> "LeBron James"
                parts = description.split()
                return " ".join(parts[:-2])
        except Exception:
            return None
    
    @staticmethod
    def extract_stat_type(bet_type, description):
        """Extract stat type from bet type."""
        if "Player" not in bet_type:
            return None
        for stat in ["Points", "Rebounds", "Assists", "Steals", "Blocks", "Made Threes"]:
            if stat in description:
                return stat
        return None
    
    @staticmethod
    def get_player_stats(player_name):
        """Get player stats from the database."""
        if not player_name:
            return {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if the table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_boxscores'")
                if not cursor.fetchone():
                    return {}
                
                # Get player's recent games
                cursor.execute("""
                    SELECT points, rebounds, assists, steals, blocks, made_threes
                    FROM player_boxscores
                    WHERE player_name = ?
                    ORDER BY game_id DESC
                    LIMIT 20
                """, (player_name,))
                stats = cursor.fetchall()
                
                if not stats:
                    return {}
                
                # Calculate rolling averages and other metrics
                features = {}
                stat_indices = {
                    'Points': 0, 'Rebounds': 1, 'Assists': 2,
                    'Steals': 3, 'Blocks': 4, 'Made Threes': 5
                }
                
                # Calculate averages for different windows
                for window in [5, 10, 20]:
                    window_stats = stats[:window]
                    if not window_stats:
                        continue
                    
                    for stat_name, idx in stat_indices.items():
                        try:
                            values = [float(game[idx]) if game[idx] is not None else 0.0 for game in window_stats]
                            avg = sum(values) / len(values)
                            features[f'{stat_name.lower()}_last_{window}_avg'] = round(avg, 2)
                        except (ValueError, TypeError) as e:
                            print(f"Error calculating {stat_name} average: {e}")
                            continue
                
                return features
                
        except Exception as e:
            print(f"Error getting player stats: {e}")
            return {}

def get_bet_by_id(bet_id):
    """Get a bet by its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM betting_data WHERE bet_id = ?", (bet_id,))
        bet = cursor.fetchone()
        return dict(bet) if bet else None

def get_bet_grade(bet_id):
    """Get a bet's grade."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bet_grades WHERE bet_id = ?", (bet_id,))
        grade = cursor.fetchone()
        return dict(grade) if grade else None

def get_bet_result(bet_id):
    """Get a bet's result."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bet_results WHERE bet_id = ?", (bet_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def save_bet_result(bet_id, result, profit_loss, closing_line=None, clv_percent=None, notes=None):
    """Save a bet result."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bet_results (
                bet_id, settlement_time, result, profit_loss, 
                closing_line, clv_percent, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            bet_id,
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            result,
            profit_loss,
            closing_line,
            clv_percent,
            notes
        ))
        conn.commit()

def save_bet_grade(bet_id, grade, ev_score, timing_score, historical_edge, composite_score,
                    thirty_day_roi=None, similar_bets_count=None):
    """Save a bet grade."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Delete existing grade if it exists
        cursor.execute("DELETE FROM bet_grades WHERE bet_id = ?", (bet_id,))
        
        cursor.execute("""
            INSERT INTO bet_grades (
                bet_id, grade, calculated_at, ev_score, timing_score,
                historical_edge, composite_score, thirty_day_roi, similar_bets_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bet_id,
            grade,
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            ev_score,
            timing_score,
            historical_edge,
            composite_score,
            thirty_day_roi,
            similar_bets_count
        ))
        conn.commit() 