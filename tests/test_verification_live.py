"""Kleiner kontrollierter Vergleich: RUN_LIVE_VERIFICATION=1 uv run pytest -s dieses_file.

Fünf feste Referenzfälle (kontrollierte Vorschläge, echte Gegenprüfung) und eine
vollständige Drei-Los-Analyse. Maximal fünf echte Aufrufe, keine Wiederholungen.
Das Tokenbudget wird zwischen Aufrufen geprüft; ein laufender Aufruf kann es
überschreiten, da die verwendete Schnittstelle kein hartes Ausgabetokenlimit anbietet.
"""

import os
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

import pytest

from ausschreibungen.analysis import (
    PROPOSAL,
    estimate_cost,
    information_quality,
    interpret,
    load_analysis_profile,
)
from ausschreibungen.extraction import extract
from ausschreibungen.llm import CodexModel
from ausschreibungen.research import save_json
from tests.support.live import CASES, Budget
from tests.support.models import wire_proposal
from tests.support.notices import FIXTURES, NOW, PROFILE

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_VERIFICATION") != "1",
    reason="Kleiner echter Modellvergleich nur mit RUN_LIVE_VERIFICATION=1.",
)


def test_budgeted_reference_verdicts_and_bundled_analysis() -> None:
    directory = Path(__file__).parents[1] / "reports" / f"task11-compact-check-{uuid4().hex[:8]}"
    directory.mkdir(parents=True)
    profile = {**load_analysis_profile(PROFILE), "model": "gpt-6.1-sol"}
    budget = Budget()
    report: dict[str, Any] = {
        "profile": profile,
        "budget": {
            "max_calls": budget.max_calls,
            "token_threshold_between_calls": budget.max_tokens,
        },
        "expected": deepcopy(CASES),
        "references": [],
        "scope": "Kontrollierte Analysevorschläge für fünf feste Fälle; echte Gegenprüfung. "
        "Zusätzlich vollständige echte Analyse und Gegenprüfung einer Drei-Los-Bekanntmachung.",
    }
    failures = []
    started = perf_counter()
    save_json(directory / "comparison.json", report)
    try:
        for number in ("773064-2026", "788030-2026", "799785-2026"):
            cases = [case for case in CASES if case["number"] == number]
            doc = extract((FIXTURES / "real" / f"{number}.xml").read_bytes(), number, now=NOW)
            answer: dict[str, Any] = {
                "facts": [],
                "checkpoints": [],
                "fit": {
                    "status": "unklar",
                    "reason": "Keine Passungsprüfung in diesem Referenzversuch.",
                    "evidence": [],
                },
            }
            claim_ids = {}
            for case in cases:
                kind = case["kind"]
                claim_ids[case["case"]] = f"{kind}:{len(answer[kind])}"
                answer[kind].append(deepcopy(case["claim"]))
            client = CodexModel(profile["model"], directory / number / "model")

            def reference_model(
                instructions: str,
                payload: dict[str, Any],
                schema: dict[str, Any],
                *,
                reference_answer: dict[str, Any] = answer,
                reference_client: CodexModel = client,
            ) -> Any:
                if schema == PROPOSAL:
                    return wire_proposal(reference_answer, payload)
                return budget.run(reference_client, instructions, payload, schema)

            interpret(doc, profile, reference_model)
            unit = doc["units"][0]
            reviews = {r["claim_id"]: r for r in unit["claim_reviews"]}
            for case in cases:
                review = reviews[claim_ids[case["case"]]]
                if case["case"] == "deadline_without_timezone":
                    ok = (
                        review["local_check"]["status"] == "structured_duplicate"
                        and any(
                            v.get("original") == case["claim"]["value"] and v["berlin"] is None
                            for v in unit["fields"]["deadlines"]["values"]
                        )
                        and unit["fields"]["deadlines"]["status"] == "uncertain"
                    )
                else:
                    verdict = review["model_check"]
                    ok = bool(
                        verdict and verdict["status"] == case["expected"] and verdict["evidence"]
                    )
                    if case["kind"] == "facts":
                        field = unit["fields"][case["claim"]["field"]]
                        accepted = case["claim"]["value"] in [
                            v.get("value") for v in field["values"]
                        ]
                        ok = ok and accepted == (case["expected"] == "bestätigt")
                        if case["expected"] != "bestätigt":
                            ok = ok and any(
                                v["value"] == case["claim"]["value"]
                                for v in field.get("unconfirmed_values", [])
                            )
                if not ok:
                    failures.append(case["case"])
                report["references"].append({"case": case["case"], "passed": ok, "review": review})
            if unit["processing_errors"]:
                failures.append(f"{number}: {unit['processing_errors']}")
            save_json(directory / number / "result.json", {"document": doc, "calls": client.calls})

        doc = extract((FIXTURES / "real/798622-2026.xml").read_bytes(), "798622-2026", now=NOW)
        client = CodexModel(profile["model"], directory / "bundle" / "model")

        def bundled_model(
            instructions: str, payload: dict[str, Any], schema: dict[str, Any]
        ) -> Any:
            return budget.run(client, instructions, payload, schema)

        interpret(doc, profile, bundled_model)
        for unit, months in zip(doc["units"], ("20", "21", "21"), strict=True):
            unit["information_quality"] = information_quality(unit)
            if (
                unit["fit"]["status"] != "unpassend"
                or unit["processing_errors"]
                or unit["fields"]["duration"]["values"][0]["value"] != months
                or unit["fields"]["deadlines"]["values"][0]["berlin"] != "2026-11-17T11:00:00+01:00"
            ):
                failures.append(unit["lot_id"])
        report["bundle"] = {
            "document": doc,
            "calls": client.calls,
            "cost": estimate_cost(client.calls),
        }
        if len(client.calls) != 2:
            failures.append("Gebündelte Analyse benötigt genau zwei Aufrufe.")
    finally:
        cost = estimate_cost(budget.calls)
        report.update(
            failures=failures,
            calls=budget.calls,
            cost=cost,
            token_threshold_exceeded=sum(cost["tokens"].values()) > budget.max_tokens,
            elapsed_seconds=perf_counter() - started,
        )
        save_json(directory / "comparison.json", report)
        print(f"\nKontrolllauf: {directory / 'comparison.json'}")
    assert failures == []
    assert len(budget.calls) == 5
    # Ein abgeschlossener letzter Aufruf darf die Schwelle überschreiten.
    # Entscheidend ist, dass danach kein weiterer Aufruf gestartet wurde.
    for index in range(len(budget.calls)):
        assert sum(estimate_cost(budget.calls[:index])["tokens"].values()) < budget.max_tokens
