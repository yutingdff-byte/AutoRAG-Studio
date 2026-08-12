import threading
import time

import pytest

from agents import rag_agent
from agents.rag_agent import RagBatchExecutionError, execute_rag_batches, generate_rag, get_rag_max_concurrency


def fact(fact_id: str) -> dict:
    return {
        "fact_id": fact_id,
        "brand": "测试品牌",
        "model": "测试车型",
        "category": "配置",
        "content": f"{fact_id} 内容",
    }


def patch_simple_rag_pipeline(monkeypatch, batches):
    monkeypatch.setattr(rag_agent, "load_prompt", lambda: "prompt")
    monkeypatch.setattr(rag_agent, "group_facts", lambda facts: batches)
    monkeypatch.setattr(rag_agent, "merge_small_groups", lambda groups, max_size=30: groups)
    monkeypatch.setattr(rag_agent, "normalize_vehicle_fields", lambda item: None)
    monkeypatch.setattr(rag_agent, "build_fact_index", lambda facts: {item["fact_id"]: item for item in facts})
    monkeypatch.setattr(rag_agent, "normalize_rag_metadata", lambda result, fact_index: result)
    monkeypatch.setattr(rag_agent, "dedupe_rag_items", lambda items: items)
    monkeypatch.setattr(rag_agent, "ensure_model_price_overview", lambda result, facts: result)
    monkeypatch.setattr(rag_agent.rag_quality, "apply_export_quality_gate", lambda result: result)


def batch_result(batch, _system_prompt):
    fact_id = batch[0]["fact_id"]
    return {
        "rag_knowledge": [
            {
                "rag_id": "",
                "model": "测试车型",
                "question": f"{fact_id} 问题",
                "answer": f"{fact_id} 回答",
                "category": "配置",
                "knowledge_type": "static",
                "fact_refs": [fact_id],
            }
        ],
        "info_gaps": [],
        "confirm_items": [],
    }


def test_rag_concurrency_config_accepts_one_and_two(monkeypatch):
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "1")
    assert get_rag_max_concurrency() == 1

    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")
    assert get_rag_max_concurrency() == 2


def test_concurrency_one_preserves_serial_order(monkeypatch):
    batches = [[fact("F001")], [fact("F002")]]
    patch_simple_rag_pipeline(monkeypatch, batches)
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "1")
    monkeypatch.setattr(rag_agent, "generate_batch", batch_result)

    result = generate_rag({"facts": [fact("F001"), fact("F002")]})

    assert [item["rag_id"] for item in result["rag_knowledge"]] == ["RAG-001", "RAG-002"]
    assert [item["question"] for item in result["rag_knowledge"]] == ["F001 问题", "F002 问题"]


def test_concurrency_two_limits_running_batches(monkeypatch):
    batches = [[fact("F001")], [fact("F002")], [fact("F003")], [fact("F004")]]
    patch_simple_rag_pipeline(monkeypatch, batches)
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")
    active = 0
    max_active = 0
    lock = threading.Lock()

    def tracked_generate_batch(batch, system_prompt):
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        try:
            return batch_result(batch, system_prompt)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(rag_agent, "generate_batch", tracked_generate_batch)

    result = generate_rag({"facts": [fact(f"F00{i}") for i in range(1, 5)]})

    assert max_active == 2
    assert len(result["rag_knowledge"]) == 4


def test_out_of_order_completion_merges_by_batch_index(monkeypatch):
    batches = [[fact("F001")], [fact("F002")], [fact("F003")]]
    patch_simple_rag_pipeline(monkeypatch, batches)
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")

    def delayed_generate_batch(batch, system_prompt):
        if batch[0]["fact_id"] == "F001":
            time.sleep(0.08)
        return batch_result(batch, system_prompt)

    monkeypatch.setattr(rag_agent, "generate_batch", delayed_generate_batch)

    result = generate_rag({"facts": [fact("F001"), fact("F002"), fact("F003")]})

    assert [(item["rag_id"], item["question"]) for item in result["rag_knowledge"]] == [
        ("RAG-001", "F001 问题"),
        ("RAG-002", "F002 问题"),
        ("RAG-003", "F003 问题"),
    ]


def test_single_batch_works_with_concurrency_two(monkeypatch):
    batches = [[fact("F001")]]
    patch_simple_rag_pipeline(monkeypatch, batches)
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")
    monkeypatch.setattr(rag_agent, "generate_batch", batch_result)

    result = generate_rag({"facts": [fact("F001")]})

    assert len(result["rag_knowledge"]) == 1
    assert result["rag_knowledge"][0]["rag_id"] == "RAG-001"


def test_two_batches_can_run_concurrently(monkeypatch):
    batches = [[fact("F001")], [fact("F002")]]
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")
    started = []
    release = threading.Event()

    def blocking_generate_batch(batch, system_prompt):
        started.append(batch[0]["fact_id"])
        if len(started) == 2:
            release.set()
        assert release.wait(timeout=1)
        return batch_result(batch, system_prompt)

    monkeypatch.setattr(rag_agent, "generate_batch", blocking_generate_batch)

    results = execute_rag_batches(batches, "prompt", {}, max_concurrency=2)

    assert sorted(started) == ["F001", "F002"]
    assert [item["rag_knowledge"][0]["question"] for item in results] == ["F001 问题", "F002 问题"]


def test_batch_failure_raises_without_partial_success(monkeypatch):
    batches = [[fact("F001")], [fact("F002")]]
    patch_simple_rag_pipeline(monkeypatch, batches)
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")

    def failing_generate_batch(batch, system_prompt):
        if batch[0]["fact_id"] == "F002":
            return None
        return batch_result(batch, system_prompt)

    monkeypatch.setattr(rag_agent, "generate_batch", failing_generate_batch)

    with pytest.raises(RagBatchExecutionError):
        generate_rag({"facts": [fact("F001"), fact("F002")]})


def test_empty_input_returns_empty_rag(monkeypatch):
    patch_simple_rag_pipeline(monkeypatch, [])
    monkeypatch.setenv("RAG_MAX_CONCURRENCY", "2")
    monkeypatch.setattr(rag_agent, "generate_batch", batch_result)

    result = generate_rag({"facts": []})

    assert result["rag_knowledge"] == []
