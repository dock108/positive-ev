from typing import Dict, Any, List, Optional
import logging
from .db import (save_chat_message, get_chat_history, check_timeout, record_violation,
                 get_db, get_user_preferences, update_user_preference, detect_preference_in_query)
from .utils import get_timestamp_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_query(user_id: int, session_id: str, query: str) -> Dict[str, Any]:
    """
    Process a user query and generate a response.
    
    Args:
        user_id: The ID of the user making the query
        session_id: The session ID for the conversation
        query: The user's query text
        
    Returns:
        A dictionary containing the response and metadata
    """
    # Log the incoming query for debugging
    logger.info(f"Processing query from user_id {user_id}, session {session_id}: '{query}'")
    
    # Check for timestamp command
    cleaned_query = query.strip().lower()
    if cleaned_query == "!timestamps":
        logger.info(f"Timestamp command detected from user_id {user_id}")
        response = get_timestamp_info()
        save_chat_message(user_id, session_id, response, "assistant")
        return {
            "response": response,
            "is_timed_out": False,
            "is_violation": False,
            "recommendation_count": 0,
            "session_id": session_id
        }
    
    # Check for preference setting
    if cleaned_query.startswith("set preference") or "i prefer" in cleaned_query or "my favorite" in cleaned_query:
        # Detect preferences in the query
        preferences = detect_preference_in_query(query)
        
        if preferences['has_preference']:
            updates = []
            
            if preferences['sportsbook']:
                success = update_user_preference(user_id, 'sportsbooks', preferences['sportsbook'])
                if success:
                    updates.append(f"sportsbook: {preferences['sportsbook']}")
            
            if preferences['sport']:
                success = update_user_preference(user_id, 'sports', preferences['sport'])
                if success:
                    updates.append(f"sport: {preferences['sport']}")
            
            if preferences['bet_type']:
                success = update_user_preference(user_id, 'bet_types', preferences['bet_type'])
                if success:
                    updates.append(f"bet type: {preferences['bet_type']}")
            
            if updates:
                response = f"I've updated your preferences for {', '.join(updates)}. I'll prioritize these in future recommendations."
                save_chat_message(user_id, session_id, response, "assistant")
                return {
                    "response": response,
                    "is_timed_out": False,
                    "is_violation": False,
                    "recommendation_count": 0,
                    "session_id": session_id
                }
    
    # Check if user is asking about their preferences
    if "my preferences" in cleaned_query or "what are my preferences" in cleaned_query or "show my preferences" in cleaned_query:
        preferences = get_user_preferences(user_id)
        
        response = "Here are your current preferences:\n\n"
        
        if preferences['preferred_sportsbooks']:
            response += f"**Preferred Sportsbooks**: {', '.join(preferences['preferred_sportsbooks'])}\n"
        else:
            response += "**Preferred Sportsbooks**: None set\n"
            
        if preferences['preferred_sports']:
            response += f"**Preferred Sports**: {', '.join(preferences['preferred_sports'])}\n"
        else:
            response += "**Preferred Sports**: None set\n"
            
        if preferences['preferred_leagues']:
            response += f"**Preferred Leagues**: {', '.join(preferences['preferred_leagues'])}\n"
        else:
            response += "**Preferred Leagues**: None set\n"
            
        if preferences['preferred_bet_types']:
            response += f"**Preferred Bet Types**: {', '.join(preferences['preferred_bet_types'])}\n"
        else:
            response += "**Preferred Bet Types**: None set\n"
            
        response += "\nYou can update these by saying something like 'I prefer DraftKings' or 'My favorite sport is basketball'."
        
        save_chat_message(user_id, session_id, response, "assistant")
        return {
            "response": response,
            "is_timed_out": False,
            "is_violation": False,
            "recommendation_count": 0,
            "session_id": session_id
        }
    
    # Check if user is in timeout
    try:
        timeout_info = check_timeout(user_id)
        if timeout_info and timeout_info.get("is_timed_out", False):
            remaining_time = timeout_info.get("remaining_seconds", 0)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            response = f"You are currently in timeout for {minutes} minutes and {seconds} seconds due to a previous violation of our guidelines."
            save_chat_message(user_id, session_id, response, "assistant")
            return {
                "response": response,
                "is_timed_out": True,
                "is_violation": False,
                "recommendation_count": 0,
                "session_id": session_id
            }
    except Exception as e:
        logger.error(f"Error checking timeout: {str(e)}")
        # Continue processing if timeout check fails
    
    # Check for violations
    try:
        is_violation = check_for_violation(query)
        if is_violation:
            record_violation(user_id)
            response = "Your message appears to violate our guidelines. Please refrain from using offensive language or discussing prohibited topics."
            save_chat_message(user_id, session_id, response, "assistant")
            return {
                "response": response,
                "is_timed_out": False,
                "is_violation": True,
                "recommendation_count": 0,
                "session_id": session_id
            }
    except Exception as e:
        logger.error(f"Error checking for violations: {str(e)}")
        # Continue processing if violation check fails
    
    try:
        # Get user preferences to enhance recommendations
        user_preferences = get_user_preferences(user_id)
        
        # Get betting recommendations
        recommendations = []
        try:
            recommendations = get_bet_recommendations(query)
            logger.info(f"Found {len(recommendations)} recommendations")
        except Exception as e:
            logger.error(f"Error getting bet recommendations: {str(e)}")
        
        # Get historical betting data only if no current recommendations are found
        historical_bets = []
        historical_context = ""
        if not recommendations:
            try:
                # Only check for historical data if we don't have current recommendations
                historical_bets = get_historical_bets(query)
                if historical_bets:
                    historical_context = format_bets_for_gpt(historical_bets, "Historical Betting Data (Last 24 Hours)")
                    logger.info(f"Found {len(historical_bets)} historical bets for context")
            except Exception as e:
                logger.error(f"Error getting historical bets: {str(e)}")
        
        # Get recent context bets
        recent_context = ""
        if recommendations:
            try:
                recent_context = format_bets_for_gpt(recommendations, "Recent Betting Recommendations")
            except Exception as e:
                logger.error(f"Error formatting recommendations: {str(e)}")
        
        # Combine contexts
        betting_context = ""
        if historical_context:
            betting_context += historical_context + "\n\n"
        if recent_context:
            betting_context += recent_context
        
        # Add user preferences to the context
        preferences_context = ""
        if user_preferences['preferred_sportsbooks'] or user_preferences['preferred_sports'] or user_preferences['preferred_bet_types']:
            preferences_context = "User Preferences:\n"
            if user_preferences['preferred_sportsbooks']:
                preferences_context += f"- Preferred Sportsbooks: {', '.join(user_preferences['preferred_sportsbooks'])}\n"
            if user_preferences['preferred_sports']:
                preferences_context += f"- Preferred Sports: {', '.join(user_preferences['preferred_sports'])}\n"
            if user_preferences['preferred_bet_types']:
                preferences_context += f"- Preferred Bet Types: {', '.join(user_preferences['preferred_bet_types'])}\n"
            
            if betting_context:
                betting_context += "\n\n" + preferences_context
            else:
                betting_context = preferences_context
        
        # Get chat history
        history = []
        try:
            history = get_chat_history(user_id, session_id, limit=5)
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
        
        # Generate response
        response = ""
        
        # If we have historical data but no current recommendations, add a note about line movement
        if historical_bets and not recommendations:
            # Extract information from the most recent historical bet
            recent_bet = historical_bets[0]
            sportsbook = recent_bet.get('sportsbook', 'a sportsbook')
            description = recent_bet.get('description', 'this bet')
            odds = recent_bet.get('odds', 'favorable odds')
            timestamp = recent_bet.get('timestamp', 'earlier')
            
            # Add a note about line movement to the beginning of the context
            line_movement_note = f"NOTE TO ASSISTANT: {sportsbook} had {description} available at {odds} on {timestamp}, but the line has likely moved or is no longer available at the same price. Don't provide this specific recommendation, but mention that lines were available earlier and suggest the user check for similar opportunities. For example, if this was about LeBron James props, suggest checking other Lakers players' props or similar markets."
            
            if betting_context:
                betting_context = line_movement_note + "\n\n" + betting_context
            else:
                betting_context = line_movement_note
        
        # If we have no historical data and no recommendations, add a hint note
        elif not historical_bets and not recommendations:
            # Get the most recent timestamp from the database to ensure we're providing current hints
            try:
                conn = get_db()
                cursor = conn.execute("SELECT MAX(timestamp) as latest FROM betting_data")
                result = cursor.fetchone()
                latest_timestamp = result['latest'] if result else None
                
                if latest_timestamp:
                    logger.info(f"Most recent betting data timestamp: {latest_timestamp}")
                    
                    # Try to get some recent betting data to use as hints
                    cursor = conn.execute(
                        """
                        SELECT 
                            id, 
                            description, 
                            sportsbook, 
                            odds, 
                            ev_percent, 
                            win_probability,
                            sport,
                            league
                        FROM betting_data 
                        WHERE timestamp = ? 
                        ORDER BY CAST(REPLACE(ev_percent, '%', '') AS REAL) DESC 
                        LIMIT 3
                        """, 
                        (latest_timestamp,)
                    )
                    
                    recent_bets = cursor.fetchall()
                    if recent_bets:
                        # Extract some information from the recent bets to use as hints
                        recent_bet = recent_bets[0]
                        sport = recent_bet.get('sport', 'basketball')
                        league = recent_bet.get('league', 'NBA')
                        sportsbook = recent_bet.get('sportsbook', 'a major sportsbook')
                        
                        logger.info(f"Found recent bets for hints: {sport}, {league}, {sportsbook}")
            except Exception as e:
                logger.error(f"Error getting recent timestamp: {str(e)}")
                sport = "basketball"
                league = "NBA"
                sportsbook = "a major sportsbook"
            
            # Extract potential player or team names from the query
            query_lower = query.lower()
            
            # Check for common player names
            player_hint = None
            team_hint = None
            
            common_players = {
                "lebron": ("LeBron James", "Lakers", "Anthony Davis"),
                "curry": ("Stephen Curry", "Warriors", "Klay Thompson"),
                "giannis": ("Giannis Antetokounmpo", "Bucks", "Damian Lillard"),
                "jokic": ("Nikola Jokić", "Nuggets", "Jamal Murray"),
                "embiid": ("Joel Embiid", "76ers", "Tyrese Maxey"),
                "doncic": ("Luka Dončić", "Mavericks", "Kyrie Irving"),
                "tatum": ("Jayson Tatum", "Celtics", "Jaylen Brown"),
                "durant": ("Kevin Durant", "Suns", "Devin Booker"),
                "morant": ("Ja Morant", "Grizzlies", "Jaren Jackson Jr."),
                "young": ("Trae Young", "Hawks", "Dejounte Murray"),
                "booker": ("Devin Booker", "Suns", "Kevin Durant"),
                "lillard": ("Damian Lillard", "Bucks", "Giannis Antetokounmpo")
            }
            
            common_teams = {
                "lakers": ("Lakers", "LeBron James", "Anthony Davis"),
                "warriors": ("Warriors", "Stephen Curry", "Klay Thompson"),
                "bucks": ("Bucks", "Giannis Antetokounmpo", "Damian Lillard"),
                "nuggets": ("Nuggets", "Nikola Jokić", "Jamal Murray"),
                "76ers": ("76ers", "Joel Embiid", "Tyrese Maxey"),
                "sixers": ("76ers", "Joel Embiid", "Tyrese Maxey"),
                "mavericks": ("Mavericks", "Luka Dončić", "Kyrie Irving"),
                "mavs": ("Mavericks", "Luka Dončić", "Kyrie Irving"),
                "celtics": ("Celtics", "Jayson Tatum", "Jaylen Brown"),
                "suns": ("Suns", "Kevin Durant", "Devin Booker"),
                "grizzlies": ("Grizzlies", "Ja Morant", "Jaren Jackson Jr."),
                "hawks": ("Hawks", "Trae Young", "Dejounte Murray")
            }
            
            # Check for player names
            for key, (player, team, teammate) in common_players.items():
                if key in query_lower:
                    player_hint = (player, team, teammate)
                    break
            
            # Check for team names if no player found
            if not player_hint:
                for key, (team, player1, player2) in common_teams.items():
                    if key in query_lower:
                        team_hint = (team, player1, player2)
                        break
            
            # Create a hint note based on what we found
            hint_note = "NOTE TO ASSISTANT: No specific betting data is available for this query. "
            
            if player_hint:
                player, team, teammate = player_hint
                hint_note += f"The user is asking about {player}, but we don't have current data. Based on the most recent betting data from {sportsbook}, suggest they check for betting opportunities for {player}'s team (the {team}) or for his teammate {teammate}. Don't provide specific odds or lines, just brief hints."
            elif team_hint:
                team, player1, player2 = team_hint
                hint_note += f"The user is asking about the {team}, but we don't have current data. Based on the most recent betting data from {sportsbook}, suggest they check for betting opportunities for key players like {player1} or {player2}. Don't provide specific odds or lines, just brief hints."
            else:
                hint_note += f"Based on the most recent betting data from {sportsbook} for {league}, provide brief general hints about where to look for betting value without specific recommendations. For example, suggest checking player props for star players in tonight's games or looking at home underdogs for potential value."
            
            if betting_context:
                betting_context = hint_note + "\n\n" + betting_context
            else:
                betting_context = hint_note
        
        # Generate the response
        response = generate_gpt_response(query, betting_context if betting_context else None, history)
        
        # Save the assistant's response
        try:
            save_chat_message(user_id, session_id, response, "assistant")
        except Exception as e:
            logger.error(f"Error saving assistant message: {str(e)}")
        
        return {
            "response": response,
            "is_timed_out": False,
            "is_violation": False,
            "recommendation_count": len(recommendations) if recommendations else 0,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        response = generate_fallback_response(query)
        try:
            save_chat_message(user_id, session_id, response, "assistant")
        except Exception as save_error:
            logger.error(f"Error saving fallback response: {str(save_error)}")
        return {
            "response": response,
            "is_timed_out": False,
            "is_violation": False,
            "recommendation_count": 0,
            "session_id": session_id
        }

# Helper functions for the chatbot

def check_for_violation(query: str) -> bool:
    """
    Check if a query violates the chat rules.
    
    Args:
        query: The user's query
        
    Returns:
        True if the query violates the rules, False otherwise
    """
    # List of prohibited terms
    prohibited_terms = [
        "match fixing", "match-fixing", "fix the match", "throw the game",
        "money laundering", "launder money", "illegal betting", "illegal gambling",
        "insider information", "inside info for betting", "cheat the bookies",
        "bypass betting limits", "evade betting restrictions"
    ]
    
    # Check if any prohibited terms are in the query
    query_lower = query.lower()
    for term in prohibited_terms:
        if term in query_lower:
            return True
    
    return False

def get_bet_recommendations(query: str, limit: int = 1) -> List[Dict]:
    """
    Get betting recommendations from the database based on the user's query.
    
    Args:
        query: The user's query
        limit: Maximum number of recommendations to return (default: 1)
        
    Returns:
        List of betting recommendations
    """
    conn = get_db()
    
    # Get the most recent timestamp
    cursor = conn.execute("SELECT MAX(timestamp) as latest FROM betting_data")
    result = cursor.fetchone()
    latest_timestamp = result['latest'] if result else None
    
    if not latest_timestamp:
        return []
    
    # Extract keywords from the query
    keywords = [word.strip() for word in query.lower().split() if len(word.strip()) > 2]
    
    # Extract potential team names from the query
    # Instead of hardcoding team names, we'll use a more dynamic approach
    # by looking for team names in the database that match parts of the query
    
    # First, get all unique team names from the database
    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT event_teams FROM betting_data
            WHERE timestamp = ?
            """, 
            [latest_timestamp]
        )
        
        all_teams = []
        for row in cursor.fetchall():
            event_teams = row['event_teams']
            if event_teams is None:
                continue
                
            if ' vs ' in event_teams:
                teams = event_teams.split(' vs ')
                all_teams.extend(teams)
            elif ' at ' in event_teams:
                teams = event_teams.split(' at ')
                all_teams.extend(teams)
        
        # Remove duplicates and sort by length (longer names first to avoid partial matches)
        all_teams = list(set([t for t in all_teams if t is not None]))
        all_teams.sort(key=len, reverse=True)
        
        # Check if any team names appear in the query
        query_lower = query.lower()
        matched_teams = []
        
        for team in all_teams:
            if team is None:
                continue
                
            # Check for exact team name or common abbreviations/nicknames
            team_lower = team.lower()
            team_parts = team_lower.split()
            
            # Check for full team name
            if team_lower in query_lower:
                matched_teams.append(team)
                continue
                
            # Check for last part of team name (e.g., "Lakers" in "Los Angeles Lakers")
            if len(team_parts) > 1 and team_parts[-1] in query_lower:
                matched_teams.append(team)
                continue
                
            # Check for first part of team name (e.g., "Boston" in "Boston Celtics")
            if len(team_parts) > 1 and team_parts[0] in query_lower:
                matched_teams.append(team)
                continue
        
        # Add matched team names to keywords
        for team in matched_teams:
            keywords.append(team.lower())
            
        logger.info(f"Matched teams: {matched_teams}")
        
    except Exception as e:
        logger.error(f"Error extracting team names: {str(e)}")
    
    # If no valid keywords, return empty list
    if not keywords:
        return []
    
    # Build the SQL query with keyword search
    sql = """
            SELECT 
                id,
                bet_id,
                event_teams,
                description,
                sportsbook,
                odds,
                ev_percent,
                win_probability,
                sport,
                league,
                event_time,
                timestamp
            FROM betting_data 
            WHERE timestamp = ?
         """
    
    # Add sport filter if query contains sport keywords
    sport_keywords = {
        "nba": "%nba%",
        "basketball": "%basketball%",
        "nfl": "%nfl%",
        "football": "%football%",
        "mlb": "%mlb%",
        "baseball": "%baseball%",
        "nhl": "%nhl%",
        "hockey": "%hockey%",
        "soccer": "%soccer%",
        "premier league": "%premier league%",
        "la liga": "%la liga%",
        "bundesliga": "%bundesliga%",
        "serie a": "%serie a%",
        "ligue 1": "%ligue 1%",
        "mls": "%mls%",
        "tennis": "%tennis%",
        "golf": "%golf%",
        "ufc": "%ufc%",
        "mma": "%mma%",
        "boxing": "%boxing%",
        "cricket": "%cricket%",
        "rugby": "%rugby%",
        "formula 1": "%formula 1%",
        "f1": "%f1%",
        "nascar": "%nascar%"
    }
    
    # Try to extract sports from the database as well
    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT sport FROM betting_data
            WHERE timestamp = ?
            """, 
            [latest_timestamp]
        )
        
        db_sports = [row['sport'].lower() for row in cursor.fetchall() if row['sport']]
        
        # Add sports from database to the keywords dictionary
        for sport in db_sports:
            if sport.lower() not in sport_keywords:
                sport_keywords[sport.lower()] = f"%{sport.lower()}%"
                
    except Exception as e:
        logger.error(f"Error extracting sports: {str(e)}")
    
    # Check if any sport keywords are in the query
    for sport, pattern in sport_keywords.items():
        if sport in query.lower():
            sql += f" AND sport LIKE '{pattern}'"
            break
    
    # Add keyword filters for event_teams
    sql += " AND ("
    placeholders = []
    for i, keyword in enumerate(keywords):
        if i > 0:
            sql += " OR "
        sql += "event_teams LIKE ?"
        placeholders.append(f"%{keyword}%")
    sql += ")"
    
    # Order by EV and limit results
    sql += " ORDER BY CAST(REPLACE(ev_percent, '%', '') AS REAL) DESC LIMIT ?"
    placeholders.append(limit)
    
    # Execute the query
    logger.info(f"Executing SQL: {sql} with params: {[latest_timestamp] + placeholders}")
    cursor = conn.execute(sql, [latest_timestamp] + placeholders)
    
    # Convert to list of dictionaries
    recommendations = [dict(row) for row in cursor.fetchall()]
    logger.info(f"Found {len(recommendations)} recommendations")
    
    return recommendations

