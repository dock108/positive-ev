import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class SportsReferenceError(Exception):
    """Custom exception for sports-reference related errors."""
    pass

def get_basketball_reference_boxscore(teams: str, date: datetime, league: str = "nba") -> Optional[Dict]:
    """
    Scrape basketball-reference.com for the game's box score.
    
    Args:
        teams (str): Team names (e.g., "Los Angeles Lakers vs Golden State Warriors")
        date (datetime): Game date
        league (str): "nba" or "ncaab"
        
    Returns:
        Optional[Dict]: Box score data if found, None otherwise
    """
    try:
        # Format date for URL
        date_str = date.strftime("%Y%m%d")
        
        # Extract team names and convert to basketball-reference format
        nba_team_mapping = {
            "Hawks": "ATL", "Celtics": "BOS", "Nets": "BRK", "Hornets": "CHO",
            "Bulls": "CHI", "Cavaliers": "CLE", "Mavericks": "DAL", "Nuggets": "DEN",
            "Pistons": "DET", "Warriors": "GSW", "Rockets": "HOU", "Pacers": "IND",
            "Clippers": "LAC", "Lakers": "LAL", "Grizzlies": "MEM", "Heat": "MIA",
            "Bucks": "MIL", "Timberwolves": "MIN", "Pelicans": "NOP", "Knicks": "NYK",
            "Thunder": "OKC", "Magic": "ORL", "76ers": "PHI", "Suns": "PHO",
            "Trail Blazers": "POR", "Kings": "SAC", "Spurs": "SAS", "Raptors": "TOR",
            "Jazz": "UTA", "Wizards": "WAS"
        }
        
        # Split teams and clean up
        team_parts = teams.split(" vs ")
        if len(team_parts) != 2:
            logger.debug(f"Invalid team format: {teams}")
            return None
            
        team1, team2 = team_parts[0].strip(), team_parts[1].strip()
        
        # Try to find teams in the mapping
        home_team = None
        away_team = None
        
        # Look for team names in the mapping
        for team_name, abbr in nba_team_mapping.items():
            if team_name in team1:
                home_team = abbr
            elif team_name in team2:
                away_team = abbr
                
        if not (home_team and away_team):
            logger.debug(f"Could not identify teams from: {teams}")
            return None
            
        # Construct URL based on league
        base_url = "https://www.basketball-reference.com" if league == "nba" else "https://www.sports-reference.com/cbb"
        urls = [
            f"{base_url}/boxscores/{date_str}0{home_team}.html",
            f"{base_url}/boxscores/{date_str}0{away_team}.html"
        ]
        
        for url in urls:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract box score tables
                    basic_stats = {}
                    advanced_stats = {}
                    
                    # Get all player stats tables
                    tables = soup.find_all('table', {'class': 'stats_table'})
                    
                    for table in tables:
                        table_id = table.get('id', '')
                        if not table_id or 'game-basic' not in table_id:
                            continue
                            
                        team_name = table_id.split('-')[0].upper()
                        rows = table.find_all('tr')
                        
                        if not rows:
                            continue
                            
                        for row in rows[1:]:  # Skip header row
                            cols = row.find_all(['th', 'td'])
                            
                            # Skip if no columns or if it's a header row
                            if not cols or cols[0].get('class', [''])[0] == 'thead':
                                continue
                                
                            try:
                                player_name = cols[0].text.strip()
                                if not player_name:
                                    continue
                                    
                                # Only process if we have all required columns
                                if len(cols) >= 17:
                                    stats = {
                                        'MIN': cols[1].text.strip(),
                                        'FG': cols[2].text.strip(),
                                        'FGA': cols[3].text.strip(),
                                        'FG%': cols[4].text.strip(),
                                        '3P': cols[5].text.strip(),
                                        '3PA': cols[6].text.strip(),
                                        '3P%': cols[7].text.strip(),
                                        'FT': cols[8].text.strip(),
                                        'FTA': cols[9].text.strip(),
                                        'FT%': cols[10].text.strip(),
                                        'ORB': cols[11].text.strip(),
                                        'DRB': cols[12].text.strip(),
                                        'TRB': cols[13].text.strip(),
                                        'AST': cols[14].text.strip(),
                                        'STL': cols[15].text.strip(),
                                        'BLK': cols[16].text.strip(),
                                        'TOV': cols[17].text.strip() if len(cols) > 17 else '',
                                        'PF': cols[18].text.strip() if len(cols) > 18 else '',
                                        'PTS': cols[19].text.strip() if len(cols) > 19 else ''
                                    }
                                    
                                    if team_name not in basic_stats:
                                        basic_stats[team_name] = {}
                                    basic_stats[team_name][player_name] = stats
                            except IndexError as e:
                                logger.debug(f"Error processing player row: {str(e)}")
                                continue
                    
                    if basic_stats:
                        return {
                            'url': url,
                            'basic_stats': basic_stats,
                            'advanced_stats': advanced_stats
                        }
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error fetching URL {url}: {str(e)}")
                continue
                    
        logger.debug(f"No box score found for {teams} on {date}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping basketball-reference: {str(e)}")
        return None

