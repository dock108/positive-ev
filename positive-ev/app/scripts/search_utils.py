import os
import logging
import requests
from typing import List, Dict
from ratelimit import limits, sleep_and_retry
from dotenv import load_dotenv
from datetime import datetime
from app.scripts.sports_reference import get_boxscore
import time

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Google Search API Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
# Update rate limits to be more conservative
SEARCH_REQUESTS_PER_MINUTE = 30  # Reduced from 60 to be more conservative
SEARCH_DELAY = 2  # Add delay between requests

class SearchError(Exception):
    """Custom exception for search-related errors."""
    pass

def determine_sport(event: str, bet_type: str, sport_league: str = None) -> tuple:
    """
    Determine the sport and league based on the event, bet type, and sport_league fields.
    
    Args:
        event (str): Event description
        bet_type (str): Type of bet
        sport_league (str): Sport/league from database (e.g., "Basketball | NBA")
        
    Returns:
        tuple: (sport, league) or (None, None) if not in supported leagues
    """
    # Supported leagues whitelist with their standardized names
    SUPPORTED_LEAGUES = {
        # Basketball
        "Basketball | NBA": ("nba", "NBA"),
        "Basketball | NCAAB": ("ncaab", "NCAAB"),
        
        # Hockey
        "Hockey | NHL": ("nhl", "NHL"),
        
        # Tennis
        "Tennis | WTA": ("tennis", "WTA"),
        "Tennis | ATP": ("tennis", "ATP"),
        "Tennis | ATP Challenger": ("tennis", "ATP Challenger"),
        "Tennis | ITF Men": ("tennis", "ITF Men"),
        
        # Soccer
        "Soccer | Saudi Arabia - Saudi League": ("soccer", "Saudi League"),
        "Soccer | England - Premier League": ("soccer", "Premier League"),
        "Soccer | England - FA Cup": ("soccer", "FA Cup"),
        "Soccer | Spain - La Liga": ("soccer", "La Liga"),
        "Soccer | UEFA - Champions League": ("soccer", "Champions League"),
        "Soccer | UEFA - Europa League": ("soccer", "Europa League"),
        "Soccer | Italy - Serie A": ("soccer", "Serie A"),
        
        # Baseball
        "Baseball | MLB": ("mlb", "MLB"),
        
        # Football
        "Football | NFL": ("nfl", "NFL"),
        "Football | NCAAF": ("ncaaf", "NCAAF"),
        
        # MMA
        "MMA | UFC": ("mma", "UFC")
    }
    
    # If sport_league is provided and in whitelist, use that
    if sport_league and sport_league in SUPPORTED_LEAGUES:
        return SUPPORTED_LEAGUES[sport_league]
    
    # If we don't have a valid sport_league, try to determine from event
    event_upper = event.upper()
    
    # Look for league indicators in the event
    if any(x in event_upper for x in ["NBA", "NATIONAL BASKETBALL ASSOCIATION"]):
        return ("nba", "NBA")
    elif any(x in event_upper for x in ["NCAA", "COLLEGE BASKETBALL"]):
        return ("ncaab", "NCAAB")
    elif "NHL" in event_upper:
        return ("nhl", "NHL")
    elif "PREMIER LEAGUE" in event_upper:
        return ("soccer", "Premier League")
    elif "LA LIGA" in event_upper:
        return ("soccer", "La Liga")
    elif "CHAMPIONS LEAGUE" in event_upper:
        return ("soccer", "Champions League")
    elif "EUROPA LEAGUE" in event_upper:
        return ("soccer", "Europa League")
    elif "SERIE A" in event_upper:
        return ("soccer", "Serie A")
    elif "NFL" in event_upper:
        return ("nfl", "NFL")
    elif any(x in event_upper for x in ["NCAA FOOTBALL", "COLLEGE FOOTBALL"]):
        return ("ncaaf", "NCAAF")
    elif "UFC" in event_upper:
        return ("mma", "UFC")
    elif "MLB" in event_upper:
        return ("mlb", "MLB")
    
    # Check for tennis match format (Player1 vs Player2) as last resort
    if " vs " in event and len(event.split(" vs ")) == 2:
        player1, player2 = event.split(" vs ")
        # If both parts look like player names (no team identifiers)
        if all(not any(team in name.upper() for team in ["FC", "UNITED", "CITY", "ATHLETIC", "WARRIORS", "LAKERS", "CELTICS"]) 
               for name in [player1, player2]):
            # Default to ATP if we can't determine specific tennis league
            return ("tennis", "ATP")
    
    # If we can't determine the league, return None
    return (None, None)

