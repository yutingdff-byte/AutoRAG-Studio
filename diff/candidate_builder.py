"""Build limited candidate sets for rule matching."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from diff.intent_normalizer import GENERAL_BENEFIT, has_related_intent, has_same_intent
from diff.model_normalizer import ModelRelation, is_related_model_relation, normalize_model, model_relation
from diff.normalizer import NormalizedKnowledge, normalize_item
from knowledge.models import KnowledgeItem


@dataclass(slots=True)
class CandidateIndex:
    old_normalized: dict[str, NormalizedKnowledge] = field(default_factory=dict)
    new_normalized: dict[str, NormalizedKnowledge] = field(default_factory=dict)
    by_normalized_question: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_model: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_model_alias: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_model_family: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_trim: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_category: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_knowledge_type: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_signature: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    by_intent: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def build_index(old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> CandidateIndex:
    index = CandidateIndex()

    for item in old_items:
        normalized = normalize_item(item)
        item_id = item.knowledge_id
        index.old_normalized[item_id] = normalized
        index.by_normalized_question[normalized.normalized_question].append(item_id)
        if item.model:
            index.by_model[item.model].append(item_id)
            normalized_model = normalize_model(item.model)
            index.by_model_alias[normalized_model.without_brand].append(item_id)
            index.by_model_family[normalized_model.family].append(item_id)
        if item.trim:
            index.by_trim[item.trim].append(item_id)
        if item.category:
            index.by_category[item.category].append(item_id)
        if item.knowledge_type:
            index.by_knowledge_type[item.knowledge_type].append(item_id)
        index.by_signature[normalized.signature].append(item_id)
        for intent in normalized.intents:
            index.by_intent[intent].append(item_id)

    for item in new_items:
        index.new_normalized[item.knowledge_id] = normalize_item(item)

    return index


def _compatible_model(new_item: KnowledgeItem, old_item: KnowledgeItem) -> bool:
    return is_related_model_relation(model_relation(new_item.model, old_item.model))


def build_candidates_for_new(
    new_item: KnowledgeItem,
    index: CandidateIndex,
    max_candidates_per_item: int = 5,
) -> list[str]:
    normalized_new = index.new_normalized[new_item.knowledge_id]
    candidate_ids: list[str] = []

    def add(ids: list[str]) -> None:
        for old_id in ids:
            if old_id in candidate_ids:
                continue
            old_item = index.old_normalized[old_id].item
            if not _compatible_model(new_item, old_item):
                continue
            candidate_ids.append(old_id)
            if len(candidate_ids) >= max_candidates_per_item:
                return

    add(index.by_normalized_question.get(normalized_new.normalized_question, []))
    add(index.by_signature.get(normalized_new.signature, []))
    for intent in normalized_new.intents:
        add(index.by_intent.get(intent, []))
        if intent == GENERAL_BENEFIT:
            continue
        for old_id, old_normalized in index.old_normalized.items():
            if old_id in candidate_ids:
                continue
            old_item = old_normalized.item
            if model_relation(new_item.model, old_item.model) == ModelRelation.CONFLICT:
                continue
            if has_same_intent(normalized_new.intents, old_normalized.intents) or has_related_intent(
                normalized_new.intents, old_normalized.intents
            ):
                add([old_id])
    if new_item.model:
        add(index.by_model.get(new_item.model, []))
        normalized_model = normalize_model(new_item.model)
        add(index.by_model_alias.get(normalized_model.without_brand, []))
        add(index.by_model_family.get(normalized_model.family, []))
    if new_item.category:
        add(index.by_category.get(new_item.category, []))
    if new_item.knowledge_type:
        add(index.by_knowledge_type.get(new_item.knowledge_type, []))

    return candidate_ids[:max_candidates_per_item]
