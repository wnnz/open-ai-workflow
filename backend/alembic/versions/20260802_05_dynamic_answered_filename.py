"""Derive answered DOCX names from their source files."""

import re
from copy import deepcopy
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from app.services.english_exam_script import ENGLISH_EXAM_ANSWER_FILLER_SLUG

revision = "20260802_05"
down_revision = "20260802_04"
branch_labels = None
depends_on = None

LEGACY_OUTPUT_NAME = "英语试卷_已作答.docx"
SOURCE_VARIABLE = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

workflows = sa.table(
    "workflows",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("draft_graph", sa.JSON),
    sa.column("draft_version", sa.Integer),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
scripts = sa.table(
    "scripts",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("slug", sa.String),
)


def dynamic_output_name(source: object) -> str | None:
    match = SOURCE_VARIABLE.fullmatch(source) if isinstance(source, str) else None
    if not match:
        return None
    return f"{{{{{match.group(1).strip()}.stem}}}}_已作答.docx"


def migrate_graph(graph: dict, script_id: str, *, downgrade: bool = False) -> tuple[dict, bool]:
    migrated = False
    next_graph = deepcopy(graph)
    for node in next_graph.get("nodes", []):
        if str(node.get("type") or node.get("data", {}).get("nodeType") or "") != "script":
            continue
        config = node.get("data", {}).get("config") or {}
        if str(config.get("script_id") or "") != script_id:
            continue
        inputs = config.get("inputs")
        if not isinstance(inputs, dict):
            continue
        dynamic_name = dynamic_output_name(inputs.get("source"))
        if not dynamic_name:
            continue
        expected, replacement = (
            (dynamic_name, LEGACY_OUTPUT_NAME)
            if downgrade
            else (LEGACY_OUTPUT_NAME, dynamic_name)
        )
        if inputs.get("output_name") != expected:
            continue
        inputs["output_name"] = replacement
        migrated = True
    return next_graph, migrated


def update_workflows(connection, *, downgrade: bool = False) -> None:
    script_rows = connection.execute(
        sa.select(scripts.c.id, scripts.c.workspace_id).where(
            scripts.c.slug == ENGLISH_EXAM_ANSWER_FILLER_SLUG
        )
    ).mappings().all()
    script_ids = {str(row["workspace_id"]): str(row["id"]) for row in script_rows}
    if not script_ids:
        return
    rows = connection.execute(
        sa.select(
            workflows.c.id,
            workflows.c.workspace_id,
            workflows.c.draft_graph,
            workflows.c.draft_version,
        ).where(workflows.c.workspace_id.in_(list(script_ids)))
    ).mappings().all()
    for row in rows:
        script_id = script_ids.get(str(row["workspace_id"]))
        if not script_id:
            continue
        graph, migrated = migrate_graph(
            row["draft_graph"] or {}, script_id, downgrade=downgrade
        )
        if migrated:
            connection.execute(
                workflows.update()
                .where(workflows.c.id == row["id"])
                .values(
                    draft_graph=graph,
                    draft_version=int(row["draft_version"]) + 1,
                    updated_at=datetime.now(UTC),
                )
            )


def upgrade() -> None:
    update_workflows(op.get_bind())


def downgrade() -> None:
    update_workflows(op.get_bind(), downgrade=True)
