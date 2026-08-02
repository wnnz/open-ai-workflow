import io
import json
import re
import zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
DOCUMENT_XML = "word/document.xml"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
XML_NS = "http://www.w3.org/XML/1998/namespace"
MAX_DOCX_ENTRIES = 10_000
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_INSERTIONS = 2_000
MAX_ANSWER_LENGTH = 100_000


def qn(namespace, name):
    return f"{{{namespace}}}{name}"


W_P = qn(W_NS, "p")
W_R = qn(W_NS, "r")
W_RPR = qn(W_NS, "rPr")
W_B = qn(W_NS, "b")
W_COLOR = qn(W_NS, "color")
W_T = qn(W_NS, "t")
W_TAB = qn(W_NS, "tab")
W_BR = qn(W_NS, "br")


def answer_plan(value):
    if isinstance(value, str):
        raw = value.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Answer plan is not valid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("insertions"), list):
        raise ValueError("Answer plan requires an insertions array")
    insertions = value["insertions"]
    if len(insertions) > MAX_INSERTIONS:
        raise ValueError("Answer plan contains too many insertions")
    if any(not isinstance(item, dict) for item in insertions):
        raise ValueError("Answer plan contains an invalid insertion")
    return insertions


def normalized_anchor(value):
    return re.sub(r"\s+", "", re.sub(r"\[图片\s*\d+\]", "", value)).casefold()


def register_namespaces(xml_bytes):
    namespaces = {}
    try:
        for _, item in ET.iterparse(io.BytesIO(xml_bytes), events=("start-ns",)):
            prefix, uri = item
            namespaces[prefix or ""] = uri
            if not re.fullmatch(r"ns\d+", prefix or ""):
                ET.register_namespace(prefix or "", uri)
    except ET.ParseError as exc:
        raise ValueError("DOCX document XML is invalid") from exc
    return namespaces


def parse_document(xml_bytes):
    register_namespaces(xml_bytes)
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ValueError("DOCX document XML is invalid") from exc


def paragraph_text(paragraph):
    parts = []
    for element in paragraph.iter():
        if element.tag == W_T:
            parts.append(element.text or "")
        elif element.tag == W_TAB:
            parts.append("\t")
        elif element.tag == W_BR:
            parts.append("\n")
    return "".join(parts).strip()


def remove_unbound_ignorable_prefixes(root, namespaces):
    attribute = qn(MC_NS, "Ignorable")
    value = root.get(attribute)
    if not value:
        return
    used_namespaces = set()
    for element in root.iter():
        names = [element.tag, *element.attrib]
        used_namespaces.update(
            name[1:].partition("}")[0]
            for name in names
            if isinstance(name, str) and name.startswith("{") and "}" in name
        )
    prefixes = [
        prefix for prefix in value.split() if namespaces.get(prefix) in used_namespaces
    ]
    if prefixes:
        root.set(attribute, " ".join(prefixes))
    else:
        root.attrib.pop(attribute, None)


def append_text_run(paragraph, text, bold=False):
    run = ET.SubElement(paragraph, W_R)
    properties = ET.SubElement(run, W_RPR)
    if bold:
        ET.SubElement(properties, W_B)
    ET.SubElement(properties, W_COLOR, {qn(W_NS, "val"): "FF0000"})
    for index, line in enumerate(text.split("\n")):
        if index:
            ET.SubElement(run, W_BR)
        node = ET.SubElement(
            run,
            W_T,
            {qn(XML_NS, "space"): "preserve"},
        )
        node.text = line


def answer_paragraph(question_number, answer):
    paragraph = ET.Element(W_P)
    append_text_run(paragraph, f"Answer {question_number}: ", bold=True)
    append_text_run(paragraph, answer)
    return paragraph


def open_docx(path):
    try:
        package = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise ValueError("Document is not a valid DOCX file") from exc
    entries = package.infolist()
    if DOCUMENT_XML not in package.namelist():
        package.close()
        raise ValueError("Document is not a valid DOCX file")
    if len(entries) > MAX_DOCX_ENTRIES or sum(
        item.file_size for item in entries
    ) > MAX_UNCOMPRESSED_BYTES:
        package.close()
        raise ValueError("Expanded DOCX file is too large")
    return package


def fill_answers(source_path, answers):
    insertions = answer_plan(answers)
    with open_docx(source_path) as package:
        document_xml = package.read(DOCUMENT_XML)
        namespaces = register_namespaces(document_xml)
        root = parse_document(document_xml)
        paragraphs = list(root.iter(W_P))
        parents = {child: parent for parent in root.iter() for child in parent}
        paragraph_texts = [paragraph_text(paragraph) for paragraph in paragraphs]
        last_inserted = {}
        report = []

        for insertion in insertions:
            question_number = str(insertion.get("question_number") or "").strip()
            answer = str(insertion.get("answer") or "").strip()
            anchor_id = str(insertion.get("anchor_id") or "").strip().upper()
            anchor_text = str(insertion.get("anchor") or "").strip()
            if len(answer) > MAX_ANSWER_LENGTH:
                raise ValueError("An answer is too long")

            anchor_index = None
            match = re.fullmatch(r"P(\d+)", anchor_id)
            if match and 1 <= int(match.group(1)) <= len(paragraphs):
                anchor_index = int(match.group(1)) - 1
                matched_by = "anchor_id"
            else:
                normalized = normalized_anchor(anchor_text)
                candidates = [
                    index
                    for index, text in enumerate(paragraph_texts)
                    if normalized and normalized_anchor(text) == normalized
                ]
                if not candidates and normalized:
                    candidates = [
                        index
                        for index, text in enumerate(paragraph_texts)
                        if normalized in normalized_anchor(text)
                        or normalized_anchor(text) in normalized
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
            paragraph = answer_paragraph(question_number, answer)
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

        remove_unbound_ignorable_prefixes(root, namespaces)
        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as target:
            for entry in package.infolist():
                target.writestr(
                    entry,
                    updated_xml
                    if entry.filename == DOCUMENT_XML
                    else package.read(entry.filename),
                )
    return output.getvalue(), report, len(insertions)


def main(inputs, context):
    source = inputs.get("source")
    if not isinstance(source, dict) or not source.get("path"):
        raise ValueError("source must be a file input")
    source_path = Path(str(source["path"]))
    if not source_path.is_file():
        raise ValueError("Source file is unavailable")

    content, report, requested_count = fill_answers(source_path, inputs.get("answers"))
    raw_name = str(inputs.get("output_name") or "英语试卷_已作答.docx").replace(
        "\\", "/"
    )
    output_name = PurePosixPath(raw_name).name or "英语试卷_已作答.docx"
    if not output_name.casefold().endswith(".docx"):
        output_name += ".docx"
    output_path = Path(context["output_dir"]) / output_name
    output_path.write_bytes(content)
    return {
        "file": context["output_file"](
            output_path,
            filename=output_name,
            content_type=DOCX_CONTENT_TYPE,
        ),
        "inserted_count": sum(item["status"] == "inserted" for item in report),
        "requested_count": requested_count,
        "insertions": report,
    }
