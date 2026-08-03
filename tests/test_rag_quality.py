import sys
import types

from utils.rag_quality import (
    apply_export_quality_gate,
    is_exportable_rag,
    normalize_answer_for_tts,
    normalize_model_name
)


fake_llm_client = types.ModuleType(
    "agents.llm_client"
)
fake_llm_client.call_llm = lambda *args, **kwargs: ""
fake_llm_client.get_llm_timeout = lambda: None
sys.modules[
    "agents.llm_client"
] = fake_llm_client

from agents.qc_agent import should_report_static_dynamic_mismatch  # noqa: E402


def test_missing_rag_is_blocked_when_effective_topic_exists():

    rag_data = {
        "rag_knowledge": [
            {
                "rag_id": "RAG-OK",
                "brand": "阿维塔",
                "model": "阿维塔07",
                "trim": "全系",
                "category": "价格信息",
                "module": "价格",
                "knowledge_type": "dynamic",
                "answer_type": "fact_answer",
                "questions": [
                    "阿维塔07多少钱？"
                ],
                "answer": "阿维塔07官方指导价21.99万元起，具体成交价格以门店为准。",
                "fact_refs": [
                    "F001"
                ]
            },
            {
                "rag_id": "RAG-MISS",
                "brand": "阿维塔",
                "model": "阿维塔07",
                "trim": "全系",
                "category": "价格",
                "module": "价格",
                "knowledge_type": "static",
                "answer_type": "need_confirm",
                "questions": [
                    "阿维塔07多少钱？"
                ],
                "answer": "目前还没有阿维塔07的官方价格信息，建议您咨询当地门店获取最新报价。",
                "fact_refs": []
            }
        ]
    }

    apply_export_quality_gate(
        rag_data
    )

    blocked = rag_data[
        "rag_knowledge"
    ][1]

    assert is_exportable_rag(
        rag_data[
            "rag_knowledge"
        ][0]
    )

    assert not is_exportable_rag(
        blocked
    )

    assert blocked[
        "review_type"
    ] == "missing"

    assert "已有有效知识" in blocked[
        "export_block_reason"
    ]


def test_static_fixed_benefit_does_not_trigger_dynamic_mismatch():

    item = {
        "rag_id": "RAG-063",
        "knowledge_type": "static",
        "category": "权益政策",
        "module": "购车权益",
        "answer_type": "fact_answer",
        "questions": [
            "买车送哪些权益？"
        ],
        "answer": "购车赠送终身车联网基础流量不限，座舱娱乐流量每月10G，还赠送智能驾驶辅助系统进阶功能包。",
        "fact_refs": [
            "F120"
        ]
    }

    assert not should_report_static_dynamic_mismatch(
        item
    )


def test_real_price_conflict_is_reviewed_not_deleted():

    rag_data = {
        "rag_knowledge": [
            {
                "rag_id": "RAG-PRICE-1",
                "brand": "阿维塔",
                "model": "阿维塔07",
                "trim": "Ultra版",
                "category": "价格信息",
                "module": "价格",
                "knowledge_type": "dynamic",
                "answer_type": "fact_answer",
                "questions": [
                    "Ultra版多少钱？"
                ],
                "answer": "Ultra版官方指导价26.99万元。",
                "fact_refs": [
                    "F001"
                ]
            },
            {
                "rag_id": "RAG-PRICE-2",
                "brand": "阿维塔",
                "model": "阿维塔07",
                "trim": "Ultra版",
                "category": "价格信息",
                "module": "价格",
                "knowledge_type": "dynamic",
                "answer_type": "fact_answer",
                "questions": [
                    "Ultra版价格是多少？"
                ],
                "answer": "Ultra版官方指导价28.99万元。",
                "fact_refs": [
                    "F002"
                ]
            }
        ]
    }

    apply_export_quality_gate(
        rag_data
    )

    assert all(
        is_exportable_rag(
            item
        )
        for item in rag_data[
            "rag_knowledge"
        ]
    )

    conflicts = [
        item
        for item in rag_data.get(
            "review_items",
            []
        )
        if item.get(
            "review_type"
        ) == "conflict"
    ]

    assert len(
        conflicts
    ) == 1

    assert "26.99万元" in conflicts[0][
        "item"
    ]

    assert "28.99万元" in conflicts[0][
        "item"
    ]


def test_limited_time_benefit_still_triggers_dynamic_mismatch():

    item = {
        "rag_id": "RAG-LIMIT",
        "knowledge_type": "static",
        "category": "权益政策",
        "module": "购车权益",
        "answer_type": "fact_answer",
        "questions": [
            "限时权益？"
        ],
        "answer": "7月31日前下定赠送道路救援权益。",
        "fact_refs": [
            "F121"
        ]
    }

    assert should_report_static_dynamic_mismatch(
        item
    )


def test_tts_and_model_normalization():

    answer = normalize_answer_for_tts(
        "全国建议零售价 ¥289,900，30%-80%快充，10G，800V，ADS/OTA/LCC/NCA/APA/RPA/CDC，4K屏"
    )

    assert "28.99万元" in answer
    assert "百分之三十" in answer
    assert "10GB流量" in answer
    assert "800伏" in answer
    assert "智能驾驶辅助系统" in answer
    assert "在线升级" in answer
    assert "车道居中辅助" in answer
    assert "领航辅助驾驶" in answer
    assert "自动泊车" in answer
    assert "遥控泊车" in answer
    assert "可变阻尼悬架" in answer

    assert normalize_model_name(
        "新阿维塔12"
    ) == "阿维塔12"

    assert normalize_model_name(
        "阿维塔06T"
    ) == "阿维塔06T"
