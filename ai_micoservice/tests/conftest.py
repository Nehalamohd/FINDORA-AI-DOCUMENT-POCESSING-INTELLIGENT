"""
Shared pytest fixtures and configuration for the Findora AI test suite.
"""
import pytest
from unittest.mock import MagicMock
import sys
import os

try:
    # Ensure app is in path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except Exception as e:
    print(f"Error setting up test benchmarks: {e}")

@pytest.fixture
def mock_db_session():
    """
    Fixture for providing a mocked database session to tests.
    """
    return MagicMock()

@pytest.fixture
def mock_api_client():
    """
    Fixture for providing a FastAPI TestClient with the application instance.
    """
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    except Exception as e:
        pytest.fail(f"Failed to initialize API TestClient: {str(e)}")
