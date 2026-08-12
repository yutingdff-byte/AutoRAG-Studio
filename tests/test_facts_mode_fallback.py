import agents.fact_agent as fact_agent


def test_facts_mode_single_uses_single_path(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "single")
    monkeypatch.setattr(
        fact_agent,
        "call_llm",
        lambda prompt, content: calls.append(content) or '{"facts":[{"fact_id":"F001","category":"配置","content":"单次事实"}]}',
    )

    result = fact_agent.extract_facts("完整文档")

    assert calls == ["完整文档"]
    assert result["facts"][0]["fact_id"] == "F001"


def test_unknown_facts_mode_falls_back_to_single(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "unknown")
    monkeypatch.setattr(
        fact_agent,
        "call_llm",
        lambda prompt, content: calls.append(content) or '{"facts":[{"fact_id":"F001","category":"配置","content":"单次事实"}]}',
    )

    fact_agent.extract_facts("完整文档")

    assert calls == ["完整文档"]


def test_facts_mode_chunked_uses_chunks_and_renumbers(monkeypatch):
    calls = []

    monkeypatch.setenv("FACTS_MODE", "chunked")
    monkeypatch.setenv("FACTS_CHUNK_TARGET_CHARS", "20")
    monkeypatch.setenv("FACTS_CHUNK_MAX_CHARS", "100")
    monkeypatch.setenv("FACTS_MAX_CONCURRENCY", "1")
    monkeypatch.setattr(
        fact_agent,
        "call_llm",
        lambda prompt, content: calls.append(content) or '{"facts":[{"fact_id":"F999","category":"配置","content":"%s"}]}' % content.splitlines()[-1],
    )

    result = fact_agent.extract_facts(
        "标题\n\n第一段内容包含一段较长政策说明。\n\n第二段内容也包含一段较长政策说明。"
    )

    assert len(calls) >= 2
    assert [fact["fact_id"] for fact in result["facts"]] == [
        f"F{index:03d}" for index in range(1, len(result["facts"]) + 1)
    ]
    assert "chunk_report" in result
