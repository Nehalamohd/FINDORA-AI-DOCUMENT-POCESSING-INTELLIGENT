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

app = FastAPI(title="Findora AI Service")

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

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile):
    # Standardize temp path for Windows/Docker
    temp_dir = "/tmp" if os.name != 'nt' else "C:\\tmp"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # Send to Celery Worker
    task = process_pdf_task.delay(temp_path, file.filename)
    
    return {
        "status": "Processing started",
        "task_id": task.id,
        "filename": file.filename
    }

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str):
    """
    Verify the PDF processing status.
    Returns details on why it failed if status is FAILURE.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    # Extract result or error message
    result_data = None
    error_detail = None
    
    if task_result.failed():
        # Cleanly capture the error message from the exception
        error_detail = str(task_result.result)
    elif task_result.ready():
        result_data = task_result.result

    response = {
        "task_id": task_id,
        "status": task_result.status, # PENDING, STARTED, SUCCESS, FAILURE
        "error": error_detail,
        "result": result_data
    }
    return response

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
async def chat(message: str = Form(...), session_id: str = Form(None)):
    # Swagger default is "string", clean it up
    if session_id == "string" or not session_id:
        session_id = str(uuid.uuid4())
    
    # Ensure session exists in database (needed for foreign key)
    from app.database import get_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM sessions WHERE id = %s", (session_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO sessions (id) VALUES (%s)", (session_id,))
                conn.commit()

    history = get_chat_history(session_id)
    context = retrieve_chunks(message)
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
