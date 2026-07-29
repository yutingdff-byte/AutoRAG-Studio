"""Detect factual changes for already matched knowledge pairs."""

from __future__ import annotations

from diff import confidence
from diff.models import ChangeType, DiffResult, MatchMethod, ReviewReason
from diff.normalizer import extract_numbers, normalize_answer_text, normalize_question_text
from diff.reasons import reason_text, unchanged_summary, updated_summary
from knowledge.models import KnowledgeItem


DEPRECATED_KEYWORDS = [
    "取消",
    "停止",
    "终止",
    "作废",
    "失效",
    "到期",
    "不再执行",
    "不再提供",
    "停售",
    "下架",
    "替代",
    "以新政策为准",
    "原政策废止",
    "活动结束",
]


def has_deprecation_evidence(item: KnowledgeItem) -> bool:
    text = f"{item.question} {item.answer}"
    return any(keyword in text for keyword in DEPRECATED_KEYWORDS)


def has_required_fields(item: KnowledgeItem | None) -> bool:
    if item is None:
        return False
    return bool(item.question and item.answer)


def _bool_changed(old_item: KnowledgeItem, new_item: KnowledgeItem) -> bool:
    return old_item.need_confirm != new_item.need_confirm


def _numbers_changed(old_answer: str, new_answer: str) -> bool:
    old_numbers = extract_numbers(old_answer)
    new_numbers = extract_numbers(new_answer)
    return old_numbers != new_numbers


def detect_change(
    old_item: KnowledgeItem,
    new_item: KnowledgeItem,
    diff_id: str,
    match_method: MatchMethod,
    match_confidence: float,
) -> DiffResult:
    if not has_required_fields(old_item) or not has_required_fields(new_item):
        return DiffResult(
            diff_id=diff_id,
            old_item=old_item,
            new_item=new_item,
            change_type=ChangeType.REVIEW_REQUIRED,
            match_method=match_method,
            match_confidence=match_confidence,
            change_confidence=confidence.REVIEW_REQUIRED,
            overall_confidence=confidence.combine(match_confidence, confidence.REVIEW_REQUIRED),
            reason_code=ReviewReason.MISSING_REQUIRED_FIELD.value,
            reason_text=reason_text("MISSING_REQUIRED_FIELD"),
            review_reason=ReviewReason.MISSING_REQUIRED_FIELD,
            changed_fields=[],
            change_summary="缺少问题或回答，无法可靠比较。",
            needs_review=True,
            review_priority="P1",
        )

    if has_deprecation_evidence(new_item):
        return DiffResult(
            diff_id=diff_id,
            old_item=old_item,
            new_item=new_item,
            change_type=ChangeType.REVIEW_REQUIRED,
            match_method=match_method,
            match_confidence=match_confidence,
            change_confidence=confidence.REVIEW_REQUIRED,
            overall_confidence=confidence.combine(match_confidence, confidence.REVIEW_REQUIRED),
            reason_code="POSSIBLE_DEPRECATED",
            reason_text=reason_text("POSSIBLE_DEPRECATED"),
            review_reason=ReviewReason.POSSIBLE_DEPRECATED,
            changed_fields=["answer"],
            change_summary="新资料存在取消、终止、作废或到期等表达，需人工确认是否失效。",
            needs_review=True,
            review_priority="P1",
        )

    old_answer = normalize_answer_text(old_item.answer)
    new_answer = normalize_answer_text(new_item.answer)
    old_question = normalize_question_text(old_item.question)
    new_question = normalize_question_text(new_item.question)

    changed_fields: list[str] = []
    if old_question != new_question:
        changed_fields.append("question")

    if old_answer == new_answer and not _bool_changed(old_item, new_item):
        return DiffResult(
            diff_id=diff_id,
            old_item=old_item,
            new_item=new_item,
            change_type=ChangeType.UNCHANGED,
            match_method=match_method,
            match_confidence=match_confidence,
            change_confidence=confidence.UNCHANGED,
            overall_confidence=confidence.combine(match_confidence, confidence.UNCHANGED),
            reason_code="UNCHANGED",
            reason_text=reason_text("UNCHANGED"),
            changed_fields=changed_fields,
            change_summary=unchanged_summary(changed_fields),
            needs_review=False,
            review_priority="P3",
        )

    if _numbers_changed(old_item.answer, new_item.answer):
        changed_fields.append("number")
        if any(keyword in f"{old_item.question}{new_item.question}{old_item.category}{new_item.category}" for keyword in ["价格", "售价", "指导价", "多少钱"]):
            changed_fields.append("price")
            reason_code = "PRICE_CHANGED"
        else:
            reason_code = "NUMBER_CHANGED"
    else:
        reason_code = "ANSWER_CHANGED"

    if _bool_changed(old_item, new_item):
        changed_fields.append("need_confirm")

    if "answer" not in changed_fields:
        changed_fields.insert(0, "answer")

    return DiffResult(
        diff_id=diff_id,
        old_item=old_item,
        new_item=new_item,
        change_type=ChangeType.UPDATED,
        match_method=match_method,
        match_confidence=match_confidence,
        change_confidence=confidence.UPDATED,
        overall_confidence=confidence.combine(match_confidence, confidence.UPDATED),
        reason_code=reason_code,
        reason_text=reason_text(reason_code),
        changed_fields=changed_fields,
        change_summary=updated_summary(changed_fields),
        needs_review=True,
        review_priority="P1",
    )
