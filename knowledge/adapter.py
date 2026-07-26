"""Adapters that convert generated or restored data into KnowledgeItem objects."""

from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha1
from typing import Any

from knowledge.models import KnowledgeItem, normalize_question


PRICE_CATEGORIES = {"价格", "售价", "指导价", "价位", "价格信息"}
FINANCE_CATEGORIES = {"金融", "金融政策", "免息", "分期", "贷款"}
POLICY_CATEGORIES = {"政策", "权益", "购车权益", "优惠", "补贴", "活动", "价格政策"}
PRODUCT_CATEGORIES = {
    "配置",
    "车型信息",
    "空间",
    "动力",
    "续航",
    "补能",
    "智驾",
    "安全",
    "舒适",
    "质保",
    "道路救援",
}


def normalize_internal_knowledge_type(value: str | None, category: str | None = None, module: str | None = None) -> str:
    """Map source-specific knowledge types into V0.8 internal buckets."""

    source_value = str(value or "").strip().lower()
    if source_value in {"product", "price", "policy", "store", "marketing", "finance", "general"}:
        return source_value

    text = f"{category or ''} {module or ''}"
    if any(keyword in text for keyword in FINANCE_CATEGORIES):
        return "finance"
    if any(keyword in text for keyword in PRICE_CATEGORIES):
        return "price"
    if any(keyword in text for keyword in POLICY_CATEGORIES):
        return "policy"
    if any(keyword in text for keyword in PRODUCT_CATEGORIES):
        return "product"

    if source_value == "dynamic":
        return "policy"
    if source_value == "static":
        return "product"

    return "general"


def build_knowledge_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    digest = sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def first_question(item: dict[str, Any]) -> str:
    questions = item.get("questions")
    if isinstance(questions, list):
        return str(next((question for question in questions if question), ""))
    return str(questions or item.get("question") or "")


def as_bool_need_confirm(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip() in {"是", "true", "True", "1", "yes", "需要确认"}


def rag_item_to_knowledge(item: dict[str, Any], source_file: str | None = None, index: int = 0) -> KnowledgeItem:
    question = first_question(item)
    source_files = item.get("source_files") or item.get("source_file") or []
    if isinstance(source_files, str):
        source_files = [source_files]
    if source_file and source_file not in source_files:
        source_files = [*source_files, source_file]

    category = str(item.get("category") or "")
    module = item.get("module")

    return KnowledgeItem(
        knowledge_id=str(
            item.get("knowledge_id")
            or item.get("rag_id")
            or build_knowledge_id("RAG", index, question, item.get("answer"), category)
        ),
        question=question,
        normalized_question=normalize_question(question),
        answer=str(item.get("answer") or ""),
        category=category,
        module=str(module) if module else None,
        brand=item.get("brand"),
        model=item.get("model"),
        trim=item.get("trim"),
        knowledge_type=normalize_internal_knowledge_type(
            item.get("knowledge_type"),
            category,
            str(module or ""),
        ),
        answer_type=item.get("answer_type"),
        need_confirm=as_bool_need_confirm(item.get("need_confirm")),
        fact_refs=list(item.get("fact_refs") or []),
        source_files=list(source_files),
        metadata={
            "source": "rag",
            "source_knowledge_type": item.get("knowledge_type"),
            "review_type": item.get("review_type"),
            "exportable": item.get("exportable"),
        },
    )


def rag_to_knowledge(rag_data: dict[str, Any], source_file: str | None = None) -> list[KnowledgeItem]:
    return [
        rag_item_to_knowledge(item, source_file=source_file, index=index)
        for index, item in enumerate(rag_data.get("rag_knowledge", []), start=1)
        if isinstance(item, dict)
    ]


def excel_row_to_knowledge(row: dict[str, Any], source_file: str, index: int) -> KnowledgeItem:
    question = str(row.get("问题") or "")
    category = str(row.get("分类") or "")

    return KnowledgeItem(
        knowledge_id=build_knowledge_id("XLSX", source_file, index, question, row.get("回答"), category),
        question=question,
        normalized_question=normalize_question(question),
        answer=str(row.get("回答") or ""),
        category=category,
        module=None,
        brand=str(row.get("品牌") or "") or None,
        model=str(row.get("车型") or "") or None,
        trim=str(row.get("版本") or "") or None,
        knowledge_type=normalize_internal_knowledge_type(None, category, None),
        answer_type="restored",
        need_confirm=False,
        fact_refs=[],
        source_files=[source_file],
        metadata={
            "source": "excel",
            "row_number": index + 1,
        },
    )


def knowledge_to_preview_rows(items: Iterable[KnowledgeItem], limit: int = 50) -> list[dict[str, Any]]:
    rows = []
    for item in list(items)[:limit]:
        rows.append(
            {
                "问题": item.question,
                "回答": item.answer,
                "分类": item.category,
                "车型": item.model or "",
                "版本": item.trim or "",
                "来源": "、".join(item.source_files),
            }
        )
    return rows
