import pytest
from unittest.mock import Mock, patch, ANY
from datetime import datetime, timedelta
import json

from scrape_boxscores import (
    fetch_game_ids,
    fetch_boxscore_with_quarters,
    parse_and_save_boxscore,
    main
)

# Sample API responses
SAMPLE_SCOREBOARD_RESPONSE = {
    "resultSets": [{
        "rowSet": [
            ["20240205", "0022300001", "0021234567", "Final", "20240205"],  # Game ID is at index 2
            ["20240205", "0022300002", "0021234568", "Final", "20240205"]
        ]
    }]
}

SAMPLE_SUMMARY_RESPONSE = {
    "resultSets": [
        {
            "name": "GameSummary",
            "headers": ["GAME_DATE_EST", "GAME_ID", "HOME_TEAM_ID", "VISITOR_TEAM_ID"],
            "rowSet": [["2024-02-05", "0021234567", "1610612738", "1610612739"]]
        },
        {
            "name": "LineScore",
            "headers": ["GAME_ID", "TEAM_ID", "TEAM_CITY_NAME", "PTS_QTR1", "PTS_QTR2", "PTS_QTR3", "PTS_QTR4", "PTS"],
            "rowSet": [
                ["0021234567", "1610612738", "Boston", 30, 25, 28, 27, 110],
                ["0021234567", "1610612739", "Cleveland", 28, 22, 25, 25, 100]
            ]
        }
    ]
}

SAMPLE_BOXSCORE_RESPONSE = {
    "resultSets": [{
        "headers": ["GAME_ID", "PLAYER_NAME", "PTS", "REB", "AST", "STL", "BLK", "TO", "FG3M"],
        "rowSet": [
            ["0021234567", "Player 1", 25, 5, 8, 2, 1, 3, 3],
            ["0021234567", "Player 2", 18, 10, 4, 1, 2, 2, 2]
        ]
    }]
}

@pytest.fixture
def mock_responses():
    with patch('requests.get') as mock_get:
        def mock_response(*args, **kwargs):
            mock = Mock()
            if 'scoreboardv2' in args[0]:
                mock.json.return_value = SAMPLE_SCOREBOARD_RESPONSE
            elif 'boxscoresummaryv2' in args[0]:
                mock.json.return_value = SAMPLE_SUMMARY_RESPONSE
            elif 'boxscoretraditionalv2' in args[0]:
                mock.json.return_value = SAMPLE_BOXSCORE_RESPONSE
            return mock
        mock_get.side_effect = mock_response
        yield mock_get

@pytest.fixture
def mock_db():
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_connect.return_value.cursor.return_value = mock_cursor
        yield mock_cursor

def test_fetch_game_ids(mock_responses):
    game_date = "2024-02-05"
    game_ids = fetch_game_ids(game_date)
    
    assert len(game_ids) == 2
    assert game_ids == ["0021234567", "0021234568"]
    mock_responses.assert_called_with(
        "https://stats.nba.com/stats/scoreboardv2",
        headers=ANY,
        params={"GameDate": game_date, "LeagueID": "00", "DayOffset": 0}
    )

def test_fetch_boxscore_with_quarters(mock_responses):
    game_id = "0021234567"
    boxscore_data, summary_data = fetch_boxscore_with_quarters(game_id)
    
    assert boxscore_data == SAMPLE_BOXSCORE_RESPONSE
    assert summary_data == SAMPLE_SUMMARY_RESPONSE
    
    # Verify API calls
    assert mock_responses.call_count == 2
    calls = mock_responses.call_args_list
    assert 'boxscoresummaryv2' in calls[0][0][0]
    assert 'boxscoretraditionalv2' in calls[1][0][0]

def test_parse_and_save_boxscore(mock_db):
    parse_and_save_boxscore(SAMPLE_BOXSCORE_RESPONSE, SAMPLE_SUMMARY_RESPONSE)
    
    # Verify game data was saved
    game_insert_calls = [
        call for call in mock_db.execute.call_args_list 
        if "INSERT OR REPLACE INTO game_boxscores" in call[0][0]
    ]
    assert len(game_insert_calls) == 2  # One for home, one for away
    
    # Verify player data was saved
    player_insert_calls = [
        call for call in mock_db.execute.call_args_list 
        if "INSERT OR REPLACE INTO player_boxscores" in call[0][0]
    ]
    assert len(player_insert_calls) == 2  # Two players in sample data

def test_main_success(mock_responses, mock_db):
    game_date = "2024-02-05"
    main(game_date)
    
    # Verify tables were created
    create_table_calls = [
        call for call in mock_db.execute.call_args_list 
        if "CREATE TABLE IF NOT EXISTS" in call[0][0]
    ]
    assert len(create_table_calls) >= 2  # At least game and player tables
    
    # Verify data was inserted
    insert_calls = [
        call for call in mock_db.execute.call_args_list 
        if "INSERT OR REPLACE INTO" in call[0][0]
    ]
    assert len(insert_calls) > 0

@pytest.mark.parametrize("api_error", [
    "scoreboardv2",
    "boxscoresummaryv2",
    "boxscoretraditionalv2"
])
def test_main_api_errors(api_error, mock_responses):
    def mock_response(*args, **kwargs):
        mock = Mock()
        if api_error in args[0]:
            mock.raise_for_status.side_effect = Exception("API Error")
        else:
            if 'scoreboardv2' in args[0]:
                mock.json.return_value = SAMPLE_SCOREBOARD_RESPONSE
            elif 'boxscoresummaryv2' in args[0]:
                mock.json.return_value = SAMPLE_SUMMARY_RESPONSE
            elif 'boxscoretraditionalv2' in args[0]:
                mock.json.return_value = SAMPLE_BOXSCORE_RESPONSE
        return mock
    
    with patch('requests.get', side_effect=mock_response):
        main("2024-02-05")  # Should handle the error gracefully

def test_parse_and_save_boxscore_missing_data(mock_db):
    # Test with missing data in the response
    incomplete_summary = {
        "resultSets": [
            {
                "name": "GameSummary",
                "headers": ["GAME_DATE_EST", "GAME_ID"],
                "rowSet": [["2024-02-05", "0021234567"]]
            }
        ]
    }
    
    parse_and_save_boxscore(SAMPLE_BOXSCORE_RESPONSE, incomplete_summary)
    mock_db.execute.assert_not_called()  # Should not attempt to save incomplete data 