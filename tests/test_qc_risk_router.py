from qc.risk_router import route_qc_items


def _item(**overrides):
    data = {
        "rag_id": "RAG-1",
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


def test_low_risk_static_single_fact_can_rule_pass():
    result = route_qc_items([_item()])

    assert len(result.passed_items) == 1
    assert len(result.routed_items) == 0


def test_price_item_routes_to_llm():
    result = route_qc_items([
        _item(category="价格", questions=["哈弗H6多少钱？"], answer="9.89万元起。")
    ])

    assert len(result.routed_items) == 1
    assert "POLICY_OR_PRICE_SIGNAL" in result.decisions[0].reasons


def test_dynamic_finance_item_routes_to_llm():
    result = route_qc_items([
        _item(
            category="金融政策",
            knowledge_type="dynamic",
            questions=["哈弗H6有免息吗？"],
            answer="本月支持3年0息。",
        )
    ])

    assert len(result.routed_items) == 1
    assert "DYNAMIC_KNOWLEDGE" in result.decisions[0].reasons


def test_multi_fact_routes_to_llm():
    result = route_qc_items([_item(fact_refs=["F001", "F002"])])

    assert len(result.routed_items) == 1
    assert "MULTI_FACT" in result.decisions[0].reasons


def test_rule_issue_item_is_not_routed_to_llm():
    result = route_qc_items([_item()], {"RAG-1"})

    assert len(result.routed_items) == 0
    assert result.decisions[0].route == "rule_issue"
