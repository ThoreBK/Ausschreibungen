"""Läufe lokal archivieren und ohne erneuten Netzabruf lesbar machen."""

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, date, datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from ausschreibungen.notices import Download, download_document, html_page, inspect_document
from ausschreibungen.ted import ENDPOINT, Profile, SearchError, search


def save_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def text_value(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "nicht angegeben"
    if isinstance(value, list):
        return "; ".join(map(str, value))
    return str(value)


def link(url: str, label: str) -> str:
    # Externe Dokumentinhalte dürfen weder Skripte noch lokale Datei-URLs einschleusen.
    try:
        public = urlsplit(url).scheme in {"https", "http"}
    except ValueError:
        public = False
    if not public:
        return escape(url) + " (kein öffentlicher HTTP-Link)"
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def overview(result: dict[str, Any]) -> str:
    profile = result["profile"]
    state = {
        "running": "Lauf noch nicht abgeschlossen",
        "complete": "Abrufe abgeschlossen",
        "empty": "Suche erfolgreich: keine Treffer",
        "incomplete": "Lauf unvollständig / offene Prüfpunkte",
        "failed": "Lauf fehlgeschlagen",
        "interrupted": "Lauf unterbrochen",
    }[result["status"]]
    body = [
        "<h1>TED-Recherche: gespeicherter Lauf</h1>",
        f'<p class="warning"><strong>{state}</strong></p>',
        f"<p>Lauf: {escape(result['run_id'])}<br>"
        f"Gestartet: {escape(result['started_at'])}<br>"
        f"Beendet: {escape(text_value(result.get('finished_at')))}</p>",
        "<p>Treffer sind Kandidaten. Fachliche Eignung und offene Teilnahme sind ungeprüft. "
        "Zusätzliche Vergabeunterlagen werden in dieser Version nicht abgerufen und nicht "
        "ausgewertet. Grundlage sind die erfolgreich gespeicherten Bekanntmachungen.</p>",
        f"<h2>Suchprofil: {escape(profile['name'])}</h2>",
        '<p><a href="profile.toml">Originales Suchprofil</a> · '
        '<a href="results.json">Ergebnisdaten mit Suchanfragen und Rohantworten</a></p>',
        f"<p>Stichtag: {escape(result['as_of'])}; Zeitraum: {profile['days_back']} Kalendertage "
        f"einschließlich Stichtag; Länder: {escape(text_value(profile['countries']))}; "
        f"Länderfeld: {escape(profile['country_field'])}; Suchbereich: {escape(profile['scope'])}; "
        f"Trefferlimit: {profile['max_results']} je Suchgruppe und insgesamt. "
        "Nur neueste Versionen laut TED-Suchanfrage; kein vollständiges Verfahrensarchiv.</p>",
        "<details><summary>Alle verwendeten Einstellungen</summary><pre>"
        + escape(json.dumps(profile, ensure_ascii=False, indent=2))
        + "</pre></details>",
    ]
    if result.get("error"):
        body.append(f'<p class="warning">{escape(result["error"])}</p>')
    if result.get("limited"):
        body.append('<p class="warning">Trefferlimit erreicht: begrenzte Auswahl.</p>')
    body.append("<h2>Suchgruppen</h2>")
    for query in result.get("queries", []):
        body.append(
            f"<p><strong>{escape(query['name'])}</strong>: "
            + (
                "Abruffehler: " + escape(query["error"])
                if query["status"] == "error"
                else (
                    f"{query['returned']} geliefert / {query['total']} laut TED"
                    if query["status"] == "ok"
                    else "Suchanfrage noch nicht abgeschlossen"
                )
            )
            + "</p>"
        )
    body.append(f"<h2>Kandidaten ({len(result.get('notices', []))})</h2>")
    for notice in result.get("notices", []):
        number = notice["publication_number"]
        document = notice.get("document", {"status": "pending"})
        statuses = {
            "pending": "Abruf noch nicht abgeschlossen",
            "ok": "Bekanntmachung gespeichert und Veröffentlichungsnummer geprüft",
            "error": "Abruffehler / Dokumentprüfung fehlgeschlagen",
            "unavailable": "XML-Downloadlink nicht angegeben",
        }
        body.extend(
            [
                f"<article><h3>{escape(number)} — {escape(text_value(notice['title']))}</h3>",
                f"<p>Auftraggeber: {escape(text_value(notice['buyer']))}<br>"
                f"Veröffentlichung: {escape(text_value(notice['publication_date']))}<br>"
                f"Bekanntmachungsart: {escape(text_value(notice['notice_type']))}<br>"
                f"Suchgruppen: {escape(', '.join(notice['matched_queries']))}</p>",
                "<p>Quelle: "
                + link(f"https://ted.europa.eu/de/notice/-/detail/{number}", "TED")
                + f"<br>Abrufstatus: {statuses[document['status']]}<br>"
                + f"Abrufzeit: {escape(text_value(document.get('retrieved_at')))}</p>",
            ]
        )
        if document.get("error"):
            body.append(f'<p class="warning">{escape(document["error"])}</p>')
        if notice["conflicts"]:
            body.append(
                '<p class="warning">Ungeklärte abweichende Suchangaben: '
                + escape(", ".join(notice["conflicts"]))
                + ". Alle Varianten stehen in den Ergebnisdaten.</p>"
            )
        if document["status"] == "ok":
            body.append(
                f'<p><a href="{document["file"]}">Original-XML</a> · '
                f'<a href="{document["reading_copy"]}">Bekanntmachung lokal lesen</a></p>'
            )
            hints = document["metadata"]
            for label, key in (
                ("Bekanntmachungskennung", "notice_ids"),
                ("Verfahrenskennung", "procedure_ids"),
                ("Version", "versions"),
                ("Lose", "lot_ids"),
            ):
                body.append(f"<p>{label}: {escape(text_value(hints[key]))}</p>")
            references = hints["additional_documents"]
            if not references:
                body.append(
                    "<p>Kein Unterlagenlink angegeben (strukturierte eForms-Verweise). "
                    "Weitere Verweise im Freitext bleiben im Original erhalten.</p>"
                )
            for reference in references:
                body.append(
                    "<p>Zusätzliche Unterlagen — Los: "
                    + escape(text_value(reference["lot_id"]))
                    + ": "
                    + link(reference["url"], reference["url"])
                    + " — verlinkt, nicht abgerufen und nicht ausgewertet.</p>"
                )
        else:
            body.append(
                "<p>Unterlagenlinks ungeklärt: Bekanntmachung nicht erfolgreich geprüft.</p>"
            )
        body.append("</article>")
    body.append(
        "<p><small>Quelle: TED, Amt für Veröffentlichungen der Europäischen Union. "
        "Originaldateien unverändert; Übersicht und Lesekopien lokal erzeugt. "
        + link("https://ted.europa.eu/en/legal-notice", "Nutzungshinweise")
        + "</small></p>"
    )
    return html_page("TED-Recherche — " + result["run_id"], "".join(body))


def collect(
    profile: Profile,
    config_bytes: bytes,
    directory: Path,
    *,
    today: date | None = None,
    search_fn: Callable[..., dict[str, Any]] = search,
    download: Callable[[str, int], Download] = download_document,
) -> tuple[dict[str, Any], Path]:
    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    run_dir = directory / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "profile.toml").write_bytes(config_bytes)
    (run_dir / "documents").mkdir()
    result: dict[str, Any] = {
        "run_id": run_id,
        "run_directory": str(run_dir.resolve()),
        "started_at": now.isoformat(),
        "status": "running",
        "stage": "search",
        "source": "TED",
        "endpoint": ENDPOINT,
        "profile": asdict(profile),
        "as_of": (today or date.today()).isoformat(),
        "queries": [],
        "notices": [],
    }

    def save() -> None:
        save_json(run_dir / "results.json", result)
        temporary = run_dir / "overview.tmp"
        temporary.write_text(overview(result), encoding="utf-8")
        temporary.replace(run_dir / "overview.html")

    def progress(snapshot: dict[str, Any]) -> None:
        result.update(snapshot)
        save()

    save()
    try:
        progress(search_fn(profile, today=today, continue_on_error=True, on_progress=progress))
        result["stage"] = "documents"
        for notice in result["notices"]:
            number = notice["publication_number"]
            expected_url = f"https://ted.europa.eu/en/notice/{number}/xml"
            # Nur explizite XML-Links abrufen. Fremde Unterlagenlinks bleiben reine Daten.
            urls = []
            for occurrence in notice["occurrences"]:
                links = occurrence["raw"].get("links") or {}
                xml_links = links.get("xml", {}) if isinstance(links, dict) else {}
                if isinstance(xml_links, dict):
                    urls.extend(value for value in xml_links.values() if isinstance(value, str))
            doc: dict[str, Any] = {
                "status": "unavailable",
                "attempted_at": datetime.now(UTC).isoformat(),
            }
            notice["document"] = doc
            if not urls:
                save()
                continue
            doc["status"] = "pending"
            doc["source_url"] = expected_url
            try:
                if expected_url not in urls:
                    raise SearchError(
                        "XML-Link weicht von der erwarteten öffentlichen TED-Adresse ab."
                    )
                retrieved = download(expected_url, profile.timeout_seconds)
                doc.update(
                    final_url=retrieved.final_url,
                    content_type=retrieved.content_type,
                    retrieved_at=retrieved.retrieved_at,
                    sha256=hashlib.sha256(retrieved.content).hexdigest(),
                    size_bytes=len(retrieved.content),
                )
                # Auch unbrauchbare Antworten als Beleg behalten, niemals als gültiges XML ausgeben.
                payload = run_dir / "documents" / f"{number}.response"
                payload.write_bytes(retrieved.content)
                doc["response_file"] = payload.relative_to(run_dir).as_posix()
                metadata, reading = inspect_document(retrieved.content, number)
                original = payload.with_suffix(".xml")
                payload.replace(original)
                doc.pop("response_file")
                doc.update(file=original.relative_to(run_dir).as_posix(), metadata=metadata)
                reading_path = original.with_suffix(".html")
                reading_path.write_text(
                    html_page(
                        "Bekanntmachung " + number,
                        f"<h1>Bekanntmachung {number}</h1>"
                        '<p><a href="../overview.html">Zur Laufübersicht</a> · '
                        f'<a href="{number}.xml">Unverändertes Original-XML</a></p>'
                        "<p>Lesekopie aller XML-Textwerte in Originalreihenfolge mit Fundstellen. "
                        "Keine fachliche Auswertung. Attribute und vollständige Struktur stehen im "
                        "Original. Quelle: TED, Amt für Veröffentlichungen "
                        "der Europäischen Union.</p>" + reading,
                    ),
                    encoding="utf-8",
                )
                doc["reading_copy"] = reading_path.relative_to(run_dir).as_posix()
                doc["status"] = "ok"
            except (SearchError, ValueError) as error:
                doc.update(status="error", error=str(error))
            save()
        incomplete = result["search_incomplete"] or any(
            notice["document"]["status"] != "ok" or notice["conflicts"]
            for notice in result["notices"]
        )
        result["status"] = (
            "incomplete" if incomplete else ("complete" if result["notices"] else "empty")
        )
        result["stage"] = "finished"
    except (SearchError, OSError) as error:
        result.update(status="failed", error=str(error))
        raise
    except KeyboardInterrupt:
        result["status"] = "interrupted"
        raise
    finally:
        result["finished_at"] = datetime.now(UTC).isoformat()
        save()
    return result, run_dir
