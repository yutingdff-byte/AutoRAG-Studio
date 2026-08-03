import pytest

import main


def test_run_pipeline_stops_when_facts_are_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(main, "extract_facts", lambda material: None)
    monkeypatch.setattr(
        main,
        "generate_rag",
        lambda facts: pytest.fail("generate_rag should not run when facts are empty"),
    )

    with pytest.raises(main.PipelineStepError, match="Facts 提取失败"):
        main.run_pipeline("测试资料")


def test_run_pipeline_stops_when_rag_is_none(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        main,
        "extract_facts",
        lambda material: {"facts": [{"fact_id": "F001", "content": "事实"}]},
    )
    monkeypatch.setattr(main, "generate_rag", lambda facts: None)
    monkeypatch.setattr(
        main,
        "quality_check",
        lambda rag: pytest.fail("quality_check should not run when rag is empty"),
    )

    with pytest.raises(main.PipelineStepError, match="RAG 生成失败"):
        main.run_pipeline("测试资料")
