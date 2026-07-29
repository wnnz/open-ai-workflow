"""Add protected workflow access policies."""

from alembic import op
import sqlalchemy as sa


revision = "20260729_03"
down_revision = "20260728_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_access_grants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("grant_type", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_access_grants_workspace_id", "workflow_access_grants", ["workspace_id"])
    op.create_index("ix_workflow_access_grants_workflow_id", "workflow_access_grants", ["workflow_id"])
    op.create_index("ix_workflow_access_grants_grant_type", "workflow_access_grants", ["grant_type"])
    op.create_index("ix_workflow_access_grants_user_id", "workflow_access_grants", ["user_id"])
    op.execute(
        "INSERT INTO workflow_access_grants "
        "(id, workspace_id, workflow_id, grant_type, user_id, label, password_hash, "
        "expires_at, created_by, created_at) "
        "SELECT md5(random()::text || clock_timestamp()::text || id), workspace_id, id, "
        "'all_users', NULL, 'All signed-in users', NULL, NULL, created_by, CURRENT_TIMESTAMP "
        "FROM workflows WHERE published_access = 'protected'"
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_access_grants_user_id", table_name="workflow_access_grants")
    op.drop_index("ix_workflow_access_grants_grant_type", table_name="workflow_access_grants")
    op.drop_index("ix_workflow_access_grants_workflow_id", table_name="workflow_access_grants")
    op.drop_index("ix_workflow_access_grants_workspace_id", table_name="workflow_access_grants")
    op.drop_table("workflow_access_grants")
