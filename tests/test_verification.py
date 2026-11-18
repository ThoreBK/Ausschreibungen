"""Offline: Quellenvertrag und Urteilsverarbeitung, nicht die Urteilsgüte eines Modells."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from ausschreibungen.analysis import (
    CORRECTED_FIT,
    PROPOSAL,
    VERIFICATION,
    analyze_run,
    expand_claim,
    extract,
    interpret,
    load_analysis_profile,
    model_payload,
)
from ausschreibungen.llm import ModelError
from ausschreibungen.notices import NS
from tests.test_analysis import (
    FIXTURES,
    NOW,
    PROFILE,
    citation,
    lot,
    original_path,
    proposal,
    saved_run,
    wire_proposal,
    wire_verdict,
    xml,
)

CASES = json.loads((FIXTURES / "real/verification-cases.json").read_text("utf-8"))


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


def resolve_span(span: dict[str, Any], payload: dict[str, Any]) -> str:
    record = next(r for r in payload["records"] if r["id"] == span["source"])
    text = payload["texts"][record["text_id"]]
    return text[span.get("start", 0) : span.get("end", len(text))]


@pytest.mark.parametrize(
    "number", ["773064-2026", "788030-2026", "794059-2026", "798622-2026", "799785-2026"]
)
def test_compact_inputs_preserve_every_original_node_and_field_value(number: str) -> None:
    content = (FIXTURES / "real" / f"{number}.xml").read_bytes()
    doc = extract(content, number, now=NOW)
    profile = load_analysis_profile(PROFILE)
    payload, _ = model_payload(doc, profile)
    root = ET.fromstring(content)
    assert len(payload["records"]) == sum(bool((n.text or "").strip()) for n in root.iter())
    assert len({original_path(r, payload) for r in payload["records"]}) == len(payload["records"])
    for record in payload["records"]:
        node = root.find("./" + original_path(record, payload).split("/", 2)[2], NS)
        assert node is not None
        assert payload["texts"][record["text_id"]] == (node.text or "").strip()
        assert record["attributes"] == node.attrib
    assert len(set(payload["texts"].values())) == len(payload["texts"])
    assert payload["document"]["publication_number"] == number
    assert payload["document"]["metadata"]["versions"] == doc["metadata"]["versions"]
    for unit, packed in zip(doc["units"], payload["units"], strict=True):
        assert packed["lot_id"] == unit["lot_id"]
        for key, field in unit["fields"].items():
            compact = packed["structured_fields"][key]
            assert compact["status"] == field["status"]
            for before, after in zip(field["values"], compact["values"], strict=True):
                for name, value in before.items():
                    if name == "evidence":
                        for old, new in zip(value, after[name], strict=True):
                            record = next(r for r in payload["records"] if r["id"] == new["source"])
                            assert old["path"] == original_path(record, payload)
                            assert old["lot_id"] == record["lot_id"]
                            assert old["quote"] == resolve_span(new, payload)
                    elif isinstance(after[name], dict) and "source" in after[name]:
                        assert value == resolve_span(after[name], payload)
                    else:
                        assert value == after[name]
    legacy = [
        {
            "company_profile": profile["company_profile"],
            "lot_id": unit["lot_id"],
            "records": [r for r in doc["records"] if r["lot_id"] in (None, unit["lot_id"])],
            "structured_fields": unit["fields"],
        }
        for unit in doc["units"]
    ]
    assert len(json.dumps(payload, ensure_ascii=False).encode()) < sum(
        len(json.dumps(p, ensure_ascii=False).encode()) for p in legacy
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case"])
def test_reference_sources_and_fixed_judgments(case: dict[str, Any]) -> None:
    content = (FIXTURES / "real" / (case["number"] + ".xml")).read_bytes()
    root = ET.fromstring(content)
    claim = case["claim"]
    for ev in claim["evidence"]:
        node = root.find("./" + ev["path"].split("/", 2)[2], NS)
        assert node is not None and ev["quote"] in (node.text or "")
    if case["case"] == "framework_conflict":
        assert node is not None
        assert node.attrib["listName"] == "framework-agreement"
    doc = extract(content, case["number"], now=NOW)
    # Fehlender Passungsbeleg ist absichtlich lokal ungültig, nicht Teil dieses Testfalls.
    answer = {
        "facts": [],
        "fit": {
            "status": "unklar",
            "reason": "Keine Passungsprüfung in diesem Test.",
            "evidence": [],
        },
        "checkpoints": [],
    }
    answer[case["kind"]] = [deepcopy(claim)]
    judgment = decision(case["kind"] + ":0", claim, case["expected"])
    judgment["reason"] = case["reason"]
    model = Answers(answer, {"claims": [judgment]})
    interpret(doc, load_analysis_profile(PROFILE), model)
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    if case["case"] == "deadline_without_timezone":
        assert len(model.requests) == 1
        value = unit["fields"]["deadlines"]["values"][0]
        assert value["original"] == "Einreichungsfrist: Mittwoch, den 09.12.2026, 09:00 Uhr"
        assert value["original_date"] == "09.12.2026"
        assert value["original_time"] == "09:00 Uhr"
        assert value["berlin"] is None
        assert unit["fields"]["deadlines"]["status"] == "uncertain"
        assert unit["claim_reviews"][0]["local_check"]["status"] == "structured_duplicate"
        return
    assert len(model.requests) == 2
    request = model.requests[1]
    assert [c["claim_id"] for c in request["claims"]] == ["u0/" + case["kind"] + ":0"]
    sent = request["claims"][0]["claim"]
    for ev, compact in zip(claim["evidence"], sent["evidence"], strict=True):
        expected = ev["quote"]
        if case["kind"] == "checkpoints":
            source_node = root.find("./" + ev["path"].split("/", 2)[2], NS)
            assert source_node is not None
            expected = (source_node.text or "").strip()
        assert resolve_span(compact, request) == expected
    if case["case"] == "framework_conflict":
        assert unit["checkpoints"][0]["reason"] == claim["reason"]
        assert len(unit["checkpoints"][0]["evidence"]) == 2
    elif case["case"] == "email_submission":
        assert unit["fields"]["submission"]["values"][0]["value"] == claim["value"]
    else:
        field = unit["fields"][claim["field"]]
        assert claim["value"] not in [v.get("value", v.get("original")) for v in field["values"]]
        if case["case"] == "appeal_not_submission_deadline":
            assert field["status"] == "present"
            assert unit["participation"]["status"] == "Frist offen"
        else:
            assert field["status"] == "uncertain"
        assert field["unconfirmed_values"][0]["value"] == claim["value"]
        checkpoint = unit["checkpoints"][0]
        assert checkpoint["verification"]["status"] == "widerlegt"
        assert checkpoint["verification"]["reason"] == case["reason"]
        assert checkpoint["evidence"] == claim["evidence"]


@pytest.mark.parametrize("status", ["bestätigt", "widerlegt", "nicht entscheidbar"])
def test_disputed_checkpoint_and_fit_survive_in_saved_output(status: str, tmp_path: Path) -> None:
    content = xml(lot())
    doc = extract(content, "100-2026", now=NOW)
    answer = proposal(doc)
    answer["checkpoints"] = [{"reason": "KI-Beratung ist genannt.", "evidence": citation_list(doc)}]
    judgments = {
        "claims": [
            decision("checkpoints:0", answer["checkpoints"][0], status),
            decision("fit", answer["fit"], status),
        ]
    }
    model = Answers(answer, judgments)
    output = analyze_run(saved_run(tmp_path, content), PROFILE, model=model, now=NOW)
    result = json.loads((output / "analysis.json").read_text("utf-8"))
    unit = result["documents"][0]["units"][0]
    assert unit["processing_errors"] == []
    assert result["status"] == ("complete" if status == "bestätigt" else "incomplete")
    assert unit["fit"]["status"] == ("passend" if status == "bestätigt" else "unklar")
    assert {r["model_check"]["status"] for r in unit["claim_reviews"]} == {status}
    assert "KI-Beratung ist genannt." in (output / "analysis.html").read_text("utf-8")
    if status != "bestätigt":
        assert len(unit["checkpoints"]) == 2
        assert all(c["method"] == "ai_unconfirmed" for c in unit["checkpoints"])
        assert all(c["evidence"] for c in unit["checkpoints"])


def citation_list(doc: dict[str, Any]) -> list[dict[str, str]]:
    return [citation(doc, "KI-Beratung")]


def test_reordered_mixed_verdicts_are_assigned_by_id_and_keep_unicode_quotes() -> None:
    note = "Hinweis 🙂: Einreichungsform: per E-Mail. Vorzulegende Unterlagen: Anschreiben."
    doc = extract(xml(lot(), extra=f"<cbc:Note>{note}</cbc:Note>"), "100-2026", now=NOW)
    answer = proposal(doc)
    answer["facts"] = [
        {
            "field": "submission",
            "value": text,
            "state": "present",
            "evidence": [citation(doc, text)],
        }
        for text in ("Einreichungsform: per E-Mail.", "Vorzulegende Unterlagen: Anschreiben.")
    ]
    model = Answers(
        answer,
        {
            "claims": [
                decision("facts:1", answer["facts"][1], "widerlegt"),
                decision("fit", answer["fit"], "bestätigt"),
                decision("facts:0", answer["facts"][0], "bestätigt"),
            ]
        },
    )
    interpret(doc, load_analysis_profile(PROFILE), model)
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    field = unit["fields"]["submission"]
    assert [v["value"] for v in field["values"]] == ["Einreichungsform: per E-Mail."]
    assert field["unconfirmed_values"][0]["value"] == "Vorzulegende Unterlagen: Anschreiben."
    assert field["status"] == "present"
    assert unit["fit"]["status"] == "passend"
    payload = model.requests[1]
    assert resolve_span(payload["claims"][0]["claim"]["value"], payload) == (
        "Einreichungsform: per E-Mail."
    )


@pytest.mark.parametrize("failure", ["missing", "duplicate", "unknown", "quote", "lot", "offline"])
def test_invalid_verification_never_discards_locally_valid_claims(failure: str) -> None:
    doc = extract(xml(lot() + lot("LOT-2", subject="Bauarbeiten")), "100-2026", now=NOW)
    answer = proposal(doc)
    answer["checkpoints"] = [{"reason": "Prüfpunkt.", "evidence": citation_list(doc)}]
    values = [
        decision("fit", answer["fit"], "bestätigt"),
        decision("checkpoints:0", answer["checkpoints"][0], "bestätigt"),
    ]
    if failure == "missing":
        values.pop()
    elif failure == "duplicate":
        values[1] = deepcopy(values[0])
    elif failure == "unknown":
        values[1]["claim_id"] = "facts:99"
    elif failure == "quote":
        values[1]["evidence"][0]["quote"] = "Erfundener Beleg"
    elif failure == "lot":
        values[1]["evidence"] = [citation(doc, "Bauarbeiten")]
    model = Answers(answer, ModelError("offline") if failure == "offline" else {"claims": values})
    interpret(doc, load_analysis_profile(PROFILE), model)
    unit = doc["units"][0]
    assert unit["processing_errors"]
    if failure in {"quote", "lot"}:
        assert unit["fit"]["status"] == "passend"
        assert [c["claim_id"] for c in unit["checkpoints"]] == ["checkpoints:0"]
    else:
        assert unit["fit"]["status"] == "unklar"
        assert len(unit["checkpoints"]) == 2
    assert all(c["verification"]["status"] == "nicht entscheidbar" for c in unit["checkpoints"])
    assert all(r["stage"] == "model" for r in unit["rejected_claims"])


@pytest.mark.parametrize("change", ["none", "field", "state", "evidence"])
def test_only_exact_structured_duplicate_skips_model_review(change: str) -> None:
    doc = extract(
        xml(
            lot(),
            extra="<cac:TenderingProcess><cbc:ProcedureCode>open</cbc:ProcedureCode></cac:TenderingProcess>",
        ),
        "100-2026",
        now=NOW,
    )
    answer = proposal(doc)
    item = {
        "field": "procedure",
        "value": "open",
        "state": "present",
        "evidence": [citation(doc, "open")],
    }
    if change == "field":
        item["field"] = "submission"
    elif change == "state":
        item["state"] = "conflict"
    elif change == "evidence":
        item["evidence"].append(citation(doc, "Referenz über zwei KI-Schulungen"))
    answer["facts"] = [item]
    judgments = [decision("fit", answer["fit"], "bestätigt")]
    if change != "none":
        judgments.append(decision("facts:0", item, "nicht entscheidbar"))
    model = Answers(answer, {"claims": judgments})
    interpret(doc, load_analysis_profile(PROFILE), model)
    assert len(model.requests) == 2
    ids = [c["claim_id"] for c in model.requests[1]["claims"]]
    assert ids == (["u0/fit"] if change == "none" else ["u0/facts:0", "u0/fit"])
    unit = doc["units"][0]
    assert unit["processing_errors"] == []
    if change == "none":
        assert len(unit["fields"]["procedure"]["values"]) == 1
        assert unit["claim_reviews"][0]["model_check"] is None


def test_live_oracle_requires_confirmed_email_not_just_a_retained_quote() -> None:
    from tests.test_analysis_live import assert_missing_notice_fields

    email = {"value": "Einreichungsform: per E-Mail an vergabestelle@ukaachen.de"}
    unit = {
        "fields": {
            "deadlines": {
                "status": "uncertain",
                "values": [
                    {
                        "original": "Einreichungsfrist: Mittwoch, den 09.12.2026, 09:00 Uhr",
                        "berlin": None,
                    }
                ],
            },
            "submission": {"values": [email]},
            "selection_criteria": {"values": [{"value": "Mindestens drei Referenzen"}]},
        },
        "participation": {"status": "ungeklärt"},
    }
    assert_missing_notice_fields(unit)
    unit["fields"]["submission"] = {"values": [], "unconfirmed_values": [email]}
    with pytest.raises(AssertionError, match="E-Mail-Abgabeform nicht bestätigt"):
        assert_missing_notice_fields(unit)


@pytest.mark.parametrize("limit", ["tokens", "calls", "unknown"])
def test_controlled_live_budget_prevents_further_model_calls(limit: str, tmp_path: Path) -> None:
    from ausschreibungen.llm import CodexModel
    from tests.test_verification_live import Budget

    budget = Budget()
    if limit == "tokens":
        budget.calls = [{"usage": {"input_tokens": 149_000, "output_tokens": 1_000}}]
    elif limit == "calls":
        budget.calls = [{"usage": {"input_tokens": 1, "output_tokens": 1}}] * 5
    else:
        budget.calls = [{"status": "error"}]
    client = CodexModel("must-not-run", tmp_path / "must-not-exist")
    with pytest.raises(ModelError, match="Budget erreicht oder Verbrauch unbekannt"):
        budget.run(client, "", {}, {})
    assert client.calls == []
    assert not client.directory.exists()


def test_numeric_fact_preserves_qualifier_in_comparison_quote() -> None:
    correction = "Für Los 3 sind maximal 3 anstelle von 8 Bewerbern vorgesehen."
    item = {"value": "8", "evidence": [{"source": "note"}, {"source": "limit"}]}
    sources = {
        "note": {"path": "/note", "value": correction},
        "limit": {"path": "/limit", "value": "8"},
    }
    assert expand_claim(item, sources)["evidence"] == [
        {"path": "/note", "quote": correction},
        {"path": "/limit", "quote": "8"},
    ]


@pytest.mark.parametrize(
    "number,position,anchor,original,corrected",
    [
        (
            "794059-2026",
            2,
            "Digitalisierung und Automatisierung von Prozessen",
            "Das Los umfasst die Weiterentwicklung von KI-Anwendungen.",
            "Die ausgeschriebene Prozessautomatisierung passt zum Automatisierungsangebot.",
        ),
        (
            "791547-2026",
            1,
            "Moderierte Online-Workshops",
            "Die beauftragten KI-Workshops passen zum Schulungsangebot.",
            "Die ausgeschriebenen KI-Aufbauworkshops passen zum Schulungsangebot.",
        ),
    ],
)
def test_fit_verification_can_correct_reason_with_own_service_evidence(
    number: str, position: int, anchor: str, original: str, corrected: str
) -> None:
    content = (FIXTURES / "real" / f"{number}.xml").read_bytes()
    root = ET.fromstring(content)
    lot_path = f"cac:ProcurementProjectLot[{position}]"
    project = lot_path + "/cac:ProcurementProject[1]"
    description = project + "/cbc:Description[1]"
    assert anchor in root.findtext(description, namespaces=NS)
    base = "/" + root.tag.split("}")[-1] + "/"
    doc = extract(content, number, now=NOW)
    unit = doc["units"][position - 1]
    doc["units"] = [unit]
    participation = deepcopy(unit["participation"])
    claim = {
        "status": "passend",
        "reason": original,
        "evidence": [
            {"path": base + description, "quote": anchor},
            {
                "path": base + project + "/cbc:Name[1]",
                "quote": root.findtext(project + "/cbc:Name[1]", namespaces=NS).strip(),
            },
        ],
    }
    verdict = {
        "claim_id": "fit",
        "status": CORRECTED_FIT,
        "reason": corrected,
        "evidence": [claim["evidence"][0]],
    }
    model = Answers({"facts": [], "fit": claim, "checkpoints": []}, {"claims": [verdict]})
    interpret(doc, load_analysis_profile(PROFILE), model)
    assert [q["stage"] for q in model.requests] == ["analysis", "verification"]
    assert unit["fit"]["status"] == "passend"
    assert unit["fit"]["reason"] == corrected
    assert [(e["path"], e["lot_id"]) for e in unit["fit"]["evidence"]] == [
        (base + description, unit["lot_id"])
    ]
    assert unit["claim_reviews"][0]["claim"]["reason"] == original
    assert unit["claim_reviews"][0]["model_check"]["reason_corrected"] is True
    assert unit["participation"] == participation
    if number == "791547-2026":
        assert participation["status"] == "nicht offen"


@pytest.mark.parametrize("wrong_status", [True, False])
def test_fit_correction_requires_positive_proposal_and_service_evidence(wrong_status: bool) -> None:
    doc = extract(xml(lot()), "100-2026", now=NOW)
    answer = proposal(doc, status="unklar" if wrong_status else "passend")
    verdict = decision("fit", answer["fit"], CORRECTED_FIT)
    if not wrong_status:
        verdict["evidence"] = [citation(doc, "Referenz über zwei KI-Schulungen")]
    interpret(doc, load_analysis_profile(PROFILE), Answers(answer, {"claims": [verdict]}))
    assert doc["units"][0]["fit"]["status"] == "unklar"
    assert doc["units"][0]["claim_reviews"][0]["model_check"]["status"] == "nicht entscheidbar"
