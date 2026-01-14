import os
import sys
import uuid
from sqlalchemy import text

# Set up path to allow imports from app
sys.path.append(os.path.abspath('ai_micoservice'))

from app.rag import retrieve_chunks, build_prompt
from app.database import SessionLocal
from app.models import Document

def test_summarization_retrieval():
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
            for i, chunk in enumerate(context[:2]):
                print(f"Chunk {i+1} preview: {chunk[:100]}...")
        else:
            print("FAILED: No chunks retrieved for summarization.")

        # Test prompt building
        prompt = build_prompt(context_chunks=context, chat_history=[], question=query, web_results=None)
        
        if "Document Context:" in prompt and len(context) > 0:
            print("\nPrompt correctly contains Document Context.")
        else:
            print("\nFAILED: Prompt does not contain Document Context.")
            
        if "Web Search Context: None available." in prompt:
            print("Web search fallback correctly disabled for document query.")
        else:
            print("WARNING: Web search context present in prompt.")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_summarization_retrieval()
