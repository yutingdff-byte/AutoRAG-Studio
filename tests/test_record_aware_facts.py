import pytest

from facts.executor import execute_fact_chunks
from facts.models import FactChunkExecutionError
from facts.record_chunker import build_record_batch_manifest, build_record_fact_chunks, split_vehicle_records


def record(index: int, body: str = "字段: 值") -> str:
    return f"【车型记录{index}】\n车型: Model {index}\n{body}"


def test_splits_vehicle_records_without_dropping_context():
    material = "【文件来源:test.xlsx】\n【Sheet:车型】\n\n" + "\n\n".join(
        record(index)
        for index in range(1, 42)
    )

    context, records = split_vehicle_records(material)
    chunks = build_record_fact_chunks(material, batch_size=5, max_chars=12000)

    assert "test.xlsx" in context
    assert len(records) == 41
    assert [len(chunk.source_blocks) for chunk in chunks] == [5] * 8 + [1]
    assert chunks[0].record_ids == ["VR001", "VR002", "VR003", "VR004", "VR005"]
    assert chunks[-1].record_ids == ["VR041"]
    assert all("【车型记录" in block for chunk in chunks for block in chunk.source_blocks)


def test_starts_new_batch_when_char_limit_would_be_exceeded():
    material = "GLOBAL\n\n" + "\n\n".join(
        [
            record(1, "字段: " + "a" * 20),
            record(2, "字段: " + "b" * 20),
            record(3, "字段: " + "c" * 20),
        ]
    )

    chunks = build_record_fact_chunks(material, batch_size=5, max_chars=80)

    assert [len(chunk.source_blocks) for chunk in chunks] == [1, 1, 1]
    assert all("GLOBAL" in chunk.text for chunk in chunks)


def test_record_ids_are_stable_in_manifest():
    material = "GLOBAL\n\n" + "\n\n".join(record(index) for index in range(1, 7))

    chunks = build_record_fact_chunks(material, batch_size=3, max_chars=12000)
    manifest = build_record_batch_manifest(chunks)

    assert [chunk.record_ids for chunk in chunks] == [
        ["VR001", "VR002", "VR003"],
        ["VR004", "VR005", "VR006"],
    ]
    assert [item["record_ids"] for item in manifest] == [
        ["VR001", "VR002", "VR003"],
        ["VR004", "VR005", "VR006"],
    ]


def test_single_oversized_record_is_kept_whole():
    material = "GLOBAL\n\n" + record(1, "字段: " + "x" * 200)

    chunks = build_record_fact_chunks(material, batch_size=5, max_chars=80)

    assert len(chunks) == 1
    assert chunks[0].oversized is True
    assert chunks[0].record_ids == ["VR001"]
    assert chunks[0].source_blocks == [record(1, "字段: " + "x" * 200)]


def test_merge_order_and_fact_ids_are_stable_for_c2_completion_order():
    chunks = build_record_fact_chunks(
        "GLOBAL\n\n" + "\n\n".join([record(1), record(2), record(3)]),
        batch_size=1,
        max_chars=12000,
    )

    def extract_one(text):
        marker = "F002" if "Model 2" in text else "F001" if "Model 1" in text else "F003"
        return {
            "facts": [
                {
                    "fact_id": marker,
                    "category": "价格信息",
                    "content": marker,
                }
            ],
            "info_gaps": [],
        }

    result = execute_fact_chunks(chunks, extract_one, max_concurrency=2)

    assert [fact["fact_id"] for fact in result["facts"]] == ["F001", "F002", "F003"]
    assert [fact["content"] for fact in result["facts"]] == ["F001", "F002", "F003"]


def test_exact_dedup_and_renumbering():
    chunks = build_record_fact_chunks(
        "GLOBAL\n\n" + "\n\n".join([record(1), record(2)]),
        batch_size=1,
        max_chars=12000,
    )

    def extract_one(_text):
        return {
            "facts": [
                {
                    "fact_id": "X",
                    "category": "价格信息",
                    "content": "同一事实",
                }
            ],
            "info_gaps": [],
        }

    result = execute_fact_chunks(chunks, extract_one, max_concurrency=2)

    assert len(result["facts"]) == 1
    assert result["facts"][0]["fact_id"] == "F001"
    assert result["chunk_report"]["exact_duplicates_removed"] == 1


def test_failed_batch_fails_whole_execution_without_partial_result():
    chunks = build_record_fact_chunks(
        "GLOBAL\n\n" + "\n\n".join([record(1), record(2)]),
        batch_size=1,
        max_chars=12000,
    )

    def extract_one(text):
        if "Model 2" in text:
            return None
        return {
            "facts": [
                {
                    "fact_id": "F001",
                    "category": "价格信息",
                    "content": "ok",
                }
            ],
            "info_gaps": [],
        }

    with pytest.raises(FactChunkExecutionError):
        execute_fact_chunks(chunks, extract_one, max_concurrency=2)
