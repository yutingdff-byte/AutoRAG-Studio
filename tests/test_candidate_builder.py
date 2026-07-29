from diff.candidate_builder import build_candidates_for_new, build_index
from knowledge.models import KnowledgeItem


def item(knowledge_id, model, question, category="续航"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer="续航表现不错。",
        category=category,
        model=model,
        knowledge_type="product",
    )


def test_candidate_builder_respects_model_isolation():
    old_items = [
        item("OLD-06", "阿维塔06", "续航是多少？"),
        item("OLD-07", "阿维塔07", "续航是多少？"),
    ]
    new_item = item("NEW-06", "阿维塔06", "续航是多少？")

    index = build_index(old_items, [new_item])

    assert build_candidates_for_new(new_item, index) == ["OLD-06"]
