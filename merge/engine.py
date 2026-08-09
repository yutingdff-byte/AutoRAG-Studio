"""Deterministic merge engine for Update workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from diff.models import ChangeType, DiffRunResult
from knowledge.models import KnowledgeItem
from review.decisions import default_decision_for_result
from review.models import ReviewDecision, ReviewDecisionType


@dataclass(slots=True)
class MergeWarning:
    warning_type: str
    knowledge_ids: list[str]
    message: str


@dataclass(slots=True)
class MergeResult:
    final_items: list[KnowledgeItem]
    added_accepted: int = 0
    updated_accepted: int = 0
    kept_old: int = 0
    removed: int = 0
    skipped: int = 0
    duplicate_warnings: list[MergeWarning] = field(default_factory=list)


def _decision_for(diff_id: str, decisions: dict[str, ReviewDecision], result) -> ReviewDecision:
    return decisions.get(diff_id) or default_decision_for_result(result)


def _duplicate_key(item: KnowledgeItem) -> tuple[str, str, str]:
    return (
        str(item.model or "").strip(),
        str(item.normalized_question or "").strip(),
        str(item.category or "").strip(),
    )


def _duplicate_warnings(items: list[KnowledgeItem]) -> list[MergeWarning]:
    seen: dict[tuple[str, str, str], KnowledgeItem] = {}
    warnings: list[MergeWarning] = []
    for item in items:
        key = _duplicate_key(item)
        if not any(key):
            continue
        previous = seen.get(key)
        if previous is None:
            seen[key] = item
            continue
        if previous.answer == item.answer:
            warning_type = "duplicate_exact"
            message = "发现完全重复知识，已保留原条目供人工确认。"
        else:
            warning_type = "duplicate_possible"
            message = "发现可能重复知识，答案不同，已全部保留供人工确认。"
        warnings.append(
            MergeWarning(
                warning_type=warning_type,
                knowledge_ids=[previous.knowledge_id, item.knowledge_id],
                message=message,
            )
        )
    return warnings


def merge_knowledge(diff_result: DiffRunResult, decisions: dict[str, ReviewDecision] | None = None) -> MergeResult:
    decisions = decisions or {}
    final_items: list[KnowledgeItem] = []
    result = MergeResult(final_items=final_items)

    for diff_item in diff_result.results:
        if diff_item.change_type == ChangeType.UNCHANGED:
            if diff_item.old_item:
                final_items.append(diff_item.old_item)
                result.kept_old += 1
            continue

        decision = _decision_for(diff_item.diff_id, decisions, diff_item)

        if decision.decision == ReviewDecisionType.REMOVE:
            if decision.metadata.get("delete_confirmed"):
                result.removed += 1
            elif diff_item.old_item:
                final_items.append(diff_item.old_item)
                result.kept_old += 1
            continue

        if decision.decision == ReviewDecisionType.SKIP:
            result.skipped += 1
            continue

        if decision.decision == ReviewDecisionType.ACCEPT_NEW:
            if diff_item.new_item:
                final_items.append(diff_item.new_item)
                if diff_item.change_type == ChangeType.ADDED:
                    result.added_accepted += 1
                elif diff_item.change_type == ChangeType.UPDATED:
                    result.updated_accepted += 1
            elif diff_item.old_item:
                final_items.append(diff_item.old_item)
                result.kept_old += 1
            continue

        if diff_item.old_item:
            final_items.append(diff_item.old_item)
            result.kept_old += 1

    result.duplicate_warnings = _duplicate_warnings(final_items)
    return result

