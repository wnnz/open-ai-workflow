from app.celery_app import celery
from app.core.config import get_settings


async def enqueue_workflow_run(
    run_id: str,
    approval_id: str | None = None,
    *,
    task_id: str | None = None,
) -> bool:
    if get_settings().task_always_eager:
        from app.worker import _execute_run

        await _execute_run(run_id, approval_id)
        return True
    celery.send_task(
        "workflow.execute_run",
        args=[run_id, approval_id],
        task_id=task_id,
    )
    return False
