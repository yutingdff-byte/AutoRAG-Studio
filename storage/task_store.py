"""Minimal persisted Excel task store.

The MVP implementation uses a local filesystem backend so development and
tests do not require paid cloud resources. The module deliberately exposes a
small storage interface so an object-store backend can replace the local
implementation without changing Generate/Update page logic.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_RETENTION_DAYS = 7
TOKEN_BYTES = 24


class TaskStoreError(RuntimeError):
    """Raised when persisted task storage cannot complete an operation."""


class TaskNotFoundError(TaskStoreError):
    """Raised when a recovery token does not resolve to a task."""


class TaskExpiredError(TaskStoreError):
    """Raised when a task exists but is past its retention window."""


@dataclass(frozen=True)
class ExcelFileRecord:
    key: str
    file_name: str
    size: int
    sha256: str
    storage_path: str


@dataclass(frozen=True)
class PersistedTask:
    task_id: str
    mode: str
    created_at: str
    completed_at: str
    expires_at: str
    status: str
    app_version: str
    excel_files: list[ExcelFileRecord]

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mode": self.mode,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "app_version": self.app_version,
            "excel_files": [
                {
                    "key": item.key,
                    "file_name": item.file_name,
                    "size": item.size,
                    "sha256": item.sha256,
                }
                for item in self.excel_files
            ],
        }


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def get_retention_days() -> int:
    raw_value = os.getenv("TASK_STORE_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS))
    try:
        days = int(raw_value)
    except ValueError:
        return DEFAULT_RETENTION_DAYS
    return max(1, days)


def get_store_root() -> Path:
    return Path(os.getenv("TASK_STORE_LOCAL_DIR", "output/task_store"))


def _task_dir(task_id: str) -> Path:
    return get_store_root() / "tasks" / task_id


def _manifest_path(task_id: str) -> Path:
    return _task_dir(task_id) / "manifest.json"


def _index_dir() -> Path:
    return get_store_root() / "token_index"


def _safe_file_name(file_name: str) -> str:
    cleaned = Path(file_name).name.strip()
    return cleaned or "knowledge.xlsx"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _task_id() -> str:
    return secrets.token_urlsafe(12)


def generate_recovery_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _record_from_dict(data: dict[str, Any]) -> ExcelFileRecord:
    return ExcelFileRecord(
        key=str(data.get("key", "")),
        file_name=str(data.get("file_name", "")),
        size=int(data.get("size", 0)),
        sha256=str(data.get("sha256", "")),
        storage_path=str(data.get("storage_path", "")),
    )


def _task_from_manifest(manifest: dict[str, Any]) -> PersistedTask:
    return PersistedTask(
        task_id=str(manifest["task_id"]),
        mode=str(manifest["mode"]),
        created_at=str(manifest["created_at"]),
        completed_at=str(manifest["completed_at"]),
        expires_at=str(manifest["expires_at"]),
        status=str(manifest["status"]),
        app_version=str(manifest.get("app_version", "")),
        excel_files=[
            _record_from_dict(item)
            for item in manifest.get("excel_files", [])
            if isinstance(item, dict)
        ],
    )


def _ensure_not_expired(task: PersistedTask) -> None:
    if _parse_iso(task.expires_at) < _utc_now():
        raise TaskExpiredError("任务文件已过期，无法继续下载。")


def persist_excel_files(
    *,
    mode: str,
    excel_files: dict[str, dict[str, Any]],
    app_version: str = "",
    recovery_token: str | None = None,
    existing_task_id: str | None = None,
) -> tuple[PersistedTask, str]:
    """Persist final Excel bytes and return task metadata plus recovery token.

    ``excel_files`` uses the same in-memory structure already used by the UI:
    ``{"static": {"file_name": "...", "data": b"..."}}``.
    The operation is idempotent when ``existing_task_id`` and the same token are
    supplied; files are overwritten within that task directory, not duplicated.
    """

    if not excel_files:
        raise TaskStoreError("没有可保存的 Excel 文件。")

    token = recovery_token or generate_recovery_token()
    task_id = existing_task_id or _task_id()
    now = _utc_now()
    expires_at = now + timedelta(days=get_retention_days())
    task_directory = _task_dir(task_id)
    task_directory.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for key, payload in excel_files.items():
        data = payload.get("data")
        if not isinstance(data, bytes) or not data:
            raise TaskStoreError(f"{key} Excel 文件为空，无法持久化。")
        file_name = _safe_file_name(str(payload.get("file_name", f"{key}.xlsx")))
        storage_path = task_directory / file_name
        storage_path.write_bytes(data)
        records.append(
            {
                "key": key,
                "file_name": file_name,
                "size": len(data),
                "sha256": _sha256_bytes(data),
                "storage_path": str(storage_path),
            }
        )

    manifest = {
        "task_id": task_id,
        "mode": mode,
        "created_at": _iso(now),
        "completed_at": _iso(now),
        "expires_at": _iso(expires_at),
        "status": "completed",
        "app_version": app_version,
        "token_hash": _hash_token(token),
        "excel_files": records,
        "storage_backend": "local",
    }
    _write_json(_manifest_path(task_id), manifest)
    _write_json(_index_dir() / f"{_hash_token(token)}.json", {"task_id": task_id})
    return _task_from_manifest(manifest), token


def resolve_recovery_token(recovery_token: str) -> PersistedTask:
    token = (recovery_token or "").strip()
    if not token:
        raise TaskNotFoundError("恢复码无效。")
    index_path = _index_dir() / f"{_hash_token(token)}.json"
    if not index_path.exists():
        raise TaskNotFoundError("恢复码无效或任务不存在。")
    task_id = str(_read_json(index_path).get("task_id", ""))
    manifest_path = _manifest_path(task_id)
    if not manifest_path.exists():
        raise TaskNotFoundError("恢复码无效或任务不存在。")
    manifest = _read_json(manifest_path)
    if not secrets.compare_digest(str(manifest.get("token_hash", "")), _hash_token(token)):
        raise TaskNotFoundError("恢复码无效或任务不存在。")
    task = _task_from_manifest(manifest)
    _ensure_not_expired(task)
    return task


def load_excel_files(recovery_token: str) -> tuple[PersistedTask, dict[str, dict[str, Any]]]:
    task = resolve_recovery_token(recovery_token)
    files: dict[str, dict[str, Any]] = {}
    for record in task.excel_files:
        path = Path(record.storage_path)
        if not path.exists():
            raise TaskStoreError("已保存的 Excel 文件缺失，请重新生成或联系管理员。")
        data = path.read_bytes()
        if _sha256_bytes(data) != record.sha256:
            raise TaskStoreError("已保存的 Excel 文件校验失败，请重新生成或联系管理员。")
        files[record.key] = {
            "file_name": record.file_name,
            "data": data,
            "sha256": record.sha256,
            "size": record.size,
        }
    return task, files


def cleanup_expired_tasks(now: datetime | None = None) -> int:
    """Remove expired local task directories and token index entries."""

    current = now or _utc_now()
    removed = 0
    tasks_root = get_store_root() / "tasks"
    if not tasks_root.exists():
        return 0

    for manifest_path in tasks_root.glob("*/manifest.json"):
        try:
            manifest = _read_json(manifest_path)
            expires_at = _parse_iso(str(manifest.get("expires_at", "")))
        except Exception:
            continue
        if expires_at >= current:
            continue
        task_id = str(manifest.get("task_id", manifest_path.parent.name))
        token_hash = str(manifest.get("token_hash", ""))
        shutil.rmtree(_task_dir(task_id), ignore_errors=True)
        if token_hash:
            (_index_dir() / f"{token_hash}.json").unlink(missing_ok=True)
        removed += 1
    return removed

