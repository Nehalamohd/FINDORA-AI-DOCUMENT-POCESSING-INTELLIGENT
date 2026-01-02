from app.celery_app import celery_app
from app.pdf_ingest import ingest_pdf
from app.pptx_ingest import ingest_pptx
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

@celery_app.task(bind=True, name="process_document")
def process_document_task(self, file_path: str, filename: str, flow_id: str, x_username: str):
    task_id = self.request.id
    try:
        ext = os.path.splitext(filename)[1].lower()
        publish_update(task_id, "processing", f"Starting {ext.upper()} analysis...", filename)
        
        if ext == ".pdf":
            doc_id = ingest_pdf(file_path, filename, task_id=task_id, flow_id=flow_id, username=x_username)
        elif ext in [".pptx", ".ppt"]:
            doc_id = ingest_pptx(file_path, filename, task_id=task_id, flow_id=flow_id, username=x_username)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")
        
        publish_update(task_id, "completed", f"{ext.upper()} processing successful.", filename)
        return {"status": "success", "document_id": doc_id, "filename": filename, "task_id": task_id, "flow_id": flow_id, "username": x_username}
    except Exception as e:
        publish_update(task_id, "failed", str(e), filename)
        raise e
