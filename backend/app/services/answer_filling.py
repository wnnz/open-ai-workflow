from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import HTTPException, status

from app.services import document_processing

MAX_INSERTIONS = 2_000
MAX_ANSWER_LENGTH = 100_000


def _answer_plan(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Answer plan is not valid JSON",
            ) from exc
    if not isinstance(value, dict) or not isinstance(value.get("insertions"), list):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Answer plan requires an insertions array",
        )
    insertions = value["insertions"]
    if len(insertions) > MAX_INSERTIONS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Answer plan contains too many insertions",
        )
    if any(not isinstance(item, dict) for item in insertions):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Answer plan contains an invalid insertion",
        )
    return insertions


def _normalized_anchor(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"\[图片\s*\d+\]", "", value)).casefold()


def _append_text_run(paragraph: ET.Element, text: str, *, bold: bool) -> None:
    run = ET.SubElement(paragraph, document_processing.qn(document_processing.W_NS, "r"))
    properties = ET.SubElement(run, document_processing.qn(document_processing.W_NS, "rPr"))
    if bold:
        ET.SubElement(properties, document_processing.qn(document_processing.W_NS, "b"))
    ET.SubElement(
        properties,
        document_processing.qn(document_processing.W_NS, "color"),
        {document_processing.qn(document_processing.W_NS, "val"): "FF0000"},
    )
    for index, line in enumerate(text.split("\n")):
        if index:
            ET.SubElement(run, document_processing.qn(document_processing.W_NS, "br"))
        node = ET.SubElement(
            run,
            document_processing.qn(document_processing.W_NS, "t"),
            {document_processing.qn(document_processing.XML_NS, "space"): "preserve"},
        )
        node.text = line


def _answer_paragraph(question_number: str, answer: str) -> ET.Element:
    paragraph = ET.Element(document_processing.W_P)
    _append_text_run(paragraph, f"Answer {question_number}: ", bold=True)
    _append_text_run(paragraph, answer, bold=False)
    return paragraph


def fill_docx_answers(
    source: Any,
    answers: Any,
    *,
    output_name: str = "",
) -> dict[str, Any]:
    content, filename = document_processing._source_file(source)
    insertions = _answer_plan(answers)
    with document_processing._open_docx(content) as package:
        document_xml = package.read(document_processing.DOCUMENT_XML)
        namespaces = document_processing._register_namespaces(document_xml)
        root = document_processing._parse_document(document_xml)
        paragraphs = list(root.iter(document_processing.W_P))
        parents = {child: parent for parent in root.iter() for child in parent}
        paragraph_texts = [
            document_processing._paragraph_text(paragraph) for paragraph in paragraphs
        ]
        last_inserted: dict[ET.Element, ET.Element] = {}
        report: list[dict[str, Any]] = []

        for insertion in insertions:
            question_number = str(insertion.get("question_number") or "").strip()
            answer = str(insertion.get("answer") or "").strip()
            anchor_id = str(insertion.get("anchor_id") or "").strip().upper()
            anchor_text = str(insertion.get("anchor") or "").strip()
            if len(answer) > MAX_ANSWER_LENGTH:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    "An answer is too long",
                )

            anchor_index: int | None = None
            match = re.fullmatch(r"P(\d+)", anchor_id)
            if match and 1 <= int(match.group(1)) <= len(paragraphs):
                anchor_index = int(match.group(1)) - 1
                matched_by = "anchor_id"
            else:
                normalized = _normalized_anchor(anchor_text)
                candidates = [
                    index
                    for index, text in enumerate(paragraph_texts)
                    if normalized and _normalized_anchor(text) == normalized
                ]
                if not candidates and normalized:
                    candidates = [
                        index
                        for index, text in enumerate(paragraph_texts)
                        if normalized in _normalized_anchor(text)
                        or _normalized_anchor(text) in normalized
                    ]
                if candidates:
                    anchor_index = candidates[-1]
                    anchor_id = f"P{anchor_index + 1:04d}"
                    matched_by = "anchor"
                else:
                    report.append(
                        {
                            "question_number": question_number,
                            "anchor_id": anchor_id,
                            "status": "not_found",
                        }
                    )
                    continue

            anchor = paragraphs[anchor_index]
            parent = parents.get(anchor)
            if parent is None:
                report.append(
                    {
                        "question_number": question_number,
                        "anchor_id": anchor_id,
                        "status": "not_found",
                    }
                )
                continue
            previous = last_inserted.get(anchor, anchor)
            paragraph = _answer_paragraph(question_number, answer)
            parent.insert(list(parent).index(previous) + 1, paragraph)
            last_inserted[anchor] = paragraph
            report.append(
                {
                    "question_number": question_number,
                    "anchor_id": anchor_id,
                    "status": "inserted",
                    "matched_by": matched_by,
                }
            )

        document_processing._remove_unbound_ignorable_prefixes(root, namespaces)
        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as target:
            for entry in package.infolist():
                target.writestr(
                    entry,
                    updated_xml
                    if entry.filename == document_processing.DOCUMENT_XML
                    else package.read(entry.filename),
                )

    stem = Path(filename).stem or "document"
    requested_name = Path(output_name).name.strip() if output_name else ""
    result_name = requested_name or f"{stem}_已作答.docx"
    if not result_name.casefold().endswith(".docx"):
        result_name = f"{result_name}.docx"
    inserted_count = sum(item["status"] == "inserted" for item in report)
    return {
        "file": document_processing.GeneratedFile(
            result_name,
            document_processing.DOCX_CONTENT_TYPE,
            output.getvalue(),
        ),
        "inserted_count": inserted_count,
        "requested_count": len(insertions),
        "insertions": report,
    }
