from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from review.relation_grouper import group_review_required
from review.relation_models import RelationType


def item(knowledge_id: str, model: str, question: str, category: str = "policy") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=f"answer {knowledge_id}",
        category=category,
        model=model,
        knowledge_type="policy",
    )


def diff(diff_id: str, change_type: ChangeType, old=None, new=None, reason=None, candidates=None) -> DiffResult:
    return DiffResult(
        diff_id=diff_id,
        old_item=old,
        new_item=new,
        change_type=change_type,
        match_method=MatchMethod.AMBIGUOUS,
        match_confidence=0.5,
        change_confidence=0.5,
        overall_confidence=0.5,
        review_reason=reason,
        reason_code=reason.value if reason else "",
        metadata={"candidate_old_ids": candidates or []},
    )


def run_result(results) -> DiffRunResult:
    return DiffRunResult(results=results, detected_scope=DetectedUpdateScope(), total_count=len(results))


def test_one_old_to_many_new_items_becomes_one_relation_group():
    old = item("OLD-GENERAL", "H6L", "H6L有什么购车权益？", "购车权益")
    new_cash = item("NEW-CASH", "H6L", "H6L现在优惠多少？", "现金优惠")
    new_finance = item("NEW-FINANCE", "H6L", "H6L有什么金融政策？", "金融政策")

    grouped = group_review_required(
        run_result(
            [
                diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
                diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD-GENERAL"]),
                diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD-GENERAL"]),
            ]
        )
    )

    assert grouped.raw_review_count == 2
    assert len(grouped.groups) == 1
    group = grouped.groups[0]
    assert group.relation_type in {RelationType.ONE_TO_MANY, RelationType.GENERAL_TO_DETAIL}
    assert group.diff_ids == ["D1", "D2"]
    assert [item.knowledge_id for item in group.old_items] == ["OLD-GENERAL"]
    assert {item.knowledge_id for item in group.new_items} == {"NEW-CASH", "NEW-FINANCE"}


def test_many_old_to_one_new_becomes_one_relation_group():
    old_cash = item("OLD-CASH", "H6L", "H6L现金礼是什么？", "现金优惠")
    old_finance = item("OLD-FINANCE", "H6L", "H6L金融礼是什么？", "金融政策")
    new_general = item("NEW-GENERAL", "H6L", "H6L有什么购车权益？", "购车权益")

    grouped = group_review_required(
        run_result(
            [
                diff("OLD-CASH-DIFF", ChangeType.UNCHANGED, old=old_cash),
                diff("OLD-FINANCE-DIFF", ChangeType.UNCHANGED, old=old_finance),
                diff(
                    "D1",
                    ChangeType.REVIEW_REQUIRED,
                    new=new_general,
                    reason=ReviewReason.MANY_TO_ONE,
                    candidates=["OLD-CASH", "OLD-FINANCE"],
                ),
            ]
        )
    )

    assert len(grouped.groups) == 1
    group = grouped.groups[0]
    assert group.relation_type in {RelationType.MANY_TO_ONE, RelationType.DETAIL_TO_GENERAL}
    assert group.diff_ids == ["D1"]
    assert {item.knowledge_id for item in group.old_items} == {"OLD-CASH", "OLD-FINANCE"}
    assert [item.knowledge_id for item in group.new_items] == ["NEW-GENERAL"]


def test_unrelated_single_review_required_stays_single():
    new_item = item("NEW", "H6", "H6有什么新权益？")
    grouped = group_review_required(
        run_result(
            [
                diff("D1", ChangeType.REVIEW_REQUIRED, new=new_item, reason=ReviewReason.NO_RELIABLE_MATCH),
            ]
        )
    )

    assert grouped.groups == []
    assert grouped.single_items == ["D1"]

