from app.celery_app import celery_app
from app.pdf_ingest import ingest_pdf
from app.config import REDIS_URL
import os
import redis
import json

redis_client = redis.from_url(REDIS_URL)

def publish_update(task_id: str, status: str, message: str = "", filename: str = ""):
    data = {
        "task_id": task_id,
        "status": status,
        "message": message,
        "filename": filename
    }
    redis_client.publish("task_updates", json.dumps(data))

@celery_app.task(bind=True, name="process_pdf")
def process_pdf_task(self, file_path: str, filename: str, flow_id: str = None):
    task_id = self.request.id
    try:
        publish_update(task_id, "processing", "Starting PDF analysis...", filename)
        
        doc_id = ingest_pdf(file_path, filename, task_id=task_id, flow_id=flow_id)
        
        publish_update(task_id, "completed", "PDF processing successful.", filename)
        return {"status": "success", "document_id": doc_id, "filename": filename, "task_id": task_id}
    except Exception as e:
        publish_update(task_id, "failed", str(e), filename)
        # We raise the exception so Celery marks the task as FAILURE
        raise e
