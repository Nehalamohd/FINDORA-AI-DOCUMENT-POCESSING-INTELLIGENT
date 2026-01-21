"""
Unit tests for the LLM interaction module (app/llm.py).
"""
import pytest
from unittest.mock import MagicMock, patch
from app.llm import generate_answer, generate_answer_stream, analyze_image
from app.logger import logger

@patch("app.llm.client")
def test_generate_answer_success(mock_client):
    """
    Verifies that generate_answer correctly returns content from the Groq client.
    """
    try:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test Answer"
        mock_client.chat.completions.create.return_value = mock_response
        
        result = generate_answer("Test Prompt")
        assert result == "Test Answer"
        mock_client.chat.completions.create.assert_called_once()
    except Exception as e:
        logger.error(f"test_generate_answer_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.llm.client")
def test_generate_answer_failure(mock_client):
    """
    Ensures that an error message is returned if the LLM API call fails.
    """
    try:
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        result = generate_answer("Test Prompt")
        assert "Error: API Error" in result
    except Exception as e:
        logger.error(f"test_generate_answer_failure failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.llm.client")
def test_generate_answer_stream_success(mock_client):
    """
    Verifies that generate_answer_stream correctly yields chunks of content.
    """
    try:
        mock_chunk1 = MagicMock()
        mock_chunk1.choices[0].delta.content = "Part 1 "
        mock_chunk2 = MagicMock()
        mock_chunk2.choices[0].delta.content = "Part 2"
        
        mock_client.chat.completions.create.return_value = [mock_chunk1, mock_chunk2]
        
        stream = generate_answer_stream("Test Prompt")
        chunks = list(stream)
        assert chunks == ["Part 1 ", "Part 2"]
    except Exception as e:
        logger.error(f"test_generate_answer_stream_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.llm.client")
def test_generate_answer_stream_failure(mock_client):
    """
    Ensures that a special error tag is yielded if the LLM stream fails.
    """
    try:
        mock_client.chat.completions.create.side_effect = Exception("Stream Error")
        
        stream = generate_answer_stream("Test Prompt")
        chunks = list(stream)
        assert "__ERROR__:Stream Error" in chunks
    except Exception as e:
        logger.error(f"test_generate_answer_stream_failure failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.llm.client")
@patch("time.sleep", return_value=None)  # Skip sleeping during tests
def test_analyze_image_retry_success(mock_sleep, mock_client):
    """
    Tests the retry logic of analyze_image when a rate limit is hit.
    """
    try:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Detected Text"
        
        # Fail first, succeed second
        mock_client.chat.completions.create.side_effect = [
            Exception("rate_limit_exceeded"),
            mock_response
        ]
        
        result = analyze_image("dummy_base64")
        assert result == "Detected Text"
        assert mock_client.chat.completions.create.call_count == 2
    except Exception as e:
        logger.error(f"test_analyze_image_retry_success failed: {e}")
        pytest.fail(f"Test failed: {e}")

@patch("app.llm.client")
def test_analyze_image_fatal_failure(mock_client):
    """
    Ensures that non-rate-limit exceptions are re-raised immediately by analyze_image.
    """
    try:
        mock_client.chat.completions.create.side_effect = Exception("Fatal Error")
        
        with pytest.raises(Exception) as exc:
            analyze_image("dummy_base64")
        assert "Fatal Error" in str(exc.value)
    except Exception as e:
        logger.error(f"test_analyze_image_fatal_failure failed: {e}")
        pytest.fail(f"Test failed: {e}")
