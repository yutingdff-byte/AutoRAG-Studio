"""Restore AutoRAG standard Excel exports into KnowledgeItem objects."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from knowledge.adapter import excel_row_to_knowledge
from knowledge.models import KnowledgeItem


STANDARD_COLUMNS = ["车型", "版本", "问题", "回答", "分类"]


class KnowledgeRestoreError(ValueError):
    """Raised when a history knowledge file cannot be restored safely."""


def get_source_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "历史知识.xlsx"


def restore_excel(file: Any) -> list[KnowledgeItem]:
    """Restore a standard AutoRAG exported Excel file without invoking Agents."""

    source_name = get_source_name(file)

    try:
        dataframe = pd.read_excel(file)
    except Exception as exc:
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件格式。"
        ) from exc

    columns = [str(column).strip() for column in dataframe.columns]
    missing_columns = [
        column
        for column in STANDARD_COLUMNS
        if column not in columns
    ]

    if missing_columns:
        raise KnowledgeRestoreError(
            "不是标准知识库，请检查导出的Excel格式。"
            f"缺少字段：{', '.join(missing_columns)}"
        )

    restored_items: list[KnowledgeItem] = []

    for index, row in dataframe.iterrows():
        row_data = {
            column: "" if pd.isna(row[column]) else row[column]
            for column in STANDARD_COLUMNS
        }

        if not str(row_data["问题"]).strip() and not str(row_data["回答"]).strip():
            continue

        restored_items.append(
            excel_row_to_knowledge(
                row_data,
                source_name,
                int(index) + 1,
            )
        )

    return restored_items
