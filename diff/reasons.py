"""Central reason codes and user-facing explanations for Diff results."""

from __future__ import annotations

from diff.models import ChangeType, ReviewReason


REVIEW_REASON_LABELS = {
    ReviewReason.NO_RELIABLE_MATCH: "未找到可靠对应知识",
    ReviewReason.OUT_OF_DETECTED_SCOPE: "不在本轮识别范围内",
    ReviewReason.AMBIGUOUS_MATCH: "存在多个可能对应项",
    ReviewReason.ONE_TO_MANY: "一条新知识可能对应多条历史知识",
    ReviewReason.MANY_TO_ONE: "多条新知识可能对应同一条历史知识",
    ReviewReason.MODEL_CONFLICT: "车型信息存在冲突",
    ReviewReason.TRIM_CONFLICT: "版本信息存在冲突",
    ReviewReason.CATEGORY_CONFLICT: "分类信息存在冲突",
    ReviewReason.ANSWER_CONFLICT: "新旧答案存在明显冲突",
    ReviewReason.POSSIBLE_DEPRECATED: "新资料存在可能失效证据",
    ReviewReason.LOW_CONFIDENCE: "匹配置信度不足",
    ReviewReason.DUPLICATE_KNOWLEDGE: "存在重复知识",
    ReviewReason.MISSING_REQUIRED_FIELD: "缺少必要字段",
}

CHANGE_TYPE_LABELS = {
    ChangeType.ADDED: "新增",
    ChangeType.UPDATED: "更新",
    ChangeType.UNCHANGED: "未变化",
    ChangeType.REVIEW_REQUIRED: "待确认",
}


def review_reason_label(reason: ReviewReason | None) -> str:
    if reason is None:
        return ""
    return REVIEW_REASON_LABELS.get(reason, reason.value)


def change_type_label(change_type: ChangeType) -> str:
    return CHANGE_TYPE_LABELS.get(change_type, change_type.value)


def reason_text(reason_code: str) -> str:
    return {
        "EXACT_MATCH": "问题、车型和分类高度一致，形成确定匹配。",
        "STRUCTURED_MATCH": "车型、主题和结构字段一致，形成规则匹配。",
        "NEW_KNOWLEDGE": "未在历史知识中找到可靠对应知识。",
        "UNCHANGED": "新旧答案核心内容一致，仅存在格式或问法差异。",
        "ANSWER_CHANGED": "问题主题和车型一致，但回答内容发生变化。",
        "PRICE_CHANGED": "问题主题和车型一致，但回答中的价格发生变化。",
        "NUMBER_CHANGED": "问题主题和车型一致，但回答中的数字信息发生变化。",
        "POSSIBLE_DEPRECATED": "新资料出现取消、终止、作废或到期等可能失效证据。",
        "OLD_NOT_IN_SCOPE": "本轮新增资料中未明显涉及该旧知识，旧知识默认继续保留。",
        "OLD_IN_SCOPE_UNMATCHED": "本轮资料可能涉及该知识范围，但未找到可靠对应内容，默认建议保留并人工确认。",
        "MISSING_REQUIRED_FIELD": "知识缺少问题或回答等必要字段，无法可靠比较。",
        "AMBIGUOUS_MATCH": "存在多个候选知识，系统无法可靠选择唯一对应项。",
        "NO_NEW_KNOWLEDGE": "本轮新增资料未生成有效知识，无法执行可靠差异分析。",
        "NO_KNOWLEDGE": "没有可比较的知识。",
    }.get(reason_code, reason_code)


def added_summary(item_category: str) -> str:
    return f"识别到一条新的{item_category or '知识'}。"


def unchanged_summary(changed_fields: list[str] | None = None) -> str:
    if changed_fields:
        return "核心答案未变化，仅问法或格式存在差异。"
    return "新旧知识内容一致。"


def updated_summary(changed_fields: list[str]) -> str:
    fields = "、".join(changed_fields) if changed_fields else "回答"
    return f"{fields}发生变化，建议人工复核后更新。"
