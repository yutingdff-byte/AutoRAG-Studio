"""Initial knowledge object definitions for future update workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def normalize_question(question: str) -> str:
    """Normalize question text for future matching without changing display text."""

    return "".join(str(question or "").split()).lower()


@dataclass(slots=True)
class KnowledgeItem:
    """Canonical knowledge object placeholder for V0.8 update milestones."""

    knowledge_id: str
    question: str
    answer: str
    category: str
    normalized_question: str = ""
    module: str | None = None
    brand: str | None = None
    model: str | None = None
    trim: str | None = None
    knowledge_type: str = "general"
    answer_type: str | None = None
    need_confirm: bool = False
    fact_refs: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.normalized_question:
            self.normalized_question = normalize_question(self.question)
