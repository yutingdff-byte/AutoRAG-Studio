from diff.engine import compare
from diff.models import ChangeType, ReviewReason
from knowledge.models import KnowledgeItem


def item(knowledge_id: str, model: str, question: str, answer: str, category: str = "权益政策") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        model=model,
        question=question,
        answer=answer,
        category=category,
        knowledge_type="policy",
    )


def test_general_benefit_to_specific_new_requires_review():
    result = compare(
        [item("OLD", "哈弗大狗PLUS", "哈弗大狗PLUS有什么购车权益？", "包含现金、金融、置换等权益。")],
        [item("NEW", "哈弗大狗PLUS", "大狗PLUS燃油版分期有免息吗？", "支持24期0息。", "金融政策")],
    )

    review = result.results[0]
    assert review.change_type == ChangeType.REVIEW_REQUIRED
    assert review.review_reason == ReviewReason.ONE_TO_MANY


def test_specific_old_to_general_new_requires_review():
    result = compare(
        [
            item("OLD-CASH", "哈弗H6L", "哈弗H6L的现金礼是什么？", "现金优惠1.4万元。"),
            item("OLD-FIN", "哈弗H6L", "哈弗H6L的金融礼是什么？", "支持24期0息。", "金融政策"),
        ],
        [item("NEW", "哈弗H6L", "哈弗H6L现在有什么购车权益？", "有现金优惠和免息政策。")],
    )

    review = result.results[0]
    assert review.change_type == ChangeType.REVIEW_REQUIRED
    assert review.review_reason == ReviewReason.MANY_TO_ONE
