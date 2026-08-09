from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod, ReviewReason
from knowledge.models import KnowledgeItem
from pages.update_page import _diff_rows, _reviewable_results


def item(knowledge_id: str, question: str, answer: str, category: str = "价格") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category=category,
        model="测试车型",
        trim="全系",
        knowledge_type="price",
    )


def diff(change_type: ChangeType) -> DiffResult:
    old_item = item("OLD", "测试问题？", "旧答案") if change_type != ChangeType.ADDED else None
    new_item = item("NEW", "测试问题？", "新答案") if change_type != ChangeType.UNCHANGED else None
    return DiffResult(
        diff_id=f"DIFF-{change_type.value}",
        old_item=old_item,
        new_item=new_item,
        change_type=change_type,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=0.8,
        change_confidence=0.8,
        overall_confidence=0.8,
        review_reason=ReviewReason.NO_RELIABLE_MATCH if change_type == ChangeType.REVIEW_REQUIRED else None,
        reason_code="NO_RELIABLE_MATCH",
        change_summary="内部变化说明",
    )


def test_added_diff_tab_fields_are_user_facing():
    row = _diff_rows([diff(ChangeType.ADDED)], ChangeType.ADDED)[0]

    assert set(row) == {"车型", "问题", "新增答案", "分类"}
    assert "原回答" not in row
    assert "状态" not in row
    assert "变化原因" not in row
    assert "confidence" not in "".join(row)


def test_updated_diff_tab_fields_hide_algorithm_reason():
    row = _diff_rows([diff(ChangeType.UPDATED)], ChangeType.UPDATED)[0]

    assert set(row) == {"车型", "问题", "原答案", "新答案", "分类"}
    assert "变化原因" not in row


def test_unchanged_diff_tab_fields_are_current_answer_only():
    row = _diff_rows([diff(ChangeType.UNCHANGED)], ChangeType.UNCHANGED)[0]

    assert set(row) == {"车型", "问题", "当前答案", "分类"}
    assert "新答案" not in row
    assert "状态" not in row


def test_review_required_diff_tab_includes_business_reason_only():
    row = _diff_rows([diff(ChangeType.REVIEW_REQUIRED)], ChangeType.REVIEW_REQUIRED)[0]

    assert set(row) == {"车型", "问题", "原答案", "候选新答案", "需要确认的原因"}
    assert row["需要确认的原因"] == "未找到可靠对应知识"
    assert "NO_RELIABLE_MATCH" not in row["需要确认的原因"]


def test_review_tab_filtering_returns_only_requested_status():
    results = [
        diff(ChangeType.ADDED),
        diff(ChangeType.UPDATED),
        diff(ChangeType.REVIEW_REQUIRED),
        diff(ChangeType.UNCHANGED),
    ]
    run = DiffRunResult(results=results, detected_scope=DetectedUpdateScope(), total_count=4)

    assert [item.change_type for item in _reviewable_results(run, ChangeType.ADDED)] == [ChangeType.ADDED]
    assert [item.change_type for item in _reviewable_results(run, ChangeType.UPDATED)] == [ChangeType.UPDATED]
    assert [item.change_type for item in _reviewable_results(run, ChangeType.REVIEW_REQUIRED)] == [
        ChangeType.REVIEW_REQUIRED
    ]
    assert ChangeType.UNCHANGED not in [item.change_type for item in _reviewable_results(run)]

