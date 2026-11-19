"""TASK-12: vier echte Gegenprüfungen; keine neue Erstanalyse, keine Wiederholung.

RUN_LIVE_CONTEXT=1 uv run pytest -s tests/test_verification_context_live.py
Die Tokenschwelle wird zwischen Aufrufen geprüft, nicht als harte Obergrenze.
"""

import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from ausschreibungen.analysis import (
    PROPOSAL,
    estimate_cost,
    extract,
    interpret,
    load_analysis_profile,
)
from ausschreibungen.llm import CodexModel, ModelError
from ausschreibungen.research import save_json
from tests.test_analysis import FIXTURES, NOW, PROFILE, wire_proposal
from tests.test_verification import CASES
from tests.test_verification_live import Budget


def full_verification_payload(
    payload: dict[str, Any], claims: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        **payload,
        "stage": "verification",
        "claims": claims,
        "context": {"complete_sources": True, "selection": "Vollständige Referenzeingabe."},
    }


def bundle_expectations(doc: dict[str, Any]) -> list[str]:
    """Fachliche Erwartung aus Original-XML, nicht aus dem gespeicherten Prüfurteil.

    Materiallieferungen sind profilfremd. Spezifikationen und Kriterienkatalog
    werden nur referenziert; Beginn/Lieferstellen fehlen. Kaufvertrag und
    Unterlagenverweise, Auftragnehmer als Trommelkäufer und der Los-2-Dateititel
    im Los-3-Text begründen die offenen Prüfpunkte.
    """
    failures = []
    for i, unit in enumerate(doc["units"]):
        expected_ids = {"fit", *(f"checkpoints:{n}" for n in range(6 if i == 0 else 7))}
        reviews = {r["claim_id"]: r for r in unit["claim_reviews"]}
        if set(reviews) != expected_ids:
            failures.append(f"{unit['lot_id']}: unvollständige Aussagen")
        for key, review in reviews.items():
            check = review["model_check"]
            if not check or check["status"] != "bestätigt" or not check["evidence"]:
                failures.append(f"{unit['lot_id']}/{key}: erwartete Bestätigung fehlt")
        if unit["fit"]["status"] != "unpassend" or unit["processing_errors"]:
            failures.append(f"{unit['lot_id']}: Passung oder lokale Validierung")
        if unit["fields"]["duration"]["values"][0]["value"] != ("20" if i == 0 else "21"):
            failures.append(f"{unit['lot_id']}: Laufzeit verändert")
        if unit["fields"]["deadlines"]["values"][0]["berlin"] != "2026-11-17T11:00:00+01:00":
            failures.append(f"{unit['lot_id']}: Frist verändert")
        # Ein Prüfpunkt zum falsch bezeichneten Anhang benötigt den eigenen Los-3-Anker.
        if i == 2:
            review = reviews["checkpoints:0"]["model_check"]
            if not review or not any(
                e["path"]
                == "/ContractNotice/cac:ProcurementProjectLot[3]/"
                "cac:ProcurementProject[1]/cbc:Description[1]"
                and "Teil B - Los 2 - T2-05.003" in e["quote"]
                for e in review["evidence"]
            ):
                failures.append("LOT-0003: konkreter Beleg zum falschen Dateititel fehlt")
    return failures


