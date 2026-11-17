"""Codex über das bestehende ChatGPT-Konto; kein API-Schlüssel und kein API-Fallback."""

import json
import os
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from openai_codex import ApprovalMode, Codex, CodexConfig, CodexError, ExternalMessage, Sandbox

from ausschreibungen.research import save_json

MAX_MODEL_INPUT_BYTES = 300_000


class ModelError(Exception):
    """Keine erfolgreiche Analyse ohne verwertbare Modellantwort."""


def validate(value: Any, schema: dict[str, Any]) -> None:
    """Prüft die hier verwendete kleine JSON-Schema-Teilmenge auch lokal."""
    types = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int}
    if type(value) is not types[schema["type"]]:
        raise ModelError("KI-Antwort hat einen falschen Datentyp.")
    if "enum" in schema and value not in schema["enum"]:
        raise ModelError("KI-Antwort enthält einen unbekannten Wert.")
    if isinstance(value, str) and not value.strip():
        raise ModelError("KI-Antwort enthält einen leeren Pflichttext.")
    if isinstance(value, dict):
        if set(value) != set(schema["properties"]):
            raise ModelError("KI-Antwort ist unvollständig oder enthält zusätzliche Felder.")
        for key, item in value.items():
            validate(item, schema["properties"][key])
    if isinstance(value, list):
        for item in value:
            validate(item, schema["items"])


def object_schema(**properties: Any) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def runtime_overrides() -> tuple[str, ...]:
    """Nur für diesen Prozess; persönliche Codex-Konfiguration wird nicht geändert."""
    settings: dict[str, Any] = {
        "forced_login_method": "chatgpt",
        "model_provider": "openai",
        "chatgpt_base_url": "https://chatgpt.com/backend-api/",
        "features.shell_tool": False,
        "features.view_image": False,
        "features.multi_agent": False,
        "agents.enabled": False,
        "features.hooks": False,
        "features.memories": False,
        "features.apps": False,
        "features.remote_plugin": False,
        "web_search": "disabled",
        "project_doc_max_bytes": 0,
        "apps._default.enabled": False,
        # ExternalMessage ist ein Tool-Ergebnis. Der übliche History-Grenzwert
        # würde lange Bekanntmachungen mitten im Text kürzen.
        "tool_output_token_limit": MAX_MODEL_INPUT_BYTES,
        "skills.include_instructions": False,
        "skills.bundled.enabled": False,
    }
    # Tabellen werden beim Konfigurations-Merge kombiniert. Daher vorhandene
    # MCP-/Plugin-Einträge einzeln sperren, statt eine leere Tabelle zu übergeben.
    config_dir = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    path = config_dir / "config.toml"
    if path.is_file():
        config = tomllib.loads(path.read_text("utf-8"))
        for section in ("mcp_servers", "plugins", "apps"):
            for key in config.get(section, {}):
                if key != "_default":
                    if "." in key:
                        raise ModelError(
                            "Codex-Konfiguration enthält einen nicht isolierbaren Toolnamen."
                        )
                    settings[f"{section}.{key}.enabled"] = False
    return tuple(f"{key}={json.dumps(value)}" for key, value in settings.items())


class CodexModel:
    def __init__(self, model: str, directory: Path) -> None:
        self.model = model
        self.directory = directory
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, instructions: str, payload: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        self.directory.mkdir(parents=True, exist_ok=True)
        stem = f"call-{len(self.calls) + 1}"
        call: dict[str, Any] = {
            "request_file": stem + ".request.json",
            "status": "pending",
            "provider": "codex_chatgpt",
            "billing": "chatgpt_plan",
        }
        self.calls.append(call)
        save_json(
            self.directory / call["request_file"],
            {
                "instructions": instructions,
                "input": payload,
                "schema": schema,
                "requested_model": self.model,
                "auth_required": "chatgpt",
            },
        )
        try:
            payload_text = json.dumps(payload, ensure_ascii=False)
            call["input_bytes"] = len(payload_text.encode("utf-8"))
            call["tool_output_token_limit"] = MAX_MODEL_INPUT_BYTES
            if call["input_bytes"] > MAX_MODEL_INPUT_BYTES:
                raise ModelError(
                    "Bekanntmachung ist für eine ungekürzte Modellübergabe zu groß. "
                    "Keine Teilanalyse als vollständiges Ergebnis ausgegeben."
                )
            with tempfile.TemporaryDirectory(prefix="tender-analysis-") as workspace:
                config = CodexConfig(
                    # Der Desktop-Client kann zusätzliche lokale Transports unterstützen.
                    codex_bin=shutil.which("codex"),
                    cwd=workspace,
                    config_overrides=runtime_overrides(),
                    env={"OPENAI_API_KEY": "", "CODEX_API_KEY": "", "CODEX_ACCESS_TOKEN": ""},
                )
                with Codex(config) as client:
                    account = client.account().account
                    if account is None or account.root.type != "chatgpt":
                        raise ModelError(
                            "Codex benötigt ChatGPT-Anmeldung: codex login ausführen. "
                            "API-Anmeldung ist für diese Anwendung gesperrt."
                        )
                    call["auth"] = "chatgpt"
                    call["plan"] = account.root.plan_type.value
                    resolved = self.model
                    if resolved == "default":
                        models = client.models().data
                        resolved = next(m.model for m in models if m.is_default)
                    call["model"] = resolved
                    thread = client.thread_start(
                        model=resolved,
                        model_provider="openai",
                        cwd=workspace,
                        ephemeral=True,
                        sandbox=Sandbox.read_only,
                        approval_mode=ApprovalMode.deny_all,
                        developer_instructions=instructions
                        + "\nAntworte nur im vorgegebenen JSON-Schema. "
                        "Verwende keine Werkzeuge. Analysiere ausschließlich "
                        "die übergebenen Daten.",
                    )
                    response = thread.run(
                        ExternalMessage(
                            tool_name="stored_ted_notice",
                            content=payload_text,
                        ),
                        output_schema=schema,
                    )
                    raw = {
                        "id": response.id,
                        "status": response.status.value,
                        "final_response": response.final_response,
                        "error": response.error.model_dump(mode="json") if response.error else None,
                        "items": [item.model_dump(mode="json") for item in response.items],
                        "usage": response.usage.model_dump(mode="json") if response.usage else None,
                    }
                    call["response_file"] = stem + ".response.json"
                    save_json(self.directory / call["response_file"], raw)
                    if response.usage:
                        call["usage"] = response.usage.total.model_dump(mode="json")
                    # Werkzeugaufrufe gelten auch bei formal gültiger Endantwort nicht als Erfolg.
                    allowed_items = {
                        "agentMessage",
                        "reasoning",
                        "userMessage",
                        "functionCallOutput",
                    }
                    if any(item.get("type") not in allowed_items for item in raw["items"]):
                        raise ModelError("Codex hat eine unerwartete Werkzeugaktion ausgeführt.")
                    if response.status.value != "completed" or not response.final_response:
                        raise ModelError(
                            "Codex-Auswertung fehlgeschlagen oder nicht abgeschlossen."
                        )
                    result = json.loads(response.final_response)
                    validate(result, schema)
                    call["status"] = "ok"
                    return result
        except ModelError as error:
            call.update(status="error", error=str(error))
            raise
        except (CodexError, OSError, ValueError, TypeError, AttributeError, StopIteration) as error:
            call.update(
                status="error",
                error=f"Codex-/Antwortverarbeitung fehlgeschlagen ({type(error).__name__}).",
            )
            raise ModelError(call["error"]) from error
