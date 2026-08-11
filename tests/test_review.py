from diff.models import ChangeType, DiffResult, MatchMethod
from knowledge.models import KnowledgeItem
from review.decisions import build_default_decisions, decision_from_label
from review.models import ReviewDecisionType


def item(knowledge_id: str, answer: str = "答案") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question="这款车多少钱？",
        answer=answer,
        category="价格",
        model="测试车型",
        trim="全系",
        knowledge_type="price",
    )


def diff(change_type: ChangeType) -> DiffResult:
    return DiffResult(
        diff_id=f"DIFF-{change_type.value}",
        old_item=item("OLD", "旧答案") if change_type != ChangeType.ADDED else None,
        new_item=item("NEW", "新答案") if change_type != ChangeType.UNCHANGED else None,
        change_type=change_type,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=0.8,
        change_confidence=0.8,
        overall_confidence=0.8,
    )


def test_added_defaults_to_accept_new():
    result = diff(ChangeType.ADDED)
    decisions = build_default_decisions([result])

    decision = decisions[result.diff_id]
    assert decision.decision == ReviewDecisionType.ACCEPT_NEW
    assert decision.final_item == result.new_item
    assert not decision.reviewed


def test_added_can_be_rejected():
    result = diff(ChangeType.ADDED)
    decision = decision_from_label(result, "不加入")

    assert decision.decision == ReviewDecisionType.SKIP
    assert decision.final_item is None
    assert decision.reviewed


def test_updated_defaults_to_accept_new_and_can_keep_old():
    result = diff(ChangeType.UPDATED)
    default = build_default_decisions([result])[result.diff_id]
    keep_old = decision_from_label(result, "保留原答案")

    assert default.decision == ReviewDecisionType.ACCEPT_NEW
    assert default.final_item == result.new_item
    assert keep_old.decision == ReviewDecisionType.KEEP_OLD
    assert keep_old.final_item == result.old_item


def test_review_required_defaults_to_old_and_remove_requires_confirmation():
    result = diff(ChangeType.REVIEW_REQUIRED)
    default = build_default_decisions([result])[result.diff_id]
    remove = decision_from_label(result, "确认删除", delete_confirmed=True)

    assert default.decision == ReviewDecisionType.KEEP_OLD
    assert default.final_item == result.old_item
    assert remove.decision == ReviewDecisionType.REMOVE
    assert remove.metadata["delete_confirmed"]


def test_review_required_without_old_defaults_to_accept_new():
    result = DiffResult(
        diff_id="DIFF-ORPHAN",
        old_item=None,
        new_item=item("NEW", "新答案"),
        change_type=ChangeType.REVIEW_REQUIRED,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=0.2,
        change_confidence=0.2,
        overall_confidence=0.2,
    )

    decision = build_default_decisions([result])[result.diff_id]

    assert decision.decision == ReviewDecisionType.ACCEPT_NEW
    assert decision.final_item == result.new_item
    assert decision.metadata["routed_as"] == "ADDED_WITHOUT_OLD"
