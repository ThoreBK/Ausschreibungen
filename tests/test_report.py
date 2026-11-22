"""Abnahme am erzeugten PDF einschließlich Suchfehlern und getrennten Losen."""

import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from pypdf import PageObject, PdfReader

import main
from ausschreibungen.analysis import PROPOSAL, analyze_run, extract
from ausschreibungen.report import write_report
from ausschreibungen.selection import select_results
from ausschreibungen.ted import Profile, Query, SearchError
from tests.test_analysis import (
    FIXTURES,
    NOW,
    PROFILE,
    ControlledModel,
    citation,
    lot,
    proposal,
    xml,
)
from tests.test_research import Network, execute, response, row


@pytest.mark.parametrize("failed", [True, False])
def test_report_cli_distinguishes_empty_and_failed(
    failed: bool,
    tmp_path: Path,
    profile: Profile,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = [SearchError("TED offline") if failed else response(), response()]
    research, run = execute(tmp_path, profile, Network(answers, {}))
    monkeypatch.setattr(main, "collect", lambda *args, **kwargs: (research, run))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--report",
            "--config",
            str(profile_path),
            "--output",
            str(tmp_path / "copy.json"),
        ],
    )
    assert main.main() == int(failed)
    text = PdfReader(run / "bericht.pdf").pages[0].extract_text()
    if failed:
        assert "1 von 2 Suchgruppen erfolgreich abgefragt" in text
        assert "TED offline" in text
        assert "Keine Treffer im Suchbereich" not in text
    else:
        assert "2 von 2 Suchgruppen erfolgreich abgefragt" in text
        assert "Keine Treffer im Suchbereich" in text
        assert "unvollständig" not in text


@pytest.mark.parametrize(
    ("terms", "codes", "expected", "filter_text", "absent"),
    [
        (
            [["Copilot", "Microsoft 365"], ["Schulung"]],
            [],
            "(Copilot ODER Microsoft 365) UND Schulung",
            "keiner",
            "72200000",
        ),
        (
            [["Power Automate"], ["Entwicklung", "Integration"]],
            ["72200000"],
            "Power Automate UND (Entwicklung ODER Integration)",
            "72200000",
            "Schulung",
        ),
    ],
)
def test_pdf_distinguishes_searches_with_identical_names(
    tmp_path: Path,
    profile: Profile,
    terms: list[list[str]],
    codes: list[str],
    expected: str,
    filter_text: str,
    absent: str,
) -> None:
    profile = replace(profile, queries=[Query("Digitalisierung", terms)], cpv_codes=codes)
    network = Network([response()], {})
    research, run = execute(tmp_path, profile, network)
    page = PdfReader(write_report(research, None, run)).pages[0]
    text = " ".join(page.extract_text().split())
    assert f"Digitalisierung: {expected}" in text
    assert f"CPV-Filter: {filter_text}" in text
    assert absent not in text
    assert run.name in text
    uri = page["/Annots"][0].get_object()["/A"]["/URI"]
    overview = run / uri
    assert overview == run / "overview.html"
    assert 'href="results.json"' in overview.read_text("utf-8")
    archived = json.loads(overview.with_name("results.json").read_bytes())
    assert archived["run_id"] == run.name
    assert archived["queries"][0]["request"] == network.search_requests[0]


