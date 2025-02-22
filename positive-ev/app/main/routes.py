from flask import render_template, request, jsonify
from app.main import bp
from app.db_utils import get_db_connection
from datetime import datetime
import logging
from app.parlay_utils import ParlayUtils

# Configure logging to write to a file
logging.basicConfig(filename='app/logs/thirty_day_results.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_datetime(dt_str):
    """Parse datetime string, trying multiple formats."""
    if not dt_str:
        return None
    
    formats = [
        '%Y-%m-%d %H:%M:%S',  # with seconds
        '%Y-%m-%d %H:%M',     # without seconds
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None

def safe_float(value, strip_chars='%$'):
    """Safely convert string to float, removing specified characters."""
    if not value or value == 'N/A':
        return 0
    try:
        for char in strip_chars:
            value = value.replace(char, '')
        return float(value.strip())
    except (ValueError, TypeError, AttributeError):
        return 0

@bp.route('/')
def index():
    """Home Dashboard: Display all betting opportunities."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the latest timestamp
        cursor.execute("SELECT timestamp FROM betting_data ORDER BY timestamp DESC LIMIT 1")
        latest_timestamp = cursor.fetchone()
        
        if not latest_timestamp:
            return render_template('index.html', current_bets=[], summary_stats={'total_bets': 0}, sportsbook_counts={})
        
        latest_timestamp = latest_timestamp[0]
        
        # Get all bets from the latest timestamp
        cursor.execute("""
            SELECT b.*, g.grade, g.composite_score, g.ev_score, g.timing_score, g.historical_edge,
                   CASE WHEN ab.bet_id IS NOT NULL THEN 1 ELSE 0 END as already_bet,
                   oh.close_odds, oh.low_odds, oh.high_odds
            FROM betting_data b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
            LEFT JOIN already_bet ab ON b.bet_id = ab.bet_id
            LEFT JOIN odds_history oh ON b.bet_id = oh.bet_id
            WHERE b.timestamp = ?
            ORDER BY g.composite_score DESC NULLS LAST
        """, (latest_timestamp,))
        all_bets = cursor.fetchall()
        
        print(f"Found {len(all_bets)} bets for timestamp {latest_timestamp}")
        
        # Convert bets to a list of dictionaries with additional features
        current_bets = []
        total_ev = 0
        total_edge = 0
        valid_ev_count = 0
        valid_edge_count = 0
        time_distribution = {'Early': 0, 'Mid': 0, 'Late': 0, 'Unknown': 0}
        sportsbook_distribution = {}
        
        for bet in all_bets:
            try:
                # Convert sqlite3.Row to dictionary
                bet_dict = dict(bet)
                
                # Calculate market metrics
                odds = float(bet_dict['odds']) if bet_dict['odds'] and bet_dict['odds'] != 'N/A' else 0
                
                # Track odds in history only if they're different from what we've seen
                if odds != 0:
                    cursor.execute("""
                        SELECT close_odds, low_odds, high_odds 
                        FROM odds_history 
                        WHERE bet_id = ?
                        LIMIT 1
                    """, (bet_dict['bet_id'],))
                    
                    existing_odds = cursor.fetchone()
                    current_odds = int(odds)
                    
                    if not existing_odds:
                        # First time seeing this bet
                        cursor.execute("""
                            INSERT INTO odds_history (bet_id, close_odds, low_odds, high_odds, recorded_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (bet_dict['bet_id'], current_odds, current_odds, current_odds, bet_dict['timestamp']))
                    else:
                        # Update existing record
                        close_odds = current_odds  # Always update close odds to current
                        low_odds = min(current_odds, existing_odds['low_odds'] if existing_odds['low_odds'] is not None else current_odds)
                        high_odds = max(current_odds, existing_odds['high_odds'] if existing_odds['high_odds'] is not None else current_odds)
                        
                        cursor.execute("""
                            UPDATE odds_history 
                            SET close_odds = ?, low_odds = ?, high_odds = ?, recorded_at = ?
                            WHERE bet_id = ?
                        """, (close_odds, low_odds, high_odds, bet_dict['timestamp'], bet_dict['bet_id']))
                    
                    conn.commit()
                
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                # Parse timestamps
                timestamp = parse_datetime(bet_dict['timestamp'])
                event_time = parse_datetime(bet_dict['event_time'])
                
                # Calculate EV and probability metrics
                ev_percent = safe_float(bet_dict['ev_percent'], '%')
                win_prob = safe_float(bet_dict['win_probability'], '%')
                
                # Debug prints
                print(f"\nDebug for bet {bet_dict['bet_id']}:")
                print(f"Raw odds: {bet_dict['odds']}")
                print(f"Converted odds: {odds}")
                print(f"Market implied prob: {market_implied_prob}")
                print(f"Raw win probability: {bet_dict['win_probability']}")
                print(f"Converted win prob: {win_prob}")
                
                edge = win_prob - market_implied_prob if market_implied_prob and win_prob else None
                print(f"Calculated edge: {edge}")
                
                # Calculate Kelly criterion
                kelly_criterion = None
                if odds and win_prob:
                    decimal_odds = (abs(odds) + 100) / 100 if odds > 0 else (100 / abs(odds)) + 1
                    kelly_criterion = ((win_prob / 100 * (decimal_odds - 1)) - (1 - win_prob / 100)) / (decimal_odds - 1) * 100
                
                # Update summary statistics
                if ev_percent:
                    total_ev += ev_percent
                    valid_ev_count += 1
                if edge:
                    total_edge += edge
                    valid_edge_count += 1
                
                # Calculate time-based features
                time_to_event = None
                bet_time_category = "Unknown"
                if event_time and timestamp:
                    time_diff = event_time - timestamp
                    time_to_event = time_diff.total_seconds() / 3600
                    bet_time_category = (
                        "Early" if time_to_event >= 24 
                        else "Mid" if time_to_event >= 6 
                        else "Late"
                    )
                
                # Update time distribution
                time_distribution[bet_time_category] += 1
                
                # Update sportsbook distribution
                if bet_dict['sportsbook']:
                    sportsbook_distribution[bet_dict['sportsbook']] = sportsbook_distribution.get(bet_dict['sportsbook'], 0) + 1
                
                # Format bet data
                bet_data = {
                    'bet_id': bet_dict['bet_id'],
                    'event_teams': bet_dict['event_teams'],
                    'sport_league': bet_dict['sport_league'],
                    'bet_type': bet_dict['bet_type'],
                    'description': bet_dict['description'],
                    'sportsbook': bet_dict['sportsbook'],
                    'odds': odds if odds is not None else bet_dict['odds'],
                    'close_odds': bet_dict.get('close_odds'),
                    'low_odds': bet_dict.get('low_odds'),
                    'high_odds': bet_dict.get('high_odds'),
                    'win_probability': win_prob,
                    'market_implied_prob': market_implied_prob if market_implied_prob is not None else 0,
                    'edge': edge,
                    'ev_percent': ev_percent,
                    'kelly_criterion': kelly_criterion,
                    'recommended_bet_size': safe_float(bet_dict['bet_size'], '$'),
                    'timestamp': timestamp,
                    'event_time': event_time,
                    'time_to_event': time_to_event,
                    'bet_time_category': bet_time_category,
                    'composite_score': round(bet_dict['composite_score'], 1) if bet_dict['composite_score'] else 0,
                    'grade': bet_dict['grade'] if bet_dict['grade'] else 'N/A',
                    'ev_score': round(bet_dict['ev_score'], 1) if bet_dict['ev_score'] else 0,
                    'timing_score': round(bet_dict['timing_score'], 1) if bet_dict['timing_score'] else 0,
                    'historical_edge': round(bet_dict['historical_edge'], 1) if bet_dict['historical_edge'] else 0,
                    'ev_percentile': None,
                    'edge_percentile': None,
                    'kelly_percentile': None,
                    'already_bet': bool(bet_dict['already_bet'])
                }
                
                current_bets.append(bet_data)
                
            except Exception as e:
                print(f"Error processing bet {bet['bet_id']}: {str(e)}")
                continue
        
        # Prepare summary statistics
        summary_stats = {
            'total_bets': len(current_bets),
            'avg_ev': total_ev / valid_ev_count if valid_ev_count > 0 else 0,
            'avg_edge': total_edge / valid_edge_count if valid_edge_count > 0 else 0,
            'time_distribution': time_distribution,
            'sportsbook_distribution': sportsbook_distribution,
            'latest_timestamp': latest_timestamp,
            'grade_distribution': {
                'A': sum(1 for bet in current_bets if bet['grade'] == 'A'),
                'B': sum(1 for bet in current_bets if bet['grade'] == 'B'),
                'C': sum(1 for bet in current_bets if bet['grade'] == 'C'),
                'D': sum(1 for bet in current_bets if bet['grade'] == 'D'),
                'F': sum(1 for bet in current_bets if bet['grade'] == 'F')
            }
        }
        
        # Count sportsbooks by grade
        sportsbook_grade_counts = {}
        for bet in current_bets:
            sportsbook = bet['sportsbook']
            grade = bet['grade']
            if sportsbook:
                if sportsbook not in sportsbook_grade_counts:
                    sportsbook_grade_counts[sportsbook] = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0, 'total': 0}
                if grade in ['A', 'B', 'C', 'D', 'F']:
                    sportsbook_grade_counts[sportsbook][grade] += 1
                    sportsbook_grade_counts[sportsbook]['total'] += 1
        
        return render_template(
            'index.html',
            current_bets=current_bets,
            summary_stats=summary_stats,
            sportsbook_counts=sportsbook_grade_counts
        )

@bp.route('/nba-props')
def nba_props():
    """NBA Props Page: Display NBA player props with stats and predictions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get the latest timestamp
        cursor.execute("SELECT timestamp FROM betting_data ORDER BY timestamp DESC LIMIT 1")
        latest_timestamp = cursor.fetchone()
        
        if not latest_timestamp:
            return render_template('nba_props.html', props=[], summary_stats={'total_props': 0})
        
        latest_timestamp = latest_timestamp[0]
        
        # Get NBA player props
        cursor.execute("""
            SELECT * FROM betting_data 
            WHERE timestamp = ? 
                AND sport_league LIKE '%NBA%'
                AND bet_type LIKE 'Player%'
            ORDER BY ev_percent DESC
        """, (latest_timestamp,))
        nba_props = cursor.fetchall()
        
        # Initialize model predictor
        from app.ml.nba_props import NBAPropsPredictor
        predictor = NBAPropsPredictor()
        
        # Process each prop bet
        processed_props = []
        for prop in nba_props:
            try:
                # Get player stats (assuming this is implemented elsewhere)
                player_stats = {}  # This would need to be implemented
                
                # Calculate market metrics
                odds = float(prop['odds']) if prop['odds'] and prop['odds'] != 'N/A' else 0
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                # Calculate edge
                win_prob = safe_float(prop['win_probability'], '%')
                edge = win_prob - market_implied_prob if market_implied_prob and win_prob else None
                
                # Prepare data for model prediction
                prop_data = {
                    'timestamp': prop['timestamp'],
                    'event_time': prop['event_time'],
                    'ev_percent': safe_float(prop['ev_percent'], '%'),
                    'stats': player_stats
                }
                
                # Get model prediction
                prediction = predictor.predict(prop_data)
                
                # Format prop data
                prop_data = {
                    'bet_id': prop['bet_id'],
                    'player_name': prop['description'].split()[0],  # Simple extraction
                    'stat_type': 'Points' if 'Points' in prop['description'] else 'Other',  # Simple extraction
                    'description': prop['description'],
                    'odds': prop['odds'],
                    'sportsbook': prop['sportsbook'],
                    'ev_percent': safe_float(prop['ev_percent'], '%'),
                    'win_probability': win_prob,
                    'edge': edge,
                    'recommended_bet_size': safe_float(prop['bet_size'], '$'),
                    'stats': player_stats,
                    'model_prediction': prediction
                }
                processed_props.append(prop_data)
                
            except Exception as e:
                print(f"Error processing prop {prop['bet_id']}: {str(e)}")
                continue
        
        # Prepare summary statistics
        summary_stats = {
            'total_props': len(processed_props),
            'latest_timestamp': latest_timestamp,
            'avg_model_confidence': (
                sum(p['model_prediction']['confidence_score'] 
                    for p in processed_props 
                    if p.get('model_prediction')) / len(processed_props)
                if processed_props else 0
            )
        }
        
        return render_template(
            'nba_props.html',
            props=processed_props,
            summary_stats=summary_stats
        )

@bp.route('/guide')
def guide():
    """Display the explainer/guide page."""
    return render_template('explainer.html')

@bp.route('/thirty_day_results')
def thirty_day_results():
    """Display betting opportunities from the last 30 days."""
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = 25
    selected_sport = request.args.get('sport', None)
    show_all_sports = request.args.get('show_all', '0') == '1'
    sort_by = request.args.get('sort', 'timestamp')
    sort_dir = request.args.get('dir', 'desc').lower()
    if sort_dir not in ['asc', 'desc']:
        sort_dir = 'desc'
    
    # Get filter parameters
    grade_filter = request.args.get('grade')
    result_filter = request.args.get('result')
    min_ev_filter = request.args.get('min_ev', type=float)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # First calculate summary stats from complete 30-day data (before filters)
        summary_query = """
            WITH UniqueBets AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY bet_id ORDER BY timestamp DESC) as rn
                FROM betting_data
                WHERE timestamp >= date('now', '-30 days')
            )
            SELECT 
                COUNT(DISTINCT b.bet_id) as total_bets,
                AVG(CAST(REPLACE(REPLACE(b.ev_percent, '%', ''), ',', '') AS FLOAT)) as avg_ev,
                COUNT(DISTINCT CASE WHEN g.grade IN ('A', 'B') THEN b.bet_id END) as grade_a_b_count
            FROM UniqueBets b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
            WHERE b.rn = 1
        """
        cursor.execute(summary_query)
        summary_row = cursor.fetchone()
        
        # Calculate average edge from complete data
        edge_query = """
            WITH UniqueBets AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY bet_id ORDER BY timestamp DESC) as rn
                FROM betting_data
                WHERE timestamp >= date('now', '-30 days')
            )
            SELECT 
                b.odds,
                CAST(REPLACE(REPLACE(b.win_probability, '%', ''), ',', '') AS FLOAT) as win_prob
            FROM UniqueBets b
            WHERE b.rn = 1
        """
        cursor.execute(edge_query)
        edge_rows = cursor.fetchall()
        
        total_edge = 0
        valid_edge_count = 0
        for row in edge_rows:
            try:
                odds = float(row['odds']) if row['odds'] and row['odds'] != 'N/A' else 0
                win_prob = row['win_prob']
                
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                if market_implied_prob is not None and win_prob > 0:
                    edge = win_prob - market_implied_prob
                    total_edge += edge
                    valid_edge_count += 1
            except Exception as e:
                logging.error(f"Error calculating edge: {str(e)}")
                continue
        
        avg_edge = total_edge / valid_edge_count if valid_edge_count > 0 else 0
        
        # Prepare summary statistics (from complete data)
        summary_stats = {
            'total_bets': summary_row['total_bets'],
            'avg_ev': summary_row['avg_ev'] if summary_row['avg_ev'] is not None else 0,
            'avg_edge': avg_edge,
            'grade_a_b_count': summary_row['grade_a_b_count']
        }
        
        # Archive and clean up old data
        cursor.execute("""
            INSERT INTO odds_history_archive (bet_id, close_odds, low_odds, high_odds, recorded_at)
            SELECT bet_id, close_odds, low_odds, high_odds, recorded_at
            FROM odds_history
            WHERE bet_id IN (
                SELECT bet_id 
                FROM betting_data 
                WHERE timestamp < date('now', '-30 days')
            )
        """)
        
        cursor.execute("""
            DELETE FROM odds_history
            WHERE bet_id IN (
                SELECT bet_id 
                FROM betting_data 
                WHERE timestamp < date('now', '-30 days')
            )
        """)
        conn.commit()
        
        # Base query for counting total bets
        count_query = """
            SELECT COUNT(DISTINCT b.bet_id) 
            FROM betting_data b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
            LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
            WHERE b.timestamp >= date('now', '-30 days')
        """
        
        # Base query for fetching bets
        base_query = """
            WITH UniqueBets AS (
                SELECT *
                FROM (
                    SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY bet_id ORDER BY timestamp DESC) as bet_rn
                    FROM betting_data
                    WHERE timestamp >= date('now', '-30 days')
                ) sub
                WHERE bet_rn = 1
            ),
            LatestBets AS (
                SELECT 
                    b.*,
                    g.grade,
                    g.composite_score,
                    oh.close_odds,
                    oh.low_odds,
                    oh.high_odds,
                    boe.outcome as result,
                    boe.confidence_score,
                    bv.status as validation_status,
                    ROW_NUMBER() OVER (PARTITION BY b.bet_id ORDER BY b.timestamp DESC) as rn
                FROM UniqueBets b
                LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
                LEFT JOIN odds_history oh ON b.bet_id = oh.bet_id
                LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
                LEFT JOIN bet_verification bv ON b.bet_id = bv.bet_id
            )
            SELECT * FROM LatestBets WHERE rn = 1"""
        
        # Add filters to both queries
        params = []
        
        # Sport filter
        if selected_sport:
            base_query += " AND sport_league = ?"
            count_query += " AND b.sport_league = ?"
            params.append(selected_sport)
        
        # Grade filter
        if grade_filter:
            base_query += " AND grade = ?"
            count_query += " AND g.grade = ?"
            params.append(grade_filter)
        
        # Result filter
        if result_filter:
            base_query += " AND result = ?"
            count_query += " AND boe.outcome = ?"
            params.append(result_filter)
        
        # Min EV filter
        if min_ev_filter is not None:
            base_query += " AND CAST(REPLACE(REPLACE(ev_percent, '%', ''), ',', '') AS FLOAT) >= ?"
            count_query += " AND CAST(REPLACE(REPLACE(b.ev_percent, '%', ''), ',', '') AS FLOAT) >= ?"
            params.append(min_ev_filter)
        
        # Get total count for pagination
        cursor.execute(count_query, params)
        total_bets = cursor.fetchone()[0]
        total_pages = (total_bets + per_page - 1) // per_page
        
        # Add sorting
        sort_column = {
            'timestamp': 'timestamp',
            'sport': 'sport_league',
            'grade': 'grade',
            'ev': 'ev_percent',
            'composite': 'composite_score',
            'result': 'result'
        }.get(sort_by, 'timestamp')
        
        base_query += f" ORDER BY {sort_column} {sort_dir}"
        base_query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"
        
        # Fetch paginated bets
        cursor.execute(base_query, params)
        raw_bets = cursor.fetchall()
        
        # Get sport distribution
        sport_query = """
            WITH LatestBets AS (
                SELECT bet_id, sport_league, timestamp,
                       ROW_NUMBER() OVER (PARTITION BY bet_id ORDER BY timestamp DESC) as rn
                FROM betting_data
                WHERE timestamp >= date('now', '-30 days')
            )
            SELECT sport_league as name, COUNT(*) as count
            FROM LatestBets
            WHERE rn = 1
            GROUP BY sport_league
            ORDER BY count DESC
        """
        if not show_all_sports:
            sport_query += " LIMIT 8"  # Show only top 8 sports by default
            
        cursor.execute(sport_query)
        sports = [dict(row) for row in cursor.fetchall()]
        
        # Process bets to ensure correct types
        bets = []
        for bet in raw_bets:
            bet_dict = dict(bet)
            
            # Debug logging for result and confidence score
            logging.debug(f"Raw bet data for {bet_dict['bet_id']}:")
            logging.debug(f"Result from query: {bet_dict.get('result')}")
            logging.debug(f"Confidence Score from query: {bet_dict.get('confidence_score')}")
            
            # Convert odds and calculate market probability
            odds = float(bet_dict['odds']) if bet_dict['odds'] and bet_dict['odds'] != 'N/A' else 0
            market_implied_prob = None
            if odds > 0:
                market_implied_prob = round(100 / (odds + 100) * 100, 2)
            elif odds < 0:
                market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
            
            # Log after calculation
            logging.debug(f"Calculated market_implied_prob: {market_implied_prob} for bet: {bet_dict['bet_id']}")
            
            # Ensure market_implied_prob is added to the bet dictionary
            bet_dict['market_implied_prob'] = market_implied_prob if market_implied_prob is not None else 0
            
            # Log final bet dictionary
            logging.debug(f"Final bet dictionary: {bet_dict}")
            
            # Convert win probability and calculate edge
            win_prob = safe_float(bet_dict['win_probability'], '%')
            edge = round(win_prob - market_implied_prob, 2) if market_implied_prob is not None and win_prob > 0 else 0
            
            # Calculate Kelly criterion
            kelly_criterion = None
            if odds and win_prob > 0:
                decimal_odds = (abs(odds) + 100) / 100 if odds > 0 else (100 / abs(odds)) + 1
                kelly_criterion = ((win_prob / 100 * (decimal_odds - 1)) - (1 - win_prob / 100)) / (decimal_odds - 1) * 100
            
            # Convert timestamp
            timestamp = parse_datetime(bet_dict['timestamp'])
            
            # Update the bet dictionary with calculated values
            bet_dict.update({
                'odds': odds,
                'ev_percent': safe_float(bet_dict['ev_percent'], '%'),
                'win_probability': win_prob,
                'edge': edge,
                'kelly_criterion': kelly_criterion,
                'timestamp': timestamp,
                'grade': bet_dict.get('grade', 'F'),  # Default to F if no grade
                'result': bet_dict.get('result'),  # Get result directly from bet_outcome_evaluation
                'confidence_score': bet_dict.get('confidence_score'),  # Get confidence score directly from bet_outcome_evaluation
                'validation_status': bet_dict.get('validation_status', 'NO')
            })
            
            bets.append(bet_dict)
        
        # Prepare pagination info
        pagination = {
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_items': total_bets
        }
        
        return render_template(
            'thirty_day_results.html',
            bets=bets,
            sports=sports,
            pagination=pagination,
            selected_sport=selected_sport,
            show_all_sports=show_all_sports,
            sort_by=sort_by,
            sort_dir=sort_dir,
            max=max,  # Pass the max function to the template
            min=min,  # Pass the min function to the template
            summary_stats=summary_stats  # Pass summary statistics to the template
        )

@bp.route('/api/sportsbook_bets/<sportsbook>')
def get_sportsbook_bets(sportsbook):
    """Get all active bets for a specific sportsbook."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # First get the latest timestamp
            cursor.execute("SELECT timestamp FROM betting_data ORDER BY timestamp DESC LIMIT 1")
            latest_timestamp = cursor.fetchone()[0]
            
            # Then get bets for this sportsbook from the latest timestamp only
            cursor.execute("""
                SELECT b.*, g.grade, g.composite_score, g.ev_score, g.timing_score, g.historical_edge
                FROM betting_data b
                LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
                LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
                WHERE b.sportsbook = ? 
                AND b.timestamp = ?
                AND (boe.outcome IS NULL OR boe.outcome = 'UNCERTAIN')
                AND g.grade IN ('A', 'B', 'C')
                ORDER BY g.grade ASC, b.timestamp DESC
            """, (sportsbook, latest_timestamp))
            
            # Convert rows to dictionaries with proper type conversion
            bets = []
            for row in cursor.fetchall():
                bet_dict = dict(row)
                
                # Convert odds and calculate market probability
                odds = float(bet_dict['odds']) if bet_dict['odds'] and bet_dict['odds'] != 'N/A' else 0
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                # Calculate market implied probability
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                # Ensure market_implied_prob is added to the bet dictionary
                bet_dict['market_implied_prob'] = market_implied_prob if market_implied_prob is not None else 0
                
                # Convert win probability and calculate edge
                win_prob = safe_float(bet_dict['win_probability'], '%')
                edge = round(win_prob - market_implied_prob, 2) if market_implied_prob is not None and win_prob > 0 else 0
                
                # Update the bet dictionary with calculated values
                bet_dict.update({
                    'odds': odds,
                    'ev_percent': safe_float(bet_dict['ev_percent'], '%'),
                    'win_probability': win_prob,
                    'edge': edge
                })
                
                bets.append(bet_dict)
            
            return jsonify(bets)
    except Exception as e:
        logging.error(f"Error fetching sportsbook bets: {str(e)}")
        return jsonify({'error': 'Error loading bets. Please try again.'}), 500

