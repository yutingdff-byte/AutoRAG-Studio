"""Automatic update scope detection from new KnowledgeItem objects."""

from __future__ import annotations

from collections.abc import Iterable

from diff.models import DetectedUpdateScope
from knowledge.models import KnowledgeItem


def _unique(values: Iterable[str | None]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value or "").strip()})


def detect_update_scope(new_items: list[KnowledgeItem], old_items: list[KnowledgeItem] | None = None) -> DetectedUpdateScope:
    old_items = old_items or []

    scope = DetectedUpdateScope(
        brands=_unique(item.brand for item in new_items),
        models=_unique(item.model for item in new_items),
        trims=_unique(item.trim for item in new_items),
        categories=_unique(item.category for item in new_items),
        modules=_unique(item.module for item in new_items),
        knowledge_types=_unique(item.knowledge_type for item in new_items),
        source_files=_unique(source for item in new_items for source in item.source_files),
    )

    detected_dimensions = sum(
        1
        for values in [
            scope.brands,
            scope.models,
            scope.categories,
            scope.knowledge_types,
            scope.source_files,
        ]
        if values
    )
    scope.confidence = min(0.95, 0.45 + detected_dimensions * 0.1) if new_items else 0.0

    old_categories = set(_unique(item.category for item in old_items))
    new_categories = set(scope.categories)
    not_obvious_categories = sorted(old_categories - new_categories)

    model_text = "、".join(scope.models) if scope.models else "未识别明确车型"
    category_text = "、".join(scope.categories) if scope.categories else "未识别明确分类"
    scope.summary = f"系统识别本轮资料涉及车型：{model_text}；主要分类：{category_text}。"
    scope.metadata = {
        "not_obvious_categories": not_obvious_categories,
    }
    return scope


def item_in_scope(item: KnowledgeItem, scope: DetectedUpdateScope) -> bool:
    if not scope.categories and not scope.models and not scope.knowledge_types:
        return False

    model_match = bool(item.model and item.model in scope.models)
    category_match = bool(item.category and item.category in scope.categories)
    type_match = bool(item.knowledge_type and item.knowledge_type in scope.knowledge_types)

    if scope.models and item.model and not model_match:
        return False

    if category_match or type_match:
        return True

    # Model-only overlap is useful for display, but it is too broad to mark
    # unrelated old knowledge as affected by the current update.
    return False
