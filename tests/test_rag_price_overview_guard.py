from agents.rag_agent import (
    ensure_model_price_overview,
    guard_incomplete_model_price_overviews,
)
from utils.rag_quality import apply_export_quality_gate, is_exportable_rag


def _fact(fact_id, model, trim, price):
    return {
        "fact_id": fact_id,
        "brand": "长城汽车",
        "model": model,
        "trim": trim,
        "category": "价格信息",
        "content": f"建议零售价为{price}万元",
        "knowledge_type": "dynamic",
    }


def _price_rag(rag_id, model, trim, answer, refs):
    return {
        "rag_id": rag_id,
        "brand": "长城汽车",
        "model": model,
        "trim": trim,
        "category": "价格信息",
        "module": "价格",
        "questions": [f"{model}多少钱？"],
        "answer": answer,
        "answer_type": "fact_answer",
        "fact_refs": refs,
        "need_confirm": "否",
        "review_type": "dynamic_notice",
        "knowledge_type": "dynamic",
        "confidence": "高",
    }


def _complete_h6_facts():
    return [
        _fact("F029", "新一代哈弗H6", "1.5T Pro", "11.79"),
        _fact("F030", "新一代哈弗H6", "1.5T Max", "12.39"),
        _fact("F031", "新一代哈弗H6", "1.5T Ultra", "13.19"),
        _fact("F032", "新一代哈弗H6", "2.0T 两驱Max", "13.39"),
        _fact("F033", "新一代哈弗H6", "2.0T 四驱Max", "14.39"),
    ]


def test_incomplete_full_series_price_overview_is_blocked_and_replaced():
    facts = _complete_h6_facts()
    result = {
        "rag_knowledge": [
            _price_rag(
                "RAG-019",
                "新一代哈弗H6",
                "全系",
                "新一代哈弗H6的建议零售价区间为13.19万元-14.39万元。",
                ["F031", "F032", "F033"],
            )
        ]
    }

    result = guard_incomplete_model_price_overviews(result, facts)
    pre_gate_blocked = result["rag_knowledge"][0]
    assert not is_exportable_rag(pre_gate_blocked)
    assert "全系价格范围未覆盖" in pre_gate_blocked["export_block_reason"]

    result = ensure_model_price_overview(result, facts)
    result = apply_export_quality_gate(result)

    items = result["rag_knowledge"]
    blocked = [
        item
        for item in items
        if "13.19万元-14.39万元" in item.get("answer", "")
    ][0]
    inserted = [
        item
        for item in items
        if "11.79万元-14.39万元" in item.get("answer", "")
    ][0]

    assert not is_exportable_rag(blocked)
    assert is_exportable_rag(inserted)
    assert inserted["trim"] == "全系"
    assert set(inserted["fact_refs"]) == {"F029", "F030", "F031", "F032", "F033"}


def test_partial_version_price_rag_does_not_block_model_overview_insertion():
    facts = _complete_h6_facts()
    result = {
        "rag_knowledge": [
            _price_rag(
                "RAG-016",
                "新一代哈弗H6",
                "不同版本",
                "1.5T Pro建议零售价11.79万元，1.5T Max建议零售价12.39万元。",
                ["F029", "F030"],
            )
        ]
    }

    result = guard_incomplete_model_price_overviews(result, facts)
    result = ensure_model_price_overview(result, facts)

    assert any(
        item.get("trim") == "不同版本"
        and "11.79万元" in item.get("answer", "")
        and "12.39万元" in item.get("answer", "")
        for item in result["rag_knowledge"]
    )
    assert any(
        item.get("trim") == "全系"
        and "11.79万元-14.39万元" in item.get("answer", "")
        for item in result["rag_knowledge"]
    )


def test_explicit_full_series_price_range_is_not_blocked():
    facts = [
        {
            "fact_id": "F100",
            "brand": "长城汽车",
            "model": "新一代哈弗H6",
            "trim": "全系",
            "category": "价格信息",
            "content": "全系建议零售价区间为11.79万元-14.39万元",
            "knowledge_type": "dynamic",
        }
    ]
    result = {
        "rag_knowledge": [
            _price_rag(
                "RAG-001",
                "新一代哈弗H6",
                "全系",
                "新一代哈弗H6全系建议零售价区间为11.79万元-14.39万元。",
                ["F100"],
            )
        ]
    }

    result = guard_incomplete_model_price_overviews(result, facts)
    result = ensure_model_price_overview(result, facts)
    result = apply_export_quality_gate(result)

    assert len(result["rag_knowledge"]) == 1
    assert is_exportable_rag(result["rag_knowledge"][0])


def test_single_version_price_is_not_removed_by_range_guard():
    facts = [_fact("F001", "哈弗H6经典版", "2026款", "9.99")]
    result = {
        "rag_knowledge": [
            _price_rag(
                "RAG-003",
                "哈弗H6经典版",
                "2026款",
                "哈弗H6经典版2026款建议零售价为9.99万元。",
                ["F001"],
            )
        ]
    }

    result = guard_incomplete_model_price_overviews(result, facts)
    result = ensure_model_price_overview(result, facts)
    result = apply_export_quality_gate(result)

    assert any(
        item.get("trim") == "2026款" and is_exportable_rag(item)
        for item in result["rag_knowledge"]
    )


def test_price_overview_guard_does_not_cross_models():
    facts = [
        _fact("F001", "车型A", "低配", "10.00"),
        _fact("F002", "车型A", "高配", "15.00"),
        _fact("F101", "车型B", "Max", "13.00"),
        _fact("F102", "车型B", "Ultra", "18.00"),
    ]
    result = {
        "rag_knowledge": [
            _price_rag(
                "RAG-A",
                "车型A",
                "全系",
                "车型A全系建议零售价区间为10万元-15万元。",
                ["F001", "F002"],
            ),
            _price_rag(
                "RAG-B",
                "车型B",
                "全系",
                "车型B全系建议零售价区间为13万元-18万元。",
                ["F101", "F102"],
            ),
        ]
    }

    result = guard_incomplete_model_price_overviews(result, facts)
    result = apply_export_quality_gate(result)

    assert all(is_exportable_rag(item) for item in result["rag_knowledge"])
