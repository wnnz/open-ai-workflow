"""Add workflow run controls and stored file lifecycle fields."""

import sqlalchemy as sa

from alembic import op

revision = "20260803_07"
down_revision = "20260803_06"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _indexes(table: str) -> set[str]:
    return {str(index["name"]) for index in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade() -> None:
    run_columns = _columns("workflow_runs")
    additions = {
        "task_id": sa.Column("task_id", sa.String(36)),
        "attempt_count": sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        "retry_of_run_id": sa.Column("retry_of_run_id", sa.String(36)),
        "idempotency_key": sa.Column("idempotency_key", sa.String(128)),
        "request_fingerprint": sa.Column("request_fingerprint", sa.String(64)),
        "lease_token": sa.Column("lease_token", sa.String(36)),
        "lease_expires_at": sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        "started_at": sa.Column("started_at", sa.DateTime(timezone=True)),
        "cancel_requested_at": sa.Column(
            "cancel_requested_at", sa.DateTime(timezone=True)
        ),
    }
    for name, column in additions.items():
        if name not in run_columns:
            op.add_column("workflow_runs", column)

    run_indexes = _indexes("workflow_runs")
    indexes = {
        "ix_workflow_runs_task_id": (["task_id"], False),
        "ix_workflow_runs_retry_of_run_id": (["retry_of_run_id"], False),
        "ix_workflow_runs_lease_expires_at": (["lease_expires_at"], False),
        "ux_workflow_runs_idempotency": (
            ["workflow_id", "triggered_by", "idempotency_key"],
            True,
        ),
    }
    for name, (columns, unique) in indexes.items():
        if name not in run_indexes:
            op.create_index(name, "workflow_runs", columns, unique=unique)

    file_columns = _columns("stored_files")
    if "purpose" not in file_columns:
        op.add_column(
            "stored_files",
            sa.Column(
                "purpose", sa.String(40), nullable=False, server_default=sa.text("'upload'")
            ),
        )
    if "expires_at" not in file_columns:
        op.add_column("stored_files", sa.Column("expires_at", sa.DateTime(timezone=True)))
    if "ix_stored_files_expires_at" not in _indexes("stored_files"):
        op.create_index("ix_stored_files_expires_at", "stored_files", ["expires_at"])


def downgrade() -> None:
    if "ix_stored_files_expires_at" in _indexes("stored_files"):
        op.drop_index("ix_stored_files_expires_at", table_name="stored_files")
    for name in ("expires_at", "purpose"):
        if name in _columns("stored_files"):
            op.drop_column("stored_files", name)

    for name in (
        "ux_workflow_runs_idempotency",
        "ix_workflow_runs_lease_expires_at",
        "ix_workflow_runs_retry_of_run_id",
        "ix_workflow_runs_task_id",
    ):
        if name in _indexes("workflow_runs"):
            op.drop_index(name, table_name="workflow_runs")
    for name in (
        "cancel_requested_at",
        "started_at",
        "lease_expires_at",
        "lease_token",
        "request_fingerprint",
        "idempotency_key",
        "retry_of_run_id",
        "attempt_count",
        "task_id",
    ):
        if name in _columns("workflow_runs"):
            op.drop_column("workflow_runs", name)
