import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
from app.scraper.services import ScraperService
from app.models import Bet, BetResult

# Import the modules to test
from scraper import (
    parse_cleaned_data,
    setup_chrome_driver,
    upsert_data,
    create_daily_backup
)

# Sample HTML for testing
SAMPLE_HTML = """
<div id="betting-tool-table-row">
    <p id="percent-cell">5.2%</p>
    <div data-testid="event-cell"><p class="text-xs">Wed, Feb 5 at 2:30 PM</p></div>
    <p class="text-sm font-semibold">Team A vs Team B</p>
    <p class="text-sm">NBA</p>
    <p class="text-sm text-brand-purple">Player Points</p>
    <div class="tour__bet_and_books"><p class="flex-1">John Doe Over 20.5</p></div>
    <p class="text-sm font-bold">+110</p>
    <img alt="DraftKings" src="sportsbook.png"/>
    <p class="text-sm font-semibold text-white">$50</p>
    <p class="text-sm text-white">52%</p>
</div>
"""

@pytest.fixture
def sample_soup():
    return BeautifulSoup(SAMPLE_HTML, 'html.parser')

@pytest.fixture
def mock_db():
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        yield mock_cursor

@pytest.fixture
def scraper_service(app):
    """Create a scraper service instance with app context."""
    return ScraperService()

@pytest.fixture
def sample_bet_block():
    """Create a sample bet block HTML for testing."""
    return """
    <div class="bet-block">
        <span class="ev-percent">5.2%</span>
        <span class="event-time">2024-02-15 20:00:00</span>
        <span class="teams">Lakers vs Warriors</span>
        <span class="sport">NBA</span>
        <span class="bet-type">Moneyline</span>
        <span class="description">Lakers to win</span>
        <span class="odds">+150</span>
        <img class="sportsbook-logo" alt="DraftKings" src="logo.png"/>
        <span class="bet-size">$100</span>
        <span class="win-prob">55%</span>
    </div>
    """

def test_parse_cleaned_data(sample_soup):
    timestamp = "2024-02-05 14:30:00"
    result = parse_cleaned_data(sample_soup, timestamp)
    
    assert len(result) == 1
    bet = result[0]
    assert bet["EV Percent"] == "5.2"
    assert bet["Event Teams"] == "Team A vs Team B"
    assert bet["Sport/League"] == "NBA"
    assert bet["Bet Type"] == "Player Points"
    assert bet["Description"] == "John Doe Over 20.5"
    assert bet["Odds"] == "+110"
    assert bet["Sportsbook"] == "DraftKings"
    assert bet["Win Probability"] == "52"
    assert bet["Bet Size"] == "50"
    assert bet["timestamp"] == timestamp

def test_setup_chrome_driver():
    with patch('selenium.webdriver.Chrome') as mock_chrome:
        driver = setup_chrome_driver()
        
        # Verify Chrome was initialized with correct options
        options = mock_chrome.call_args[1]['options']
        assert isinstance(options, Options)
        
        # Check that required Chrome options were set
        option_args = options.arguments
        assert "--disable-blink-features=AutomationControlled" in option_args
        assert "--no-sandbox" in option_args
        assert "--disable-dev-shm-usage" in option_args
        assert "--headless" in option_args

def test_upsert_data(mock_db):
    test_data = [{
        "bet_id": "test123",
        "timestamp": "2024-02-05 14:30:00",
        "EV Percent": "5.2",
        "Event Time": "2024-02-05 14:30",
        "Event Teams": "Team A vs Team B",
        "Sport/League": "NBA",
        "Bet Type": "Player Points",
        "Description": "John Doe Over 20.5",
        "Odds": "+110",
        "Sportsbook": "DraftKings",
        "Bet Size": "50",
        "Win Probability": "52"
    }]
    
    upsert_data(test_data)
    
    # Verify the correct SQL was executed
    mock_db.execute.assert_called_once()
    sql_call = mock_db.execute.call_args[0]
    assert "INSERT INTO betting_data" in sql_call[0]
    assert len(sql_call[1]) == 13  # 12 fields plus empty result

