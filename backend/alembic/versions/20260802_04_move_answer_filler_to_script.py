"""Move draft answer-filler nodes to workspace scripts."""

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa

from alembic import op
from app.services.english_exam_script import (
    ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
    ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
    ENGLISH_EXAM_ANSWER_FILLER_NAME,
    ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
    ENGLISH_EXAM_ANSWER_FILLER_SLUG,
    ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
)
from app.services.scripts import validate_script

revision = "20260802_04"
down_revision = "20260729_03"
branch_labels = None
depends_on = None


workflows = sa.table(
    "workflows",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("draft_graph", sa.JSON),
    sa.column("draft_version", sa.Integer),
    sa.column("created_by", sa.String),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
scripts = sa.table(
    "scripts",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("description", sa.Text),
    sa.column("tags", sa.JSON),
    sa.column("latest_version", sa.Integer),
    sa.column("deleted_at", sa.DateTime(timezone=True)),
    sa.column("created_by", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)
script_versions = sa.table(
    "script_versions",
    sa.column("id", sa.String),
    sa.column("workspace_id", sa.String),
    sa.column("script_id", sa.String),
    sa.column("version", sa.Integer),
    sa.column("source_type", sa.String),
    sa.column("source_code", sa.Text),
    sa.column("source_files", sa.JSON),
    sa.column("entrypoint", sa.String),
    sa.column("input_schema", sa.JSON),
    sa.column("output_schema", sa.JSON),
    sa.column("content_hash", sa.String),
    sa.column("environment_version_id", sa.String),
    sa.column("change_note", sa.Text),
    sa.column("created_by", sa.String),
    sa.column("created_at", sa.DateTime(timezone=True)),
)


def legacy_answer_config(node: dict) -> dict | None:
    node_type = str(node.get("data", {}).get("nodeType") or node.get("type") or "")
    config = node.get("data", {}).get("config") or {}
    if node_type == "answer_filler":
        return dict(config)
    if node_type == "document" and config.get("operation") == "fill_answers":
        return {
            key: value
            for key, value in config.items()
            if key not in {"operation", "extract_mode", "page_range", "ocr_fallback"}
        }
    return None


def migrate_graph(graph: dict, script_id: str) -> tuple[dict, bool]:
    migrated = False
    next_graph = deepcopy(graph)
    for node in next_graph.get("nodes", []):
        config = legacy_answer_config(node)
        if config is None:
            continue
        migrated = True
        source = config.pop("source", "")
        answers = config.pop("answers", "")
        output_name = config.pop("output_name", "英语试卷_已作答.docx")
        node["type"] = "script"
        node.setdefault("data", {})["nodeType"] = "script"
        node["data"]["config"] = {
            **config,
            "script_id": script_id,
            "script_name": ENGLISH_EXAM_ANSWER_FILLER_NAME,
            "version": "latest",
            "inputs": {
                "source": source,
                "answers": answers,
                "output_name": output_name,
            },
            "input_schema": deepcopy(ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA),
            "output_schema": deepcopy(ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA),
        }
    return next_graph, migrated


def ensure_script(connection, workspace_id: str, created_by: str) -> str:
    existing = connection.execute(
        sa.select(
            scripts.c.id,
            scripts.c.latest_version,
            scripts.c.deleted_at,
        ).where(
            scripts.c.workspace_id == workspace_id,
            scripts.c.slug == ENGLISH_EXAM_ANSWER_FILLER_SLUG,
        )
    ).mappings().first()
    if existing and existing["deleted_at"] is None:
        return str(existing["id"])

    now = datetime.now(UTC)
    source_files = {"main.py": ENGLISH_EXAM_ANSWER_FILLER_SOURCE}
    digest = validate_script(
        ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
        "main:main",
        ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
        ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
        source_files,
    )
    if existing:
        script_id = str(existing["id"])
        version = int(existing["latest_version"]) + 1
        connection.execute(
            scripts.update()
            .where(scripts.c.id == script_id)
            .values(
                name=ENGLISH_EXAM_ANSWER_FILLER_NAME,
                description=ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
                tags=["document", "docx", "english-exam"],
                latest_version=version,
                deleted_at=None,
                updated_at=now,
            )
        )
    else:
        script_id = str(uuid4())
        version = 1
        connection.execute(
            scripts.insert().values(
                id=script_id,
                workspace_id=workspace_id,
                name=ENGLISH_EXAM_ANSWER_FILLER_NAME,
                slug=ENGLISH_EXAM_ANSWER_FILLER_SLUG,
                description=ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
                tags=["document", "docx", "english-exam"],
                latest_version=version,
                deleted_at=None,
                created_by=created_by,
                created_at=now,
                updated_at=now,
            )
        )
    connection.execute(
        script_versions.insert().values(
            id=str(uuid4()),
            workspace_id=workspace_id,
            script_id=script_id,
            version=version,
            source_type="python",
            source_code=ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
            source_files=source_files,
            entrypoint="main:main",
            input_schema=ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
            output_schema=ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
            content_hash=digest,
            environment_version_id=None,
            change_note="Moved answer filling to a workspace script",
            created_by=created_by,
            created_at=now,
        )
    )
    return script_id


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            workflows.c.id,
            workflows.c.workspace_id,
            workflows.c.draft_graph,
            workflows.c.draft_version,
            workflows.c.created_by,
        )
    ).mappings().all()
    script_ids: dict[str, str] = {}
    for row in rows:
        graph = row["draft_graph"] or {}
        if not any(legacy_answer_config(node) is not None for node in graph.get("nodes", [])):
            continue
        workspace_id = str(row["workspace_id"])
        script_id = script_ids.get(workspace_id)
        if not script_id:
            script_id = ensure_script(connection, workspace_id, str(row["created_by"]))
            script_ids[workspace_id] = script_id
        migrated_graph, migrated = migrate_graph(graph, script_id)
        if migrated:
            connection.execute(
                workflows.update()
                .where(workflows.c.id == row["id"])
                .values(
                    draft_graph=migrated_graph,
                    draft_version=int(row["draft_version"]) + 1,
                    updated_at=datetime.now(UTC),
                )
            )


def downgrade() -> None:
    # Published compatibility remains available; avoid rewriting user-edited drafts.
    pass
