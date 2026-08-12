from io import BytesIO
from pathlib import Path

from docx import Document

from knowledge.standard_word_restore import FORMAT_ID
from knowledge.word_format_detector import UNKNOWN_WORD_FORMAT, detect_word_format


def _docx_bytes(paragraphs: list[str]) -> BytesIO:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    buffer.name = "normal.docx"
    return buffer


def _download_docx_by_size(size: int) -> Path | None:
    downloads = Path.home() / "Downloads"
    for path in downloads.glob("*.docx"):
        if path.stat().st_size == size:
            return path
    return None


def test_system_standard_word_v1_detects_three_real_exports():
    expected = {
        54967: 832,
        5396: 46,
        12813: 258,
    }

    for size, record_count in expected.items():
        path = _download_docx_by_size(size)
        assert path is not None, f"missing real fixture with size {size}"

        result = detect_word_format(path)

        assert result.format_id == FORMAT_ID
        assert result.candidate_records == record_count
        assert result.parse_success_rate >= 0.8
        assert result.supported_schema_rate >= 0.8


def test_word_format_detector_does_not_misclassify_normal_word():
    file = _docx_bytes(
        [
            "这是普通说明文档。",
            "它可能包含问题两个字，但不是系统标准 JSON 导出。",
            "问题：这是什么？",
            "回答：只是普通段落。",
        ]
    )

    result = detect_word_format(file)

    assert result.format_id == UNKNOWN_WORD_FORMAT
    assert result.candidate_records < 3
