"""Lokale TED-Recherche mit konfigurierbarem Suchprofil."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from analysis import analyze_run
from research import collect, save_json
from ted import SearchError, load_profile, search


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender Research Agent: TED-Suche")
    parser.add_argument("--config", type=Path, default=Path("search-profile.toml"))
    parser.add_argument("--output", type=Path, default=Path("reports/ted-results.json"))
    parser.add_argument("--as-of", type=date.fromisoformat, help="Stichtag YYYY-MM-DD")
    parser.add_argument("--search", action="store_true", help="Live-Suche starten")
    parser.add_argument("--analyze", type=Path, help="Gespeicherten Laufordner auswerten")
    parser.add_argument("--analysis-config", type=Path, default=Path("analysis-profile.toml"))
    parser.add_argument("--notice", help="Nur diese Veröffentlichungsnummer auswerten")
    parser.add_argument("--structured-only", action="store_true", help="Nur XML-Fakten, ohne KI")
    args = parser.parse_args()
    if args.analyze:
        if args.search:
            parser.error("--search und --analyze bitte getrennt starten.")
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
    if not args.search:
        parser.print_help()
        return 0
    try:
        profile = load_profile(args.config)
        result, run_dir = collect(
            profile,
            args.config.read_bytes(),
            args.output.parent / "runs",
            today=args.as_of,
            search_fn=search,
        )
        if not result["search_incomplete"]:
            save_json(args.output, result)
    except (ValueError, OSError, SearchError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    print(f"Tender Research Agent: {len(result['notices'])} Bekanntmachungen")
    for notice in result["notices"]:
        print(f"{notice['publication_number']}: {notice['title'] or '(Titel fehlt)'}")
        print(f"  Suchgruppen: {', '.join(notice['matched_queries'])}")
        print(f"  Bekanntmachungsabruf: {notice['document']['status']}")
        links = notice["links"] or {}
        html = links.get("html", {})
        link = html.get(profile.language.upper()) or next(iter(html.values()), None)
        if link:
            print(f"  {link}")
    if result["limited"]:
        print("Trefferlimit erreicht: Ausgabe ist eine begrenzte Auswahl.")
    print("Treffer sind Kandidaten; fachliche Eignung und Angebotsfristen sind zu prüfen.")
    print(f"Laufstatus: {result['status']}")
    print(f"Gespeicherte Übersicht: {run_dir / 'overview.html'}")
    print(f"Ergebnisse und Rohantworten des Laufs: {run_dir / 'results.json'}")
    if not result["search_incomplete"]:
        print(f"Aktuelle Ergebniskopie: {args.output}")
    failed = result["search_incomplete"] or any(
        notice["document"]["status"] == "error" for notice in result["notices"]
    )
    if failed:
        print(
            "Abruffehler: Details und erhaltene Daten stehen in der Laufübersicht.", file=sys.stderr
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
