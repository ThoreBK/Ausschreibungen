"""Vertragsdauer, Bindung, Rückfragen und Eignung vom XML bis zum sichtbaren Steckbrief."""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

from ausschreibungen.analysis import CORRECTED_SUMMARY, PROPOSAL, Model, analyze_run
from ausschreibungen.notices import NS
from ausschreibungen.report import write_report
from ausschreibungen.ted import Profile
from tests.support.notices import FIXTURES, NOW, PROFILE, lot, xml
from tests.support.research import Network, execute, response, row


def fixed_model(
    proposals: dict[str, dict[str, list[dict[str, Any]]]],
    *,
    rejected: tuple[str, ...] = (),
    corrections: dict[str, str] | None = None,
    coverage: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> Model:
    """Fachliche Urteile vorgeben; XML-Auflösung, Übernahme, Losgrenzen und PDF real ausführen."""

    def model(instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        if schema != PROPOSAL:
            return {
                "claims": [
                    {
                        "claim_id": c["claim_id"],
                        "status": (
                            CORRECTED_SUMMARY
                            if c["claim_id"] in (corrections or {})
                            else "widerlegt"
                            if c["claim_id"] in rejected
                            else "bestätigt"
                        ),
                        "reason": (corrections or {}).get(
                            c["claim_id"], "Vorgegebenes Testurteil."
                        ),
                        "evidence": [{"source": e["source"]} for e in c["claim"]["evidence"]],
                    }
                    for c in payload["claims"]
                ],
                "summary_coverage": [{"fact_id": f, "summary_ids": list(s)} for f, s in coverage],
            }
        units = []
        for u in payload["units"]:

            def source(snippet: str, lot_id: str = u["lot_id"]) -> dict[str, str]:
                return {
                    "source": next(
                        r["id"]
                        for r in payload["records"]
                        if r["lot_id"] in (None, lot_id)
                        and snippet in payload["texts"][r["text_id"]]
                    )
                }

            unit = {
                "unit_id": u["unit_id"],
                "fit": {
                    "status": "unklar",
                    "reason": "Test der Pflichtfelder.",
                    "evidence": [u["structured_fields"]["subject"]["values"][-1]["evidence"][0]],
                },
            }
            for group in ("facts", "criteria_summaries", "checkpoints"):
                unit[group] = [
                    {**claim, "evidence": [source(e) for e in claim["evidence"]]}
                    for claim in proposals.get(u["lot_id"], {}).get(group, [])
                ]
            units.append(unit)
        return {"units": units}

    return model


def report_for(
    tmp_path: Path, profile: Profile, number: int, content: bytes, model: Model | None = None
) -> tuple[list[dict[str, Any]], str]:
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(number, 14)), response()],
            {f"https://ted.europa.eu/en/notice/{number}-2026/xml": content},
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=model is None, model=model, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    pages = PdfReader(write_report(research, analysis, directory)).pages
    briefs = " ".join(" ".join(p.extract_text() for p in pages[1:]).split())
    return analysis["documents"][0]["units"], briefs.split("Belegverzeichnis")[0]