@pytest.mark.parametrize("file_exists", [True, False])
def test_create_daily_backup(file_exists):
    with patch('os.path.exists') as mock_exists, \
         patch('shutil.copy') as mock_copy, \
         patch('logging.info') as mock_log, \
         patch('scraper.DB_FILE', '/tmp/test_positive_ev/test.db'), \
         patch('scraper.BACKUP_FOLDER', '/tmp/test_positive_ev/backups'):
        
        mock_exists.return_value = file_exists
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%m%d%y")
        expected_backup_path = f"/tmp/test_positive_ev/backups/betting_data_{yesterday}.db"
        
        create_daily_backup()
        
        if not file_exists:
            mock_copy.assert_called_once()
            assert mock_copy.call_args[0][1] == expected_backup_path  # Verify exact path
            assert yesterday in mock_copy.call_args[0][1]
        else:
            mock_copy.assert_not_called()
            mock_log.assert_called_once_with(f"Backup already exists for {yesterday}: {expected_backup_path}")

def test_parse_cleaned_data_empty():
    empty_soup = BeautifulSoup("", 'html.parser')
    result = parse_cleaned_data(empty_soup, "2024-02-05 14:30:00")
    assert result == []

def test_parse_cleaned_data_missing_fields(sample_soup):
    # Remove some fields from the soup
    for tag in sample_soup.select("p.text-sm.font-bold"):
        tag.decompose()
    
    result = parse_cleaned_data(sample_soup, "2024-02-05 14:30:00")
    assert len(result) == 1
    assert result[0]["Odds"] == "N/A"

def test_upsert_data_empty(mock_db):
    upsert_data([])
    mock_db.execute.assert_not_called()

def test_upsert_data_invalid_data(mock_db):
    with pytest.raises(Exception):
        upsert_data([{"invalid": "data"}])

def test_parse_bet_block(scraper_service, sample_bet_block):
    """Test parsing of individual bet blocks."""
    soup = BeautifulSoup(sample_bet_block, 'html.parser')
    timestamp = datetime.utcnow()
    
    result = scraper_service.parse_bet_block(soup, timestamp, 0)
    
    assert result is not None
    assert result['ev_percent'] == '5.2'
    assert result['event_teams'] == 'Lakers vs Warriors'
    assert result['sport_league'] == 'NBA'
    assert result['bet_type'] == 'Moneyline'
    assert result['description'] == 'Lakers to win'
    assert result['odds'] == '+150'
    assert result['sportsbook'] == 'DraftKings'
    assert result['bet_size'] == '100'
    assert result['win_probability'] == '55'

def test_generate_bet_id(scraper_service):
    """Test bet ID generation."""
    row = {
        'event_time': '2024-02-15 20:00:00',
        'event_teams': 'Lakers vs Warriors',
        'sport_league': 'NBA',
        'bet_type': 'Moneyline',
        'description': 'Lakers to win'
    }
    
    bet_id = scraper_service.generate_bet_id(row)
    expected_id = '2024-02-15 20:00:00_Lakers vs Warriors_NBA_Moneyline_Lakers to win'
    
    assert bet_id == expected_id

def test_save_betting_data(scraper_service, app, db):
    """Test saving betting data to database."""
    data = [{
        'bet_id': 'test_bet_1',
        'timestamp': datetime.utcnow(),
        'ev_percent': '5.2',
        'event_time': '2024-02-15 20:00:00',
        'event_teams': 'Lakers vs Warriors',
        'sport_league': 'NBA',
        'bet_type': 'Moneyline',
        'description': 'Lakers to win',
        'odds': '+150',
        'sportsbook': 'DraftKings',
        'bet_size': '100',
        'win_probability': '55'
    }]
    
    with app.app_context():
        new_bets = scraper_service.save_betting_data(data)
        
        assert len(new_bets) == 1
        saved_bet = Bet.query.filter_by(bet_id='test_bet_1').first()
        assert saved_bet is not None
        assert saved_bet.ev_percent == 5.2
        assert saved_bet.sport_league == 'NBA'

def test_cleanup_old_data(scraper_service, app, db):
    """Test cleanup of old data."""
    # Create some test data
    old_date = datetime.utcnow() - timedelta(days=40)
    bet = Bet(
        bet_id='old_bet_1',
        timestamp=old_date,
        ev_percent=5.2,
        event_time=old_date,
        event_teams='Lakers vs Warriors',
        sport_league='NBA',
        bet_type='Moneyline',
        description='Lakers to win',
        odds=150,
        sportsbook='DraftKings',
        result='W'
    )
    
    with app.app_context():
        db.session.add(bet)
        db.session.commit()
        
        cleaned_count = scraper_service.cleanup_old_data()
        
        assert cleaned_count == 1
        assert Bet.query.filter_by(bet_id='old_bet_1').first() is None
 