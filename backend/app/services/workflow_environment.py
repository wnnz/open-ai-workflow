from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.models.entities import WorkflowEnvironmentVariable


def cast_environment_value(value_type: str, value: str) -> Any:
    if value_type == "number":
        number = float(value)
        return int(number) if number.is_integer() else number
    return value


async def load_workflow_environment(
    db: AsyncSession, workspace_id: str, workflow_id: str
) -> dict[str, Any]:
    variables = list(
        (
            await db.scalars(
                select(WorkflowEnvironmentVariable).where(
                    WorkflowEnvironmentVariable.workspace_id == workspace_id,
                    WorkflowEnvironmentVariable.workflow_id == workflow_id,
                )
            )
        ).all()
    )
    return {
        variable.name: cast_environment_value(
            variable.value_type, decrypt_secret(variable.encrypted_value)
        )
        for variable in variables
    }


def build_system_variables(
    *, workflow_id: str, run_id: str, user_id: str = "", app_id: str | None = None
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "app_id": app_id or workflow_id,
        "workflow_id": workflow_id,
        "workflow_run_id": run_id,
        "timestamp": int(datetime.now(UTC).timestamp()),
    }