def get_football_reference_boxscore(teams: str, date: datetime, league: str = "nfl") -> Optional[Dict]:
    """
    Scrape pro-football-reference.com or sports-reference.com/cfb for the game's box score.
    
    Args:
        teams (str): Team names
        date (datetime): Game date
        league (str): "nfl" or "ncaaf"
        
    Returns:
        Optional[Dict]: Box score data if found, None otherwise
    """
    try:
        # Format date for URL
        date_str = date.strftime("%Y%m%d")
        
        # NFL team mappings
        nfl_team_mapping = {
            "Cardinals": "crd", "Falcons": "atl", "Ravens": "rav", "Bills": "buf",
            "Panthers": "car", "Bears": "chi", "Bengals": "cin", "Browns": "cle",
            "Cowboys": "dal", "Broncos": "den", "Lions": "det", "Packers": "gnb",
            "Texans": "htx", "Colts": "clt", "Jaguars": "jax", "Chiefs": "kan",
            "Raiders": "rai", "Chargers": "sdg", "Rams": "ram", "Dolphins": "mia",
            "Vikings": "min", "Patriots": "nwe", "Saints": "nor", "Giants": "nyg",
            "Jets": "nyj", "Eagles": "phi", "Steelers": "pit", "49ers": "sfo",
            "Seahawks": "sea", "Buccaneers": "tam", "Titans": "oti", "Commanders": "was"
        }
        
        # Split teams and clean up
        team_parts = teams.split(" vs ")
        if len(team_parts) != 2:
            logger.debug(f"Invalid team format: {teams}")
            return None
            
        team1, team2 = team_parts[0].strip(), team_parts[1].strip()
        
        # Try to find teams in the mapping
        home_team = None
        away_team = None
        
        # Look for team names in the mapping
        for team_name, abbr in nfl_team_mapping.items():
            if team_name in team1:
                home_team = abbr
            elif team_name in team2:
                away_team = abbr
                
        if not (home_team and away_team):
            logger.debug(f"Could not identify teams from: {teams}")
            return None
            
        # Construct URL based on league
        base_url = "https://www.pro-football-reference.com" if league == "nfl" else "https://www.sports-reference.com/cfb"
        urls = [
            f"{base_url}/boxscores/{date_str}0{home_team}.htm",
            f"{base_url}/boxscores/{date_str}0{away_team}.htm"
        ]
        
        for url in urls:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract box score tables
                    basic_stats = {}
                    
                    # Get all player stats tables
                    tables = soup.find_all('table', {'class': 'stats_table'})
                    
                    for table in tables:
                        table_id = table.get('id', '')
                        if not table_id or 'game-basic' not in table_id:
                            continue
                            
                        team_name = table_id.split('-')[0].upper()
                        rows = table.find_all('tr')
                        
                        if not rows:
                            continue
                            
                        for row in rows[1:]:  # Skip header row
                            cols = row.find_all(['th', 'td'])
                            
                            # Skip if no columns or if it's a header row
                            if not cols or cols[0].get('class', [''])[0] == 'thead':
                                continue
                                
                            try:
                                player_name = cols[0].text.strip()
                                if not player_name:
                                    continue
                                    
                                # Process stats based on table type (passing, rushing, receiving)
                                stats = {}
                                for i, col in enumerate(cols[1:], 1):
                                    header = col.get('data-stat', f'stat_{i}')
                                    stats[header] = col.text.strip()
                                    
                                if team_name not in basic_stats:
                                    basic_stats[team_name] = {}
                                basic_stats[team_name][player_name] = stats
                            except IndexError as e:
                                logger.debug(f"Error processing player row: {str(e)}")
                                continue
                    
                    if basic_stats:
                        return {
                            'url': url,
                            'basic_stats': basic_stats
                        }
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error fetching URL {url}: {str(e)}")
                continue
                    
        logger.debug(f"No box score found for {teams} on {date}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping football-reference: {str(e)}")
        return None

