"""Unabhängige Quellen-Erwartungen; feste Urteile testen nur die Verarbeitung."""

from copy import deepcopy
from typing import Any

import pytest

from ausschreibungen.analysis import extract as extract_notice
from ausschreibungen.analysis import (
    interpret,
    load_analysis_profile,
    model_payload,
    verification_payload,
)
from tests.test_analysis import NOW, PROFILE, citation, lot, original_path, xml
from tests.test_verification import Answers, decision


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


def test_independent_selection_keeps_distant_counterevidence_unknown_nodes_and_lot_comparison() -> (
    None
):
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
    assert not any(
        "/cbc:EndDate[" in path or "/cbc:DurationMeasure[" in path for path in text_by_path
    )
    assert doc["records"] == original["records"]
    assert doc["verification_context"]["complete_sources"] is False
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    assert unit["claim_reviews"][0]["model_check"]["status"] == "widerlegt"
    assert unit["fields"]["selection_criteria"]["status"] == "uncertain"
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
    assert check["context"]["fallback"] == "unrestricted_reason"
    assert check["context"]["complete_sources"] is True
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    assert unit["checkpoints"][0]["verification"]["status"] == "widerlegt"
    assert unit["fields"]["duration"]["values"][0]["value"] == "24"


def test_scalar_in_requested_field_is_included_without_analysis_citation() -> None:
    doc = context_fixture()
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    check = verification_payload(
        payload,
        sources,
        [{"claim_id": "u0/facts:0", "unit_id": "u0", "claim": {"field": "deadlines"}}],
    )
    sent = {original_path(r, check) for r in check["records"]}
    assert (
        "/ContractNotice/cac:ProcurementProjectLot[1]/cac:TenderingProcess[1]/"
        "cac:TenderSubmissionDeadlinePeriod[1]/cbc:EndDate[1]"
    ) in sent
    assert (
        "/ContractNotice/cac:ProcurementProjectLot[2]/cac:TenderingProcess[1]/"
        "cac:TenderSubmissionDeadlinePeriod[1]/cbc:EndTime[1]"
    ) in sent


def test_unexpected_text_in_scalar_location_is_never_discarded() -> None:
    doc = extract_notice(
        xml(lot(day="Abweichend sind drei Referenzen erforderlich.")),
        "100-2026",
        now=NOW,
    )
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    check = verification_payload(payload, sources, [])
    assert "Abweichend sind drei Referenzen erforderlich." in check["texts"].values()


@pytest.mark.parametrize("state", ["uncertain", "conflict"])
def test_uncertain_fact_expands_context_without_interpreting_its_words(state: str) -> None:
    doc = context_fixture()
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    check = verification_payload(
        payload,
        sources,
        [
            {
                "claim_id": "u0/facts:0",
                "unit_id": "u0",
                "claim": {
                    "field": "selection_criteria",
                    "state": state,
                },
            }
        ],
    )
    assert check["records"] == payload["records"]
    assert check["context"]["fallback"] == "uncertain_fact"


def test_unknown_attributes_on_scalar_fields_expand_context() -> None:
    content = xml(lot()).replace(b"<cbc:EndDate>", b"<cbc:EndDate custom='unexpected'>")
    doc = extract_notice(content, "100-2026", now=NOW)
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    check = verification_payload(payload, sources, [])
    assert "2026-12-01Z" in check["texts"].values()


def test_cited_scalar_remains_even_for_a_wrong_field_assignment() -> None:
    doc = context_fixture()
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    cited = next(s for s in sources.values() if s["value"] == "24")
    check = verification_payload(
        payload,
        sources,
        [
            {
                "claim_id": "u0/facts:0",
                "unit_id": "u0",
                "claim": {
                    "field": "selection_criteria",
                    "evidence": [{"source": cited["id"]}],
                },
            }
        ],
    )
    assert cited["id"] in {r["id"] for r in check["records"]}
    assert "24" in check["texts"].values()


def test_verifier_cannot_cite_an_original_source_that_was_not_sent() -> None:
    doc = context_fixture()
    doc["units"] = doc["units"][:1]
    answer = fact_answer(doc)
    payload, sources = model_payload(doc, load_analysis_profile(PROFILE))
    hidden_id = next(s["id"] for s in sources.values() if s["value"] == "24")
    model = Answers(answer, {"claims": []})

    def invented_reference(
        instructions: str, request: dict[str, Any], schema: dict[str, Any]
    ) -> Any:
        if request["stage"] == "analysis":
            return model(instructions, request, schema)
        assert hidden_id not in {r["id"] for r in request["records"]}
        return {
            "claims": [
                {
                    "claim_id": "u0/facts:0",
                    "status": "bestätigt",
                    "reason": "Behauptete Stützung.",
                    "evidence": [{"source": hidden_id}],
                }
            ]
        }

    interpret(doc, load_analysis_profile(PROFILE), invented_reference)
    unit = doc["units"][0]
    assert unit["processing_errors"]
    assert unit["claim_reviews"][0]["model_check"]["status"] == "nicht entscheidbar"
    assert unit["fields"]["selection_criteria"]["status"] == "uncertain"
