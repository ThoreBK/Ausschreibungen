"""Abnahme am erzeugten PDF einschließlich Suchfehlern und getrennten Losen."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

import main
from ausschreibungen.analysis import analyze_run
from ausschreibungen.report import write_report
from ausschreibungen.ted import Profile, SearchError
from tests.test_analysis import NOW, PROFILE, lot, xml
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
        assert "TED offline" in text
        assert "Keine Treffer im Suchbereich" not in text
    else:
        assert "Keine Treffer im Suchbereich" in text
        assert "unvollständig" not in text


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
    assert "LOT-1 · Passung: unklar · Teilnahmestand: Frist offen" in first
    assert "LOT-2 · Passung: unklar" in first
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
    lot1, lot2 = detail.split("LOT-2", 1)
    assert "Referenz über zwei KI-Schulungen" in lot1
    assert "Meisterbrief" not in lot1
    assert "Meisterbrief" in lot2
    assert "Auftraggeber: nicht angegeben" in lot1
    assert "Angebotsfrist: 2026-12-01Z, 12:00:00Z" in lot1
    assert "Belegverzeichnis · TED 100-2026" in lot2
    assert "/cbc:Description[1]" in lot2
    destinations = [
        ann["/Dest"][0].idnum
        for page in reader.pages[1:]
        for annotation in page.get("/Annots", [])
        if "/Dest" in (ann := annotation.get_object())
    ]
    assert reader.pages[-1].indirect_reference.idnum in destinations


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
    assert "Referenz über zwei KI-Schulungen" in pages[1]
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
    assert "Weitere Angaben im Belegverzeichnis" in brief
    assert "/cbc:Description[7]" in sources and "/cbc:Description[8]" in sources
    assert "Gleicher Wortlaut wie Beleg" in sources
    assert "Fall 6" in sources
