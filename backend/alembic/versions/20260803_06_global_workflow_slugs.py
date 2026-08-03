"""Make published workflow slugs globally unique."""

from itertools import count

import sqlalchemy as sa

from alembic import op

revision = "20260803_06"
down_revision = "20260802_05"
branch_labels = None
depends_on = None

INDEX_NAME = "ux_workflows_slug"
MAX_SLUG_LENGTH = 80

workflows = sa.table(
    "workflows",
    sa.column("id", sa.String),
    sa.column("slug", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def unique_slug(slug: str, workflow_id: str, used: set[str]) -> str:
    token = workflow_id.replace("-", "")[:8] or "workflow"
    for index in count(1):
        suffix = f"-{token}" if index == 1 else f"-{token}-{index}"
        base = slug[: MAX_SLUG_LENGTH - len(suffix)].rstrip("-") or "workflow"
        candidate = f"{base}{suffix}"
        if candidate not in used:
            return candidate
    raise RuntimeError("Unable to allocate a unique workflow slug")


def deduplicate_slugs(connection) -> None:
    rows = connection.execute(
        sa.select(workflows.c.id, workflows.c.slug).order_by(workflows.c.created_at, workflows.c.id)
    ).mappings()
    used: set[str] = set()
    for row in rows:
        slug = str(row["slug"])
        if slug in used:
            slug = unique_slug(slug, str(row["id"]), used)
            connection.execute(
                workflows.update().where(workflows.c.id == row["id"]).values(slug=slug)
            )
        used.add(slug)


def index_names() -> set[str]:
    return {str(index["name"]) for index in sa.inspect(op.get_bind()).get_indexes("workflows")}


def upgrade() -> None:
    if INDEX_NAME in index_names():
        return
    deduplicate_slugs(op.get_bind())
    op.create_index(INDEX_NAME, "workflows", ["slug"], unique=True)


def downgrade() -> None:
    if INDEX_NAME in index_names():
        op.drop_index(INDEX_NAME, table_name="workflows")