def get_hockey_reference_boxscore(teams: str, date: datetime) -> Optional[Dict]:
    """
    Scrape hockey-reference.com for the game's box score.
    
    Args:
        teams (str): Team names
        date (datetime): Game date
        
    Returns:
        Optional[Dict]: Box score data if found, None otherwise
    """
    try:
        # Format date for URL
        date_str = date.strftime("%Y%m%d")
        
        # NHL team mappings
        nhl_team_mapping = {
            "Ducks": "ANA", "Coyotes": "ARI", "Bruins": "BOS", "Sabres": "BUF",
            "Flames": "CGY", "Hurricanes": "CAR", "Blackhawks": "CHI", "Avalanche": "COL",
            "Blue Jackets": "CBJ", "Stars": "DAL", "Red Wings": "DET", "Oilers": "EDM",
            "Panthers": "FLA", "Kings": "LAK", "Wild": "MIN", "Canadiens": "MTL",
            "Predators": "NSH", "Devils": "NJD", "Islanders": "NYI", "Rangers": "NYR",
            "Senators": "OTT", "Flyers": "PHI", "Penguins": "PIT", "Sharks": "SJS",
            "Kraken": "SEA", "Blues": "STL", "Lightning": "TBL", "Maple Leafs": "TOR",
            "Canucks": "VAN", "Golden Knights": "VEG", "Capitals": "WSH", "Jets": "WPG"
        }
        
        # Split teams and clean up
        team_parts = teams.split(" vs ")
        if len(team_parts) != 2:
            logger.debug(f"Invalid team format: {teams}")
            return None
            
        team1, team2 = team_parts[0].strip(), team_parts[1].strip()
        
        # Try to find teams in the mapping
        home_team = None
        away_team = None
        
        # Look for team names in the mapping
        for team_name, abbr in nhl_team_mapping.items():
            if team_name in team1:
                home_team = abbr
            elif team_name in team2:
                away_team = abbr
                
        if not (home_team and away_team):
            logger.debug(f"Could not identify teams from: {teams}")
            return None
            
        # Construct possible URLs
        urls = [
            f"https://www.hockey-reference.com/boxscores/{date_str}0{home_team}.html",
            f"https://www.hockey-reference.com/boxscores/{date_str}0{away_team}.html"
        ]
        
        for url in urls:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract box score tables
                    basic_stats = {}
                    
                    # Get all player stats tables
                    tables = soup.find_all('table', {'class': 'stats_table'})
                    
                    for table in tables:
                        table_id = table.get('id', '')
                        if not table_id or 'game-basic' not in table_id:
                            continue
                            
                        team_name = table_id.split('-')[0].upper()
                        rows = table.find_all('tr')
                        
                        if not rows:
                            continue
                            
                        for row in rows[1:]:  # Skip header row
                            cols = row.find_all(['th', 'td'])
                            
                            # Skip if no columns or if it's a header row
                            if not cols or cols[0].get('class', [''])[0] == 'thead':
                                continue
                                
                            try:
                                player_name = cols[0].text.strip()
                                if not player_name:
                                    continue
                                    
                                # Process stats
                                stats = {}
                                for i, col in enumerate(cols[1:], 1):
                                    header = col.get('data-stat', f'stat_{i}')
                                    stats[header] = col.text.strip()
                                    
                                if team_name not in basic_stats:
                                    basic_stats[team_name] = {}
                                basic_stats[team_name][player_name] = stats
                            except IndexError as e:
                                logger.debug(f"Error processing player row: {str(e)}")
                                continue
                    
                    if basic_stats:
                        return {
                            'url': url,
                            'basic_stats': basic_stats
                        }
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error fetching URL {url}: {str(e)}")
                continue
                    
        logger.debug(f"No box score found for {teams} on {date}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping hockey-reference: {str(e)}")
        return None

