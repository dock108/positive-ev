from flask import render_template, request
from app.main import bp
from app.db_utils import get_db_connection
from datetime import datetime
import logging
import sqlite3

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
            return render_template('index.html', current_bets=[], summary_stats={'total_bets': 0})
        
        latest_timestamp = latest_timestamp[0]
        
        # Get all bets from the latest timestamp
        cursor.execute("""
            SELECT b.*, g.grade, g.composite_score, g.ev_score, g.timing_score, g.historical_edge
            FROM betting_data b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
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
                edge = win_prob - market_implied_prob if market_implied_prob and win_prob else None
                
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
                    'win_probability': win_prob,
                    'market_implied_prob': market_implied_prob,
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
                    'kelly_percentile': None
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
        
        return render_template(
            'index.html',
            current_bets=current_bets,
            summary_stats=summary_stats
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
    """Guide Page: Display explanations of metrics and calculations."""
    return render_template('explainer.html')

@bp.route('/thirty_day_results')
def thirty_day_results():
    """Display betting opportunities from the last 30 days."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        cursor = conn.cursor()
        
        # Base query for unique bets in last 30 days
        latest_bets_subquery = """
            SELECT DISTINCT b.*, g.grade, g.composite_score, g.ev_score, g.timing_score, g.historical_edge
            FROM betting_data b
            LEFT JOIN bet_grades g ON b.bet_id = g.bet_id
            INNER JOIN (
                SELECT bet_id, MAX(timestamp) as max_timestamp
                FROM betting_data
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY bet_id
            ) latest ON b.bet_id = latest.bet_id AND b.timestamp = latest.max_timestamp
            WHERE b.timestamp >= date('now', '-30 days')
        """
        
        logging.debug("Executing summary statistics query for unique bets")
        # Get summary statistics for unique bets in last 30 days
        cursor.execute(f"""
            WITH UniqueBets AS (
                {latest_bets_subquery}
            )
            SELECT 
                COUNT(DISTINCT bet_id) as total_unique_bets,
                AVG(CAST(ev_percent AS FLOAT)) as avg_ev,
                AVG(CAST(win_probability AS FLOAT) - (
                    CASE 
                        WHEN CAST(odds AS FLOAT) > 0 THEN 100 / (CAST(odds AS FLOAT) + 100) * 100
                        ELSE ABS(CAST(odds AS FLOAT)) / (ABS(CAST(odds AS FLOAT)) + 100) * 100
                    END
                )) as avg_edge,
                SUM(CASE WHEN grade = 'A' THEN 1 ELSE 0 END) as grade_a_count,
                SUM(CASE WHEN grade = 'B' THEN 1 ELSE 0 END) as grade_b_count,
                SUM(CASE WHEN grade = 'C' THEN 1 ELSE 0 END) as grade_c_count,
                SUM(CASE WHEN grade = 'D' THEN 1 ELSE 0 END) as grade_d_count,
                SUM(CASE WHEN grade = 'F' THEN 1 ELSE 0 END) as grade_f_count
            FROM UniqueBets
        """)
        overall_stats = dict(cursor.fetchone())
        logging.debug(f"Overall Stats: {overall_stats}")
        print(f"Overall Stats: {overall_stats}")
        
        logging.debug("Executing sport-specific statistics query for unique bets")
        # Get sport-specific statistics for unique bets
        cursor.execute(f"""
            WITH UniqueBets AS (
                {latest_bets_subquery}
            )
            SELECT 
                sport_league,
                COUNT(DISTINCT bet_id) as unique_bet_count,
                AVG(CAST(ev_percent AS FLOAT)) as avg_ev,
                AVG(CAST(win_probability AS FLOAT) - (
                    CASE 
                        WHEN CAST(odds AS FLOAT) > 0 THEN 100 / (CAST(odds AS FLOAT) + 100) * 100
                        ELSE ABS(CAST(odds AS FLOAT)) / (ABS(CAST(odds AS FLOAT)) + 100) * 100
                    END
                )) as avg_edge,
                COUNT(CASE WHEN grade = 'A' THEN 1 END) as grade_a_count,
                COUNT(CASE WHEN grade = 'B' THEN 1 END) as grade_b_count
            FROM UniqueBets
            GROUP BY sport_league
            ORDER BY unique_bet_count DESC
        """)
        sport_stats = [dict(row) for row in cursor.fetchall()]
        logging.debug(f"Sport Stats: {sport_stats}")
        print(f"Sport Stats: {sport_stats}")
        
        # Get total unique opportunities (timestamps) in last 30 days
        cursor.execute("""
            SELECT COUNT(DISTINCT timestamp) 
            FROM betting_data 
            WHERE timestamp >= date('now', '-30 days')
        """)
        total_opportunities = cursor.fetchone()[0]
        
        # Prepare summary statistics with default values to avoid IndexError
        summary_stats = {
            'total_bets': overall_stats.get('total_unique_bets', 0),
            'total_opportunities': total_opportunities,
            'avg_ev': round(overall_stats.get('avg_ev', 0), 1),
            'avg_edge': round(overall_stats.get('avg_edge', 0), 1),
            'grade_distribution': {
                'A': overall_stats.get('grade_a_count', 0),
                'B': overall_stats.get('grade_b_count', 0),
                'C': overall_stats.get('grade_c_count', 0),
                'D': overall_stats.get('grade_d_count', 0),
                'F': overall_stats.get('grade_f_count', 0)
            }
        }
        
        # Organize sports into qualifying and other with their stats, using default values
        qualifying_sports = {
            row['sport_league']: {
                'count': row.get('unique_bet_count', 0),
                'avg_ev': round(row.get('avg_ev', 0), 1),
                'avg_edge': round(row.get('avg_edge', 0), 1),
                'grade_a_count': row.get('grade_a_count', 0),
                'grade_b_count': row.get('grade_b_count', 0)
            }
            for row in sport_stats if row.get('unique_bet_count', 0) >= 50
        }
        other_sports = {
            row['sport_league']: {
                'count': row.get('unique_bet_count', 0),
                'avg_ev': round(row.get('avg_ev', 0), 1),
                'avg_edge': round(row.get('avg_edge', 0), 1),
                'grade_a_count': row.get('grade_a_count', 0),
                'grade_b_count': row.get('grade_b_count', 0)
            }
            for row in sport_stats if row.get('unique_bet_count', 0) < 50
        }

        print(f"Summary Stats: {summary_stats}")
        print(f"Qualifying Sports: {qualifying_sports}")
        print(f"Other Sports: {other_sports}")

        # Get page parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        show_all_sports = request.args.get('show_all', '0') == '1'
        selected_sport = request.args.get('sport', None)
        sort_by = request.args.get('sort', 'timestamp')
        sort_dir = request.args.get('dir', 'desc')
        
        # Build the base query for paginated results
        base_query = latest_bets_subquery
        
        params = []
        
        # Add sport filter if applicable
        if selected_sport:
            base_query += " AND sport_league = ?"
            params.append(selected_sport)
        elif not show_all_sports:
            base_query += " AND sport_league IN ({})".format(
                ','.join('?' * len(qualifying_sports))
            )
            params.extend(qualifying_sports.keys())
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Add sorting and pagination
        sort_column = {
            'timestamp': 'timestamp',
            'sport': 'sport_league',
            'grade': 'grade',
            'ev': 'ev_percent',
            'composite': 'composite_score'
        }.get(sort_by, 'timestamp')
        
        query = f"{base_query} ORDER BY {sort_column} {sort_dir} LIMIT ? OFFSET ?"
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        historical_bets = cursor.fetchall()
        
        if not historical_bets:
            return render_template(
                'thirty_day_results.html',
                bets=[],
                summary_stats={'total_bets': 0, 'total_opportunities': 0},
                qualifying_sports={},
                other_sports={},
                pagination={'current_page': 1, 'total_pages': 1})
        
        # Convert sqlite3.Row objects to dictionaries
        historical_bets = [dict(bet) for bet in historical_bets]

        # Process bets and calculate summary statistics
        processed_bets = []
        total_ev = 0
        total_edge = 0
        valid_ev_count = 0
        valid_edge_count = 0
        grade_distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

        def calculate_percentile(value, values):
            if not values or value is None:
                return None
            values.sort()
            return (sum(v < value for v in values) / len(values)) * 100
        
        for bet in historical_bets:
            try:
                # Calculate market metrics
                odds = float(bet.get('odds', 0)) if bet.get('odds') and bet['odds'] != 'N/A' else 0
                market_implied_prob = None
                if odds > 0:
                    market_implied_prob = round(100 / (odds + 100) * 100, 2)
                elif odds < 0:
                    market_implied_prob = round(abs(odds) / (abs(odds) + 100) * 100, 2)
                
                # Calculate metrics
                ev_percent = safe_float(bet.get('ev_percent', 0), '%')
                win_prob = safe_float(bet.get('win_probability', 0), '%')
                edge = win_prob - market_implied_prob if market_implied_prob and win_prob else None
                
                # Calculate Kelly criterion
                kelly_criterion = None
                if odds and win_prob:
                    decimal_odds = (abs(odds) + 100) / 100 if odds > 0 else (100 / abs(odds)) + 1
                    kelly_criterion = ((win_prob / 100 * (decimal_odds - 1)) - (1 - win_prob / 100)) / (decimal_odds - 1) * 100
                
                # Parse timestamp
                timestamp = parse_datetime(bet.get('timestamp'))
                
                # Update summary statistics
                if ev_percent:
                    total_ev += ev_percent
                    valid_ev_count += 1
                if edge:
                    total_edge += edge
                    valid_edge_count += 1
                
                # Update grade distribution
                if bet.get('grade'):
                    grade_distribution[bet['grade']] = grade_distribution.get(bet['grade'], 0) + 1
                
                # Initialize all expected keys with default values
                bet_data = {
                    'bet_id': bet.get('bet_id'),
                    'sport_league': bet.get('sport_league'),
                    'bet_type': bet.get('bet_type'),
                    'description': bet.get('description'),
                    'odds': bet.get('odds', 0),
                    'sportsbook': bet.get('sportsbook'),
                    'ev_percent': ev_percent,
                    'win_probability': win_prob,
                    'edge': edge,
                    'kelly_criterion': kelly_criterion,
                    'grade': bet.get('grade', 'N/A'),
                    'composite_score': bet.get('composite_score', 0),
                    'timestamp': timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A',
                    'ev_score': round(bet.get('ev_score', 0), 1),
                    'timing_score': round(bet.get('timing_score', 0), 1),
                    'historical_edge': round(bet.get('historical_edge', 0), 1),
                    'ev_percentile': None,
                    'edge_percentile': None,
                    'kelly_percentile': None
                }
                processed_bets.append(bet_data)
                
            except Exception as e:
                print(f"Error processing bet {bet['bet_id']}: {str(e)}")
                continue

        # Calculate percentiles after all bets are processed
        ev_values = [bet['ev_percent'] for bet in processed_bets if bet['ev_percent'] is not None]
        edge_values = [bet['edge'] for bet in processed_bets if bet['edge'] is not None]
        kelly_values = [bet['kelly_criterion'] for bet in processed_bets if bet['kelly_criterion'] is not None]

        # Update percentiles in processed bets
        for bet in processed_bets:
            bet['ev_percentile'] = calculate_percentile(bet['ev_percent'], ev_values)
            bet['edge_percentile'] = calculate_percentile(bet['edge'], edge_values)
            bet['kelly_percentile'] = calculate_percentile(bet['kelly_criterion'], kelly_values)
        
        # Prepare pagination info
        pagination = {
            'current_page': page,
            'total_pages': total_pages,
            'per_page': per_page,
            'total_count': total_count
        }
        
        return render_template(
            'thirty_day_results.html',
            bets=processed_bets,
            summary_stats=summary_stats,
            qualifying_sports=qualifying_sports,
            other_sports=other_sports,
            pagination=pagination,
            show_all_sports=show_all_sports,
            selected_sport=selected_sport,
            sort_by=sort_by,
            sort_dir=sort_dir,
            min=min,
            max=max
        ) 