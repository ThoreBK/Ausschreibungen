"""Unabhängige Quellen-Erwartungen; feste Urteile testen nur die Verarbeitung."""

from copy import deepcopy
from typing import Any

import pytest

from ausschreibungen.analysis import (
    interpret,
    load_analysis_profile,
)
from ausschreibungen.extraction import extract as extract_notice
from tests.support.models import Answers, decision, original_path
from tests.support.notices import NOW, PROFILE, citation, lot, xml


def context_fixture() -> dict[str, Any]:
    # Gegenbelege stehen absichtlich weit außerhalb des zitierten Elternknotens.
    content = xml(
        lot("LOT-A", subject="KI-Beratung", criterion="Referenzen sind nicht erforderlich.")
        .replace(
            "</cac:ProcurementProject>",
            "<cac:PlannedPeriod><cbc:DurationMeasure unitCode='MON'>24</cbc:DurationMeasure>"
            "</cac:PlannedPeriod></cac:ProcurementProject>",
        )
        .replace(
            "</cac:ProcurementProjectLot>",
            "<cac:AdditionalDocumentReference><cbc:DocumentDescription>"
            "Abweichend werden für Los A drei Referenzen verlangt."
            "</cbc:DocumentDescription><cbc:ID>Anlage 9</cbc:ID>"
            "</cac:AdditionalDocumentReference></cac:ProcurementProjectLot>",
        )
        + lot("LOT-B", subject="Referenzpflicht betrifft ausschließlich Los A."),
        extra="<cbc:Note>Für alle Lose ist eine Haftpflichtversicherung nachzuweisen.</cbc:Note>",
    )
    return extract_notice(content, "100-2026", now=NOW)


def fact_answer(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "facts": [
            {
                "field": "selection_criteria",
                "value": "Referenzen sind nicht erforderlich.",
                "state": "present",
                "evidence": [citation(doc, "Referenzen sind nicht erforderlich.")],
            }
        ],
        "fit": {"status": "unklar", "reason": "Kein Testziel.", "evidence": []},
        "checkpoints": [],
    }


def test_verification_keeps_distant_counterevidence_unknown_nodes_and_lot_comparison() -> None:
    doc = context_fixture()
    # Nur Los A auswerten; Vergleichsquellen des anderen Loses müssen bleiben.
    doc["units"] = doc["units"][:1]
    original = deepcopy(doc)
    answer = fact_answer(doc)
    judgment = decision("facts:0", answer["facts"][0], "widerlegt")
    judgment["evidence"].append(
        citation(doc, "Abweichend werden für Los A drei Referenzen verlangt.")
    )
    model = Answers(answer, {"claims": [judgment]})
    interpret(doc, load_analysis_profile(PROFILE), model)
    analysis, check = model.requests
    assert len(analysis["records"]) == len(original["records"])
    assert "structured_fields" in analysis["units"][0]
    assert "structured_fields" not in check["units"][0]
    text_by_path = {original_path(r, check): check["texts"][r["text_id"]] for r in check["records"]}
    assert (
        text_by_path[
            "/ContractNotice/cac:ProcurementProjectLot[1]/cac:AdditionalDocumentReference[1]/"
            "cbc:DocumentDescription[1]"
        ]
        == "Abweichend werden für Los A drei Referenzen verlangt."
    )
    assert (
        text_by_path[
            "/ContractNotice/cac:ProcurementProjectLot[2]/cac:ProcurementProject[1]/cbc:Description[1]"
        ]
        == "Referenzpflicht betrifft ausschließlich Los A."
    )
    assert text_by_path["/ContractNotice/cbc:Note[1]"] == (
        "Für alle Lose ist eine Haftpflichtversicherung nachzuweisen."
    )
    for key in ("records", "paths", "texts"):
        assert check[key] == analysis[key]
    assert doc["records"] == original["records"]
    assert doc["verification_context"]["complete_sources"] is True
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    assert unit["claim_reviews"][0]["model_check"]["status"] == "widerlegt"
    assert unit["fields"]["selection_criteria"]["status"] == "uncertain"
    assert all(
        v["value"] != "Referenzen sind nicht erforderlich."
        for v in unit["fields"]["selection_criteria"]["values"]
    )
    assert len(unit["claim_reviews"][0]["model_check"]["evidence"]) == 2


@pytest.mark.parametrize("reason", ["Die Laufzeit ist nicht angegeben.", "Die Dauer bleibt offen."])
def test_false_absence_gets_full_sources_even_without_keyword_match(reason: str) -> None:
    doc = context_fixture()
    doc["units"] = doc["units"][:1]
    answer = fact_answer(doc)
    answer["facts"] = []
    claim = {"reason": reason, "evidence": [citation(doc, "KI-Beratung")]}
    answer["checkpoints"] = [claim]
    judgment = decision("checkpoints:0", claim, "widerlegt")
    judgment["evidence"].append(citation(doc, "24"))
    model = Answers(answer, {"claims": [judgment]})
    interpret(doc, load_analysis_profile(PROFILE), model)
    analysis, check = model.requests
    assert check["records"] == analysis["records"]
    assert check["texts"] == analysis["texts"]
    assert check["context"]["complete_sources"] is True
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    assert unit["checkpoints"][0]["verification"]["status"] == "widerlegt"
    assert unit["fields"]["duration"]["values"][0]["value"] == "24"
