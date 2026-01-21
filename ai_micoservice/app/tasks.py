from app.celery_app import celery_app
from app.pdf_ingest import ingest_pdf, process_pdf_page
from app.pptx_ingest import ingest_pptx, process_pptx_slide
from app.config import REDIS_URL
import os
import redis
import json
import fitz # PyMuPDF
from celery import group
from app.logger import logger

# for connecting to redis
redis_client = redis.from_url(REDIS_URL)

# publishes the status of a task to Redis channel
def publish_update(task_id: str, status: str, message: str = "", filename: str = ""):
    data = {
        "task_id": task_id,
        "status": status,
        "message": message,
        "filename": filename
    }
    #to show live progress on the dashboard
    logger.debug(f"Publishing update for task {task_id}: {status} - {message}")
    redis_client.publish("task_updates", json.dumps(data))

#to process pdf synchronously
@celery_app.task(name="process_pdf_page_task")
def process_pdf_page_task(document_id: int, page_no: int, file_path: str):
    return process_pdf_page(document_id, page_no, file_path)

#for ppt
@celery_app.task(name="process_pptx_slide_task")
def process_pptx_slide_task(document_id: int, slide_no: int, slide_text: str):
    return process_pptx_slide(document_id, slide_no, slide_text)

#for any document processing task in parallel
@celery_app.task(bind=True, name="process_document")
def process_document_task(self, file_path: str, filename: str, flow_id: str, x_username: str):
#celery task id
    task_id = self.request.id
    try:
        #file extension
        ext = os.path.splitext(filename)[1].lower()
        logger.info(f"Processing task {task_id} for file {filename}")
        #report starting to ui
        publish_update(task_id, "processing", f"Initializing {ext.upper()} parallel analysis...", filename)
        
        from app.database import SessionLocal
        from app.models import Document
        db = SessionLocal()
        #pdf type
        if ext == ".pdf":
            # 1. Register document and get total pages
            pdf_doc = fitz.open(file_path)
            total_pages = len(pdf_doc)
            pdf_doc.close()
            
            doc = Document(filename=filename, file_path=file_path, file_type="pdf", status="processing", task_id=task_id, flow_id=flow_id)
            db.add(doc)
            db.commit()
            db.refresh(doc)
            document_id = doc.id
            db.close()

            publish_update(task_id, "processing", f"Processing {total_pages} pages in parallel...", filename)

            # 2. Spawn parallel tasks
            job = group(process_pdf_page_task.s(document_id, p, file_path) for p in range(1, total_pages + 1))
            result = job.apply_async()
            result.get() #wait for completion

            db = SessionLocal()
            doc = db.query(Document).get(document_id)
            doc.status = 'completed'
            db.commit()
            db.close()
            doc_id = document_id
            
        elif ext in [".pptx", ".ppt"]:
            from app.pptx_ingest import extract_text_from_pptx
            
            doc = Document(filename=filename, file_path=file_path, file_type="pptx", status="processing", task_id=task_id, flow_id=flow_id)
            db.add(doc)
            db.commit()
            db.refresh(doc)
            document_id = doc.id
            db.close()

            slides = list(extract_text_from_pptx(file_path))
            publish_update(task_id, "processing", f"Processing {len(slides)} slides in parallel...", filename)

            # Spawn parallel tasks for slides
            job = group(process_pptx_slide_task.s(document_id, s_no, s_text) for s_no, s_text in slides)
            result = job.apply_async()
            result.get()

            db = SessionLocal()
            doc = db.query(Document).get(document_id)
            doc.status = 'completed'
            db.commit()
            db.close()
            doc_id = document_id
        else:
            db.close()
            raise ValueError(f"Unsupported file type: {ext}")
        
        publish_update(task_id, "completed", f"{ext.upper()} processing successful.", filename)
        logger.info(f"Task {task_id} completed successfully for {filename}")
        return {"status": "success", "document_id": doc_id, "filename": filename, "task_id": task_id, "flow_id": flow_id, "username": x_username}
    except Exception as e:
        logger.error(f"Task {task_id} failed for {filename}: {str(e)}", exc_info=True)
        publish_update(task_id, "failed", str(e), filename)
        raise e