def test_pdf_names_both_limits_and_links_from_analysis(tmp_path: Path, profile: Profile) -> None:
    network = Network(
        [dict(response(row(100, 14)), totalNoticeCount=4), response(row(101, 13))],
        {"https://ted.europa.eu/en/notice/100-2026/xml": xml(lot())},
    )
    research, run = execute(tmp_path, replace(profile, max_results=1), network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    page = PdfReader(write_report(research, analysis, directory)).pages[0]
    text = " ".join(page.extract_text().split())
    assert "TED meldete für mindestens eine Suchgruppe weitere Treffer." in text
    assert "Gesamtlimit: 1 von 2 verschiedenen gelieferten Bekanntmachungen ausgewählt." in text
    links = [ref.get_object().get("/A", {}).get("/URI") for ref in page["/Annots"]]
    assert "../../overview.html" in links
    assert (directory / "../../overview.html").samefile(run / "overview.html")


@pytest.mark.parametrize(
    ("dates", "times", "expected", "participation"),
    [
        (
            ["2026-12-01Z", "2026-12-10Z"],
            ["12:00:00Z"],
            "Datum widersprüchlich (2026-12-01Z oder 2026-12-10Z), 12:00:00Z",
            "ungeklärt",
        ),
        (
            ["2026-12-01Z"],
            ["12:00:00Z", "16:00:00Z"],
            "2026-12-01Z, Uhrzeit widersprüchlich (12:00:00Z oder 16:00:00Z)",
            "ungeklärt",
        ),
        (
            ["2026-12-01Z"] * 2,
            ["12:00:00Z"] * 2,
            "01.12.2026, 13:00 MEZ",
            "Frist offen",
        ),
        ([], ["12:00:00Z"], "Datum nicht angegeben, 12:00:00Z", "ungeklärt"),
        (
            ["2026-12-01Z", "2026-12-01+00:00"],
            ["12:00:00+00:00", "12:00:00Z"],
            "01.12.2026, 13:00 MEZ",
            "Frist offen",
        ),
        (
            ["2026-12-01Z", "2026-12-01+01:00"],
            ["12:00:00Z"],
            "Datum widersprüchlich (2026-12-01Z oder 2026-12-01+01:00), 12:00:00Z",
            "ungeklärt",
        ),
        (["2026-12-01Z"], [], "2026-12-01Z, Uhrzeit nicht angegeben", "ungeklärt"),
        (
            ["2026-12-01"],
            ["12:00:00"],
            "2026-12-01, 12:00:00 · Zeitzone nicht angegeben",
            "ungeklärt",
        ),
        (
            ["2026-12-01Z"],
            ["12:00:00+02:00"],
            "2026-12-01Z, 12:00:00+02:00 · Zeitzonenangaben widersprechen sich",
            "ungeklärt",
        ),
    ],
)
def test_deadline_in_finished_pdf(
    tmp_path: Path,
    profile: Profile,
    dates: list[str],
    times: list[str],
    expected: str,
    participation: str,
) -> None:
    components = "".join(f"<cbc:EndDate>{v}</cbc:EndDate>" for v in dates)
    components += "".join(f"<cbc:EndTime>{v}</cbc:EndTime>" for v in times)
    content = lot().replace(
        "<cbc:EndDate>2026-12-01Z</cbc:EndDate><cbc:EndTime>12:00:00Z</cbc:EndTime>", components
    )
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {
                "https://ted.europa.eu/en/notice/100-2026/xml": xml(
                    content + lot("LOT-2", day="2027-03-04Z")
                )
            },
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    reader = PdfReader(write_report(research, analysis, directory))
    overview = " ".join(reader.pages[0].extract_text().split())
    assert re.search(rf"LOT-1 · TED 100-2026 unklar {participation}\b", overview)
    text = " ".join(" ".join(p.extract_text() for p in reader.pages[1:]).split())
    briefs, sources = text.split("Belegverzeichnis · TED")
    parts = re.split(r"(LOT-[12]) Teilnahmestand:", briefs)
    by_lot = dict(zip(parts[1::2], parts[2::2], strict=True))
    first, second = by_lot["LOT-1"], by_lot["LOT-2"]
    line = first.split("Angebotsfrist: ")[1].split(" Angebotsbindefrist:")[0]
    match = re.fullmatch(re.escape(expected) + r" \[([\d, ]+)\]", line)
    assert match
    refs = match[1].split(", ")
    assert len(refs) == len(dates) + len(times)
    for ref, (leaf, index, value) in zip(
        refs,
        [
            (leaf, i, v)
            for leaf, values in [("EndDate", dates), ("EndTime", times)]
            for i, v in enumerate(values, 1)
        ],
        strict=True,
    ):
        entry = re.split(r"\[\d+\] TED ", sources.split(f"[{ref}] TED ", 1)[1], maxsplit=1)[0]
        assert f"cbc:{leaf}[{index}] {value}" in entry
    assert "2027-03-04Z" not in first
    assert "Angebotsfrist: 04.03.2027, 13:00 MEZ" in second


def test_pdf_separates_deadline_periods_and_kinds(tmp_path: Path, profile: Profile) -> None:
    def period(kind: str, day: str, detail: str = "") -> str:
        return f"<cac:{kind}><cbc:EndDate>{day}</cbc:EndDate>{detail}</cac:{kind}>"

    extra = (
        period("TenderSubmissionDeadlinePeriod", "2026-12-15Z")
        + period(
            "ParticipationRequestReceptionPeriod",
            "2026-11-20Z",
            "<cbc:Description>Phase A</cbc:Description>",
        )
        + period("AdditionalInformationRequestPeriod", "2026-11-18Z")
    )
    content = lot().replace("</cac:TenderingProcess>", extra + "</cac:TenderingProcess>")
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": xml(content)},
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    reader = PdfReader(write_report(research, analysis, directory))
    assert "unklar ungeklärt" in " ".join(reader.pages[0].extract_text().split())
    brief = " ".join(reader.pages[1].extract_text().split())
    assert "Angebotsfrist: 01.12.2026, 13:00 MEZ" in brief
    assert (
        "Angebotsfrist: 2026-12-15Z, Uhrzeit nicht angegeben · Zuordnung zur Verfahrensphase prüfen"
        in brief
    )
    assert "Frist für Teilnahmeanträge (Phase A): 2026-11-20Z, Uhrzeit nicht angegeben" in brief
    assert "Frist für Rückfragen: 2026-11-18Z, Uhrzeit nicht angegeben" in brief
    assert "widersprüchlich" not in brief


def test_report_includes_scoped_decisions_fields_and_sources(
    tmp_path: Path, profile: Profile
) -> None:
    network = Network(
        [response(row(100, 14)), response()],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(
                lot("LOT-1") + lot("LOT-2", subject="Reinigung", criterion="Meisterbrief")
            )
        },
    )
    research, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis: dict[str, Any] = json.loads((directory / "analysis.json").read_bytes())
    reader = PdfReader(write_report(research, analysis, directory))
    first = " ".join(reader.pages[0].extract_text().split())
    assert "LOT-1 · TED 100-2026 unklar Frist offen" in first
    assert "LOT-2 · TED 100-2026 unklar" in first
    assert "Teilnahmevoraussetzungen: ungeklärt" in first
    assert "16.11.2026, 16:00" in first
    assert "in dieser Version nicht abgerufen und nicht ausgewertet" in first
    annotations = [ref.get_object() for ref in reader.pages[0]["/Annots"]]
    assert any(
        a.get("/A", {}).get("/URI") == "https://ted.europa.eu/de/notice/-/detail/100-2026"
        for a in annotations
    )
    assert any(
        a["/Dest"][0].idnum == reader.pages[1].indirect_reference.idnum
        for a in annotations
        if "/Dest" in a
    )
    detail = " ".join(" ".join(p.extract_text() for p in reader.pages[1:]).split())
    brief, sources = detail.split("Belegverzeichnis · TED 100-2026")
    lot1, lot2 = brief.split("LOT-2", 1)
    for section in (lot1, lot2):
        assert "Eignungskriterien: keine geprüfte Kurzfassung · Originalangaben" in section
        assert "Zuschlagskriterien: nicht angegeben" in section
    assert "Auftraggeber: nicht angegeben" in lot1
    assert "Angebotsfrist: 01.12.2026, 13:00 MEZ" in lot1
    assert "Referenz über zwei KI-Schulungen" in sources
    assert "Meisterbrief" in sources
    assert "/cbc:Description[1]" in sources
    destinations = [
        ann["/Dest"][0].idnum
        for page in reader.pages[1:]
        for annotation in page.get("/Annots", [])
        if "/Dest" in (ann := annotation.get_object())
    ]
    assert reader.pages[-2].indirect_reference.idnum in destinations


