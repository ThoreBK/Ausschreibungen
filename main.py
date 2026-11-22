"""Lokale TED-Recherche mit konfigurierbarem Suchprofil."""

import argparse
import json
import sys
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any

from ausschreibungen.analysis import analyze_run
from ausschreibungen.report import write_report
from ausschreibungen.research import collect, save_json
from ausschreibungen.ted import SearchError, load_profile, search


def print_search_results(
    result: dict[str, Any], language: str, run_dir: Path, output: Path
) -> None:
    for notice in result["notices"]:
        html = (notice["links"] or {}).get("html", {})
        url = html.get(language.upper()) or next(iter(html.values()), None)
        groups = ", ".join(notice["matched_queries"])
        print(f"{notice['publication_number']}: {notice['title'] or '(Titel fehlt)'}")
        print(f"  {groups} · XML: {notice['document']['status']}" + (f" · {url}" if url else ""))
    print(f"Gespeicherte Übersicht: {run_dir / 'overview.html'}")
    if not result["search_incomplete"]:
        print(f"Aktuelle Ergebniskopie: {output}")


def print_report_problems(result: dict[str, Any]) -> None:
    for query in result["queries"]:
        if error := query.get("error"):
            print(f"Abruffehler · {query['name']}: {error}", file=sys.stderr)
    for notice in result["notices"]:
        number = notice["publication_number"]
        document = notice["document"]
        if document["status"] == "error":
            print(f"TED {number}: {document['error']}", file=sys.stderr)
        elif document["status"] == "unavailable":
            print(f"TED {number}: XML-Downloadlink fehlt.", file=sys.stderr)
        if notice["conflicts"]:
            print(
                f"TED {number}: Abweichende Suchangaben ({', '.join(notice['conflicts'])}).",
                file=sys.stderr,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender Research Agent: TED-Suche")
    parser.add_argument("--config", type=Path, default=Path("search-profile.toml"))
    parser.add_argument("--output", type=Path, default=Path("reports/ted-results.json"))
    parser.add_argument("--as-of", type=date.fromisoformat, help="Stichtag YYYY-MM-DD")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--search", action="store_true", help="Live-Suche starten")
    actions.add_argument("--report", action="store_true", help="Live suchen und PDF erstellen")
    actions.add_argument("--analyze", type=Path, help="Gespeicherten Laufordner auswerten")
    parser.add_argument("--analysis-config", type=Path, default=Path("analysis-profile.toml"))
    parser.add_argument("--notice", help="Nur diese Veröffentlichungsnummer auswerten")
    parser.add_argument("--structured-only", action="store_true", help="Nur XML-Fakten, ohne KI")
    args = parser.parse_args()
    if args.notice and args.report:
        parser.error("--notice gilt für --analyze. Für --report report_limit im Profil wählen.")
    if args.analyze:
        try:
            directory = analyze_run(
                args.analyze,
                args.analysis_config,
                number=args.notice,
                structured_only=args.structured_only,
            )
            status = json.loads((directory / "analysis.json").read_text("utf-8"))["status"]
        except (ValueError, OSError, KeyError) as error:
            print(f"Fehler: {error}", file=sys.stderr)
            return 1
        print(f"Auswertung: {directory / 'analysis.html'}")
        print(f"Ergebnisdaten: {directory / 'analysis.json'}")
        print(f"Analysestatus: {status}")
        return 0 if status == "complete" else 1
    if not (args.search or args.report):
        parser.print_help()
        return 0
    try:
        profile = load_profile(args.config)
        if args.report:
            print("Suche auf TED und lade Bekanntmachungen …", flush=True)
        result, run_dir = collect(
            profile,
            args.config.read_bytes(),
            args.output.parent / "runs",
            today=args.as_of,
            search_fn=partial(search, all_returned=True) if args.report else search,
        )
        if not result["search_incomplete"]:
            save_json(args.output, result)
    except (ValueError, OSError, SearchError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    count = len(result["notices"])
    print(f"{count} {'Bekanntmachung' if count == 1 else 'Bekanntmachungen'} gefunden.")
    if result["limited"]:
        print("Trefferlimit erreicht: Ausgabe ist eine begrenzte Auswahl.")
    print(f"Laufstatus: {result['status']}")
    if args.search:
        print_search_results(result, profile.language, run_dir, args.output)
        if result["search_incomplete"] or any(
            n["document"]["status"] == "error" for n in result["notices"]
        ):
            print("Abruffehler: Details stehen in der Laufübersicht.", file=sys.stderr)
    elif result["status"] == "incomplete":
        print_report_problems(result)
        print(f"Details zur Recherche: {run_dir / 'overview.html'}", file=sys.stderr)
    failed = result["status"] not in {"complete", "empty"}
    if args.report:
        try:
            analysis = None
            destination = run_dir
            if result["notices"]:
                print("Werte die Bekanntmachungen aus …", flush=True)
                destination = analyze_run(
                    run_dir, args.analysis_config, structured_only=args.structured_only
                )
                analysis = json.loads((destination / "analysis.json").read_text("utf-8"))
                if analysis["status"] != "complete":
                    print("Auswertung unvollständig. Offene Punkte stehen im PDF.", file=sys.stderr)
            print("Erstelle den PDF-Bericht …", flush=True)
            pdf = write_report(result, analysis, destination)
            print(f"PDF-Bericht: {pdf}")
            failed = failed or (analysis is not None and analysis["status"] != "complete")
        except (ValueError, OSError, KeyError) as error:
            print(f"Berichtsfehler: {error}", file=sys.stderr)
            return 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
