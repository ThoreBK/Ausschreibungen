"""Berichtsübersicht, Reihenfolge der Steckbriefe und Ausgabe als PDF."""

from html import escape
from os.path import relpath
from pathlib import Path
from urllib.parse import quote

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import CondPageBreak, PageBreak, SimpleDocTemplate, Table, TableStyle

from ausschreibungen.notices import PARTICIPATION_PERIODS
from ausschreibungen.report_brief import add_brief
from ausschreibungen.report_fonts import REGULAR, font_runs
from ausschreibungen.report_layout import Data, ReportLayout, deadline_text, local_time, xml_leaf
from ausschreibungen.research import link, text_value

LIMIT = "in dieser Version nicht abgerufen und nicht ausgewertet"
ReportRow = tuple[Data, int, Data | None]


def research_details(layout: ReportLayout, research: Data, analysis: Data | None) -> None:
    profile = research["profile"]
    layout.paragraph('<a name="recherche"/>Suchprofil und Recherchegrenzen', "heading", markup=True)
    country_label = (
        "Auftraggeberland" if profile["country_field"] == "buyer-country" else "Leistungsort"
    )
    layout.paragraph(
        f"Stichtag {research['as_of']} · {profile['days_back']} Tage · "
        f"{country_label}: "
        f"{', '.join(profile['countries']) or 'alle Länder'} · Suchbereich {profile['scope']}"
    )
    codes = profile["cpv_codes"]
    layout.paragraph("CPV-Filter: " + (" ODER ".join(codes) if codes else "keiner"))
    layout.paragraph("Volltextsuche · mindestens eine Suchgruppe muss passen", "label")
    for query in profile["queries"]:
        conditions = [
            terms[0] if len(terms) == 1 else "(" + " ODER ".join(terms) + ")"
            for terms in query["term_groups"]
        ]
        layout.paragraph(f"{query['name']}: " + " UND ".join(conditions))
    if analysis:
        layout.paragraph("Unternehmensprofil: " + analysis["profile"]["company_profile"])


def overview_rows(
    notices: list[Data], documents: dict[str, Data], selection: Data | None
) -> list[ReportRow]:
    if selection is not None:
        notices_by_number = {n["publication_number"]: n for n in notices}
        rows = []
        for entry in selection["selected"]:
            number, index = entry["publication_number"], entry["unit_index"]
            unit = {
                **documents[number]["units"][index],
                "fit": entry["fit"],
                "participation": entry["participation"],
                "selection_entry": entry,
            }
            rows.append((notices_by_number[number], index, unit))
        return rows
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

    return sorted(rows, key=priority)


