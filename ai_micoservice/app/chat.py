from app.database import get_conn

def save_message(session_id, role, content):
    sql = """
    INSERT INTO messages (session_id, role, content)
    VALUES (%s, %s, %s)
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, role, content))
            conn.commit()

def get_chat_history(session_id, limit=6):
    sql = """
    SELECT role, content
    FROM messages
    WHERE session_id = %s
    ORDER BY created_at DESC
    LIMIT %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_id, limit))
            rows = cur.fetchall()
    return [f"{r['role']}: {r['content']}" for r in reversed(rows)]
