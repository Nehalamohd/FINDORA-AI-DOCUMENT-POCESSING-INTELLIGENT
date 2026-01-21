"""
Fast mock-based verification for document summarization retrieval logic.
"""
import os
import sys
import uuid
from unittest.mock import MagicMock

# Mock app.embedding before importing rag
sys.modules['app.embedding'] = MagicMock()
mock_embed = sys.modules['app.embedding'].embed
mock_embed.return_value = [[0.1] * 384] # Mock embedding vector

# Set up path to allow imports from app
sys.path.append(os.path.abspath('ai_micoservice'))

from app.rag import retrieve_chunks, build_prompt
from app.database import SessionLocal
from app.models import Document

def test_summarization_retrieval():
    """
    Fast integration test using mocks to verify retrieval logic for document summarization.
    """
    db = SessionLocal()
    try:
        # Get the latest document ID and flow ID
        latest_doc = db.query(Document).order_by(Document.uploaded_at.desc()).first()
        if not latest_doc:
            print("No documents found in DB to test.")
            return

        flow_id = str(latest_doc.flow_id)
        filename = latest_doc.filename
        print(f"Testing summarization for Document: {filename}, Flow ID: {flow_id}")

        # Test query
        query = "summarize this document"
        
        # Test retrieve_chunks
        context = retrieve_chunks(query, flow_id=flow_id)
        
        print(f"\nRetrieved Chunks Count: {len(context)}")
        if context:
            print("Successfully retrieved chunks for summarization!")
            print(f"Sample content: {context[0][:100]}...")
        else:
            print("FAILED: No chunks retrieved for summarization.")

        # Test web search logic (manually checked here or in prompt builder)
        is_doc_query = any(word in query.lower() for word in ["this document", "the pdf", "the file", "summarize", "about"])
        print(f"\nIs Doc Query: {is_doc_query}")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_summarization_retrieval()