def get_soccer_reference_boxscore(teams: str, date: datetime) -> Optional[Dict]:
    """
    Scrape fbref.com for the game's box score.
    
    Args:
        teams (str): Team names
        date (datetime): Game date
        
    Returns:
        Optional[Dict]: Box score data if found, None otherwise
    """
    try:
        # Format date for URL
        date_str = date.strftime("%Y%m%d")
        
        # Clean team names and construct search URL
        team_parts = teams.split(" vs ")
        if len(team_parts) != 2:
            logger.debug(f"Invalid team format: {teams}")
            return None
            
        team1, team2 = team_parts[0].strip(), team_parts[1].strip()
        
        # FBRef uses a different URL structure, we need to search for the match
        search_url = f"https://fbref.com/en/matches/{date_str}"
        
        try:
            response = requests.get(search_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the match in the day's matches
                matches = soup.find_all('div', {'class': 'match'})
                
                for match in matches:
                    home = match.find('div', {'class': 'home'}).text.strip()
                    away = match.find('div', {'class': 'away'}).text.strip()
                    
                    if (team1 in home and team2 in away) or (team1 in away and team2 in home):
                        match_url = match.find('a')['href']
                        if match_url:
                            # Get the full match stats
                            match_response = requests.get(f"https://fbref.com{match_url}")
                            if match_response.status_code == 200:
                                match_soup = BeautifulSoup(match_response.text, 'html.parser')
                                
                                # Extract stats tables
                                basic_stats = {}
                                
                                # Get all stats tables
                                tables = match_soup.find_all('table', {'class': 'stats_table'})
                                
                                for table in tables:
                                    team_name = table.get('id', '').split('_')[0].upper()
                                    rows = table.find_all('tr')
                                    
                                    if not rows:
                                        continue
                                        
                                    for row in rows[1:]:  # Skip header row
                                        cols = row.find_all(['th', 'td'])
                                        
                                        try:
                                            player_name = cols[0].text.strip()
                                            if not player_name:
                                                continue
                                                
                                            # Process stats
                                            stats = {}
                                            for i, col in enumerate(cols[1:], 1):
                                                header = col.get('data-stat', f'stat_{i}')
                                                stats[header] = col.text.strip()
                                                
                                            if team_name not in basic_stats:
                                                basic_stats[team_name] = {}
                                            basic_stats[team_name][player_name] = stats
                                        except IndexError as e:
                                            logger.debug(f"Error processing player row: {str(e)}")
                                            continue
                                
                                if basic_stats:
                                    return {
                                        'url': f"https://fbref.com{match_url}",
                                        'basic_stats': basic_stats
                                    }
                                
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error fetching URL {search_url}: {str(e)}")
            
        logger.debug(f"No box score found for {teams} on {date}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping fbref: {str(e)}")
        return None

def get_tennis_match_result(player1: str, player2: str, date: datetime) -> Optional[Dict]:
    """
    Scrape tennis match results from ATP/WTA websites.
    
    Args:
        player1 (str): First player's name
        player2 (str): Second player's name
        date (datetime): Match date
        
    Returns:
        Optional[Dict]: Match statistics if found, None otherwise
    """
    try:
        # Format date for URL
        date_str = date.strftime("%Y-%m-%d")
        
        # Try ATP website first
        atp_url = f"https://www.atptour.com/en/scores/archive/{date_str}"
        wta_url = f"https://www.wtatennis.com/scores/{date_str}"
        
        urls = [atp_url, wta_url]
        
        for url in urls:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for match results
                    matches = soup.find_all('div', {'class': 'match-row'})
                    
                    for match in matches:
                        # Extract player names
                        players = match.find_all('a', {'class': 'player-name'})
                        if len(players) != 2:
                            continue
                            
                        match_player1 = players[0].text.strip()
                        match_player2 = players[1].text.strip()
                        
                        # Check if this is our match
                        if (player1 in match_player1 and player2 in match_player2) or \
                           (player1 in match_player2 and player2 in match_player1):
                            
                            # Extract score
                            score = match.find('div', {'class': 'score'})
                            if not score:
                                continue
                                
                            sets = []
                            for set_score in score.find_all('span', {'class': 'set-score'}):
                                sets.append(set_score.text.strip())
                                
                            if sets:
                                return {
                                    'url': url,
                                    'player1': match_player1,
                                    'player2': match_player2,
                                    'sets': sets,
                                    'source': 'ATP/WTA Tour'
                                }
                                
            except requests.exceptions.RequestException as e:
                logger.debug(f"Error fetching URL {url}: {str(e)}")
                continue
                
        # If ATP/WTA sites don't have it, try flashscore.com
        flashscore_url = "https://www.flashscore.com/tennis"
        try:
            response = requests.get(flashscore_url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find the match
                match_date = date.strftime("%Y%m%d")
                match_container = soup.find('div', {'id': f'g_2_{match_date}'})
                
                if match_container:
                    # Extract score
                    score_elements = match_container.find_all('div', {'class': 'score'})
                    sets = [score.text.strip() for score in score_elements]
                    
                    if sets:
                        return {
                            'url': flashscore_url,
                            'player1': player1,
                            'player2': player2,
                            'sets': sets,
                            'source': 'Flashscore'
                        }
                        
        except requests.exceptions.RequestException as e:
            logger.debug(f"Error fetching flashscore: {str(e)}")
            
        logger.debug(f"No tennis match results found for {player1} vs {player2} on {date}")
        return None
        
    except Exception as e:
        logger.error(f"Error scraping tennis match: {str(e)}")
        return None

def get_boxscore(sport: str, teams: str, date_str: str) -> Optional[Dict]:
    """
    Get box score data from the appropriate sports reference website.
    
    Args:
        sport (str): Sport type (nba, nfl, ncaaf, ncaab, nhl, soccer, tennis)
        teams (str): Team/player names
        date_str (str): Date string in YYYY-MM-DD format
        
    Returns:
        Optional[Dict]: Box score data if found, None otherwise
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        
        if sport == "tennis":
            # Split player names
            players = teams.split(" vs ")
            if len(players) == 2:
                return get_tennis_match_result(players[0].strip(), players[1].strip(), date)
            return None
            
        elif sport == "nba":
            return get_basketball_reference_boxscore(teams, date, "nba")
            
        elif sport == "ncaab":
            return get_basketball_reference_boxscore(teams, date, "ncaab")
            
        elif sport == "nfl":
            return get_football_reference_boxscore(teams, date, "nfl")
            
        elif sport == "ncaaf":
            return get_football_reference_boxscore(teams, date, "ncaaf")
            
        elif sport == "nhl":
            return get_hockey_reference_boxscore(teams, date)
            
        elif sport == "soccer":
            return get_soccer_reference_boxscore(teams, date)
            
        else:
            logger.debug(f"Unsupported sport: {sport}")
            return None
            
    except ValueError as e:
        logger.error(f"Error parsing date: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting box score: {str(e)}")
        return None 