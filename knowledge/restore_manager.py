"""Unified restore entrypoint for Update mode history knowledge files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from knowledge.excel_restore import KnowledgeRestoreError, restore_excel
from knowledge.models import KnowledgeItem
from knowledge.word_restore import restore_word


@dataclass(slots=True)
class RestoreFileResult:
    file_name: str
    file_type: str
    success: bool
    items: list[KnowledgeItem] = field(default_factory=list)
    error: str = ""


@dataclass(slots=True)
class RestoreResult:
    items: list[KnowledgeItem] = field(default_factory=list)
    files: list[RestoreFileResult] = field(default_factory=list)

    @property
    def restored_count(self) -> int:
        return len(self.items)

    @property
    def model_count(self) -> int:
        models = {
            item.model
            for item in self.items
            if item.model
        }
        return len(models)

    @property
    def need_confirm_count(self) -> int:
        return sum(1 for item in self.items if item.need_confirm)


def get_file_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "uploaded_file"


def get_file_type(file: Any) -> str:
    return Path(get_file_name(file)).suffix.lower()


def restore_file(file: Any) -> RestoreFileResult:
    file_name = get_file_name(file)
    file_type = get_file_type(file)

    try:
        if file_type in {".xlsx", ".xls"}:
            items = restore_excel(file)
        elif file_type == ".docx":
            items = restore_word(file)
        else:
            raise KnowledgeRestoreError(
                f"暂不支持的历史知识格式：{file_type or '未知格式'}"
            )

        return RestoreFileResult(
            file_name=file_name,
            file_type=file_type,
            success=True,
            items=items,
        )

    except Exception as exc:
        return RestoreFileResult(
            file_name=file_name,
            file_type=file_type,
            success=False,
            error=str(exc),
        )


def restore(files: Any) -> RestoreResult:
    if not files:
        return RestoreResult()

    if not isinstance(files, (list, tuple)):
        files = [files]

    result = RestoreResult()

    for file in files:
        file_result = restore_file(file)
        result.files.append(file_result)

        if file_result.success:
            result.items.extend(file_result.items)

    return result
