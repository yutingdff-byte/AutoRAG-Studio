from diff.engine import compare
from diff.models import ChangeType, ReviewReason
from knowledge.models import KnowledgeItem


def item(knowledge_id, model, question, answer, category="价格", knowledge_type="price"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category=category,
        model=model,
        trim="全系",
        knowledge_type=knowledge_type,
        source_files=["fixture.xlsx"],
    )


def test_engine_marks_same_answer_as_unchanged():
    result = compare(
        [item("OLD", "阿维塔06", "阿维塔06多少钱？", "249,800元")],
        [item("NEW", "阿维塔06", "阿维塔06官方指导价多少", "249800 元")],
    )

    assert result.unchanged_count == 1
    assert result.results[0].change_type == ChangeType.UNCHANGED


def test_engine_detects_price_update():
    result = compare(
        [item("OLD", "阿维塔06", "阿维塔06多少钱？", "24.98万元起。")],
        [item("NEW", "阿维塔06", "阿维塔06多少钱？", "23.98万元起。")],
    )

    assert result.updated_count == 1


def test_engine_detects_added_knowledge():
    result = compare(
        [],
        [item("NEW", "阿维塔06", "阿维塔06多少钱？", "23.98万元起。")],
    )

    assert result.added_count == 1


def test_engine_keeps_old_out_of_scope_unchanged():
    result = compare(
        [
            item("OLD-CONFIG", "阿维塔06", "阿维塔06空间怎么样？", "空间比较宽裕。", "空间", "product"),
        ],
        [
            item("NEW-PRICE", "阿维塔06", "阿维塔06多少钱？", "23.98万元起。", "价格", "price"),
        ],
    )

    old_result = next(item for item in result.results if item.old_item and item.old_item.knowledge_id == "OLD-CONFIG")
    assert old_result.change_type == ChangeType.UNCHANGED
    assert old_result.metadata["untouched_by_current_update"]


def test_engine_marks_old_in_scope_unmatched_for_review():
    result = compare(
        [
            item("OLD-PRICE", "阿维塔06", "阿维塔06多少钱？", "24.98万元起。", "价格", "price"),
        ],
        [
            item("NEW-PRICE", "阿维塔06", "阿维塔06金融政策？", "支持三年免息。", "金融", "finance"),
        ],
    )

    old_result = next(item for item in result.results if item.old_item and item.old_item.knowledge_id == "OLD-PRICE")
    assert old_result.change_type == ChangeType.UNCHANGED


def test_engine_marks_possible_deprecated_for_review():
    result = compare(
        [
            item("OLD", "阿维塔06", "免费充电权益还有吗？", "购车可享受免费充电权益。", "权益", "policy"),
        ],
        [
            item("NEW", "阿维塔06", "免费充电权益还有吗？", "自8月1日起，免费充电权益活动结束。", "权益", "policy"),
        ],
    )

    assert result.review_required_count == 1
    assert result.results[0].review_reason == ReviewReason.POSSIBLE_DEPRECATED


def test_engine_does_not_match_different_models():
    result = compare(
        [item("OLD", "阿维塔07", "续航是多少？", "续航700公里。", "续航", "product")],
        [item("NEW", "阿维塔06", "续航是多少？", "续航700公里。", "续航", "product")],
    )

    assert result.added_count == 1
