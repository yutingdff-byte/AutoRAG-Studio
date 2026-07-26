"""Restore Word knowledge material through the existing Generate Agent chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agents.fact_agent import extract_facts
from agents.rag_agent import generate_rag
from knowledge.adapter import rag_to_knowledge
from knowledge.excel_restore import KnowledgeRestoreError
from knowledge.models import KnowledgeItem
from parser.parser_factory import parse_file


def get_source_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "历史知识.docx"


def restore_word(file: Any) -> list[KnowledgeItem]:
    """Restore Word material by reusing Parser -> Fact Agent -> RAG Agent."""

    source_name = get_source_name(file)

    try:
        material = parse_file(file).strip()
    except Exception as exc:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件格式。"
        ) from exc

    if not material:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。文件解析结果为空。"
        )

    try:
        facts = extract_facts(material)
        if not facts:
            raise ValueError("Fact Agent未返回有效结果")

        rag = generate_rag(facts)
        if not rag:
            raise ValueError("RAG Agent未返回有效结果")

        return rag_to_knowledge(rag, source_file=source_name)

    except KnowledgeRestoreError:
        raise
    except Exception as exc:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件内容或模型配置。"
        ) from exc
