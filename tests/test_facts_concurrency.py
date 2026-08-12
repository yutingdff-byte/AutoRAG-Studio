import threading
import time

import pytest

from facts.executor import execute_fact_chunks
from facts.models import FactChunk, FactChunkExecutionError


def _chunk(index):
    return FactChunk(chunk_index=index, text=f"chunk-{index}", input_chars=10)


def test_concurrency_one_runs_all_chunks():
    result = execute_fact_chunks(
        [_chunk(0), _chunk(1)],
        lambda text: {"facts": [{"fact_id": "F001", "category": "测试", "content": text}]},
        max_concurrency=1,
    )

    assert [fact["content"] for fact in result["facts"]] == ["chunk-0", "chunk-1"]
    assert result["chunk_report"]["max_concurrency"] == 1


def test_concurrency_two_limits_parallelism():
    active = 0
    max_seen = 0
    lock = threading.Lock()

    def extract(text):
        nonlocal active, max_seen
        with lock:
            active += 1
            max_seen = max(max_seen, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"facts": [{"fact_id": "F001", "category": "测试", "content": text}]}

    execute_fact_chunks([_chunk(i) for i in range(4)], extract, max_concurrency=2)

    assert max_seen <= 2
    assert max_seen == 2


def test_out_of_order_completion_still_merges_by_chunk_index():
    def extract(text):
        if text == "chunk-0":
            time.sleep(0.05)
        return {"facts": [{"fact_id": "F001", "category": "测试", "content": text}]}

    result = execute_fact_chunks([_chunk(0), _chunk(1)], extract, max_concurrency=2)

    assert [fact["content"] for fact in result["facts"]] == ["chunk-0", "chunk-1"]


def test_single_chunk_works():
    result = execute_fact_chunks(
        [_chunk(0)],
        lambda text: {"facts": [{"fact_id": "F001", "category": "测试", "content": text}]},
        max_concurrency=2,
    )

    assert len(result["facts"]) == 1
    assert result["chunk_report"]["max_concurrency"] == 1


def test_chunk_failure_fails_whole_extraction():
    def extract(text):
        if text == "chunk-1":
            raise RuntimeError("boom")
        return {"facts": [{"fact_id": "F001", "category": "测试", "content": text}]}

    with pytest.raises(FactChunkExecutionError):
        execute_fact_chunks([_chunk(0), _chunk(1)], extract, max_concurrency=2)


def test_empty_chunks_return_empty_facts():
    result = execute_fact_chunks([], lambda text: {"facts": []}, max_concurrency=2)

    assert result["facts"] == []
    assert result["chunk_report"]["request_count"] == 0
