"""Strukturierte eForms-Felder, Fristen und Teilnahmestand aus dem Original-XML."""

import hashlib
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from ausschreibungen.notices import (
    NS,
    PARTICIPATION_PERIODS,
    NoDoctype,
    inspect_document,
    short_tag,
)

# eForms BG-708: Description (BT-728) is free text, unlike the address fields.
PERFORMANCE_ADDRESS_FIELDS = (
    "cbc:CityName",
    "cbc:PostalZone",
    "cbc:CountrySubentityCode",
    "cbc:Region",
    "cac:Country/cbc:IdentificationCode",
    "cbc:StreetName",
    "cbc:AdditionalStreetName",
    "cac:AddressLine/cbc:Line",
)

FIELDS = (
    "buyer",
    "subject",
    "place",
    "procedure",
    "deadlines",
    "tender_validity",
    "duration",
    "selection_criteria",
    "award_criteria",
    "submission",
    "source_link",
)
CRITERIA_FIELDS = ("selection_criteria", "award_criteria")
ELECTRONIC_SUBMISSION_FIELDS = {
    "electronic_submission_required": "required",
    "electronic_submission_allowed": "allowed",
    "electronic_submission_prohibited": "not-allowed",
}
SUBMISSION_CODE_PATH = "/cbc:SubmissionMethodCode["


def check_submission(field: dict[str, Any]) -> None:
    modes = set()
    for value in field["values"]:
        if value["method"] == "xml" and any(
            SUBMISSION_CODE_PATH in e["path"] for e in value["evidence"]
        ):
            if value["value"] in ELECTRONIC_SUBMISSION_FIELDS.values():
                modes.add(value["value"])
        elif value.get("electronic_submission") and value["status"] != "uncertain":
            modes.add(value["electronic_submission"])
    if len(modes) > 1:
        field["status"] = "conflict"


