from app.database import SessionLocal
from app.models import Message as DBMessage

# for saving each chat messages
# role means who send the msg: user or assistant
def save_message(session_id, role, content):
    db = SessionLocal()
    try:
        msg = DBMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        db.commit()
    finally:
        db.close()


#for retrieving chat history
#limit %s here limit is 6
#This function fetches previous chat messages from the database for a specific chat session
def get_chat_history(session_id, limit=6):
    db = SessionLocal()
    try:
        rows = db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.created_at.desc()).limit(limit).all()
        return [f"{r.role}: {r.content}" for r in reversed(rows)]
    finally:
        db.close()
#db return rows like newest first but we want oldest first so we reverse it