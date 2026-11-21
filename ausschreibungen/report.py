"""Lesbare TED-Berichte mit kompakten Steckbriefen und auflösbaren XML-Belegen."""

from collections.abc import Iterable
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

from ausschreibungen.analysis import CRITERIA_FIELDS, deadline_components
from ausschreibungen.report_fonts import BOLD, REGULAR, apply_fonts, font_runs, register_fonts
from ausschreibungen.research import link, text_value

LABELS = {
    "buyer": "Auftraggeber",
    "subject": "Gegenstand",
    "place": "Leistungsort",
    "procedure": "Verfahrensart",
    "deadlines": "Fristen",
    "tender_validity": "Angebotsbindefrist",
    "duration": "Laufzeit",
    "selection_criteria": "Eignungskriterien",
    "award_criteria": "Zuschlagskriterien",
    "submission": "Abgabeform",
    "source_link": "Quellenlink",
}
STATES = {"missing": "nicht angegeben", "uncertain": "unsicher", "conflict": "Widerspruch"}
DEADLINES = {
    "TenderSubmissionDeadlinePeriod": "Angebotsfrist",
    "ParticipationRequestReceptionPeriod": "Frist für Teilnahmeanträge",
    "AdditionalInformationRequestPeriod": "Frist für Rückfragen",
}
LIMIT = "in dieser Version nicht abgerufen und nicht ausgewertet"
Data = dict[str, Any]
CriteriaDetails = tuple[str, str, list[int]]


def local_time(value: str | None) -> str:
    if not value:
        return "nicht angegeben"
    local = datetime.fromisoformat(value).astimezone(ZoneInfo("Europe/Berlin"))
    abbreviation = local.strftime("%Z")
    zone = {"CET": "MEZ", "CEST": "MESZ"}.get(abbreviation, abbreviation)
    return local.strftime("%d.%m.%Y, %H:%M") + " " + zone


def excerpt(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit].rsplit(" ", 1)[0] + " […]"


def deadline_text(item: Data) -> str:
    kind = DEADLINES.get(item["kind"], item["kind"])
    if context := item.get("context"):
        kind += f" ({context})"
    if original := item.get("original"):
        detail = STATES.get(item["status"], item["status"])
        if (
            item["kind"] == "AdditionalInformationRequestPeriod"
            and item.get("method") == "labelled_text"
            and not item.get("original_time")
        ):
            detail = "Uhrzeit nicht angegeben"
        return f"{kind}: {original} · {detail}"
    if "dates" not in item:
        # Ältere Analysen enthalten Alternativen nur als indizierte XML-Belege.
        def originals(leaf: str, scalar: str) -> list[str]:
            quotes = [
                e["quote"]
                for e in item["evidence"]
                if e["path"].rsplit("/", 1)[-1].startswith(f"cbc:{leaf}[")
            ]
            return quotes or [item.get(scalar) or ""]

        item = deadline_components(
            originals("EndDate", "original_date"), originals("EndTime", "original_time")
        )
    parts = []
    for values, label in ((item["dates"], "Datum"), (item["times"], "Uhrzeit")):
        if len(values) > 1:
            parts.append(f"{label} widersprüchlich ({' oder '.join(values)})")
        else:
            parts.append(values[0] if values else f"{label} nicht angegeben")
    text = f"{kind}: " + ", ".join(parts)
    if item["berlin"]:
        text = f"{kind}: {local_time(item['berlin'])}"
    if item["reason"]:
        text += " · " + item["reason"]
    return text


def xml_leaf(item: Data) -> str:
    if item.get("method") == "xml" and item.get("evidence"):
        return item["evidence"][0]["path"].rsplit("/", 1)[-1].partition("[")[0]
    return ""


