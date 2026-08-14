from facts.merge import merge_fact_chunk_results, merge_record_fact_chunk_results
from facts.models import FactChunk
from facts.models import FactChunkResult


def _result(index, facts):
    return FactChunkResult(
        chunk_index=index,
        input_chars=100,
        fact_count=len(facts),
        data={"facts": facts, "info_gaps": []},
    )


def test_merge_orders_by_chunk_index_and_renumbers():
    result = merge_fact_chunk_results([
        _result(1, [{"fact_id": "F001", "category": "金融", "content": "支持3年0息"}]),
        _result(0, [{"fact_id": "F001", "category": "价格", "content": "售价10万元"}]),
    ])

    assert [fact["content"] for fact in result["facts"]] == ["售价10万元", "支持3年0息"]
    assert [fact["fact_id"] for fact in result["facts"]] == ["F001", "F002"]


def test_exact_duplicate_keeps_first_only():
    result = merge_fact_chunk_results([
        _result(0, [{"fact_id": "A", "category": "价格", "content": "售价10万元"}]),
        _result(1, [{"fact_id": "B", "category": "价格", "content": " 售价 10 万元。"}]),
    ])

    assert len(result["facts"]) == 1
    assert result["chunk_report"]["exact_duplicates_removed"] == 1


def test_same_category_different_content_is_kept():
    result = merge_fact_chunk_results([
        _result(0, [{"fact_id": "A", "category": "价格", "content": "售价10万元"}]),
        _result(1, [{"fact_id": "B", "category": "价格", "content": "售价11万元"}]),
    ])

    assert len(result["facts"]) == 2


def test_same_content_different_category_is_kept():
    result = merge_fact_chunk_results([
        _result(0, [{"fact_id": "A", "category": "价格", "content": "最高10000元"}]),
        _result(1, [{"fact_id": "B", "category": "置换", "content": "最高10000元"}]),
    ])

    assert len(result["facts"]) == 2


def test_record_aware_keeps_same_content_across_different_records():
    chunks = [
        FactChunk(
            chunk_index=0,
            text="",
            input_chars=10,
            record_ids=["VR001"],
        ),
        FactChunk(
            chunk_index=1,
            text="",
            input_chars=10,
            record_ids=["VR002"],
        ),
    ]
    result = merge_record_fact_chunk_results(
        [
            _result(0, [{"fact_id": "A", "model": "GS8", "trim": "Max", "category": "价格", "content": "199800"}]),
            _result(1, [{"fact_id": "B", "model": "E8", "trim": "Max", "category": "价格", "content": "199800"}]),
        ],
        chunks,
    )

    assert len(result["facts"]) == 2
    assert result["chunk_report"]["exact_duplicates_removed"] == 0


def test_record_aware_dedups_exact_duplicate_in_same_record_and_strips_record_id():
    chunks = [
        FactChunk(
            chunk_index=0,
            text="",
            input_chars=10,
            record_ids=["VR001"],
        )
    ]
    result = merge_record_fact_chunk_results(
        [
            _result(
                0,
                [
                    {"fact_id": "A", "category": "价格", "content": "199800"},
                    {"fact_id": "B", "category": "价格", "content": "199800"},
                ],
            )
        ],
        chunks,
    )

    assert len(result["facts"]) == 1
    assert result["facts"][0]["fact_id"] == "F001"
    assert "record_id" not in result["facts"][0]
    assert "_record_id" not in result["facts"][0]
    assert result["chunk_report"]["exact_duplicates_removed"] == 1
