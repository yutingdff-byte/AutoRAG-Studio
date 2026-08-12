from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from merge.engine import merge_knowledge
from review.decisions import build_default_decisions
from review.relation_decisions import apply_relation_decisions, build_default_relation_decisions
from review.relation_grouper import group_review_required
from review.relation_models import RelationDecision, RelationDecisionType


def item(knowledge_id: str, question: str) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=f"answer {knowledge_id}",
        category="policy",
        model="H6L",
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


def relation_run():
    old = item("OLD", "H6L有什么购车权益？")
    new_cash = item("NEW-CASH", "H6L现在优惠多少？")
    new_finance = item("NEW-FINANCE", "H6L有什么金融政策？")
    return DiffRunResult(
        results=[
            diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
            diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
        ],
        detected_scope=DetectedUpdateScope(),
        total_count=3,
    )


def test_default_complex_relation_merge_adds_new_and_keeps_old():
    result = relation_run()
    groups = group_review_required(result).groups
    decisions = apply_relation_decisions(
        result,
        groups,
        build_default_relation_decisions(groups),
        build_default_decisions(result.results),
    )

    merged = merge_knowledge(result, decisions)
    ids = [item.knowledge_id for item in merged.final_items]

    assert ids == ["OLD", "NEW-CASH", "NEW-FINANCE"]
    assert merged.kept_old == 1


def test_replace_complex_relation_removes_old_only_when_confirmed():
    result = relation_run()
    groups = group_review_required(result).groups
    group = groups[0]
    decisions = apply_relation_decisions(
        result,
        groups,
        {
            group.group_id: RelationDecision(
                group_id=group.group_id,
                decision=RelationDecisionType.REPLACE_OLD_WITH_NEW,
                reviewed=True,
                metadata={"delete_confirmed": True},
            )
        },
        build_default_decisions(result.results),
    )

    merged = merge_knowledge(result, decisions)
    ids = [item.knowledge_id for item in merged.final_items]

    assert ids == ["NEW-CASH", "NEW-FINANCE"]
    assert merged.removed == 1

