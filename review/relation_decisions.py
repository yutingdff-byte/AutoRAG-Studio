"""Expand relation-level decisions into existing ReviewDecision objects."""

from __future__ import annotations

from diff.models import DiffResult, DiffRunResult
from diff.models import ChangeType
from review.models import ReviewDecision, ReviewDecisionType
from review.relation_models import RelationDecision, RelationDecisionType, RelationGroup


def default_relation_decision(group: RelationGroup) -> RelationDecision:
    return RelationDecision(
        group_id=group.group_id,
        decision=group.default_decision,
        reviewed=False,
        selected_old_ids=[item.knowledge_id for item in group.old_items],
        selected_new_ids=[item.knowledge_id for item in group.new_items],
    )


def build_default_relation_decisions(groups: list[RelationGroup]) -> dict[str, RelationDecision]:
    return {group.group_id: default_relation_decision(group) for group in groups}


def _result_index(diff_result: DiffRunResult) -> dict[str, DiffResult]:
    return {result.diff_id: result for result in diff_result.results}


def apply_relation_decisions(
    diff_result: DiffRunResult,
    groups: list[RelationGroup],
    relation_decisions: dict[str, RelationDecision],
    base_decisions: dict[str, ReviewDecision],
) -> dict[str, ReviewDecision]:
    """Return a ReviewDecision map with relation decisions applied."""

    decisions = dict(base_decisions)
    result_by_id = _result_index(diff_result)

    for group in groups:
        relation_decision = relation_decisions.get(group.group_id) or default_relation_decision(group)

        if relation_decision.decision == RelationDecisionType.KEEP_OLD_ONLY:
            _apply_keep_old_only(group, decisions, result_by_id)
            continue

        if relation_decision.decision == RelationDecisionType.REPLACE_OLD_WITH_NEW:
            _apply_accept_new(group, decisions, result_by_id, keep_old_with_new=False)
            _apply_remove_old(group, decisions, result_by_id, delete_confirmed=bool(relation_decision.metadata.get("delete_confirmed")))
            continue

        if relation_decision.decision == RelationDecisionType.CUSTOM:
            _apply_custom(group, relation_decision, decisions, result_by_id)
            continue

        _apply_accept_new(group, decisions, result_by_id, keep_old_with_new=True)
        _apply_keep_old(group, decisions, result_by_id)

    return decisions


def _apply_accept_new(
    group: RelationGroup,
    decisions: dict[str, ReviewDecision],
    result_by_id: dict[str, DiffResult],
    *,
    keep_old_with_new: bool,
) -> None:
    for diff_id in group.diff_ids:
        result = result_by_id.get(diff_id)
        if not result or not result.new_item:
            continue
        decisions[diff_id] = ReviewDecision(
            diff_id=diff_id,
            decision=ReviewDecisionType.ACCEPT_NEW,
            final_item=result.new_item,
            reviewed=True,
            metadata={
                "relation_group_id": group.group_id,
                "keep_old_with_new": keep_old_with_new,
            },
        )


def _apply_keep_old(
    group: RelationGroup,
    decisions: dict[str, ReviewDecision],
    result_by_id: dict[str, DiffResult],
) -> None:
    for diff_id in group.old_diff_ids:
        result = result_by_id.get(diff_id)
        if not result or not result.old_item:
            continue
        if result.change_type not in {ChangeType.UNCHANGED, ChangeType.REVIEW_REQUIRED}:
            continue
        decisions[diff_id] = ReviewDecision(
            diff_id=diff_id,
            decision=ReviewDecisionType.KEEP_OLD,
            final_item=result.old_item,
            reviewed=True,
            metadata={"relation_group_id": group.group_id},
        )


def _apply_keep_old_only(
    group: RelationGroup,
    decisions: dict[str, ReviewDecision],
    result_by_id: dict[str, DiffResult],
) -> None:
    for diff_id in group.diff_ids:
        result = result_by_id.get(diff_id)
        decisions[diff_id] = ReviewDecision(
            diff_id=diff_id,
            decision=ReviewDecisionType.SKIP,
            final_item=None,
            reviewed=True,
            metadata={"relation_group_id": group.group_id},
        )
    _apply_keep_old(group, decisions, result_by_id)


def _apply_remove_old(
    group: RelationGroup,
    decisions: dict[str, ReviewDecision],
    result_by_id: dict[str, DiffResult],
    *,
    delete_confirmed: bool,
) -> None:
    for diff_id in group.old_diff_ids:
        result = result_by_id.get(diff_id)
        if not result or not result.old_item:
            continue
        if result.change_type not in {ChangeType.UNCHANGED, ChangeType.REVIEW_REQUIRED}:
            continue
        decisions[diff_id] = ReviewDecision(
            diff_id=diff_id,
            decision=ReviewDecisionType.REMOVE,
            final_item=None,
            reviewed=True,
            metadata={
                "relation_group_id": group.group_id,
                "delete_confirmed": delete_confirmed,
            },
        )


def _apply_custom(
    group: RelationGroup,
    relation_decision: RelationDecision,
    decisions: dict[str, ReviewDecision],
    result_by_id: dict[str, DiffResult],
) -> None:
    selected_new_ids = set(relation_decision.selected_new_ids)
    selected_old_ids = set(relation_decision.selected_old_ids)

    for diff_id in group.diff_ids:
        result = result_by_id.get(diff_id)
        if not result or not result.new_item:
            continue
        if result.new_item.knowledge_id in selected_new_ids:
            decisions[diff_id] = ReviewDecision(
                diff_id=diff_id,
                decision=ReviewDecisionType.ACCEPT_NEW,
                final_item=result.new_item,
                reviewed=True,
                metadata={"relation_group_id": group.group_id, "keep_old_with_new": True},
            )
        else:
            decisions[diff_id] = ReviewDecision(
                diff_id=diff_id,
                decision=ReviewDecisionType.SKIP,
                final_item=None,
                reviewed=True,
                metadata={"relation_group_id": group.group_id},
            )

    for diff_id in group.old_diff_ids:
        result = result_by_id.get(diff_id)
        if not result or not result.old_item:
            continue
        if result.change_type not in {ChangeType.UNCHANGED, ChangeType.REVIEW_REQUIRED}:
            continue
        decision_type = ReviewDecisionType.KEEP_OLD if result.old_item.knowledge_id in selected_old_ids else ReviewDecisionType.REMOVE
        decisions[diff_id] = ReviewDecision(
            diff_id=diff_id,
            decision=decision_type,
            final_item=result.old_item if decision_type == ReviewDecisionType.KEEP_OLD else None,
            reviewed=True,
            metadata={
                "relation_group_id": group.group_id,
                "delete_confirmed": bool(relation_decision.metadata.get("delete_confirmed")),
            },
        )
