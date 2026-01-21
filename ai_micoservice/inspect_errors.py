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
        print("\n--- Failed Documents Analysis ---")
        failed_docs = db.query(Document).filter(Document.status == 'failed').all()
        for d in failed_docs:
            print(f"Doc: {d.filename} (ID: {d.id})")
            print(f"Error: {d.error_message}")
            print("-" * 20)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_data()