@pytest.mark.parametrize("end, mismatch", [("2029-06-29", True), ("2029-06-30", False)])
def test_planned_duration_and_extension_options(
    tmp_path: Path, profile: Profile, end: str, mismatch: bool
) -> None:
    options = (
        "Die Mindestvertragslaufzeit beträgt ab Leistungsbeginn zwei Jahre. "
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
    model = fixed_model(
        {
            "LOT-0001": {
                "facts": [
                    {
                        "field": "minimum_service_months",
                        "value": "24",
                        "state": "present",
                        "evidence": [options],
                    }
                ],
                "checkpoints": [
                    {
                        "reason": "Wie passt das Planende zur Mindestvertragslaufzeit?",
                        "evidence": ["2027-07-01+02:00", end + "+02:00", options],
                    }
                ]
                if mismatch
                else [],
            }
        }
    )
    units, brief = report_for(tmp_path, profile, 100, xml(first + lot("LOT-0002")), model)
    duration = units[0]["fields"]["duration"]
    assert duration["status"] == ("uncertain" if mismatch else "present")
    assert [v["value"] for v in duration["values"] if v["method"] == "xml"] == [
        "2027-07-01+02:00",
        end + "+02:00",
        options,
    ]
    assert duration["values"][2]["evidence"] == [
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
        [point] = [
            p for p in units[0]["checkpoints"] if p.get("method") == "xml_duration_comparison"
        ]
        assert "Wie passt das Planende zur Mindestvertragslaufzeit?" not in first_brief
        assert "Weitere Prüfpunkte (1)" in first_brief
        assert [e["quote"] for e in point["evidence"]] == [
            "2027-07-01+02:00",
            end + "+02:00",
            options,
        ]
        assert first_brief.count("Maßgebliche Laufzeit klären.") == 1
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


def test_renewal_period_is_not_compared_as_original_planned_period(
    tmp_path: Path, profile: Profile
) -> None:
    content = lot().replace(
        "</cac:ProcurementProject>",
        "<cac:ContractExtension><cbc:OptionsDescription>"
        "Der Vertrag hat eine Mindestvertragslaufzeit von 24 Monaten ab Leistungsbeginn."
        """</cbc:OptionsDescription>
        <cac:Renewal><cac:Period><cbc:StartDate>2029-07-01</cbc:StartDate>
        <cbc:EndDate>2030-06-30</cbc:EndDate></cac:Period></cac:Renewal>
        </cac:ContractExtension></cac:ProcurementProject>""",
    )
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {
                        "field": "minimum_service_months",
                        "value": "24",
                        "state": "present",
                        "evidence": ["Mindestvertragslaufzeit"],
                    }
                ]
            }
        }
    )
    [unit], _ = report_for(tmp_path, profile, 100, xml(content), model)
    assert any(
        v.get("kind") == "minimum_service_months" for v in unit["fields"]["duration"]["values"]
    )
    assert unit["fields"]["duration"]["status"] == "present"
    assert not unit["checkpoints"]


def test_eligibility_originals_stay_visible_per_lot(tmp_path: Path, profile: Profile) -> None:
    fixture = (FIXTURES / "real/794059-2026.xml").read_bytes()
    source_texts = [
        e.text
        for e in ET.fromstring(fixture).findall(
            "./cac:ProcurementProjectLot[1]//efac:SelectionCriteria/cbc:Description", NS
        )
        if e.text
        and e.text.startswith(
            ("Eintragung im Handelsregister:", "Betriebshaftpflichtversicherung: Der Bewerber")
        )
    ]
    assert len(source_texts) == 2
    model = fixed_model(
        {
            f"LOT-000{i}": {
                "facts": [
                    {
                        "field": "selection_criteria",
                        "value": value,
                        "state": "present",
                        "evidence": [value],
                    }
                    for value in source_texts
                ],
                "criteria_summaries": [
                    {
                        "field": "selection_criteria",
                        "summary": "Jedes Mitglied braucht nur eine Eigenerklärung.",
                        "evidence": [
                            "Eintragung im Handelsregister:",
                            "Betriebshaftpflichtversicherung: Der Bewerber",
                        ],
                    }
                ],
            }
            for i in (1, 2, 3)
        },
        rejected=tuple(f"u{i}/criteria_summaries:0" for i in range(3)),
    )
    units, brief = report_for(tmp_path, profile, 794059, fixture, model)
    sections = re.split(r"LOT-000[123] Teilnahmestand", brief)[1:]
    assert len(sections) == len(units) == 3
    for index, (unit, section) in enumerate(zip(units, sections, strict=True), 1):
        assert "bis maximal zum 31.05.2031." in section
        assert "wegen eines Nachprüfungsverfahrens" in section
        assert "längstens aber bis zum 30.11.2031" in section
        assert "zur Eintragung verpflichtet" in section
        assert "nicht älter als 6 Monate vom Tag der Teilnahmefrist gerechnet" in section
        assert "spätestens 8 (acht) Wochen nach Zuschlag" in section
        assert "vom bevollmächtigten Mitglied" in section
        assert "von jedem Mitglied der Bewerbergemeinschaft" in section
        assert "Jedes Mitglied braucht nur eine Eigenerklärung." not in section
        register, insurance = [
            v
            for v in unit["fields"]["selection_criteria"]["values"]
            if v["value"].startswith(
                ("Eintragung im Handelsregister:", "Betriebshaftpflichtversicherung: Der Bewerber")
            )
        ]
        for item, phrase in ((register, "6 Monate"), (insurance, "8 (acht) Wochen")):
            [evidence] = item["evidence"]
            assert phrase in evidence["quote"]
            assert evidence["lot_id"] == f"LOT-000{index}"
            assert f"/cac:ProcurementProjectLot[{index}]/" in evidence["path"]


