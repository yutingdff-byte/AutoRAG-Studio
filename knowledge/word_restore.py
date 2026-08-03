"""Restore Word knowledge material through the existing Generate Agent chain."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import Any

from knowledge.adapter import rag_to_knowledge
from knowledge.excel_restore import KnowledgeRestoreError
from knowledge.models import KnowledgeItem


def get_source_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "历史知识.docx"


def parse_document(file: Any) -> str:
    from parser.parser_factory import parse_file

    return parse_file(file)


def extract_material_facts(material: str):
    from agents.fact_agent import extract_facts

    return extract_facts(material)


def generate_material_rag(facts):
    from agents.rag_agent import generate_rag

    return generate_rag(facts)


StageLogger = Callable[[str, str, str], None]


def restore_word(file: Any, progress_callback: StageLogger | None = None) -> list[KnowledgeItem]:
    """Restore Word material by reusing Parser -> Fact Agent -> RAG Agent."""

    source_name = get_source_name(file)

    def log(stage: str, status: str, message: str) -> None:
        if progress_callback:
            progress_callback(stage, status, message)

    try:
        log("Parser", "开始", "解析Word资料")
        material = parse_document(file).strip()
        log("Parser", "成功", f"解析出 {len(material)} 个字符")
    except Exception as exc:
        log("Parser", "失败", str(exc))
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件格式。"
        ) from exc

    if not material:
        log("Parser", "失败", "解析结果为空")
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。文件解析结果为空。"
        )

    try:
        log("Facts", "开始", "调用现有Fact Agent恢复事实")
        facts = extract_material_facts(material)
        if not facts:
            raise ValueError("Fact Agent未返回有效结果")
        fact_count = len(facts.get("facts", [])) if isinstance(facts, dict) else 0
        log("Facts", "成功", f"恢复 {fact_count} 条事实")

        log("RAG", "开始", "调用现有RAG Agent生成知识")
        rag = generate_material_rag(facts)
        if not rag:
            raise ValueError("RAG Agent未返回有效结果")
        rag_count = len(rag.get("rag_knowledge", [])) if isinstance(rag, dict) else 0
        log("RAG", "成功", f"生成 {rag_count} 条RAG知识")

        log("Adapter", "开始", "转换为KnowledgeItem")
        items = rag_to_knowledge(rag, source_file=source_name)
        log("KnowledgeItem", "成功", f"转换 {len(items)} 条知识")
        return items

    except KnowledgeRestoreError:
        raise
    except Exception as exc:
        log("Restore", "失败", str(exc))
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件内容或模型配置。"
        ) from exc
