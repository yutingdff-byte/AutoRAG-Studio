from pathlib import Path

import pytest

import main
from agents.fact_agent import apply_material_grounding_guard
from utils.rag_quality import is_exportable_rag


def test_material_grounding_blocks_unseen_versions_and_wrong_cargo_numbers():
    material = """
    哈弗H6经典版2026款
    建议零售价：9.99万元
    百变后备箱：560L-1485L可拓展
    """
    data = {
        "facts": [
            {
                "fact_id": "F001",
                "brand": "长城汽车",
                "model": "哈弗H6经典版",
                "trim": "经典版、豪华版、尊贵版",
                "category": "版本差异",
                "content": "配置对比表中列出经典版、豪华版、尊贵版三个版本",
            },
            {
                "fact_id": "F002",
                "brand": "长城汽车",
                "model": "哈弗H6经典版",
                "trim": "2026款",
                "category": "空间信息",
                "content": "后备箱容积586L，后排座椅放倒后可扩展至1450L",
            },
            {
                "fact_id": "F003",
                "brand": "长城汽车",
                "model": "哈弗H6经典版",
                "trim": "2026款",
                "category": "价格信息",
                "content": "建议零售价9.99万元",
            },
        ],
        "info_gaps": [],
    }

    guarded = apply_material_grounding_guard(data, material)

    assert [fact["content"] for fact in guarded["facts"]] == [
        "建议零售价9.99万元"
    ]
    assert guarded["facts"][0]["fact_id"] == "F001"
    assert guarded["material_grounding_removed"] == 2


def test_material_grounding_blocks_unsupported_connectivity_and_comfort_config():
    material = """
    HUAWEI HiCar
    ICCOA Carlink
    前排座椅加热
    双温区自动空调
    空调后排出风口
    """
    data = {
        "facts": [
            {
                "fact_id": "F001",
                "category": "舒适配置",
                "content": "前排座椅支持加热和通风功能，后排座椅也带加热功能",
            },
            {
                "fact_id": "F002",
                "category": "舒适配置",
                "content": "自动空调，后排独立空调",
            },
            {
                "fact_id": "F003",
                "category": "配置信息",
                "content": "大尺寸中控屏，支持CarPlay和Android Auto",
            },
            {
                "fact_id": "F004",
                "category": "配置信息",
                "content": "支持HUAWEI HiCar和ICCOA Carlink",
            },
        ],
        "info_gaps": [],
    }

    guarded = apply_material_grounding_guard(data, material)

    assert [fact["content"] for fact in guarded["facts"]] == [
        "支持HUAWEI HiCar和ICCOA Carlink"
    ]
    assert guarded["material_grounding_removed"] == 3


def test_material_grounding_blocks_mixed_mobile_interconnect_systems():
    material = """
    HUAWEI HiCar
    ICCOA Carlink
    CarPlay
    Android Auto
    """
    data = {
        "facts": [
            {
                "fact_id": "F001",
                "category": "智能座舱",
                "content": "支持HUAWEI HiCar、ICCOA Carlink、CarPlay、Android Auto等多种手机互联功能",
            }
        ],
        "info_gaps": [],
    }

    guarded = apply_material_grounding_guard(data, material)

    assert guarded["facts"] == []
    assert guarded["material_grounding_removed"] == 1
    assert "mobile interconnect" in guarded["material_grounding_removed_items"][0]["reason"]


def test_material_grounding_blocks_high_risk_uncertain_finance_and_aftersales():
    material = """
    金融政策：【图片内容无法确认】
    其他权益：【图片内容无法确认】
    """
    data = {
        "facts": [
            {
                "fact_id": "F001",
                "category": "金融政策",
                "content": "提供多种贷款方案，首付比例低至30%，年化利率低至4.5%，最长可贷5年",
            },
            {
                "fact_id": "F002",
                "category": "售后信息",
                "content": "整车质保3年或10万公里",
            },
        ],
        "info_gaps": [],
    }

    guarded = apply_material_grounding_guard(data, material)

    assert guarded["facts"] == []
    assert guarded["material_grounding_removed"] == 2


def test_high_risk_unconfirmed_rag_is_not_exportable():
    finance = {
        "model": "哈弗H6经典版",
        "trim": "需确认",
        "category": "金融",
        "questions": ["有什么金融方案？"],
        "answer": "首付比例低至百分之三十，年化利率低至百分之四点五。",
        "answer_type": "fact_answer",
        "review_type": "dynamic_notice",
    }
    brand = {
        "model": "新一代哈弗H6",
        "trim": "需确认",
        "category": "品牌",
        "questions": ["是什么品牌？"],
        "answer": "新一代哈弗H6是长城汽车旗下车型。",
        "answer_type": "fact_answer",
        "review_type": "无",
    }

    assert not is_exportable_rag(finance)
    assert is_exportable_rag(brand)


def test_run_pipeline_saves_material(monkeypatch, tmp_path):
    output_dir = tmp_path / "output" / "RUN"
    output_dir.mkdir(parents=True)

    monkeypatch.setattr(
        main,
        "create_run_context",
        lambda: {
            "run_id": "RUN",
            "output_dir": str(output_dir),
            "start_time": "2026-09-19T00:00:00",
        },
    )
    monkeypatch.setattr(
        main,
        "extract_facts",
        lambda material: {"facts": [{"fact_id": "F001", "content": "事实"}]},
    )
    monkeypatch.setattr(
        main,
        "generate_rag",
        lambda facts: {"rag_knowledge": [{"rag_id": "RAG-001", "answer": "回答"}]},
    )
    monkeypatch.setattr(main, "quality_check", lambda rag: {"result": "PASS"})
    monkeypatch.setattr(
        main,
        "generate_excel",
        lambda *args: {"static": str(output_dir / "static.xlsx"), "dynamic": str(output_dir / "dynamic.xlsx")},
    )

    result = main.run_pipeline("测试Material", source_files=["sample.zip"])

    assert (output_dir / "material.txt").read_text(encoding="utf-8") == "测试Material"
    assert result["run_info"]["output_files"]["material"] == str(output_dir / "material.txt")
