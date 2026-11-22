"""XML-Pflichtangaben, Fristen, Teilnahmestand und Originalbelege."""

import hashlib
import json
import xml.etree.ElementTree as ET

import pytest

from ausschreibungen.extraction import berlin_time, extract
from ausschreibungen.notices import NS
from tests.support.notices import FIXTURES, NOW, lot, xml


@pytest.mark.parametrize(
    "day,clock,expected",
    [
        ("2026-01-10Z", "12:30:00Z", "2026-01-10T13:30:00+01:00"),
        ("2026-07-10Z", "12:30:00Z", "2026-07-10T14:30:00+02:00"),
        ("2026-07-10+02:00", "12:30:00+02:00", "2026-07-10T12:30:00+02:00"),
        ("2026-07-10", "12:30:00", None),
        ("2026-07-10Z", None, None),
        (None, "12:30:00Z", None),
        ("2026-07-10+01:00", "12:30:00+02:00", None),
        ("2026-02-30Z", "12:30:00Z", None),
        ("2026-07-10+15:00", "12:30:00+15:00", None),
        ("2026-07-10+01:99", "12:30:00+01:99", None),
    ],
)
def test_t4_05_berlin_conversion(day: str | None, clock: str | None, expected: str | None) -> None:
    assert berlin_time(day, clock) == expected


def test_t4_05_participation_requires_notice_and_reliable_deadline() -> None:
    content = xml(lot())
    assert (
        extract(content, "100-2026", now=NOW)["units"][0]["participation"]["status"]
        == "Frist offen"
    )
    past = extract(xml(lot(day="2026-01-01Z")), "100-2026", now=NOW)
    assert past["units"][0]["participation"]["status"] == "Frist abgelaufen"
    unknown = extract(xml(lot(day="2026-12-01", clock="12:00:00")), "100-2026", now=NOW)
    assert unknown["units"][0]["participation"]["status"] == "ungeklärt"
    award = content.replace(b"ContractNotice", b"ContractAwardNotice")
    assert (
        extract(award, "100-2026", now=NOW)["units"][0]["participation"]["status"] == "nicht offen"
    )
    info = content.replace(b"ContractNotice", b"PriorInformationNotice")
    assert extract(info, "100-2026", now=NOW)["units"][0]["participation"]["status"] == "ungeklärt"
    other = content.replace(
        b"TenderSubmissionDeadlinePeriod", b"AdditionalInformationRequestPeriod"
    )
    assert extract(other, "100-2026", now=NOW)["units"][0]["participation"]["status"] == "ungeklärt"


def test_structured_extraction_leaves_freetext_for_model() -> None:
    doc = extract((FIXTURES / "real/788030-2026.xml").read_bytes(), "788030-2026", now=NOW)
    fields = doc["units"][0]["fields"]
    for key in ("duration", "selection_criteria", "award_criteria", "submission"):
        assert fields[key] == {"status": "missing", "display": "nicht angegeben", "values": []}


def test_real_labelled_freetext_deadline_needs_no_model_approval() -> None:
    doc = extract((FIXTURES / "real/788030-2026.xml").read_bytes(), "788030-2026", now=NOW)
    unit = doc["units"][0]
    field = unit["fields"]["deadlines"]
    assert field["status"] == "uncertain"
    assert len(field["values"]) == 1
    value = field["values"][0]
    assert value["original"] == "Einreichungsfrist: Mittwoch, den 09.12.2026, 09:00 Uhr"
    assert value["original_date"] == "09.12.2026"
    assert value["original_time"] == "09:00 Uhr"
    assert value["berlin"] is None
    assert value["method"] == "labelled_text"
    assert value["lot_id"] == "PAR-0001"
    assert (
        value["evidence"][0]["path"]
        == "/PriorInformationNotice/cac:ProcurementProject[1]/cbc:Note[1]"
    )
    assert unit["participation"]["status"] == "nicht offen"
    assert unit["participation"]["evidence"][0]["quote"] == "pin-only"


