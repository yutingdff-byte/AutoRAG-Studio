from qc.rule_engine import run_rule_qc


def _item(**overrides):
    data = {
        "rag_id": "RAG-1",
        "questions": ["车长是多少？"],
        "answer": "车长为4950毫米。",
        "answer_type": "fact_answer",
        "need_confirm": "否",
        "review_type": "",
        "knowledge_status": "valid",
        "fact_refs": ["F001"],
    }
    data.update(overrides)
    return data


def test_rule_engine_flags_empty_answer():
    result = run_rule_qc([_item(answer="")])

    assert any(issue["issue_type"] == "回答为空" for issue in result.issues)
    assert "RAG-1" in result.issue_item_ids


def test_rule_engine_flags_need_confirm_as_non_exportable():
    result = run_rule_qc([_item(answer_type="need_confirm")])

    assert any(issue["issue_type"] == "不可导出知识" for issue in result.issues)
    assert "RAG-1" in result.issue_item_ids


def test_rule_engine_flags_missing_answer_phrase():
    result = run_rule_qc([_item(answer="资料未提供，建议咨询门店。")])

    assert any(issue["issue_type"] == "不可导出知识" for issue in result.issues)


def test_rule_engine_flags_malformed_fact_refs():
    result = run_rule_qc([_item(fact_refs="F001")])

    assert any(issue["issue_type"] == "Fact引用异常" for issue in result.issues)


def test_rule_engine_does_not_flag_normal_static_item():
    result = run_rule_qc([_item()])

    assert result.issues == []
    assert result.issue_item_ids == set()
