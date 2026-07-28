"""Adopt the existing schema and add queued execution fields."""

from alembic import op
import sqlalchemy as sa

from app.core.database import Base

revision = "20260728_01"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind())
    workflow_columns = _columns("workflows")
    if "next_run_at" not in workflow_columns:
        op.add_column("workflows", sa.Column("next_run_at", sa.DateTime(timezone=True)))
        op.create_index("ix_workflows_next_run_at", "workflows", ["next_run_at"])
    run_columns = _columns("workflow_runs")
    if "execution_graph" not in run_columns:
        op.add_column(
            "workflow_runs",
            sa.Column("execution_graph", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )
    if "trigger_user_id" not in run_columns:
        op.add_column("workflow_runs", sa.Column("trigger_user_id", sa.String(255)))


def downgrade() -> None:
    if "execution_graph" in _columns("workflow_runs"):
        op.drop_column("workflow_runs", "execution_graph")
    if "trigger_user_id" in _columns("workflow_runs"):
        op.drop_column("workflow_runs", "trigger_user_id")
    if "next_run_at" in _columns("workflows"):
        op.drop_index("ix_workflows_next_run_at", table_name="workflows")
        op.drop_column("workflows", "next_run_at")
