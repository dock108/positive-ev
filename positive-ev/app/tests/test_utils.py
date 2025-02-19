import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
import os
import sqlite3
from unittest.mock import MagicMock

from utils import (
    cleanup_logs,
    connect_db,
    fix_event_time,
    generate_bet_id,
    create_tables,
    get_latest_date_from_db
)

@pytest.fixture
def mock_db():
    with patch('sqlite3.connect') as mock_connect:
        mock_cursor = Mock()
        mock_connection = Mock()
        mock_cursor.connection = mock_connection  # Add connection to cursor
        mock_connect.return_value = mock_connection  # Return the connection
        mock_connection.cursor.return_value = mock_cursor  # Set cursor on connection
        yield mock_cursor

def test_cleanup_logs():
    # Create sample log content with mix of old and new entries
    current_time = datetime.now()
    old_time = current_time - timedelta(hours=3)
    recent_time = current_time - timedelta(minutes=30)
    
    log_lines = [
        f"{old_time.strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - Old log\n",
        f"{recent_time.strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - Recent log\n",
        f"{current_time.strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - Current log\n"
    ]

    # Mock the file operations
    file_mock = MagicMock()
    file_mock.__enter__ = Mock(return_value=file_mock)
    file_mock.__exit__ = Mock(return_value=None)
    file_mock.readlines.return_value = log_lines
    
    # Mock open to return our file mock
    open_mock = Mock(return_value=file_mock)
    
    with patch('builtins.open', open_mock), \
         patch('os.path.exists', return_value=True):
        cleanup_logs('test.log')
        
        # Get what was written
        write_args = file_mock.writelines.call_args[0][0]
        written_content = ''.join(write_args)
        
        print(f"Input content: {''.join(log_lines)}")
        print(f"Written content: {written_content}")
        
        # Verify content
        assert 'Old log' not in written_content, "Old log should have been removed"
        assert 'Recent log' in written_content, "Recent log should be present"
        assert 'Current log' in written_content, "Current log should be present"
        
        # Verify file operations
        assert open_mock.call_count == 2  # Once for read, once for write
        assert file_mock.readlines.called
        assert file_mock.writelines.called

def test_cleanup_logs_no_file():
    with patch('os.path.exists', return_value=False), \
         patch('builtins.open', mock_open()) as mock_file:
        cleanup_logs('test.log')
        mock_file.assert_not_called()

def test_connect_db():
    with patch('sqlite3.connect') as mock_connect:
        conn = connect_db()
        mock_connect.assert_called_once()
        assert conn == mock_connect.return_value

@pytest.mark.parametrize("event_time,timestamp,expected", [
    (
        "Today at 7:30 PM",
        "2024-02-05 14:00:00",
        "2024-02-05 19:30"
    ),
    (
        "Tomorrow at 8:00 PM",
        "2024-02-05 14:00:00",
        "2024-02-06 20:00"
    ),
    (
        "Wed, Feb 7 at 7:30 PM",
        "2024-02-05 14:00:00",
        "2024-02-07 19:30"
    ),
    # Test year rollover (December to January)
    (
        "Wed, Jan 3 at 7:30 PM",
        "2023-12-31 14:00:00",
        "2024-01-03 19:30"
    )
])
def test_fix_event_time(event_time, timestamp, expected):
    result = fix_event_time(event_time, timestamp)
    assert result == expected

def test_fix_event_time_invalid():
    # Should return original string if parsing fails
    invalid_time = "Invalid Time Format"
    result = fix_event_time(invalid_time, "2024-02-05 14:00:00")
    assert result == invalid_time

def test_generate_bet_id():
    # Test that same inputs generate same ID
    inputs = (
        "2024-02-05 19:30",
        "Team A vs Team B",
        "NBA",
        "Player Points",
        "Player 1 Over 20.5"
    )
    
    id1 = generate_bet_id(*inputs)
    id2 = generate_bet_id(*inputs)
    assert id1 == id2
    
    # Test that different inputs generate different IDs
    different_inputs = (
        "2024-02-05 19:30",
        "Team B vs Team A",  # Changed teams
        "NBA",
        "Player Points",
        "Player 1 Over 20.5"
    )
    id3 = generate_bet_id(*different_inputs)
    assert id1 != id3

def test_create_tables(mock_db):
    create_tables()
    
    # Verify all tables were created
    create_calls = [
        call for call in mock_db.execute.call_args_list 
        if "CREATE TABLE IF NOT EXISTS" in call[0][0]
    ]
    
    # Check for each table
    table_names = ["game_boxscores", "player_boxscores", "betting_data"]
    for table in table_names:
        assert any(table in call[0][0] for call in create_calls)
    
    # Verify commit was called on the connection
    mock_db.connection.commit.assert_called_once()

@pytest.mark.parametrize("table_name,date_column,mock_result,expected_year", [
    ("game_boxscores", "game_date", ("2024-02-05",), 2024),  # Single tuple, not list
    ("game_boxscores", "game_date", None, 2025),  # Default year when no data
    ("game_boxscores", "game_date", ("invalid_date",), 2025)  # Default year on error
])
def test_get_latest_date_from_db(mock_db, table_name, date_column, mock_result, expected_year):
    mock_db.fetchone.return_value = mock_result
    
    result = get_latest_date_from_db(table_name, date_column)
    
    assert result.year == expected_year
    if mock_result and mock_result[0] != "invalid_date":
        assert result.strftime("%Y-%m-%d") == mock_result[0]

def test_get_latest_date_from_db_error(mock_db):
    mock_db.fetchone.side_effect = sqlite3.Error("Database error")
    
    result = get_latest_date_from_db("table", "column")
    
    # Should return default date on error
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 1 