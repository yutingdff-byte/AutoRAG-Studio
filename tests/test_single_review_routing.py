from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from review.relation_grouper import group_review_required


def item(knowledge_id: str, model: str, question: str, category: str = "权益") -> KnowledgeItem:
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


def test_one_to_many_routes_to_complex_group_not_single_review():
    old = item("OLD", "H6L", "H6L有什么购车权益？", "购车权益")
    new_cash = item("NEW-CASH", "H6L", "H6L现金优惠多少？", "现金优惠")
    new_finance = item("NEW-FINANCE", "H6L", "H6L有什么金融政策？", "金融政策")

    grouped = group_review_required(
        run_result(
            [
                diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
                diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
                diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            ]
        )
    )

    assert len(grouped.groups) == 1
    assert grouped.single_items == []


def test_many_to_one_routes_to_complex_group_not_single_review():
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
    assert grouped.single_items == []


def test_single_review_requires_one_old_and_one_new():
    old = item("OLD", "H6L", "H6L价格是多少？", "价格")
    new = item("NEW", "H6L", "H6L PHEV价格是多少？", "价格")

    grouped = group_review_required(
        run_result(
            [
                diff("D1", ChangeType.REVIEW_REQUIRED, old=old, new=new, reason=ReviewReason.TRIM_CONFLICT),
            ]
        )
    )

    assert grouped.groups == []
    assert grouped.single_items == ["D1"]