@pytest.mark.parametrize(
    ("label", "confirmed", "expected"),
    [
        ("Angebotsfrist", True, "ungeklärt"),
        ("Angebotsfrist", False, "Frist offen"),
        ("Rückfragefrist", True, "Frist offen"),
    ],
)
def test_conflicting_deadline_excerpt_in_pdf(
    tmp_path: Path, profile: Profile, label: str, confirmed: bool, expected: str
) -> None:
    quote = f"{label}: 05.11.2026, 09:00 Uhr"
    note = f"Termine für dieses Verfahren. {quote}. Die Abgabe erfolgt elektronisch."
    content = xml(lot(), extra=f"<cbc:Note>{note}</cbc:Note>")
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": content},
        ),
    )
    doc = extract(content, "100-2026", now=NOW)
    answer = proposal(doc)
    answer["facts"] = [
        {
            "field": "deadlines",
            "value": quote,
            "state": "conflict",
            "evidence": [citation(doc, quote)],
        }
    ]
    model = ControlledModel(answer, {"facts": [confirmed], "fit": True})
    directory = analyze_run(run, PROFILE, now=NOW, model=model)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    pages = PdfReader(write_report(research, analysis, directory)).pages
    overview, brief = [" ".join(p.extract_text().split()) for p in pages[:2]]
    assert f"LOT-1 · TED 100-2026 passend {expected}" in overview
    assert f"Teilnahmestand: {expected}." in brief
    if confirmed and label == "Angebotsfrist":
        assert f"{quote} · Widerspruch" in brief
        unit = analysis["documents"][0]["units"][0]
        assert {e["quote"] for e in unit["participation"]["evidence"]} == {
            "2026-12-01Z",
            "12:00:00Z",
            quote,
        }


