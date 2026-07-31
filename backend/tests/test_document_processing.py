import io
import zipfile
from xml.etree import ElementTree as ET

import pytest

import app.services.document_processing as document_processing
from app.services.document_processing import GeneratedFile, extract_docx, fill_docx_answers
from app.services.workflow_templates import build_english_exam_graph

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def minimal_docx() -> bytes:
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:mc="{MC_NS}" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" mc:Ignorable="w14"><w:body>
<w:p><w:r><w:t>Reading</w:t></w:r></w:p>
<w:p><w:r><w:t>1. Choose the correct word.</w:t></w:r></w:p>
<w:p><w:r><w:t>A. is  B. are</w:t></w:r></w:p>
<w:sectPr />
</w:body></w:document>""".encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types />")
        package.writestr("word/styles.xml", "<styles>preserved</styles>")
        package.writestr("word/document.xml", document)
    return output.getvalue()


@pytest.fixture
def source(monkeypatch):
    content = minimal_docx()
    monkeypatch.setattr(
        document_processing,
        "_source_file",
        lambda value: (content, "english-exam.docx"),
    )
    return {"id": "file-1"}


def test_extract_docx_adds_stable_paragraph_ids(source):
    result = extract_docx(source)

    assert result["paragraph_count"] == 3
    assert result["content"].splitlines() == [
        "[P0001] Reading",
        "[P0002] 1. Choose the correct word.",
        "[P0003] A. is  B. are",
    ]


def test_fill_docx_answers_preserves_package_and_insertion_order(source):
    result = fill_docx_answers(
        source,
        {
            "insertions": [
                {
                    "question_number": "Reading A",
                    "anchor_id": "P0003",
                    "anchor": "A. is  B. are",
                    "answer": "1. are",
                },
                {
                    "question_number": "Reading B",
                    "anchor_id": "P0003",
                    "anchor": "A. is  B. are",
                    "answer": "2. is",
                },
            ]
        },
    )

    assert result["inserted_count"] == 2
    assert isinstance(result["file"], GeneratedFile)
    with zipfile.ZipFile(io.BytesIO(result["file"].content)) as package:
        assert package.read("word/styles.xml") == b"<styles>preserved</styles>"
        root = ET.fromstring(package.read("word/document.xml"))
    text = ["".join(node.text or "" for node in paragraph.iter(f"{{{W_NS}}}t")) for paragraph in root.iter(f"{{{W_NS}}}p")]
    assert text[-2:] == ["Answer Reading A: 1. are", "Answer Reading B: 2. is"]
    colors = [item.get(f"{{{W_NS}}}val") for item in root.iter(f"{{{W_NS}}}color")]
    assert colors == ["FF0000", "FF0000", "FF0000", "FF0000"]
    assert root.get(f"{{{MC_NS}}}Ignorable") is None


def test_fill_docx_answers_falls_back_to_anchor_text(source):
    result = fill_docx_answers(
        source,
        {
            "insertions": [
                {
                    "question_number": "Reading",
                    "anchor_id": "P9999",
                    "anchor": "A. is B. are",
                    "answer": "1. are",
                }
            ]
        },
    )

    assert result["inserted_count"] == 1
    assert result["insertions"][0]["matched_by"] == "anchor"


def test_english_exam_template_is_a_valid_form_workflow():
    graph = build_english_exam_graph(
        provider_id="provider-1",
        model="gpt-test",
        vision_enabled=True,
    )

    start = graph["nodes"][0]
    assert start["data"]["config"]["input_fields"][0]["type"] == "file"
    assert [node["type"] for node in graph["nodes"]] == [
        "start",
        "document",
        "llm",
        "document",
        "end",
    ]
