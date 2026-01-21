import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import Chunk

DOC_ID = 57

def check_chunks():
    db = SessionLocal()
    print(f"Checking Chunks for Doc: {DOC_ID}")
    chunks = db.query(Chunk).filter(Chunk.document_id == DOC_ID).all()
    for c in chunks:
        print(f"--- Chunk {c.chunk_index} ---")
        print(c.content[:200]) # First 200 chars
        print("...")

if __name__ == "__main__":
    check_chunks()
