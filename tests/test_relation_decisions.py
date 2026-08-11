from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from review.decisions import build_default_decisions
from review.relation_decisions import apply_relation_decisions, build_default_relation_decisions
from review.relation_grouper import group_review_required
from review.relation_models import RelationDecision, RelationDecisionType
from review.models import ReviewDecisionType


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


def run_result(results) -> DiffRunResult:
    return DiffRunResult(results=results, detected_scope=DetectedUpdateScope(), total_count=len(results))


def relation_fixture():
    old = item("OLD", "H6L有什么购车权益？")
    new_cash = item("NEW-CASH", "H6L现在优惠多少？")
    new_finance = item("NEW-FINANCE", "H6L有什么金融政策？")
    result = run_result(
        [
            diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
            diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
        ]
    )
    groups = group_review_required(result).groups
    return result, groups


def test_default_relation_decision_accepts_new_and_keeps_old():
    result, groups = relation_fixture()
    base = build_default_decisions(result.results)
    relation_decisions = build_default_relation_decisions(groups)

    decisions = apply_relation_decisions(result, groups, relation_decisions, base)

    assert decisions["D1"].decision == ReviewDecisionType.ACCEPT_NEW
    assert decisions["D1"].metadata["keep_old_with_new"]
    assert decisions["D2"].decision == ReviewDecisionType.ACCEPT_NEW
    assert decisions["OLD-DIFF"].decision == ReviewDecisionType.KEEP_OLD


def test_replace_old_with_new_expands_to_remove_old_with_confirmation():
    result, groups = relation_fixture()
    group = groups[0]
    base = build_default_decisions(result.results)
    relation_decisions = {
        group.group_id: RelationDecision(
            group_id=group.group_id,
            decision=RelationDecisionType.REPLACE_OLD_WITH_NEW,
            reviewed=True,
            metadata={"delete_confirmed": True},
        )
    }

    decisions = apply_relation_decisions(result, groups, relation_decisions, base)

    assert decisions["D1"].decision == ReviewDecisionType.ACCEPT_NEW
    assert not decisions["D1"].metadata["keep_old_with_new"]
    assert decisions["OLD-DIFF"].decision == ReviewDecisionType.REMOVE
    assert decisions["OLD-DIFF"].metadata["delete_confirmed"]


def test_keep_old_only_skips_group_new_items():
    result, groups = relation_fixture()
    group = groups[0]
    base = build_default_decisions(result.results)
    relation_decisions = {
        group.group_id: RelationDecision(
            group_id=group.group_id,
            decision=RelationDecisionType.KEEP_OLD_ONLY,
            reviewed=True,
        )
    }

    decisions = apply_relation_decisions(result, groups, relation_decisions, base)

    assert decisions["D1"].decision == ReviewDecisionType.SKIP
    assert decisions["D2"].decision == ReviewDecisionType.SKIP
    assert decisions["OLD-DIFF"].decision == ReviewDecisionType.KEEP_OLD