def reference_expectations(doc: dict[str, Any]) -> list[str]:
    unit = doc["units"][0]
    failures = []
    reviews = {r["claim_id"]: r for r in unit["claim_reviews"]}
    for key, status in (("facts:0", "bestätigt"), ("facts:2", "widerlegt")):
        check = reviews[key]["model_check"]
        if not check or check["status"] != status or not check["evidence"]:
            failures.append(f"788030/{key}: erwartet {status}")
    field = unit["fields"]["submission"]
    if not any(
        v["value"] == "Einreichungsform: per E-Mail an vergabestelle@ukaachen.de"
        for v in field["values"]
    ):
        failures.append("E-Mail-Abgabeform nicht bestätigt")
    if any("Vorzulegende Unterlagen:" in v["value"] for v in field["values"]):
        failures.append("Unterlagenliste fälschlich als Abgabeform akzeptiert")
    if not any(
        v["value"] == "Vorzulegende Unterlagen:  - Anschreiben - Unternehmensdarstellung"
        for v in field.get("unconfirmed_values", [])
    ):
        failures.append("Strittige Unterlagenliste verloren")
    deadline = unit["fields"]["deadlines"]
    if deadline["status"] != "uncertain" or not any(
        v.get("original") == "Einreichungsfrist: Mittwoch, den 09.12.2026, 09:00 Uhr"
        and v["berlin"] is None
        for v in deadline["values"]
    ):
        failures.append("Frist ohne Zeitzone nicht korrekt erhalten")
    if unit["processing_errors"]:
        failures.append("Lokale Validierung fehlgeschlagen")
    return failures


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_CONTEXT") != "1", reason="Freigegebener Live-Vergleich."
)
def test_same_saved_proposals_with_full_and_reduced_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = Path(__file__).parents[1] / "reports" / f"task12-context-{uuid4().hex[:8]}"
    directory.mkdir(parents=True)
    profile = {**load_analysis_profile(PROFILE), "model": "gpt-6.1-sol"}
    budget = Budget()
    budget.max_calls = 4
    budget.max_tokens = 120_000
    proposal_bytes = (FIXTURES / "real/bundled-798622-proposal.json").read_bytes()
    bundled = json.loads(proposal_bytes)
    reference = {
        "facts": [deepcopy(c["claim"]) for c in CASES if c["number"] == "788030-2026"],
        "fit": {"status": "unklar", "reason": "Kein Testziel.", "evidence": []},
        "checkpoints": [],
    }
    # Vor dem ersten Aufruf fixieren; kontrollierte Vorschläge sind keine echte Erstanalyse.
    save_json(directory / "reference-proposal.json", reference)
    save_json(directory / "bundle-proposal.json", bundled)
    report: dict[str, Any] = {
        "kind": "live_verification_comparison",
        "model": profile["model"],
        "budget": {"max_calls": 4, "token_threshold_between_calls": 120_000},
        "analysis": {
            "live_calls": 0,
            "tokens": 0,
            "elapsed_seconds": 0,
            "basis": "Gespeicherte echte Drei-Los-Analyse und kontrollierte Referenzvorschläge.",
            "bundle_proposal_sha256": hashlib.sha256(proposal_bytes).hexdigest(),
        },
        "limitations": "Zwei Bekanntmachungen, je Variante ein Versuch; keine Fehlerquote. "
        "Offline-Tests und ältere Replays sind keine frischen Modellmessungen. "
        "Beide Varianten erhalten alle Quellen; nur die Referenz enthält abgeleitete Felder.",
        "runs": [],
    }
    failures = []
    try:
        for number, answer, oracle in (
            ("798622-2026", bundled, bundle_expectations),
            ("788030-2026", reference, reference_expectations),
        ):
            if number == "798622-2026":
                for unit in answer["units"]:
                    unit["criteria_summaries"] = []
            for mode in ("full", "reduced"):
                doc = extract((FIXTURES / "real" / f"{number}.xml").read_bytes(), number, now=NOW)
                (directory / number / mode).mkdir(parents=True)
                client = CodexModel(profile["model"], directory / number / mode / "model")

                def model(
                    instructions: str,
                    payload: dict[str, Any],
                    schema: dict[str, Any],
                    *,
                    answer: dict[str, Any] = answer,
                    number: str = number,
                    client: CodexModel = client,
                ) -> Any:
                    if schema == PROPOSAL:
                        return (
                            deepcopy(answer)
                            if number == "798622-2026"
                            else wire_proposal(answer, payload)
                        )
                    return budget.run(client, instructions, payload, schema)

                with monkeypatch.context() as context:
                    if mode == "full":
                        context.setattr(
                            "ausschreibungen.analysis.verification_payload",
                            full_verification_payload,
                        )
                    interpret(doc, profile, model)
                deviations = oracle(doc)
                failures.extend(f"{number}/{mode}: {s}" for s in deviations)
                result = {
                    "number": number,
                    "mode": mode,
                    "document": doc,
                    "calls": client.calls,
                    "cost": estimate_cost(client.calls),
                    "quality_deviations": deviations,
                }
                save_json(directory / number / mode / "result.json", result)
                report["runs"].append(result)
                save_json(directory / "comparison.json", report)
                if not client.calls or any(c["status"] != "ok" for c in client.calls):
                    raise ModelError(
                        "Messlauf abgebrochen; keine Folgeaufrufe nach Transportfehler."
                    )
    finally:
        report.update(cost=estimate_cost(budget.calls), failures=failures, calls=budget.calls)
        save_json(directory / "comparison.json", report)
        print(f"\nVergleich: {directory / 'comparison.json'}")
    assert len(budget.calls) == 4
    assert failures == []
