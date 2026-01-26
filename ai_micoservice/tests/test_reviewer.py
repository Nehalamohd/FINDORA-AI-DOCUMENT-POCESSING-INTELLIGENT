import pytest
from unittest.mock import MagicMock, patch
from app.reviewer import DocumentReviewer
from app.models import Page, Document

@patch("app.reviewer.SessionLocal")
def test_get_document_content_success(mock_session_local):
    """
    Verifies that get_document_content correctly aggregates text from multiple pages.
    """
    # Mock Database Session
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    # Mock Pages
    page1 = MagicMock(content="Page 1 content.")
    page2 = MagicMock(content="Page 2 content.")
    
    # Mock Query Chain: query().join().filter().order_by().all()
    mock_db.query().join().filter().order_by().all.return_value = [page1, page2]

    reviewer = DocumentReviewer()
    content = reviewer.get_document_content("test_flow_id")

    assert "Page 1 content." in content
    assert "Page 2 content." in content
    # Should be joined by newline
    assert content == "Page 1 content.\nPage 2 content."

@patch("app.reviewer.SessionLocal")
def test_get_document_content_failure(mock_session_local):
    """
    Ensures empty string is returned if DB query fails.
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_db.query.side_effect = Exception("DB Connection Error")

    reviewer = DocumentReviewer()
    content = reviewer.get_document_content("test_flow_id")

    assert content == ""

@patch("app.reviewer.SessionLocal")
@patch("app.reviewer.generate_answer")
def test_review_document_success(mock_generate_answer, mock_session_local):
    """
    Tests the full review flow: fetching content -> calling LLM -> returning dict.
    """
    # Mock DB
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_page = MagicMock(content="Test content for review.")
    mock_db.query().join().filter().order_by().all.return_value = [mock_page]

    # Mock LLM
    mock_generate_answer.return_value = "Excellent document."

    reviewer = DocumentReviewer()
    result = reviewer.review_document("test_flow_id")

    assert "review" in result
    assert result["review"] == "Excellent document."
    mock_generate_answer.assert_called_once()

@patch("app.reviewer.SessionLocal")
def test_review_document_no_content(mock_session_local):
    """
    Tests behavior when the flow has no content to review.
    """
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    # Return empty list
    mock_db.query().join().filter().order_by().all.return_value = []

    reviewer = DocumentReviewer()
    result = reviewer.review_document("empty_flow")

    assert "error" in result
    assert result["error"] == "No content found in this flow to review."
