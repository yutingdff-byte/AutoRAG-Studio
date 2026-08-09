from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope, MatchMethod
from knowledge.models import KnowledgeItem
from merge.engine import merge_knowledge
from review.decisions import decision_from_label


def item(knowledge_id: str, question: str = "这款车多少钱？", answer: str = "答案") -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category="价格",
        model="测试车型",
        trim="全系",
        knowledge_type="price",
    )


def diff(diff_id: str, change_type: ChangeType, old=None, new=None) -> DiffResult:
    return DiffResult(
        diff_id=diff_id,
        old_item=old,
        new_item=new,
        change_type=change_type,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=0.8,
        change_confidence=0.8,
        overall_confidence=0.8,
    )


def run_result(results) -> DiffRunResult:
    return DiffRunResult(results=results, detected_scope=DetectedUpdateScope(), total_count=len(results))


def test_merge_unchanged_keeps_old():
    old = item("OLD")
    result = merge_knowledge(run_result([diff("D1", ChangeType.UNCHANGED, old=old)]))

    assert result.final_items == [old]
    assert result.kept_old == 1


def test_merge_added_accept_and_reject():
    new = item("NEW")
    added = diff("D1", ChangeType.ADDED, new=new)

    accepted = merge_knowledge(run_result([added]))
    rejected = merge_knowledge(run_result([added]), {"D1": decision_from_label(added, "不加入")})

    assert accepted.final_items == [new]
    assert accepted.added_accepted == 1
    assert rejected.final_items == []
    assert rejected.skipped == 1


def test_merge_updated_accepts_new_or_keeps_old():
    old = item("OLD", answer="旧")
    new = item("NEW", answer="新")
    updated = diff("D1", ChangeType.UPDATED, old=old, new=new)

    accepted = merge_knowledge(run_result([updated]))
    kept = merge_knowledge(run_result([updated]), {"D1": decision_from_label(updated, "保留原答案")})

    assert accepted.final_items == [new]
    assert accepted.updated_accepted == 1
    assert kept.final_items == [old]
    assert kept.kept_old == 1


def test_merge_review_required_defaults_old_and_remove_can_delete():
    old = item("OLD")
    review = diff("D1", ChangeType.REVIEW_REQUIRED, old=old)

    default = merge_knowledge(run_result([review]))
    removed = merge_knowledge(
        run_result([review]),
        {"D1": decision_from_label(review, "确认删除", delete_confirmed=True)},
    )

    assert default.final_items == [old]
    assert default.kept_old == 1
    assert removed.final_items == []
    assert removed.removed == 1


def test_merge_records_duplicate_warnings_without_dropping_items():
    first = item("OLD", question="质保怎么样？", answer="5年质保")
    second = item("NEW", question="质保怎么样？", answer="5年质保")
    result = merge_knowledge(
        run_result(
            [
                diff("D1", ChangeType.UNCHANGED, old=first),
                diff("D2", ChangeType.ADDED, new=second),
            ]
        )
    )

    assert result.final_items == [first, second]
    assert result.duplicate_warnings
    assert result.duplicate_warnings[0].warning_type == "duplicate_exact"

