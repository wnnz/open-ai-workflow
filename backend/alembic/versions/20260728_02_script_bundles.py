"""Store complete multi-file script bundles."""

from alembic import op
import sqlalchemy as sa


revision = "20260728_02"
down_revision = "20260728_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "script_versions",
        sa.Column("source_files", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.execute(
        "UPDATE script_versions SET source_files = json_build_object('main.py', source_code) "
        "WHERE source_files::text = '{}'"
    )


def downgrade() -> None:
    op.drop_column("script_versions", "source_files")
