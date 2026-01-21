"""
Utilities for saving and retrieving chat messages from the database.
"""
from app.database import SessionLocal
from app.models import Message as DBMessage
from app.logger import logger

# for saving each chat messages
def save_message(session_id, role, content):
    """
    Saves a single chat message to the database.
    """
    db = None
    try:
        db = SessionLocal()
        msg = DBMessage(session_id=session_id, role=role, content=content)
        db.add(msg)
        db.commit()
        logger.debug(f"Message saved for session {session_id}, role: {role}")
    except Exception as e:
        logger.error(f"Failed to save message for session {session_id}: {str(e)}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


#fetch last few chat msg 
#This function fetches previous chat messages from the database for a specific chat session
def get_chat_history(session_id, limit=6):
    """
    Retrieves the most recent chat messages for a given session.
    """
    db = None
    try:
        db = SessionLocal()
        # Fetch newest first, then reverse to chronological order
        rows = db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.created_at.desc()).limit(limit).all()
        logger.debug(f"Retrieved {len(rows)} messages for session {session_id}")
        
        # Return structured list for frontend/API consumption
        return [{"role": r.role, "content": r.content} for r in reversed(rows)]
    except Exception as e:
        logger.error(f"Error fetching chat history for session {session_id}: {str(e)}")
        return []
    finally:
        if db:
            db.close()
#db return rows like newest first but we want oldest first so we reverse it