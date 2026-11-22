"""Steckbriefe und das zugehörige Belegverzeichnis je Bekanntmachung."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from html import escape

from reportlab.platypus import PageBreak, Paragraph

from ausschreibungen.extraction import CRITERIA_FIELDS
from ausschreibungen.notices import PARTICIPATION_PERIODS
from ausschreibungen.report_layout import (
    STATES,
    Data,
    ReportLayout,
    deadline_text,
    local_time,
    xml_leaf,
)
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
FIELD_PREVIEW_LENGTH = 240
CriteriaDetails = tuple[str, str, list[int]]


def excerpt(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit].rsplit(" ", 1)[0] + " […]"


def criteria_originals(unit: Data, key: str, summaries: list[Data]) -> list[Data]:
    field = unit["fields"][key]
    summarized_paths = {e["path"] for summary in summaries for e in summary["evidence"]}
    originals = []
    for review in unit.get("claim_reviews", []):
        claim = review["claim"]
        if claim.get("field") != key or "value" not in claim:
            continue
        if (review.get("model_check") or {}).get("status") != "bestätigt":
            continue
        # Frühere Gegenprüfungen haben die inhaltliche Abdeckung nicht protokolliert.
        # Deren Originalzitate bleiben über die Originalangaben des Feldes erreichbar.
        paths = {e["path"] for e in claim["evidence"]}
        if not review.get("covered_by", paths <= summarized_paths):
            originals.append(claim)
    # Ältere Analysen können eigene Auszüge enthalten. Längere Originale derselben
    # Fundstelle schließen solche Ausschnitte bereits ein.
    for excerpt_value in field.get("notice_excerpts", []):
        path = excerpt_value["evidence"][0]["path"]
        if path not in summarized_paths:
            full = next(
                (
                    v
                    for v in field["values"]
                    if xml_leaf(v) == "cbc:Description" and v["evidence"][0]["path"] == path
                ),
                excerpt_value,
            )
            originals.append(full)
    return [
        v
        for v in originals
        if not any(
            v["value"] != other["value"]
            and v["value"] in other["value"]
            and v["evidence"][0]["path"] == other["evidence"][0]["path"]
            for other in originals
        )
    ]


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
            ("cbc:SubmissionMethodCode", "not-allowed"): "Elektronische Abgabe nicht zulässig",
            ("cbc:Region", "anyw"): "Beliebiger Ort",
            ("cbc:Region", "anyw-cou"): "Landesweit",
            ("cbc:Region", "anyw-eea"): "Im gesamten Europäischen Wirtschaftsraum",
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
    if item.get("kind") == "minimum_service_months":
        return "Mindestlaufzeit ab Leistungsbeginn: " + value
    return value


@dataclass
class NoticeAppendix:
    number: str
    title: str
    sources: dict[tuple[str, str], int] = field(default_factory=dict)
    criteria_details: list[CriteriaDetails] = field(default_factory=list)
    detail_blocks: list[Paragraph] = field(default_factory=list)

    def source_ids(self, items: Iterable[Data]) -> list[int]:
        ids = []
        for item in items:
            for evidence in item.get("evidence", []):
                key = evidence["path"], evidence["quote"]
                ids.append(self.sources.setdefault(key, len(self.sources) + 1))
        return list(dict.fromkeys(ids))

    def links(self, ids: Iterable[int]) -> str:
        links = [f'<a href="#beleg-{self.number}-{i}" color="#125B62">{i}</a>' for i in ids]
        return " [" + ", ".join(links) + "]" if links else ""

    def refs(self, *items: Data) -> str:
        return self.links(self.source_ids(items))

    def write(self, layout: ReportLayout) -> None:
        number = self.number
        layout.paragraph(f"Belegverzeichnis · TED {number}", "heading")
        if " – " in self.title:
            layout.paragraph(self.title, "source", field=f"Titel · TED {number}")
        layout.paragraph(
            "Die Nummern im Steckbrief verweisen auf folgende Originalzitate und "
            "XML-Fundstellen dieser Bekanntmachung.",
            "source",
        )
        layout.story.extend(self.detail_blocks)
        for anchor, label, ids in self.criteria_details:
            layout.paragraph(
                f'<a name="{anchor}"/>{escape(label)}' + self.links(ids),
                "source",
                markup=True,
            )
        original_quotes: dict[str, int] = {}
        for (path, quote), index in self.sources.items():
            layout.paragraph(
                f'<a name="beleg-{number}-{index}"/>[{index}] TED {number} · {escape(path)}',
                "source",
                markup=True,
            )
            if len(quote) > 250 and quote in original_quotes:
                previous = original_quotes[quote]
                layout.paragraph(
                    f'Gleicher Wortlaut wie <a href="#beleg-{number}-{previous}" '
                    f'color="#125B62">Beleg [{previous}]</a>.',
                    markup=True,
                )
            else:
                layout.paragraph(quote, "body", field=f"Beleg {index} · TED {number} · {path}")
                original_quotes[quote] = index


def notice_heading(layout: ReportLayout, notice: Data) -> None:
    number = notice["publication_number"]
    layout.paragraph(
        text_value(notice.get("title")).split(" – ", 2)[-1],
        "label",
        field=f"Titel · TED {number}",
    )
    url = f"https://ted.europa.eu/de/notice/-/detail/{number}"
    retrieved = local_time(notice.get("document", {}).get("retrieved_at"))
    layout.paragraph(
        link(url, f"TED {number}") + " · Abruf: " + escape(retrieved), "source", markup=True
    )


def add_criteria(
    layout: ReportLayout, appendix: NoticeAppendix, unit: Data, key: str, label: str
) -> None:
    number = appendix.number
    field = unit["fields"][key]
    summaries = unit.get("criteria_summaries", {}).get(key, [])
    rejected = any(
        claim["claim"].get("field") == key and "summary" in claim["claim"]
        for claim in unit["rejected_claims"]
    )
    state = field["status"]
    if state == "missing" and (summaries or rejected):
        state = "uncertain" if rejected else "present"
    originals = criteria_originals(unit, key, summaries)
    summarized_paths = {e["path"] for summary in summaries for e in summary["evidence"]}
    long_originals = [
        item
        for item in originals
        if len(item["value"]) > FIELD_PREVIEW_LENGTH
        and any(e["path"] in summarized_paths for e in item["evidence"])
    ]
    grouped: dict[str, list[Data]] = {}
    for item in [*summaries, *(v for v in originals if v not in long_originals)]:
        value = item.get("summary") or item["value"]
        grouped.setdefault(" ".join(value.split()), []).append(item)
    lines = [escape(value) + appendix.refs(*items) for value, items in grouped.items()]
    if long_originals:
        lines.append(
            "Ergänzende Originalpassagen vollständig lesen" + appendix.refs(*long_originals)
        )
    if document_sources := field.get("document_sources"):
        label_source = (
            "Verweis auf Vergabeunterlagen"
            if lines
            else "Einzelanforderungen in den Vergabeunterlagen prüfen."
        )
        lines.append(label_source + appendix.refs(*document_sources))
    raw_ids = appendix.source_ids(field["values"])
    if not lines:
        lines = ["keine geprüfte Kurzfassung" if state != "missing" else ""]
    if set(raw_ids).difference(appendix.source_ids([*originals, *summaries])):
        anchor = f"kriterien-{number}-{len(appendix.criteria_details) + 1}"
        scope = unit["lot_id"] or "Verfahren ohne Losaufteilung"
        appendix.criteria_details.append((anchor, f"{scope} · {label}", raw_ids))
        lines[-1] += f' · <a href="#{anchor}" color="#125B62">Originalangaben</a>'
    layout.paragraph(
        f"{label}: " + " · ".join(filter(None, [STATES.get(state), lines[0]])),
        markup=True,
    )
    for line in lines[1:]:
        layout.paragraph(line, markup=True)


def checkpoint_line(layout: ReportLayout, appendix: NoticeAppendix, point: Data) -> Paragraph:
    claim = point.get("claim", {})
    value = claim.get("value") or claim.get("reason")
    if claim.get("kind") == "minimum_service_months":
        value = f"Mindestlaufzeit ab Leistungsbeginn von {value} Monaten"
    label = f"Zu prüfen: {str(value).rstrip('.')}. " if value else ""
    ids = appendix.source_ids([point, point.get("verification") or {}])
    line = escape(label + point["reason"]) + appendix.links(ids)
    if url := point.get("url"):
        line += " · " + link(url, "Unterlagen öffnen")
    return layout.cell(line)


def add_brief(
    layout: ReportLayout, notice: Data, documents: dict[str, Data], selected: dict[int, Data] | None
) -> NoticeAppendix:
    number = notice["publication_number"]
    doc = documents.get(number, {})
    source = notice.get("document", {})
    layout.paragraph("Steckbrief", "title")
    notice_heading(layout, notice)
    if versions := source.get("metadata", {}).get("versions"):
        layout.paragraph("Dokumentversion: " + ", ".join(versions), "source")
    if conflicts := notice.get("conflicts"):
        layout.paragraph("Widersprüchliche Suchangaben: " + ", ".join(conflicts))
    if doc.get("error") or not doc.get("units"):
        layout.paragraph(
            "Auswertung unvollständig: "
            + str(source.get("error") or doc.get("error") or "Keine auswertbaren Angaben.")
        )
    appendix = NoticeAppendix(number, text_value(notice.get("title")))
    brief_units = selected.items() if selected is not None else enumerate(doc.get("units", []))
    if not doc.get("units"):
        layout.paragraph(f'<a name="los-{number}-0"/>', markup=True)
    first_buyer = None
    for position, (index, unit) in enumerate(brief_units):
        scope = unit["lot_id"] or "Verfahren ohne Losaufteilung"
        if position:
            layout.story.append(PageBreak())
            layout.paragraph(f"Steckbrief · TED {number}", "title")
        layout.paragraph(f'<a name="los-{number}-{index}"/>{escape(scope)}', "heading", markup=True)
        for key, label in (
            ("participation", "Teilnahmestand"),
            ("fit", "Fachliche Passung"),
            ("participation_requirements", "Teilnahmevoraussetzungen"),
        ):
            value = unit[key]
            layout.paragraph(
                f"<b>{label}: {escape(value['status'])}.</b> "
                + escape(value["reason"])
                + appendix.refs(value)
                + appendix.refs(value.get("verification") or {}),
                markup=True,
            )
        layout.paragraph("Pflichtangaben", "label")
        duration_checks = [
            p
            for p in unit["checkpoints"]
            if p.get("field") == "duration" or p.get("method") == "xml_duration_comparison"
        ]
        comparisons = [
            {e["path"] for e in p["evidence"]}
            for p in duration_checks
            if p.get("method") == "xml_duration_comparison"
        ]
        # Zusätzliche KI-Hinweise zu denselben Vergleichsgrundlagen bleiben im Anhang.
        # Eine identische Belegmenge allein beweist keine sinngleiche Aussage.
        related = [
            p
            for p in unit["checkpoints"]
            if p.get("method") == "ai_verified"
            and {e["path"] for e in p["evidence"]} in comparisons
        ]
        for key, label in LABELS.items():
            if key in CRITERIA_FIELDS:
                add_criteria(layout, appendix, unit, key, label)
                continue
            if key == "tender_validity" and key not in unit["fields"]:
                layout.paragraph(f"{label}: nicht ausgewertet")
                continue
            field = unit["fields"][key]
            state = STATES.get(field["status"], "")
            if key == "deadlines" and field["values"]:
                grouped: dict[str, list[Data]] = {}
                for item in field["values"]:
                    grouped.setdefault(deadline_text(item), []).append(item)
                for line, items in grouped.items():
                    layout.paragraph(escape(line) + appendix.refs(*items), markup=True)
                if field["status"] in {"uncertain", "conflict"} and not any(
                    item.get("status") == field["status"] for item in field["values"]
                ):
                    layout.paragraph(f"{label}: {state}")
                continue
            if key == "buyer" and position and field == first_buyer:
                continue
            if key == "buyer" and not position:
                first_buyer = field
            items = field["values"]
            if key == "place":
                # Ältere Analysen haben die Zusatzbeschreibung als Ortswert übernommen.
                items = [v for v in items if xml_leaf(v) != "cbc:Description"]
                if not items and not state:
                    state = STATES["missing"]
            if key == "submission":
                items = sorted(items, key=lambda v: v.get("method") != "ai_quote_verified")
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
                extension_paths = {e["path"] for v in extension_texts for e in v["evidence"]}
                items = [
                    v
                    for v in items
                    if v not in extension_texts
                    and not (
                        v.get("method") == "ai_quote_verified"
                        and field["status"] != "conflict"
                        and all(e["path"] in extension_paths for e in v["evidence"])
                        and (
                            v.get("kind") == "minimum_service_months"
                            or any(v["value"] in ext["value"] for ext in extension_texts)
                        )
                    )
                ]
            preferred = {
                "subject": {"cbc:Name"},
                "duration": {
                    "cbc:StartDate",
                    "cbc:EndDate",
                    "cbc:DurationMeasure",
                    "cbc:Description",
                    "cbc:DescriptionCode",
                    "cbc:DurationTypeCode",
                },
            }.get(key, set())
            visible = [
                v
                for v in items
                if xml_leaf(v) in preferred
                or (key == "duration" and v.get("method") == "ai_quote_verified")
            ] or items
            if state and (key != "duration" or field["status"] == "conflict"):
                visible = items
            extra = [v for v in items if v not in visible]
            values = []
            for v in visible:
                value = field_value(v)
                if (
                    key == "submission"
                    and field["status"] == "conflict"
                    and xml_leaf(v) == "cbc:SubmissionMethodCode"
                ):
                    value = "Strukturierte Angabe: " + value
                if xml_leaf(v) in {"cbc:EndpointID", "cbc:URI"} and value.startswith(
                    ("https://", "http://")
                ):
                    display = link(value, "Portal öffnen" if key == "submission" else "TED öffnen")
                elif key == "source_link" and value.startswith(("https://", "http://")):
                    display = link(value, f"TED {number}")
                else:
                    display = escape(
                        value
                        if key in {"duration", "tender_validity", "submission"}
                        else excerpt(value, FIELD_PREVIEW_LENGTH)
                    )
                values.append(display + appendix.refs(v))
            if extra:
                anchor = f"feld-{number}-{index}-{key}"
                appendix.criteria_details.append(
                    (anchor, f"{scope} · {label}", appendix.source_ids(extra))
                )
                values.append(f'<a href="#{anchor}" color="#125B62">Details</a>')
            if state or values or not extension_texts:
                layout.paragraph(
                    f"<b>{label}:</b> " + " · ".join(filter(None, [state, *values])),
                    markup=True,
                )
            for item in sorted(
                extension_texts, key=lambda v: xml_leaf(v) == "cbc:OptionsDescription"
            ):
                prefix = (
                    "Optionen und Bedingungen"
                    if xml_leaf(item) == "cbc:OptionsDescription"
                    else "Verlängerung"
                )
                if not (state or values):
                    prefix = f"{label} · {prefix}"
                layout.paragraph(
                    f"<b>{prefix}:</b> "
                    + escape(" ".join(item["value"].split()))
                    + appendix.refs(item),
                    markup=True,
                )
            if key == "duration":
                layout.story.extend(
                    checkpoint_line(layout, appendix, p)
                    for p in duration_checks
                    if p not in related
                )
        entry = unit.get("selection_entry", {})
        history = entry.get("history", [])
        show_history = len(history) > 1 or any(stage.get("duplicate_reason") for stage in history)
        if (
            duration_checks
            and not related
            and not unit["processing_errors"]
            and not unit["rejected_claims"]
            and not entry.get("checkpoints")
            and not show_history
            and all(p in duration_checks for p in unit["checkpoints"])
        ):
            continue
        layout.paragraph("Informationsqualität und Prüfpunkte", "label")
        for point in entry.get("checkpoints", []):
            citations = []
            for origin in point["sources"]:
                pub = escape(origin["publication_number"])
                if "unit_index" in origin:
                    anchor = f"los-{pub}-{origin['unit_index']}"
                    citations.append(f'<a href="analysis.html#{anchor}">TED {pub}</a>')
                else:
                    citations.append(f"TED {pub}")
            layout.paragraph(f"{escape(point['reason'])} ({', '.join(citations)})", markup=True)
        if show_history:
            layout.paragraph("Dokumentstände und Herkunft", "label")
            for stage in history:
                pub, old_index = stage["publication_number"], stage["unit_index"]
                label = "Aktueller Stand" if pub == number else "Früherer Stand"
                old_unit = documents[pub]["units"][old_index]
                source_link = f'<a href="analysis.html#los-{pub}-{old_index}">TED {pub}</a>'
                dates = ", ".join(
                    deadline_text(d)
                    for d in old_unit["fields"]["deadlines"]["values"]
                    if d["kind"] in (*PARTICIPATION_PERIODS, "Einreichungsfrist (Freitext)")
                )
                layout.paragraph(
                    f"{label} · {source_link} · {escape(dates)}", "source", markup=True
                )
                if stage.get("duplicate_reason"):
                    copies = ", ".join(
                        f"TED {n['publication_number']}" for n in stage["ted_occurrences"]
                    )
                    layout.paragraph(stage["duplicate_reason"] + " " + copies, "source")
        for error in unit["processing_errors"]:
            layout.paragraph("Verarbeitungsfehler: " + error)
        for rejected in unit["rejected_claims"]:
            if not any(p.get("claim_id") == rejected["claim_id"] for p in unit["checkpoints"]):
                layout.paragraph("Unbestätigte Aussage: " + rejected["reason"])
        extended = []
        immediate = {}
        summary_failures = {
            r["claim_id"] for r in unit["rejected_claims"] if "summary" in r["claim"]
        }
        diagnostics = []
        for point in unit["checkpoints"]:
            if point in duration_checks or point in related:
                continue
            if point.get("claim_id") in summary_failures:
                diagnostics.append(point)
            elif point.get("method") == "ai_verified":
                extended.append(point)
            elif point.get("method") == "xml_lot_scope":
                immediate.setdefault(point["reason"], []).append(point)
            else:
                layout.story.append(checkpoint_line(layout, appendix, point))
        for reason, group in immediate.items():
            layout.paragraph(escape(reason) + appendix.refs(*group), markup=True)
        if extended:
            critical_paths = {
                e["path"]
                for field in unit["fields"].values()
                if field["status"] in {"conflict", "uncertain"}
                for item in field["values"]
                for e in item.get("evidence", [])
            }
            document_paths = {
                e["path"]
                for item in unit["fields"]["selection_criteria"].get("document_sources", [])
                for e in item["evidence"]
            }
            candidates = [
                p
                for p in extended
                if all(e["path"] not in document_paths for e in p.get("evidence", []))
            ]
            if candidates:
                preview = next(
                    (
                        p
                        for p in candidates
                        if any(e["path"] in critical_paths for e in p.get("evidence", []))
                    ),
                    candidates[0],
                )
                layout.story.append(checkpoint_line(layout, appendix, preview))
                extended.remove(preview)
        remaining = [*related, *diagnostics, *extended]
        if remaining:
            anchor = f"pruefung-{number}-{index}"
            appendix.detail_blocks.append(
                layout.cell(f'<a name="{anchor}"/>{escape(scope)} · Weitere Prüfpunkte', "label")
            )
            appendix.detail_blocks.extend(
                checkpoint_line(layout, appendix, point) for point in remaining
            )
            status = "Kurzfassung der Kriterien nicht bestätigt · " if diagnostics else ""
            layout.paragraph(
                f'{status}<a href="#{anchor}" color="#125B62">'
                f"Weitere Prüfpunkte ({len(remaining)})</a>",
                "source",
                markup=True,
            )
        if not (
            unit["processing_errors"]
            or unit["rejected_claims"]
            or unit["checkpoints"]
            or entry.get("checkpoints")
        ):
            layout.paragraph("Keine zusätzlichen Prüfpunkte erfasst.")
    if doc.get("checkpoints"):
        layout.paragraph("Prüfpunkte zur Bekanntmachung", "heading")
        grouped = {}
        for point in doc["checkpoints"]:
            grouped.setdefault((point.get("url"), point["reason"]), []).append(point)
        for (url, reason), group in grouped.items():
            scopes = list(dict.fromkeys(p.get("lot_id") or "Bekanntmachung" for p in group))
            label = ", ".join(scopes) + " · " if url else ""
            line = escape(label + reason) + appendix.refs(*group)
            if url:
                line += " · " + link(url, "Unterlagen öffnen")
            layout.paragraph(line, markup=True)
    return appendix
