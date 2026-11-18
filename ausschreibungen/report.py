"""Lesbare TED-Berichte mit kompakten Steckbriefen und auflösbaren XML-Belegen."""

import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

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


def field_value(item: Data) -> str:
    if "kind" in item:
        kind = DEADLINES.get(item["kind"], item["kind"])
        original = item.get("original") or (
            f"{item.get('original_date') or 'Datum nicht angegeben'}, "
            f"{item.get('original_time') or 'Uhrzeit nicht angegeben'}"
        )
        berlin = f" (Berlin: {local_time(item['berlin'])})" if item.get("berlin") else ""
        return f"{kind}: {original}{berlin}"
    value = item["value"]
    if item.get("method") == "xml":
        leaf = item["evidence"][0]["path"].rsplit("/", 1)[-1].partition("[")[0]
        value = {
            ("cbc:ProcedureCode", "open"): "Offenes Verfahren",
            ("cbc:ProcedureCode", "restricted"): "Nichtoffenes Verfahren",
            ("cbc:AwardingCriterionTypeCode", "quality"): "Qualität",
            ("cbc:AwardingCriterionTypeCode", "cost"): "Kosten",
            ("cbc:AwardingCriterionTypeCode", "price"): "Preis",
            ("efbc:ParameterCode", "per-exa"): "Gewichtung in Prozent",
        }.get((leaf, value), value)
        prefix = {"cbc:StartDate": "Beginn", "cbc:EndDate": "Ende"}.get(leaf)
        if prefix:
            value = f"{prefix}: {value}"
    if unit := item.get("attributes", {}).get("unitCode"):
        value += f" ({unit})"
    return value


def write_report(research: Data, analysis: Data | None, directory: Path) -> Path:
    pdfmetrics.registerFont(TTFont("Vera", "Vera.ttf"))
    pdfmetrics.registerFont(TTFont("VeraBold", "VeraBd.ttf"))
    styles = {
        key: ParagraphStyle(
            key,
            fontName="VeraBold" if heading else "Vera",
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

    def paragraph(value: str, style: str = "body", *, markup: bool = False) -> None:
        story.append(Paragraph(value if markup else escape(value), styles[style]))

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
    paragraph("Suchgruppen: " + ", ".join(q["name"] for q in profile["queries"]))
    if analysis:
        paragraph("Unternehmensprofil: " + analysis["profile"]["company_profile"])
    paragraph(
        "Analysegrundlage sind die erfolgreich abgerufenen vollständigen "
        "TED-Bekanntmachungen. Zusätzliche Vergabeunterlagen: " + LIMIT + "."
    )
    paragraph(
        f"Auswahlgrenze: {profile['max_results']} Treffer je Suchgruppe und insgesamt."
        + (" Trefferlimit erreicht." if research.get("limited") else "")
    )
    paragraph("Die Suche berücksichtigt nur die von TED gelieferten neuesten Fassungen.")
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
        paragraph(title, "label", markup=True)
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
            eligibility = unit["fields"]["selection_criteria"]
            if eligibility["status"] == "present":
                descriptions = [
                    v["value"]
                    for v in eligibility["values"]
                    if v.get("method") != "xml" or "/cbc:Description[" in v["evidence"][0]["path"]
                ]
                if descriptions:
                    paragraph(
                        "Eignung laut Bekanntmachung (Auszug): " + excerpt(descriptions[0], 130),
                        "source",
                    )

    appendices: list[tuple[str, dict[tuple[str, str], int]]] = []

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

        def refs(item: Data) -> str:
            ids = []
            for evidence in item.get("evidence", []):
                key = (evidence["path"], evidence["quote"])
                index = sources.setdefault(key, len(sources) + 1)
                ids.append(f'<a href="#beleg-{number}-{index}" color="#125B62">{index}</a>')
            return " [" + ", ".join(ids) + "]" if ids else ""

        def checkpoint(point: Data) -> None:
            label = (point.get("lot_id") or "Bekanntmachung") + " · " if point.get("url") else ""
            claim = point.get("claim", {})
            if claim:
                label += "Zu prüfen: " + str(claim.get("value") or claim.get("reason")) + ". "
            paragraph(
                escape(label + point["reason"])
                + refs(point)
                + refs(point.get("verification") or {}),
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
                field = unit["fields"][key]
                state = STATES.get(field["status"], "")
                groups: dict[str, list[str]] = {}
                further: list[str] = []
                shown = 0
                for v in field["values"]:
                    if key == "selection_criteria" and len(field["values"]) > 6:
                        if shown >= 3 or v.get("attributes", {}).get("listName"):
                            further.append(refs(v))
                            continue
                        shown += 1
                    group = ""
                    if key == "award_criteria" and v.get("method") == "xml":
                        match = re.match(
                            r"(.*/cac:(?:Subordinate)?AwardingCriterion\[\d+\])/",
                            v["evidence"][0]["path"],
                        )
                        group = match[1] if match else ""
                    groups.setdefault(group, []).append(
                        escape(excerpt(field_value(v), 240)) + refs(v)
                    )
                lines = [" · ".join(entries) for entries in groups.values()]
                paragraph(f"{label}: " + " · ".join(filter(None, [state, *lines[:1]])), markup=True)
                for line in lines[1:]:
                    paragraph(line, markup=True)
                if further:
                    paragraph(
                        "Weitere Angaben im Belegverzeichnis: " + " ".join(further),
                        "source",
                        markup=True,
                    )
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
            appendices.append((number, sources))

    for notice in notices:
        add_brief(notice)

    for number, sources in appendices:
        story.append(PageBreak())
        paragraph(f"Belegverzeichnis · TED {number}", "heading")
        paragraph(
            "Die Nummern im Steckbrief verweisen auf folgende Originalzitate und "
            "XML-Fundstellen dieser Bekanntmachung.",
            "source",
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
                paragraph(quote, "body")
                original_quotes[quote] = index

    def footer(canvas: Canvas, document: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Vera", 8)
        canvas.setFillColor(colors.HexColor("#394E5C"))
        canvas.drawString(18 * mm, 12 * mm, "TED-Recherche  /  " + research["run_id"])
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
