"""
Unit tests for the RAG retrieval and prompt logic (app/rag.py).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.rag import retrieve_chunks, get_first_chunks, build_prompt
from app.logger import logger
import numpy as np

@patch("app.rag.embed")
@patch("app.rag.SessionLocal")
def test_retrieve_chunks_success(mock_session_local, mock_embed):
    """
    Verifies that retrieve_chunks correctly handles query embedding and hybrid search execution.
    """
    try:
        # Mock embedding
        mock_embed.return_value = [np.zeros(384)]
        
        # Mock DB
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.execute().fetchall.return_value = [
            ("Content 1", "file1.pdf", 1, 0.9),
            ("Content 2", "file2.pdf", 2, 0.8)
        ]
        
        results = retrieve_chunks("test query", flow_id="test-uuid")
        
        assert len(results) == 2
        assert results[0]["filename"] == "file1.pdf"
        assert results[1]["score"] == 0.8
        mock_db.close.assert_called_once()
    except Exception as e:
        logger.error(f"test_retrieve_chunks_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.rag.SessionLocal")
def test_get_first_chunks_success(mock_session_local):
    """
    Tests retrieval of the first N chunks of a flow for overview generation.
    """
    try:
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_db.execute().fetchall.return_value = [
            ("Overview 1", "file1.pdf", 0, 0.5)
        ]
        
        results = get_first_chunks("test-uuid", limit=1)
        assert len(results) == 1
        assert results[0]["content"] == "Overview 1"
    except Exception as e:
        logger.error(f"test_get_first_chunks_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

def test_build_prompt_basic():
    """
    Verifies that the prompt is correctly constructed using document context and chat history.
    """
    try:
        chunks = [{"content": "Doc Text", "filename": "doc.pdf", "page_number": 1}]
        history = [{"role": "user", "content": "hello"}]
        question = "What is this?"
        
        prompt = build_prompt(chunks, history, question)
        
        assert "Doc Text" in prompt
        assert "user: hello" in prompt
        assert "What is this?" in prompt
        assert "Document Context:" in prompt
    except Exception as e:
        logger.error(f"test_build_prompt_basic failed: {e}")
        pytest.fail(f"Test failed: {e}")

def test_build_prompt_with_web():
    """
    Verifies that the prompt includes web search context when provided.
    """
    try:
        chunks = []
        history = []
        question = "Who is the president?"
        web_results = ["President is X (Source: Wikipedia)"]
        
        prompt = build_prompt(chunks, history, question, web_results=web_results)
        
        assert "President is X" in prompt
        assert "Active: YES" in prompt
        assert "No documents matched this query" in prompt
    except Exception as e:
        logger.error(f"test_build_prompt_with_web failed: {e}")
        pytest.fail(f"Test failed: {e}")
