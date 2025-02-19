import os
from pathlib import Path

class BaseConfig:
    """Base configuration with common settings."""
    
    # Project structure
    PROJECT_ROOT = Path("/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev")
    APP_DIR = PROJECT_ROOT / "app"
    DATA_DIR = PROJECT_ROOT / "data"
    LOGS_DIR = PROJECT_ROOT / "logs"
    MODELS_DIR = PROJECT_ROOT / "models"
    ANALYSIS_DIR = PROJECT_ROOT / "analysis"
    
    # Ensure all directories exist
    for directory in [APP_DIR, DATA_DIR, LOGS_DIR, MODELS_DIR, ANALYSIS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    
    # Database
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASEDIR, 'betting_data.db')
    
    # Caching
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Scraping
    PAGE_LOAD_WAIT = int(os.environ.get('PAGE_LOAD_WAIT', '10'))
    TARGET_URL = os.environ.get('TARGET_URL', 'https://oddsjam.com/positive-ev')
    SCRAPE_INTERVAL = int(os.environ.get('SCRAPE_INTERVAL', '300'))  # 5 minutes
    
    # Backup
    BACKUP_DIR = APP_DIR / 'backups'
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_RETENTION_DAYS = int(os.environ.get('LOG_RETENTION_DAYS', '7'))
    
    # Chrome
    CHROME_PROFILE = Path(os.path.expanduser('~')) / 'Library/Application Support/Google/Chrome/ScraperProfile'
    CHROME_OPTIONS = [
        '--headless',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1920,1080',
        '--disable-blink-features=AutomationControlled'
    ]
    
    # Selectors for scraping
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
        'bet_size': "p.text-sm.__className_179fbf.self-center.font-semibold.text-white",
        'win_probability': "p.text-sm.text-white:last-child"
    }
    
    # Model settings
    MODEL_SETTINGS = {
        'min_samples_for_training': 1000,
        'test_size': 0.2,
        'random_state': 42,
        'cv_folds': 5,
        'confidence_threshold': 0.6
    }
    
    # Feature engineering settings
    FEATURE_SETTINGS = {
        'rolling_window_sizes': [5, 10, 20],
        'min_games_for_stats': 5,
        'max_games_for_stats': 82
    }

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    CACHE_TYPE = "simple"
    LOG_LEVEL = "DEBUG"
    
    # Development database
    DATABASE_PATH = os.path.join(BaseConfig.BASEDIR, 'dev_betting_data.db')

class TestingConfig(BaseConfig):
    """Testing configuration."""
    DEBUG = False
    TESTING = True
    
    # Test database
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests
    
    # Test-specific settings
    CACHE_TYPE = "null"
    LOG_LEVEL = "DEBUG"
    PAGE_LOAD_WAIT = 1
    SCRAPE_INTERVAL = 10

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Production settings must be set via environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_PATH = os.environ.get('DATABASE_PATH')
    
    # Production-specific settings
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    LOG_LEVEL = "INFO"
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', False)

# Dictionary to map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

# Function to get current config based on environment
def get_config():
    """Get the configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

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
    'bet_size': "p.text-sm.__className_179fbf.self-center.font-semibold.text-white",
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