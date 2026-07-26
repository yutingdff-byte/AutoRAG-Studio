from knowledge.models import KnowledgeItem


def test_knowledge_item_defaults_are_isolated():
    first = KnowledgeItem(
        knowledge_id="K001",
        question="多少钱？",
        answer="官方指导价以资料为准。",
        category="价格",
    )
    second = KnowledgeItem(
        knowledge_id="K002",
        question="续航怎么样？",
        answer="日常出行比较够用。",
        category="续航",
    )

    first.fact_refs.append("F001")
    first.metadata["source"] = "fixture"

    assert second.fact_refs == []
    assert second.metadata == {}
    assert first.need_confirm is False
