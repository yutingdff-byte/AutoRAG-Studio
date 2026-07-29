"""Rule-based Diff Engine entrypoint."""

from __future__ import annotations

from time import perf_counter

from diff import confidence
from diff.candidate_builder import build_index
from diff.change_detector import has_deprecation_evidence, has_required_fields, detect_change
from diff.matcher import match_new_item
from diff.models import ChangeType, DiffResult, DiffRunResult, MatchMethod, ReviewReason
from diff.reasons import added_summary, reason_text
from diff.scope_detector import detect_update_scope, item_in_scope
from knowledge.models import KnowledgeItem


def _diff_id(index: int) -> str:
    return f"DIFF-{index:04d}"


def _added_result(item: KnowledgeItem, index: int) -> DiffResult:
    return DiffResult(
        diff_id=_diff_id(index),
        old_item=None,
        new_item=item,
        change_type=ChangeType.ADDED,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=confidence.NO_MATCH,
        change_confidence=confidence.UPDATED,
        overall_confidence=confidence.UPDATED,
        reason_code="NEW_KNOWLEDGE",
        reason_text=reason_text("NEW_KNOWLEDGE"),
        changed_fields=["new_item"],
        change_summary=added_summary(item.category),
        needs_review=False,
        review_priority="P3",
    )


def _review_result(
    old_item: KnowledgeItem | None,
    new_item: KnowledgeItem | None,
    index: int,
    review_reason: ReviewReason,
    reason_code: str,
    summary: str,
    priority: str = "P2",
    metadata: dict | None = None,
) -> DiffResult:
    return DiffResult(
        diff_id=_diff_id(index),
        old_item=old_item,
        new_item=new_item,
        change_type=ChangeType.REVIEW_REQUIRED,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=confidence.REVIEW_CANDIDATE,
        change_confidence=confidence.REVIEW_REQUIRED,
        overall_confidence=confidence.combine(confidence.REVIEW_CANDIDATE, confidence.REVIEW_REQUIRED),
        reason_code=reason_code,
        reason_text=reason_text(reason_code),
        review_reason=review_reason,
        changed_fields=[],
        change_summary=summary,
        needs_review=True,
        review_priority=priority,
        metadata=metadata or {},
    )


def _unchanged_old_result(old_item: KnowledgeItem, index: int) -> DiffResult:
    return DiffResult(
        diff_id=_diff_id(index),
        old_item=old_item,
        new_item=None,
        change_type=ChangeType.UNCHANGED,
        match_method=MatchMethod.UNMATCHED,
        match_confidence=confidence.NO_MATCH,
        change_confidence=confidence.UNCHANGED,
        overall_confidence=confidence.UNCHANGED,
        reason_code="OLD_NOT_IN_SCOPE",
        reason_text=reason_text("OLD_NOT_IN_SCOPE"),
        change_summary="本轮未明显涉及，继续保留。",
        needs_review=False,
        review_priority="P3",
        metadata={"untouched_by_current_update": True},
    )


def _missing_required_result(item: KnowledgeItem, index: int, is_new: bool) -> DiffResult:
    return _review_result(
        old_item=None if is_new else item,
        new_item=item if is_new else None,
        index=index,
        review_reason=ReviewReason.MISSING_REQUIRED_FIELD,
        reason_code="MISSING_REQUIRED_FIELD",
        summary="知识缺少问题或回答，无法可靠比较。",
        priority="P1",
    )


def _summarize(results: list[DiffResult], scope, started_at: float) -> DiffRunResult:
    total = len(results)
    return DiffRunResult(
        results=results,
        detected_scope=scope,
        total_count=total,
        added_count=sum(1 for result in results if result.change_type == ChangeType.ADDED),
        updated_count=sum(1 for result in results if result.change_type == ChangeType.UPDATED),
        unchanged_count=sum(1 for result in results if result.change_type == ChangeType.UNCHANGED),
        review_required_count=sum(1 for result in results if result.change_type == ChangeType.REVIEW_REQUIRED),
        timings={"total_seconds": round(perf_counter() - started_at, 4)},
        metadata={"engine": "rule-based"},
    )


