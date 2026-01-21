"""
Integration tests for the API endpoints (app/main.py).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import MagicMock, patch
from app.models import User, Flow
from app.logger import logger
import uuid
import pytest

client = TestClient(app)

@patch("app.main.get_db")
def test_register_user_success(mock_get_db):
    """
    Tests that a new user can be successfully registered via the /users/register endpoint.
    """
    try:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.query().filter().first.return_value = None # User doesn't exist
        
        response = client.post(
            "/users/register",
            data={"username": "newuser", "password": "password123", "email": "new@example.com"}
        )
        
        assert response.status_code == 200
        assert "user_id" in response.json()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    except Exception as e:
        logger.error(f"test_register_user_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.main.get_db")
@patch("app.main.verify_password", return_value=True)
def test_login_success(mock_verify, mock_get_db):
    """
    Tests successful user login and generation of a bearer token.
    """
    try:
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_user = User(username="testuser", password_hash="hashed")
        mock_db.query().filter().first.return_value = mock_user
        
        response = client.post(
            "/token",
            data={"username": "testuser", "password": "password123"}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
    except Exception as e:
        logger.error(f"test_login_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.main.get_db")
@patch("app.main.get_current_user")
def test_get_my_flows(mock_current_user, mock_get_db):
    """
    Tests retrieval of document flows for the currently authenticated user.
    """
    try:
        mock_user = User(username="testuser", id=uuid.uuid4())
        mock_current_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        mock_flow = Flow(name="My Flow", created_at=uuid.uuid1().hex[:8])
        mock_db.query().filter().all.return_value = [mock_flow]
        
        headers = {"Authorization": "Bearer fake_token"}
        response = client.get("/flows/my-flows", headers=headers)
        
        assert response.status_code == 200
        assert "flows" in response.json()
        assert response.json()["flows"][0]["name"] == "My Flow"
    except Exception as e:
        logger.error(f"test_get_my_flows failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.main.get_db")
@patch("app.main.get_current_user")
def test_create_flow(mock_current_user, mock_get_db):
    """
    Tests the creation of a new document flow/workspace through the API.
    """
    try:
        mock_user = User(username="testuser", id=uuid.uuid4())
        mock_current_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        headers = {"Authorization": "Bearer fake_token"}
        response = client.post("/flows/create", data={"name": "New Flow"}, headers=headers)
        
        assert response.status_code == 200
        assert response.json()["name"] == "New Flow"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    except Exception as e:
        logger.error(f"test_create_flow failed: {e}")
        pytest.fail(f"Test failed: {e}")
