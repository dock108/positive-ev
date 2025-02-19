import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from update_results import (
    normalize_team_name,
    extract_and_normalize_teams,
    determine_result,
    parse_bet_details,
    find_game_id,
    update_bet_results
)

# Sample player stats tuples (points, rebounds, assists, steals, blocks, turnovers, made_threes)
SAMPLE_PLAYER_STATS = (25, 10, 8, 2, 1, 3, 3)  # Good all-around game
SAMPLE_TRIPLE_DOUBLE = (28, 12, 11, 2, 1, 3, 3)  # Triple double
SAMPLE_DOUBLE_DOUBLE = (25, 12, 5, 2, 1, 3, 3)  # Double double
SAMPLE_DNP_STATS = (None, None, None, None, None, None, None)  # Did not play

@pytest.fixture
def mock_db():
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        yield mock_cursor

def test_normalize_team_name():
    assert normalize_team_name("Los Angeles Lakers") == "Los Angeles"
    assert normalize_team_name("Golden State Warriors") == "Golden State"
    assert normalize_team_name("Unknown Team") == "Unknown Team"  # Returns input if not found
    assert normalize_team_name(" Boston Celtics ") == "Boston"  # Handles whitespace

def test_extract_and_normalize_teams():
    # Test valid team names
    teams = extract_and_normalize_teams("Los Angeles Lakers vs Golden State Warriors")
    assert teams == ["Los Angeles", "Golden State"]
    
    # Test invalid format
    assert extract_and_normalize_teams("Invalid Format") is None
    
    # Test with extra whitespace
    teams = extract_and_normalize_teams(" Boston Celtics  vs  Miami Heat ")
    assert teams == ["Boston", "Miami"]

@pytest.mark.parametrize("stats,stat_types,condition,target,expected", [
    (SAMPLE_PLAYER_STATS, ["Points"], "Over", 20.0, "W"),  # Over points hit
    (SAMPLE_PLAYER_STATS, ["Points"], "Under", 30.0, "W"),  # Under points hit
    (SAMPLE_PLAYER_STATS, ["Points"], "Over", 30.0, "L"),  # Over points missed
    (SAMPLE_PLAYER_STATS, ["Points", "Rebounds"], "Over", 30.0, "W"),  # Combined stats over
    (SAMPLE_TRIPLE_DOUBLE, ["Triple Double"], None, None, "W"),  # Triple double hit
    (SAMPLE_DOUBLE_DOUBLE, ["Double Double"], None, None, "W"),  # Double double hit
    (SAMPLE_DNP_STATS, ["Points"], "Over", 20.0, "R"),  # DNP should refund
    (SAMPLE_PLAYER_STATS, ["Points"], "Over", 25.0, "R"),  # Exact match should refund
])
def test_determine_result(stats, stat_types, condition, target, expected):
    result = determine_result(stats, stat_types, condition, target)
    assert result == expected

@pytest.mark.parametrize("description,bet_type,expected", [
    (
        "LeBron James Over 25.5",
        "Player Points",
        ("LeBron James", ["Points"], "Over", 25.5)
    ),
    (
        "Nikola Jokic Player Double Double",
        "Player Double Double",
        ("Nikola Jokic", ["Double Double"], None, None)
    ),
    (
        "Stephen Curry Over 5.5",
        "Player Made Threes",
        ("Stephen Curry", ["Made Threes"], "Over", 5.5)
    ),
    (
        "Giannis Antetokounmpo Over 35.5",
        "Player Points + Rebounds",
        ("Giannis Antetokounmpo", ["Points", "Rebounds"], "Over", 35.5)
    )
])
def test_parse_bet_details(description, bet_type, expected):
    result = parse_bet_details(description, bet_type)
    assert result == expected

def test_find_game_id(mock_db):
    # Setup mock cursor to return a game ID
    mock_db.fetchone.return_value = ("0021234567",)
    
    game_id = find_game_id(
        mock_db,
        "Los Angeles Lakers vs Golden State Warriors",
        "Wed, Feb 5 at 7:30 PM"
    )
    
    assert game_id == "0021234567"
    # Verify the SQL query used correct team names
    sql_call = mock_db.execute.call_args[0]
    assert "Los Angeles" in sql_call[1]
    assert "Golden State" in sql_call[1]

def test_find_game_id_no_match(mock_db):
    # Setup mock cursor to return no match
    mock_db.fetchone.return_value = None
    
    game_id = find_game_id(
        mock_db,
        "Los Angeles Lakers vs Golden State Warriors",
        "Wed, Feb 5 at 7:30 PM"
    )
    
    assert game_id is None

def test_update_bet_results(mock_db):
    # Setup mock cursor to return test data
    mock_db.fetchall.return_value = [
        (1, "bet123", "Los Angeles Lakers vs Golden State Warriors",
         "Wed, Feb 5 at 7:30 PM", "Player Points", "Stephen Curry Over 25.5")
    ]
    mock_db.fetchone.side_effect = [
        ("0021234567",),  # Game ID
        (30, 5, 6, 2, 0, 2, 5)  # Player stats
    ]
    
    update_bet_results()
    
    # Verify the result was updated
    update_calls = [
        call for call in mock_db.execute.call_args_list 
        if "UPDATE betting_data SET result" in call[0][0]
    ]
    assert len(update_calls) == 1
    assert "bet123" in update_calls[0][0][1]
    assert "W" in update_calls[0][0][1]  # Should be a win (30 points > 25.5)

def test_update_bet_results_no_game(mock_db):
    # Setup mock cursor to return test data but no matching game
    mock_db.fetchall.return_value = [
        (1, "bet123", "Los Angeles Lakers vs Golden State Warriors",
         "Wed, Feb 5 at 7:30 PM", "Player Points", "Stephen Curry Over 25.5")
    ]
    mock_db.fetchone.return_value = None  # No game found
    
    update_bet_results()
    
    # Verify no update was made
    update_calls = [
        call for call in mock_db.execute.call_args_list 
        if "UPDATE betting_data SET result" in call[0][0]
    ]
    assert len(update_calls) == 0 