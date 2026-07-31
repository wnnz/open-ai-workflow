from __future__ import annotations

import base64
import io
import json
import mimetypes
import posixpath
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from fastapi import HTTPException, status

from app.services.storage import object_path

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCUMENT_XML = "word/document.xml"
RELATIONSHIPS_XML = "word/_rels/document.xml.rels"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
XML_NS = "http://www.w3.org/XML/1998/namespace"
MAX_DOCX_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_INSERTIONS = 2_000
MAX_ANSWER_LENGTH = 100_000


def qn(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


W_P = qn(W_NS, "p")
W_T = qn(W_NS, "t")
W_TAB = qn(W_NS, "tab")
W_BR = qn(W_NS, "br")
A_BLIP = qn(A_NS, "blip")


@dataclass(frozen=True)
class GeneratedFile:
    filename: str
    content_type: str
    content: bytes


def _source_file(source: Any) -> tuple[bytes, str]:
    if not isinstance(source, dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Document source must be a file")
    object_key = str(source.get("__ordo_object_key") or "")
    if not object_key:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Document source file is unavailable")
    path = object_path(object_key)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document source file was not found")
    return path.read_bytes(), str(source.get("filename") or path.name or "document.docx")


def _open_docx(content: bytes) -> zipfile.ZipFile:
    try:
        package = zipfile.ZipFile(io.BytesIO(content), "r")
    except zipfile.BadZipFile as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Document is not a valid DOCX file") from exc
    entries = package.infolist()
    if DOCUMENT_XML not in package.namelist():
        package.close()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Document is not a valid DOCX file")
    if len(entries) > MAX_DOCX_ENTRIES or sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_BYTES:
        package.close()
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Expanded DOCX file is too large")
    return package


def _register_namespaces(xml_bytes: bytes) -> dict[str, str]:
    namespaces: dict[str, str] = {}
    try:
        for _, item in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
            prefix, uri = item
            namespaces[prefix or ""] = uri
            if not re.fullmatch(r"ns\d+", prefix or ""):
                ET.register_namespace(prefix or "", uri)
    except ET.ParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "DOCX document XML is invalid") from exc
    return namespaces


def _parse_document(xml_bytes: bytes) -> ET.Element:
    _register_namespaces(xml_bytes)
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "DOCX document XML is invalid") from exc


def _remove_unbound_ignorable_prefixes(root: ET.Element, namespaces: dict[str, str]) -> None:
    attribute = qn(MC_NS, "Ignorable")
    value = root.get(attribute)
    if not value:
        return
    used_namespaces: set[str] = set()
    for element in root.iter():
        names = [element.tag, *element.attrib]
        used_namespaces.update(
            name[1:].partition("}")[0]
            for name in names
            if isinstance(name, str) and name.startswith("{") and "}" in name
        )
    prefixes = [
        prefix
        for prefix in value.split()
        if namespaces.get(prefix) in used_namespaces
    ]
    if prefixes:
        root.set(attribute, " ".join(prefixes))
    else:
        root.attrib.pop(attribute, None)


def _paragraph_text(paragraph: ET.Element) -> str:
    parts: list[str] = []
    for element in paragraph.iter():
        if element.tag == W_T:
            parts.append(element.text or "")
        elif element.tag == W_TAB:
            parts.append("\t")
        elif element.tag == W_BR:
            parts.append("\n")
    return "".join(parts).strip()


def _relationships(package: zipfile.ZipFile) -> dict[str, str]:
    if RELATIONSHIPS_XML not in package.namelist():
        return {}
    try:
        root = ET.fromstring(package.read(RELATIONSHIPS_XML))
    except ET.ParseError:
        return {}
    return {
        str(item.get("Id")): str(item.get("Target"))
        for item in root.findall(qn(REL_NS, "Relationship"))
        if item.get("Id") and item.get("Target") and item.get("TargetMode") != "External"
    }


def _relationship_path(target: str) -> str:
    return posixpath.normpath(posixpath.join("word", target)).lstrip("/")


def _image_content_type(filename: str) -> str:
    content_type, _ = mimetypes.guess_type(filename)
    return content_type if content_type and content_type.startswith("image/") else "application/octet-stream"


