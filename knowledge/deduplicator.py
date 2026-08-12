"""Deterministic exact duplicate cleanup for final knowledge export."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata

from knowledge.models import KnowledgeItem


WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class DuplicateGroup:
    duplicate_group_id: str
    kept_item_id: str
    removed_item_ids: list[str]
    reason: str = "EXACT_DUPLICATE"
    duplicate_key: tuple[str, str, str, str, str] = field(default_factory=tuple)


@dataclass(slots=True)
class DuplicateCleanupResult:
    final_items: list[KnowledgeItem]
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    removed_items: list[KnowledgeItem] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return len(self.removed_items)


def _normalize_exact_value(value: str | None) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def exact_duplicate_key(item: KnowledgeItem) -> tuple[str, str, str, str, str]:
    """Build a conservative key for exact production duplicate cleanup."""

    question = item.normalized_question or item.question
    return (
        _normalize_exact_value(item.model),
        _normalize_exact_value(item.trim),
        _normalize_exact_value(question),
        _normalize_exact_value(item.answer),
        _normalize_exact_value(item.category),
    )


def cleanup_exact_duplicates(items: list[KnowledgeItem]) -> DuplicateCleanupResult:
    """Remove only exact duplicates while preserving the first item instance."""

    kept_by_key: dict[tuple[str, str, str, str, str], KnowledgeItem] = {}
    groups_by_key: dict[tuple[str, str, str, str, str], DuplicateGroup] = {}
    final_items: list[KnowledgeItem] = []
    removed_items: list[KnowledgeItem] = []

    for item in items:
        key = exact_duplicate_key(item)
        kept = kept_by_key.get(key)
        if kept is None:
            kept_by_key[key] = item
            final_items.append(item)
            continue

        removed_items.append(item)
        group = groups_by_key.get(key)
        if group is None:
            group = DuplicateGroup(
                duplicate_group_id=f"DUP-{len(groups_by_key) + 1:03d}",
                kept_item_id=kept.knowledge_id,
                removed_item_ids=[],
                duplicate_key=key,
            )
            groups_by_key[key] = group
        group.removed_item_ids.append(item.knowledge_id)

    return DuplicateCleanupResult(
        final_items=final_items,
        duplicate_groups=list(groups_by_key.values()),
        removed_items=removed_items,
    )
