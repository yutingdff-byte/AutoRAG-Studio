"""Rule-based knowledge matching."""

from __future__ import annotations

from dataclasses import dataclass

from diff import confidence
from diff.candidate_builder import CandidateIndex, build_candidates_for_new
from diff.intent_normalizer import GENERAL_BENEFIT, has_related_intent, has_same_intent, normalize_intents, specific_intents
from diff.model_normalizer import ModelRelation, is_strong_model_relation, model_relation
from diff.models import MatchMethod, MatchResult, ReviewReason
from diff.normalizer import NormalizedKnowledge
from diff.reasons import reason_text
from knowledge.models import KnowledgeItem


@dataclass(slots=True)
class ScoredCandidate:
    old_id: str
    score: float
    method: MatchMethod
    reason: str = ""


def has_model_conflict(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    return model_relation(old_item.model, new_item.model) == ModelRelation.CONFLICT


def has_trim_conflict(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    return bool(old_item.trim and new_item.trim and old_item.trim != new_item.trim)


def category_compatible(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    if old_item.category and new_item.category and old_item.category == new_item.category:
        return True
    if old_item.knowledge_type and new_item.knowledge_type and old_item.knowledge_type == new_item.knowledge_type:
        return True
    old_intents = getattr(old_item, "_diff_intents", None)
    new_intents = getattr(new_item, "_diff_intents", None)
    if old_intents and new_intents and (has_same_intent(old_intents, new_intents) or has_related_intent(old_intents, new_intents)):
        return True
    return not (old_item.category and new_item.category and old_item.knowledge_type and new_item.knowledge_type)


def _same_specific_intent(old: NormalizedKnowledge, new: NormalizedKnowledge) -> bool:
    return bool(specific_intents(old.intents) & specific_intents(new.intents))


def _same_or_related_intent(old: NormalizedKnowledge, new: NormalizedKnowledge) -> bool:
    return has_same_intent(old.intents, new.intents) or has_related_intent(old.intents, new.intents)


def _general_specific_relation(old: NormalizedKnowledge, new: NormalizedKnowledge) -> bool:
    old_surface = normalize_intents(old.item.question, old.item.category)
    new_surface = normalize_intents(new.item.question, new.item.category)
    old_specific = specific_intents(old_surface)
    new_specific = specific_intents(new_surface)
    return (GENERAL_BENEFIT in old_surface and not old_specific and bool(specific_intents(new.intents))) or (
        GENERAL_BENEFIT in new_surface and not new_specific and bool(specific_intents(old.intents))
    )


def _complex_review_reason(old: NormalizedKnowledge, new: NormalizedKnowledge) -> ReviewReason:
    old_surface = normalize_intents(old.item.question, old.item.category)
    new_surface = normalize_intents(new.item.question, new.item.category)
    old_specific = specific_intents(old_surface)
    new_specific = specific_intents(new_surface)
    if GENERAL_BENEFIT in old_surface and not old_specific and bool(specific_intents(new.intents)):
        return ReviewReason.ONE_TO_MANY
    if GENERAL_BENEFIT in new_surface and not new_specific and bool(specific_intents(old.intents)):
        return ReviewReason.MANY_TO_ONE
    return ReviewReason.AMBIGUOUS_MATCH


def score_candidate(old: NormalizedKnowledge, new: NormalizedKnowledge) -> ScoredCandidate | None:
    old_item = old.item
    new_item = new.item

    relation = model_relation(old_item.model, new_item.model)
    if relation == ModelRelation.CONFLICT:
        return None
    if has_trim_conflict(old_item, new_item):
        return None

    same_specific_intent = _same_specific_intent(old, new)
    related_intent = _same_or_related_intent(old, new)
    strong_model = is_strong_model_relation(relation)
    old_specific = specific_intents(old.intents)
    new_specific = specific_intents(new.intents)
    old_surface_specific = specific_intents(normalize_intents(old.item.question, old.item.category))
    new_surface_specific = specific_intents(normalize_intents(new.item.question, new.item.category))

    if old_surface_specific and new_surface_specific and not (old_surface_specific & new_surface_specific):
        return None
    if old_specific and new_specific and not (old_specific & new_specific):
        return None

    if _general_specific_relation(old, new) and relation in {
        ModelRelation.EXACT,
        ModelRelation.ALIAS,
        ModelRelation.FAMILY,
        ModelRelation.VARIANT,
    }:
        return ScoredCandidate(
            old_item.knowledge_id,
            confidence.REVIEW_CANDIDATE,
            MatchMethod.AMBIGUOUS,
            _complex_review_reason(old, new).value,
        )

    if (
        old.normalized_question
        and old.normalized_question == new.normalized_question
        and category_compatible(old_item, new_item)
        and (has_same_intent(old.intents, new.intents) or not old.intents or not new.intents)
    ):
        return ScoredCandidate(
            old_item.knowledge_id,
            confidence.NORMALIZED_QUESTION_MATCH,
            MatchMethod.NORMALIZED_QUESTION,
            "NORMALIZED_QUESTION",
        )

    if strong_model and same_specific_intent:
        if old.normalized_question == new.normalized_question:
            return ScoredCandidate(old_item.knowledge_id, 0.94, MatchMethod.STRUCTURED, "MODEL_STRONG+INTENT+QUESTION")
        if set(old.numbers) & set(new.numbers):
            return ScoredCandidate(old_item.knowledge_id, 0.88, MatchMethod.STRUCTURED, "MODEL_STRONG+INTENT+NUMBER")
        if old.topic == new.topic and old.topic != "general":
            return ScoredCandidate(old_item.knowledge_id, 0.86, MatchMethod.STRUCTURED, "MODEL_STRONG+INTENT+TOPIC")

    score = 0.0
    if relation == ModelRelation.EXACT:
        score += 0.28
    elif relation == ModelRelation.ALIAS:
        score += 0.26
    elif relation in {ModelRelation.FAMILY, ModelRelation.VARIANT}:
        score += 0.12
    if old_item.trim and new_item.trim and old_item.trim == new_item.trim:
        score += 0.12
    if old_item.category and new_item.category and old_item.category == new_item.category:
        score += 0.18
    if old_item.knowledge_type and new_item.knowledge_type and old_item.knowledge_type == new_item.knowledge_type:
        score += 0.14
    if old.topic == new.topic and old.topic != "general":
        score += 0.24
    if same_specific_intent:
        score += 0.24
    elif related_intent:
        score += 0.10
    if old.numbers and new.numbers and set(old.numbers) & set(new.numbers):
        score += 0.08

    if relation in {ModelRelation.FAMILY, ModelRelation.VARIANT} and related_intent and score >= confidence.REVIEW_CANDIDATE:
        return ScoredCandidate(old_item.knowledge_id, score, MatchMethod.AMBIGUOUS, "MODEL_FAMILY_REVIEW")

    if score >= confidence.STRUCTURED_MATCH:
        return ScoredCandidate(old_item.knowledge_id, min(score, 0.9), MatchMethod.STRUCTURED, "STRUCTURED_V2")
    if score >= confidence.REVIEW_CANDIDATE:
        return ScoredCandidate(old_item.knowledge_id, score, MatchMethod.AMBIGUOUS, "REVIEW_CANDIDATE_V2")
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
        review_reason = best.reason if best.reason in {reason.value for reason in ReviewReason} else ReviewReason.AMBIGUOUS_MATCH.value
        return MatchResult(
            old_knowledge_id=None,
            new_knowledge_id=new_item.knowledge_id,
            matched=False,
            match_method=MatchMethod.AMBIGUOUS,
            confidence=best.score,
            reason_code=review_reason,
            reason_text=reason_text("AMBIGUOUS_MATCH"),
            candidate_old_ids=[item.old_id for item in scored],
            metadata={"review_reason": review_reason, "match_reason": best.reason},
        )

    if best.method == MatchMethod.AMBIGUOUS:
        review_reason = best.reason if best.reason in {reason.value for reason in ReviewReason} else ReviewReason.LOW_CONFIDENCE.value
        return MatchResult(
            old_knowledge_id=None,
            new_knowledge_id=new_item.knowledge_id,
            matched=False,
            match_method=MatchMethod.AMBIGUOUS,
            confidence=best.score,
            reason_code=review_reason,
            reason_text=reason_text("AMBIGUOUS_MATCH"),
            candidate_old_ids=[item.old_id for item in scored],
            metadata={"review_reason": review_reason, "match_reason": best.reason},
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
        metadata={"match_reason": best.reason},
    )
