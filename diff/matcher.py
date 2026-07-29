"""Rule-based knowledge matching."""

from __future__ import annotations

from dataclasses import dataclass

from diff import confidence
from diff.candidate_builder import CandidateIndex, build_candidates_for_new
from diff.models import MatchMethod, MatchResult, ReviewReason
from diff.normalizer import NormalizedKnowledge
from diff.reasons import reason_text
from knowledge.models import KnowledgeItem


@dataclass(slots=True)
class ScoredCandidate:
    old_id: str
    score: float
    method: MatchMethod


def has_model_conflict(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    return bool(old_item.model and new_item.model and old_item.model != new_item.model)


def has_trim_conflict(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    return bool(old_item.trim and new_item.trim and old_item.trim != new_item.trim)


def category_compatible(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    if old_item.category and new_item.category and old_item.category == new_item.category:
        return True
    if old_item.knowledge_type and new_item.knowledge_type and old_item.knowledge_type == new_item.knowledge_type:
        return True
    return not (old_item.category and new_item.category and old_item.knowledge_type and new_item.knowledge_type)


def score_candidate(old: NormalizedKnowledge, new: NormalizedKnowledge) -> ScoredCandidate | None:
    old_item = old.item
    new_item = new.item

    if has_model_conflict(old_item, new_item):
        return None
    if has_trim_conflict(old_item, new_item):
        return None

    if old.normalized_question and old.normalized_question == new.normalized_question and category_compatible(old_item, new_item):
        return ScoredCandidate(old_item.knowledge_id, confidence.NORMALIZED_QUESTION_MATCH, MatchMethod.NORMALIZED_QUESTION)

    score = 0.0
    if old_item.model and new_item.model and old_item.model == new_item.model:
        score += 0.28
    if old_item.trim and new_item.trim and old_item.trim == new_item.trim:
        score += 0.12
    if old_item.category and new_item.category and old_item.category == new_item.category:
        score += 0.18
    if old_item.knowledge_type and new_item.knowledge_type and old_item.knowledge_type == new_item.knowledge_type:
        score += 0.14
    if old.topic == new.topic and old.topic != "general":
        score += 0.24
    if old.numbers and new.numbers and set(old.numbers) & set(new.numbers):
        score += 0.08

    if score >= confidence.STRUCTURED_MATCH:
        return ScoredCandidate(old_item.knowledge_id, min(score, 0.9), MatchMethod.STRUCTURED)
    if score >= confidence.REVIEW_CANDIDATE:
        return ScoredCandidate(old_item.knowledge_id, score, MatchMethod.AMBIGUOUS)
    return None


def match_new_item(
    new_item: KnowledgeItem,
    index: CandidateIndex,
    used_old_ids: set[str] | None = None,
) -> MatchResult:
    used_old_ids = used_old_ids or set()
    candidate_ids = [
        old_id
        for old_id in build_candidates_for_new(new_item, index)
        if old_id not in used_old_ids
    ]
    new_normalized = index.new_normalized[new_item.knowledge_id]

    scored: list[ScoredCandidate] = []
    for old_id in candidate_ids:
        old_normalized = index.old_normalized[old_id]
        candidate = score_candidate(old_normalized, new_normalized)
        if candidate:
            scored.append(candidate)

    if not scored:
        return MatchResult(
            old_knowledge_id=None,
            new_knowledge_id=new_item.knowledge_id,
            matched=False,
            match_method=MatchMethod.UNMATCHED,
            confidence=confidence.NO_MATCH,
            reason_code="NEW_KNOWLEDGE",
            reason_text=reason_text("NEW_KNOWLEDGE"),
            candidate_old_ids=candidate_ids,
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    best = scored[0]

    if len(scored) > 1 and best.score - scored[1].score < 0.08:
        return MatchResult(
            old_knowledge_id=None,
            new_knowledge_id=new_item.knowledge_id,
            matched=False,
            match_method=MatchMethod.AMBIGUOUS,
            confidence=best.score,
            reason_code=ReviewReason.AMBIGUOUS_MATCH.value,
            reason_text=reason_text("AMBIGUOUS_MATCH"),
            candidate_old_ids=[item.old_id for item in scored],
            metadata={"review_reason": ReviewReason.AMBIGUOUS_MATCH.value},
        )

    if best.method == MatchMethod.AMBIGUOUS:
        return MatchResult(
            old_knowledge_id=None,
            new_knowledge_id=new_item.knowledge_id,
            matched=False,
            match_method=MatchMethod.AMBIGUOUS,
            confidence=best.score,
            reason_code=ReviewReason.LOW_CONFIDENCE.value,
            reason_text=reason_text("AMBIGUOUS_MATCH"),
            candidate_old_ids=[item.old_id for item in scored],
            metadata={"review_reason": ReviewReason.LOW_CONFIDENCE.value},
        )

    return MatchResult(
        old_knowledge_id=best.old_id,
        new_knowledge_id=new_item.knowledge_id,
        matched=True,
        match_method=best.method,
        confidence=best.score,
        reason_code="EXACT_MATCH" if best.method == MatchMethod.NORMALIZED_QUESTION else "STRUCTURED_MATCH",
        reason_text=reason_text("EXACT_MATCH" if best.method == MatchMethod.NORMALIZED_QUESTION else "STRUCTURED_MATCH"),
        candidate_old_ids=[item.old_id for item in scored],
    )
