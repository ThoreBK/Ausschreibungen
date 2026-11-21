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
from ausschreibungen.analysis import PROPOSAL, analyze_run, extract
from ausschreibungen.research import collect
from ausschreibungen.ted import Profile, search
from tests.test_analysis import FIXTURES, NOW, PROFILE, lot, xml
from tests.test_research import Network, execute, response, row

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
    tmp_path: Path, profile_path: Path, monkeypatch: pytest.MonkeyPatch
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
    output = tmp_path / "results.json"
    monkeypatch.setattr(main, "search", partial(search, transport=network.search))
    monkeypatch.setattr(main, "collect", partial(collect, download=network.download))
    monkeypatch.setattr(main, "analyze_run", partial(analyze_run, model=evaluate, now=NOW))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--report",
            "--config",
            str(config),
            "--analysis-config",
            str(PROFILE),
            "--output",
            str(output),
            "--as-of",
            "2026-11-16",
        ],
    )

    assert main.main() == 0
    assert [request["limit"] for request in network.search_requests] == [4, 4]
    assert len(network.document_requests) == len(set(network.document_requests)) == 7
    research = json.loads(output.read_bytes())
    [directory] = (Path(research["run_directory"]) / "analyses").iterdir()
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
    pages = [" ".join(p.extract_text().split()) for p in PdfReader(directory / "bericht.pdf").pages]
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
