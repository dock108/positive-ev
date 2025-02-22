import argparse
import json
import logging
import time
from datetime import datetime
from typing import Tuple, Optional
from ratelimit import limits, sleep_and_retry
from openai import OpenAI
from dotenv import load_dotenv

# Import path setup first
from path_setup import project_root  # noqa

from app.db_utils import get_db_connection
from app.scripts.config import (
    API_KEY, MODEL, TEMPERATURE,
    MAX_RETRIES, RETRY_DELAY,
    REQUESTS_PER_MINUTE
)
from app.scripts.search_utils import search_game_statistics, format_search_results, SearchError

# Configure logging
# File handler with detailed logging
file_handler = logging.FileHandler('logs/bet_evaluation.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Console handler with focused, cleaner output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(message)s'  # Simple format for console
))

# Configure root logger
logging.basicConfig(level=logging.DEBUG, handlers=[file_handler, console_handler])
logger = logging.getLogger(__name__)

# Suppress other loggers' console output
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('app.db_utils').setLevel(logging.WARNING)

# Load environment variables and initialize OpenAI client
load_dotenv()
client = OpenAI(api_key=API_KEY)

def log_search_results(event: str, date: str, stat_type: str, results: list):
    """Log search results in a clean, readable format."""
    logger.info("\n=== Search Results ===")
    logger.info(f"Query: {event} | {date} | {stat_type}")
    if not results:
        logger.info("No results found")
        return
    
    for i, result in enumerate(results, 1):
        logger.info(f"\n{i}. {result['title']}")
        logger.info(f"   {result['snippet']}")
        logger.info(f"   URL: {result['link']}")
    logger.info("==================\n")

def get_sport_specific_instructions(sport: str) -> str:
    """Get sport-specific evaluation instructions."""
    if sport == "nba":
        return """
For NBA bets:
- Quarter/Half scores include both teams combined
- Player props are marked as TIE if player is inactive/DNP
- Overtime periods count for game totals but not quarter-specific bets
- Common stats: Points, Rebounds, Assists, Steals, Blocks, Turnovers, FG Made/Attempted, 3PT Made/Attempted
- Double-Double: Player must get 10+ in two statistical categories
- Triple-Double: Player must get 10+ in three statistical categories"""
    elif sport == "nfl":
        return """
For NFL bets:
- Quarter/Half scores include both teams combined
- Player props are marked as TIE if player is inactive/DNP
- Overtime counts for all totals except quarter-specific bets
- Sacks and tackles are credited based on official NFL statistics
- Passing TD = 4pts, Rushing/Receiving TD = 6pts (for fantasy points)
- Common stats: Passing Yards, Rushing Yards, Receiving Yards, Touchdowns, Completions, Receptions, Targets"""
    elif sport == "ncaaf":
        return """
For College Football bets:
- Quarter/Half scores include both teams combined
- Player props are marked as TIE if player is inactive/DNP
- Overtime counts for game totals but not quarter-specific bets
- Sacks and tackles based on official NCAA statistics
- Common stats: Passing Yards, Rushing Yards, Receiving Yards, Touchdowns, Completions"""
    elif sport == "ncaab":
        return """
For College Basketball bets:
- Half scores include both teams combined
- Player props are marked as TIE if player is inactive/DNP
- Overtime counts for game totals but not half-specific bets
- Common stats: Points, Rebounds, Assists, Steals, Blocks, FG Made/Attempted, 3PT Made/Attempted"""
    elif sport == "nhl":
        return """
For NHL bets:
- Period scores include both teams combined
- Player props are marked as TIE if player is inactive/DNP
- Overtime/Shootout goals count for game totals but not period-specific bets
- Empty net goals count for all totals
- Common stats: Goals, Assists, Points, Shots on Goal, Saves, Power Play Points"""
    elif sport == "soccer":
        return """
For Soccer bets:
- Full time results include extra time (if played) unless specified as '90 minutes'
- Player props are marked as TIE if player is not in starting XI and doesn't play
- Goals in extra time/penalties don't count for 90-minute bets
- Own goals count for team totals but not player props
- Clean sheet = No goals conceded during specified period
- Common stats: Goals, Assists, Shots, Shots on Target, Passes, Tackles, Saves"""
    elif sport == "tennis":
        return """
For Tennis bets:
- Sets are counted as X-Y where X and Y are games won by each player
- Total Games = Sum of all games played in all sets
- Player Games = Only games won by specified player
- Match retirement/walkover results in TIE
- Common stats: Games Won, Sets Won, Aces, Double Faults
- For "Total Games" props: 6-4 set = 10 games, 7-6 set = 13 games"""
    else:
        return ""