def add_overview(
    layout: ReportLayout,
    research: Data,
    analysis: Data | None,
    documents: dict[str, Data],
    rows: list[ReportRow],
) -> None:
    notices = research["notices"]
    profile = research["profile"]
    selection = (analysis or {}).get("selection")
    layout.paragraph("Ausschreibungsübersicht", "title")
    units = [unit for _, _, unit in rows if unit]
    open_matches = sum(
        u["fit"]["status"] == "passend" and u["participation"]["status"] == "Frist offen"
        for u in units
    )
    if notices:
        layout.paragraph(
            f"{len(notices)} {'Bekanntmachung' if len(notices) == 1 else 'Bekanntmachungen'}"
            f" · {len(units)} {'Los / Verfahren' if len(units) == 1 else 'Lose / Verfahren'}",
            "heading",
        )
        layout.paragraph(f"{open_matches} fachlich passend mit offener Frist", "label")
    layout.paragraph(profile["name"] + " · Recherche am " + local_time(research["started_at"]))
    if analysis:
        layout.paragraph("Teilnahmestand zum Prüfzeitpunkt " + local_time(analysis["checked_at"]))
    if research["status"] == "empty":
        layout.paragraph(
            "Suche erfolgreich abgeschlossen. Keine Treffer im Suchbereich.", "heading"
        )
    elif research["status"] != "complete":
        layout.paragraph(
            "Recherche unvollständig. Die Trefferzahl ist nur ein Zwischenstand.", "heading"
        )
    if research.get("error"):
        layout.paragraph(research["error"])
    for q in research["queries"]:
        if q.get("error"):
            layout.paragraph(f"Abruffehler · {q['name']}: {q['error']}")
    if analysis and analysis["status"] != "complete":
        layout.paragraph(
            "Auswertung unvollständig. Offene Punkte stehen in der Auswertung und im PDF."
        )
    if selection is not None:
        layout.paragraph(
            f"Berichtslimit: {selection['limit']} Lose oder Verfahren nach Auswahl und "
            f"Zusammenführung. {len(selection['limited'])} weitere Einträge am Limit ausgelassen."
        )
        layout.paragraph(selection["order"], "source")
        if not rows:
            layout.paragraph(
                "Keine ausgewerteten Lose oder Verfahren für die Berichtsliste ausgewählt."
            )
        layout.paragraph(
            f'<a href="{layout.analysis_href}#berichtsauswahl" color="#125B62">Berichtsauswahl und '
            f"Dokumentstände prüfen</a> · {len(selection['excluded'])} ausgeschlossen · "
            f"{len(selection['unavailable'])} Bekanntmachungen ohne Auswertung",
            "source",
            markup=True,
        )
        if selection["unavailable"]:
            layout.paragraph(
                "Auswertung fehlt für TED " + ", ".join(selection["unavailable"]) + ".",
                "source",
            )
    requirements = {u["participation_requirements"]["status"] for u in units}
    shared = len(requirements) == 1 and len(units) == len(rows)
    if rows:
        layout.paragraph(
            (
                "Teilnahmevoraussetzungen: " + next(iter(requirements)) + " bei allen. "
                if shared
                else ""
            )
            + "Unternehmensnachweise wurden nicht geprüft.",
            "source",
        )

    if rows:
        retrievals = {local_time(n.get("document", {}).get("retrieved_at")) for n in notices}
        if len(retrievals) == 1:
            layout.paragraph(
                "TED-Abruf aller Bekanntmachungen: " + next(iter(retrievals)), "source"
            )
        table = [
            [
                layout.cell(x, "label")
                for x in ("Ausschreibung / Los", "Passung", "Teilnahmestand und Frist")
            ]
        ]
        for notice, index, unit in rows:
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
            name = layout.cell(
                f'<a href="#{anchor}">{escape(title)}</a><br/><font size="7">{metadata}</font>',
                "label",
                f"Titel · TED {number}",
            )
            fit = unit["fit"]["status"] if unit else "ungeklärt"
            status = unit["participation"]["status"] if unit else "ungeklärt"
            details = []
            if unit and status == "Frist offen":
                for entry in unit["fields"]["deadlines"]["values"]:
                    if entry["kind"] in PARTICIPATION_PERIODS:
                        details.append(deadline_text(entry))
            if not shared:
                details.append(
                    "Voraussetzungen: "
                    + (unit["participation_requirements"]["status"] if unit else "ungeklärt")
                )
            table.append(
                [
                    name,
                    layout.cell(escape(fit)),
                    layout.cell("<br/>".join(map(escape, [status, *dict.fromkeys(details)]))),
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
        layout.story.append(grid)

    if not rows:
        research_details(layout, research, analysis)
    layout.paragraph(
        "Analysegrundlage sind die erfolgreich abgerufenen vollständigen "
        "TED-Bekanntmachungen. Zusätzliche Vergabeunterlagen: " + LIMIT + "."
    )
    successful = [q for q in research["queries"] if q["status"] == "ok"]
    search_limit = (
        "je Suchgruppe" if research.get("all_returned") else "je Suchgruppe und insgesamt"
    )
    layout.paragraph(
        f"{len(successful)} von {len(profile['queries'])} Suchgruppen erfolgreich abgefragt. "
        f"Nur neueste Fassungen, nach Veröffentlichungsdatum absteigend. "
        f"Abruflimit: {profile['max_results']} Treffer {search_limit}."
    )
    if any(q.get("limited") for q in successful):
        layout.paragraph("TED meldete für mindestens eine Suchgruppe weitere Treffer.")
    if research.get("unique_retrieved", 0) > len(notices):
        layout.paragraph(
            f"Gesamtlimit: {len(notices)} von {research['unique_retrieved']} verschiedenen "
            "gelieferten Bekanntmachungen ausgewählt."
        )
    layout.paragraph(
        f'<a href="{layout.overview_href}" color="#125B62"><u>Laufübersicht öffnen</u></a>'
        " · Suchanfragen und Rohantworten",
        "source",
        markup=True,
    )
    if rows:
        layout.paragraph(
            '<a href="#recherche" color="#125B62">Suchprofil und Recherchegrenzen ansehen</a>',
            "source",
            markup=True,
        )


def write_report(
    research: Data, analysis: Data | None, directory: Path, *, output_dir: Path | None = None
) -> Path:
    output_dir = output_dir or directory
    details = directory.parent.parent if analysis else directory
    layout = ReportLayout(
        overview_href=quote(Path(relpath(details / "overview.html", output_dir)).as_posix()),
        analysis_href=quote(Path(relpath(directory / "analysis.html", output_dir)).as_posix()),
    )
    notices = research["notices"]
    documents = {d["publication_number"]: d for d in (analysis or {}).get("documents", [])}
    selection = (analysis or {}).get("selection")
    rows = overview_rows(notices, documents, selection)
    add_overview(layout, research, analysis, documents, rows)

    selected_units: dict[str, dict[int, Data]] = {}
    brief_notices = notices
    if selection is not None:
        for notice, index, unit in rows:
            if unit is not None:
                selected_units.setdefault(notice["publication_number"], {})[index] = unit
        notices_by_number = {n["publication_number"]: n for n in notices}
        brief_notices = [notices_by_number[n] for n in [*selected_units, *selection["unavailable"]]]

    appendices = []
    section_start_space = 215 * mm
    for index, notice in enumerate(brief_notices):
        layout.story.append(CondPageBreak(section_start_space) if index else PageBreak())
        selected = (
            selected_units.get(notice["publication_number"], {}) if selection is not None else None
        )
        appendix = add_brief(layout, notice, documents, selected)
        if appendix.sources or appendix.detail_blocks:
            appendices.append(appendix)

    for appendix in appendices:
        layout.story.append(CondPageBreak(section_start_space))
        appendix.write(layout)
    if rows:
        research_details(layout, research, analysis)

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

    target = output_dir / "bericht.pdf"
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
    document.build(layout.story, onFirstPage=footer, onLaterPages=footer)
    temporary.replace(target)
    return target
