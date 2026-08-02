from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Script, ScriptVersion
from app.services.english_exam_script import (
    ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
    ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
    ENGLISH_EXAM_ANSWER_FILLER_NAME,
    ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
    ENGLISH_EXAM_ANSWER_FILLER_SLUG,
    ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
)
from app.services.scripts import validate_script


async def ensure_english_exam_answer_filler_script(
    db: AsyncSession,
    *,
    workspace_id: str,
    created_by: str,
) -> tuple[Script, bool]:
    script = await db.scalar(
        select(Script).where(
            Script.workspace_id == workspace_id,
            Script.slug == ENGLISH_EXAM_ANSWER_FILLER_SLUG,
        )
    )
    if script and script.deleted_at is None:
        return script, False

    files = {"main.py": ENGLISH_EXAM_ANSWER_FILLER_SOURCE}
    digest = validate_script(
        ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
        "main:main",
        ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
        ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
        files,
    )
    if script:
        script.deleted_at = None
        script.name = ENGLISH_EXAM_ANSWER_FILLER_NAME
        script.description = ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION
        script.tags = ["document", "docx", "english-exam"]
        script.latest_version += 1
    else:
        script = Script(
            workspace_id=workspace_id,
            name=ENGLISH_EXAM_ANSWER_FILLER_NAME,
            slug=ENGLISH_EXAM_ANSWER_FILLER_SLUG,
            description=ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
            tags=["document", "docx", "english-exam"],
            latest_version=1,
            created_by=created_by,
        )
        db.add(script)
        await db.flush()

    db.add(
        ScriptVersion(
            workspace_id=workspace_id,
            script_id=script.id,
            version=script.latest_version,
            source_code=ENGLISH_EXAM_ANSWER_FILLER_SOURCE,
            source_files=files,
            entrypoint="main:main",
            input_schema=ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
            output_schema=ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
            content_hash=digest,
            change_note="Built-in English exam answer filler",
            created_by=created_by,
        )
    )
    return script, True
