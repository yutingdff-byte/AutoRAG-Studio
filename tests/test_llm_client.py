from types import SimpleNamespace

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
