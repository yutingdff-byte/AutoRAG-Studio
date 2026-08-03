"""Unified restore entrypoint for Update mode history knowledge files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable
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
    logs: list[str] = field(default_factory=list)


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


ProgressCallback = Callable[[str, str, str, str], None]


def restore_file(file: Any, progress_callback: ProgressCallback | None = None) -> RestoreFileResult:
    file_name = get_file_name(file)
    file_type = get_file_type(file)
    logs: list[str] = []

    def log(stage: str, status: str, message: str) -> None:
        entry = f"{stage}｜{status}｜{message}"
        logs.append(entry)
        if progress_callback:
            progress_callback(file_name, stage, status, message)

    try:
        if file_type in {".xlsx", ".xls"}:
            log("Parser", "开始", "读取标准Excel知识库")
            items = restore_excel(file)
            log("KnowledgeItem", "成功", f"恢复 {len(items)} 条知识")
        elif file_type == ".docx":
            items = restore_word(file, progress_callback=log)
        else:
            raise KnowledgeRestoreError(
                f"暂不支持的历史知识格式：{file_type or '未知格式'}"
            )

        return RestoreFileResult(
            file_name=file_name,
            file_type=file_type,
            success=True,
            items=items,
            logs=logs,
        )

    except Exception as exc:
        log("Restore", "失败", str(exc))
        return RestoreFileResult(
            file_name=file_name,
            file_type=file_type,
            success=False,
            error=str(exc),
            logs=logs,
        )


def restore(files: Any, progress_callback: ProgressCallback | None = None) -> RestoreResult:
    if not files:
        return RestoreResult()

    if not isinstance(files, (list, tuple)):
        files = [files]

    result = RestoreResult()

    for file in files:
        file_result = restore_file(file, progress_callback=progress_callback)
        result.files.append(file_result)

        if file_result.success:
            result.items.extend(file_result.items)

    return result
