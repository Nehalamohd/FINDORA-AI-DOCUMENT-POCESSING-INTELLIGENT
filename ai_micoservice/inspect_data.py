import logging
import sys
import os

# Set up path to allow imports from app
sys.path.append(os.getcwd())

from app.database import SessionLocal
from app.models import Flow, Document, Chunk, Embedding, User
from sqlalchemy import func

def inspect_data():
    db = SessionLocal()
    try:
        print("\n--- Users ---")
        users = db.query(User).all()
        for u in users:
            print(f"User: {u.username} (ID: {u.id})")

        print("\n--- Flows ---")
        flows = db.query(Flow).all()
        for f in flows:
            print(f"Flow: {f.name} (ID: {f.id}, UserID: {f.user_id})")

        print("\n--- Documents ---")
        docs = db.query(Document).all()
        for d in docs:
            chunk_count = db.query(Chunk).filter(Chunk.document_id == d.id).count()
            print(f"Doc: {d.filename} (ID: {d.id}, FlowID: {d.flow_id}, Status: {d.status}) - Chunks: {chunk_count}")

        print("\n--- Chunks & Embeddings Stats ---")
        total_chunks = db.query(Chunk).count()
        total_embeddings = db.query(Embedding).count()
        print(f"Total Chunks: {total_chunks}")
        print(f"Total Embeddings: {total_embeddings}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
