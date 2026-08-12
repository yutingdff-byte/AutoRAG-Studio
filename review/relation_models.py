"""Review-layer relation models for complex Update decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from knowledge.models import KnowledgeItem


class RelationType(str, Enum):
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    GENERAL_TO_DETAIL = "GENERAL_TO_DETAIL"
    DETAIL_TO_GENERAL = "DETAIL_TO_GENERAL"
    AMBIGUOUS_RELATION = "AMBIGUOUS_RELATION"


class RelationDecisionType(str, Enum):
    ADD_NEW_KEEP_OLD = "ADD_NEW_KEEP_OLD"
    REPLACE_OLD_WITH_NEW = "REPLACE_OLD_WITH_NEW"
    KEEP_OLD_ONLY = "KEEP_OLD_ONLY"
    CUSTOM = "CUSTOM"


@dataclass(slots=True)
class RelationGroup:
    group_id: str
    relation_type: RelationType
    old_items: list[KnowledgeItem]
    new_items: list[KnowledgeItem]
    diff_ids: list[str]
    model: str = ""
    intents: list[str] = field(default_factory=list)
    review_reason: str = ""
    default_decision: RelationDecisionType = RelationDecisionType.ADD_NEW_KEEP_OLD
    old_diff_ids: list[str] = field(default_factory=list)
    new_diff_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RelationDecision:
    group_id: str
    decision: RelationDecisionType
    reviewed: bool = False
    selected_old_ids: list[str] = field(default_factory=list)
    selected_new_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RelationGroupingResult:
    groups: list[RelationGroup] = field(default_factory=list)
    single_items: list[str] = field(default_factory=list)
    raw_review_count: int = 0

