"""Gemeinsame PDF-Formatierung für Übersicht, Steckbriefe und Belege."""

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, Paragraph

from ausschreibungen.extraction import deadline_components
from ausschreibungen.report_fonts import BOLD, REGULAR, apply_fonts, register_fonts

Data = dict[str, Any]
STATES = {"missing": "nicht angegeben", "uncertain": "unsicher", "conflict": "Widerspruch"}
DEADLINES = {
    "TenderSubmissionDeadlinePeriod": "Angebotsfrist",
    "ParticipationRequestReceptionPeriod": "Frist für Teilnahmeanträge",
    "InterestExpressionReceptionPeriod": "Frist für Interessenbekundungen",
    "AdditionalInformationRequestPeriod": "Frist für Rückfragen",
}


def local_time(value: str | None) -> str:
    if not value:
        return "nicht angegeben"
    local = datetime.fromisoformat(value).astimezone(ZoneInfo("Europe/Berlin"))
    abbreviation = local.strftime("%Z")
    zone = {"CET": "MEZ", "CEST": "MESZ"}.get(abbreviation, abbreviation)
    return local.strftime("%d.%m.%Y, %H:%M") + " " + zone


def deadline_text(item: Data) -> str:
    kind = DEADLINES.get(item["kind"], item["kind"])
    if context := item.get("context"):
        kind += f" ({context})"
    if original := item.get("original"):
        detail = STATES.get(item["status"], item["status"])
        if (
            item["kind"] == "AdditionalInformationRequestPeriod"
            and item["status"] == "uncertain"
            and not item.get("original_time")
        ):
            kind = "Rückfragen"
            detail = "Uhrzeit ungeklärt"
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


class ReportLayout:
    def __init__(self, *, overview_href: str, analysis_href: str) -> None:
        self.overview_href = overview_href
        self.analysis_href = analysis_href
        register_fonts()
        self.styles = {
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
        self.story: list[Flowable] = []

    def cell(self, markup: str, style: str = "body", field: str = "") -> Paragraph:
        content = Paragraph(markup, self.styles[style])
        apply_fonts(content, field or content.getPlainText()[:80])
        return content

    def paragraph(
        self, value: str, style: str = "body", *, markup: bool = False, field: str = ""
    ) -> None:
        self.story.append(self.cell(value if markup else escape(value), style, field))
