from types import SimpleNamespace

import agents.llm_client as llm_client
from agents.llm_client import describe_llm_exception


def test_describe_llm_exception_reports_diagnostics_without_api_key():
    request = SimpleNamespace(url="https://api.deepseek.com/chat/completions")
    cause = ConnectionError("socket blocked")
    exc = RuntimeError("Connection error.")
    exc.__cause__ = cause
    exc.request = request

    diagnostics = describe_llm_exception(exc, "deepseek-v4-flash")

    assert diagnostics["exception_class"] == "builtins.RuntimeError"
    assert diagnostics["exception_message"] == "Connection error."
    assert diagnostics["cause_class"] == "builtins.ConnectionError"
    assert diagnostics["cause_message"] == "socket blocked"
    assert diagnostics["request_endpoint"] == "https://api.deepseek.com/chat/completions"
    assert diagnostics["model"] == "deepseek-v4-flash"
    assert "api" not in diagnostics


def test_get_client_uses_bounded_timeout_without_implicit_retries(monkeypatch):
    captured = {}

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return object()

    def fake_get_config(name, default=None):
        return {
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
            "LLM_CONNECT_TIMEOUT_SECONDS": "10",
            "LLM_READ_TIMEOUT_SECONDS": "600",
            "LLM_MAX_RETRIES": "0",
        }.get(name, default)

    monkeypatch.setattr(llm_client, "OpenAI", fake_openai)
    monkeypatch.setattr(llm_client, "get_config", fake_get_config)
    monkeypatch.setattr(llm_client, "require_config", lambda *args: "test-key")

    llm_client.get_client()

    assert captured["max_retries"] == 0
    assert captured["timeout"].connect == 10
    assert captured["timeout"].read == 600


def test_call_llm_streams_long_inputs_without_changing_content(monkeypatch):
    calls = []
    chunks = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content='{"facts":'),
                    finish_reason=None,
                )
            ]
        ),
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="[]}"),
                    finish_reason="stop",
                )
            ]
        ),
    ]

    class FakeCompletions:
        def create(self, **kwargs):
            calls.append(kwargs)
            return iter(chunks)

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=FakeCompletions()
        )
    )
    monkeypatch.setattr(llm_client, "get_client", lambda: fake_client)
    monkeypatch.setattr(
        llm_client,
        "get_config",
        lambda name, default=None: {
            "DEEPSEEK_MODEL": "deepseek-v4-flash",
            "LLM_STREAM_THRESHOLD_CHARS": "10",
        }.get(name, default),
    )

    result = llm_client.call_llm("system", "long input text")

    assert result == '{"facts":[]}'
    assert calls[0]["stream"] is True
