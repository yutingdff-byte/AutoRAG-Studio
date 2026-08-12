from __future__ import annotations

import re

from utils.rag_quality import is_exportable_rag

from qc.models import RiskRouteResult, RouteDecision


HIGH_RISK_POLICY_KEYWORDS = [
    "价格",
    "售价",
    "指导价",
    "多少钱",
    "金融",
    "贷款",
    "分期",
    "免息",
    "0息",
    "贴息",
    "利率",
    "费率",
    "首付",
    "月供",
    "置换",
    "增换购",
    "以旧换新",
    "补贴",
    "优惠",
    "权益",
    "现金",
    "活动",
    "限时",
    "下订",
    "下定",
    "锁单",
    "截止",
    "有效期",
]

SCOPE_COMPLEXITY_KEYWORDS = [
    "全系",
    "部分车型",
    "指定版本",
    "全国",
    "部分地区",
    "门店",
    "地区",
    "仅限",
    "不含",
    "除外",
    "适用",
]

DYNAMIC_TYPES = {
    "dynamic",
    "price",
    "policy",
    "finance",
    "marketing",
}


def _question_text(item):
    questions = item.get("questions", item.get("question", ""))
    if isinstance(questions, list):
        return " ".join(str(question) for question in questions if question)
    return str(questions or "")


def _item_text(item):
    fields = [
        "brand",
        "model",
        "trim",
        "category",
        "knowledge_type",
        "module",
        "intent",
        "answer",
    ]
    return " ".join(str(item.get(field, "") or "") for field in fields) + " " + _question_text(item)


def _fact_refs(item):
    refs = item.get("fact_refs", [])
    if isinstance(refs, list):
        return [str(ref) for ref in refs if str(ref or "").strip()]
    if refs:
        return [str(refs)]
    return []


def _number_count(text):
    return len(re.findall(r"\d+(?:\.\d+)?\s*(?:万|元|%|公里|km|KM|年|月|日|期|次)?", text))


def route_qc_items(rag_items, rule_issue_item_ids=None):
    """Route only semantic-risk items to LLM QC."""
    rule_issue_item_ids = rule_issue_item_ids or set()
    result = RiskRouteResult()

    for item in rag_items:
        if not isinstance(item, dict):
            continue

        rag_id = item.get("rag_id", "")
        if rag_id in rule_issue_item_ids:
            result.decisions.append(
                RouteDecision(
                    rag_id=rag_id,
                    route="rule_issue",
                    reasons=["RULE_ISSUE"],
                )
            )
            continue

        if not is_exportable_rag(item):
            result.decisions.append(
                RouteDecision(
                    rag_id=rag_id,
                    route="rule_issue",
                    reasons=["NON_EXPORTABLE"],
                )
            )
            continue

        text = _item_text(item)
        reasons = []

        if str(item.get("knowledge_type", "")).lower() in DYNAMIC_TYPES:
            reasons.append("DYNAMIC_KNOWLEDGE")

        if any(keyword in text for keyword in HIGH_RISK_POLICY_KEYWORDS):
            reasons.append("POLICY_OR_PRICE_SIGNAL")

        if len(_fact_refs(item)) > 1:
            reasons.append("MULTI_FACT")

        if _number_count(str(item.get("answer", "") or "")) >= 3:
            reasons.append("MULTI_NUMERIC_CONDITION")

        if any(keyword in text for keyword in SCOPE_COMPLEXITY_KEYWORDS):
            reasons.append("SCOPE_COMPLEXITY")

        if reasons:
            result.routed_items.append(item)
            result.decisions.append(
                RouteDecision(
                    rag_id=rag_id,
                    route="llm",
                    reasons=sorted(set(reasons)),
                )
            )
        else:
            result.passed_items.append(item)
            result.decisions.append(
                RouteDecision(
                    rag_id=rag_id,
                    route="rule_pass",
                    reasons=["LOW_RISK_STATIC_SINGLE_FACT"],
                )
            )

    return result