@pytest.mark.parametrize(
    ("code", "confirmed", "expected"),
    [("allowed", True, "conflict"), ("required", True, "present"), ("allowed", False, "uncertain")],
)
def test_confirmed_submission_rule_is_visible_and_compared_with_xml(
    tmp_path: Path, profile: Profile, code: str, confirmed: bool, expected: str
) -> None:
    note = "Offers must be submitted exclusively through the electronic procurement portal."
    content = xml(
        lot().replace(
            "<cac:TenderingProcess>",
            f"<cac:TenderingProcess><cbc:SubmissionMethodCode>{code}</cbc:SubmissionMethodCode>",
        ),
        extra=f"<cbc:Note>{note}</cbc:Note>",
    )
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": content},
        ),
    )
    doc = extract(content, "100-2026", now=NOW)
    answer = proposal(doc)
    answer["facts"] = [
        {
            "field": "electronic_submission_required",
            "value": note,
            "state": "present",
            "evidence": [citation(doc, note)],
        }
    ]
    model = ControlledModel(answer, {"facts": [confirmed], "fit": True})
    directory = analyze_run(run, PROFILE, model=model, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    result = analysis["documents"][0]
    unit = result["units"][0]
    assert unit["fields"]["submission"]["status"] == expected
    assert ("submission" in unit["information_quality"]["conflicts"]) == (expected == "conflict")
    assert result["status"] == ("complete" if confirmed and code == "required" else "incomplete")
    reader = PdfReader(write_report(research, analysis, directory))
    brief = " ".join(reader.pages[1].extract_text().split())
    field = brief.split("Abgabeform: ")[1].split("Quellenlink:")[0]
    assert (note in field) == confirmed
    if expected == "conflict":
        assert field.startswith("Widerspruch · " + note)
        assert "Strukturierte Angabe: Elektronische Abgabe zulässig" in field
        assert [v["evidence"][0]["quote"] for v in unit["fields"]["submission"]["values"]] == [
            "allowed",
            note,
        ]


def test_performance_region_keeps_its_meaning_despite_unrelated_location_text(
    tmp_path: Path, profile: Profile
) -> None:
    number = "773064-2026"
    content = (FIXTURES / "real" / f"{number}.xml").read_bytes()
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(773064, 14)), response()],
            {f"https://ted.europa.eu/en/notice/{number}/xml": content},
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    doc = analysis["documents"][0]
    [place] = doc["units"][0]["fields"]["place"]["values"]
    assert place["value"] == place["evidence"][0]["quote"] == "anyw"
    assert place["evidence"][0]["path"].endswith("/cac:Address[1]/cbc:Region[1]")
    assert any("in deutscher Sprache bedienbar" in r["value"] for r in doc["records"])
    reader = PdfReader(write_report(research, analysis, directory))
    brief = " ".join(reader.pages[1].extract_text().split())
    assert re.search(r"Leistungsort: Beliebiger Ort \[\d+\] Verfahrensart:", brief)


