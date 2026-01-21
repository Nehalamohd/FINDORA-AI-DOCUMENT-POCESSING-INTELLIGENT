#for handling all incoming request
#central api orchestration file
import asyncio
import json
import uuid
import os
from datetime import timedelta
import redis.asyncio as redis

from fastapi import FastAPI, UploadFile, Form, WebSocket, WebSocketDisconnect, Header, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

from app.rag import retrieve_chunks, build_prompt, get_first_chunks
from app.llm import generate_answer, generate_answer_stream
from app.chat import save_message, get_chat_history
from app.search import web_search
from app.reviewer import DocumentReviewer
from fastapi.responses import StreamingResponse
from app.tasks import process_document_task
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.config import REDIS_URL
from app.auth import get_password_hash, verify_password, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.evaluation import generate_golden_questions, evaluate_answer
from app.logger import logger
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
#async means handle many req at the same time
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
    #record login attempt in logs
    logger.info(f"User login attempt: {form_data.username}")
    #frontend receives this token
    return {"access_token": access_token, "token_type": "bearer"}

#to register new users
@app.post("/users/register")
#from form
async def register_user(username: str = Form(...), password: str = Form(...), email: str = Form(None), db: Session = Depends(get_db)):
    """
    Register a new user. Now requires a password.
    """
    # Check if user exists if yes raise 400 error
    user = db.query(User).filter(User.username == username).first()
    #give the first matching user
    if user:
        logger.warning(f"Registration attempt for existing username: {username}")
        raise HTTPException(status_code=400, detail="User already exists")
    
    # hashes the password before storing
    #to log new user registration
    logger.info(f"New user registration: {username}")
    password_hash = get_password_hash(password)
    
    # insert new user to db
    new_user = User(username=username, email=email, password_hash=password_hash)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"User '{username}' registered successfully with ID: {new_user.id}")
    return {
        "user_id": str(new_user.id),
        "username": new_user.username,
        "message": "User created successfully"
    }

#to display current user info
@app.get("/users/me")
#check if user is active 
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    logger.info(f"Fetching info for current user: {current_user.username}")
    return {
        "user_id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "created_at": str(current_user.created_at)
    }

# --- Flow Management ---