def index_xml(root: ET.Element) -> tuple[dict[ET.Element, dict[str, Any]], list[dict[str, Any]]]:
    nodes: dict[ET.Element, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []

    def walk(node: ET.Element, path: str, lot: str | None = None) -> None:
        if node.tag == "{" + NS["cac"] + "}ProcurementProjectLot":
            lot = node.findtext("./cbc:ID", namespaces=NS) or "unresolved:" + path
        record = {
            "path": path,
            "value": (node.text or "").strip(),
            "attributes": node.attrib,
            "lot_id": lot,
        }
        nodes[node] = record
        if record["value"]:
            records.append(record)
        counters: dict[str, int] = {}
        for child in node:
            tag = short_tag(child.tag)
            counters[tag] = counters.get(tag, 0) + 1
            walk(child, f"{path}/{tag}[{counters[tag]}]", lot)

    walk(root, "/" + short_tag(root.tag))
    return nodes, records


def fact(record: dict[str, Any], *, method: str = "xml") -> dict[str, Any]:
    return {
        "value": record["value"],
        "attributes": record["attributes"],
        "method": method,
        "evidence": [
            {"path": record["path"], "quote": record["value"], "lot_id": record["lot_id"]}
        ],
    }


def berlin_time(day: str | None, clock: str | None) -> str | None:
    """XML date/time: beide Komponenten und expliziter Offset; keine Zeitzonen raten."""
    if not day or not clock:
        return None
    d = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(Z|[+-]\d{2}:\d{2})?", day)
    t = re.fullmatch(r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)(Z|[+-]\d{2}:\d{2})?", clock)
    if not d or not t or not (d[2] or t[2]):
        return None
    if d[2] and t[2] and d[2].replace("Z", "+00:00") != t[2].replace("Z", "+00:00"):
        return None
    offset = (t[2] or d[2]).replace("Z", "+00:00")
    # XML Schema timezone limits (datetime alone accepts offsets up to 24 hours).
    if (
        int(offset[1:3]) > 14
        or int(offset[4:]) >= 60
        or (offset[1:3] == "14" and offset[4:] != "00")
    ):
        return None
    try:
        return (
            datetime.fromisoformat(f"{d[1]}T{t[1]}{offset}")
            .astimezone(ZoneInfo("Europe/Berlin"))
            .isoformat()
        )
    except ValueError:
        return None


def deadline_component_key(value: str) -> str:
    return value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value


def distinct_deadline_values(values: list[str]) -> list[str]:
    originals: dict[str, str] = {}
    for value in values:
        if value:
            originals.setdefault(deadline_component_key(value), value)
    return list(originals.values())


def deadline_components(dates: list[str], times: list[str]) -> dict[str, Any]:
    dates = distinct_deadline_values(dates)
    times = distinct_deadline_values(times)
    day = dates[0] if len(dates) == 1 else None
    clock = times[0] if len(times) == 1 else None
    berlin = berlin_time(day, clock)
    status = "present" if berlin else "uncertain"
    reason = ""
    if len(dates) > 1 or len(times) > 1:
        status = "conflict"
    elif day and clock and not berlin:
        zones = [re.search(r"(Z|[+-]\d{2}:\d{2})$", part) for part in (day, clock)]
        offsets = {zone[0].replace("Z", "+00:00") for zone in zones if zone}
        if len(offsets) > 1:
            status, reason = "conflict", "Zeitzonenangaben widersprechen sich"
        elif not offsets:
            reason = "Zeitzone nicht angegeben"
        else:
            reason = "Zeitangabe nicht eindeutig lesbar"
    return {
        "dates": dates,
        "times": times,
        "original_date": day,
        "original_time": clock,
        "berlin": berlin,
        "status": status,
        "reason": reason,
    }


def labelled_deadlines(records: list[dict[str, Any]], lot_id: str | None) -> list[dict[str, Any]]:
    """Explizite Frist-/Form-Abschnitte lesen, ohne fehlende Zeitzonen zu ergänzen."""
    pattern = re.compile(
        r"Frist\s+und\s+Form\s+zur\s+Abgabe\s+Ihrer\s+Unterlagen:\s*"
        r"(?P<original>Einreichungsfrist:\s*"
        r"(?:(?P<weekday>Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),?\s+)?"
        r"(?:den\s+)?(?P<day>\d{2}\.\d{2}\.\d{4}),?\s+"
        r"(?P<clock>\d{1,2}:\d{2})\s+Uhr)(?=\s+Einreichungsform:|\s*$)",
        re.IGNORECASE,
    )
    weekdays = ["montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"]
    deadlines = []
    for record in records:
        if record["lot_id"] not in (None, lot_id):
            continue
        if not re.fullmatch(
            r"/\w+/(?:cac:ProcurementProjectLot\[\d+\]/)?"
            r"(?:cac:ProcurementProject\[\d+\]/)?cbc:(?:Note|Description)\[\d+\]",
            record["path"],
        ):
            continue
        for match in pattern.finditer(record["value"]):
            prefix = record["value"][max(0, match.start() - 60) : match.start()]
            if re.search(r"\b(Beispiel|Muster|Entwurf|keine|nicht)\b", prefix, re.IGNORECASE):
                continue
            try:
                day = datetime.strptime(match["day"], "%d.%m.%Y")
                datetime.strptime(match["clock"], "%H:%M")
            except ValueError:
                continue
            if match["weekday"] and weekdays[day.weekday()] != match["weekday"].lower():
                continue
            deadlines.append(
                {
                    "kind": "Einreichungsfrist (Freitext)",
                    "original": match["original"],
                    "original_date": match["day"],
                    "original_time": match["clock"] + " Uhr",
                    "berlin": None,
                    "status": "uncertain",
                    "method": "labelled_text",
                    "lot_id": lot_id,
                    "evidence": [
                        {
                            "path": record["path"],
                            "quote": match["original"],
                            "lot_id": record["lot_id"],
                        }
                    ],
                }
            )
    return deadlines


def extract(content: bytes, number: str, *, now: datetime) -> dict[str, Any]:
    metadata, _ = inspect_document(content, number)
    root = ET.fromstring(content, parser=ET.XMLParser(target=NoDoctype()))
    nodes, records = index_xml(root)
    result: dict[str, Any] = {
        "publication_number": number,
        "notice_type": short_tag(root.tag),
        "metadata": metadata,
        # TED ergänzt die Publikationsdaten unabhängig vom Inhalt der Bekanntmachung.
        "content_sha256": hashlib.sha256(
            ET.canonicalize(
                content,
                strip_text=True,
                rewrite_prefixes=True,
                qname_aware_attrs={"{http://www.w3.org/2001/XMLSchema-instance}type"},
                exclude_tags={f"{{{NS['efac']}}}Publication"},
            ).encode("utf-8")
        ).hexdigest(),
        "records": records,
        "units": [],
        "checkpoints": [],
    }

    def found(base: ET.Element, path: str) -> list[dict[str, Any]]:
        return [fact(nodes[n]) for n in base.findall(path, NS) if nodes[n]["value"]]

    # Auftraggeber über seine Referenz auflösen, nicht alle Organisationen zu Käufern machen.
    buyers: list[dict[str, Any]] = found(
        root, "./cac:ContractingParty/cac:Party/cac:PartyName/cbc:Name"
    )
    for ref in root.findall("./cac:ContractingParty/cac:Party/cac:PartyIdentification/cbc:ID", NS):
        for company in root.findall(".//efac:Organizations/efac:Organization/efac:Company", NS):
            if company.findtext("./cac:PartyIdentification/cbc:ID", namespaces=NS) == ref.text:
                for item in found(company, "./cac:PartyName/cbc:Name"):
                    item["evidence"].append(fact(nodes[ref])["evidence"][0])
                    buyers.append(item)
    lots = root.findall("./cac:ProcurementProjectLot", NS)
    lot_ids = [nodes[lot]["lot_id"] for lot in lots]
    for lot in lots or [root]:
        lot_id = nodes[lot]["lot_id"]
        fields = {
            key: {"status": "missing", "display": "nicht angegeben", "values": []} for key in FIELDS
        }
        fields["buyer"]["values"] = buyers.copy()
        fields["procedure"]["values"] = found(root, "./cac:TenderingProcess/cbc:ProcedureCode")
        for key, paths in {
            "subject": [
                "./cac:ProcurementProject/cbc:Name",
                "./cac:ProcurementProject/cbc:Description",
            ],
            "place": [
                f"./cac:ProcurementProject/cac:RealizedLocation/cac:Address/{path}"
                for path in PERFORMANCE_ADDRESS_FIELDS
            ],
            "duration": [
                "./cac:ProcurementProject/cac:PlannedPeriod/cbc:*",
                "./cac:ProcurementProject/cac:ContractExtension//cbc:*",
            ],
            "tender_validity": [
                "./cac:TenderingTerms/cac:TenderValidityPeriod/cbc:DurationMeasure"
            ],
            "award_criteria": [
                "./cac:TenderingTerms/cac:AwardingTerms/cac:AwardingCriterion//cbc:*",
                "./cac:TenderingTerms/cac:AwardingTerms/cac:AwardingCriterion//efbc:*",
            ],
            "submission": [
                "./cac:TenderingProcess/cbc:SubmissionMethodCode",
                "./cac:TenderingTerms/cac:TenderRecipientParty/cbc:EndpointID",
            ],
        }.items():
            fields[key]["values"] = [item for path in paths for item in found(lot, path)]
        scope_checks = []
        selection = fields["selection_criteria"]
        internal_ids = found(lot, "./cac:ProcurementProject/cbc:ID[@schemeName='internalID']")
        number_in_notice = internal_ids[0]["value"] if len(internal_ids) == 1 else ""
        for criterion in lot.findall(".//efac:SelectionCriteria", NS):
            descriptions = criterion.findall("./cbc:Description", NS)
            foreign = []
            for description in descriptions:
                heading = nodes[description]["value"].partition(":")[0].strip()
                label = re.search(r"(?:^Referenzen Los (\d+)|\(Los (\d+)\))$", heading, re.I)
                if (
                    label
                    and lot_id
                    and number_in_notice.isdecimal()
                    and len(re.findall(r"\bLos(?:e)?\b", heading, re.I)) == 1
                ):
                    number_in_heading = label[1] or label[2]
                    if number_in_heading.lstrip("0") != number_in_notice.lstrip("0"):
                        foreign.append(fact(nodes[description])["evidence"][0])
            if foreign:
                scope_checks.append(
                    {
                        "reason": "Die Überschrift nennt ein anderes Los als der XML-Abschnitt. "
                        "Geltung des Eignungskriteriums manuell prüfen.",
                        "method": "xml_lot_scope",
                        "criterion_path": nodes[criterion]["path"],
                        "evidence": foreign + internal_ids[0]["evidence"],
                    }
                )
            else:
                selection["values"].extend(found(criterion, ".//cbc:*"))
        # Die Eignungsquelle bezeichnet den Fundort der Nachweise, kein Eignungskriterium.
        for base in [root, lot] if lot is not root else [root]:
            for requirement in base.findall(
                "./cac:TenderingTerms/cac:TendererQualificationRequest/"
                "cac:SpecificTendererRequirement",
                NS,
            ):
                code = requirement.find("./cbc:TendererRequirementTypeCode", NS)
                if code is None or code.attrib.get("listName") in {
                    "selection-criterion",
                    "exclusion-ground",
                }:
                    selection["values"].extend(found(requirement, "./cbc:*"))
                elif (
                    code.attrib.get("listName") == "selection-criteria-source"
                    and nodes[code]["value"] == "epo-procurement-document"
                ):
                    selection.setdefault("document_sources", []).append(fact(nodes[code]))
        deadlines = []
        for period_path in (
            "cac:TenderSubmissionDeadlinePeriod",
            "cac:ParticipationRequestReceptionPeriod",
            "cac:AdditionalInformationRequestPeriod",
            "ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
            "efext:EformsExtension/efac:InterestExpressionReceptionPeriod",
        ):
            periods = lot.findall(f"./cac:TenderingProcess/{period_path}", NS)
            period_values = []
            for period in periods:
                days = period.findall("./cbc:EndDate", NS)
                times = period.findall("./cbc:EndTime", NS)
                descriptions = found(period, "./cbc:Description")
                period_values.append(
                    {
                        "kind": period.tag.rsplit("}", 1)[-1],
                        **deadline_components(
                            [nodes[n]["value"] for n in days], [nodes[n]["value"] for n in times]
                        ),
                        "period_path": nodes[period]["path"],
                        "context": " · ".join(item["value"] for item in descriptions),
                        "lot_id": lot_id,
                        "evidence": [fact(nodes[n])["evidence"][0] for n in days + times]
                        + [e for item in descriptions for e in item["evidence"]],
                    }
                )
            variants = {
                (
                    frozenset(map(deadline_component_key, v["dates"])),
                    frozenset(map(deadline_component_key, v["times"])),
                )
                for v in period_values
            }
            for value in period_values:
                if len(variants) > 1 and not value["context"]:
                    value["reason"] = " · ".join(
                        filter(None, [value["reason"], "Zuordnung zur Verfahrensphase prüfen"])
                    )
                    if value["status"] == "present":
                        value["status"] = "uncertain"
            deadlines.extend(period_values)
        # Globaler Freitext kann einzelne Lose nennen: Mehrlos-Zuordnung bleibt
        # der fachlichen Prüfung vorbehalten, statt die Frist pauschal zu verteilen.
        deadline_records = [r for r in records if r["lot_id"] is not None or len(lots) <= 1]
        deadlines.extend(labelled_deadlines(deadline_records, lot_id))
        fields["deadlines"]["values"] = deadlines
        pub = [r for r in records if r["path"].endswith("/efbc:NoticePublicationID[1]")]
        fields["source_link"]["values"] = [
            {
                "value": f"https://ted.europa.eu/de/notice/-/detail/{number}",
                "method": "ted_publication_link",
                "evidence": [{"path": r["path"], "quote": r["value"], "lot_id": None} for r in pub],
            }
        ]
        for key, value in fields.items():
            if value["values"]:
                value.update(status="present", display=None)
            if key == "deadlines" and deadlines:
                if any(d["status"] == "conflict" for d in deadlines):
                    value["status"] = "conflict"
                elif any(d["status"] == "uncertain" for d in deadlines):
                    value["status"] = "uncertain"
        if len({v["value"] for v in fields["procedure"]["values"]}) > 1:
            fields["procedure"]["status"] = "conflict"
        check_submission(fields["submission"])
        for period in lot.findall("./cac:ProcurementProject/cac:PlannedPeriod", NS):
            for component in ("StartDate", "EndDate"):
                if len({v["value"] for v in found(period, f"./cbc:{component}")}) > 1:
                    fields["duration"]["status"] = "conflict"
        if scope_checks and not selection["values"]:
            selection.update(status="uncertain", display="Losgeltung ungeklärt")
        if selection.get("document_sources") and selection["status"] == "missing":
            selection.update(
                status="uncertain", display="Einzelanforderungen in den Vergabeunterlagen"
            )
        unit = {
            "lot_id": lot_id,
            "fields": fields,
            "fit": {
                "status": "unklar",
                "reason": "KI-Auswertung nicht durchgeführt.",
                "evidence": [],
            },
            "participation_requirements": {
                "status": "ungeklärt",
                "reason": "Lieferfähigkeit und Erfüllung der Teilnahmevoraussetzungen "
                "sind ohne geprüfte Unternehmensnachweise ungeklärt.",
                "field": "selection_criteria",
            },
            "checkpoints": scope_checks,
            "rejected_claims": [],
            "claim_reviews": [],
            "processing_errors": [],
        }
        if lot_id and number_in_notice:
            unit["internal_lot_id"] = internal_ids[0]
        if lot_id and (lot_id.startswith("unresolved:") or lot_ids.count(lot_id) > 1):
            unit["processing_errors"].append(
                "Loskennung fehlt oder ist mehrfach vergeben; Zuordnung ungeklärt."
            )
        award_evidence = []
        if result["notice_type"] == "ContractAwardNotice":
            award_evidence = [
                e for value in found(root, "./cbc:NoticeTypeCode") for e in value["evidence"]
            ]
            for outcome in root.findall(".//efac:NoticeResult/efac:LotResult", NS):
                ref = outcome.find("./efac:TenderLot/cbc:ID", NS)
                if ref is not None and ref.text == lot_id:
                    award_evidence.extend(fact(nodes[ref])["evidence"])
                    for value in found(outcome, "./cbc:TenderResultCode"):
                        award_evidence.extend(value["evidence"])
        unit["participation"] = participation(result, unit, now, award_evidence)
        result["units"].append(unit)
    for record in records:
        path = record["path"]
        if "/efac:Changes[" in path:
            result["checkpoints"].append(
                {
                    "reason": "Änderungsangabe in der Bekanntmachung.",
                    "evidence": [fact(record)["evidence"][0]],
                }
            )
        if "/cac:PreviousNoticeReference[" in path or "/cac:NoticeDocumentReference[" in path:
            result["checkpoints"].append(
                {
                    "reason": "Verweis auf eine frühere Bekanntmachung. Zusammenhang prüfen.",
                    "evidence": [fact(record)["evidence"][0]],
                }
            )
        if "/cac:CallForTendersDocumentReference[" in record["path"] and record["path"].endswith(
            "/cbc:URI[1]"
        ):
            result["checkpoints"].append(
                {
                    "reason": "Zusätzliche Unterlagen: in dieser Version "
                    "nicht abgerufen und nicht ausgewertet.",
                    "url": record["value"],
                    "lot_id": record["lot_id"],
                    "status": "not_retrieved_not_evaluated",
                    "evidence": [fact(record)["evidence"][0]],
                }
            )
    return result


def participation(
    document: dict[str, Any],
    unit: dict[str, Any],
    now: datetime,
    award_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    answer: dict[str, Any] = {
        "status": "ungeklärt",
        "checked_at": now.isoformat(),
        "reason": "Keine eindeutige Grundlage für offene Teilnahme.",
    }
    if document["notice_type"] == "ContractAwardNotice":
        return {
            **answer,
            "status": "nicht offen",
            "reason": "Ergebnisbekanntmachung, kein Aufruf zur Teilnahme.",
            "evidence": award_evidence or [],
        }
    type_records = [
        r
        for r in document["records"]
        if r["path"].count("/") == 2 and r["path"].endswith("/cbc:NoticeTypeCode[1]")
    ]
    if document["notice_type"] == "PriorInformationNotice" and any(
        r["attributes"].get("listName") == "planning" for r in type_records
    ):
        return {
            **answer,
            "status": "nicht offen",
            "reason": "Vorinformation zur Planung.",
            "evidence": [e for r in type_records for e in fact(r)["evidence"]],
        }
    lot_id = unit["lot_id"]
    lot_ids = document["metadata"]["lot_ids"]
    cancellations = [
        r
        for r in document["records"]
        if "/efac:Changes[" in r["path"]
        and r["attributes"].get("listName") == "change-corrig-justification"
        and r["value"] in {"cancel", "cancel-intent"}
    ]
    applicable = []
    sections = []
    for code in cancellations:
        if code["value"] == "cancel-intent":
            change_path = code["path"].rsplit("/efac:ChangeReason[", 1)[0] + "/efac:Change["
            changes = [r for r in document["records"] if r["path"].startswith(change_path)]
            targets = [r for r in changes if "/efbc:ChangedSectionIdentifier[" in r["path"]]
            # Nur eine vollständig losbezogene Änderungsangabe entlastet andere Lose.
            changed_groups = {r["path"][len(change_path) :].partition("]")[0] for r in changes}
            targeted_groups = {r["path"][len(change_path) :].partition("]")[0] for r in targets}
            if (
                targets
                and targeted_groups == changed_groups
                and all(lot_ids.count(r["value"]) == 1 for r in targets)
            ):
                targets = [r for r in targets if r["value"] == lot_id]
                if not targets:
                    continue
            sections.extend(targets)
        applicable.append(code)
    if applicable:
        return {
            **answer,
            "status": "nicht offen"
            if all(r["value"] == "cancel" for r in applicable)
            else "ungeklärt",
            "reason": "Annullierung der Bekanntmachung oder angekündigte Aufhebung prüfen.",
            "evidence": [e for r in applicable + sections for e in fact(r)["evidence"]],
        }
    if document["notice_type"] != "ContractNotice" and not any(
        r["value"] in {"pin-cfc-standard", "pin-cfc-social"} for r in type_records
    ):
        return answer
    if lot_id and (lot_id.startswith("unresolved:") or lot_ids.count(lot_id) != 1):
        return answer
    deadlines = [
        d
        for d in unit["fields"]["deadlines"]["values"]
        if d["kind"] in (*PARTICIPATION_PERIODS, "Einreichungsfrist (Freitext)")
        and (len(lot_ids) <= 1 or all(e["lot_id"] == lot_id for e in d["evidence"]))
    ]
    answer["evidence"] = [e for d in deadlines for e in d["evidence"]]
    # Identische strukturierte Termine derselben Phase sind kein Widerspruch.
    terms = {(d["kind"], d["berlin"]) for d in deadlines}
    if len(terms) == 1 and deadlines[0]["berlin"]:
        opened = datetime.fromisoformat(deadlines[0]["berlin"]) > now
        answer.update(
            status="Frist offen" if opened else "Frist abgelaufen",
            reason="Aufruf zur Teilnahme und eindeutig datierte Einreichungsfrist; "
            "keine Zusage der Teilnahmeberechtigung.",
        )
    elif deadlines:
        answer["reason"] = "Einreichungsfrist oder zugehörige Verfahrensphase nicht eindeutig."
    return answer
