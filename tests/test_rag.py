import os

import pytest

from agents.fact_agent import extract_facts
from agents.rag_agent import generate_rag


MATERIAL = """
理想i6是一款中大型纯电SUV。
全国统一零售价249800元。
车长4950毫米，轴距3000毫米。
两驱版CLTC续航720公里，四驱版660公里。
支持5C超充，10分钟补能500公里。
搭载理想AD Max高级辅助驾驶系统。
"""


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="设置 RUN_LIVE_LLM_TESTS=1 后运行真实模型集成测试",
)
def test_live_fact_to_rag_pipeline():
    facts = extract_facts(MATERIAL)
    assert isinstance(facts, dict)
    assert facts.get("facts")

    rag = generate_rag(facts)
    assert isinstance(rag, dict)
    assert rag.get("rag_knowledge")