@pytest.mark.parametrize("change", ["example", "invalid_date", "wrong_weekday", "invalid_time"])
def test_labelled_text_rejects_unreliable_deadline_variants(change: str) -> None:
    note = "Frist und Form zur Abgabe Ihrer Unterlagen: Einreichungsfrist: "
    note += "Mittwoch, den 09.12.2026, 09:00 Uhr Einreichungsform: per E-Mail"
    if change == "example":
        note = "Beispiel: " + note
    elif change == "invalid_date":
        note = note.replace("09.12.2026", "32.12.2026")
    elif change == "wrong_weekday":
        note = note.replace("Mittwoch", "Montag")
    else:
        note = note.replace("09:00", "25:00")
    doc = extract(xml(extra=f"<cbc:Note>{note}</cbc:Note>"), "100-2026", now=NOW)
    assert doc["units"][0]["fields"]["deadlines"]["values"] == []


def test_labelled_deadlines_keep_different_lots_separate() -> None:
    def with_note(identifier: str, day: str) -> str:
        content = lot(identifier)
        note = "Frist und Form zur Abgabe Ihrer Unterlagen: "
        note += f"Einreichungsfrist: {day}, 10:00 Uhr Einreichungsform: per E-Mail"
        return content.replace(
            "</cac:ProcurementProject>", f"<cbc:Note>{note}</cbc:Note></cac:ProcurementProject>"
        )

    doc = extract(
        xml(with_note("LOT-A", "10.12.2026") + with_note("LOT-B", "11.12.2026")),
        "100-2026",
        now=NOW,
    )
    assert [u["fields"]["deadlines"]["values"][-1]["original_date"] for u in doc["units"]] == [
        "10.12.2026",
        "11.12.2026",
    ]


def test_global_freetext_is_not_distributed_to_multiple_lots() -> None:
    note = "Frist und Form zur Abgabe Ihrer Unterlagen: "
    note += "Einreichungsfrist: 10.12.2026, 10:00 Uhr Einreichungsform: per E-Mail"
    doc = extract(
        xml(
            lot("LOT-A", day="2026-12-01Z", clock="12:00:00Z")
            + lot("LOT-B", day="2027-01-08Z", clock="09:30:00Z"),
            extra=f"<cbc:Note>{note}</cbc:Note>",
        ),
        "100-2026",
        now=NOW,
    )
    expected = {
        "LOT-A": (1, "2026-12-01Z", "12:00:00Z", "2026-12-01T13:00:00+01:00"),
        "LOT-B": (2, "2027-01-08Z", "09:30:00Z", "2027-01-08T10:30:00+01:00"),
    }
    assert sorted(unit["lot_id"] for unit in doc["units"]) == ["LOT-A", "LOT-B"]
    for unit in doc["units"]:
        lot_id = unit["lot_id"]
        position, day, clock, berlin = expected[lot_id]
        [deadline] = unit["fields"]["deadlines"]["values"]
        assert deadline["berlin"] == berlin
        path = (
            f"/ContractNotice/cac:ProcurementProjectLot[{position}]/"
            "cac:TenderingProcess[1]/cac:TenderSubmissionDeadlinePeriod[1]"
        )
        assert [(e["path"], e["quote"], e["lot_id"]) for e in deadline["evidence"]] == [
            (path + "/cbc:EndDate[1]", day, lot_id),
            (path + "/cbc:EndTime[1]", clock, lot_id),
        ]


