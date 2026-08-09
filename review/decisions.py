"""Default review decisions derived from Diff results."""

from __future__ import annotations

from diff.models import ChangeType, DiffResult
from review.models import ReviewDecision, ReviewDecisionType


def requires_review(result: DiffResult) -> bool:
    return result.change_type in {
        ChangeType.ADDED,
        ChangeType.UPDATED,
        ChangeType.REVIEW_REQUIRED,
    }


def default_decision_for_result(result: DiffResult) -> ReviewDecision:
    if result.change_type == ChangeType.ADDED:
        return ReviewDecision(
            diff_id=result.diff_id,
            decision=ReviewDecisionType.ACCEPT_NEW,
            final_item=result.new_item,
            reviewed=False,
        )

    if result.change_type == ChangeType.UPDATED:
        return ReviewDecision(
            diff_id=result.diff_id,
            decision=ReviewDecisionType.ACCEPT_NEW,
            final_item=result.new_item,
            reviewed=False,
        )

    return ReviewDecision(
        diff_id=result.diff_id,
        decision=ReviewDecisionType.KEEP_OLD,
        final_item=result.old_item,
        reviewed=False,
    )


def build_default_decisions(results: list[DiffResult]) -> dict[str, ReviewDecision]:
    return {
        result.diff_id: default_decision_for_result(result)
        for result in results
        if requires_review(result)
    }


def decision_from_label(result: DiffResult, label: str, delete_confirmed: bool = False) -> ReviewDecision:
    if label in {"加入新版知识库", "使用新答案", "使用新知识"}:
        return ReviewDecision(
            diff_id=result.diff_id,
            decision=ReviewDecisionType.ACCEPT_NEW,
            final_item=result.new_item,
            reviewed=True,
        )

    if label in {"不加入", "跳过"}:
        return ReviewDecision(
            diff_id=result.diff_id,
            decision=ReviewDecisionType.SKIP,
            final_item=None,
            reviewed=True,
        )

    if label in {"确认删除"}:
        return ReviewDecision(
            diff_id=result.diff_id,
            decision=ReviewDecisionType.REMOVE,
            final_item=None,
            reviewed=True,
            metadata={"delete_confirmed": bool(delete_confirmed)},
        )

    return ReviewDecision(
        diff_id=result.diff_id,
        decision=ReviewDecisionType.KEEP_OLD,
        final_item=result.old_item,
        reviewed=True,
    )

