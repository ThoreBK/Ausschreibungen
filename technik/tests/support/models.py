from copy import deepcopy
from typing import Any

from ausschreibungen.analysis import PROPOSAL, VERIFICATION


def original_path(record: dict[str, Any], payload: dict[str, Any]) -> str:
    path = record["path"]
    seen = set()
    while not path.startswith("/"):
        prefix, rest = path.split("/", 1)
        assert prefix not in seen
        seen.add(prefix)
        path = payload["paths"][prefix] + "/" + rest
    return path


def wire_claim(item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Fixtures nennen unabhängige Originalfundstellen; nur Transport-IDs übersetzen."""
    result = deepcopy(item)
    result["evidence"] = [
        {
            "source": next(
                (
                    r["id"]
                    for r in payload["records"]
                    if original_path(r, payload) == ev["path"]
                    and ev["quote"] in payload["texts"][r["text_id"]]
                ),
                "unknown-source",
            )
        }
        for ev in item["evidence"]
    ]
    return result


def wire_proposal(answer: Any, payload: dict[str, Any]) -> Any:
    if (
        not isinstance(answer, dict)
        or set(answer) != {"facts", "fit", "checkpoints"}
        or not answer["fit"]
    ):
        return deepcopy(answer)
    return {
        "units": [
            {
                "unit_id": u["unit_id"],
                "facts": [wire_claim(f, payload) for f in answer["facts"]],
                "criteria_summaries": [],
                "fit": wire_claim(answer["fit"], payload),
                "checkpoints": [wire_claim(c, payload) for c in answer["checkpoints"]],
            }
            for u in payload["units"]
        ]
    }


def wire_verdict(verdict: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "claims": [
            {**wire_claim(c, payload), "claim_id": "u0/" + c["claim_id"]} for c in verdict["claims"]
        ]
    }


class ControlledModel:
    def __init__(self, answer: Any, verdict: Any = None) -> None:
        self.answer = answer
        self.verdict = verdict
        self.payloads: list[dict[str, Any]] = []

    def __call__(self, instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> Any:
        self.payloads.append(deepcopy(payload))
        assert "nicht vertrauenswürdige" in instructions
        if isinstance(self.answer, Exception):
            raise self.answer
        if schema == PROPOSAL:
            return wire_proposal(self.answer, payload)
        assert schema == VERIFICATION
        if self.verdict and "claims" in self.verdict:
            return wire_verdict(self.verdict, payload)
        decisions = []
        for request in payload["claims"]:
            key = request["claim_id"]
            kind, _, index = key.split("/", 1)[1].partition(":")
            item = self.answer[kind][int(index)] if index else self.answer[kind]
            approved = True
            if self.verdict:
                approved = self.verdict[kind][int(index)] if index else self.verdict[kind]
            decisions.append(
                {
                    "claim_id": key,
                    "status": "bestätigt" if approved else "nicht entscheidbar",
                    "reason": "Kontrolliertes Testurteil; keine Aussage über Modellqualität.",
                    "evidence": wire_claim(item, payload)["evidence"],
                }
            )
        return {"claims": deepcopy(decisions)}


def decision(claim_id: str, item: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "claim_id": claim_id,
        "status": status,
        "reason": "Fest vorgegebenes Offline-Urteil zur Prüfung der Verarbeitung.",
        "evidence": deepcopy(item["evidence"]),
    }


class Answers:
    def __init__(self, answer: dict[str, Any], judgments: dict[str, Any] | Exception) -> None:
        self.answer = answer
        self.judgments = judgments
        self.requests: list[dict[str, Any]] = []

    def __call__(self, instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> Any:
        self.requests.append(deepcopy(payload))
        if schema == PROPOSAL:
            return wire_proposal(self.answer, payload)
        assert schema == VERIFICATION
        if isinstance(self.judgments, Exception):
            raise self.judgments
        return wire_verdict(self.judgments, payload)


class LotAnswers:
    """Nur die Modellgrenze ersetzen; feste fachliche Werte je Los zurückgeben."""

    def __init__(self, failure: str = "") -> None:
        self.failure = failure
        self.requests: list[dict[str, Any]] = []

    def __call__(self, instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> Any:
        self.requests.append(deepcopy(payload))
        sources = {
            r["lot_id"]: r["id"]
            for r in payload["records"]
            if original_path(r, payload).endswith("/cac:ProcurementProject[1]/cbc:Description[1]")
        }
        if schema == PROPOSAL:
            answers = [
                {
                    "unit_id": "u0",
                    "facts": [],
                    "criteria_summaries": [],
                    "checkpoints": [],
                    "fit": {
                        "status": "passend",
                        "reason": "KI-Beratung wird beauftragt.",
                        "evidence": [{"source": sources["LOT-A"]}],
                    },
                },
                {
                    "unit_id": "u1",
                    "facts": [],
                    "criteria_summaries": [],
                    "checkpoints": [],
                    "fit": {
                        "status": "unpassend",
                        "reason": "Bauarbeiten werden beauftragt.",
                        "evidence": [{"source": sources["LOT-B"]}],
                    },
                },
            ]
            if self.failure == "missing":
                answers.pop()
            elif self.failure == "duplicate":
                answers[1]["unit_id"] = "u0"
            elif self.failure == "unknown":
                answers[1]["unit_id"] = "u99"
            elif self.failure == "analysis_scope":
                answers[0]["fit"]["evidence"] = [{"source": sources["LOT-B"]}]
            return {"units": list(reversed(answers))}
        answers = [
            {
                "claim_id": "u0/fit",
                "status": "bestätigt",
                "reason": "KI-Beratung ist genannt.",
                "evidence": [{"source": sources["LOT-A"]}],
            },
            {
                "claim_id": "u1/fit",
                "status": "bestätigt",
                "reason": "Bauleistung ist genannt.",
                "evidence": [{"source": sources["LOT-B"]}],
            },
        ]
        if self.failure == "verification_scope":
            answers[0]["evidence"] = [{"source": sources["LOT-B"]}]
        elif self.failure == "verification_scope_mixed":
            answers[0]["evidence"].append({"source": sources["LOT-B"]})
        if self.failure == "analysis_scope":
            answers = answers[1:]
        return {"claims": list(reversed(answers))}
