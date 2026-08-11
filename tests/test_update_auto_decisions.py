from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from merge.engine import merge_knowledge
from review.decisions import build_default_decisions
from review.relation_decisions import apply_relation_decisions, build_default_relation_decisions
from review.relation_grouper import group_review_required


def item(knowledge_id: str, question: str, answer: str, category: str = "价格") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category=category,
        model="测试车型",
        trim="全系",
        knowledge_type="price" if category == "价格" else "policy",
    )


def diff(diff_id: str, change_type: ChangeType, old=None, new=None, reason=None, candidates=None) -> DiffResult:
    return DiffResult(
        diff_id=diff_id,
        old_item=old,
        new_item=new,
        change_type=change_type,
        match_method=MatchMethod.STRUCTURED,
        match_confidence=0.9,
        change_confidence=0.9,
        overall_confidence=0.9,
        review_reason=reason,
        reason_code=reason.value if reason else "",
        metadata={"candidate_old_ids": candidates or []},
    )


def run_result(results) -> DiffRunResult:
    return DiffRunResult(results=results, detected_scope=DetectedUpdateScope(), total_count=len(results))


def test_added_is_accepted_automatically():
    new = item("NEW", "测试车型有什么权益？", "新增权益。", "权益")
    result = run_result([diff("D1", ChangeType.ADDED, new=new)])

    merged = merge_knowledge(result, build_default_decisions(result.results))

    assert [item.knowledge_id for item in merged.final_items] == ["NEW"]
    assert merged.added_accepted == 1


def test_updated_replaces_old_with_new_automatically():
    old = item("OLD", "测试车型多少钱？", "29.98万元。")
    new = item("NEW", "测试车型多少钱？", "27.98万元。")
    result = run_result([diff("D1", ChangeType.UPDATED, old=old, new=new)])

    merged = merge_knowledge(result, build_default_decisions(result.results))

    assert [item.knowledge_id for item in merged.final_items] == ["NEW"]
    assert merged.updated_accepted == 1


def test_orphan_review_required_is_routed_to_add_new():
    new = item("NEW", "测试车型有什么新增服务？", "新增服务。", "权益")
    result = run_result([diff("D1", ChangeType.REVIEW_REQUIRED, new=new, reason=ReviewReason.NO_RELIABLE_MATCH)])

    grouping = group_review_required(result)
    merged = merge_knowledge(result, build_default_decisions(result.results))

    assert grouping.groups == []
    assert grouping.single_items == []
    assert [item.knowledge_id for item in merged.final_items] == ["NEW"]


def test_complex_relation_default_adds_new_and_keeps_old():
    old = item("OLD", "测试车型有什么购车权益？", "综合权益。", "购车权益")
    new_cash = item("NEW-CASH", "测试车型现在优惠多少？", "现金优惠。", "现金优惠")
    new_finance = item("NEW-FINANCE", "测试车型有什么金融政策？", "金融政策。", "金融政策")
    result = run_result(
        [
            diff("OLD-DIFF", ChangeType.UNCHANGED, old=old),
            diff("D1", ChangeType.REVIEW_REQUIRED, new=new_cash, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
            diff("D2", ChangeType.REVIEW_REQUIRED, new=new_finance, reason=ReviewReason.ONE_TO_MANY, candidates=["OLD"]),
        ]
    )
    grouping = group_review_required(result)
    decisions = apply_relation_decisions(
        result,
        grouping.groups,
        build_default_relation_decisions(grouping.groups),
        build_default_decisions(result.results),
    )

    merged = merge_knowledge(result, decisions)

    assert [item.knowledge_id for item in merged.final_items] == ["OLD", "NEW-CASH", "NEW-FINANCE"]


def test_complex_relation_does_not_override_clear_updated_decision():
    old = item("OLD", "测试车型置换补贴多少？", "旧补贴。", "置换补贴")
    updated_new = item("UPDATED-NEW", "测试车型置换补贴多少？", "新补贴。", "置换补贴")
    relation_new = item("REL-NEW", "测试车型有什么购车权益？", "综合权益。", "购车权益")
    result = run_result(
        [
            diff("OLD-DIFF", ChangeType.UPDATED, old=old, new=updated_new),
            diff("D1", ChangeType.REVIEW_REQUIRED, new=relation_new, reason=ReviewReason.MANY_TO_ONE, candidates=["OLD"]),
        ]
    )
    grouping = group_review_required(result)
    decisions = apply_relation_decisions(
        result,
        grouping.groups,
        build_default_relation_decisions(grouping.groups),
        build_default_decisions(result.results),
    )

    merged = merge_knowledge(result, decisions)

    assert "UPDATED-NEW" in [item.knowledge_id for item in merged.final_items]
    assert "OLD" not in [item.knowledge_id for item in merged.final_items]