def field_value(item: Data) -> str:
    value = item["value"]
    if item.get("method") == "xml":
        leaf = item["evidence"][0]["path"].rsplit("/", 1)[-1].partition("[")[0]
        value = {
            ("cbc:DurationTypeCode", "UNLIMITED"): "Unbefristet",
            ("cbc:DescriptionCode", "UNLIMITED"): "Unbefristet",
            ("cbc:ProcedureCode", "neg-w-call"): "Verhandlungsverfahren mit Teilnahmewettbewerb",
            ("cbc:SubmissionMethodCode", "required"): "Elektronische Abgabe vorgeschrieben",
            ("cbc:SubmissionMethodCode", "allowed"): "Elektronische Abgabe zulässig",
            ("cbc:ProcedureCode", "open"): "Offenes Verfahren",
            ("cbc:ProcedureCode", "restricted"): "Nichtoffenes Verfahren",
        }.get((leaf, value), value)
        prefix = {"cbc:StartDate": "Beginn", "cbc:EndDate": "Ende"}.get(leaf)
        if prefix:
            if "/cac:PlannedPeriod[" in item["evidence"][0]["path"]:
                prefix = {"Beginn": "Planbeginn", "Ende": "Planende"}[prefix]
            try:
                value = datetime.strptime(value[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
            except ValueError:
                pass
            value = f"{prefix}: {value}"
    if unit := item.get("attributes", {}).get("unitCode"):
        units = {"YEAR": ("Jahr", "Jahre"), "MONTH": ("Monat", "Monate"), "DAY": ("Tag", "Tage")}
        value += " " + units.get(unit, (f"({unit})", f"({unit})"))[value != "1"]
    return value


def write_report(research: Data, analysis: Data | None, directory: Path) -> Path:
    register_fonts()
    styles = {
        key: ParagraphStyle(
            key,
            fontName=BOLD if heading else REGULAR,
            fontSize=size,
            leading=size * 1.4,
            spaceBefore=before,
            spaceAfter=3,
            keepWithNext=heading,
            textColor=colors.HexColor(color),
        )
        for key, size, before, heading, color in [
            ("title", 21, 3, True, "#12334A"),
            ("heading", 13, 10, True, "#125B62"),
            ("label", 10, 6, True, "#12334A"),
            ("body", 9, 0, False, "#192C36"),
            ("source", 8, 0, False, "#394E5C"),
        ]
    }
    story = []

    def paragraph(
        value: str, style: str = "body", *, markup: bool = False, field: str = ""
    ) -> None:
        content = Paragraph(value if markup else escape(value), styles[style])
        apply_fonts(content, field or content.getPlainText()[:80])
        story.append(content)

    profile = research["profile"]
    notices = research["notices"]
    notice_titles = {n["publication_number"]: text_value(n.get("title")) for n in notices}
    documents = {d["publication_number"]: d for d in (analysis or {}).get("documents", [])}
    paragraph("Ausschreibungsübersicht", "title")
    rows = [
        (notice, index, unit)
        for notice in notices
        for index, unit in enumerate(
            documents.get(notice["publication_number"], {}).get("units") or [None]
        )
    ]

    def priority(row: tuple[Data, int, Data | None]) -> tuple[bool, int]:
        unit = row[2] or {}
        fit = unit.get("fit", {}).get("status")
        return (
            unit.get("participation", {}).get("status") != "Frist offen",
            {"passend": 0, "unklar": 1, "unpassend": 2}.get(fit, 3),
        )

    units = [unit for _, _, unit in rows if unit]
    open_matches = sum(
        u["fit"]["status"] == "passend" and u["participation"]["status"] == "Frist offen"
        for u in units
    )
    if notices:
        paragraph(
            f"{len(notices)} {'Bekanntmachung' if len(notices) == 1 else 'Bekanntmachungen'}"
            f" · {len(units)} {'Los / Verfahren' if len(units) == 1 else 'Lose / Verfahren'}",
            "heading",
        )
        paragraph(f"{open_matches} fachlich passend mit offener Frist", "label")
    paragraph(profile["name"] + " · Recherche am " + local_time(research["started_at"]))
    if analysis:
        paragraph("Teilnahmestand zum Prüfzeitpunkt " + local_time(analysis["checked_at"]))
    if research["status"] == "empty":
        paragraph("Suche erfolgreich abgeschlossen. Keine Treffer im Suchbereich.", "heading")
    elif research["status"] != "complete":
        paragraph("Recherche unvollständig. Die Trefferzahl ist nur ein Zwischenstand.", "heading")
    if research.get("error"):
        paragraph(research["error"])
    for q in research["queries"]:
        if q.get("error"):
            paragraph(f"Abruffehler · {q['name']}: {q['error']}")
    if analysis and analysis["status"] != "complete":
        paragraph("Auswertung unvollständig. Offene Punkte stehen in den Steckbriefen.")
    requirements = {u["participation_requirements"]["status"] for u in units}
    shared = len(requirements) == 1 and len(units) == len(rows)
    if rows:
        paragraph(
            (
                "Teilnahmevoraussetzungen: " + next(iter(requirements)) + " bei allen. "
                if shared
                else ""
            )
            + "Unternehmensnachweise wurden nicht geprüft.",
            "source",
        )

    def notice_heading(notice: Data) -> None:
        number = notice["publication_number"]
        paragraph(
            text_value(notice.get("title")).split(" – ", 2)[-1],
            "label",
            field=f"Titel · TED {number}",
        )
        url = f"https://ted.europa.eu/de/notice/-/detail/{number}"
        retrieved = local_time(notice.get("document", {}).get("retrieved_at"))
        paragraph(
            link(url, f"TED {number}") + " · Abruf: " + escape(retrieved), "source", markup=True
        )

    def cell(markup: str, style: str = "body", field: str = "") -> Paragraph:
        content = Paragraph(markup, styles[style])
        apply_fonts(content, field or content.getPlainText()[:80])
        return content

    if rows:
        retrievals = {local_time(n.get("document", {}).get("retrieved_at")) for n in notices}
        if len(retrievals) == 1:
            paragraph("TED-Abruf aller Bekanntmachungen: " + next(iter(retrievals)), "source")
        table = [
            [
                cell(x, "label")
                for x in ("Ausschreibung / Los", "Passung", "Teilnahmestand und Frist")
            ]
        ]
        for notice, index, unit in sorted(rows, key=priority):
            number = notice["publication_number"]
            title = text_value(notice.get("title")).split(" – ", 2)[-1]
            scope = "Verfahren"
            if unit:
                scope = unit["lot_id"] or "Verfahren"
                names = [
                    v["value"]
                    for v in unit["fields"]["subject"]["values"]
                    if xml_leaf(v) == "cbc:Name"
                ]
                title = " · ".join(names) or title
            anchor = f"los-{number}-{index}"
            source = link(f"https://ted.europa.eu/de/notice/-/detail/{number}", f"TED {number}")
            retrieved = local_time(notice.get("document", {}).get("retrieved_at"))
            metadata = escape(scope) + " · " + source
            if len(retrievals) > 1:
                metadata += " · Abruf " + escape(retrieved)
            if unit and len(documents[number]["units"]) > 1:
                buyers = [v["value"] for v in unit["fields"]["buyer"]["values"]]
                if buyers:
                    title = " · ".join([*buyers, title])
            name = cell(
                f'<a href="#{anchor}">{escape(title)}</a><br/><font size="7">{metadata}</font>',
                "label",
                f"Titel · TED {number}",
            )
            fit = unit["fit"]["status"] if unit else "ungeklärt"
            status = unit["participation"]["status"] if unit else "ungeklärt"
            details = []
            if unit and status == "Frist offen":
                for entry in unit["fields"]["deadlines"]["values"]:
                    if entry["kind"] in (
                        "TenderSubmissionDeadlinePeriod",
                        "ParticipationRequestReceptionPeriod",
                    ):
                        details.append(deadline_text(entry))
            if not shared:
                details.append(
                    "Voraussetzungen: "
                    + (unit["participation_requirements"]["status"] if unit else "ungeklärt")
                )
            table.append(
                [
                    name,
                    cell(escape(fit)),
                    cell("<br/>".join(map(escape, [status, *dict.fromkeys(details)]))),
                ]
            )
        grid = Table(table, colWidths=[81 * mm, 24 * mm, 64 * mm], repeatRows=1, splitInRow=1)
        grid.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2efef")),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d6d8")),
                ]
            )
        )
        story.append(grid)

    def research_details() -> None:
        paragraph('<a name="recherche"/>Suchprofil und Recherchegrenzen', "heading", markup=True)
        country_label = (
            "Auftraggeberland" if profile["country_field"] == "buyer-country" else "Leistungsort"
        )
        paragraph(
            f"Stichtag {research['as_of']} · {profile['days_back']} Tage · "
            f"{country_label}: "
            f"{', '.join(profile['countries']) or 'alle Länder'} · Suchbereich {profile['scope']}"
        )
        codes = profile["cpv_codes"]
        paragraph("CPV-Filter: " + (" ODER ".join(codes) if codes else "keiner"))
        paragraph("Volltextsuche · mindestens eine Suchgruppe muss passen", "label")
        for query in profile["queries"]:
            conditions = [
                terms[0] if len(terms) == 1 else "(" + " ODER ".join(terms) + ")"
                for terms in query["term_groups"]
            ]
            paragraph(f"{query['name']}: " + " UND ".join(conditions))
        if analysis:
            paragraph("Unternehmensprofil: " + analysis["profile"]["company_profile"])

    if not rows:
        research_details()
    paragraph(
        "Analysegrundlage sind die erfolgreich abgerufenen vollständigen "
        "TED-Bekanntmachungen. Zusätzliche Vergabeunterlagen: " + LIMIT + "."
    )
    successful = [q for q in research["queries"] if q["status"] == "ok"]
    paragraph(
        f"{len(successful)} von {len(profile['queries'])} Suchgruppen erfolgreich abgefragt. "
        f"Nur neueste Fassungen, nach Veröffentlichungsdatum absteigend. "
        f"Auswahlgrenze: {profile['max_results']} Treffer je Suchgruppe und insgesamt."
    )
    if any(q.get("limited") for q in successful):
        paragraph("TED meldete für mindestens eine Suchgruppe weitere Treffer.")
    if research.get("unique_retrieved", 0) > len(notices):
        paragraph(
            f"Gesamtlimit: {len(notices)} von {research['unique_retrieved']} verschiedenen "
            "gelieferten Bekanntmachungen ausgewählt."
        )
    overview_path = "../../overview.html" if analysis else "overview.html"
    paragraph(
        f'<a href="{overview_path}" color="#125B62"><u>Laufübersicht ({overview_path})</u></a>'
        " · Suchanfragen und Rohantworten",
        "source",
        markup=True,
    )
    if rows:
        paragraph(
            '<a href="#recherche" color="#125B62">Suchprofil und Recherchegrenzen ansehen</a>',
            "source",
            markup=True,
        )
    appendices: list[
        tuple[str, dict[tuple[str, str], int], list[CriteriaDetails], list[Paragraph]]
    ] = []

    def source_links(number: str, ids: Iterable[int]) -> str:
        links = [f'<a href="#beleg-{number}-{i}" color="#125B62">{i}</a>' for i in ids]
        return " [" + ", ".join(links) + "]" if links else ""

    def add_brief(notice: Data) -> None:
        number = notice["publication_number"]
        doc = documents.get(number, {})
        source = notice.get("document", {})
        story.append(PageBreak())
        paragraph("Steckbrief", "title")
        notice_heading(notice)
        if versions := source.get("metadata", {}).get("versions"):
            paragraph("Dokumentversion: " + ", ".join(versions), "source")
        if conflicts := notice.get("conflicts"):
            paragraph("Widersprüchliche Suchangaben: " + ", ".join(conflicts))
        if doc.get("error") or not doc.get("units"):
            paragraph(
                "Auswertung unvollständig: "
                + str(source.get("error") or doc.get("error") or "Keine auswertbaren Angaben.")
            )
        sources: dict[tuple[str, str], int] = {}
        criteria_details: list[CriteriaDetails] = []

        def source_ids(items: Iterable[Data]) -> list[int]:
            return list(
                dict.fromkeys(
                    sources.setdefault((e["path"], e["quote"]), len(sources) + 1)
                    for item in items
                    for e in item.get("evidence", [])
                )
            )

        def refs(item: Data) -> str:
            return source_links(number, source_ids([item]))

        def add_criteria(unit: Data, key: str, label: str) -> None:
            field = unit["fields"][key]
            summaries = unit.get("criteria_summaries", {}).get(key, [])
            rejected = any(
                claim["claim"].get("field") == key and "summary" in claim["claim"]
                for claim in unit["rejected_claims"]
            )
            state = field["status"]
            if state == "missing" and (summaries or rejected):
                state = "uncertain" if rejected else "present"
            excerpts = field.get("notice_excerpts", [])
            lines = [escape(" ".join(item["value"].split())) + refs(item) for item in excerpts]
            if document_sources := field.get("document_sources"):
                lines.append(
                    "Einzelanforderungen in den Vergabeunterlagen prüfen."
                    + source_links(number, source_ids(document_sources))
                )
            lines.extend(escape(summary["summary"]) + refs(summary) for summary in summaries)
            raw_ids = source_ids(field["values"])
            if not lines:
                lines = ["keine geprüfte Kurzfassung" if state != "missing" else ""]
            if set(raw_ids).difference(source_ids([*excerpts, *summaries])):
                anchor = f"kriterien-{number}-{len(criteria_details) + 1}"
                scope = unit["lot_id"] or "Verfahren ohne Losaufteilung"
                criteria_details.append((anchor, f"{scope} · {label}", raw_ids))
                lines[-1] += f' · <a href="#{anchor}" color="#125B62">Originalangaben</a>'
            paragraph(
                f"{label}: " + " · ".join(filter(None, [STATES.get(state), lines[0]])),
                markup=True,
            )
            for line in lines[1:]:
                paragraph(line, markup=True)

        def checkpoint_line(point: Data) -> Paragraph:
            claim = point.get("claim", {})
            value = claim.get("value") or claim.get("reason")
            label = f"Zu prüfen: {str(value).rstrip('.')}. " if value else ""
            ids = source_ids([point, point.get("verification") or {}])
            line = escape(label + point["reason"]) + source_links(number, ids)
            if url := point.get("url"):
                line += " · " + link(url, "Unterlagen öffnen")
            return cell(line)

        detail_blocks: list[Paragraph] = []
        if not doc.get("units"):
            paragraph(f'<a name="los-{number}-0"/>', markup=True)
        for index, unit in enumerate(doc.get("units", [])):
            scope = unit["lot_id"] or "Verfahren ohne Losaufteilung"
            if index:
                story.append(PageBreak())
                paragraph(f"Steckbrief · TED {number}", "title")
            paragraph(f'<a name="los-{number}-{index}"/>{escape(scope)}', "heading", markup=True)
            for key, label in (
                ("participation", "Teilnahmestand"),
                ("fit", "Fachliche Passung"),
                ("participation_requirements", "Teilnahmevoraussetzungen"),
            ):
                value = unit[key]
                paragraph(
                    f"<b>{label}: {escape(value['status'])}.</b> "
                    + escape(value["reason"])
                    + refs(value)
                    + refs(value.get("verification") or {}),
                    markup=True,
                )
            paragraph("Pflichtangaben", "label")
            duration_checks = [
                p for p in unit["checkpoints"] if p.get("method") == "xml_duration_comparison"
            ]
            for key, label in LABELS.items():
                if key in CRITERIA_FIELDS:
                    add_criteria(unit, key, label)
                    continue
                if key == "tender_validity" and key not in unit["fields"]:
                    paragraph(f"{label}: nicht ausgewertet")
                    continue
                field = unit["fields"][key]
                state = STATES.get(field["status"], "")
                if key == "deadlines" and field["values"]:
                    grouped: dict[str, list[Data]] = {}
                    for item in field["values"]:
                        grouped.setdefault(deadline_text(item), []).append(item)
                    for line, items in grouped.items():
                        paragraph(
                            escape(line) + source_links(number, source_ids(items)), markup=True
                        )
                    if field["status"] in {"uncertain", "conflict"} and not any(
                        item.get("status") == field["status"] for item in field["values"]
                    ):
                        paragraph(f"{label}: {state}")
                    continue
                if key == "buyer" and index and field == doc["units"][0]["fields"]["buyer"]:
                    continue
                items = field["values"]
                extension_texts = []
                if key == "duration":
                    extension_texts = [
                        v
                        for v in items
                        if xml_leaf(v) == "cbc:OptionsDescription"
                        or (
                            xml_leaf(v) == "cbc:Description"
                            and "/cac:ContractExtension[" in v["evidence"][0]["path"]
                        )
                    ]
                    items = [v for v in items if v not in extension_texts]
                preferred = {
                    "subject": {"cbc:Name"},
                    "place": {"cbc:CityName", "cbc:Description"},
                    "duration": {
                        "cbc:StartDate",
                        "cbc:EndDate",
                        "cbc:DurationMeasure",
                        "cbc:Description",
                        "cbc:DescriptionCode",
                        "cbc:DurationTypeCode",
                    },
                    "submission": {"cbc:SubmissionMethodCode", "cbc:EndpointID"},
                }.get(key, set())
                visible = [v for v in items if xml_leaf(v) in preferred] or items
                if state and (key != "duration" or field["status"] == "conflict"):
                    visible = items
                extra = [v for v in items if v not in visible]
                values = []
                for v in visible:
                    value = field_value(v)
                    if xml_leaf(v) in {"cbc:EndpointID", "cbc:URI"} and value.startswith(
                        ("https://", "http://")
                    ):
                        display = link(
                            value, "Portal öffnen" if key == "submission" else "TED öffnen"
                        )
                    elif key == "source_link" and value.startswith(("https://", "http://")):
                        display = link(value, f"TED {number}")
                    else:
                        display = escape(excerpt(value, 240))
                    values.append(display + refs(v))
                if extra:
                    anchor = f"feld-{number}-{index}-{key}"
                    criteria_details.append((anchor, f"{scope} · {label}", source_ids(extra)))
                    values.append(f'<a href="#{anchor}" color="#125B62">Details</a>')
                paragraph(
                    f"<b>{label}:</b> " + " · ".join(filter(None, [state, *values])), markup=True
                )
                for item in sorted(
                    extension_texts, key=lambda v: xml_leaf(v) == "cbc:OptionsDescription"
                ):
                    prefix = (
                        "Optionen und Bedingungen"
                        if xml_leaf(item) == "cbc:OptionsDescription"
                        else "Verlängerung"
                    )
                    paragraph(
                        f"<b>{prefix}:</b> " + escape(" ".join(item["value"].split())) + refs(item),
                        markup=True,
                    )
                if key == "duration":
                    story.extend(checkpoint_line(point) for point in duration_checks)
            paragraph("Informationsqualität und Prüfpunkte", "label")
            for error in unit["processing_errors"]:
                paragraph("Verarbeitungsfehler: " + error)
            for rejected in unit["rejected_claims"]:
                if not any(p.get("claim_id") == rejected["claim_id"] for p in unit["checkpoints"]):
                    paragraph("Unbestätigte Aussage: " + rejected["reason"])
            extended = []
            immediate = {}
            for point in unit["checkpoints"]:
                if point in duration_checks:
                    continue
                if point.get("method") == "ai_verified":
                    extended.append(point)
                elif point.get("method") == "xml_lot_scope":
                    immediate.setdefault(point["reason"], []).append(point)
                else:
                    story.append(checkpoint_line(point))
            for reason, group in immediate.items():
                paragraph(escape(reason) + source_links(number, source_ids(group)), markup=True)
            if extended:
                anchor = f"pruefung-{number}-{index}"
                critical_paths = {
                    e["path"]
                    for field in unit["fields"].values()
                    if field["status"] in {"conflict", "uncertain"}
                    for item in field["values"]
                    for e in item.get("evidence", [])
                }
                preview = next(
                    (
                        p
                        for p in extended
                        if any(e["path"] in critical_paths for e in p.get("evidence", []))
                    ),
                    extended[0],
                )
                story.append(checkpoint_line(preview))
                detail_blocks.append(
                    cell(f'<a name="{anchor}"/>{escape(scope)} · Prüfpunkte', "label")
                )
                detail_blocks.extend(checkpoint_line(point) for point in extended)
                paragraph(
                    f'<a href="#{anchor}" color="#125B62">'
                    f"Alle {len(extended)} geprüften Hinweise zum Los lesen</a>",
                    "source",
                    markup=True,
                )
            if not (unit["processing_errors"] or unit["rejected_claims"] or unit["checkpoints"]):
                paragraph("Keine zusätzlichen Prüfpunkte erfasst.")
        if doc.get("checkpoints"):
            paragraph("Prüfpunkte zur Bekanntmachung", "heading")
            grouped = {}
            for point in doc["checkpoints"]:
                grouped.setdefault((point.get("url"), point["reason"]), []).append(point)
            for (url, reason), group in grouped.items():
                scopes = list(dict.fromkeys(p.get("lot_id") or "Bekanntmachung" for p in group))
                label = ", ".join(scopes) + " · " if url else ""
                line = escape(label + reason) + source_links(number, source_ids(group))
                if url:
                    line += " · " + link(url, "Unterlagen öffnen")
                paragraph(line, markup=True)
        if sources or detail_blocks:
            appendices.append((number, sources, criteria_details, detail_blocks))

    for notice in notices:
        add_brief(notice)

    for number, sources, criteria_details, detail_blocks in appendices:
        story.append(PageBreak())
        paragraph(f"Belegverzeichnis · TED {number}", "heading")
        if " – " in notice_titles[number]:
            paragraph(notice_titles[number], "source", field=f"Titel · TED {number}")
        paragraph(
            "Die Nummern im Steckbrief verweisen auf folgende Originalzitate und "
            "XML-Fundstellen dieser Bekanntmachung.",
            "source",
        )
        story.extend(detail_blocks)
        for anchor, label, ids in criteria_details:
            paragraph(
                f'<a name="{anchor}"/>{escape(label)}' + source_links(number, ids),
                "source",
                markup=True,
            )
        original_quotes: dict[str, int] = {}
        for (path, quote), index in sources.items():
            paragraph(
                f'<a name="beleg-{number}-{index}"/>[{index}] TED {number} · {escape(path)}',
                "source",
                markup=True,
            )
            if len(quote) > 250 and quote in original_quotes:
                previous = original_quotes[quote]
                paragraph(
                    f'Gleicher Wortlaut wie <a href="#beleg-{number}-{previous}" '
                    f'color="#125B62">Beleg [{previous}]</a>.',
                    markup=True,
                )
            else:
                paragraph(quote, "body", field=f"Beleg {index} · TED {number} · {path}")
                original_quotes[quote] = index

    if rows:
        story.append(PageBreak())
        research_details()

    def footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(REGULAR, 8)
        canvas.setFillColor(colors.HexColor("#394E5C"))
        line = canvas.beginText(18 * mm, 12 * mm)
        for name, text in font_runs("TED-Recherche  /  " + research["run_id"], REGULAR, "Lauf-ID"):
            line.setFont(name, 8)
            line.textOut(text)
        canvas.drawText(line)
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Seite {document.page}")
        canvas.restoreState()

    target = directory / "bericht.pdf"
    temporary = target.with_suffix(".pdf.tmp")
    document = SimpleDocTemplate(
        str(temporary),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title="TED-Ausschreibungsbericht",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    temporary.replace(target)
    return target
