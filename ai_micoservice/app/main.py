#for handling all incoming request
import asyncio
import json
import uuid
import os
from datetime import timedelta
import redis.asyncio as redis

from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

from app.rag import retrieve_chunks, build_prompt
from app.llm import generate_answer
from app.chat import save_message, get_chat_history
from app.search import web_search
from app.tasks import process_document_task
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.config import REDIS_URL
from app.auth import get_password_hash, verify_password, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.evaluation import generate_golden_questions, evaluate_answer
from app.database import get_db
from app.models import User, Flow, Session as DBSession, Message as DBMessage, Document, GoldenQA, Evaluation as DBEvaluation
from sqlalchemy.orm import Session

app = FastAPI(title="Findora AI Service")

#allow all http methods from any origin
#any frontend from anywhere can call apis
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

#wen user connects add to active connections
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

#when user disconnects remove from active connections
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

#broadcast message to all active connections
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Auth & User Management ---

@app.post("/token")
#receive login form data
#connect to db to verify user

async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    
#validate password
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    #set token expiry
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    #frontend receives this token
    return {"access_token": access_token, "token_type": "bearer"}

#to register new users
@app.post("/users/register")
async def register_user(username: str = Form(...), password: str = Form(...), email: str = Form(None), db: Session = Depends(get_db)):
    """
    Register a new user. Now requires a password.
    """
    # Check if user exists if yes raise 400 error
    user = db.query(User).filter(User.username == username).first()
    
    if user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # hashes the password before storing
    password_hash = get_password_hash(password)
    
    # insert new user to db
    new_user = User(username=username, email=email, password_hash=password_hash)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "user_id": str(new_user.id),
        "username": new_user.username,
        "message": "User created successfully"
    }

