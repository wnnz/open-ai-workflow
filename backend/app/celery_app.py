from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery = Celery("openworkflow", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_hijack_root_logger=False,
    beat_schedule={
        "dispatch-workflow-schedules": {
            "task": "workflow.dispatch_schedules",
            "schedule": 60.0,
        }
    },
)
