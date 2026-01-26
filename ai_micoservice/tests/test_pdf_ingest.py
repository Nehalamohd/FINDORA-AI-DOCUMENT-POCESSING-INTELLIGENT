import pytest
from unittest.mock import MagicMock, patch, mock_open
from app.pdf_ingest import extract_text_by_page, chunk_text, process_pdf_page, ingest_pdf
from app.models import Page, Chunk

# --- Test Utilities ---

def test_chunk_text():
    """Verifies that text is split into chunks of correct size."""
    text = "word " * 1000
    chunks = list(chunk_text(text, size=100))
    # 1000 words / 100 size = 10 chunks
    assert len(chunks) == 10
    assert len(chunks[0].split()) == 100

# --- Test Extraction ---

@patch("app.pdf_ingest.PdfReader")
def test_extract_text_by_page(mock_reader):
    """Verifies page-by-page text extraction."""
    mock_page1 = MagicMock()
    mock_page1.extract_text.return_value = "Page 1 Text"
    mock_page2 = MagicMock()
    mock_page2.extract_text.return_value = "Page 2 Text"
    
    mock_reader_instance = MagicMock()
    mock_reader_instance.pages = [mock_page1, mock_page2]
    mock_reader.return_value = mock_reader_instance

    results = list(extract_text_by_page("dummy.pdf"))
    
    assert len(results) == 2
    assert results[0] == (1, "Page 1 Text")
    assert results[1] == (2, "Page 2 Text")

# --- Test Page Processing (Direct vs Vision) ---

@patch("app.pdf_ingest.SessionLocal")
@patch("app.pdf_ingest.fitz.open")
@patch("app.pdf_ingest.embed")
def test_process_pdf_page_direct_success(mock_embed, mock_fitz_open, mock_session_local):
    """Tests successful direct text extraction and saving."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock Document and Page
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Direct extracted text content that is long enough."
    mock_doc.__getitem__.return_value = mock_page
    mock_fitz_open.return_value = mock_doc
    
    # Mock Embed
    mock_embed_vector = MagicMock()
    mock_embed_vector.tolist.return_value = [0.1, 0.2, 0.3]
    mock_embed.return_value = [mock_embed_vector]

    page_id = process_pdf_page(document_id=1, page_no=1, file_path="dummy.pdf")

    assert page_id is not None
    # Verify Page was added
    mock_db.add.assert_called()
    mock_db.commit.assert_called()
    # Verify Embedding was inserted
    mock_db.execute.assert_called()

@patch("app.pdf_ingest.SessionLocal")
@patch("app.pdf_ingest.fitz.open")
@patch("app.pdf_ingest.analyze_image")  # Mock Vision
@patch("app.pdf_ingest.embed")
def test_process_pdf_page_vision_fallback(mock_embed, mock_analyze, mock_fitz_open, mock_session_local):
    """Tests fallback to vision when direct extraction yields sparse text."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock Document and Page for Extraction (Sparse)
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "   "  # Too short
    
    # Mock Page for Image Conversion
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"fake_image_bytes"
    mock_page.get_pixmap.return_value = mock_pix
    
    mock_doc.__getitem__.return_value = mock_page
    mock_fitz_open.return_value = mock_doc
    
    # Mock Vision Result
    mock_analyze.return_value = "Vision extracted text from image."
    
    # Mock Embed
    mock_embed_vector = MagicMock()
    mock_embed_vector.tolist.return_value = [0.1, 0.2]
    mock_embed.return_value = [mock_embed_vector]

    page_id = process_pdf_page(document_id=1, page_no=1, file_path="dummy.pdf")

    assert page_id is not None
    mock_analyze.assert_called_once()
    mock_db.commit.assert_called()

# --- Test Ingestion Orchestration ---

@patch("app.pdf_ingest.SessionLocal")
@patch("app.pdf_ingest.fitz.open")
@patch("app.pdf_ingest.process_pdf_page")
def test_ingest_pdf_success(mock_process, mock_fitz_open, mock_session_local):
    """Verifies the ingestion orchestration loop."""
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    
    # Mock PDF Page Count
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 2
    mock_fitz_open.return_value = mock_doc

    doc_id = ingest_pdf("dummy.pdf", "dummy.pdf")

    assert doc_id is not None
    # Process should be called for each page (2 pages)
    assert mock_process.call_count == 2
    # Status updated to completed
    assert mock_db.commit.call_count >= 2 