def extract_docx(source: Any, *, include_images: bool = False) -> dict[str, Any]:
    content, filename = _source_file(source)
    with _open_docx(content) as package:
        root = _parse_document(package.read(DOCUMENT_XML))
        relationships = _relationships(package)
        images: list[dict[str, Any]] = []
        warnings: list[str] = []
        lines: list[str] = []
        image_number = 0
        paragraphs = list(root.iter(W_P))
        for index, paragraph in enumerate(paragraphs, start=1):
            paragraph_id = f"P{index:04d}"
            text = _paragraph_text(paragraph)
            markers: list[str] = []
            for blip in paragraph.iter(A_BLIP):
                relationship_id = blip.get(qn(R_NS, "embed"))
                target = relationships.get(str(relationship_id or ""))
                if not target:
                    warnings.append(f"{paragraph_id}: embedded image relationship is missing")
                    continue
                package_path = _relationship_path(target)
                if package_path not in package.namelist():
                    warnings.append(f"{paragraph_id}: embedded image file is missing")
                    continue
                image_number += 1
                marker = f"[图片 {image_number}]"
                markers.append(marker)
                if include_images:
                    image_bytes = package.read(package_path)
                    content_type = _image_content_type(package_path)
                    images.append(
                        {
                            "name": Path(package_path).name,
                            "content_type": content_type,
                            "data_url": f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
                            "paragraph_id": paragraph_id,
                            "marker": marker,
                        }
                    )
            rendered = " ".join(part for part in [text, *markers] if part)
            lines.append(f"[{paragraph_id}] {rendered}".rstrip())

        tables: list[dict[str, Any]] = []
        for table_index, table in enumerate(root.iter(qn(W_NS, "tbl")), start=1):
            rows: list[list[str]] = []
            for row in table.findall(qn(W_NS, "tr")):
                cells = [
                    "\n".join(_paragraph_text(paragraph) for paragraph in cell.iter(W_P)).strip()
                    for cell in row.findall(qn(W_NS, "tc"))
                ]
                rows.append(cells)
            tables.append({"index": table_index, "rows": rows})

    return {
        "content": "\n".join(lines),
        "paragraph_count": len(paragraphs),
        "tables": tables,
        "images": images,
        "filename": filename,
        "warnings": warnings,
    }


def _answer_plan(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Answer plan is not valid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("insertions"), list):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Answer plan requires an insertions array")
    insertions = value["insertions"]
    if len(insertions) > MAX_INSERTIONS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Answer plan contains too many insertions")
    if any(not isinstance(item, dict) for item in insertions):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Answer plan contains an invalid insertion")
    return insertions


def _normalized_anchor(value: str) -> str:
    return re.sub(r"\s+", "", re.sub(r"\[图片\s*\d+\]", "", value)).casefold()


def _append_text_run(paragraph: ET.Element, text: str, *, bold: bool) -> None:
    run = ET.SubElement(paragraph, qn(W_NS, "r"))
    properties = ET.SubElement(run, qn(W_NS, "rPr"))
    if bold:
        ET.SubElement(properties, qn(W_NS, "b"))
    ET.SubElement(properties, qn(W_NS, "color"), {qn(W_NS, "val"): "FF0000"})
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if index:
            ET.SubElement(run, qn(W_NS, "br"))
        node = ET.SubElement(run, qn(W_NS, "t"), {qn(XML_NS, "space"): "preserve"})
        node.text = line


def _answer_paragraph(question_number: str, answer: str) -> ET.Element:
    paragraph = ET.Element(W_P)
    _append_text_run(paragraph, f"Answer {question_number}: ", bold=True)
    _append_text_run(paragraph, answer, bold=False)
    return paragraph


def fill_docx_answers(source: Any, answers: Any, *, output_name: str = "") -> dict[str, Any]:
    content, filename = _source_file(source)
    insertions = _answer_plan(answers)
    with _open_docx(content) as package:
        document_xml = package.read(DOCUMENT_XML)
        namespaces = _register_namespaces(document_xml)
        root = _parse_document(document_xml)
        paragraphs = list(root.iter(W_P))
        parents = {child: parent for parent in root.iter() for child in parent}
        paragraph_texts = [_paragraph_text(paragraph) for paragraph in paragraphs]
        last_inserted: dict[ET.Element, ET.Element] = {}
        report: list[dict[str, Any]] = []

        for insertion in insertions:
            question_number = str(insertion.get("question_number") or "").strip() or ""
            answer = str(insertion.get("answer") or "").strip()
            anchor_id = str(insertion.get("anchor_id") or "").strip().upper()
            anchor_text = str(insertion.get("anchor") or "").strip()
            if len(answer) > MAX_ANSWER_LENGTH:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "An answer is too long")

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
                        if normalized in _normalized_anchor(text) or _normalized_anchor(text) in normalized
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

        _remove_unbound_ignorable_prefixes(root, namespaces)
        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as target:
            for entry in package.infolist():
                target.writestr(entry, updated_xml if entry.filename == DOCUMENT_XML else package.read(entry.filename))

    stem = Path(filename).stem or "document"
    requested_name = Path(output_name).name.strip() if output_name else ""
    result_name = requested_name or f"{stem}_已作答.docx"
    if not result_name.casefold().endswith(".docx"):
        result_name = f"{result_name}.docx"
    inserted_count = sum(item["status"] == "inserted" for item in report)
    return {
        "file": GeneratedFile(result_name, DOCX_CONTENT_TYPE, output.getvalue()),
        "inserted_count": inserted_count,
        "requested_count": len(insertions),
        "insertions": report,
    }


def execute_document(config: dict[str, Any]) -> dict[str, Any]:
    operation = str(config.get("operation") or "extract")
    if operation == "extract":
        return extract_docx(
            config.get("source"),
            include_images=config.get("extract_mode", "text") == "text_images",
        )
    if operation == "fill_answers":
        return fill_docx_answers(
            config.get("source"),
            config.get("answers"),
            output_name=str(config.get("output_name") or ""),
        )
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Only DOCX extraction and answer filling are supported",
    )
