from celery import Celery
from app.core.config import settings
celery_app=Celery("pulseboard",broker=settings.celery_broker_url,backend=settings.celery_broker_url)
@celery_app.task
def task_created_notification(task_id:int):
    return {"task_id":task_id,"status":"notification_queued"}