def get_historical_bets(query: str, limit: int = 10) -> List[Dict]:
    """
    Get historical betting data from the database based on the user's query.
    
    Args:
        query: The user's query
        limit: Maximum number of historical bets to return (default: 10)
        
    Returns:
        List of historical betting data
    """
    conn = get_db()
    
    # Extract keywords from the query
    keywords = [word.strip() for word in query.lower().split() if len(word.strip()) > 2]
    
    # Get the current timestamp
    import datetime
    current_time = datetime.datetime.now()
    
    # Calculate timestamp for 24 hours ago
    one_day_ago = current_time - datetime.timedelta(days=1)
    one_day_ago_str = one_day_ago.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get the most recent timestamp
    cursor = conn.execute("SELECT MAX(timestamp) as latest FROM betting_data")
    result = cursor.fetchone()
    latest_timestamp = result['latest'] if result else None
    
    if not latest_timestamp:
        return []
    
    # Extract potential team names from the query
    # Instead of hardcoding team names, we'll use a more dynamic approach
    # by looking for team names in the database that match parts of the query
    
    # First, get all unique team names from the database
    try:
        cursor = conn.execute(
            """
            SELECT DISTINCT event_teams FROM betting_data
            WHERE timestamp >= ?
            """,
            (one_day_ago_str,)
        )
        all_teams = [row['event_teams'] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error getting team names: {str(e)}")
        all_teams = []
    
    # Check if any team names are in the query
    matched_teams = []
    query_lower = query.lower()
    for team in all_teams:
        team_lower = team.lower()
        # Check if the team name is in the query
        if team_lower in query_lower:
            matched_teams.append(team)
        # Also check for common team nicknames
        elif "lakers" in query_lower and "los angeles lakers" in team_lower:
            matched_teams.append(team)
        elif "celtics" in query_lower and "boston celtics" in team_lower:
            matched_teams.append(team)
        # Add more common nicknames as needed
    
    logger.info(f"Matched teams: {matched_teams}")
    
    # Extract player names from the query
    common_players = {
        "lebron": "LeBron James", 
        "curry": "Stephen Curry", 
        "giannis": "Giannis Antetokounmpo",
        "jokic": "Nikola Jokić", 
        "embiid": "Joel Embiid", 
        "doncic": "Luka Dončić",
        "tatum": "Jayson Tatum", 
        "durant": "Kevin Durant", 
        "morant": "Ja Morant",
        "young": "Trae Young", 
        "booker": "Devin Booker", 
        "lillard": "Damian Lillard"
    }
    
    matched_players = []
    for key, name in common_players.items():
        if key in query_lower:
            matched_players.append(name)
    
    # Build the SQL query
    sql = """
        SELECT 
            id,
            bet_id,
            event_teams,
            description,
            sportsbook,
            odds,
            ev_percent,
            win_probability,
            sport,
            league,
            event_time,
            timestamp
        FROM betting_data 
        WHERE timestamp >= ?
    """
    
    params = [one_day_ago_str]
    
    # Add conditions for keywords
    if keywords:
        keyword_conditions = []
        for keyword in keywords:
            keyword_conditions.append("description LIKE ?")
            params.append(f"%{keyword}%")
        
        sql += " AND (" + " OR ".join(keyword_conditions) + ")"
    
    # Add conditions for matched teams
    if matched_teams:
        team_conditions = []
        for team in matched_teams:
            team_conditions.append("event_teams LIKE ?")
            params.append(f"%{team}%")
        
        if keyword_conditions:
            sql += " OR (" + " OR ".join(team_conditions) + ")"
        else:
            sql += " AND (" + " OR ".join(team_conditions) + ")"
    
    # Add conditions for matched players
    if matched_players:
        player_conditions = []
        for player in matched_players:
            player_conditions.append("description LIKE ?")
            params.append(f"%{player}%")
        
        if keyword_conditions or team_conditions:
            sql += " OR (" + " OR ".join(player_conditions) + ")"
        else:
            sql += " AND (" + " OR ".join(player_conditions) + ")"
    
    # Order by timestamp (most recent first) and limit
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    logger.info(f"Executing SQL: {sql} with params: {params}")
    
    try:
        cursor = conn.execute(sql, params)
        results = cursor.fetchall()
        
        # Convert row objects to dictionaries
        bets = []
        for row in results:
            bet = {
                'id': row['id'],
                'bet_id': row['bet_id'],
                'event_teams': row['event_teams'],
                'description': row['description'],
                'sportsbook': row['sportsbook'],
                'odds': row['odds'],
                'ev_percent': row['ev_percent'],
                'win_probability': row['win_probability'],
                'sport': row['sport'],
                'league': row['league'],
                'event_time': row['event_time'],
                'timestamp': row['timestamp']
            }
            bets.append(bet)
        
        logger.info(f"Found {len(bets)} historical bets")
        return bets
    except Exception as e:
        logger.error(f"Error executing SQL: {str(e)}")
        return []

def calculate_fair_odds(odds_str: str, ev_percent_str: str) -> str:
    """
    Calculate the implied fair odds based on the given odds and EV percentage.
    
    Args:
        odds_str: String representation of the odds (e.g., "+130", "-110")
        ev_percent_str: String representation of the EV percentage (e.g., "8.05%")
        
    Returns:
        String representation of the calculated fair odds
    """
    try:
        # Parse the EV percentage
        ev_percent = float(ev_percent_str.strip('%')) / 100
        
        # Parse the odds
        odds = odds_str.strip()
        if odds.startswith('+'):
            decimal_odds = float(odds[1:]) / 100 + 1
        elif odds.startswith('-'):
            decimal_odds = 100 / float(odds[1:]) + 1
        else:
            try:
                decimal_odds = float(odds) + 1  # Assuming decimal odds format
            except ValueError:
                return "Unknown"
        
        # Calculate the fair probability (what our model thinks is the true probability)
        # EV = (decimal_odds * win_prob) - 1
        # Therefore: win_prob = (EV + 1) / decimal_odds
        win_prob = (ev_percent + 1) / decimal_odds
        
        # Convert the fair probability to fair odds
        fair_decimal_odds = 1 / win_prob
        
        # Convert to American odds format
        if fair_decimal_odds >= 2:
            fair_american_odds = f"+{int((fair_decimal_odds - 1) * 100)}"
        else:
            fair_american_odds = f"-{int(100 / (fair_decimal_odds - 1))}"
        
        return fair_american_odds
    except Exception as e:
        logger.error(f"Error calculating fair odds: {str(e)}")
        return "Unknown"

def format_bets_for_gpt(bets: List[Dict], section_title: str) -> str:
    """
    Format betting data for GPT.
    
    Args:
        bets: List of betting data
        section_title: Title for this section of data
        
    Returns:
        Formatted string of betting data
    """
    if not bets:
        return ""
    
    result = f"### {section_title}\n\n"
    
    for i, bet in enumerate(bets):
        event_teams = bet.get('event_teams', 'Unknown Event')
        description = bet.get('description', 'No description')
        sportsbook = bet.get('sportsbook', 'Unknown')
        odds = bet.get('odds', 'Unknown')
        ev_percent = bet.get('ev_percent', 'Unknown')
        win_probability = bet.get('win_probability', 'Unknown')
        sport = bet.get('sport', 'Unknown')
        league = bet.get('league', 'Unknown')
        event_time = bet.get('event_time', 'Unknown')
        timestamp = bet.get('timestamp', 'Unknown')
        
        # Calculate fair odds
        fair_odds = calculate_fair_odds(odds, ev_percent)
        
        if section_title.startswith("Recent"):
            result += f"**CURRENT BETTING OPPORTUNITY {i+1}:** {description} at {sportsbook} with odds of {odds} and EV of {ev_percent}\n"
            result += f"- **Event:** {event_teams}\n"
            result += f"- **Win Probability:** {win_probability}\n"
            result += f"- **Fair Odds (Model's Estimate):** {fair_odds}\n"
            result += f"- **Sport/League:** {sport}/{league}\n"
            result += f"- **Event Time:** {event_time}\n"
        else:
            result += f"**Historical Bet {i+1}:** {event_teams}\n"
            result += f"- **Description:** {description}\n"
            result += f"- **Sportsbook:** {sportsbook}\n"
            result += f"- **Odds:** {odds}\n"
            result += f"- **Expected Value:** {ev_percent}\n"
            result += f"- **Win Probability:** {win_probability}\n"
            result += f"- **Fair Odds (Model's Estimate):** {fair_odds}\n"
            result += f"- **Sport/League:** {sport}/{league}\n"
            result += f"- **Event Time:** {event_time}\n"
            result += f"- **Data Timestamp:** {timestamp}\n"
        
        result += "\n"
    
    # Add analysis hints for historical data
    if section_title.startswith("Historical"):
        result += "**Analysis Hints:**\n"
        result += "- Look for patterns in the historical data that might be relevant to the user's query.\n"
        result += "- Consider how odds, EV%, and win probability have changed over time for similar bets.\n"
        result += "- Compare the offered odds with the fair odds to identify value opportunities.\n"
        result += "- Identify any trends in specific sportsbooks offering better value for certain types of bets.\n\n"
    
    # Add recommendation hints for current data
    if section_title.startswith("Recent"):
        result += "**Recommendation Hints:**\n"
        result += "- ALWAYS start your response by explicitly stating the available betting opportunity using the format: 'BETTING OPPORTUNITY: [Description] at [Sportsbook] with odds of [Odds] and EV of [EV%].'\n"
        result += "- Focus on bets with the highest EV% as they represent the best value.\n"
        result += "- Explain the difference between the offered odds and the fair odds to highlight the value.\n"
        result += "- Be direct and clear about the opportunity - users need to know exactly what's available right now.\n"
        result += "- If the user has a preferred sportsbook that doesn't match the available opportunity, acknowledge this but still present the opportunity.\n"
        result += "- Remember that being on the cutting edge of the sports market requires diversity and agility across different sportsbooks.\n\n"
    
    return result

def generate_gpt_response(query: str, betting_context: Optional[str], history: List[Dict]) -> str:
    """
    Generate a response using GPT.
    
    Args:
        query: The user's query
        betting_context: Formatted betting data context
        history: Chat history
        
    Returns:
        Generated response
    """
    import httpx
    import os
    
    # Get OpenAI API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, using fallback response")
        return generate_fallback_response(query)
    
    # Check if user is asking for multiple recommendations
    query_lower = query.lower()
    multiple_keywords = ["multiple", "several", "many", "different", "various", "few", "some"]
    asking_for_multiple = any(keyword in query_lower for keyword in multiple_keywords)
    
    # Only use fallback response if there's truly no data AND the user is asking for multiple recommendations
    # If we have betting_context (which includes historical data), we should use it
    if not betting_context and asking_for_multiple:
        logger.info("No betting data found and user asking for multiple recommendations. Using fallback response.")
        return generate_fallback_response(query)
    
    # If we have no betting context at all, use fallback
    if not betting_context:
        logger.info("No betting data found. Using fallback response.")
        return generate_fallback_response(query)
    
    # Format the messages for the API
    messages = []
    
    # Add system message with instructions
    system_message = """
    You are BetAssistant, a helpful AI assistant specializing in sports betting analysis.
    
    IMPORTANT GUIDELINES:
    1. ALWAYS start your response by explicitly stating the available betting opportunity when one is found. Be direct and clear.
    2. Use this format when a current bet is available: "BETTING OPPORTUNITY: [Description] at [Sportsbook] with odds of [Odds] and EV of [EV%]."
    3. Keep your responses concise and to the point - aim for 3-5 sentences maximum after stating the opportunity.
    4. Provide ONLY ONE specific betting recommendation in your response, even if multiple options are available.
    5. If the user has a preferred sportsbook that doesn't match the available opportunity, acknowledge this but still present the opportunity.
       For example: "While you prefer DraftKings, there's currently value at FanDuel for [bet description]."
    6. DO NOT use outdated information about players, teams, or games - the data may not be current.
    7. Focus only on the betting data provided in the context, not on your general knowledge of sports.
    8. Be conversational but brief, focusing on providing valuable betting insights.
    9. Never encourage irresponsible betting or guarantee outcomes.
    10. If no betting data is available for a query, provide a brief hint about potential opportunities rather than specific recommendations.
        For example: "While I don't have specific data on LeBron props right now, there might be value in checking player props for Anthony Davis tonight."
    11. If you see a note about historical data, briefly mention that the line was available previously but may have moved, and suggest looking for similar opportunities.
    12. If user preferences are provided, prioritize recommendations that match those preferences when possible.
    13. Always remind users to verify current odds before placing any bets, as lines move quickly.
    14. Remember that being on the cutting edge of the sports market requires diversity and agility across different sportsbooks.
    
    The betting context will be provided separately, if available.
    """
    messages.append({"role": "system", "content": system_message})
    
    # Add betting context if available
    if betting_context:
        messages.append({
            "role": "system", 
            "content": f"Here is the relevant betting data for this query. For current bets, provide ONLY ONE recommendation. For historical data, you can analyze patterns across multiple bets:\n\n{betting_context}"
        })
    
    # Add chat history
    for msg in history:
        # Make sure we're accessing the correct keys
        role = "assistant" if msg.get("role") == "assistant" else "user"
        content = msg.get("message", "")
        if content:  # Only add if there's actual content
            messages.append({"role": role, "content": content})
    
    # Add the current query
    messages.append({"role": "user", "content": query})
    
    try:
        # Make the API request
        logger.info("Sending request to OpenAI API")
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gpt-4-turbo-preview",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30.0
        )
        
        # Parse the response
        response_data = response.json()
        logger.info("Received response from OpenAI API")
        
        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        else:
            logger.error(f"Unexpected API response format: {response_data}")
            return generate_fallback_response(query)
            
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return generate_fallback_response(query)

