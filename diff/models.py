"""Data models for rule-based knowledge diff."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from knowledge.models import KnowledgeItem


class ChangeType(str, Enum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class MatchMethod(str, Enum):
    EXACT_QUESTION = "EXACT_QUESTION"
    NORMALIZED_QUESTION = "NORMALIZED_QUESTION"
    STRUCTURED = "STRUCTURED"
    UNMATCHED = "UNMATCHED"
    AMBIGUOUS = "AMBIGUOUS"


class ReviewReason(str, Enum):
    NO_RELIABLE_MATCH = "NO_RELIABLE_MATCH"
    OUT_OF_DETECTED_SCOPE = "OUT_OF_DETECTED_SCOPE"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    MODEL_CONFLICT = "MODEL_CONFLICT"
    TRIM_CONFLICT = "TRIM_CONFLICT"
    CATEGORY_CONFLICT = "CATEGORY_CONFLICT"
    ANSWER_CONFLICT = "ANSWER_CONFLICT"
    POSSIBLE_DEPRECATED = "POSSIBLE_DEPRECATED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    DUPLICATE_KNOWLEDGE = "DUPLICATE_KNOWLEDGE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"


@dataclass(slots=True)
class MatchResult:
    old_knowledge_id: str | None
    new_knowledge_id: str | None
    matched: bool
    match_method: MatchMethod
    confidence: float
    reason_code: str = ""
    reason_text: str = ""
    candidate_old_ids: list[str] = field(default_factory=list)
    candidate_new_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiffResult:
    diff_id: str
    old_item: KnowledgeItem | None
    new_item: KnowledgeItem | None
    change_type: ChangeType
    match_method: MatchMethod
    match_confidence: float
    change_confidence: float
    overall_confidence: float
    reason_code: str = ""
    reason_text: str = ""
    review_reason: ReviewReason | None = None
    changed_fields: list[str] = field(default_factory=list)
    change_summary: str = ""
    needs_review: bool = False
    review_priority: str = "P3"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DetectedUpdateScope:
    brands: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    trims: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    modules: list[str] = field(default_factory=list)
    knowledge_types: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiffRunResult:
    results: list[DiffResult]
    detected_scope: DetectedUpdateScope
    total_count: int = 0
    added_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    review_required_count: int = 0
    timings: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