def test_freetext_deadline_type_does_not_resolve_conflicting_offsets(
    tmp_path: Path, profile: Profile
) -> None:
    note = "Requests to participate must arrive by 07.01.2027, 10:00 Uhr."
    content = xml(
        lot(day="2027-01-07+01:00", clock="10:00:00+02:00").replace(
            "TenderSubmissionDeadlinePeriod", "ParticipationRequestReceptionPeriod"
        ),
        extra=f"<cbc:Note>{note}</cbc:Note>",
    )
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": content},
        ),
    )
    doc = extract(content, "100-2026", now=NOW)
    answer = proposal(doc)
    answer["facts"] = [
        {
            "field": "participation_request_deadline",
            "value": note,
            "state": "uncertain",
            "evidence": [citation(doc, note)],
        }
    ]
    directory = analyze_run(run, PROFILE, model=ControlledModel(answer), now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    unit = analysis["documents"][0]["units"][0]
    assert unit["participation"]["status"] == "ungeklärt"
    field = unit["fields"]["deadlines"]
    assert field["status"] == "conflict"
    assert [v["berlin"] for v in field["values"]] == [None, None]
    reader = PdfReader(write_report(research, analysis, directory))
    brief = " ".join(reader.pages[1].extract_text().split())
    assert f"Frist für Teilnahmeanträge: {note} · unsicher" in brief
    assert "2027-01-07+01:00, 10:00:00+02:00" in brief
    assert "Art ungeklärt" not in brief


def test_award_with_historical_questions_stays_closed_in_pdf(
    tmp_path: Path, profile: Profile
) -> None:
    fixtures = Path(__file__).parent / "fixtures" / "real"
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(801658, 14)), response()],
            {
                "https://ted.europa.eu/en/notice/801658-2026/xml": (
                    fixtures / "801658-2026.xml"
                ).read_bytes()
            },
        ),
    )

    def replay(
        instructions: str, payload: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        name = "proposal" if schema == PROPOSAL else "verification"
        answer = json.loads((fixtures / f"801658-{name}.json").read_bytes())
        if schema == PROPOSAL:
            # Der archivierte Lauf liegt vor der Einführung von Kriterienkurzfassungen.
            answer["units"][0]["criteria_summaries"] = []
        return answer

    directory = analyze_run(run, PROFILE, now=NOW, model=replay)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    unit = analysis["documents"][0]["units"][0]
    assert unit["lot_id"] == "LOT-0001"
    assert any(
        "Bieterfragen" in d.get("original", "") for d in unit["fields"]["deadlines"]["values"]
    )
    assert {e["quote"] for e in unit["participation"]["evidence"]} >= {
        "can-standard",
        "LOT-0001",
        "selec-w",
    }
    pages = PdfReader(write_report(research, analysis, directory)).pages
    overview = " ".join(pages[0].extract_text().split())
    assert not analysis["selection"]["selected"]
    [entry] = analysis["selection"]["excluded"]
    assert entry["publication_number"] == "801658-2026"
    assert entry["exclusion_reasons"] == ["nicht offen"]
    assert "1 ausgeschlossen" in overview and "801658-2026" not in overview
    html = (directory / "analysis.html").read_text("utf-8")
    assert "TED 801658-2026</a> · LOT-0001 · nicht offen" in html


def test_partial_download_keeps_success_and_failed_notice(tmp_path: Path, profile: Profile) -> None:
    network = Network(
        [response(row(100, 14), row(101, 13)), response()],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(lot()),
            "https://ted.europa.eu/en/notice/101-2026/xml": SearchError("TED-Download abgebrochen"),
        },
    )
    research, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    reader = PdfReader(
        write_report(research, json.loads((directory / "analysis.json").read_bytes()), directory)
    )
    pages = [" ".join(page.extract_text().split()) for page in reader.pages]
    assert all(number in pages[0] for number in ["100-2026", "101-2026"])
    assert "Recherche unvollständig" in pages[0]
    assert "Gegenstand: KI-Beratung" in pages[1]
    assert "Referenz über zwei KI-Schulungen" in pages[-2]
    assert "TED-Download abgebrochen" in pages[2]
    assert "TED 101-2026" in pages[2]


