"""Vertragsdauer, Bindung, Rückfragen und Eignung vom XML bis zum sichtbaren Steckbrief."""

import json
import re
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from ausschreibungen.analysis import analyze_run, extract
from ausschreibungen.report import write_report
from ausschreibungen.ted import Profile
from tests.test_analysis import FIXTURES, NOW, PROFILE, lot, xml
from tests.test_research import Network, execute, response, row


def report_for(
    tmp_path: Path, profile: Profile, number: int, content: bytes
) -> tuple[list[dict[str, Any]], str]:
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(number, 14)), response()],
            {f"https://ted.europa.eu/en/notice/{number}-2026/xml": content},
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    pages = PdfReader(write_report(research, analysis, directory)).pages
    briefs = " ".join(" ".join(p.extract_text() for p in pages[1:]).split())
    return analysis["documents"][0]["units"], briefs.split("Belegverzeichnis")[0]


@pytest.mark.parametrize("end, mismatch", [("2029-06-29", True), ("2029-06-30", False)])
def test_planned_duration_and_extension_options(
    tmp_path: Path, profile: Profile, end: str, mismatch: bool
) -> None:
    options = (
        "Der Vertrag hat eine Mindestvertragslaufzeit von 24 Monaten ab Leistungsbeginn. "
        "Er kann durch einseitige Erklärung des Auftraggebers verlängert werden. "
        "Wird diese Erklärung nicht fristgerecht abgegeben, endet der Vertrag automatisch. "
        "Die Optionen betragen 24, 12 und 12 Monate. Die Höchstlaufzeit beträgt 72 Monate."
    )
    first = lot("LOT-0001").replace(
        "</cac:ProcurementProject>",
        f"""<cac:PlannedPeriod><cbc:StartDate>2027-07-01+02:00</cbc:StartDate>
        <cbc:EndDate>{end}+02:00</cbc:EndDate></cac:PlannedPeriod>
        <cac:ContractExtension><cbc:OptionsDescription>{options}</cbc:OptionsDescription>
        </cac:ContractExtension></cac:ProcurementProject>""",
    )
    units, brief = report_for(tmp_path, profile, 100, xml(first + lot("LOT-0002")))
    duration = units[0]["fields"]["duration"]
    assert duration["status"] == ("uncertain" if mismatch else "present")
    assert [v["value"] for v in duration["values"]] == ["2027-07-01+02:00", end + "+02:00", options]
    assert duration["values"][-1]["evidence"] == [
        {
            "path": "/ContractNotice/cac:ProcurementProjectLot[1]/cac:ProcurementProject[1]"
            "/cac:ContractExtension[1]/cbc:OptionsDescription[1]",
            "quote": options,
            "lot_id": "LOT-0001",
        }
    ]
    assert units[1]["fields"]["duration"]["status"] == "missing"
    first_brief, second_brief = brief.split("LOT-0002")
    assert "Planbeginn: 01.07.2027" in first_brief
    assert f"Planende: {end[-2:]}.06.2029" in first_brief
    assert options in first_brief
    assert "72 Monate" not in second_brief
    if mismatch:
        [point] = units[0]["checkpoints"]
        assert [e["quote"] for e in point["evidence"]] == [
            "2027-07-01+02:00",
            end + "+02:00",
            options,
        ]
        assert "Maßgebliche Laufzeit klären." in first_brief
    else:
        assert not units[0]["checkpoints"]
        assert "Maßgebliche Laufzeit klären." not in first_brief


def test_offer_validity_is_not_a_submission_deadline_or_contract_duration(
    tmp_path: Path, profile: Profile
) -> None:
    units, brief = report_for(
        tmp_path, profile, 799785, (FIXTURES / "real/799785-2026.xml").read_bytes()
    )
    [unit] = units
    [binding] = unit["fields"]["tender_validity"]["values"]
    assert binding["value"] == "30"
    assert binding["attributes"] == {"unitCode": "DAY"}
    assert binding["evidence"] == [
        {
            "path": "/ContractNotice/cac:ProcurementProjectLot[1]/cac:TenderingTerms[1]"
            "/cac:TenderValidityPeriod[1]/cbc:DurationMeasure[1]",
            "quote": "30",
            "lot_id": "LOT-0000",
        }
    ]
    assert unit["fields"]["duration"]["values"][0]["value"] == "48"
    assert {d["kind"] for d in unit["fields"]["deadlines"]["values"]} == {
        "TenderSubmissionDeadlinePeriod"
    }
    assert re.search(r"Angebotsbindefrist: 30 Tage \[\d+\]", brief)
    assert "Laufzeit: 48 Monate" in brief
    selection = unit["fields"]["selection_criteria"]
    assert selection["status"] == "uncertain"
    assert selection["document_sources"][0]["evidence"][0]["quote"] == "epo-procurement-document"
    assert re.search(
        r"Eignungskriterien: .*Einzelanforderungen in den Vergabeunterlagen prüfen\. \[\d+\]", brief
    )


def test_renewal_period_is_not_compared_as_original_planned_period() -> None:
    content = lot().replace(
        "</cac:ProcurementProject>",
        "<cac:ContractExtension><cbc:OptionsDescription>"
        "Der Vertrag hat eine Mindestvertragslaufzeit von 24 Monaten ab Leistungsbeginn."
        """</cbc:OptionsDescription>
        <cac:Renewal><cac:Period><cbc:StartDate>2029-07-01</cbc:StartDate>
        <cbc:EndDate>2030-06-30</cbc:EndDate></cac:Period></cac:Renewal>
        </cac:ContractExtension></cac:ProcurementProject>""",
    )
    [unit] = extract(xml(content), "100-2026", now=NOW)["units"]
    assert unit["fields"]["duration"]["status"] == "present"
    assert not unit["checkpoints"]


