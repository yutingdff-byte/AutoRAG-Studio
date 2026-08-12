import agents.qc_agent as qc_agent


def _item(rag_id="RAG-1", **overrides):
    data = {
        "rag_id": rag_id,
        "model": "哈弗H6",
        "trim": "",
        "category": "配置",
        "knowledge_type": "static",
        "module": "基础参数",
        "intent": "参数",
        "questions": ["哈弗H6车长是多少？"],
        "answer": "哈弗H6车长为4703毫米。",
        "answer_type": "fact_answer",
        "need_confirm": "否",
        "review_type": "",
        "knowledge_status": "valid",
        "fact_refs": ["F001"],
    }
    data.update(overrides)
    return data


def test_qc_mode_full_uses_existing_full_path(monkeypatch):
    calls = []

    monkeypatch.setenv("QC_MODE", "full")
    monkeypatch.setattr(qc_agent, "call_llm", lambda prompt, content: calls.append(content) or '{"issues":[]}')

    result = qc_agent.quality_check({"rag_knowledge": [_item()]})

    assert calls
    assert result["summary"]["total_rag"] == 1


def test_rule_first_routes_only_high_risk_subset(monkeypatch):
    seen_payloads = []

    def fake_call_llm(prompt, content):
        seen_payloads.append(content)
        return '{"issues":[]}'

    monkeypatch.setenv("QC_MODE", "rule_first")
    monkeypatch.setattr(qc_agent, "call_llm", fake_call_llm)

    rag_data = {
        "rag_knowledge": [
            _item("RAG-LOW"),
            _item("RAG-PRICE", category="价格", questions=["哈弗H6多少钱？"], answer="9.89万元起。"),
        ]
    }
    result = qc_agent.quality_check(rag_data)

    assert len(seen_payloads) == 1
    assert '"RAG-PRICE"' in seen_payloads[0]
    assert '"RAG-LOW"' not in seen_payloads[0]
    assert result["rule_first_metrics"]["rule_passed"] == 1
    assert result["rule_first_metrics"]["llm_routed"] == 1


def test_rule_first_does_not_send_rule_issue_to_llm(monkeypatch):
    calls = []

    monkeypatch.setenv("QC_MODE", "rule_first")
    monkeypatch.setattr(qc_agent, "call_llm", lambda prompt, content: calls.append(content) or '{"issues":[]}')

    result = qc_agent.quality_check({"rag_knowledge": [_item(answer_type="need_confirm")]})

    assert calls == []
    assert any(issue["issue_type"] == "不可导出知识" for issue in result["issues"])
    assert result["rule_first_metrics"]["llm_routed"] == 0


def test_rule_first_llm_failure_is_not_silent_pass(monkeypatch):
    monkeypatch.setenv("QC_MODE", "rule_first")
    monkeypatch.setattr(qc_agent, "call_llm", lambda prompt, content: (_ for _ in ()).throw(RuntimeError("boom")))

    result = qc_agent.quality_check({
        "rag_knowledge": [
            _item("RAG-PRICE", category="价格", questions=["哈弗H6多少钱？"], answer="9.89万元起。")
        ]
    })

    assert any(issue["issue_type"] == "语义QC未完成" for issue in result["issues"])
    assert result["summary"]["error"] >= 1