@app.post("/flows/create")
async def create_flow(name: str = Form(...), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    logger.info(f"User {current_user.username} attempting to create new flow: {name}")
    # Create flow
    #Flow is the model
    flow = Flow(user_id=current_user.id, name=name)
    db.add(flow)
    db.commit()
    db.refresh(flow)
    
    logger.info(f"Flow '{name}' created successfully with ID: {flow.id} for user {current_user.username}")
    return {
        "flow_id": str(flow.id),
        "name": flow.name,
        "created_at": str(flow.created_at),
        "message": "Flow created successfully"
    }

#display all flows for current user in desc order
@app.get("/flows/my-flows")
async def get_my_flows(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    logger.info(f"Fetching flows for user: {current_user.username}")
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
# if flow id exist add to that flow else create new flow with file name
@app.post("/upload")
async def upload_document(
    file: UploadFile, 
    flow_id: str = Form(None), 
    flow_name: str = Form(None), 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    logger.info(f"User {current_user.username} attempting to upload document: {file.filename} to flow_id: {flow_id}")
    username = current_user.username
    user_id = current_user.id

    # ensure uploaded file is pdf or pptx
    #separate name and extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".pptx", ".ppt"]:
        logger.warning(f"Unsupported file type uploaded: {ext} by user {username}")
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    if flow_id and flow_id != "string":
        # Validate and use existing flow
        try:
            flow_uuid = uuid.UUID(flow_id)
            flow = db.query(Flow).filter(Flow.id == flow_uuid, Flow.user_id == user_id).first()
            if not flow:
                logger.warning(f"Flow {flow_id} not found or access denied for user {username}")
                raise HTTPException(status_code=404, detail="Flow not found or access denied")
            logger.info(f"Document {file.filename} being added to existing flow {flow.name} ({flow_id})")
        except ValueError:
            logger.error(f"Invalid flow_id format: {flow_id} for user {username}")
            raise HTTPException(status_code=400, detail="Invalid flow_id format")
    else:
        # create a new flow for this upload
        if not flow_name or flow_name == "string":
            flow_name = f"Upload: {file.filename}"
        
        flow = Flow(user_id=user_id, name=flow_name)
        db.add(flow)
        db.commit()
        db.refresh(flow)
        logger.info(f"New flow '{flow_name}' created for document upload with ID: {flow.id} by user {username}")
    
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
    logger.info(f"Document {file.filename} saved to temporary path: {temp_path}")

    # send file to celery worker
    task = process_document_task.delay(temp_path, file.filename, flow_id, username)
    logger.info(f"Document processing task '{task.id}' initiated for file: {file.filename} in flow: {flow_id}")
    
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
    logger.info(f"User {current_user.username} checking status for task: {task_id}")
    task_result = AsyncResult(task_id, app=celery_app)
    
    # extract result or error message
    result_data = None
    error_detail = None
    
    if task_result.failed():
        # cleanly capture the error message from the exception
        error_detail = str(task_result.result)
        logger.error(f"Task {task_id} failed: {error_detail}")
    #task completed successfully
    elif task_result.ready():
        result_data = task_result.result
        logger.info(f"Task {task_id} completed successfully.")

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
    logger.info(f"WebSocket {websocket.client} subscribed to 'task_updates' channel.")

   #listen for new messages and send to client 
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message["data"])
                logger.debug(f"Sent task update to WebSocket {websocket.client}: {message['data']}")
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await pubsub.unsubscribe("task_updates")
        logger.info(f"WebSocket {websocket.client} unsubscribed from 'task_updates' channel.")
    except Exception as e:
        logger.error(f"WebSocket error for {websocket.client}: {e}")
        manager.disconnect(websocket)

# asking question about documents in a flow

@app.post("/chat")
async def chat(message: str = Form(...), flow_id: str = Form(None), session_id: str = Form(None), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Chat with documents in a flow.
    """
    username = current_user.username
    logger.info(f"Chat request from user {username} - Message: '{message[:50]}...', Flow: {flow_id}, Session: {session_id}")

    # If flow_id not provided, get user's most recent flow
    if not flow_id or flow_id == "string":
        flow = db.query(Flow).filter(Flow.user_id == current_user.id).order_by(Flow.created_at.desc()).first()
        
        if not flow:
            logger.warning(f"No flows found for user '{username}' during chat request.")
            raise HTTPException(status_code=404, detail=f"No flows found for user '{username}'. Please upload a document first.")
        
        flow_id = str(flow.id)
        logger.info(f"No flow_id provided, using most recent flow: {flow_id} for user {username}")
    else:
        # Validate provided flow_id
        try:
            uuid.UUID(flow_id)
        except ValueError:
            logger.error(f"Invalid flow_id format: '{flow_id}' for user {username}")
            raise HTTPException(status_code=400, detail=f"Invalid flow_id format: '{flow_id}'. Must be a valid UUID.")
    
    logger.debug(f"Chat request - Message: '{message[:50]}...', Flow: {flow_id}, Session: {session_id}")
    #swagger default is "string", clean it up
    if session_id == "string" or not session_id:
        session_id = str(uuid.uuid4())#uniq identifier
        logger.info(f"New session created: {session_id} for user {username}")
    
    # ensure session exists in database (needed for foreign key)
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        #create new session
        session = DBSession(id=session_id, flow_id=flow_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"DBSession {session_id} created for flow {flow_id}.")

    # to fetch chat history(previous messages)
    history = get_chat_history(session_id)
    logger.debug(f"Chat history retrieved for session {session_id}, {len(history)} messages.")
    # retrieve relevant chunks from documents in flow
    context = retrieve_chunks(message, flow_id=flow_id)
    
    # Meta-keywords that should prioritize document context over web search
    meta_keywords = ["summarize", "summary", "review", "brief", "outline", "overview", "what is this", "tell me about this", "explain", "details", "elaborate"]
    is_meta_query = any(k in message.lower() for k in meta_keywords)

    # Context Fallback: If a meta-query returns zero results, force-retrieve first 10 chunks
    if not context and is_meta_query:
        logger.info(f"Meta-query '{message}' returned no context. Force-retrieving first 10 chunks as fallback.")
        context = get_first_chunks(flow_id, limit=10)
    
    # Calculate top score for logging/debugging
    top_score = context[0].get('score', 0) if context else 0
    logger.debug(f"Top Document Score: {top_score:.4f} for query: {message}")

    web_results = None
    # Meta-keywords that should prioritize document context over web search
    meta_keywords = ["summarize", "summary", "review", "brief", "outline", "overview", "what is this", "tell me about this"]
    is_meta_query = any(k in message.lower() for k in meta_keywords)

    # Trigger web search if no context or if context matches are weak (Retrieval Noise)
    # UNLESS it's a meta-query about a document we already found (even weakly)
    if not context or (top_score < 0.7 and not is_meta_query):
        # Enrich the query if it's short to get better web results (e.g., "what is ball" -> "what is ball definition details")
        enriched_query = message
        if len(message.split()) <= 4:
            enriched_query += " definition meaning details"
            
        logger.info(f"Context too weak (score {top_score}) or no context, performing web search for: {enriched_query}...")
        web_results = web_search(enriched_query)
        if web_results:
            logger.info(f"Web search returned {len(web_results)} results.")
        else:
            logger.info("Web search returned no results.")
    
    #builds the final prompt that will be sent to the AI model
    prompt = build_prompt(context_chunks=context, chat_history=history, question=message, web_results=web_results)
    logger.debug(f"Prompt built for LLM. Length: {len(prompt)} characters.")
    answer = generate_answer(prompt)
    logger.info(f"LLM generated answer for session {session_id}. Answer length: {len(answer)} characters.")

    save_message(session_id, "user", message)
    save_message(session_id, "assistant", answer)
    logger.debug(f"Messages saved for session {session_id}.")

    return {"session_id": session_id, "answer": answer, "flow_id": flow_id, "sources": context}

@app.post("/chat/stream")
async def chat_stream(
    message: str = Form(...), 
    flow_id: str = Form(None), 
    session_id: str = Form(None), 
    model: str = Form("llama-3.3-70b-versatile"),
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    Streaming chat endpoint.
    """
    username = current_user.username
    logger.info(f"Streaming chat request from user {username} - Message: '{message[:50]}...', Flow: {flow_id}, Session: {session_id}, Model: {model}")

    if not flow_id or flow_id == "string":
        flow = db.query(Flow).filter(Flow.user_id == current_user.id).order_by(Flow.created_at.desc()).first()
        if not flow:
            logger.warning(f"No flows found for user '{username}' during streaming chat request.")
            raise HTTPException(status_code=404, detail="No flows found.")
        flow_id = str(flow.id)
        logger.info(f"No flow_id provided, using most recent flow: {flow_id} for user {username} (streaming)")

    if not session_id or session_id == "string":
        session_id = str(uuid.uuid4())
        session = DBSession(id=session_id, flow_id=flow_id)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"New DBSession {session_id} created for flow {flow_id} (streaming).")

    history = get_chat_history(session_id)
    logger.debug(f"Chat history retrieved for session {session_id} (streaming), {len(history)} messages.")
    context = retrieve_chunks(message, flow_id=flow_id)

    # Meta-keywords that should prioritize document context over web search
    meta_keywords = ["summarize", "summary", "review", "brief", "outline", "overview", "what is this", "tell me about this"]
    is_meta_query = any(k in message.lower() for k in meta_keywords)

    # Context Fallback: If a meta-query returns zero results, force-retrieve first 10 chunks
    if not context and is_meta_query:
        logger.info(f"Meta-query '{message}' returned no context (Stream). Force-retrieving first 10 chunks as fallback.")
        context = get_first_chunks(flow_id, limit=10)
    
    # Calculate top score for logging/debugging
    top_score = context[0].get('score', 0) if context else 0
    logger.debug(f"Top Document Score (Stream): {top_score:.4f} for query: {message}")

    web_results = None

    if not context or (top_score < 0.7 and not is_meta_query):
        # Enrich the query for better streaming web results
        enriched_query = message
        if len(message.split()) <= 4:
            enriched_query += " definition meaning details"
            
        logger.info(f"Context too weak (score {top_score}) or no context, performing web search for: {enriched_query}... (streaming)")
        web_results = web_search(enriched_query)
        if web_results:
            logger.info(f"Web search returned {len(web_results)} results (streaming).")
        else:
            logger.info("Web search returned no results (streaming).")
    
    prompt = build_prompt(context_chunks=context, chat_history=history, question=message, web_results=web_results)
    logger.debug(f"Prompt built for LLM (streaming). Length: {len(prompt)} characters.")
    
    # Save user message immediately
    save_message(session_id, "user", message)
    logger.debug(f"User message saved for session {session_id} (streaming).")

    async def event_generator():
        try:
            # First yield the sources as a specific line
            sources_json = json.dumps(context)
            yield f"__SOURCES__:{sources_json}\n"
            
            full_response = ""
            # Groq streaming is synchronous in this context, but we yield it
            for chunk in generate_answer_stream(prompt, model=model):
                full_response += chunk
                yield chunk
            # Save assistant message after stream finishes
            save_message(session_id, "assistant", full_response)
            logger.info(f"LLM streaming answer completed and saved for session {session_id}. Answer length: {len(full_response)} characters.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during streaming generation: {error_msg}")
            yield f"__ERROR__:{error_msg}"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/flows/{flow_id}/review")
async def get_flow_review(
    flow_id: str, 
    current_user: User = Depends(get_current_active_user), 
    db: Session = Depends(get_db)
):
    """
    AI Document Reviewer endpoint.
    """
    logger.info(f"User {current_user.username} requesting review for flow: {flow_id}")
    # Verify ownership
    flow = db.query(Flow).filter(Flow.id == flow_id, Flow.user_id == current_user.id).first()
    if not flow:
        logger.warning(f"Flow {flow_id} not found or access denied for user {current_user.username} during review request.")
        raise HTTPException(status_code=404, detail="Flow not found")

    reviewer = DocumentReviewer(db_session=db)
    result = reviewer.review_document(flow_id)
    
    if "error" in result:
        logger.error(f"Error during document review for flow {flow_id}: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])
    
    logger.info(f"Document review completed for flow {flow_id}.")
    return result

@app.get("/chat/history/{session_id}")
async def fetch_chat_history(session_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Fetch chat history for a session.
    """
    logger.info(f"User {current_user.username} fetching chat history for session: {session_id}")
    history = get_chat_history(session_id)
    logger.debug(f"Retrieved {len(history)} messages for session {session_id}.")
    return history

# Evaluation Endpoints 
@app.post("/flows/{flow_id}/golden/auto-generate")
#only logged in users can generate golden qna
async def auto_generate_golden(flow_id: str, count: int = 5, current_user: User = Depends(get_current_active_user)):
    """
    Auto-generates 'Golden' Q&A pairs from documents in the flow.
    """
    logger.info(f"User {current_user.username} requesting auto-generation of {count} golden Q&A pairs for flow: {flow_id}")
    result = generate_golden_questions(flow_id, count)
    if "error" in result:
        logger.error(f"Error auto-generating golden Q&A for flow {flow_id}: {result['error']}")
    else:
        logger.info(f"Successfully auto-generated {result.get('generated_count', 0)} golden Q&A pairs for flow {flow_id}.")
    return result

#to view all golden qna pairs for a flow
@app.get("/flows/{flow_id}/golden")
async def get_golden_qa(flow_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    logger.info(f"User {current_user.username} fetching golden Q&A pairs for flow: {flow_id}")
    rows = db.query(GoldenQA).filter(GoldenQA.flow_id == flow_id).all()
    logger.debug(f"Retrieved {len(rows)} golden Q&A pairs for flow {flow_id}.")
    return [
        {"id": str(r.id), "question": r.question, "expected_answer": r.expected_answer, "created_at": str(r.created_at)} 
        for r in rows
    ]

#for evaluating the flow against golden qna pairs
@app.post("/flows/{flow_id}/evaluate")
async def run_evaluation(flow_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):

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
        
        # Call RAG Pipeline
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