@sleep_and_retry
@limits(calls=SEARCH_REQUESTS_PER_MINUTE, period=60)
def search_game_statistics(event: str, date: str, stat_type: str, sport_league: str = None) -> List[Dict]:
    """
    Search for game statistics using Google Custom Search API and sports-reference websites.
    
    Args:
        event (str): Event description (e.g., "Lakers vs Warriors")
        date (str): Date of the event
        stat_type (str): Type of statistic to search for
        sport_league (str): Sport/league from database (e.g., "Basketball | NBA")
        
    Returns:
        List[Dict]: List of search results with title, snippet, and link
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise SearchError("Google API credentials not configured")
        
    try:
        # Determine sport and league
        sport, league = determine_sport(event, stat_type, sport_league)
        if not sport:
            logger.debug(f"Unsupported sport/league for event: {event}")
            return []
        logger.debug(f"Using sport: {sport}, league: {league}")
        
        game_date = datetime.strptime(date, "%B %d, %Y").strftime("%Y-%m-%d")
        box_score = get_boxscore(sport, event, game_date)
        
        results = []
        
        # If we found a box score, add it as the first result
        if box_score:
            results.append({
                'title': f"Official Box Score: {event} - {date}",
                'snippet': f"Official game statistics from sports-reference.com including detailed player stats: {str(box_score['basic_stats'])}",
                'link': box_score['url'],
                'box_score': box_score
            })
        
        # Construct search query with league info
        query = f"{league} {event} {date} {stat_type} box score stats official"
        logger.debug(f"Search query: {query}")
        
        # Google Custom Search API endpoint
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Parameters for the search
        params = {
            'key': GOOGLE_API_KEY,
            'cx': GOOGLE_CSE_ID,
            'q': query,
            'num': 5,  # Number of results to return
            'dateRestrict': 'w[1]'  # Restrict to results from the past week
        }
        
        # Add delay between requests
        time.sleep(SEARCH_DELAY)
        
        # Make the API request with better error handling
        response = requests.get(url, params=params)
        
        # Handle rate limiting specifically
        if response.status_code == 429:  # Too Many Requests
            logger.warning("Hit Google Search API rate limit, waiting before retry...")
            time.sleep(60)  # Wait a minute before retry
            response = requests.get(url, params=params)
        
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        
        # Check for API-specific error messages
        if 'error' in data:
            error_reason = data['error'].get('message', 'Unknown API error')
            if 'quota' in error_reason.lower():
                logger.error(f"Google Search API quota exceeded: {error_reason}")
                raise SearchError(f"Search quota exceeded: {error_reason}")
            else:
                logger.error(f"Google Search API error: {error_reason}")
                raise SearchError(f"Search API error: {error_reason}")
        
        if 'items' in data:
            # Add Google search results after the box score
            for item in data['items']:
                result = {
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'link': item.get('link', '')
                }
                results.append(result)
            
        return results
        
    except requests.exceptions.RequestException as e:
        if "429" in str(e):
            logger.error("Google Search API rate limit exceeded")
            raise SearchError("Search rate limit exceeded - please try again later")
        logger.error(f"Error making Google Search API request: {str(e)}")
        raise SearchError(f"Search API request failed: {str(e)}")
    except KeyError as e:
        logger.error(f"Error parsing search results: {str(e)}")
        raise SearchError(f"Failed to parse search results: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        raise SearchError(f"Unexpected search error: {str(e)}")

def format_search_results(results: List[Dict]) -> str:
    """
    Format search results into a string suitable for the OpenAI prompt.
    
    Args:
        results (List[Dict]): List of search results
        
    Returns:
        str: Formatted string with search results
    """
    if not results:
        return "No relevant statistics found."
        
    formatted = "Search Results:\n\n"
    
    # Check if the first result is a box score
    if results and 'box_score' in results[0]:
        box_score = results[0]['box_score']
        formatted += "Official Box Score Statistics:\n"
        formatted += "==========================\n\n"
        
        # Format box score data
        for team, players in box_score['basic_stats'].items():
            formatted += f"{team}\n"
            # Add header row
            formatted += "Player\tMIN\tFG\tFGA\tFG%\t3P\t3PA\t3P%\tFT\tFTA\tFT%\tORB\tDRB\tTRB\tAST\tSTL\tBLK\tTOV\tPF\tPTS\n"
            formatted += "-" * 120 + "\n"  # Separator line
            
            for player, stats in players.items():
                # Skip rows that are just headers
                if player in ['Starters', 'Reserves', 'Team Totals']:
                    if player != 'Team Totals':  # Only add section headers
                        formatted += f"\n{player}:\n"
                    continue
                
                # Format each stat with proper spacing
                formatted += (
                    f"{player}\t{stats.get('MIN', '')}\t{stats.get('FG', '')}\t{stats.get('FGA', '')}\t"
                    f"{stats.get('FG%', '')}\t{stats.get('3P', '')}\t{stats.get('3PA', '')}\t{stats.get('3P%', '')}\t"
                    f"{stats.get('FT', '')}\t{stats.get('FTA', '')}\t{stats.get('FT%', '')}\t{stats.get('ORB', '')}\t"
                    f"{stats.get('DRB', '')}\t{stats.get('TRB', '')}\t{stats.get('AST', '')}\t{stats.get('STL', '')}\t"
                    f"{stats.get('BLK', '')}\t{stats.get('TOV', '')}\t{stats.get('PF', '')}\t{stats.get('PTS', '')}\n"
                )
            
            formatted += "\n"  # Add space between teams
        
        formatted += "==========================\n\n"
    
    # Add remaining search results
    for i, result in enumerate(results[1:], 1):
        formatted += f"{i}. {result['title']}\n"
        formatted += f"   {result['snippet']}\n"
        formatted += f"   Source: {result['link']}\n\n"
    
    return formatted 