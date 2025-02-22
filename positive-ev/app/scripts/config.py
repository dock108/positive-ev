import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration - from .env
API_KEY = os.getenv('OPENAI_API_KEY')
MODEL = os.getenv('OPENAI_MODEL')  # Using the model specified in .env
TEMPERATURE = float(os.getenv('TEMPERATURE', '0.3'))

# Retry Configuration - from .env
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))

# Confidence Thresholds - from .env
MIN_CONFIDENCE_FOR_AUTO_UPDATE = float(os.getenv('MIN_CONFIDENCE_FOR_AUTO_UPDATE', '80.0'))

# Rate Limiting - from .env
REQUESTS_PER_MINUTE = int(os.getenv('REQUESTS_PER_MINUTE', '50'))

# Non-configurable settings
DEFAULT_MODEL = "gpt-4o-mini"  # Default model to use if not specified in env
DEFAULT_TEMPERATURE = 0.3  # Fallback if not specified in .env
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5
DEFAULT_CONFIDENCE_THRESHOLD = 80.0
DEFAULT_REQUESTS_PER_MINUTE = 50

# Use defaults if env vars not set
if not MODEL:
    MODEL = DEFAULT_MODEL
if not TEMPERATURE:
    TEMPERATURE = DEFAULT_TEMPERATURE
if not MAX_RETRIES:
    MAX_RETRIES = DEFAULT_MAX_RETRIES
if not RETRY_DELAY:
    RETRY_DELAY = DEFAULT_RETRY_DELAY
if not MIN_CONFIDENCE_FOR_AUTO_UPDATE:
    MIN_CONFIDENCE_FOR_AUTO_UPDATE = DEFAULT_CONFIDENCE_THRESHOLD
if not REQUESTS_PER_MINUTE:
    REQUESTS_PER_MINUTE = DEFAULT_REQUESTS_PER_MINUTE

# API Endpoints
API_ENDPOINT = "https://api.openai.com/v1/chat/completions"  # Using chat completions endpoint

# Model Capabilities
MAX_CONTEXT_TOKENS = 200000
MAX_OUTPUT_TOKENS = 100000 