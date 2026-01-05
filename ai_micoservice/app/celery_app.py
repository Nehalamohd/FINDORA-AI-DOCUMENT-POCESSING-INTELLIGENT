from celery import Celery
from app.config import REDIS_URL

# Initialize Celery app, broker redis, store task back to redis
#tasks are inside the tasks.py
celery_app = Celery(
    "findora_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"]
)
# task and result is converted to json format
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