@bp.route('/api/calculate_parlay', methods=['POST'])
def calculate_parlay():
    def round_bet_size(amount):
        """Round bet size down to nearest multiple of 5 (or 1 if less than $5)."""
        if amount < 5:
            return max(1, int(amount))  # Round down to nearest dollar, minimum $1
        return (int(amount) // 5) * 5  # Round down to nearest multiple of 5
    
    def calculate_parlay_grade(ev_percent, edge_percent, kelly_criterion):
        """
        Calculate grade for parlay based on composite score using same metrics as individual bets.
        """
        # Calculate component scores
        # EV Score: Normalize EV to 0-100 scale (same as individual bets)
        ev_score = max(0, min(100, (ev_percent + 10) * 5))
        
        # Edge Score: Normalize edge to 0-100 scale (same as individual bets)
        edge_score = max(0, min(100, (edge_percent + 10) * 5))
        
        # Kelly Score: Normalize kelly to 0-100 scale (same as individual bets)
        kelly_score = max(0, min(100, (kelly_criterion + 0.1) * 500))
        
        # Calculate composite score (equal weighting)
        composite_score = (ev_score + edge_score + kelly_score) / 3
        
        # Assign grade based on composite score (same thresholds as individual bets)
        if composite_score >= 90:
            return 'A'
        elif composite_score >= 80:
            return 'B'
        elif composite_score >= 70:
            return 'C'
        elif composite_score >= 60:
            return 'D'
        else:
            return 'F'

    data = request.get_json()
    bet_ids = data.get('bet_ids', [])
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetch bet data with grades
        bets = []
        for bet_id in bet_ids:
            cursor.execute("""
                SELECT b.*, g.grade
                FROM betting_data b
                LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
                WHERE b.bet_id = ?
            """, (bet_id,))
            bet = cursor.fetchone()
            if bet:
                bets.append(dict(bet))
    
    if not bets:
        return jsonify({'error': 'No valid bets found'}), 400
    
    try:
        # Calculate parlay metrics using true probabilities
        parlay_result = ParlayUtils.compute_parlay_odds(bets)
        
        # Calculate combined market probability
        combined_market_prob = 1.0
        for bet in bets:
            odds = float(bet['odds']) if bet['odds'] and bet['odds'] != 'N/A' else 0
            # Calculate market implied probability
            if odds > 0:
                market_prob = 1 / (1 + (odds / 100))
            elif odds < 0:
                market_prob = abs(odds) / (abs(odds) + 100)
            else:
                market_prob = 0
            
            if market_prob > 0:
                combined_market_prob *= market_prob
        
        # Calculate theoretical market odds
        theoretical_market_decimal_odds = 1 / combined_market_prob if combined_market_prob > 0 else float('inf')
        theoretical_market_american_odds = ParlayUtils.decimal_to_american(theoretical_market_decimal_odds)
        
        # Calculate parlay edge
        parlay_market_edge = parlay_result.true_win_prob - combined_market_prob
        
        # Calculate EV using true probability and market odds
        payout_if_win = theoretical_market_decimal_odds - 1  # Subtract 1 to get net profit
        ev_percent = (parlay_result.true_win_prob * payout_if_win - (1 - parlay_result.true_win_prob)) * 100
        
        # Calculate recommended bet size based on individual bet sizes
        individual_bet_sizes = [safe_float(bet.get('bet_size', 0), '$') for bet in bets]
        min_bet_size = min(individual_bet_sizes) if individual_bet_sizes else 0
        
        # Scale down the bet size based on number of legs and edge
        scaling_factor = 0.5 ** (len(bets) - 1)  # Each additional leg reduces size by half
        edge_multiplier = 1 + (parlay_market_edge if parlay_market_edge > 0 else -0.5)
        
        parlay_bet_size = min_bet_size * scaling_factor * edge_multiplier
        parlay_bet_size = round_bet_size(parlay_bet_size)
        
        # Calculate Kelly criterion for parlay
        parlay_kelly = ((parlay_result.true_win_prob * (theoretical_market_decimal_odds - 1)) - (1 - parlay_result.true_win_prob)) / (theoretical_market_decimal_odds - 1)
        
        # Calculate parlay grade using new method
        parlay_grade = calculate_parlay_grade(
            ev_percent=ev_percent,
            edge_percent=parlay_market_edge * 100,
            kelly_criterion=parlay_kelly
        )
        
        # Generate insights
        insights = []
        parlay_odds_rounded = round(parlay_result.american_odds)
        theoretical_odds_rounded = round(theoretical_market_american_odds)
        
        # Add grade insight first
        insights.append(f"Parlay Grade: {parlay_grade} (based on {ev_percent:.1f}% EV, {(parlay_market_edge * 100):.1f}% edge, {(parlay_result.true_win_prob * 100):.1f}% win probability)")
        
        if parlay_odds_rounded < theoretical_odds_rounded:
            insights.append(f"✅ Our true parlay odds of +{parlay_odds_rounded} are better than market odds of +{theoretical_odds_rounded}")
            insights.append("This means we think the parlay is more likely to win than the market suggests")
        elif parlay_odds_rounded > theoretical_odds_rounded:
            insights.append(f"⚠️ Our true parlay odds of +{parlay_odds_rounded} are worse than market odds of +{theoretical_odds_rounded}")
            insights.append("This suggests the parlay might not be as valuable as the individual bets")
        
        if parlay_market_edge > 0:
            insights.append(f"Parlay has a {(parlay_market_edge * 100):.2f}% edge over market probability")
        
        # Add EV insight
        if ev_percent > 0:
            insights.append(f"Positive expected value of {ev_percent:.2f}% on this parlay")
        
        # Add bet size explanation with grade context
        if parlay_grade in ['A', 'B']:
            insights.append("Recommended bet size factors in strong parlay metrics")
        else:
            insights.append("Recommended bet size is reduced due to increased risk and moderate metrics")
        
        return jsonify({
            'parlay_metrics': {
                'american_odds': parlay_result.american_odds,
                'true_probability': parlay_result.true_win_prob,
                'ev_percent': ev_percent,
                'edge_percent': parlay_market_edge * 100,
                'correlated_warning': parlay_result.correlated_warning,
                'grade': parlay_grade
            },
            'comparison': {
                'theoretical_combined_odds': theoretical_market_american_odds,
                'recommended_parlay_size': parlay_bet_size,
                'edge_percent': parlay_market_edge * 100
            },
            'insights': insights
        })
    except Exception as e:
        logging.error(f"Error calculating parlay: {str(e)}")  # Log the error
        return jsonify({'error': 'An internal error has occurred.'}), 500 

@bp.route('/api/verify_bet', methods=['POST'])
def verify_bet():
    """Update validation status for a bet."""
    try:
        data = request.get_json()
        bet_id = data.get('bet_id')
        status = data.get('status', 'NO')
        
        if not bet_id:
            return jsonify({'error': 'No bet_id provided'}), 400
            
        if status not in ['PASS', 'FAIL', 'NO']:
            return jsonify({'error': 'Invalid status'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'NO':
                # Remove validation
                cursor.execute("""
                    DELETE FROM bet_verification
                    WHERE bet_id = ?
                """, (bet_id,))
            else:
                # Update validation status
                cursor.execute("""
                    INSERT OR REPLACE INTO bet_verification (bet_id, status, verified_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (bet_id, status))
                
            conn.commit()
            
            return jsonify({'success': True, 'status': status})
            
    except Exception as e:
        logging.error(f"Error updating validation status: {str(e)}")
        return jsonify({'error': 'Error updating validation status'}), 500 

@bp.route('/api/bet_details/<bet_id>')
def get_bet_details(bet_id):
    """Get detailed information about a specific bet."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get bet details with all related information
            cursor.execute("""
                SELECT b.*, g.grade, g.composite_score,
                       boe.outcome as result,
                       boe.confidence_score,
                       boe.reasoning,
                       bv.status as validation_status
                FROM betting_data b
                LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
                LEFT JOIN bet_outcome_evaluation boe ON b.bet_id = boe.bet_id
                LEFT JOIN bet_verification bv ON b.bet_id = bv.bet_id
                WHERE b.bet_id = ?
            """, (bet_id,))
            
            bet = cursor.fetchone()
            if not bet:
                return jsonify({'error': 'Bet not found'}), 404
            
            bet_dict = dict(bet)
            
            # Calculate market metrics
            odds = float(bet_dict['odds']) if bet_dict['odds'] and bet_dict['odds'] != 'N/A' else 0
            market_implied_prob = None
            if odds > 0:
                market_implied_prob = round(100 / (odds + 100) * 100, 2)
            elif odds < 0:
                market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
            
            # Calculate edge and other metrics
            win_prob = safe_float(bet_dict['win_probability'], '%')
            edge = round(win_prob - market_implied_prob, 2) if market_implied_prob is not None and win_prob > 0 else 0
            
            # Calculate Kelly criterion
            kelly_criterion = None
            if odds and win_prob > 0:
                decimal_odds = (abs(odds) + 100) / 100 if odds > 0 else (100 / abs(odds)) + 1
                kelly_criterion = ((win_prob / 100 * (decimal_odds - 1)) - (1 - win_prob / 100)) / (decimal_odds - 1) * 100
            
            # Get odds history
            cursor.execute("""
                SELECT oh.*, b.sportsbook,
                       b.ev_percent, b.win_probability,
                       CAST((CAST(b.win_probability AS FLOAT) - 
                            CASE 
                                WHEN oh.close_odds > 0 THEN 100.0 / (oh.close_odds + 100.0) * 100.0
                                ELSE ABS(oh.close_odds) / (ABS(oh.close_odds) + 100.0) * 100.0
                            END) AS FLOAT) as edge
                FROM odds_history oh
                LEFT JOIN betting_data b ON oh.bet_id = b.bet_id
                WHERE oh.bet_id = ?
                ORDER BY oh.recorded_at DESC
            """, (bet_id,))
            
            odds_history = []
            for row in cursor.fetchall():
                history_dict = dict(row)
                odds_history.append({
                    'recorded_at': history_dict['recorded_at'],
                    'odds': history_dict['close_odds'],
                    'sportsbook': history_dict['sportsbook'],
                    'ev_percent': safe_float(history_dict['ev_percent'], '%'),
                    'edge': safe_float(history_dict['edge'], '%')
                })
            
            return jsonify({
                'bet_id': bet_dict['bet_id'],
                'event_teams': bet_dict['event_teams'],
                'sport_league': bet_dict['sport_league'],
                'bet_type': bet_dict['bet_type'],
                'description': bet_dict['description'],
                'odds': odds,
                'grade': bet_dict.get('grade'),
                'result': bet_dict.get('result'),
                'ev_percent': safe_float(bet_dict['ev_percent'], '%'),
                'win_probability': win_prob,
                'edge': edge,
                'kelly_criterion': kelly_criterion,
                'confidence_score': bet_dict.get('confidence_score'),
                'reasoning': bet_dict.get('reasoning'),
                'validation_status': bet_dict.get('validation_status', 'NO'),
                'odds_history': odds_history
            })
            
    except Exception as e:
        logging.error(f"Error fetching bet details: {str(e)}")
        return jsonify({'error': 'Error loading bet details'}), 500 

@bp.route('/api/mark_bet', methods=['POST'])
def mark_bet():
    """Mark a bet as already bet or remove the mark."""
    try:
        data = request.get_json()
        bet_id = data.get('bet_id')
        is_already_bet = data.get('is_already_bet', False)
        
        if not bet_id:
            return jsonify({'error': 'No bet_id provided'}), 400
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if is_already_bet:
                # Mark as already bet
                cursor.execute("""
                    INSERT OR IGNORE INTO already_bet (bet_id, marked_at)
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (bet_id,))
            else:
                # Remove already bet mark
                cursor.execute("""
                    DELETE FROM already_bet
                    WHERE bet_id = ?
                """, (bet_id,))
                
            conn.commit()
            
            return jsonify({'success': True, 'is_already_bet': is_already_bet})
            
    except Exception as e:
        logging.error(f"Error marking bet: {str(e)}")
        return jsonify({'error': 'Error marking bet'}), 500 