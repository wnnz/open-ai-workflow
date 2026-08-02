from __future__ import annotations

import base64
import io
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


def execute_document(config: dict[str, Any]) -> dict[str, Any]:
    operation = str(config.get("operation") or "extract")
    if operation == "extract":
        return extract_docx(
            config.get("source"),
            include_images=config.get("extract_mode", "text") == "text_images",
        )
    if operation == "fill_answers":
        from app.services.answer_filling import fill_docx_answers

        return fill_docx_answers(
            config.get("source"),
            config.get("answers"),
            output_name=str(config.get("output_name") or ""),
        )
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "Only DOCX extraction is supported",
    )
