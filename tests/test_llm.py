"""Codex-Vertrag, Kostenabgrenzung und Fehler ohne Netzwerk oder ChatGPT-Verbrauch."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from openai_codex import ApprovalMode, ExternalMessage, Sandbox
from openai_codex.types import GetAccountResponse, ThreadTokenUsage, TurnStatus

from ausschreibungen.analysis import analyze_run, estimate_cost, extract
from ausschreibungen.llm import (
    MAX_MODEL_INPUT_BYTES,
    CodexModel,
    ModelError,
    object_schema,
    runtime_overrides,
)
from tests.test_analysis import NOW, PROFILE, lot, proposal, saved_run, xml


class Data:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        return self.value


def response(answer: Any, **changes: Any) -> SimpleNamespace:
    breakdown = {
        "inputTokens": 1000,
        "cachedInputTokens": 100,
        "outputTokens": 200,
        "reasoningOutputTokens": 50,
        "totalTokens": 1200,
    }
    return SimpleNamespace(
        **(
            {
                "id": "response-id",
                "status": TurnStatus.completed,
                "final_response": json.dumps(answer),
                "error": None,
                "usage": ThreadTokenUsage(last=breakdown, total=breakdown),
                "items": [Data({"type": "agentMessage", "text": json.dumps(answer)})],
            }
            | changes
        )
    )


def transport(
    monkeypatch: pytest.MonkeyPatch, responses: list[Any], *, auth: str | None = "chatgpt"
) -> dict[str, list[Any]]:
    log: dict[str, list[Any]] = {"configs": [], "threads": [], "runs": []}

    class FakeCodex:
        def __init__(self, config: Any) -> None:
            log["configs"].append(config)

        def __enter__(self) -> "FakeCodex":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def account(self) -> GetAccountResponse:
            account = {"type": auth}
            if auth == "chatgpt":
                account.update(email="not-to-be-stored@example.org", planType="free")
            return GetAccountResponse(account=account if auth else None, requiresOpenaiAuth=True)

        def models(self) -> SimpleNamespace:
            return SimpleNamespace(data=[SimpleNamespace(model="gpt-6.1-sol", is_default=True)])

        def thread_start(self, **kwargs: Any) -> "FakeCodex":
            log["threads"].append(kwargs)
            return self

        def run(self, message: ExternalMessage, **kwargs: Any) -> Any:
            index = len(log["runs"])
            log["runs"].append((message, kwargs))
            result = responses[index]
            if isinstance(result, Exception):
                raise result
            return result

    monkeypatch.setattr("ausschreibungen.llm.Codex", FakeCodex)
    # Keine echte persönliche Konfiguration beim isolierten Vertragstest auslesen.
    monkeypatch.setattr(
        "ausschreibungen.llm.runtime_overrides", lambda: ('forced_login_method="chatgpt"',)
    )
    return log


def test_t4_10_usage_and_no_api_cost_are_traceable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer = proposal(extract(xml(lot()), "100-2026", now=NOW))
    log = transport(
        monkeypatch, [response(answer), response({"facts": [], "fit": True, "checkpoints": []})]
    )
    monkeypatch.setenv("OPENAI_API_KEY", "secret-sentinel")
    run = saved_run(tmp_path, xml(lot()))
    output = analyze_run(run, PROFILE, now=NOW)
    result = json.loads((output / "analysis.json").read_text("utf-8"))
    assert result["status"] == "complete"
    assert result["cost"]["additional_api_cost_usd"] == 0
    assert result["cost"]["billing"] == "chatgpt_plan"
    assert result["cost"]["tokens"] == {"input_tokens": 2000, "output_tokens": 400}
    assert result["cost"]["measured"] is True
    assert len(log["threads"]) == len(log["runs"]) == 2
    for config in log["configs"]:
        assert config.env["OPENAI_API_KEY"] == config.env["CODEX_API_KEY"] == ""
        assert 'forced_login_method="chatgpt"' in config.config_overrides
    for thread in log["threads"]:
        assert thread["sandbox"] == Sandbox.read_only
        assert thread["approval_mode"] == ApprovalMode.deny_all
        assert thread["model_provider"] == "openai"
        assert thread["ephemeral"] is True
        assert thread["model"] == "gpt-6.1-sol"
    for message, options in log["runs"]:
        assert isinstance(message, ExternalMessage)
        assert message.tool_name == "stored_ted_notice"
        assert (
            json.loads(message.content)["company_profile"] == result["profile"]["company_profile"]
        )
        assert options["output_schema"]["additionalProperties"] is False
    assert len(list((output / "model").glob("*.response.json"))) == 2
    for path in output.rglob("*"):
        if path.is_file():
            assert b"secret-sentinel" not in path.read_bytes()
            assert b"not-to-be-stored@example.org" not in path.read_bytes()


@pytest.mark.parametrize("auth", [None, "apiKey", "amazonBedrock"])
def test_other_auth_never_runs_a_model_or_api_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, auth: str | None
) -> None:
    log = transport(monkeypatch, [], auth=auth)
    client = CodexModel("default", tmp_path)
    with pytest.raises(ModelError, match="ChatGPT-Anmeldung"):
        client("instructions", {}, object_schema())
    assert log["runs"] == log["threads"] == []
    assert client.calls[0]["status"] == "error"


@pytest.mark.parametrize(
    "result",
    [
        response({}, status=TurnStatus.failed),
        response({}, final_response=None),
        response({}, final_response="not-json"),
        response({"unexpected": 1}),
        response({}, items=[Data({"type": "commandExecution"})]),
        OSError("offline"),
    ],
)
def test_t4_07_bad_response_and_tool_actions_are_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, result: Any
) -> None:
    log = transport(monkeypatch, [result])
    client = CodexModel("default", tmp_path)
    with pytest.raises(ModelError):
        client("instructions", {}, object_schema())
    assert client.calls[0]["status"] == "error"
    assert len(log["runs"]) == 1


def test_missing_usage_is_unknown_while_api_path_remains_disabled() -> None:
    cost = estimate_cost([{"status": "error"}])
    assert cost["additional_api_cost_usd"] == 0
    assert cost["measured"] is False
    assert cost["unknown_usage_calls"] == 1


def test_process_only_tool_locks_preserve_personal_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Nur den Leseort substituieren; CODEX_HOME wird nicht verändert.
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setattr("ausschreibungen.llm.Path.home", lambda: tmp_path)
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    original = (
        '[mcp_servers.node_repl]\ncommand="do-not-run"\n[plugins."browser@openai"]\nenabled=true\n'
    )
    (config_dir / "config.toml").write_text(original)
    settings = runtime_overrides()
    for required in (
        'forced_login_method="chatgpt"',
        "features.shell_tool=false",
        "features.hooks=false",
        'web_search="disabled"',
        "mcp_servers.node_repl.enabled=false",
        "plugins.browser@openai.enabled=false",
        f"tool_output_token_limit={MAX_MODEL_INPUT_BYTES}",
    ):
        assert required in settings
    assert (config_dir / "config.toml").read_text() == original


def test_oversized_input_is_an_error_before_model_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log = transport(monkeypatch, [])
    client = CodexModel("default", tmp_path)
    with pytest.raises(ModelError, match="ungekürzte Modellübergabe zu groß"):
        client("instructions", {"text": "ä" * MAX_MODEL_INPUT_BYTES}, object_schema())
    assert log["configs"] == log["threads"] == log["runs"] == []
    assert client.calls[0]["status"] == "error"
