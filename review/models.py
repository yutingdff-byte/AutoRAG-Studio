"""Review decision models for Update workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from knowledge.models import KnowledgeItem


class ReviewDecisionType(str, Enum):
    ACCEPT_NEW = "ACCEPT_NEW"
    KEEP_OLD = "KEEP_OLD"
    REMOVE = "REMOVE"
    SKIP = "SKIP"


@dataclass(slots=True)
class ReviewDecision:
    diff_id: str
    decision: ReviewDecisionType
    final_item: KnowledgeItem | None = None
    reviewed: bool = False
    review_note: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

