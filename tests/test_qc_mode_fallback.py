import agents.qc_agent as qc_agent


def _item():
    return {
        "rag_id": "RAG-1",
        "model": "哈弗H6",
        "category": "配置",
        "knowledge_type": "static",
        "questions": ["哈弗H6车长是多少？"],
        "answer": "哈弗H6车长为4703毫米。",
        "answer_type": "fact_answer",
        "need_confirm": "否",
        "review_type": "",
        "knowledge_status": "valid",
        "fact_refs": ["F001"],
    }


def test_unknown_qc_mode_falls_back_to_full(monkeypatch):
    calls = []

    monkeypatch.setenv("QC_MODE", "unknown")
    monkeypatch.setattr(qc_agent, "call_llm", lambda prompt, content: calls.append(content) or '{"issues":[]}')

    result = qc_agent.quality_check({"rag_knowledge": [_item()]})

    assert calls
    assert "rule_first_metrics" not in result


def test_rule_first_all_low_risk_items_do_not_call_llm(monkeypatch):
    calls = []

    monkeypatch.setenv("QC_MODE", "rule_first")
    monkeypatch.setattr(qc_agent, "call_llm", lambda prompt, content: calls.append(content) or '{"issues":[]}')

    result = qc_agent.quality_check({"rag_knowledge": [_item()]})

    assert calls == []
    assert result["rule_first_metrics"]["llm_requests"] == 0
    assert result["rule_first_metrics"]["rule_passed"] == 1