@pytest.mark.parametrize("both_confirmed", [True, False])
def test_eligibility_shows_insurance_amounts_and_alternative_proofs(
    tmp_path: Path, profile: Profile, both_confirmed: bool
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
    short = "Mindestdeckung für Personen-, Sach- und Vermögensschäden: 0,5, 3 und 5 Mio. Euro."
    annual = "Die Jahresgesamtleistung beträgt das Doppelte."
    alternative = (
        "PQ-Nummer, Eigenerklärung oder Einheitliche Europäische Eigenerklärung sind zulässig."
    )
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {"field": "selection_criteria", "value": v, "state": "present", "evidence": [v]}
                    for v in (insurance, proofs, equivalence)
                ],
                "criteria_summaries": [
                    {"field": "selection_criteria", "summary": summary, "evidence": [original]}
                    for summary, original in [
                        (short, insurance),
                        ("Nur die PQ-Nummer ist zulässig.", proofs),
                        (annual, insurance),
                    ]
                ],
            }
        },
        corrections={"u0/criteria_summaries:1": alternative},
        rejected=() if both_confirmed else ("u0/criteria_summaries:2",),
        coverage=(
            ("u0/facts:0", ("u0/criteria_summaries:0", "u0/criteria_summaries:2")),
            ("u0/facts:1", ("u0/criteria_summaries:1",)),
        ),
    )
    [unit], brief = report_for(tmp_path, profile, 100, xml(single_lot, extra=global_note), model)
    assert not unit["processing_errors"]
    visible = brief.split("Eignungskriterien: ")[1].split("Zuschlagskriterien:")[0]
    for value in (short, alternative, equivalence):
        assert visible.count(value) == 1
    assert (annual in visible) == both_confirmed
    assert (insurance in visible) != both_confirmed
    assert proofs not in visible
    assert "Nur die PQ-Nummer ist zulässig." not in visible


@pytest.mark.parametrize("example", [False, True])
def test_request_for_questions_does_not_replace_participation_deadline(
    tmp_path: Path, profile: Profile, example: bool
) -> None:
    request = (
        "Wir bitten Fragen, die den Teilnahmewettbewerb betreffen, bis zum 11.12.2026 zu stellen."
    )
    deadline = lot(day="2026-12-21+01:00", clock="10:00:00+01:00").replace(
        "TenderSubmissionDeadlinePeriod", "ParticipationRequestReceptionPeriod"
    )
    if not example:
        request = "Bitte stellen Sie Fragen zum Teilnahmewettbewerb bis zum 11.12.2026."
    prefix = (
        "Der folgende Satz ist nur ein Beispiel." if example else "Es gilt die Vergabeplattform."
    )
    note = f"<cbc:Note>{prefix} {request} Weitere Hinweise folgen.</cbc:Note>"
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {
                        "field": "information_request_deadline",
                        "value": request,
                        "state": "uncertain",
                        "evidence": [request],
                    }
                ]
            }
        },
        rejected=("u0/facts:0",) if example else (),
    )
    [unit], brief = report_for(tmp_path, profile, 100, xml(deadline, extra=note), model)
    if example:
        assert [d["kind"] for d in unit["fields"]["deadlines"]["values"]] == [
            "ParticipationRequestReceptionPeriod"
        ]
        assert "Rückfragen:" not in brief.split("Informationsqualität und Prüfpunkte")[0]
        return
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
    assert f"Rückfragen: {request} · Uhrzeit ungeklärt" in brief
    multi_lot, _ = report_for(
        tmp_path / "multi", profile, 100, xml(deadline + lot("LOT-2"), extra=note), model
    )
    assert all(
        d["kind"] != "AdditionalInformationRequestPeriod"
        for u in multi_lot
        for d in u["fields"]["deadlines"]["values"]
    )


