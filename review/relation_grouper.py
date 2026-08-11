"""Group complex REVIEW_REQUIRED Diff results for exception review."""

from __future__ import annotations

from collections import defaultdict

from diff.intent_normalizer import GENERAL_BENEFIT, has_related_intent, normalize_intents, specific_intents
from diff.model_normalizer import is_related_model_relation, model_relation
from diff.models import ChangeType, DiffResult, DiffRunResult, ReviewReason
from knowledge.models import KnowledgeItem
from review.relation_models import RelationGroup, RelationGroupingResult, RelationType


COMPLEX_REASONS = {ReviewReason.ONE_TO_MANY, ReviewReason.MANY_TO_ONE}


def _item_id(item: KnowledgeItem | None) -> str:
    return item.knowledge_id if item else ""


def _item_model(item: KnowledgeItem | None) -> str:
    return str(item.model or "").strip() if item else ""


def _item_intents(item: KnowledgeItem | None) -> set[str]:
    if not item:
        return set()
    return normalize_intents(item.question, item.category, item.module)


def _unique_items(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    seen: set[str] = set()
    unique: list[KnowledgeItem] = []
    for item in items:
        item_id = _item_id(item)
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        unique.append(item)
    return unique


def _unique_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _old_item_index(diff_result: DiffRunResult) -> dict[str, KnowledgeItem]:
    index: dict[str, KnowledgeItem] = {}
    for result in diff_result.results:
        if result.old_item and result.old_item.knowledge_id:
            index.setdefault(result.old_item.knowledge_id, result.old_item)
    return index


def _old_diff_index(diff_result: DiffRunResult) -> dict[str, str]:
    index: dict[str, str] = {}
    for result in diff_result.results:
        if result.old_item and result.old_item.knowledge_id:
            index.setdefault(result.old_item.knowledge_id, result.diff_id)
    return index


def _candidate_old_ids(result: DiffResult) -> list[str]:
    ids = list(result.metadata.get("candidate_old_ids") or [])
    ids.extend(result.metadata.get("candidate_ids") or [])
    ids.extend(result.metadata.get("old_candidate_ids") or [])
    if result.old_item and result.old_item.knowledge_id:
        ids.insert(0, result.old_item.knowledge_id)
    return _unique_values([str(value) for value in ids if value])


def _is_safe_relation_candidate(result: DiffResult, old_item: KnowledgeItem) -> bool:
    if result.new_item:
        relation = model_relation(old_item.model, result.new_item.model)
        if not is_related_model_relation(relation):
            return False

    old_intents = _item_intents(old_item)
    new_intents = _item_intents(result.new_item)
    if old_intents and new_intents and not has_related_intent(old_intents, new_intents):
        return False

    return True


def _candidate_old_items(result: DiffResult, old_index: dict[str, KnowledgeItem]) -> list[KnowledgeItem]:
    items = []
    for candidate_id in _candidate_old_ids(result):
        old_item = old_index.get(candidate_id)
        if old_item and _is_safe_relation_candidate(result, old_item):
            items.append(old_item)
    return _unique_items(items)


def _group_type(reason: ReviewReason | None, old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> RelationType:
    old_intents = set().union(*(_item_intents(item) for item in old_items)) if old_items else set()
    new_intents = set().union(*(_item_intents(item) for item in new_items)) if new_items else set()

    if reason == ReviewReason.ONE_TO_MANY:
        if GENERAL_BENEFIT in old_intents and specific_intents(new_intents):
            return RelationType.GENERAL_TO_DETAIL
        return RelationType.ONE_TO_MANY

    if reason == ReviewReason.MANY_TO_ONE:
        if specific_intents(old_intents) and GENERAL_BENEFIT in new_intents:
            return RelationType.DETAIL_TO_GENERAL
        return RelationType.MANY_TO_ONE

    return RelationType.AMBIGUOUS_RELATION


def _group_model(old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> str:
    for item in new_items + old_items:
        model = _item_model(item)
        if model:
            return model
    return ""


def _group_intents(old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> list[str]:
    intents: set[str] = set()
    for item in old_items + new_items:
        intents.update(_item_intents(item))
    return sorted(intents)


def _make_group(
    *,
    group_id: str,
    relation_type: RelationType,
    items: list[DiffResult],
    old_items: list[KnowledgeItem],
    old_diff_ids: list[str],
) -> RelationGroup:
    new_items = _unique_items([item.new_item for item in items if item.new_item])
    old_items = _unique_items(old_items)
    diff_ids = _unique_values([item.diff_id for item in items])
    return RelationGroup(
        group_id=group_id,
        relation_type=relation_type,
        old_items=old_items,
        new_items=new_items,
        diff_ids=diff_ids,
        old_diff_ids=_unique_values(old_diff_ids),
        new_diff_ids=diff_ids,
        model=_group_model(old_items, new_items),
        intents=_group_intents(old_items, new_items),
        review_reason=_review_reason_text(relation_type),
        metadata={
            "raw_review_count": len(diff_ids),
            "old_count": len(old_items),
            "new_count": len(new_items),
        },
    )


def _review_reason_text(relation_type: RelationType) -> str:
    if relation_type == RelationType.GENERAL_TO_DETAIL:
        return "原综合知识被新资料拆分为多条更细知识。"
    if relation_type == RelationType.DETAIL_TO_GENERAL:
        return "多条历史细分知识在新资料中被合并为一条综合知识。"
    if relation_type == RelationType.ONE_TO_MANY:
        return "一条历史知识可能对应多条新知识。"
    if relation_type == RelationType.MANY_TO_ONE:
        return "多条历史知识可能对应同一条新知识。"
    return "系统发现新旧知识存在复杂对应关系。"


def group_review_required(diff_result: DiffRunResult) -> RelationGroupingResult:
    """Build review-layer relation groups without changing Diff decisions."""

    review_items = [
        result
        for result in diff_result.results
        if result.change_type == ChangeType.REVIEW_REQUIRED
        and result.review_reason in COMPLEX_REASONS
    ]
    all_review_ids = [
        result.diff_id
        for result in diff_result.results
        if result.change_type == ChangeType.REVIEW_REQUIRED
    ]
    old_index = _old_item_index(diff_result)
    old_diff_ids = _old_diff_index(diff_result)

    by_old: dict[str, list[DiffResult]] = defaultdict(list)
    many_to_one_groups: list[RelationGroup] = []
    consumed: set[str] = set()

    for result in review_items:
        old_items = _candidate_old_items(result, old_index)
        if result.review_reason == ReviewReason.MANY_TO_ONE and len(old_items) > 1:
            relation_type = _group_type(result.review_reason, old_items, [result.new_item] if result.new_item else [])
            group = _make_group(
                group_id=f"REL-{result.diff_id}",
                relation_type=relation_type,
                items=[result],
                old_items=old_items,
                old_diff_ids=[old_diff_ids[item.knowledge_id] for item in old_items if item.knowledge_id in old_diff_ids],
            )
            many_to_one_groups.append(group)
            consumed.add(result.diff_id)
            continue

        for old_item in old_items:
            by_old[old_item.knowledge_id].append(result)

    groups: list[RelationGroup] = []
    for old_id, items in by_old.items():
        items = [item for item in items if item.diff_id not in consumed]
        if len(items) < 2:
            continue
        old_item = old_index.get(old_id)
        if not old_item:
            continue
        relation_type = _group_type(items[0].review_reason, [old_item], [item.new_item for item in items if item.new_item])
        group = _make_group(
            group_id=f"REL-{old_id}",
            relation_type=relation_type,
            items=items,
            old_items=[old_item],
            old_diff_ids=[old_diff_ids[old_id]] if old_id in old_diff_ids else [],
        )
        groups.append(group)
        consumed.update(item.diff_id for item in items)

    for result in review_items:
        if result.diff_id in consumed:
            continue
        old_items = _candidate_old_items(result, old_index)
        if not old_items and result.old_item:
            old_items = [result.old_item]
        if not old_items or not result.new_item:
            continue
        relation_type = _group_type(result.review_reason, old_items, [result.new_item])
        group = _make_group(
            group_id=f"REL-{result.diff_id}",
            relation_type=relation_type,
            items=[result],
            old_items=old_items,
            old_diff_ids=[old_diff_ids[item.knowledge_id] for item in old_items if item.knowledge_id in old_diff_ids],
        )
        groups.append(group)
        consumed.add(result.diff_id)

    all_groups = many_to_one_groups + groups
    grouped_ids = {diff_id for group in all_groups for diff_id in group.diff_ids}
    singles = [diff_id for diff_id in all_review_ids if diff_id not in grouped_ids]

    return RelationGroupingResult(
        groups=all_groups,
        single_items=singles,
        raw_review_count=len(all_review_ids),
    )
