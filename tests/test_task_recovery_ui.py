from __future__ import annotations

from ui import task_recovery


def test_recovery_scripts_use_cookie_not_url_query(monkeypatch):
    rendered: list[str] = []

    def fake_html(body: str, **kwargs):
        rendered.append(body)

    monkeypatch.setattr(task_recovery.components, "html", fake_html)

    task_recovery.install_auto_restore_script()
    task_recovery.remember_recovery_token("sample-token")
    task_recovery.clear_recovery_token()

    combined = "\n".join(rendered)
    assert "document.cookie" in combined
    assert "Max-Age" in combined
    assert "window.parent.location" not in combined
    assert "restore_token" not in combined

