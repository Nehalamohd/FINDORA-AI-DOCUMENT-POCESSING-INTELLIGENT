"""
Script to check flow details and associated documents.
"""
import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import Document, Flow

from app.logger import logger

TARGET_FLOW_ID = "98aaec21-e9e3-4cfc-9310-df84b17e7a2e"

def check_flow():
    """
    Queries and logs the status of documents associated with a specific TARGET_FLOW_ID.
    
    This script is useful for debugging flow state without accessing the database directly.
    """
    db = SessionLocal()
    try:
        logger.info(f"Checking Flow: {TARGET_FLOW_ID}")
        docs = db.query(Document).filter(Document.flow_id == TARGET_FLOW_ID).all()
        
        if not docs:
            logger.warning(f"No documents found for Flow ID: {TARGET_FLOW_ID}")
            return

        for d in docs:
            logger.info(f"Found Doc: {d.filename} (ID: {d.id}, Status: {d.status})")
    except Exception as e:
        logger.error(f"Error checking flow: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    check_flow()
