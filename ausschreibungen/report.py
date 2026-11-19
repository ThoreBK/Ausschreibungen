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
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

from ausschreibungen.analysis import CRITERIA_FIELDS, deadline_components
from ausschreibungen.report_fonts import BOLD, REGULAR, apply_fonts, font_runs, register_fonts
from ausschreibungen.research import link, text_value

LABELS = {
    "buyer": "Auftraggeber",
    "subject": "Gegenstand",
    "place": "Leistungsort",
    "procedure": "Verfahrensart",
    "deadlines": "Fristen",
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
    return (
        datetime.fromisoformat(value)
        .astimezone(ZoneInfo("Europe/Berlin"))
        .strftime("%d.%m.%Y, %H:%M %Z")
    )


def excerpt(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit].rsplit(" ", 1)[0] + " […]"


def deadline_text(item: Data) -> str:
    kind = DEADLINES.get(item["kind"], item["kind"])
    if context := item.get("context"):
        kind += f" ({context})"
    if original := item.get("original"):
        return f"{kind}: {original} · {STATES.get(item['status'], item['status'])}"
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
        text += f" (Berlin: {local_time(item['berlin'])})"
    if item["reason"]:
        text += " · " + item["reason"]
    return text


def field_value(item: Data) -> str:
    value = item["value"]
    if item.get("method") == "xml":
        leaf = item["evidence"][0]["path"].rsplit("/", 1)[-1].partition("[")[0]
        value = {
            ("cbc:ProcedureCode", "open"): "Offenes Verfahren",
            ("cbc:ProcedureCode", "restricted"): "Nichtoffenes Verfahren",
        }.get((leaf, value), value)
        prefix = {"cbc:StartDate": "Beginn", "cbc:EndDate": "Ende"}.get(leaf)
        if prefix:
            value = f"{prefix}: {value}"
    if unit := item.get("attributes", {}).get("unitCode"):
        value += f" ({unit})"
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
    documents = {d["publication_number"]: d for d in (analysis or {}).get("documents", [])}
    paragraph("Ausschreibungsübersicht", "title")
    paragraph(profile["name"], "heading")
    paragraph(f"Recherche am {local_time(research['started_at'])} · Quelle: TED")
    paragraph(
        f"Stichtag {research['as_of']} · {profile['days_back']} Tage · "
        f"{'Auftraggeberland' if profile['country_field'] == 'buyer-country' else 'Leistungsort'}: "
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
    if notices:
        paragraph(f"Ausgewählte Bekanntmachungen · {len(notices)}", "heading")
        paragraph(
            "Teilnahmestand zum Prüfzeitpunkt"
            + (f" {local_time(analysis['checked_at'])}" if analysis else "")
            + ". Unternehmensnachweise wurden nicht geprüft."
        )

    def notice_heading(notice: Data, *, overview: bool = False) -> None:
        number = notice["publication_number"]
        title = escape(text_value(notice.get("title")))
        if overview:
            title = f'<a href="#steckbrief-{number}">{title}</a>'
        else:
            title = f'<a name="steckbrief-{number}"/>{title}'
        paragraph(title, "label", markup=True, field=f"Titel · TED {number}")
        url = f"https://ted.europa.eu/de/notice/-/detail/{number}"
        retrieved = local_time(notice.get("document", {}).get("retrieved_at"))
        paragraph(
            link(url, f"TED {number}") + " · Abruf: " + escape(retrieved), "source", markup=True
        )

    for notice in notices:
        notice_heading(notice, overview=True)
        units = documents.get(notice["publication_number"], {}).get("units", [])
        if not units:
            paragraph("Passung, Teilnahmestand und Teilnahmevoraussetzungen ungeklärt.")
        for unit in units:
            paragraph(
                f"{unit['lot_id'] or 'Verfahren'} · Passung: {unit['fit']['status']} · "
                f"Teilnahmestand: {unit['participation']['status']} · "
                f"Teilnahmevoraussetzungen: {unit['participation_requirements']['status']}"
            )
    appendices: list[tuple[str, dict[tuple[str, str], int], list[CriteriaDetails]]] = []

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
            lines = [escape(summary["summary"]) + refs(summary) for summary in summaries]
            raw_ids = source_ids(field["values"])
            if not lines:
                lines = ["keine geprüfte Kurzfassung" if state != "missing" else ""]
            if set(raw_ids).difference(source_ids(summaries)):
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

        def checkpoint(point: Data) -> None:
            label = (point.get("lot_id") or "Bekanntmachung") + " · " if point.get("url") else ""
            claim = point.get("claim", {})
            if claim:
                label += "Zu prüfen: " + str(claim.get("value") or claim.get("reason")) + ". "
            paragraph(
                escape(label + point["reason"])
                + source_links(number, source_ids([point, point.get("verification") or {}])),
                markup=True,
            )
            if url := point.get("url"):
                paragraph(link(url, url), "source", markup=True)

        for unit in doc.get("units", []):
            paragraph(unit["lot_id"] or "Verfahren ohne Losaufteilung", "heading")
            for key, label in (
                ("fit", "Fachliche Passung"),
                ("participation", "Teilnahmestand"),
                ("participation_requirements", "Teilnahmevoraussetzungen"),
            ):
                value = unit[key]
                paragraph(
                    escape(f"{label}: {value['status']}. {value['reason']}")
                    + refs(value)
                    + refs(value.get("verification") or {}),
                    markup=True,
                )
            paragraph("Pflichtangaben", "label")
            for key, label in LABELS.items():
                if key in CRITERIA_FIELDS:
                    add_criteria(unit, key, label)
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
                values = [escape(excerpt(field_value(v), 240)) + refs(v) for v in field["values"]]
                paragraph(f"{label}: " + " · ".join(filter(None, [state, *values])), markup=True)
            paragraph("Informationsqualität und Prüfpunkte", "label")
            for error in unit["processing_errors"]:
                paragraph("Verarbeitungsfehler: " + error)
            for rejected in unit["rejected_claims"]:
                if not any(p.get("claim_id") == rejected["claim_id"] for p in unit["checkpoints"]):
                    paragraph("Unbestätigte Aussage: " + rejected["reason"])
            for point in unit["checkpoints"]:
                checkpoint(point)
            if not (unit["processing_errors"] or unit["rejected_claims"] or unit["checkpoints"]):
                paragraph("Keine zusätzlichen Prüfpunkte erfasst.")
        if doc.get("checkpoints"):
            paragraph("Prüfpunkte zur Bekanntmachung", "heading")
            for point in doc["checkpoints"]:
                checkpoint(point)
        if sources:
            appendices.append((number, sources, criteria_details))

    for notice in notices:
        add_brief(notice)

    for number, sources, criteria_details in appendices:
        story.append(PageBreak())
        paragraph(f"Belegverzeichnis · TED {number}", "heading")
        paragraph(
            "Die Nummern im Steckbrief verweisen auf folgende Originalzitate und "
            "XML-Fundstellen dieser Bekanntmachung.",
            "source",
        )
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
