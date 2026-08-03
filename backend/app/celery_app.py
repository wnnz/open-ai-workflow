from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery = Celery("ordo", broker=settings.redis_url, backend=settings.redis_url)
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
        },
        "recover-workflow-runs": {
            "task": "workflow.recover_runs",
            "schedule": 60.0,
        },
        "cleanup-stored-files": {
            "task": "storage.cleanup_files",
            "schedule": 3600.0,
        },
    },
)
