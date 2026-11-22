import json
from typing import Any

from ausschreibungen.analysis import estimate_cost
from ausschreibungen.llm import CodexModel, ModelError
from tests.support.notices import FIXTURES


class Budget:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.max_calls = 5
        self.max_tokens = 150_000

    def run(
        self, client: CodexModel, instructions: str, payload: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        usage = estimate_cost(self.calls)
        if (
            len(self.calls) >= self.max_calls
            or usage["unknown_usage_calls"]
            or sum(usage["tokens"].values()) >= self.max_tokens
        ):
            raise ModelError(
                "Kontrolllauf-Budget erreicht oder Verbrauch unbekannt; kein Folgeaufruf."
            )
        if len(json.dumps(payload, ensure_ascii=False).encode()) > 150_000:
            raise ModelError(
                "Kontrolllauf-Anfrage überschreitet das vorab festgelegte Größenlimit."
            )
        try:
            return client(instructions, payload, schema)
        finally:
            self.calls.append(client.calls[-1])


def assert_missing_notice_fields(unit: dict[str, Any]) -> None:
    deadline = unit["fields"]["deadlines"]
    assert deadline["status"] == "uncertain"
    assert any(
        "09.12.2026" in value["original"]
        and "09:00 Uhr" in value["original"]
        and value["berlin"] is None
        for value in deadline["values"]
    )
    submission = json.dumps(unit["fields"]["submission"]["values"], ensure_ascii=False)
    assert "per E-Mail an vergabestelle@ukaachen.de" in submission, (
        "E-Mail-Abgabeform nicht bestätigt"
    )
    assert "Mindestens drei Referenzen" in json.dumps(
        unit["fields"]["selection_criteria"]["values"], ensure_ascii=False
    )
    assert unit["participation"]["status"] == "ungeklärt"


CASES = json.loads((FIXTURES / "real/verification-cases.json").read_text("utf-8"))
