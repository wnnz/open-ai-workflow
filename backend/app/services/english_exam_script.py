from pathlib import Path
from typing import Any

ENGLISH_EXAM_ANSWER_FILLER_TEMPLATE_ID = "english-exam-answer-filler"
ENGLISH_EXAM_ANSWER_FILLER_SLUG = "english-exam-answer-filler"
ENGLISH_EXAM_ANSWER_FILLER_NAME = "英语试卷答案填充"
ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION = (
    "按段落锚点将答案以红色文字插入原始 DOCX，并返回可下载的新文件。"
)
ENGLISH_EXAM_ANSWER_FILLER_SOURCE = (
    Path(__file__).parents[1]
    .joinpath("script_sources", "english_exam_answer_filler.py")
    .read_text(encoding="utf-8")
)

FILE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "x-ordo-type": "file",
    "properties": {
        "id": {"type": "string"},
        "filename": {"type": "string"},
        "content_type": {"type": "string"},
        "size": {"type": "integer"},
    },
    "required": ["filename", "content_type"],
}

ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "source": {
            **FILE_SCHEMA,
            "description": "需要写入答案的原始 DOCX 文件",
        },
        "answers": {
            "type": "object",
            "description": "包含 insertions 数组的答案方案",
        },
        "output_name": {
            "type": "string",
            "description": "输出 DOCX 文件名",
            "default": "英语试卷_已作答.docx",
        },
    },
    "required": ["source", "answers"],
}

ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "file": {**FILE_SCHEMA, "description": "已填入答案的 DOCX 文件"},
        "inserted_count": {"type": "integer"},
        "requested_count": {"type": "integer"},
        "insertions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_number": {"type": "string"},
                    "anchor_id": {"type": "string"},
                    "status": {"type": "string"},
                    "matched_by": {"type": "string"},
                },
                "required": ["question_number", "anchor_id", "status"],
            },
        },
    },
    "required": ["file", "inserted_count", "requested_count", "insertions"],
}


def english_exam_answer_filler_template() -> dict[str, Any]:
    return {
        "id": ENGLISH_EXAM_ANSWER_FILLER_TEMPLATE_ID,
        "name": ENGLISH_EXAM_ANSWER_FILLER_NAME,
        "description": ENGLISH_EXAM_ANSWER_FILLER_DESCRIPTION,
        "category": "document",
        "source_files": {"main.py": ENGLISH_EXAM_ANSWER_FILLER_SOURCE},
        "entrypoint": "main:main",
        "input_schema": ENGLISH_EXAM_ANSWER_FILLER_INPUT_SCHEMA,
        "output_schema": ENGLISH_EXAM_ANSWER_FILLER_OUTPUT_SCHEMA,
        "sample_inputs": {
            "source": None,
            "answers": {"insertions": []},
            "output_name": "英语试卷_已作答.docx",
        },
    }
