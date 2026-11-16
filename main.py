"""Lokale TED-Recherche mit konfigurierbarem Suchprofil."""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from ted import SearchError, load_profile, search


def main() -> int:
    parser = argparse.ArgumentParser(description="Tender Research Agent: TED-Suche")
    parser.add_argument("--config", type=Path, default=Path("search-profile.toml"))
    parser.add_argument("--output", type=Path, default=Path("reports/ted-results.json"))
    parser.add_argument("--as-of", type=date.fromisoformat, help="Stichtag YYYY-MM-DD")
    parser.add_argument("--search", action="store_true", help="Live-Suche starten")
    args = parser.parse_args()
    if not args.search:
        parser.print_help()
        return 0
    try:
        profile = load_profile(args.config)
        result = search(profile, today=args.as_of)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(args.output)
    except (ValueError, OSError, SearchError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    print(f"Tender Research Agent: {len(result['notices'])} Bekanntmachungen")
    for notice in result["notices"]:
        print(f"{notice['publication_number']}: {notice['title'] or '(Titel fehlt)'}")
        print(f"  Suchgruppen: {', '.join(notice['matched_queries'])}")
        links = notice["links"] or {}
        html = links.get("html", {})
        link = html.get(profile.language.upper()) or next(iter(html.values()), None)
        if link:
            print(f"  {link}")
    if result["limited"]:
        print("Trefferlimit erreicht: Ausgabe ist eine begrenzte Auswahl.")
    print("Treffer sind Kandidaten; fachliche Eignung und Angebotsfristen sind zu prüfen.")
    print(f"Ergebnisse und Rohantworten: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