def test_eligibility_originals_stay_visible_per_lot(tmp_path: Path, profile: Profile) -> None:
    units, brief = report_for(
        tmp_path, profile, 794059, (FIXTURES / "real/794059-2026.xml").read_bytes()
    )
    sections = re.split(r"LOT-000[123] Teilnahmestand", brief)[1:]
    assert len(sections) == len(units) == 3
    for index, (unit, section) in enumerate(zip(units, sections, strict=True), 1):
        assert "bis maximal zum 31.05.2031." in section
        assert "wegen eines Nachprüfungsverfahrens" in section
        assert "längstens aber bis zum 30.11.2031" in section
        assert "zur Eintragung verpflichtet" in section
        assert "nicht älter als 6 Monate vom Tag der Teilnahmefrist gerechnet" in section
        assert "spätestens 8 (acht) Wochen nach Zuschlag" in section
        register, insurance = unit["fields"]["selection_criteria"]["notice_excerpts"]
        for item, phrase in ((register, "6 Monate"), (insurance, "8 (acht) Wochen")):
            [evidence] = item["evidence"]
            assert phrase in evidence["quote"]
            assert evidence["lot_id"] == f"LOT-000{index}"
            assert f"/cac:ProcurementProjectLot[{index}]/" in evidence["path"]


def test_eligibility_shows_insurance_amounts_and_alternative_proofs(
    tmp_path: Path, profile: Profile
) -> None:
    insurance = (
        "Eigenerklärung Versicherungen. Die Deckungssumme beträgt mindestens "
        "500.000 Euro für Personenschäden, 3.000.000 Euro für Sachschäden und "
        "5.000.000 Euro für Vermögensschäden. Jahresgesamtleistung: das Zweifache."
    )
    single_lot = lot().replace(
        "<cac:TenderingTerms>",
        "<cac:TenderingTerms><efac:SelectionCriteria>"
        '<cbc:TendererRequirementTypeCode listName="selection-criterion">'
        "slc-stand-other</cbc:TendererRequirementTypeCode>"
        f"<cbc:Description>{insurance}</cbc:Description></efac:SelectionCriteria>",
    )
    proofs = (
        "Angabe der PQ-Nummer oder Eigenerklärung oder Einheitliche Europäische Eigenerklärung."
    )
    equivalence = "Gleichwertige Nachweise sind zulässig. Die Gleichwertigkeit ist zu belegen."
    global_note = (
        "<cac:ProcurementProject><cbc:Note>Mit dem Angebot einzureichen:\n"
        f"{proofs}\nBei Bedarf Nachweise nachreichen.\n{equivalence}"
        "</cbc:Note></cac:ProcurementProject>"
    )
    [unit], brief = report_for(tmp_path, profile, 100, xml(single_lot, extra=global_note))
    selection = unit["fields"]["selection_criteria"]
    assert [item["value"] for item in selection["notice_excerpts"]] == [
        insurance,
        proofs,
        equivalence,
    ]
    assert selection["notice_excerpts"][0]["evidence"][0]["lot_id"] == "LOT-1"
    assert selection["notice_excerpts"][1]["evidence"] == [
        {
            "path": "/ContractNotice/cac:ProcurementProject[1]/cbc:Note[1]",
            "quote": proofs,
            "lot_id": None,
        }
    ]
    visible = brief.split("Eignungskriterien: ")[1].split("Zuschlagskriterien:")[0]
    for value in (insurance, proofs, equivalence):
        assert re.search(re.escape(value) + r" \[\d+\]", visible)
    multi_lot = extract(xml(single_lot + lot("LOT-2"), extra=global_note), "100-2026", now=NOW)
    for unit in multi_lot["units"]:
        assert all(
            item["value"] not in (proofs, equivalence)
            for item in unit["fields"]["selection_criteria"].get("notice_excerpts", [])
        )


def test_request_for_questions_does_not_replace_participation_deadline(
    tmp_path: Path, profile: Profile
) -> None:
    request = (
        "Wir bitten Fragen, die den Teilnahmewettbewerb betreffen, bis zum 11.12.2026 zu stellen."
    )
    deadline = lot(day="2026-12-21+01:00", clock="10:00:00+01:00").replace(
        "TenderSubmissionDeadlinePeriod", "ParticipationRequestReceptionPeriod"
    )
    note = f"<cbc:Note>Es gilt die Vergabeplattform. {request} Weitere Hinweise folgen.</cbc:Note>"
    [unit], brief = report_for(tmp_path, profile, 100, xml(deadline, extra=note))
    participation, questions = unit["fields"]["deadlines"]["values"]
    assert participation["kind"] == "ParticipationRequestReceptionPeriod"
    assert participation["berlin"] == "2026-12-21T10:00:00+01:00"
    assert questions["kind"] == "AdditionalInformationRequestPeriod"
    assert questions["original_date"] == "11.12.2026"
    assert questions["original_time"] is questions["berlin"] is None
    assert questions["status"] == "uncertain"
    assert questions["lot_id"] == "LOT-1"
    assert questions["evidence"] == [
        {"path": "/ContractNotice/cbc:Note[1]", "quote": request, "lot_id": None}
    ]
    assert unit["participation"]["status"] == "Frist offen"
    assert "Frist für Teilnahmeanträge: 21.12.2026, 10:00 MEZ" in brief
    assert f"Frist für Rückfragen: {request} · Uhrzeit nicht angegeben" in brief
    multi_lot = extract(xml(deadline + lot("LOT-2"), extra=note), "100-2026", now=NOW)
    assert all(
        d["kind"] != "AdditionalInformationRequestPeriod"
        for u in multi_lot["units"]
        for d in u["fields"]["deadlines"]["values"]
    )