#to display current user info
@app.get("/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user info. Requires 'Authorization: Bearer <token>'
    """
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "created_at": str(current_user.created_at)
    }

# --- Flow Management ---

@app.post("/flows/create")
async def create_flow(name: str = Form(...), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Create a new flow for the current user.
    """
    # Create flow
    flow = Flow(user_id=current_user.id, name=name)
    db.add(flow)
    db.commit()
    db.refresh(flow)
    
    return {
        "flow_id": str(flow.id),
        "name": flow.name,
        "created_at": str(flow.created_at),
        "message": "Flow created successfully"
    }

#display all flows for current user in dashboard in desc order
@app.get("/flows/my-flows")
async def get_my_flows(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get all flows for the current user.
    """
    # Get all flows for this user
    flows = db.query(Flow).filter(Flow.user_id == current_user.id).order_by(Flow.created_at.desc()).all()
    
    return {
        "username": current_user.username,
        "flows": [
            {
                "flow_id": str(flow.id),
                "name": flow.name,
                "created_at": str(flow.created_at)
            }
            for flow in flows
        ]
    }

# --- Document Upload ---

@app.post("/upload")
async def upload_document(
    file: UploadFile, 
    flow_id: str = Form(None), 
    flow_name: str = Form(None), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    Upload a document (PDF, PPTX). 
    If flow_id is provided, adds to that flow. 
    Otherwise, creates a new flow with flow_name.
    """
    username = current_user.username
    user_id = current_user.id

    # ensure uploaded file is pdf or pptx
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".pptx", ".ppt"]:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    if flow_id and flow_id != "string":
        # Validate and use existing flow
        try:
            flow_uuid = uuid.UUID(flow_id)
            flow = db.query(Flow).filter(Flow.id == flow_uuid, Flow.user_id == user_id).first()
            if not flow:
                raise HTTPException(status_code=404, detail="Flow not found or access denied")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid flow_id format")
    else:
        # create a new flow for this upload
        if not flow_name or flow_name == "string":
            flow_name = f"Upload: {file.filename}"
        
        flow = Flow(user_id=user_id, name=flow_name)
        db.add(flow)
        db.commit()
        db.refresh(flow)
    
    flow_id = str(flow.id)
    flow_name = flow.name
    
    # Create folder structure: /tmp/flows/{flow_id}/
    #each flow has its own folder
    temp_dir = "/tmp" if os.name != 'nt' else "C:\\tmp"
    flow_folder = os.path.join(temp_dir, "flows", flow_id)
    os.makedirs(flow_folder, exist_ok=True)
    
    # Save file in the flow folder
    temp_path = os.path.join(flow_folder, file.filename)
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    # send file to celery worker
    task = process_document_task.delay(temp_path, file.filename, flow_id, username)
    
    return {
        "status": "Processing started",
        "task_id": task.id,
        "filename": file.filename,
        "flow_id": flow_id,
        "flow_name": flow_name,
        "username": username,
        "message": f"Created new flow '{flow_name}' and uploaded file"
    }



# --- Task Status ---

@app.get("/task-status/{task_id}")
async def get_task_status(task_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Verify the document processing status.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    
    # extract result or error message
    result_data = None
    error_detail = None
    
    if task_result.failed():
        # cleanly capture the error message from the exception
        error_detail = str(task_result.result)
    #task completed successfully
    elif task_result.ready():
        result_data = task_result.result

    response = {
        "task_id": task_id,
        "status": task_result.status, # PENDING, STARTED, SUCCESS, FAILURE
        "error": error_detail,
        "result": result_data
    }
    return response

#web socket to stay open for status updates
# WebSocket for Real-time task updates 
@app.websocket("/ws/status")
async def websocket_status(websocket: WebSocket):
    await manager.connect(websocket)
    #check if redis has new messages
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

# asking question about documents in a flow

@app.post("/chat")
async def chat(message: str = Form(...), flow_id: str = Form(None), session_id: str = Form(None), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Chat with documents in a flow.
    """
    username = current_user.username

    # If flow_id not provided, get user's most recent flow
    if not flow_id or flow_id == "string":
        flow = db.query(Flow).filter(Flow.user_id == current_user.id).order_by(Flow.created_at.desc()).first()
        
        if not flow:
            raise HTTPException(status_code=404, detail=f"No flows found for user '{username}'. Please upload a document first.")
        
        flow_id = str(flow.id)
    else:
        # Validate provided flow_id
        try:
            uuid.UUID(flow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid flow_id format: '{flow_id}'. Must be a valid UUID.")
    
    #swagger default is "string", clean it up
    if session_id == "string" or not session_id:
        session_id = str(uuid.uuid4())#uniq identifier
    
    # ensure session exists in database (needed for foreign key)
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        #create new session
        session = DBSession(id=session_id, flow_id=flow_id)
        db.add(session)
        db.commit()

    # to fetch chat history(previous messages)
    history = get_chat_history(session_id)
    #retrieve relevant chunks from documents in flow
    context = retrieve_chunks(message, flow_id=flow_id)
    
    web_results = None
    # If no context found in documents, try web search
    if not context:
        web_results = web_search(message)
    
    #builds the final prompt that will be sent to the AI model
    prompt = build_prompt(context_chunks=context, chat_history=history, question=message, web_results=web_results)
    answer = generate_answer(prompt)

    save_message(session_id, "user", message)
    save_message(session_id, "assistant", answer)

    return {"session_id": session_id, "answer": answer, "flow_id": flow_id}

# Evaluation Endpoints 
@app.post("/flows/{flow_id}/golden/auto-generate")
#only logged in users can generate golden qna
async def auto_generate_golden(flow_id: str, count: int = 5, current_user: User = Depends(get_current_active_user)):
    """
    Auto-generates 'Golden' Q&A pairs from documents in the flow.
    """
    return generate_golden_questions(flow_id, count)

#to view all golden qna pairs for a flow
@app.get("/flows/{flow_id}/golden")
async def get_golden_qa(flow_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get all Golden Q&A pairs for a flow.
    """
    rows = db.query(GoldenQA).filter(GoldenQA.flow_id == flow_id).all()
    return [
        {"id": str(r.id), "question": r.question, "expected_answer": r.expected_answer, "created_at": str(r.created_at)} 
        for r in rows
    ]

#for evaluating the flow against golden qna pairs
@app.post("/flows/{flow_id}/evaluate")
async def run_evaluation(flow_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Runs the RAG pipeline against all Golden Q&A pairs for this flow and scores the results.
    """
    # 1. Get Golden Pairs
    golden_pairs = db.query(GoldenQA).filter(GoldenQA.flow_id == flow_id).all()
            
    if not golden_pairs:
        raise HTTPException(status_code=400, detail="No golden Q&A pairs found for this flow. Please generate or add some first.")

    results = []
    
    #Loop through each golden Q&A row one by one
    for pair in golden_pairs:
        golden_id = str(pair.id)
        question = pair.question
        expected = pair.expected_answer
        
        # Call RAG Pipeline (Internal Call)
        # We simulate the chat logic directly to avoid HTTP overhead
        context = retrieve_chunks(question, flow_id=flow_id)
        
        # Web Search Fallback (reuse logic from chat)
        web_results_list = None
        if not context:
             # Basic web search call since async isn't needed here strictly, 
             # but web_search is synchronous.
             from app.search import web_search
             web_results_list = web_search(question)
        
        prompt = build_prompt(context_chunks=context, chat_history=[], question=question, web_results=web_results_list)
        generated_answer = generate_answer(prompt)
        
        # Score it
        eval_result = evaluate_answer(question, expected, generated_answer)
        
        # Save Evaluation to db
        eval_record = DBEvaluation(
            golden_id=pair.id,
            generated_answer=generated_answer,
            similarity_score=eval_result["score"],
            judge_feedback=eval_result["feedback"]
        )
        db.add(eval_record)
        db.commit()
         #store each result in a list to return later
         # together       
        results.append({
            "question": question,
            "generated_answer": generated_answer,
            "score": eval_result["score"],
            "feedback": eval_result["feedback"]
        })
        
    return {"message": "Evaluation complete", "results": results}
