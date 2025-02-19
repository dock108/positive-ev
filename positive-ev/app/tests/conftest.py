import pytest
import os
import sys
from pathlib import Path
import tempfile
from app import create_app, db
from app.models import Bet, BetResult
from config import TestingConfig

# Add the app directory to Python path
app_path = Path(__file__).parent.parent
sys.path.append(str(app_path))

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv('BASE_DIR', '/tmp/test_positive_ev')
    monkeypatch.setenv('DB_FILE', '/tmp/test_positive_ev/test.db')

@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Clean up test files after tests."""
    yield
    if os.path.exists('/tmp/test_positive_ev'):
        import shutil
        shutil.rmtree('/tmp/test_positive_ev')

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to isolate the database for each test
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app(TestingConfig)
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'WTF_CSRF_ENABLED': False
    })

    # Create the database and load test data
    with app.app_context():
        db.create_all()
        yield app

    # Cleanup after test
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

@pytest.fixture
def _db(app):
    """Create and configure a new database for each test."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def sample_bet(_db):
    """Create a sample bet for testing."""
    bet = Bet(
        bet_id='test_bet_1',
        timestamp='2024-02-15 20:00:00',
        ev_percent=5.2,
        event_time='2024-02-15 20:00:00',
        event_teams='Lakers vs Warriors',
        sport_league='NBA',
        bet_type='Moneyline',
        description='Lakers to win',
        odds=150,
        sportsbook='DraftKings',
        bet_size=100,
        win_probability=55,
        result=None
    )
    _db.session.add(bet)
    _db.session.commit()
    return bet

@pytest.fixture
def sample_bet_result(_db, sample_bet):
    """Create a sample bet result for testing."""
    result = BetResult(
        bet_id=sample_bet.bet_id,
        result='W',
        profit_loss=150.0,
        settlement_time='2024-02-16 00:00:00',
        notes='Test result'
    )
    _db.session.add(result)
    _db.session.commit()
    return result 