def compare(old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> DiffRunResult:
    """Compare old and new KnowledgeItem lists with conservative rule matching."""

    started_at = perf_counter()
    old_items = old_items or []
    new_items = new_items or []
    scope = detect_update_scope(new_items, old_items)
    results: list[DiffResult] = []
    result_index = 1

    if not old_items and not new_items:
        return _summarize(results, scope, started_at)

    if old_items and not new_items:
        return _summarize(
            [
                _review_result(
                    old_item=None,
                    new_item=None,
                    index=1,
                    review_reason=ReviewReason.NO_RELIABLE_MATCH,
                    reason_code="NO_NEW_KNOWLEDGE",
                    summary="本轮新增资料未生成有效知识，无法执行可靠差异分析。",
                    priority="P1",
                )
            ],
            scope,
            started_at,
        )

    if not old_items and new_items:
        for item in new_items:
            results.append(_added_result(item, result_index))
            result_index += 1
        return _summarize(results, scope, started_at)

    index = build_index(old_items, new_items)
    used_old_ids: set[str] = set()
    used_new_ids: set[str] = set()

    for new_item in new_items:
        if not has_required_fields(new_item):
            results.append(_missing_required_result(new_item, result_index, is_new=True))
            result_index += 1
            used_new_ids.add(new_item.knowledge_id)
            continue

        match = match_new_item(new_item, index, used_old_ids)

        if match.matched and match.old_knowledge_id:
            old_item = index.old_normalized[match.old_knowledge_id].item
            results.append(
                detect_change(
                    old_item=old_item,
                    new_item=new_item,
                    diff_id=_diff_id(result_index),
                    match_method=match.match_method,
                    match_confidence=match.confidence,
                )
            )
            used_old_ids.add(old_item.knowledge_id)
            used_new_ids.add(new_item.knowledge_id)
            result_index += 1
            continue

        if match.match_method == MatchMethod.AMBIGUOUS:
            review_reason = ReviewReason(match.metadata.get("review_reason", ReviewReason.AMBIGUOUS_MATCH.value))
            results.append(
                _review_result(
                    old_item=None,
                    new_item=new_item,
                    index=result_index,
                    review_reason=review_reason,
                    reason_code=review_reason.value,
                    summary="存在多个可能对应项，需人工确认后再处理。",
                    priority="P1",
                    metadata={"candidate_old_ids": match.candidate_old_ids},
                )
            )
        else:
            results.append(_added_result(new_item, result_index))

        used_new_ids.add(new_item.knowledge_id)
        result_index += 1

    for old_item in old_items:
        if old_item.knowledge_id in used_old_ids:
            continue

        if not has_required_fields(old_item):
            results.append(_missing_required_result(old_item, result_index, is_new=False))
            result_index += 1
            continue

        if has_deprecation_evidence(old_item):
            results.append(
                _review_result(
                    old_item=old_item,
                    new_item=None,
                    index=result_index,
                    review_reason=ReviewReason.POSSIBLE_DEPRECATED,
                    reason_code="POSSIBLE_DEPRECATED",
                    summary="历史知识自身包含取消、终止、作废或到期等表达，需人工确认。",
                    priority="P1",
                )
            )
        elif item_in_scope(old_item, scope):
            results.append(
                _review_result(
                    old_item=old_item,
                    new_item=None,
                    index=result_index,
                    review_reason=ReviewReason.NO_RELIABLE_MATCH,
                    reason_code="OLD_IN_SCOPE_UNMATCHED",
                    summary="本轮资料可能涉及该范围，但未找到可靠对应新知识，默认建议保留并人工确认。",
                    priority="P2",
                    metadata={"default_action": "KEEP"},
                )
            )
        else:
            results.append(_unchanged_old_result(old_item, result_index))

        result_index += 1

    return _summarize(results, scope, started_at)
