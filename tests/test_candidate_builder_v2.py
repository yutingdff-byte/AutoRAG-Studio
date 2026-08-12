from diff.candidate_builder import build_candidates_for_new, build_index
from knowledge.models import KnowledgeItem


def item(knowledge_id: str, model: str, question: str, category: str, knowledge_type: str = "policy") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        model=model,
        question=question,
        answer="测试答案",
        category=category,
        knowledge_type=knowledge_type,
    )


def test_candidate_builder_recalls_model_alias_and_same_intent():
    old = item("OLD", "哈弗猛龙PLUS", "哈弗猛龙PLUS置换补贴", "权益政策")
    new = item("NEW", "猛龙PLUS", "猛龙PLUS置换补贴多少？", "置换补贴")
    index = build_index([old], [new])

    assert "OLD" in build_candidates_for_new(new, index)


def test_candidate_builder_does_not_recall_h6_for_h6l_by_short_prefix():
    old = item("OLD", "哈弗H6", "哈弗H6价格", "价格")
    new = item("NEW", "哈弗H6L", "哈弗H6L价格", "价格")
    index = build_index([old], [new])

    assert "OLD" not in build_candidates_for_new(new, index)
