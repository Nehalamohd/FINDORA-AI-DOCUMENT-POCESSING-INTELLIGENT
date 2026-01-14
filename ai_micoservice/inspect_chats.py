import sys
import os
sys.path.append(os.getcwd())
from app.database import SessionLocal
from app.models import Message, Session, Flow

def inspect_chats():
    db = SessionLocal()
    print("--- Recent Messages ---")
    msgs = db.query(Message).order_by(Message.created_at.desc()).limit(10).all()
    for m in msgs:
        session = db.query(Session).get(m.session_id)
        flow = db.query(Flow).get(session.flow_id) if session else None
        print(f"Time: {m.created_at} | Role: {m.role}")
        print(f"Flow: {flow.name if flow else 'Unknown'} (ID: {session.flow_id if session else '?'})")
        print(f"Content: {m.content[:50]}...")
        print("-" * 20)

if __name__ == "__main__":
    inspect_chats()