def generate_fallback_response(query: str) -> str:
    """
    Generate a fallback response when the OpenAI API call fails or no betting data is found.
    
    Args:
        query: The user's query
        
    Returns:
        A fallback response
    """
    import random
    from app.db import get_user_preferences
    
    # Get current user ID from Flask context
    from flask import g
    user_id = getattr(g, 'user_id', None)
    
    # Default fallback responses
    general_responses = [
        "I don't have specific betting data for that query. Could you try asking about a different team, player, or bet type?",
        "I couldn't find exact matches for your query. Try being more specific about the team, player, or game you're interested in.",
        "No specific betting data available for that request. How about asking about a recent game or popular betting market?",
    ]
    
    # Responses with alternative suggestions
    alternative_suggestions = [
        "I don't have data on that specific bet, but there's an interesting over/under line on the Celtics game that's getting attention.",
        "While I don't have that exact information, there's a player prop for Nikola Jokić that shows good value right now.",
        "I couldn't find that specific data, but there's a promising spread bet in tonight's Warriors game worth looking into.",
        "No exact matches found, but FanDuel has some interesting player props for tonight's Bucks game you might want to check out.",
        "I don't have that specific information, but DraftKings has a special promotion on parlays for tonight's games.",
    ]
    
    # Responses with educational content
    educational_responses = [
        "I don't have that specific data, but remember that line shopping across different sportsbooks can often find you better odds.",
        "While I don't have that exact information, it's always important to check the current line price before placing any bet, as odds can change quickly.",
        "I couldn't find that specific data, but keep in mind that player props can be volatile based on matchups and recent performance.",
        "No exact matches found. When betting on spreads, remember that home court advantage typically accounts for 2-3 points in basketball.",
        "I don't have that specific information. Remember that betting units should typically be 1-5% of your bankroll for responsible betting.",
    ]
    
    # Responses about historical data and line movement
    historical_responses = [
        "DraftKings had that line available a few hours ago at -110, but it seems to have stabilized and is no longer available. Lines can move quickly based on betting volume and new information.",
        "FanDuel offered that prop earlier today, but the line has moved significantly since then. This often happens when there's breaking news about injuries or lineup changes.",
        "That specific bet was available on BetMGM this morning, but the odds have shifted and it's no longer showing the same value. This is why timing can be crucial in sports betting.",
        "Caesars had that market open yesterday with favorable odds, but it appears the line has stabilized and is no longer available at the same price. Always check for the most current odds before placing a bet.",
        "That player prop was trending earlier today on PointsBet, but the market has adjusted and the line has moved. This is common when sharp bettors target specific opportunities."
    ]
    
    # Extract potential player names from query to personalize historical responses
    query_lower = query.lower()
    player_name = None
    common_players = {
        "lebron": "LeBron James", 
        "curry": "Stephen Curry", 
        "giannis": "Giannis Antetokounmpo",
        "jokic": "Nikola Jokić", 
        "embiid": "Joel Embiid", 
        "doncic": "Luka Dončić",
        "tatum": "Jayson Tatum", 
        "durant": "Kevin Durant", 
        "morant": "Ja Morant",
        "young": "Trae Young", 
        "booker": "Devin Booker", 
        "lillard": "Damian Lillard"
    }
    
    for key, name in common_players.items():
        if key in query_lower:
            player_name = name
            break
    
    # If a player name is found, create personalized historical responses
    if player_name:
        personalized_historical = [
            f"There was a {player_name} prop bet available on DraftKings earlier today, but the line has moved significantly since then. This often happens when there's new information or heavy betting on one side.",
            f"FanDuel had {player_name} player props this morning, but those lines have stabilized and the value isn't as good now. Always check the current odds before placing any bets.",
            f"BetMGM offered some interesting {player_name} props a few hours ago, but the market has adjusted and those specific lines are no longer available at the same price.",
            f"There were some {player_name} props with good value earlier, but the lines have moved. This is common when sharp bettors target specific opportunities.",
            f"Caesars had {player_name} props with favorable odds earlier today, but the lines have shifted. This is why timing can be important in sports betting."
        ]
        # Add these personalized responses to our pool
        historical_responses = personalized_historical
    
    # Combine all response types, with more weight to historical responses if player is mentioned
    all_responses = general_responses + alternative_suggestions + educational_responses
    if player_name and "prop" in query_lower:
        # Add historical responses multiple times to increase their probability
        all_responses.extend(historical_responses * 3)
    else:
        all_responses.extend(historical_responses)
    
    # If we have a user ID, try to personalize based on preferences
    personalized_response = ""
    if user_id:
        try:
            preferences = get_user_preferences(user_id)
            
            # If user has preferences, add a personalized note
            if preferences:
                pref_sportsbook = preferences.get('sportsbooks', [])
                pref_sport = preferences.get('sports', [])
                pref_bet_type = preferences.get('bet_types', [])
                
                if any([pref_sportsbook, pref_sport, pref_bet_type]):
                    personalized_response = "\n\nI'll try to honor your preferences for "
                    
                    if pref_sportsbook:
                        personalized_response += f"{', '.join(pref_sportsbook)} sportsbook"
                        if pref_sport or pref_bet_type:
                            personalized_response += ", "
                    
                    if pref_sport:
                        personalized_response += f"{', '.join(pref_sport)}"
                        if pref_bet_type:
                            personalized_response += ", "
                    
                    if pref_bet_type:
                        personalized_response += f"{', '.join(pref_bet_type)} bets"
                    
                    personalized_response += " when possible, but availability may vary."
        except Exception as e:
            logger.error(f"Error getting user preferences: {str(e)}")
    
    # Add a disclaimer
    disclaimer = "\n\nRemember to always verify the current line price before placing any bet, as odds can change quickly."
    
    # Select a random response and add personalization and disclaimer
    return random.choice(all_responses) + personalized_response + disclaimer 