"""Unified restore entrypoint for Update mode history knowledge files."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from knowledge.excel_restore import KnowledgeRestoreError, restore_excel
from knowledge.models import KnowledgeItem
from knowledge.standard_word_restore import (
    FORMAT_ID as SYSTEM_STANDARD_WORD_V1,
    PARSER_VERSION as SYSTEM_STANDARD_WORD_V1_PARSER_VERSION,
    restore_report_to_logs,
    restore_system_standard_word_v1,
)
from knowledge.word_format_detector import detect_word_format
from knowledge.word_restore import restore_word
from knowledge.word_fast_restore import FAST_RESTORE_STRATEGY_VERSION
from utils.config import get_config


@dataclass(slots=True)
class RestoreFileResult:
    file_name: str
    file_type: str
    success: bool
    items: list[KnowledgeItem] = field(default_factory=list)
    error: str = ""
    logs: list[str] = field(default_factory=list)
    file_hash: str = ""
    elapsed_seconds: float = 0.0
    report: dict[str, Any] = field(default_factory=dict)


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


def get_file_bytes(file: Any) -> bytes:
    if hasattr(file, "getvalue"):
        return file.getvalue()

    if isinstance(file, (str, Path)):
        return Path(file).read_bytes()

    if hasattr(file, "read"):
        position = file.tell() if hasattr(file, "tell") else None
        content = file.read()
        if position is not None and hasattr(file, "seek"):
            file.seek(position)
        if isinstance(content, str):
            return content.encode("utf-8")
        return content

    return b""


def get_file_fingerprint(file: Any) -> str:
    file_name = get_file_name(file)
    file_type = get_file_type(file)
    content = get_file_bytes(file)
    digest = sha256(content).hexdigest()
    return f"{file_name}:{file_type}:{len(content)}:{digest}"


def get_restore_cache_key(file: Any, deep_restore: bool = False) -> str:
    if get_file_type(file) == ".docx":
        detected = detect_word_format(file)
        if detected.format_id == SYSTEM_STANDARD_WORD_V1:
            return (
                f"{get_file_fingerprint(file)}:"
                f"{SYSTEM_STANDARD_WORD_V1}:"
                f"{SYSTEM_STANDARD_WORD_V1_PARSER_VERSION}"
            )

    model_config = "|".join(
        [
            get_config("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            get_config("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        ]
    )
    return (
        f"{get_file_fingerprint(file)}:"
        f"{FAST_RESTORE_STRATEGY_VERSION}:"
        f"deep={int(deep_restore)}:"
        f"{sha256(model_config.encode('utf-8')).hexdigest()[:12]}"
    )


ProgressCallback = Callable[[str, str, str, str], None]


def restore_file(
    file: Any,
    progress_callback: ProgressCallback | None = None,
    deep_restore: bool = False,
) -> RestoreFileResult:
    file_name = get_file_name(file)
    file_type = get_file_type(file)
    file_hash = get_file_fingerprint(file)
    started_at = perf_counter()
    logs: list[str] = []
    report: dict[str, Any] = {}

    def log(stage: str, status: str, message: str) -> None:
        elapsed = perf_counter() - started_at
        entry = f"{stage}｜{status}｜{message}｜{elapsed:.2f}s"
        logs.append(entry)
        if progress_callback:
            progress_callback(file_name, stage, status, f"{message}｜{elapsed:.2f}s")

    try:
        if file_type in {".xlsx", ".xls"}:
            log("Parser", "开始", "读取标准Excel知识库")
            items = restore_excel(file)
            log("KnowledgeItem", "成功", f"恢复 {len(items)} 条知识")
        elif file_type == ".docx":
            detected = detect_word_format(file)
            if detected.format_id == SYSTEM_STANDARD_WORD_V1:
                log(
                    "Format Detector",
                    "成功",
                    "已识别为系统标准历史知识格式",
                )
                log(
                    "Standard Restore",
                    "开始",
                    "正在快速恢复，无需模型处理",
                )
                standard_result = restore_system_standard_word_v1(file)
                items = standard_result.items
                report = asdict(standard_result.report)
                for entry in restore_report_to_logs(standard_result.report):
                    logs.append(entry)
                    if progress_callback:
                        progress_callback(file_name, "Standard Restore", "报告", entry)
            else:
                items = restore_word(file, progress_callback=log, deep_restore=deep_restore)
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
            file_hash=file_hash,
            elapsed_seconds=perf_counter() - started_at,
            report=report,
        )

    except Exception as exc:
        log("Restore", "失败", str(exc))
        return RestoreFileResult(
            file_name=file_name,
            file_type=file_type,
            success=False,
            error=str(exc),
            logs=logs,
            file_hash=file_hash,
            elapsed_seconds=perf_counter() - started_at,
            report=report,
        )


def restore(
    files: Any,
    progress_callback: ProgressCallback | None = None,
    deep_restore: bool = False,
) -> RestoreResult:
    if not files:
        return RestoreResult()

    if not isinstance(files, (list, tuple)):
        files = [files]

    result = RestoreResult()

    for file in files:
        file_result = restore_file(
            file,
            progress_callback=progress_callback,
            deep_restore=deep_restore,
        )
        result.files.append(file_result)

        if file_result.success:
            result.items.extend(file_result.items)

    return result
