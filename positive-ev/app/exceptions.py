class BettingAppError(Exception):
    """Base exception class for the betting application."""
    def __init__(self, message, error_code=None):
        super().__init__(message)
        self.error_code = error_code

class ScraperError(BettingAppError):
    """Base class for scraper-related errors."""
    pass

class WebDriverError(ScraperError):
    """Raised when there are issues with the WebDriver."""
    pass

class DataExtractionError(ScraperError):
    """Raised when data cannot be extracted from the page."""
    pass

class DatabaseError(BettingAppError):
    """Base class for database-related errors."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when unable to connect to the database."""
    pass

class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""
    pass

class ModelError(BettingAppError):
    """Base class for model-related errors."""
    pass

class InsufficientDataError(ModelError):
    """Raised when there is not enough data for model training."""
    pass

class ModelTrainingError(ModelError):
    """Raised when model training fails."""
    pass

class ModelPredictionError(ModelError):
    """Raised when model prediction fails."""
    pass

class ConfigurationError(BettingAppError):
    """Raised when there are configuration-related issues."""
    pass

class ValidationError(BettingAppError):
    """Raised when data validation fails."""
    pass

class APIError(BettingAppError):
    """Base class for API-related errors."""
    pass

class APIRequestError(APIError):
    """Raised when an API request fails."""
    pass

class APIResponseError(APIError):
    """Raised when there are issues with the API response."""
    pass

class BacktestError(BettingAppError):
    """Base class for backtesting-related errors."""
    pass

class SimulationError(BettingAppError):
    """Base class for simulation-related errors."""
    pass

# Error code mapping
ERROR_CODES = {
    WebDriverError: 1001,
    DataExtractionError: 1002,
    DatabaseConnectionError: 2001,
    DatabaseQueryError: 2002,
    InsufficientDataError: 3001,
    ModelTrainingError: 3002,
    ModelPredictionError: 3003,
    ConfigurationError: 4001,
    ValidationError: 4002,
    APIRequestError: 5001,
    APIResponseError: 5002,
    BacktestError: 6001,
    SimulationError: 7001
} 