def construct_prompt(bet_dict):
    """Construct the prompt for the bet evaluation."""
    try:
        # Format event date
        event_date = datetime.strptime(bet_dict['event_time'], "%Y-%m-%d %H:%M").strftime("%B %d, %Y")
        
        # Search for game statistics
        search_results = search_game_statistics(
            bet_dict['event_teams'],
            event_date,
            bet_dict['bet_type'],
            bet_dict['sport_league']
        )
        
        # Format search results
        formatted_results = format_search_results(search_results)
        
        # Log search results
        logging.info("\n=== Search Results ===")
        logging.info(f"Query: {bet_dict['event_teams']} | {event_date} | {bet_dict['bet_type']}")
        logging.info(formatted_results)
        logging.info("==================\n")
        
        prompt = """You are a sports betting outcome evaluator with access to real-time search results. Your task is to analyze search results and determine if a specific bet condition was met.

Please evaluate the following bet:
Event: {event}
Date: {date}
Type: {bet_type}
Sport/League: {sport_league}
Condition: {condition}

Search Results:
{search_results}

Instructions for OVER/UNDER bets:
1. For "Over X.5" bets:
   - If the actual statistic is greater than X.5, it's a WIN
   - If the actual statistic is less than or equal to X.5, it's a LOSS
   Example: If bet is "Over 5.5 assists" and player had 6 assists = WIN
   Example: If bet is "Over 5.5 assists" and player had 5 assists = LOSS

2. For "Under X.5" bets:
   - If the actual statistic is less than X.5, it's a WIN
   - If the actual statistic is greater than or equal to X.5, it's a LOSS
   Example: If bet is "Under 5.5 assists" and player had 5 assists = WIN
   Example: If bet is "Under 5.5 assists" and player had 6 assists = LOSS

3. For combined stats (e.g. Points + Rebounds + Assists):
   - Sum the individual statistics first, then compare to the Over/Under line
   Example: If bet is "Over 26.5 Points + Rebounds + Assists":
   - Points (20) + Rebounds (5) + Assists (3) = 28 total > 26.5 = WIN
   - Points (15) + Rebounds (6) + Assists (5) = 26 total < 26.5 = LOSS

4. If a player did not play in the game, the result is a TIE.

Please respond in this format:
{{
    "result": "WIN"|"LOSS"|"TIE"|"UNCERTAIN",
    "confidence": 0-100,
    "explanation": "Include: exact statistic found, source URL, and verification details"
}}"""

        return prompt.format(
            event=bet_dict['event_teams'],
            date=event_date,
            bet_type=bet_dict['bet_type'],
            sport_league=bet_dict['sport_league'],
            condition=bet_dict['description'],
            search_results=formatted_results
        )
    except SearchError as e:
        logging.error(f"Error searching for game statistics: {e}")
        return None

