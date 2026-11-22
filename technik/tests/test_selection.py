"""TASK-5: belegte Passung, belastbare Identität und nachvollziehbare Dokumentstände."""

import json
import sys
from dataclasses import replace
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader

import main
from ausschreibungen.analysis import PROPOSAL, Model, analyze_run
from ausschreibungen.extraction import extract
from ausschreibungen.report import write_report
from ausschreibungen.research import collect
from ausschreibungen.ted import Profile, search
from tests.support.notices import FIXTURES, NOW, PROFILE, lot, xml
from tests.support.research import Network, execute, response, row

Data = dict[str, Any]
ORIGINAL = "fe845e3b-c2a7-4183-b842-0b6ada5b9cfa"
PROCEDURE = "5a0d592d-b0c3-40fd-ad6a-ceaf95251829"


def notice(
    number: int,
    identifier: str,
    lots: str,
    *,
    previous: str = "",
    procedure: str = PROCEDURE,
) -> bytes:
    content = xml(lots, extra=f"<cbc:ContractFolderID>{procedure}</cbc:ContractFolderID>")
    content = content.replace(b"100-2026", f"{number}-2026".encode())
    content = content.replace(b"<cbc:ID>notice</cbc:ID>", f"<cbc:ID>{identifier}</cbc:ID>".encode())
    if previous:
        change = f"""
        <efac:Changes><efbc:ChangedNoticeIdentifier>{previous}</efbc:ChangedNoticeIdentifier>
        <efac:Change><efac:ChangedSection>
          <efbc:ChangedSectionIdentifier>LOT-1</efbc:ChangedSectionIdentifier>
          <efbc:ChangeDescription>Neue Frist für Los 1.</efbc:ChangeDescription>
        </efac:ChangedSection></efac:Change></efac:Changes>
        """
        content = content.replace(b"<efac:Publication>", change.encode() + b"<efac:Publication>")
    return content


def download_urls(documents: dict[int, bytes]) -> dict[str, bytes | Exception]:
    return {f"https://ted.europa.eu/en/notice/{n}-2026/xml": xml for n, xml in documents.items()}


def evaluate(_: str, payload: Data, schema: Data) -> Data:
    """Feste fachliche Urteile für die Leistungsbeschreibungen des CLI-Testlaufs."""
    verdicts = {
        "Konzeption und Einführung eines KI-Assistenten": "passend",
        "Schulung zu Microsoft 365": "passend",
        "Entwicklung von Power-Automate-Workflows": "passend",
        "Unterhaltsreinigung der Büroflächen": "unpassend",
        "Beratungsleistungen nach weiterer Abstimmung": "unklar",
    }
    if schema == PROPOSAL:
        units = []
        for unit in payload["units"]:
            record = next(
                r
                for r in payload["records"]
                if r["lot_id"] == unit["lot_id"]
                and r["path"].endswith("/cbc:Description[1]")
                and payload["texts"][r["text_id"]] in verdicts
            )
            units.append(
                {
                    "unit_id": unit["unit_id"],
                    "facts": [],
                    "criteria_summaries": [],
                    "checkpoints": [],
                    "fit": {
                        "status": verdicts[payload["texts"][record["text_id"]]],
                        "reason": "Maßgeblich ist die zitierte Leistungsbeschreibung.",
                        "evidence": [{"source": record["id"]}],
                    },
                }
            )
        return {"units": units}
    return {
        "claims": [
            {
                "claim_id": c["claim_id"],
                "status": "bestätigt",
                "reason": "Beleg trägt die Einschätzung.",
                "evidence": [{"source": e["source"]} for e in c["claim"]["evidence"]],
            }
            for c in payload["claims"]
        ]
    }


