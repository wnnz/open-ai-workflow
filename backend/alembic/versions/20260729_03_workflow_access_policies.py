"""Add protected workflow access policies."""

from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "20260729_03"
down_revision = "20260728_02"
branch_labels = None
depends_on = None

INDEXES = {
    "ix_workflow_access_grants_workspace_id": ["workspace_id"],
    "ix_workflow_access_grants_workflow_id": ["workflow_id"],
    "ix_workflow_access_grants_grant_type": ["grant_type"],
    "ix_workflow_access_grants_user_id": ["user_id"],
}
workflows = sa.table(
    "workflows",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("published_access", sa.String),
    sa.column("created_by", sa.String),
)
workflow_access_grants = sa.table(
    "workflow_access_grants",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("workflow_id", sa.String),
    sa.column("grant_type", sa.String),
    sa.column("user_id", sa.String),
    sa.column("label", sa.String),
    sa.column("password_hash", sa.Text),
    sa.column("expires_at", sa.DateTime(timezone=True)),
    sa.column("created_by", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes() -> set[str]:
    return {
        str(index["name"])
        for index in sa.inspect(op.get_bind()).get_indexes("workflow_access_grants")
    }


def upgrade() -> None:
    if "workflow_access_grants" not in _tables():
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
    existing_indexes = _indexes()
    for name, columns in INDEXES.items():
        if name not in existing_indexes:
            op.create_index(name, "workflow_access_grants", columns)

    connection = op.get_bind()
    granted_workflow_ids = set(
        connection.scalars(
            sa.select(workflow_access_grants.c.workflow_id).where(
                workflow_access_grants.c.grant_type == "all_users"
            )
        )
    )
    protected = connection.execute(
        sa.select(
            workflows.c.id,
            workflows.c.workspace_id,
            workflows.c.created_by,
        ).where(workflows.c.published_access == "protected")
    ).mappings()
    for row in protected:
        if row["id"] in granted_workflow_ids:
            continue
        connection.execute(
            workflow_access_grants.insert().values(
                id=str(uuid4()),
                workspace_id=row["workspace_id"],
                workflow_id=row["id"],
                grant_type="all_users",
                user_id=None,
                label="All signed-in users",
                password_hash=None,
                expires_at=None,
                created_by=row["created_by"],
                created_at=datetime.now(UTC),
            )
        )


def downgrade() -> None:
    if "workflow_access_grants" not in _tables():
        return
    existing_indexes = _indexes()
    for name in reversed(INDEXES):
        if name in existing_indexes:
            op.drop_index(name, table_name="workflow_access_grants")
    op.drop_table("workflow_access_grants")
