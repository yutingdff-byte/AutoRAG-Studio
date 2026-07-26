"""Initial knowledge object definitions for future update workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KnowledgeItem:
    """Canonical knowledge object placeholder for V0.8 update milestones."""

    knowledge_id: str
    question: str
    answer: str
    category: str
    module: str | None = None
    brand: str | None = None
    model: str | None = None
    trim: str | None = None
    answer_type: str | None = None
    need_confirm: bool = False
    fact_refs: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
