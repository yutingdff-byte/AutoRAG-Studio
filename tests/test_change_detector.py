from diff.change_detector import detect_change
from diff.models import ChangeType, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem


def item(knowledge_id, answer, question="阿维塔06多少钱？", category="价格"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category=category,
        model="阿维塔06",
        knowledge_type="price",
    )


def test_change_detector_treats_format_only_price_as_unchanged():
    result = detect_change(
        item("OLD", "249,800元"),
        item("NEW", "249800 元"),
        "DIFF-1",
        MatchMethod.NORMALIZED_QUESTION,
        0.95,
    )

    assert result.change_type == ChangeType.UNCHANGED


def test_change_detector_detects_price_change():
    result = detect_change(
        item("OLD", "官方指导价24.98万元起。"),
        item("NEW", "官方指导价23.98万元起。"),
        "DIFF-1",
        MatchMethod.NORMALIZED_QUESTION,
        0.95,
    )

    assert result.change_type == ChangeType.UPDATED
    assert "price" in result.changed_fields


def test_change_detector_marks_explicit_deprecation_for_review():
    result = detect_change(
        item("OLD", "购车可享受免费充电权益。", "免费充电权益还有吗？", "权益"),
        item("NEW", "自8月1日起，免费充电权益活动结束。", "免费充电权益还有吗？", "权益"),
        "DIFF-1",
        MatchMethod.STRUCTURED,
        0.86,
    )

    assert result.change_type == ChangeType.REVIEW_REQUIRED
    assert result.review_reason == ReviewReason.POSSIBLE_DEPRECATED
