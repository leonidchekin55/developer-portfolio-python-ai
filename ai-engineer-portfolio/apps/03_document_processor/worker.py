from celery import Celery
from sqlalchemy.exc import OperationalError
from shared.core import settings
from importlib import import_module
process=import_module("apps.03_document_processor.main").process
celery_app=Celery("document_processor",broker=settings.redis_url,backend=settings.redis_url)
celery_app.conf.update(task_acks_late=True,task_reject_on_worker_lost=True,worker_prefetch_multiplier=1,task_track_started=True,task_soft_time_limit=90,task_time_limit=120,result_expires=3600,broker_transport_options={"visibility_timeout":3600})
@celery_app.task(name="document_processor.process",autoretry_for=(OperationalError,ConnectionError),retry_backoff=True,retry_kwargs={"max_retries":3})
def process_document(document_id:str):
    process(document_id)
def enqueue_document(document_id:str):
    return process_document.delay(document_id)
