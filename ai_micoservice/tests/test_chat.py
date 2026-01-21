"""
Unit tests for the chat utilities module (app/chat.py).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.chat import save_message, get_chat_history
from app.models import Message as DBMessage
from app.logger import logger
import uuid

@patch("app.chat.SessionLocal")
def test_save_message_success(mock_session_local):
    """
    Verifies that save_message correctly interacts with the DB session to store a new message.
    """
    try:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        session_id = str(uuid.uuid4())
        save_message(session_id, "user", "Hello")
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
    except Exception as e:
        logger.error(f"test_save_message_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.chat.SessionLocal")
def test_save_message_failure(mock_session_local):
    """
    Ensures that a database rollback occurs if an error happens during message saving.
    """
    try:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.commit.side_effect = Exception("DB Error")
        
        session_id = str(uuid.uuid4())
        # The function handles the exception internally
        save_message(session_id, "user", "Hello")
        
        mock_db.rollback.assert_called()
        mock_db.close.assert_called()
    except Exception as e:
        logger.error(f"test_save_message_failure failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.chat.SessionLocal")
def test_get_chat_history_success(mock_session_local):
    """
    Verifies that get_chat_history correctly retrieves and formats messages from the DB.
    """
    try:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # Mock actual objects with properties
        class MockMsg:
            def __init__(self, role, content):
                self.role = role
                self.content = content

        msg1 = MockMsg("user", "Hi")
        msg2 = MockMsg("assistant", "Hello there")
        
        # get_chat_history returns newest first, then reverses
        mock_db.query().filter().order_by().limit().all.return_value = [msg2, msg1]
        
        session_id = str(uuid.uuid4())
        history = get_chat_history(session_id)
        
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        mock_db.close.assert_called()
    except Exception as e:
        logger.error(f"test_get_chat_history_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.chat.SessionLocal")
def test_get_chat_history_error(mock_session_local):
    """
    Ensures that an empty list is returned if an exception occurs during history retrieval.
    """
    try:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.query.side_effect = Exception("Query error")
        
        session_id = str(uuid.uuid4())
        history = get_chat_history(session_id)
        
        assert history == []
        mock_db.close.assert_called_once()
    except Exception as e:
        logger.error(f"test_get_chat_history_error failed: {e}")
        pytest.fail(f"Test failed: {e}")
