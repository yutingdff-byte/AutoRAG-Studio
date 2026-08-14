import pytest

import agents.fact_agent as fact_agent


def record(index: int, body: str = "字段: 值") -> str:
    return "銆愯溅鍨嬭褰晎" + str(index) + f"銆慭n车型: Model {index}\n{body}"


def matrix_material(count: int = 4) -> str:
    return "GLOBAL\n\n" + "\n\n".join(
        record(index)
        for index in range(1, count + 1)
    )


def test_auto_routes_matrix_material_to_record_aware(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "auto")
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_record_aware",
        lambda material, chunks=None: calls.append(("record", len(chunks or []))) or {"facts": []},
    )
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_single",
        lambda material: calls.append(("single", 0)) or {"facts": []},
    )

    fact_agent.extract_facts(matrix_material())

    assert calls == [("record", 2)]


def test_auto_routes_normal_word_material_to_single(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "auto")
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_record_aware",
        lambda material, chunks=None: calls.append(("record", 0)) or {"facts": []},
    )
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_single",
        lambda material: calls.append(("single", 0)) or {"facts": []},
    )

    fact_agent.extract_facts("普通 Word 资料\n价格政策\n配置说明")

    assert calls == [("single", 0)]


def test_auto_routes_row_oriented_excel_material_to_single(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "auto")
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_record_aware",
        lambda material, chunks=None: calls.append(("record", 0)) or {"facts": []},
    )
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_single",
        lambda material: calls.append(("single", 0)) or {"facts": []},
    )

    fact_agent.extract_facts("【Sheet:车型】\n车系 | 问题 | 答案\nGS8 | 价格 | 18.68万")

    assert calls == [("single", 0)]


def test_forced_single_uses_single_for_matrix(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "single")
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_single",
        lambda material: calls.append("single") or {"facts": []},
    )

    fact_agent.extract_facts(matrix_material())

    assert calls == ["single"]


def test_forced_record_aware_uses_record_aware(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "record_aware")
    monkeypatch.setattr(
        fact_agent,
        "_extract_facts_record_aware",
        lambda material, chunks=None: calls.append("record") or {"facts": []},
    )

    fact_agent.extract_facts(matrix_material())

    assert calls == ["record"]


def test_forced_record_aware_fails_fast_without_records(monkeypatch):
    monkeypatch.setenv("FACTS_MODE", "record_aware")

    with pytest.raises(RuntimeError, match="Record-aware Facts preparation failed"):
        fact_agent.extract_facts("普通文档没有车型记录块")


def test_record_aware_uses_batch_size_and_concurrency(monkeypatch):
    captured = {}

    monkeypatch.setenv("FACTS_RECORD_BATCH_SIZE", "3")
    monkeypatch.setenv("FACTS_RECORD_BATCH_MAX_CHARS", "12000")
    monkeypatch.setenv("FACTS_MAX_CONCURRENCY", "2")

    def fake_execute(chunks, extract_one, max_concurrency=2, merge_func=None):
        captured["record_ids"] = [chunk.record_ids for chunk in chunks]
        captured["max_concurrency"] = max_concurrency
        return {
            "facts": [{"fact_id": "F001", "category": "配置", "content": "ok"}],
            "info_gaps": [],
            "chunk_report": {"raw_facts": 1, "exact_duplicates_removed": 0, "final_facts": 1},
        }

    monkeypatch.setattr(fact_agent, "execute_fact_chunks", fake_execute)

    result = fact_agent._extract_facts_record_aware(matrix_material(7))

    assert captured["record_ids"] == [
        ["VR001", "VR002", "VR003"],
        ["VR004", "VR005", "VR006"],
        ["VR007"],
    ]
    assert captured["max_concurrency"] == 2
    assert result["chunk_report"]["record_batch_manifest"][0]["record_count"] == 3