def test_long_repeated_criteria_keep_each_source(tmp_path: Path, profile: Profile) -> None:
    common = "Nachweis für die Wartung automatisierter Systeme. " * 10
    criteria = "".join(f"<cbc:Description>{common}Fall {i}</cbc:Description>" for i in range(7))
    repeated = f"<cbc:Description>{common}Fall 6</cbc:Description>"
    content = lot(criterion="Platzhalter").replace(
        "<cbc:Description>Platzhalter</cbc:Description>", criteria + repeated
    )
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": xml(content)},
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    reader = PdfReader(
        write_report(research, json.loads((directory / "analysis.json").read_bytes()), directory)
    )
    text = " ".join(" ".join(page.extract_text() for page in reader.pages).split())
    brief, sources = text.split("Belegverzeichnis · TED 100-2026")
    assert "Eignungskriterien: keine geprüfte Kurzfassung · Originalangaben" in brief
    assert common.strip() not in brief
    assert "/cbc:Description[7]" in sources and "/cbc:Description[8]" in sources
    assert "Gleicher Wortlaut wie Beleg" in sources
    assert "Fall 6" in sources


def locate_pdf_line(pages: list[PageObject], pattern: str) -> tuple[PageObject, float]:
    positions = []

    def visit(text: str, cm: list[float], tm: list[float], _font: Any, _size: float) -> None:
        if re.search(pattern, " ".join(text.split())):
            positions.append(cm[5] + tm[5])

    for page in pages:
        page.extract_text(visitor_text=visit)
        if positions:
            return page, positions[0]
    raise AssertionError(f"PDF-Zeile nicht gefunden: {pattern}")


