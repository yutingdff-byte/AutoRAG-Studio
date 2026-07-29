"""Restore Word knowledge material through the existing Generate Agent chain."""

from __future__ import annotations

from pathlib import Path
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


def restore_word(file: Any) -> list[KnowledgeItem]:
    """Restore Word material by reusing Parser -> Fact Agent -> RAG Agent."""

    source_name = get_source_name(file)

    try:
        material = parse_document(file).strip()
    except Exception as exc:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件格式。"
        ) from exc

    if not material:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。文件解析结果为空。"
        )

    try:
        facts = extract_material_facts(material)
        if not facts:
            raise ValueError("Fact Agent未返回有效结果")

        rag = generate_material_rag(facts)
        if not rag:
            raise ValueError("RAG Agent未返回有效结果")

        return rag_to_knowledge(rag, source_file=source_name)

    except KnowledgeRestoreError:
        raise
    except Exception as exc:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件内容或模型配置。"
        ) from exc
