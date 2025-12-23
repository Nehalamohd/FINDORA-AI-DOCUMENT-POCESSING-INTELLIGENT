import asyncio
import json
import uuid
from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect
from app.rag import retrieve_chunks, build_prompt
from app.llm import generate_answer
from app.chat import save_message, get_chat_history
from app.tasks import process_pdf_task
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.config import REDIS_URL
import os
import redis.asyncio as redis
from fastapi import Depends, HTTPException, status, Header
from app.database import get_conn


app = FastAPI(title="Findora AI Service")

async def get_current_user(x_username: str = Header(None)):
    if not x_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Username header is missing. Please provide your username (e.g. your email or name).",
        )
    
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check if user exists, if not, create them automatically
            cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", (x_username, x_username))
            user = cur.fetchone()
            if not user:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                    (x_username, "simple_mode") # No password needed in simple mode
                )
                user_id = cur.fetchone()["id"]
                conn.commit()
                return str(user_id)
            return str(user["id"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

@app.get("/me")
async def read_users_me(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}

@app.post("/create-flow")
async def create_flow(name: str = Form(...), user_id: str = Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO flows (name, user_id) VALUES (%s, %s) RETURNING id",
                (name, user_id)
            )
            flow_id = cur.fetchone()["id"]
            conn.commit()
            return {"flow_id": str(flow_id), "name": name}

@app.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile, 
    flow_id: str = Form(...), 
    user_id: str = Depends(get_current_user)
):
    # Verify ownership of flow
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM flows WHERE id = %s AND user_id = %s", (flow_id, user_id))
            if not cur.fetchone():
                raise HTTPException(status_code=403, detail="You do not own this flow or flow does not exist")

    # Standardize temp path for Windows/Docker
    temp_dir = "/tmp" if os.name != 'nt' else "C:\\tmp"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Send to Celery Worker
    task = process_pdf_task.delay(temp_path, file.filename, flow_id=flow_id)
    
    return {
        "status": "Processing started",
        "task_id": task.id,
        "filename": file.filename
    }

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str, user_id: str = Depends(get_current_user)):
    """
    Verify the PDF processing status.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    result_data = None
    error_detail = None
    
    if task_result.failed():
        error_detail = str(task_result.result)
    elif task_result.ready():
        result_data = task_result.result

    return {
        "task_id": task_id,
        "status": task_result.status,
        "error": error_detail,
        "result": result_data
    }

@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    await manager.connect(websocket)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("task_updates")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await pubsub.unsubscribe("task_updates")

# Chat Endpoint
@app.post("/chat")
async def chat(
    message: str = Form(...), 
    session_id: str = Form(None), 
    user_id: str = Depends(get_current_user)
):
    # Validate/Generate UUID for session_id
    if session_id:
        try:
            uuid.UUID(str(session_id))
        except ValueError:
            # If "1" or invalid string provided, generate a fresh session ID
            session_id = str(uuid.uuid4())
    else:
        session_id = str(uuid.uuid4())
    
    # Ensure session exists and user owns it (via flow ownership)
    flow_id = None

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, flow_id FROM sessions WHERE id = %s", (session_id,))
            session_row = cur.fetchone()
            if not session_row:
                # If no session, they must provide a flow_id they own
                # For now let's assume they might be starting a fresh session
                # In a real UI, you'd pass flow_id here
                cur.execute("INSERT INTO sessions (id) VALUES (%s)", (session_id,))
                conn.commit()
            else:
                flow_id = session_row.get("flow_id")
                # Verify ownership if flow exists
                if flow_id:
                    cur.execute("SELECT user_id FROM flows WHERE id = %s", (flow_id,))
                    flow_owner = cur.fetchone()
                    if flow_owner and str(flow_owner["user_id"]) != user_id:
                        raise HTTPException(status_code=403, detail="You do not own this flow")

    history = get_chat_history(session_id)
    # Filter documents by flow_id if available
    context = retrieve_chunks(message, flow_id=flow_id)
    prompt = build_prompt(context_chunks=context, chat_history=history, question=message)
    answer = generate_answer(prompt)

    save_message(session_id, "user", message)
    save_message(session_id, "assistant", answer)

    return {"session_id": session_id, "answer": answer}

@app.get("/debug/db-info")
async def db_info():
    """
    Check the current status of the database (Counts for documents, pages, and chunks).
    """
    from app.database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM documents")
            doc_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM pages")
            page_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cur.fetchone()[0]
            
            cur.execute("SELECT id, filename, status, task_id FROM documents ORDER BY uploaded_at DESC LIMIT 5")
            recent_docs = cur.fetchall()
            
    return {
        "counts": {
            "documents": doc_count,
            "pages": page_count,
            "chunks": chunk_count
        },
        "recent_documents": recent_docs
    }
