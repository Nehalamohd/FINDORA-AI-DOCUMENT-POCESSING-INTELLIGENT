from app.database import SessionLocal
from app.models import Message as DBMessage

# for saving each chat messages
def save_message(session_id, role, content):
    #create a new database session
    db = SessionLocal()
    # to do database operations
    try:
        #create obj or row
        msg = DBMessage(session_id=session_id, role=role, content=content)
        #add a new row
        db.add(msg)
        db.commit()
    finally:
        #close the database session
        db.close()


#fetch last few chat msg 
#This function fetches previous chat messages from the database for a specific chat session
def get_chat_history(session_id, limit=6):
    db = SessionLocal()
    try:
        #show newest first
        #select messages for the given session_id from DBMessage table ,newest first
        rows = db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.created_at.desc()).limit(limit).all()
        return [f"{r.role}: {r.content}" for r in reversed(rows)]
    finally:
        db.close()
#db return rows like newest first but we want oldest first so we reverse it