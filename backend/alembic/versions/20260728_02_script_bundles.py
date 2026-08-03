"""Store complete multi-file script bundles."""

import sqlalchemy as sa

from alembic import op

revision = "20260728_02"
down_revision = "20260728_01"
branch_labels = None
depends_on = None

script_versions = sa.table(
    "script_versions",
    sa.column("id", sa.String),
    sa.column("source_code", sa.Text),
    sa.column("source_files", sa.JSON),
)


def _columns() -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("script_versions")
    }


def upgrade() -> None:
    if "source_files" not in _columns():
        op.add_column(
            "script_versions",
            sa.Column(
                "source_files",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            script_versions.c.id,
            script_versions.c.source_code,
            script_versions.c.source_files,
        )
    ).mappings()
    for row in rows:
        if row["source_files"]:
            continue
        connection.execute(
            script_versions.update()
            .where(script_versions.c.id == row["id"])
            .values(source_files={"main.py": row["source_code"]})
        )


def downgrade() -> None:
    if "source_files" in _columns():
        op.drop_column("script_versions", "source_files")
