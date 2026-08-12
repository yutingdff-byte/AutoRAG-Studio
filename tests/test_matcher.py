from diff.candidate_builder import build_index
from diff.matcher import match_new_item
from diff.models import MatchMethod
from knowledge.models import KnowledgeItem


def item(knowledge_id, model, question, category="价格", knowledge_type="price"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer="官方指导价24.98万元起。",
        category=category,
        model=model,
        knowledge_type=knowledge_type,
    )


def test_matcher_matches_normalized_same_question():
    old = item("OLD", "阿维塔06", "阿维塔06多少钱？")
    new = item("NEW", "阿维塔06", "阿维塔06 的价格是多少")
    index = build_index([old], [new])

    result = match_new_item(new, index)

    assert result.matched
    assert result.old_knowledge_id == "OLD"


def test_matcher_does_not_match_same_question_different_model():
    old = item("OLD", "阿维塔07", "续航是多少？", "续航", "product")
    new = item("NEW", "阿维塔06", "续航是多少？", "续航", "product")
    index = build_index([old], [new])

    result = match_new_item(new, index)

    assert not result.matched
    assert result.match_method == MatchMethod.UNMATCHED
