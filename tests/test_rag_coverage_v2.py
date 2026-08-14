from evaluation.rag_coverage_v2 import (
    VehicleRecord,
    build_coverage_report,
    contains_any,
    price_in_text,
    version_alias_match,
)


def _record(index=1, price="89800"):
    return VehicleRecord(
        record_index=index,
        series="传祺GS3 影速",
        version="2026款 劲享版",
        configuration_level="GS3-中配",
        brand="广汽传祺",
        source_price=price,
        dynamic_source={
            "cash": "限时现金礼20000元",
            "trade_in": "厂家置换补贴10000元",
            "finance": "金融礼6万2年0息",
            "benefit": "赠送保养服务",
            "activity": "8月试驾活动",
        },
    )


def _facts():
    return [
        {
            "fact_id": "F001",
            "model": "GS3 影速",
            "trim": "2026款 劲享版",
            "category": "配置信息",
            "content": "配置",
        },
        {
            "fact_id": "F002",
            "model": "GS3 影速",
            "trim": "2026款 劲享版",
            "category": "价格信息",
            "content": "厂商指导价89800元；车型名称：2026款 劲享版",
        },
        {
            "fact_id": "F003",
            "model": "GS3 影速",
            "trim": "2026款 劲享版",
            "category": "权益政策",
            "content": "限时现金礼20000元；厂家置换补贴10000元；金融礼6万2年0息；赠送保养服务；8月试驾活动",
        },
    ]


def test_price_normalization_matches_wan_units():
    assert price_in_text("劲享版指导价8.98万元", "89800")
    assert price_in_text("劲智版售价9.98万", "99800")


def test_version_alias_allows_short_trim_but_not_family_merge():
    assert version_alias_match("2026款 劲享版", "劲享版")
    assert not version_alias_match("M6", "M6 PRO")


def test_dynamic_answerability_uses_question_and_answer_content():
    text = "现在买有什么优惠？目前有2万元现金优惠，支持置换补贴，金融可享免息。"
    assert contains_any(text, ["现金优惠"])
    assert contains_any(text, ["置换"])
    assert contains_any(text, ["金融", "免息"])


def test_evaluator_v2_uses_fact_refs_and_separates_answerability_from_independent_faq():
    records = [_record()]
    rags = [
        {
            "rag_id": "RAG-001",
            "questions": ["这款车多少钱？"],
            "answer": "劲享版官方指导价8.98万元。",
            "category": "价格",
            "intent": "price",
            "fact_refs": ["F002"],
        },
        {
            "rag_id": "RAG-002",
            "questions": ["现在买有什么优惠？"],
            "answer": "目前有现金优惠，同时支持置换补贴，金融可享6万2年0息，并赠送保养服务，还有8月试驾活动。",
            "category": "权益政策",
            "intent": "benefit_overview",
            "fact_refs": ["F003"],
        },
    ]
    legacy = {
        "coverage": {
            "price": {"covered": 0, "source": 1},
            "dynamic": {
                "cash": {"covered": 0, "source": 1},
                "trade_in": {"covered": 0, "source": 1},
                "finance": {"covered": 0, "source": 1},
                "other_benefit": {"covered": 0, "source": 1},
                "activity": {"covered": 0, "source": 1},
            },
        }
    }

    report, price_rows, dynamic_rows = build_coverage_report(records, _facts(), rags, legacy)

    assert report["answerability_coverage"]["price"]["covered"] == 1
    assert report["answerability_coverage"]["cash"]["covered"] == 1
    assert report["answerability_coverage"]["trade_in"]["covered"] == 1
    assert report["answerability_coverage"]["finance"]["covered"] == 1
    assert report["answerability_coverage"]["benefit"]["covered"] == 1
    assert report["answerability_coverage"]["activity"]["covered"] == 1
    assert report["legacy_independent_faq_coverage"]["cash"]["covered"] == 0
    assert report["false_negative_fixed"]["price"] == 1
    assert price_rows[0]["reason"] == "TRUE_COVERED"
    assert {row["intent"]: row["reason"] for row in dynamic_rows if row["source_exist"]} == {
        "cash": "TRUE_COVERED",
        "trade_in": "TRUE_COVERED",
        "finance": "TRUE_COVERED",
        "benefit": "TRUE_COVERED",
        "activity": "TRUE_COVERED",
    }


def test_true_missing_is_reported_when_fact_exists_but_rag_does_not_answer():
    records = [_record()]
    report, _, _ = build_coverage_report(records, _facts(), [], {})

    assert report["answerability_coverage"]["price"]["covered"] == 0
    assert report["true_rag_missing_cases"]["price"] == 1
    assert report["true_rag_missing_cases"]["finance"] == 1
