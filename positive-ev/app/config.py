import os

# Base Directory Configuration
BASE_DIR = "/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app"

# File Paths
DB_FILE = os.path.join(BASE_DIR, "betting_data.db")
LOGS_FOLDER = os.path.join(BASE_DIR, "logs")
BACKUP_FOLDER = os.path.join(BASE_DIR, "backups")
LOG_FILE = os.path.join(LOGS_FOLDER, "scraping.log")
NBA_STATS_LOG_FILE = os.path.join(LOGS_FOLDER, "nba_stats_scraping.log")
CHROME_PROFILE = os.path.expanduser('~/Library/Application Support/Google/Chrome/ScraperProfile')

# Scraping Configuration
TARGET_URL = "https://oddsjam.com/betting-tools/positive-ev"
PAGE_LOAD_WAIT = 10  # seconds to wait for page load

# NBA Stats API Configuration
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com"
}
NBA_STATS_URLS = {
    "scoreboard": "https://stats.nba.com/stats/scoreboardv2",
    "summary": "https://stats.nba.com/stats/boxscoresummaryv2",
    "boxscore": "https://stats.nba.com/stats/boxscoretraditionalv2"
}

# Backup and Cleanup Settings
BACKUP_RETENTION_DAYS = 10
LOG_RETENTION_HOURS = 2

# Chrome Options
CHROME_OPTIONS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--headless"
]

# CSS Selectors
SELECTORS = {
    'bet_blocks': "div#betting-tool-table-row",
    'ev_percent': "p#percent-cell",
    'event_time': "div[data-testid='event-cell'] > p.text-xs",
    'event_teams': "p.text-sm.font-semibold",
    'sport_league': "p.text-sm:not(.font-semibold)",
    'bet_type': "p.text-sm.text-brand-purple",
    'description': "div.tour__bet_and_books p.flex-1",
    'odds': "p.text-sm.font-bold",
    'sportsbook': "img[alt]",
    'bet_size': "p.text-sm.font-semibold.text-white:not(:last-child)",
    'win_probability': "p.text-sm.text-white:last-child"
}

# NBA Team Name Normalization
TEAM_NORMALIZATION_MAP = {
    "Memphis Grizzlies": "Memphis",
    "Golden State Warriors": "Golden State",
    "Denver Nuggets": "Denver",
    "San Antonio Spurs": "San Antonio",
    "Utah Jazz": "Utah",
    "Miami Heat": "Miami",
    "New York Knicks": "New York",
    "Chicago Bulls": "Chicago",
    "Portland Trail Blazers": "Portland",
    "Milwaukee Bucks": "Milwaukee",
    "Minnesota Timberwolves": "Minnesota",
    "Detroit Pistons": "Detroit",
    "Phoenix Suns": "Phoenix",
    "Indiana Pacers": "Indiana",
    "Atlanta Hawks": "Atlanta",
    "Los Angeles Clippers": "LA",
    "Los Angeles Lakers": "Los Angeles",
    "Sacramento Kings": "Sacramento",
    "Houston Rockets": "Houston",
    "Orlando Magic": "Orlando",
    "New Orleans Pelicans": "New Orleans",
    "Washington Wizards": "Washington",
    "Boston Celtics": "Boston",
    "Oklahoma City Thunder": "Oklahoma City",
    "Charlotte Hornets": "Charlotte",
    "Cleveland Cavaliers": "Cleveland",
    "Philadelphia 76ers": "Philadelphia",
    "Brooklyn Nets": "Brooklyn",
    "Toronto Raptors": "Toronto",
    "Dallas Mavericks": "Dallas"
}

# Stats Mapping
STATS_MAPPING = {
    "Points": 0,
    "Rebounds": 1,
    "Assists": 2,
    "Steals": 3,
    "Blocks": 4,
    "Turnovers": 5,
    "Made Threes": 6
}

# Results Update Log File
RESULTS_UPDATE_LOG_FILE = os.path.join(LOGS_FOLDER, "results_update.log") 