def test_verified_free_text_binding_and_uncertain_service_start(
    tmp_path: Path, profile: Profile
) -> None:
    binding = "Der Bieter ist 60 Tage an sein Angebot gebunden."
    condition = "Der Leistungsbeginn steht unter dem Vorbehalt der Genehmigung."
    first = lot().replace(
        "</cac:ProcurementProject>",
        f"<cbc:Note>{binding} {condition}</cbc:Note>"
        "<cac:PlannedPeriod><cbc:StartDate>2027-07-01</cbc:StartDate></cac:PlannedPeriod></cac:ProcurementProject>",
    )
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {"field": key, "value": value, "state": state, "evidence": [value]}
                    for key, value, state in [
                        ("tender_validity", binding, "present"),
                        ("duration", condition, "uncertain"),
                    ]
                ]
            }
        }
    )
    units, brief = report_for(tmp_path, profile, 100, xml(first + lot("LOT-2")), model)
    field = units[0]["fields"]["tender_validity"]
    assert field["status"] == "present" and field["values"][0]["evidence"][0]["quote"] == binding
    lot1, lot2 = brief.split("LOT-2")
    assert "Angebotsbindefrist: " + binding in lot1
    duration = lot1.split("Laufzeit: ")[1].split("Eignungskriterien:")[0]
    assert "unsicher" in duration and "Planbeginn: 01.07.2027" in duration and condition in duration
    assert binding not in lot2 and condition not in lot2


def test_rejected_minimum_keeps_xml_duration(tmp_path: Path, profile: Profile) -> None:
    period = (
        '<cac:PlannedPeriod><cbc:DurationMeasure unitCode="MONTH">24</cbc:DurationMeasure>'
        "</cac:PlannedPeriod>"
    )
    content = xml(lot().replace("</cac:ProcurementProject>", period + "</cac:ProcurementProject>"))
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {
                        "field": "minimum_service_months",
                        "value": "24",
                        "state": "present",
                        "evidence": ["24"],
                    }
                ]
            }
        },
        rejected=("u0/facts:0",),
    )
    [unit], brief = report_for(tmp_path, profile, 100, content, model)
    [duration] = unit["fields"]["duration"]["values"]
    assert duration["method"] == "xml" and duration["attributes"]["unitCode"] == "MONTH"
    assert "Laufzeit: 24 Monate" in brief
    assert not any(p.get("method") == "xml_duration_comparison" for p in unit["checkpoints"])


def test_long_overlapping_original_links_to_full_source(tmp_path: Path, profile: Profile) -> None:
    common = "Für jede Referenz ist ein Ansprechpartner anzugeben. "
    source = (
        common + "Je Projekt sind außerdem Auftraggeber, Leistungszeitraum und Auftragswert "
        "anzugeben. Der Ansprechpartner muss über die erbrachte Leistung Auskunft geben können. "
        "Eine Referenz darf von einem ausländischen Auftraggeber stammen."
    )
    summary = "Die Referenzen benötigen einen Ansprechpartner."
    model = fixed_model(
        {
            "LOT-1": {
                "facts": [
                    {
                        "field": "selection_criteria",
                        "value": source,
                        "state": "present",
                        "evidence": [source],
                    }
                ],
                "criteria_summaries": [
                    {"field": "selection_criteria", "summary": summary, "evidence": [source]}
                ],
            }
        }
    )
    _, brief = report_for(tmp_path, profile, 100, xml(lot(criterion=source)), model)
    assert summary in brief and common.strip() not in brief
    reference = re.search(r"Ergänzende Originalpassagen vollständig lesen \[(\d+)\]", brief)
    assert reference
    pdf = next(tmp_path.rglob("bericht.pdf"))
    full = " ".join(" ".join(p.extract_text() for p in PdfReader(pdf).pages).split())
    appendix = full.split("Belegverzeichnis · TED")[1]
    entry = appendix.split(f"[{reference[1]}] TED 100-2026", 1)[1].split("] TED 100-2026", 1)[0]
    assert "Eine Referenz darf von einem ausländischen Auftraggeber stammen." in entry
