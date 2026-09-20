from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from storage.task_store import (
    TaskExpiredError,
    TaskNotFoundError,
    cleanup_expired_tasks,
    load_excel_files,
    persist_excel_files,
)


def _excel_files() -> dict:
    return {
        "static": {
            "file_name": "车型配置知识库.xlsx",
            "data": b"static-excel",
        },
        "dynamic": {
            "file_name": "价格政策知识库.xlsx",
            "data": b"dynamic-excel",
        },
    }


def test_persist_and_recover_excel_files(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_STORE_LOCAL_DIR", str(tmp_path))

    task, token = persist_excel_files(
        mode="generate",
        excel_files=_excel_files(),
        app_version="test",
    )

    recovered_task, files = load_excel_files(token)

    assert recovered_task.task_id == task.task_id
    assert recovered_task.mode == "generate"
    assert files["static"]["data"] == b"static-excel"
    assert files["dynamic"]["data"] == b"dynamic-excel"
    assert files["static"]["sha256"]


def test_manifest_does_not_store_plain_recovery_token(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_STORE_LOCAL_DIR", str(tmp_path))

    task, token = persist_excel_files(
        mode="update",
        excel_files=_excel_files(),
        app_version="test",
    )

    manifest_path = tmp_path / "tasks" / task.task_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert token not in manifest_path.read_text(encoding="utf-8")
    assert manifest["token_hash"]
    assert "token" not in manifest


def test_invalid_recovery_token_cannot_access_files(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_STORE_LOCAL_DIR", str(tmp_path))
    persist_excel_files(
        mode="generate",
        excel_files=_excel_files(),
        app_version="test",
    )

    with pytest.raises(TaskNotFoundError):
        load_excel_files("not-a-real-token")


def test_existing_task_retry_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_STORE_LOCAL_DIR", str(tmp_path))
    task, token = persist_excel_files(
        mode="generate",
        excel_files=_excel_files(),
        app_version="test",
    )

    retried_task, retried_token = persist_excel_files(
        mode="generate",
        excel_files=_excel_files(),
        app_version="test",
        recovery_token=token,
        existing_task_id=task.task_id,
    )

    assert retried_task.task_id == task.task_id
    assert retried_token == token
    assert len(list((tmp_path / "tasks").iterdir())) == 1


def test_expired_task_is_rejected_and_cleaned(tmp_path, monkeypatch):
    monkeypatch.setenv("TASK_STORE_LOCAL_DIR", str(tmp_path))
    task, token = persist_excel_files(
        mode="generate",
        excel_files=_excel_files(),
        app_version="test",
    )
    manifest_path = tmp_path / "tasks" / task.task_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(TaskExpiredError):
        load_excel_files(token)

    assert cleanup_expired_tasks() == 1
    assert not (tmp_path / "tasks" / task.task_id).exists()