@pytest.mark.parametrize(
    "number", ["773064-2026", "798622-2026", "799785-2026", "788030-2026", "800874-2026"]
)
def test_real_oracles_match_original_and_structured_extraction(number: str) -> None:
    expected = json.loads((FIXTURES / "real/expectations.json").read_text("utf-8"))[number]
    content = (FIXTURES / "real" / f"{number}.xml").read_bytes()
    provenance = json.loads((FIXTURES / "real/provenance.json").read_text("utf-8"))["documents"][
        number
    ]
    assert hashlib.sha256(content).hexdigest() == provenance["sha256"]
    root = ET.fromstring(content)
    # Unabhängige Prüfung festgelegter Fundstellen direkt gegen das Original.
    for ev in expected.get("evidence", []):
        node = root.find("./" + ev["path"].split("/", 2)[2], NS)
        assert node is not None and ev["quote"] in (node.text or "")
    if "freetext_source" in expected:
        note = root.find("./" + expected["freetext_source"].split("/", 2)[2], NS)
        assert note is not None
        for key in ("original_deadline", "original_submission", "original_selection"):
            assert expected[key] in (note.text or "")
    doc = extract(content, number, now=NOW)
    unit = doc["units"][0]
    for key, value in expected.get("fields", {}).items():
        if key == "selection_criteria_free_text":
            # Fachliche Zuordnung ist erst Gegenstand des echten KI-Laufs.
            assert value in content.decode("utf-8")
            continue
        if key == "selection_criteria_document_source":
            selection = unit["fields"]["selection_criteria"]
            assert selection["status"] == "uncertain"
            assert [source["value"] for source in selection["document_sources"]] == [value]
            continue
        field = unit["fields"][key]
        if value == "nicht angegeben":
            assert field["status"] == "missing"
            assert field["display"] == "nicht angegeben"
        elif key == "deadlines":
            assert field["values"][0]["berlin"] == value
        else:
            values = [v["value"] for v in field["values"]]
            assert all(v in values for v in (value if isinstance(value, list) else [value]))
    for unit in doc["units"]:
        if "lot_durations_months" in expected:
            assert (
                unit["fields"]["duration"]["values"][0]["value"]
                == expected["lot_durations_months"][unit["lot_id"]]
            )
            assert unit["fields"]["duration"]["values"][0]["attributes"]["unitCode"] == "MONTH"
            assert unit["fields"]["deadlines"]["values"][0]["berlin"] == expected["deadline_berlin"]


def test_deadline_without_time_retains_original_and_unknown_state() -> None:
    content = xml(lot()).replace(b"<cbc:EndTime>12:00:00Z</cbc:EndTime>", b"")
    unit = extract(content, "100-2026", now=NOW)["units"][0]
    field = unit["fields"]["deadlines"]
    assert field["status"] == "uncertain"
    assert field["values"][0]["original_date"] == "2026-12-01Z"
    assert field["values"][0]["original_time"] is None
    assert field["values"][0]["berlin"] is None
    assert unit["participation"]["status"] == "ungeklärt"


def test_conflicting_structured_deadlines_and_procedures_keep_both_values() -> None:
    content = xml(
        lot(),
        extra="<cac:TenderingProcess><cbc:ProcedureCode>open</cbc:ProcedureCode>"
        "<cbc:ProcedureCode>restricted</cbc:ProcedureCode></cac:TenderingProcess>",
    )
    content = content.replace(
        b"<cbc:EndDate>2026-12-01Z</cbc:EndDate>",
        b"<cbc:EndDate>2026-12-01Z</cbc:EndDate><cbc:EndDate>2026-12-10Z</cbc:EndDate>",
    )
    unit = extract(content, "100-2026", now=NOW)["units"][0]
    assert unit["fields"]["deadlines"]["status"] == "conflict"
    period = unit["fields"]["deadlines"]["values"][0]
    assert period["dates"] == ["2026-12-01Z", "2026-12-10Z"]
    assert period["times"] == ["12:00:00Z"]
    assert period["original_date"] is None and period["berlin"] is None
    assert unit["fields"]["procedure"]["status"] == "conflict"
    assert [v["value"] for v in unit["fields"]["procedure"]["values"]] == ["open", "restricted"]
    assert [e["quote"] for e in unit["fields"]["deadlines"]["values"][0]["evidence"]] == [
        "2026-12-01Z",
        "2026-12-10Z",
        "12:00:00Z",
    ]
    assert unit["participation"]["status"] == "ungeklärt"


@pytest.mark.parametrize(("second", "status"), [("StartDate", "present"), ("EndDate", "conflict")])
def test_duration_compares_only_same_component_in_same_period(second: str, status: str) -> None:
    periods = (
        "<cac:PlannedPeriod><cbc:EndDate>2027-12-01</cbc:EndDate>"
        f"<cbc:{second}>2027-01-01</cbc:{second}></cac:PlannedPeriod>"
        "<cac:PlannedPeriod><cbc:EndDate>2028-12-01</cbc:EndDate></cac:PlannedPeriod>"
    )
    content = lot().replace("</cac:ProcurementProject>", periods + "</cac:ProcurementProject>")
    unit = extract(xml(content), "100-2026", now=NOW)["units"][0]
    assert unit["fields"]["duration"]["status"] == status
