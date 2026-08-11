from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from pages.update_page import _reviewable_results
from review.relation_grouper import group_review_required


def item(knowledge_id: str, model: str, question: str) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=f"answer {knowledge_id}",
        category="policy",
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


def test_complex_review_groups_remove_grouped_required_from_single_items():
    old = item("OLD", "H6L", "H6L有什么购车权益？")
    new_cash = item("NEW-CASH", "H6L", "H6L现金优惠多少？")
    new_finance = item("NEW-FINANCE", "H6L", "H6L有什么金融政策？")
    single_new = item("NEW-SINGLE", "H9", "H9资料范围怎么确认？")
    result = DiffRunResult(
        results=[
            diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
            diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            diff("D3", ChangeType.REVIEW_REQUIRED, new=single_new, reason=ReviewReason.NO_RELIABLE_MATCH),
        ],
        detected_scope=DetectedUpdateScope(),
        total_count=4,
    )

    grouping = group_review_required(result)
    single_required = [item for item in _reviewable_results(result, ChangeType.REVIEW_REQUIRED) if item.diff_id in grouping.single_items]

    assert len(grouping.groups) == 1
    assert grouping.single_items == ["D3"]
    assert [item.diff_id for item in single_required] == ["D3"]