def test_report_selects_and_consolidates_before_applying_limit(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assistant = "Konzeption und Einführung eines KI-Assistenten"
    training = lot("LOT-2", day="2027-01-08Z", subject="Schulung zu Microsoft 365")
    old_lots = lot(day="2026-11-10Z", subject=assistant) + training
    new_lots = lot(day="2026-12-18Z", subject=assistant) + training
    unrelated = "90000000-0000-4000-8000-000000000000"
    network = Network(
        [
            response(row(102, 15), row(103, 14), row(105, 14), row(106, 13)),
            response(row(100, 9), row(101, 9), row(102, 15), row(104, 8)),
        ],
        download_urls(
            {
                100: notice(100, ORIGINAL, old_lots),
                101: notice(101, ORIGINAL, old_lots),
                102: notice(102, "change", new_lots, previous=ORIGINAL + "-01"),
                103: notice(
                    103,
                    "cleaning",
                    lot(subject="Unterhaltsreinigung der Büroflächen"),
                    procedure=unrelated + "-cleaning",
                ),
                104: notice(
                    104,
                    "workflow",
                    lot(day="2026-12-01Z", subject="Entwicklung von Power-Automate-Workflows"),
                    procedure=unrelated,
                ),
                105: notice(
                    105,
                    "unknown",
                    lot(
                        day="2026-12-02",
                        clock="09:00:00",
                        subject="Beratungsleistungen nach weiterer Abstimmung",
                    ),
                    procedure=unrelated + "-unknown",
                ),
                106: notice(
                    106,
                    "closed",
                    lot(day="2026-11-10Z", subject=assistant),
                    procedure=unrelated + "-closed",
                ),
            }
        ),
    )
    config = tmp_path / "search.toml"
    config.write_text(
        profile_path.read_text("utf-8").replace(
            "max_results = 20", "max_results = 4\nreport_limit = 2"
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "Demo Berichte"
    output = output_dir / "ted-results.json"
    monkeypatch.setattr(main, "search", partial(search, transport=network.search))
    monkeypatch.setattr(main, "collect", partial(collect, download=network.download))
    monkeypatch.setattr(main, "analyze_run", partial(analyze_run, model=evaluate, now=NOW))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "report",
            "--config",
            str(config),
            "--analysis-config",
            str(PROFILE),
            "--output-dir",
            str(output_dir),
            "--as-of",
            "2026-11-16",
        ],
    )

    assert main.main() == 0
    output_lines = capsys.readouterr().out.splitlines()
    assert "7 Bekanntmachungen gefunden." in output_lines
    assert "Werte die Bekanntmachungen aus …" in output_lines
    assert not any("104-2026" in line for line in output_lines)
    assert [request["limit"] for request in network.search_requests] == [4, 4]
    assert len(network.document_requests) == len(set(network.document_requests)) == 7
    research = json.loads(output.read_bytes())
    run_dir = Path(research["run_directory"])
    assert run_dir.parent == output_dir
    [directory] = (run_dir / "Details/analyses").iterdir()
    assert {path.name for path in run_dir.iterdir()} == {"bericht.pdf", "Details"}
    assert output_lines[-1] == f"PDF-Bericht: {run_dir / 'bericht.pdf'}"
    analysis = json.loads((directory / "analysis.json").read_bytes())
    selection = analysis["selection"]
    first, corrected = selection["selected"]
    assert first["publication_number"] == "104-2026"
    assert (corrected["publication_number"], corrected["lot_id"]) == ("102-2026", "LOT-1")
    assert corrected["fit"]["evidence"][0]["quote"] == assistant
    assert corrected["participation"]["status"] == "Frist offen"
    old, new = corrected["history"]
    assert [o["publication_number"] for o in old["ted_occurrences"]] == ["100-2026", "101-2026"]
    assert "Gleiche Bekanntmachungskennung" in old["duplicate_reason"]
    assert new["ted_occurrences"] == [
        {
            "publication_number": "102-2026",
            "search_groups": ["KI-Beratung", "Schulungen"],
            "occurrence_count": 2,
        },
    ]
    assert any(
        e["quote"] == ORIGINAL + "-01" and "ChangedNoticeIdentifier" in e["path"]
        for e in new["change_sources"][0]["evidence"]
    )
    second_lot, unclear = selection["limited"]
    assert (second_lot["publication_number"], second_lot["lot_id"]) == ("102-2026", "LOT-2")
    assert [v["unit_index"] for v in second_lot["history"]] == [1, 1]
    assert (unclear["fit"]["status"], unclear["participation"]["status"]) == ("unklar", "ungeklärt")
    assert {e["publication_number"]: e["exclusion_reasons"] for e in selection["excluded"]} == {
        "103-2026": ["Fachlich unpassend"],
        "106-2026": ["Frist abgelaufen"],
    }
    documents = {d["publication_number"]: d for d in analysis["documents"]}
    for stage, original_date in [(old, "2026-11-10Z"), (new, "2026-12-18Z")]:
        doc = documents[stage["publication_number"]]
        unit = doc["units"][stage["unit_index"]]
        deadline = unit["fields"]["deadlines"]["values"][0]
        assert deadline["original_date"] == original_date
        assert any(
            e["quote"] == original_date and "EndDate" in e["path"] for e in deadline["evidence"]
        )
        assert unit["fields"]["source_link"]["values"][0]["value"].endswith(
            doc["publication_number"]
        )
        assert doc["provenance"]["original_file"].endswith(doc["publication_number"] + ".xml")
    reader = PdfReader(run_dir / "bericht.pdf")
    links = {
        ref.get_object().get("/A", {}).get("/URI")
        for page in reader.pages
        for ref in page.get("/Annots", [])
    }
    assert f"Details/analyses/{directory.name}/analysis.html#berichtsauswahl" in links
    assert "Details/overview.html" in links
    pages = [" ".join(p.extract_text().split()) for p in reader.pages]
    assert pages[0].index("104-2026") < pages[0].index("102-2026")
    assert "Abruflimit: 4 Treffer je Suchgruppe." in pages[0]
    assert "Berichtslimit: 2 Lose oder Verfahren" in pages[0]
    assert "LOT-2" not in pages[0]
    text = " ".join(pages[1:])
    assert "Früherer Stand · TED 100-2026 · Angebotsfrist: 10.11.2026, 13:00 MEZ" in text
    assert "Aktueller Stand · TED 102-2026 · Angebotsfrist: 18.12.2026, 13:00 MEZ" in text
    assert "Unterhaltsreinigung" not in text and "Schulung zu Microsoft 365" not in text
    html = (directory / "analysis.html").read_text("utf-8")
    for number in ("100-2026", "102-2026"):
        assert f'<a href="#los-{number}-0">TED {number}</a>' in html
        assert f'<a href="../../documents/{number}.xml">Original-XML</a>' in html


def test_same_procedure_with_unproven_relationship_keeps_both_notices(
    tmp_path: Path, profile: Profile
) -> None:
    network = Network(
        [response(row(100, 9), row(101, 10)), response()],
        download_urls(
            {
                100: notice(100, ORIGINAL, lot()),
                101: notice(101, "different-id", lot(day="2026-12-03Z")),
            }
        ),
    )
    _, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    selected = json.loads((directory / "analysis.json").read_bytes())["selection"]["selected"]
    assert [e["publication_number"] for e in selected] == ["100-2026", "101-2026"]
    for entry in selected:
        assert len(entry["history"]) == 1
        [point] = entry["checkpoints"]
        assert "Zuordnung" in point["reason"]
        assert {s["publication_number"] for s in point["sources"]} == {"100-2026", "101-2026"}
        assert all(any(e["quote"] == PROCEDURE for e in s["evidence"]) for s in point["sources"])


def test_conflicting_documents_and_forked_change_do_not_supply_a_current_deadline(
    tmp_path: Path, profile: Profile
) -> None:
    network = Network(
        [response(row(100, 9), row(101, 10), row(102, 11), row(103, 12)), response()],
        download_urls(
            {
                100: notice(100, ORIGINAL, lot()),
                101: notice(101, ORIGINAL, lot(day="2026-12-02Z")),
                102: notice(102, "change-a", lot(day="2026-12-03Z"), previous="000100-2026"),
                103: notice(103, "change-b", lot(day="2026-12-04Z"), previous="000100-2026"),
            }
        ),
    )
    _, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    selected = json.loads((directory / "analysis.json").read_bytes())["selection"]["selected"]
    assert len(selected) == 4
    assert all(len(e["history"]) == 1 for e in selected)
    assert {e["participation"]["status"] for e in selected} == {"ungeklärt"}
    assert any("gleicher Bekanntmachungskennung" in p["reason"] for p in selected[0]["checkpoints"])
    assert any(
        "Verzweigung" in p["reason"]
        and any(e["quote"] == "000100-2026" for s in p["sources"] for e in s["evidence"])
        for p in selected[2]["checkpoints"]
    )


def test_real_correction_without_predecessor_leaves_source_and_open_question(
    tmp_path: Path, profile: Profile
) -> None:
    content = (FIXTURES / "real/799785-2026.xml").read_bytes()
    network = Network([response(row(799785, 14))], download_urls({799785: content}))
    _, run = execute(tmp_path, replace(profile, queries=profile.queries[:1]), network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    selection = json.loads((directory / "analysis.json").read_bytes())["selection"]
    [entry] = selection["selected"]
    assert entry["lot_id"] == "LOT-0000"
    assert len(entry["history"]) == 1
    assert entry["participation"]["status"] == "Frist offen"
    assert {e["quote"] for e in entry["participation"]["evidence"]} >= {
        "2026-12-16+01:00",
        "23:59:00+01:00",
    }
    [point] = entry["checkpoints"]
    assert "nicht eindeutig zugeordnet" in point["reason"]
    [original] = point["sources"]
    assert original["publication_number"] == "799785-2026"
    assert any(e["quote"] == ORIGINAL + "-01" for e in original["evidence"])
    assert len(network.document_requests) == 1


def test_unconfirmed_fit_is_visible_for_procedure_without_lots(
    tmp_path: Path, profile: Profile
) -> None:
    fields = (
        "<cac:ProcurementProject><cbc:Description>Schulung zu Microsoft 365</cbc:Description>"
        "</cac:ProcurementProject>"
    )
    content = notice(100, ORIGINAL, fields)
    network = Network([response(row(100, 14)), response()], download_urls({100: content}))
    _, run = execute(tmp_path, profile, network)

    def model(instructions: str, payload: Data, schema: Data) -> Data:
        result = evaluate(instructions, payload, schema)
        if schema != PROPOSAL:
            [claim] = result["claims"]
            claim["status"] = "nicht entscheidbar"
        return result

    directory = analyze_run(run, PROFILE, model=model, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    [entry] = analysis["selection"]["selected"]
    assert entry["lot_id"] is None
    assert entry["fit"]["status"] == "unklar"
    assert entry["participation"]["status"] == "ungeklärt"
    [doc] = analysis["documents"]
    [unit] = doc["units"]
    assert unit["rejected_claims"][0]["claim"]["status"] == "passend"


@pytest.mark.parametrize(
    ("form_type", "code", "expected"),
    [
        ("planning", "pin-only", "nicht offen"),
        ("competition", "pin-cfc-standard", "Frist offen"),
    ],
)
def test_prior_information_distinguishes_planning_and_call_for_competition(
    form_type: str, code: str, expected: str
) -> None:
    xml_content = xml(
        lot(), extra=f'<cbc:NoticeTypeCode listName="{form_type}">{code}</cbc:NoticeTypeCode>'
    )
    document = extract(
        xml_content.replace(b"ContractNotice", b"PriorInformationNotice"),
        "100-2026",
        now=NOW,
    )
    assert document["units"][0]["participation"]["status"] == expected


@pytest.mark.parametrize(
    ("code", "expected"), [("cancel", "nicht offen"), ("cancel-intent", "ungeklärt")]
)
def test_cancellation_code_takes_precedence_over_unchanged_deadline(
    code: str, expected: str
) -> None:
    change = (
        "<efac:Changes><efac:ChangeReason>"
        f'<cbc:ReasonCode listName="change-corrig-justification">{code}</cbc:ReasonCode>'
        "</efac:ChangeReason></efac:Changes>"
    )
    content = xml(lot()).replace(b"<efac:Publication>", change.encode() + b"<efac:Publication>")
    document = extract(content, "100-2026", now=NOW)
    participation = document["units"][0]["participation"]
    assert participation["status"] == expected
    assert [e["quote"] for e in participation["evidence"]] == [code]


def analyze_notices(
    tmp_path: Path, profile: Profile, documents: dict[int, bytes], model: Model | None = None
) -> tuple[Data, Data, Path]:
    network = Network(
        [response(*(row(n, 14) for n in documents)), response()], download_urls(documents)
    )
    research, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, now=NOW, structured_only=model is None, model=model)
    return research, json.loads((directory / "analysis.json").read_bytes()), directory


def test_cancel_intent_only_affects_referenced_lot(tmp_path: Path, profile: Profile) -> None:
    lots = lot() + lot("LOT-2", day="2026-11-01Z") + lot("LOT-3")
    correction = notice(101, "change", lots, previous=ORIGINAL + "-01").replace(
        b"</efac:Changes>",
        b'<efac:ChangeReason><cbc:ReasonCode listName="change-corrig-justification">'
        b"cancel-intent</cbc:ReasonCode></efac:ChangeReason></efac:Changes>",
    )
    _, analysis, _ = analyze_notices(
        tmp_path, profile, {100: notice(100, ORIGINAL, lots), 101: correction}
    )
    selection = analysis["selection"]
    assert [(e["lot_id"], e["participation"]["status"]) for e in selection["selected"]] == [
        ("LOT-3", "Frist offen"),
        ("LOT-1", "ungeklärt"),
    ]
    evidence = selection["selected"][1]["participation"]["evidence"]
    assert {e["quote"] for e in evidence} >= {"LOT-1", "cancel-intent"}
    assert [(e["lot_id"], e["exclusion_reasons"]) for e in selection["excluded"]] == [
        ("LOT-2", ["Frist abgelaufen"])
    ]


def test_pin_competition_selects_by_expression_of_interest_deadline(
    tmp_path: Path, profile: Profile
) -> None:
    lots = lot(day="2026-11-01Z") + lot("LOT-2", day="2026-12-02Z")
    lots = lots.replace(
        "<cac:TenderSubmissionDeadlinePeriod>",
        "<ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension>"
        "<efac:InterestExpressionReceptionPeriod>",
    ).replace(
        "</cac:TenderSubmissionDeadlinePeriod>",
        "</efac:InterestExpressionReceptionPeriod></efext:EformsExtension></ext:ExtensionContent>"
        "</ext:UBLExtension></ext:UBLExtensions>",
    )
    pin = xml(
        lots,
        extra='<cbc:NoticeTypeCode listName="competition">pin-cfc-standard</cbc:NoticeTypeCode>',
    ).replace(b"ContractNotice", b"PriorInformationNotice")
    research, analysis, directory = analyze_notices(tmp_path, profile, {100: pin})
    selection = analysis["selection"]
    assert [(e["lot_id"], e["participation"]["status"]) for e in selection["selected"]] == [
        ("LOT-2", "Frist offen")
    ]
    assert [(e["lot_id"], e["exclusion_reasons"]) for e in selection["excluded"]] == [
        ("LOT-1", ["Frist abgelaufen"])
    ]
    evidence = selection["selected"][0]["participation"]["evidence"]
    assert {e["quote"] for e in evidence if "InterestExpressionReceptionPeriod" in e["path"]} == {
        "2026-12-02Z",
        "12:00:00Z",
    }
    page = PdfReader(write_report(research, analysis, directory)).pages[0]
    assert "Frist für Interessenbekundungen: 02.12.2026, 13:00 MEZ" in " ".join(
        page.extract_text().split()
    )


def test_verified_checkpoint_from_duplicate_reaches_brief(tmp_path: Path, profile: Profile) -> None:
    note = "Der Termin der verpflichtenden Ortsbesichtigung wird gesondert bekannt gegeben."
    reason = "Termin für die verpflichtende Ortsbesichtigung klären."
    lots = lot(subject="Schulung zu Microsoft 365").replace(
        "</cac:ProcurementProject>", f"</cac:ProcurementProject><cbc:Note>{note}</cbc:Note>"
    )

    def model(instructions: str, payload: Data, schema: Data) -> Data:
        result = evaluate(instructions, payload, schema)
        if schema == PROPOSAL and payload["document"]["publication_number"] == "101-2026":
            record = next(r for r in payload["records"] if payload["texts"][r["text_id"]] == note)
            result["units"][0]["checkpoints"].append(
                {"reason": reason, "evidence": [{"source": record["id"]}]}
            )
        return result

    research, analysis, directory = analyze_notices(
        tmp_path, profile, {n: notice(n, ORIGINAL, lots) for n in (100, 101)}, model
    )
    assert analysis["status"] == "complete"
    [entry] = analysis["selection"]["selected"]
    [point] = [p for p in entry["checkpoints"] if p["reason"] == reason]
    [source] = point["sources"]
    assert source["publication_number"] == "101-2026"
    assert [e["quote"] for e in source["evidence"]] == [note]
    brief = PdfReader(write_report(research, analysis, directory)).pages[1]
    text = " ".join(brief.extract_text().split())
    assert reason in text and "Keine zusätzlichen Prüfpunkte" not in text
    assert "analysis.html#los-101-2026-0" in {
        ref.get_object().get("/A", {}).get("/URI") for ref in brief["/Annots"]
    }


def test_unlinked_conflicting_deadlines_keep_both_stands_unclear(
    tmp_path: Path, profile: Profile
) -> None:
    content = {100: notice(100, ORIGINAL, lot()), 101: notice(101, "other", lot(day="2026-11-01Z"))}
    _, analysis, _ = analyze_notices(tmp_path, profile, content)
    selection = analysis["selection"]
    assert selection["excluded"] == []
    assert [
        (e["publication_number"], e["participation"]["status"]) for e in selection["selected"]
    ] == [("100-2026", "ungeklärt"), ("101-2026", "ungeklärt")]
    for entry in selection["selected"]:
        dates = {
            (s["publication_number"], e["quote"])
            for p in entry["checkpoints"]
            for s in p["sources"]
            for e in s["evidence"]
            if "EndDate" in e["path"]
        }
        assert dates == {("100-2026", "2026-12-01Z"), ("101-2026", "2026-11-01Z")}


def test_namespace_alias_does_not_split_identical_lots(tmp_path: Path, profile: Profile) -> None:
    lots = lot() + lot("LOT-2", day="2026-12-03Z")
    alias = (
        notice(101, ORIGINAL, lots)
        .replace(b"xmlns:cbc=", b"xmlns:common=")
        .replace(b"cbc:", b"common:")
    )
    _, analysis, _ = analyze_notices(
        tmp_path, profile, {100: notice(100, ORIGINAL, lots), 101: alias}
    )
    selected = analysis["selection"]["selected"]
    assert [(e["lot_id"], e["participation"]["status"]) for e in selected] == [
        ("LOT-1", "Frist offen"),
        ("LOT-2", "Frist offen"),
    ]
    for entry in selected:
        [stage] = entry["history"]
        assert {n["publication_number"] for n in stage["ted_occurrences"]} == {
            "100-2026",
            "101-2026",
        }
        assert entry["checkpoints"] == []


def with_internal_id(lots: str, identifier: str) -> str:
    return lots.replace(
        "<cac:ProcurementProject>",
        f'<cac:ProcurementProject><cbc:ID schemeName="internalID">{identifier}</cbc:ID>',
    )


@pytest.mark.parametrize("unknown_lot", [False, True])
def test_reused_technical_lot_id_keeps_independent_deadlines(
    tmp_path: Path, profile: Profile, unknown_lot: bool
) -> None:
    closed = with_internal_id(lot("LOT-0001", day="2026-11-01Z", subject="KI-Schulung"), "Los A")
    opened = with_internal_id(lot("LOT-0001", subject="Servermigration"), "Los B")
    notices = {100: notice(100, ORIGINAL, closed), 101: notice(101, "other", opened)}
    if unknown_lot:
        notices[102] = notice(
            102, "unknown", lot("LOT-0001").replace("<cbc:EndDate>2026-12-01Z</cbc:EndDate>", "")
        )
    _, analysis, _ = analyze_notices(tmp_path, replace(profile, report_limit=1), notices)
    selection = analysis["selection"]
    [selected] = selection["selected"]
    assert (selected["publication_number"], selected["participation"]["status"]) == (
        "101-2026",
        "Frist offen",
    )
    [excluded] = selection["excluded"]
    assert (excluded["publication_number"], excluded["exclusion_reasons"]) == (
        "100-2026",
        ["Frist abgelaufen"],
    )
    if unknown_lot:
        [unknown] = selection["limited"]
        assert unknown["publication_number"] == "102-2026"
        assert unknown["participation"]["status"] == "ungeklärt"
        for entry in (selected, excluded, unknown):
            assert entry["checkpoints"]
            for point in entry["checkpoints"]:
                assert "Widersprüchliche Einreichungsfristen" not in point["reason"]
                assert {s["publication_number"] for s in point["sources"]} in (
                    {"100-2026", "102-2026"},
                    {"101-2026", "102-2026"},
                )
    else:
        assert selected["checkpoints"] == excluded["checkpoints"] == []


@pytest.mark.parametrize(
    ("partial_date", "expected"),
    [
        ("2026-11-01Z", "ungeklärt"),
        ("2026-12-01Z", "Frist offen"),
        ("2026-12-02+14:00", "Frist offen"),  # 1. Dezember 12:00 UTC = 2. Dezember vor Ort.
        ("2026-12-02", "Frist offen"),
        ("2026-11-01", "ungeklärt"),
    ],
)
def test_partial_deadline_preserves_date_and_detects_conflict(
    tmp_path: Path, profile: Profile, partial_date: str, expected: str
) -> None:
    incomplete = lot(day=partial_date).replace("<cbc:EndTime>12:00:00Z</cbc:EndTime>", "")
    _, analysis, _ = analyze_notices(
        tmp_path,
        profile,
        {
            100: notice(100, ORIGINAL, with_internal_id(lot(), "Los A")),
            101: notice(101, "other", with_internal_id(incomplete, "Los A")),
        },
    )
    entries = {e["publication_number"]: e for e in analysis["selection"]["selected"]}
    assert entries["100-2026"]["participation"]["status"] == expected
    assert entries["101-2026"]["participation"]["status"] == "ungeklärt"
    [point] = entries["100-2026"]["checkpoints"]
    assert ("Widersprüchliche Einreichungsfristen" in point["reason"]) == (expected == "ungeklärt")
    dates = {
        (s["publication_number"], e["quote"])
        for s in point["sources"]
        for e in s["evidence"]
        if "EndDate" in e["path"]
    }
    assert dates == {("100-2026", "2026-12-01Z"), ("101-2026", partial_date)}
    assert [e["quote"] for e in entries["101-2026"]["participation"]["evidence"]] == [partial_date]


def test_duration_conflict_from_duplicate_reaches_brief(tmp_path: Path, profile: Profile) -> None:
    minimum = "Die Mindestvertragslaufzeit beträgt ab Leistungsbeginn zwei Jahre."
    lots = lot(subject="Schulung zu Microsoft 365").replace(
        "</cac:ProcurementProject>",
        "<cac:PlannedPeriod><cbc:StartDate>2027-07-01</cbc:StartDate>"
        "<cbc:EndDate>2028-06-30</cbc:EndDate></cac:PlannedPeriod>"
        f"<cac:ContractExtension><cbc:OptionsDescription>{minimum}</cbc:OptionsDescription>"
        "</cac:ContractExtension></cac:ProcurementProject>",
    )

    def model(instructions: str, payload: Data, schema: Data) -> Data:
        result = evaluate(instructions, payload, schema)
        if schema == PROPOSAL and payload["document"]["publication_number"] == "101-2026":
            record = next(
                r for r in payload["records"] if payload["texts"][r["text_id"]] == minimum
            )
            result["units"][0]["facts"].append(
                {
                    "field": "minimum_service_months",
                    "value": "24",
                    "state": "present",
                    "evidence": [{"source": record["id"]}],
                }
            )
        return result

    research, analysis, directory = analyze_notices(
        tmp_path, profile, {n: notice(n, ORIGINAL, lots) for n in (100, 101)}, model
    )
    assert analysis["status"] == "complete"
    [entry] = analysis["selection"]["selected"]
    [point] = entry["checkpoints"]
    [source] = point["sources"]
    assert (source["publication_number"], source["unit_index"]) == ("101-2026", 0)
    assert {e["quote"] for e in source["evidence"]} == {"2027-07-01", "2028-06-30", minimum}
    brief = PdfReader(write_report(research, analysis, directory)).pages[1]
    text = " ".join(brief.extract_text().split())
    assert "vor Ablauf der Mindestlaufzeit von 24 Monaten" in text
    assert "Keine zusätzlichen Prüfpunkte" not in text