def test_report_uses_confirmed_criteria_and_links_to_unabridged_originals(
    tmp_path: Path, profile: Profile
) -> None:
    eligibility = {
        "LOT-1": "Bewerberauswahl: Los 1 erhält 3 Punkte ab 750 Beschäftigten.",
        "LOT-2": "Bewerberauswahl: Los 2 erhält 3 Punkte ab 500 Beschäftigten oder "
        "ab 300 Beschäftigten und 200 Honorarkräften.",
    }
    criteria = {
        lot_id: f"{eligibility['LOT-1']} {eligibility['LOT-2']} "
        f"Die Angaben zur Bewerberauswahl werden jährlich überprüft. Detailbeleg {lot_id}."
        for lot_id in eligibility
    }
    weighting = {"LOT-1": 35, "LOT-2": 60}
    awards = {
        lot_id: f"Preisgewichtung: {weight} Prozent. Die Einzelheiten zum Vergleich der "
        "angebotenen Preise stehen in der Zuschlagsmatrix."
        for lot_id, weight in weighting.items()
    }
    content = xml(
        "".join(
            lot(lot_id, subject=f"KI-Beratung {lot_id}", criterion=criteria[lot_id]).replace(
                "</cac:TenderingTerms>",
                "<cac:AwardingTerms><cac:AwardingCriterion>"
                f"<cbc:Description>{awards[lot_id]}</cbc:Description>"
                "</cac:AwardingCriterion></cac:AwardingTerms></cac:TenderingTerms>",
            )
            for lot_id in eligibility
        )
    )
    summaries = {
        "LOT-1": (
            "Ab 750 Beschäftigten gibt es bei der Bewerberauswahl die vollen drei Punkte.",
            "Der Preis zählt 35 %.",
        ),
        "LOT-2": (
            "Drei Punkte gibt es ab 500 Beschäftigten oder ab 300 Beschäftigten "
            "und 200 Honorarkräften.",
            "Der Preis zählt 60 %.",
        ),
    }
    wrong_rule = "Eine Mindestgröße von 750 Beschäftigten ist erforderlich."
    foreign_rule = "Der Preis zählt auch in Los 2 nur 35 %."
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {"https://ted.europa.eu/en/notice/100-2026/xml": content},
        ),
    )

    def model(instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        def source(lot_id: str, text: str) -> dict[str, str]:
            return {
                "source": next(
                    r["id"]
                    for r in payload["records"]
                    if r["lot_id"] == lot_id and payload["texts"][r["text_id"]] == text
                )
            }

        if schema == PROPOSAL:
            units = []
            for unit in payload["units"]:
                lot_id = unit["lot_id"]
                selection, award = summaries[lot_id]
                items = [
                    {
                        "field": "selection_criteria",
                        "summary": selection,
                        "evidence": [source(lot_id, criteria[lot_id])],
                    },
                    {
                        "field": "award_criteria",
                        "summary": award,
                        "evidence": [source(lot_id, awards[lot_id])],
                    },
                ]
                if lot_id == "LOT-2":
                    items.extend(
                        [
                            {**items[0], "summary": wrong_rule},
                            {
                                **items[1],
                                "summary": foreign_rule,
                                "evidence": [source("LOT-1", awards["LOT-1"])],
                            },
                        ]
                    )
                units.append(
                    {
                        "unit_id": unit["unit_id"],
                        "facts": [],
                        "criteria_summaries": items,
                        "fit": {
                            "status": "passend",
                            "reason": "KI-Beratung ist ausgeschrieben.",
                            "evidence": [source(lot_id, f"KI-Beratung {lot_id}")],
                        },
                        "checkpoints": [],
                    }
                )
            return {"units": list(reversed(units))}
        proposed = {c["claim"].get("summary") for c in payload["claims"]}
        assert wrong_rule in proposed and foreign_rule not in proposed
        return {
            "claims": [
                {
                    "claim_id": c["claim_id"],
                    "status": "widerlegt"
                    if c["claim"].get("summary") == wrong_rule
                    else "bestätigt",
                    "reason": (
                        "Das ist eine Punkteschwelle eines anderen Loses."
                        if c["claim"].get("summary") == wrong_rule
                        else "Die Originalangaben tragen die Aussage."
                    ),
                    "evidence": [{"source": ref["source"]} for ref in c["claim"]["evidence"]],
                }
                for c in reversed(payload["claims"])
            ]
        }

    directory = analyze_run(run, PROFILE, model=model, now=NOW)
    reader = PdfReader(
        write_report(research, json.loads((directory / "analysis.json").read_bytes()), directory)
    )
    pages = [" ".join(p.extract_text().split()) for p in reader.pages]
    appendix = next(i for i, text in enumerate(pages) if "Belegverzeichnis · TED" in text)
    brief = " ".join(pages[1:appendix])
    first, second = re.split(r"LOT-[12] Teilnahmestand", brief)[1:]
    assert wrong_rule not in brief and foreign_rule not in brief
    assert "Kurzfassung der Kriterien nicht bestätigt" in second
    assert "gehört zu anderem Los" in second
    sources = " ".join(pages[appendix:])
    for i, section in enumerate((first, second), 1):
        lot_id = f"LOT-{i}"
        assert all(text not in section for text in summaries[f"LOT-{3 - i}"])
        for label, short, original in zip(
            ("Eignungskriterien", "Zuschlagskriterien"),
            summaries[lot_id],
            (criteria[lot_id], awards[lot_id]),
            strict=True,
        ):
            match = re.search(rf"{label}: {re.escape(short)} \[(\d+)\]", section)
            assert match is not None, section
            index = int(match[1])
            source_entry = re.split(
                r"\[\d+\] TED 100-2026", sources.split(f"[{index}] TED 100-2026")[1]
            )[0]
            assert f"cac:ProcurementProjectLot[{i}]" in source_entry
            assert original in source_entry
            assert original not in section

            page, y = locate_pdf_line(reader.pages[1:appendix], rf"\[{index}\]$")
            target_page, target_y = locate_pdf_line(
                reader.pages[appendix:], rf"^\[{index}\] TED 100-2026"
            )
            destinations = [
                annotation["/Dest"]
                for ref in page.get("/Annots", [])
                if "/Dest" in (annotation := ref.get_object())
                and annotation["/Rect"][1] <= y <= annotation["/Rect"][3]
            ]
            assert len(destinations) == 1
            target = destinations[0]
            assert target[0].idnum == target_page.indirect_reference.idnum
            assert 0 <= target[3] - target_y < 15


def test_overview_prioritizes_open_matches_and_links_to_each_lot(
    tmp_path: Path, profile: Profile
) -> None:
    research, run = execute(
        tmp_path,
        profile,
        Network(
            [response(row(100, 14)), response()],
            {
                "https://ted.europa.eu/en/notice/100-2026/xml": xml(
                    lot("LOT-1", subject="Reinigung") + lot("LOT-2", subject="IT-Beratung")
                )
            },
        ),
    )
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    first, second = analysis["documents"][0]["units"]
    for unit, status in [(first, "unklar"), (second, "passend")]:
        unit["fit"] = {
            "status": status,
            "method": "ai_verified",
            "reason": "Kontrollierte Einschätzung für die Darstellung",
            "evidence": unit["fields"]["subject"]["values"][0]["evidence"],
        }
    second["checkpoints"] = [
        {
            "method": "ai_verified",
            "reason": reason,
            "evidence": second["fields"]["subject"]["values"][0]["evidence"],
        }
        for reason in ["Referenzen prüfen.", "Einzelheiten der Wertung prüfen."]
    ]
    analysis["selection"] = select_results(research, analysis["documents"], 20)
    reader = PdfReader(write_report(research, analysis, directory))
    overview, brief = [" ".join(page.extract_text().split()) for page in reader.pages[:2]]
    assert "1 fachlich passend mit offener Frist" in overview
    assert overview.index("LOT-2") < overview.index("LOT-1")
    assert overview.count("Teilnahmevoraussetzungen: ungeklärt") == 1
    assert "Referenzen prüfen." in brief and "Einzelheiten der Wertung prüfen." not in brief
    assert "Weitere Prüfpunkte (1)" in brief
    assert "Einzelheiten der Wertung prüfen." in reader.pages[3].extract_text()
    links = [
        ref.get_object()["/Dest"][0].idnum
        for ref in reader.pages[0]["/Annots"]
        if "/Dest" in ref.get_object()
    ]
    assert links[:2] == [reader.pages[i].indirect_reference.idnum for i in (1, 2)]
