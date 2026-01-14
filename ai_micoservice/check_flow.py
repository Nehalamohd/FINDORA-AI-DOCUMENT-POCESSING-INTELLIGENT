import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import Document, Flow

TARGET_FLOW_ID = "98aaec21-e9e3-4cfc-9310-df84b17e7a2e"

def check_flow():
    db = SessionLocal()
    print(f"Checking Flow: {TARGET_FLOW_ID}")
    docs = db.query(Document).filter(Document.flow_id == TARGET_FLOW_ID).all()
    for d in docs:
        print(f"Found Doc: {d.filename} (ID: {d.id}, Status: {d.status})")

if __name__ == "__main__":
    check_flow()
