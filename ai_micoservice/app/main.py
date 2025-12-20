from fastapi import FastAPI, UploadFile, Form
import uuid
from app.pdf_ingest import ingest_pdf
from app.rag import retrieve_chunks, build_prompt
from app.llm import generate_answer
from app.chat import save_message, get_chat_history

app = FastAPI(title="Findora AI Service")

# PDF Upload Endpoint
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile):
    temp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    ingest_pdf(file_path=temp_path, filename=file.filename)
    return {"status": "PDF ingested successfully"}

# Chat Endpoint
@app.post("/chat")
async def chat(message: str = Form(...), session_id: str = Form(None)):
    session_id = session_id or str(uuid.uuid4())
    history = get_chat_history(session_id)
    context = retrieve_chunks(message)
    prompt = build_prompt(context_chunks=context, chat_history=history, question=message)
    answer = generate_answer(prompt)

    save_message(session_id, "user", message)
    save_message(session_id, "assistant", answer)

    return {"session_id": session_id, "answer": answer}
