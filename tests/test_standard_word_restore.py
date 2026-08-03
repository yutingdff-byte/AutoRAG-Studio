from io import BytesIO
from pathlib import Path

from docx import Document

from knowledge.restore_manager import get_restore_cache_key, restore_file
from knowledge.standard_word_restore import (
    FORMAT_ID,
    PARSER_VERSION,
    restore_system_standard_word_v1,
)


def _download_docx_by_size(size: int) -> Path | None:
    downloads = Path.home() / "Downloads"
    for path in downloads.glob("*.docx"):
        if path.stat().st_size == size:
            return path
    return None


def _docx_bytes(paragraphs: list[str], name: str = "history.docx") -> BytesIO:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    buffer.name = name
    return buffer


def _assert_no_json_leak(items):
    assert items
    for item in items:
        assert item.question
        assert item.answer
        assert "{" not in item.question
        assert "}" not in item.question
        assert "{" not in item.answer
        assert "}" not in item.answer
        assert '"答案"' not in item.question
        assert '"问题"' not in item.answer
        assert not ("答案" in item.question and "是什么" in item.question)


def test_standard_restore_real_system_exports_counts_and_quality():
    expected = {
        54967: {"success": 832, "strict": 832, "repaired": 0, "qa": 832, "intent": 0},
        5396: {"success": 46, "strict": 46, "repaired": 0, "qa": 2, "intent": 44},
        12813: {"success": 258, "strict": 257, "repaired": 1, "qa": 258, "intent": 0},
    }

    for size, counts in expected.items():
        path = _download_docx_by_size(size)
        assert path is not None, f"missing real fixture with size {size}"

        result = restore_system_standard_word_v1(path)
        report = result.report

        assert report.format_id == FORMAT_ID
        assert report.parser_version == PARSER_VERSION
        assert report.success_count == counts["success"]
        assert report.strict_success_count == counts["strict"]
        assert report.repaired_success_count == counts["repaired"]
        assert report.failed_count == 0
        assert report.qa_v1_count == counts["qa"]
        assert report.intent_v1_count == counts["intent"]
        assert report.llm_calls == 0
        assert report.elapsed_seconds < 5
        assert len(result.items) == counts["success"]
        _assert_no_json_leak(result.items)


def test_standard_restore_schema_b_does_not_infer_model():
    path = _download_docx_by_size(5396)
    assert path is not None

    result = restore_system_standard_word_v1(path)
    schema_b_items = [
        item
        for item in result.items
        if item.metadata.get("schema_type") == "intent_v1"
    ]

    assert len(schema_b_items) == 44
    assert all(item.model is None for item in schema_b_items)
    assert all(item.metadata.get("intent_name") for item in schema_b_items)


def test_standard_restore_safe_repairs_only_supported_missing_opening_quote():
    file = _docx_bytes(
        [
            "{",
            '"车系": "哈弗猛龙26款燃油版",',
            '"问题": 哈弗猛龙26款燃油版的价格？",',
            '"答案": "哈弗猛龙26款燃油版低至15.69万起，还没有算上这个月的优惠呢。"',
            "}",
        ]
    )

    result = restore_system_standard_word_v1(file)

    assert result.report.success_count == 1
    assert result.report.repaired_success_count == 1
    assert result.report.failed_count == 0
    assert result.items[0].question == "哈弗猛龙26款燃油版的价格？"


def test_standard_restore_single_bad_record_does_not_fail_file():
    file = _docx_bytes(
        [
            "{",
            '"车系": "哈弗H6",',
            '"问题": "哈弗H6多少钱？",',
            '"答案": "价格以官方资料为准。"',
            "}",
            "{",
            '"车系": "哈弗H9",',
            '"问题": "这条缺答案字段"',
            "}",
        ]
    )

    result = restore_system_standard_word_v1(file)

    assert result.report.candidate_records == 2
    assert result.report.success_count == 1
    assert result.report.failed_count == 0
    assert result.report.skipped_count == 1
    assert len(result.report.failures) == 1
    assert result.items[0].model == "哈弗H6"


def test_restore_manager_standard_word_route_skips_agents(monkeypatch):
    path = _download_docx_by_size(12813)
    assert path is not None

    def fail_extract(material):
        raise AssertionError("standard Word restore must not call Fact Agent")

    def fail_rag(facts, progress_callback=None):
        raise AssertionError("standard Word restore must not call RAG Agent")

    monkeypatch.setattr("knowledge.word_restore.extract_material_facts", fail_extract)
    monkeypatch.setattr("knowledge.word_restore.generate_material_rag", fail_rag)

    result = restore_file(path)

    assert result.success
    assert len(result.items) == 258
    assert result.report["format_id"] == FORMAT_ID
    assert result.report["llm_calls"] == 0


def test_standard_restore_cache_key_uses_format_and_parser_version():
    path = _download_docx_by_size(12813)
    assert path is not None

    key = get_restore_cache_key(path)

    assert FORMAT_ID in key
    assert PARSER_VERSION in key
    assert "deep=" not in key
