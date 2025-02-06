import pytest
import os
import sys
from pathlib import Path

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