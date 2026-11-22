"""Lokale TED-Recherche mit konfigurierbarem Suchprofil."""

import argparse
import json
import sys
from collections.abc import Callable
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any

from ausschreibungen.analysis import analyze_run
from ausschreibungen.report import write_report
from ausschreibungen.research import collect, save_json
from ausschreibungen.ted import Profile, SearchError, load_profile, search


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


def report_problems(result: dict[str, Any], warn: Callable[[str], None]) -> None:
    for query in result["queries"]:
        if error := query.get("error"):
            warn(f"Abruffehler · {query['name']}: {error}")
    for notice in result["notices"]:
        number = notice["publication_number"]
        document = notice["document"]
        if document["status"] == "error":
            warn(f"TED {number}: {document['error']}")
        elif document["status"] == "unavailable":
            warn(f"TED {number}: XML-Downloadlink fehlt.")
        if notice["conflicts"]:
            warn(f"TED {number}: Abweichende Suchangaben ({', '.join(notice['conflicts'])}).")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tender Research Agent: TED-Ausschreibungen")
    commands = parser.add_subparsers(dest="command", title="Befehle")
    report = commands.add_parser("report", help="Auf TED suchen und einen PDF-Bericht erstellen.")
    search_command = commands.add_parser(
        "search", help="Auf TED suchen und die Originale speichern."
    )
    analyze = commands.add_parser("analyze", help="Einen gespeicherten Lauf erneut auswerten.")
    analyze.add_argument(
        "--notice", metavar="NUMMER", help="Nur diese TED-Bekanntmachung auswerten."
    )

    for command in (report, search_command):
        command.add_argument(
            "--config",
            type=Path,
            default=Path("search-profile.toml"),
            metavar="DATEI",
            help="Suchprofil (Standard: search-profile.toml).",
        )
        command.add_argument(
            "--as-of",
            type=date.fromisoformat,
            metavar="YYYY-MM-DD",
            help="Stichtag für die TED-Suche (Standard: heute).",
        )
        output = command.add_mutually_exclusive_group()
        output.add_argument(
            "--output-dir",
            type=Path,
            default=Path("reports"),
            metavar="ORDNER",
            help="Ziel für die Laufarchive und ted-results.json (Standard: reports).",
        )
        output.add_argument("--output", type=Path, help=argparse.SUPPRESS)

    for command in (report, analyze):
        command.add_argument(
            "--analysis-config",
            type=Path,
            default=Path("analysis-profile.toml"),
            metavar="DATEI",
            help="Analyseprofil (Standard: analysis-profile.toml).",
        )
        command.add_argument(
            "--structured-only",
            action="store_true",
            help="Nur strukturierte XML-Angaben auswerten, ohne KI.",
        )

    # Alte Aufrufe erlauben Optionen vor dem Aktionsflag. Der zuständige Parser
    # liest sie in Originalreihenfolge und prüft auch fehlende Optionswerte.
    aliases = {"--search": search_command, "--report": report, "--analyze": analyze}
    if argv and argv[0].startswith("-"):
        for arg in argv:
            flag = arg.partition("=")[0]
            if arg == "--":
                break
            if flag in aliases:
                selected = aliases[flag]
                if selected is analyze:
                    selected.add_argument(
                        flag,
                        dest="run_dir",
                        type=Path,
                        metavar="LAUFORDNER",
                        required=True,
                        help="Ordner mit results.json.",
                    )
                else:
                    selected.add_argument(
                        flag, action="store_true", required=True, help=argparse.SUPPRESS
                    )
                selected.set_defaults(command=flag[2:])
                return selected.parse_args(argv)

    analyze.add_argument(
        "run_dir", type=Path, metavar="LAUFORDNER", help="Ordner mit results.json."
    )
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return args


def main() -> int:
    args = parse_args(sys.argv[1:])
    if args.command is None:
        return 0
    if args.command == "analyze":
        try:
            directory = analyze_run(
                args.run_dir,
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
    output_file = args.output or args.output_dir / "ted-results.json"
    try:
        if args.command == "report":
            pdf, failed = generate_report(
                args.config,
                args.analysis_config,
                output_file,
                partial(print, flush=True),
                partial(print, file=sys.stderr),
                as_of=args.as_of,
                structured_only=args.structured_only,
            )
            print(f"PDF-Bericht: {pdf}")
            return int(failed)
        profile, result, run_dir = research(args.config, output_file, args.as_of, report=False)
    except (ValueError, OSError, SearchError, KeyError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        return 1
    describe_result(result, print)
    print_search_results(result, profile.language, run_dir, output_file)
    if result["search_incomplete"] or any(
        n["document"]["status"] == "error" for n in result["notices"]
    ):
        print("Abruffehler: Details stehen in der Laufübersicht.", file=sys.stderr)
    return int(result["status"] not in {"complete", "empty"})


def research(
    config: Path, output: Path, as_of: date | None, *, report: bool
) -> tuple[Profile, dict[str, Any], Path]:
    profile = load_profile(config)
    result, run_dir = collect(
        profile,
        config.read_bytes(),
        output.parent / "runs",
        today=as_of,
        search_fn=partial(search, all_returned=True) if report else search,
    )
    if not result["search_incomplete"]:
        save_json(output, result)
    return profile, result, run_dir


def describe_result(result: dict[str, Any], progress: Callable[[str], None]) -> None:
    count = len(result["notices"])
    progress(f"{count} {'Bekanntmachung' if count == 1 else 'Bekanntmachungen'} gefunden.")
    if result["limited"]:
        progress("Trefferlimit erreicht: Ausgabe ist eine begrenzte Auswahl.")
    progress(f"Laufstatus: {result['status']}")


def generate_report(
    config: Path,
    analysis_config: Path,
    output_file: Path,
    progress: Callable[[str], None],
    warn: Callable[[str], None],
    *,
    as_of: date | None = None,
    structured_only: bool = False,
    on_analysis_progress: Callable[[int, int], None] | None = None,
) -> tuple[Path, bool]:
    progress("Suche auf TED und lade Bekanntmachungen …")
    _, result, run_dir = research(config, output_file, as_of, report=True)
    describe_result(result, progress)
    if result["status"] == "incomplete":
        report_problems(result, warn)
        warn(f"Details zur Recherche: {run_dir / 'overview.html'}")
    failed = result["status"] not in {"complete", "empty"}
    analysis = None
    destination = run_dir
    if result["notices"]:
        progress("Werte die Bekanntmachungen aus …")
        destination = analyze_run(
            run_dir,
            analysis_config,
            structured_only=structured_only,
            on_progress=on_analysis_progress,
        )
        analysis = json.loads((destination / "analysis.json").read_text("utf-8"))
        if analysis["status"] != "complete":
            warn("Auswertung unvollständig. Offene Punkte stehen im PDF.")
            failed = True
    progress("Erstelle den PDF-Bericht …")
    return write_report(result, analysis, destination), failed


if __name__ == "__main__":
    raise SystemExit(main())
