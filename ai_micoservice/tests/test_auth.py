"""
Unit tests for the authentication module (app/auth.py).
"""
import pytest
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from datetime import timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM
from fastapi import HTTPException
from unittest.mock import MagicMock
from app.models import User
from app.logger import logger

def test_password_hashing():
    """
    Verifies that password hashing and verification logic is correct.
    """
    try:
        password = "secret_password"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    except Exception as e:
        logger.error(f"test_password_hashing failed: {e}")
        pytest.fail(f"Test failed with error: {e}")

def test_create_access_token():
    """
    Verifies that JWT access tokens are created with the correct sub and exp.
    """
    try:
        data = {"sub": "testuser"}
        token = create_access_token(data)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"
        assert "exp" in decoded
    except Exception as e:
        logger.error(f"test_create_access_token failed: {e}")
        pytest.fail(f"Test failed: {e}")

def test_create_access_token_with_expiry():
    """
    Verifies that access tokens can be created with a custom expiry duration.
    """
    try:
        data = {"sub": "testuser"}
        expires = timedelta(minutes=10)
        token = create_access_token(data, expires_delta=expires)
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert decoded["sub"] == "testuser"
    except Exception as e:
        logger.error(f"test_create_access_token_with_expiry failed: {e}")
        pytest.fail(f"Test failed: {e}")

@pytest.mark.asyncio
async def test_get_current_user_valid():
    """
    Verifies that get_current_user returns the user object when a valid token is provided.
    """
    try:
        # Mock database
        db = MagicMock()
        mock_user = User(username="testuser", id="test-uuid")
        db.query().filter().first.return_value = mock_user
        
        # Create valid token
        token = create_access_token({"sub": "testuser"})
        
        user = await get_current_user(token=token, db=db)
        assert user.username == "testuser"
    except Exception as e:
        logger.error(f"test_get_current_user_valid failed: {e}")
        pytest.fail(f"Test failed: {e}")

@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    """
    Ensures that an HTTPException is raised when an invalid token is provided.
    """
    try:
        db = MagicMock()
        with pytest.raises(HTTPException) as excinfo:
            await get_current_user(token="invalid_token", db=db)
        assert excinfo.value.status_code == 401
    except Exception as e:
        logger.error(f"test_get_current_user_invalid_token failed: {e}")
        pytest.fail(f"Test failed: {e}")

@pytest.mark.asyncio
async def test_get_current_user_not_found():
    """
    Ensures that an 401 error is raised if the user in the token metadata is not found.
    """
    try:
        db = MagicMock()
        db.query().filter().first.return_value = None
        token = create_access_token({"sub": "nonexistent"})
        
        with pytest.raises(HTTPException) as excinfo:
            await get_current_user(token=token, db=db)
        assert excinfo.value.status_code == 401
    except Exception as e:
        logger.error(f"test_get_current_user_not_found failed: {e}")
        pytest.fail(f"Test failed: {e}")
