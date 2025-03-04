import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Database configuration
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'chatbot.db')

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

# JWT configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-key-for-development-only')
JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7  # 7 days

# Flask configuration
DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
TESTING = False
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-for-development-only')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'app.log')

# Ensure log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Positive EV database path (for migration)
POSITIVE_EV_DB_PATH = os.getenv(
    'POSITIVE_EV_DB_PATH', 
    '/Users/michaelfuscoletti/Desktop/mega-plan/positive-ev/app/betting_data.db'
)

# Free tier limits
FREE_TIER_DAILY_RECOMMENDATIONS = 3

# Timeout settings (in hours)
TIMEOUT_DURATIONS = {
    4: 24,      # 4th violation: 24 hours
    5: 72,      # 5th violation: 3 days
    6: 168,     # 6th violation: 1 week
    7: 720      # 7th+ violation: 1 month
}
