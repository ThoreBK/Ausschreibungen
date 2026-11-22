"""Bekanntmachung einmal übergeben, Losgeltung und Belege unabhängig prüfen."""

import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Any

import pytest

from ausschreibungen.analysis import interpret, load_analysis_profile
from ausschreibungen.extraction import extract as extract_notice
from ausschreibungen.notices import NS
from tests.support.models import Answers, LotAnswers, decision
from tests.support.notices import FIXTURES, NOW, PROFILE, two_lots


def test_real_foreign_lot_criterion_stays_out_of_structured_and_ai_facts() -> None:
    content = (FIXTURES / "real/794059-2026.xml").read_bytes()
    provenance = json.loads((FIXTURES / "real/provenance.json").read_text("utf-8"))
    assert hashlib.sha256(content).hexdigest() == provenance["documents"]["794059-2026"]["sha256"]
    path = (
        "/ContractNotice/cac:ProcurementProjectLot[1]/cac:TenderingTerms[1]/"
        "ext:UBLExtensions[1]/ext:UBLExtension[1]/ext:ExtensionContent[1]/"
        "efext:EformsExtension[1]/efac:SelectionCriteria[2]/cbc:Description[1]"
    )
    node = ET.fromstring(content).find("./" + path.split("/", 2)[2], NS)
    assert node is not None and node.text is not None
    quote = node.text.strip()
    assert quote.startswith("Referenzen Los 2:")
    doc = extract_notice(content, "794059-2026", now=NOW)
    doc["units"] = doc["units"][:1]
    assert doc["units"][0]["lot_id"] == "LOT-0001"
    claim = {
        "field": "selection_criteria",
        "state": "present",
        "value": quote,
        "evidence": [{"path": path, "quote": quote}],
    }
    model = Answers(
        {
            "facts": [claim],
            "fit": {"status": "unklar", "reason": "Kein Testziel.", "evidence": []},
            "checkpoints": [],
        },
        {"claims": [decision("facts:0", claim, "widerlegt")]},
    )
    interpret(doc, load_analysis_profile(PROFILE), model)
    assert len(model.requests) == 1
    unit = doc["units"][0]
    assert unit["claim_reviews"][0]["local_check"]["status"] == "invalid"
    criterion_path = path.rsplit("/", 1)[0]
    values = unit["fields"]["selection_criteria"]["values"]
    assert all(not v["evidence"][0]["path"].startswith(criterion_path + "/") for v in values)
    assert any(v["value"].startswith("Referenzen Los 1:") for v in values)
    assert any("(Lose 1 bis 3)" in v["value"] for v in values)
    assert any(c["evidence"][0]["path"] == path for c in unit["checkpoints"])


def test_two_lots_share_calls_but_reordered_results_remain_separate() -> None:
    doc = two_lots()
    model = LotAnswers()
    interpret(doc, load_analysis_profile(PROFILE), model)
    assert len(model.requests) == 2
    for request in model.requests:
        assert list(request["texts"].values()).count("Gemeinsam 🙂") == 1
        assert [u["lot_id"] for u in request["units"]] == ["LOT-A", "LOT-B"]
    a, b = doc["units"]
    assert a["processing_errors"] == b["processing_errors"] == []
    assert a["fit"]["status"] == "passend"
    assert b["fit"]["status"] == "unpassend"
    assert a["fit"]["evidence"] == [
        {
            "path": "/ContractNotice/cac:ProcurementProjectLot[1]/"
            "cac:ProcurementProject[1]/cbc:Description[1]",
            "quote": "KI-Beratung",
            "lot_id": "LOT-A",
        }
    ]
    assert b["fit"]["evidence"][0]["quote"] == "Bauarbeiten"
    assert b["fit"]["evidence"][0]["lot_id"] == "LOT-B"


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unknown"])
def test_ambiguous_bundle_never_assigns_answers_by_position(failure: str) -> None:
    doc = two_lots()
    model = LotAnswers(failure)
    interpret(doc, load_analysis_profile(PROFILE), model)
    assert len(model.requests) == 1
    assert all(u["processing_errors"] and u["fit"]["status"] == "unklar" for u in doc["units"])


@pytest.mark.parametrize(
    "failure", ["analysis_scope", "verification_scope", "verification_scope_mixed"]
)
def test_shared_sources_do_not_authorize_foreign_lot_citations(failure: str) -> None:
    doc = two_lots()
    model = LotAnswers(failure)
    interpret(doc, load_analysis_profile(PROFILE), model)
    a, b = doc["units"]
    assert a["fit"]["status"] == "unklar"
    if failure == "analysis_scope":
        assert a["rejected_claims"][0]["stage"] == "local"
        assert b["fit"]["status"] == "unpassend"
        assert [c["claim_id"] for c in model.requests[1]["claims"]] == ["u1/fit"]
    else:
        assert a["processing_errors"] and not b["processing_errors"]
        assert b["fit"]["status"] == "unpassend"
        assert a["checkpoints"][0]["claim"]["reason"] == "KI-Beratung wird beauftragt."
        assert b["checkpoints"] == []


@pytest.mark.parametrize("comparison_in_proposal", [False, True])
def test_real_bundled_response_keeps_foreign_comparison_sources_out_of_lot_facts(
    comparison_in_proposal: bool,
) -> None:
    # Gespeicherte echte Modellantworten des kleinen Kontrolllaufs; kein neuer Live-Aufruf.
    doc = extract_notice((FIXTURES / "real/798622-2026.xml").read_bytes(), "798622-2026", now=NOW)
    original_fields = [deepcopy(u["fields"]) for u in doc["units"]]
    replies = [
        json.loads((FIXTURES / "real" / f"bundled-798622-{stage}.json").read_text("utf-8"))
        for stage in ("proposal", "verification")
    ]
    for unit in replies[0]["units"]:
        unit["criteria_summaries"] = []

    if comparison_in_proposal:
        # Regression aus dem Fünferlauf: Analyse und Prüfer nennen beide Lose.
        proposal = next(u for u in replies[0]["units"] if u["unit_id"] == "u2")
        comparison = next(c for c in replies[1]["claims"] if c["claim_id"] == "u2/checkpoints:0")
        proposal["checkpoints"][0]["evidence"] = deepcopy(comparison["evidence"])

    def model(instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> Any:
        return replies.pop(0)

    interpret(doc, load_analysis_profile(PROFILE), model)
    assert replies == []
    for unit, fields in zip(doc["units"], original_fields, strict=True):
        assert unit["processing_errors"] == []
        assert unit["fit"]["status"] == "unpassend"
        assert unit["fields"] == fields
        assert unit["rejected_claims"] == []
    third = doc["units"][2]
    comparisons = [
        r
        for r in third["claim_reviews"]
        if any(e["lot_id"] == "LOT-0002" for e in r["model_check"]["evidence"])
    ]
    assert len(comparisons) == 1
    review = comparisons[0]
    assert review["model_check"]["status"] == "bestätigt"
    assert any(
        e["path"]
        == (
            "/ContractNotice/cac:ProcurementProjectLot[3]/cac:ProcurementProject[1]/cbc:Description[1]"
        )
        and "Los 2" in e["quote"]
        for e in review["claim"]["evidence"]
    )
    if comparison_in_proposal:
        assert {e["lot_id"] for e in third["checkpoints"][0]["evidence"]} == {
            "LOT-0002",
            "LOT-0003",
        }
    assert {e["lot_id"] for e in review["model_check"]["evidence"]} == {"LOT-0002", "LOT-0003"}