@sleep_and_retry
@limits(calls=REQUESTS_PER_MINUTE, period=60)
def query_model(prompt: str) -> Tuple[str, float, str]:
    """
    Query OpenAI's API with retry logic and rate limiting.
    Returns: (outcome, confidence, reasoning)
    """
    if not API_KEY:
        raise ValueError("OpenAI API key not found in environment variables")

    retries = 0
    while retries < MAX_RETRIES:
        try:
            completion = OpenAI(api_key=API_KEY).chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=TEMPERATURE
            )
            
            # Extract the response content
            try:
                content = completion.choices[0].message.content
                # Remove markdown code block if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
                
                result = json.loads(content)
                return (
                    result.get("result", "UNCERTAIN"),
                    float(result.get("confidence", 0)),
                    result.get("explanation", "")
                )
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                logger.error(f"Error parsing model response: {e}")
                logger.debug(f"Raw response: {content}")
                return "UNCERTAIN", 0, f"Error parsing response: {str(e)}"
                
        except Exception as e:
            retries += 1
            if retries < MAX_RETRIES:
                logger.warning(f"API call failed, attempt {retries} of {MAX_RETRIES}: {str(e)}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"All API call attempts failed: {str(e)}")
                return "UNCERTAIN", 0, f"API Error: {str(e)}"
    
    return "UNCERTAIN", 0, "Max retries exceeded"

def get_ungraded_bets(conn, start_date: Optional[str] = None, end_date: Optional[str] = None, 
                      limit: Optional[int] = None, last_processed_id: Optional[str] = None) -> list:
    """Get unique ungraded bets that need outcome evaluation."""
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT b.bet_id, b.event_teams, b.event_time, b.bet_type, b.description,
               b.sport_league
        FROM betting_data b
        LEFT JOIN bet_outcome_evaluation e ON b.bet_id = e.bet_id
        WHERE datetime(b.event_time, '+4 hours') < datetime('now')
        AND e.bet_id IS NULL
        AND b.sport_league IN (
            'Basketball | NBA',
            'Basketball | NCAAB',
            'Hockey | NHL',
            'Tennis | WTA',
            'Tennis | ATP',
            'Tennis | ATP Challenger',
            'Tennis | ITF Men',
            'Soccer | Saudi Arabia - Saudi League',
            'Soccer | England - Premier League',
            'Soccer | England - FA Cup',
            'Soccer | Spain - La Liga',
            'Soccer | UEFA - Champions League',
            'Soccer | UEFA - Europa League',
            'Soccer | Italy - Serie A',
            'Baseball | MLB',
            'Football | NFL',
            'Football | NCAAF',
            'MMA | UFC'
        )
    """
    
    params = []
    
    if last_processed_id:
        query += " AND b.bet_id > ?"
        params.append(last_processed_id)
    
    if start_date:
        query += " AND b.event_time >= ?"
        params.append(start_date)
    if end_date:
        query += " AND b.event_time <= ?"
        params.append(end_date)
    
    query += " ORDER BY b.bet_id"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    return cursor.fetchall()

def store_outcome(conn, bet_id: str, outcome: str, confidence: float, reasoning: str):
    """Store the evaluated outcome in the database."""
    cursor = conn.cursor()
    
    try:
        # First check if this bet_id has already been evaluated
        cursor.execute("""
            SELECT bet_id FROM bet_outcome_evaluation 
            WHERE bet_id = ?
        """, (bet_id,))
        
        if cursor.fetchone():
            logger.info(f"Skipping bet {bet_id} - already evaluated")
            return
            
        # Insert new evaluation
        cursor.execute("""
            INSERT INTO bet_outcome_evaluation 
            (bet_id, outcome, confidence_score, reasoning)
            VALUES (?, ?, ?, ?)
        """, (bet_id, outcome, confidence, reasoning))
        
        # Always update the main betting_data table with the result
        if outcome != "UNCERTAIN":
            result = outcome[0]  # 'W' for WIN, 'L' for LOSS, 'T' for TIE
            cursor.execute("""
                UPDATE betting_data 
                SET result = ? 
                WHERE bet_id = ?
            """, (result, bet_id))
        
        conn.commit()
        logger.info(f"Stored outcome for bet {bet_id}: {outcome} ({confidence}%)")
        
    except Exception as e:
        logger.error(f"Error storing outcome for bet {bet_id}: {str(e)}")
        conn.rollback()

def evaluate_bets(start_date: Optional[str] = None, end_date: Optional[str] = None, 
                  batch_size: Optional[int] = None, max_bets: Optional[int] = None):
    """Main function to evaluate ungraded bets."""
    total_processed = 0
    last_processed_id = None
    start_time = time.time()

    with get_db_connection() as conn:
        # Get total count first
        cursor = conn.cursor()
        count_query = """
            SELECT COUNT(DISTINCT b.bet_id)
            FROM betting_data b
            LEFT JOIN bet_outcome_evaluation e ON b.bet_id = e.bet_id
            WHERE datetime(b.event_time, '+4 hours') < datetime('now')
            AND e.bet_id IS NULL
            AND b.sport_league IN (
                'Basketball | NBA',
                'Basketball | NCAAB',
                'Hockey | NHL',
                'Tennis | WTA',
                'Tennis | ATP',
                'Tennis | ATP Challenger',
                'Tennis | ITF Men',
                'Soccer | Saudi Arabia - Saudi League',
                'Soccer | England - Premier League',
                'Soccer | England - FA Cup',
                'Soccer | Spain - La Liga',
                'Soccer | UEFA - Champions League',
                'Soccer | UEFA - Europa League',
                'Soccer | Italy - Serie A',
                'Baseball | MLB',
                'Football | NFL',
                'Football | NCAAF',
                'MMA | UFC'
            )
        """
        cursor.execute(count_query)
        total_bets = cursor.fetchone()[0]
        
        if max_bets:
            total_bets = min(total_bets, max_bets)
        
        logger.info(f"Evaluating {total_bets} bets...")
        
        if batch_size is None:
            batch_size = 50  # Default batch size
        
        while True:
            if max_bets and total_processed >= max_bets:
                break
                
            remaining = max_bets - total_processed if max_bets else batch_size
            current_batch_size = min(batch_size, remaining) if max_bets else batch_size
            
            bets = get_ungraded_bets(conn, start_date, end_date, current_batch_size, last_processed_id)
            if not bets:
                break
            
            for bet in bets:
                bet_dict = {
                    'bet_id': bet[0],
                    'event_teams': bet[1],
                    'event_time': bet[2],
                    'bet_type': bet[3],
                    'description': bet[4],
                    'sport_league': bet[5] if len(bet) > 5 else None
                }
                
                logger.info(f"\nEvaluating Bet ({total_processed + 1}/{total_bets}):")
                logger.info(f"Event: {bet_dict['event_teams']}")
                logger.info(f"Date: {bet_dict['event_time']}")
                logger.info(f"Type: {bet_dict['bet_type']}")
                logger.info(f"Sport/League: {bet_dict['sport_league'] or 'Not specified'}")
                logger.info(f"Condition: {bet_dict['description']}\n")
                
                prompt = construct_prompt(bet_dict)
                outcome, confidence, reasoning = query_model(prompt)
                store_outcome(conn, bet_dict['bet_id'], outcome, confidence, reasoning)
                
                logger.info(f"Result: {outcome} (Confidence: {confidence}%)")
                logger.info(f"Explanation: {reasoning}\n")
                
                total_processed += 1
                last_processed_id = bet_dict['bet_id']
                
                # Add a small delay between API calls if processing many bets
                if len(bets) > 10:
                    time.sleep(60 / REQUESTS_PER_MINUTE)  # Respect rate limit
        
        logger.info(f"\nCompleted! Processed {total_processed} bets in {(time.time() - start_time)/60:.1f} minutes")

def main():
    parser = argparse.ArgumentParser(description='Evaluate ungraded sports bets')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--batch-size', type=int, help='Number of bets to process in each batch')
    parser.add_argument('--max-bets', type=int, help='Maximum number of bets to process in total')
    args = parser.parse_args()
    
    try:
        evaluate_bets(args.start, args.end, args.batch_size, args.max_bets)
        logger.info("Bet evaluation completed successfully")
    except Exception as e:
        logger.error(f"Error during bet evaluation: {str(e)}")
        raise

if __name__ == "__main__":
    main() 