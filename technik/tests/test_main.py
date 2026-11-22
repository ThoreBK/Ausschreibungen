"""Programmeinstieg und Ausgabe mit kontrollierten Antworten ohne Netzwerk."""

import json
import subprocess
import sys
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest

import main
from ausschreibungen.ted import SearchError, search
from tests.support.research import Network, response, row, xml


def test_entrypoint() -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(project_root / "main.py")],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert all(command in result.stdout for command in ("report", "search", "analyze"))
    assert "--output-dir" not in result.stdout
    assert "Tender Research Agent" in result.stdout
    assert result.stderr == ""


def test_cli_keeps_existing_reports_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "reports"
    archive.mkdir()
    monkeypatch.setattr(main, "PROJECT_DIR", tmp_path)
    assert main.parse_args(["report"]).output_dir == archive
    assert main.parse_args(["search"]).output_dir == archive


@pytest.mark.parametrize(
    ("command", "shown", "hidden"),
    [
        (
            "search",
            ["--config", "--as-of", "--output-dir"],
            ["--structured-only", "--notice", "--analysis-config"],
        ),
        ("report", ["--output-dir", "--structured-only", "--analysis-config"], ["--notice"]),
        (
            "analyze",
            ["LAUFORDNER", "--notice", "--structured-only"],
            ["--as-of", "--output-dir", "--config"],
        ),
    ],
)
def test_help_lists_options_for_the_selected_command(
    command: str, shown: list[str], hidden: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as stopped:
        main.parse_args([command, "--help"])
    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    assert all(option in help_text for option in shown)
    assert all(option not in help_text for option in hidden)


@pytest.mark.parametrize(
    "argv",
    [
        ["search", "--notice", "123-2026"],
        ["--search", "--structured-only"],
        ["report", "--notice", "123-2026"],
        ["analyze", ".", "--as-of", "2026-11-15"],
        ["analyze"],
        ["--search", "--report"],
        ["--config", "--report", "profil.toml"],
        ["report", "--output-dir", "archiv", "--output", "kopie.json"],
    ],
)
def test_invalid_command_combinations_fail_during_parsing(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        main.parse_args(argv)
    assert stopped.value.code == 2


def test_failed_search_preserves_previous_output(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "results.json"
    output.write_text("previous result", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--config", str(profile_path), "--output", str(output), "--search"]
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise SearchError("offline")

    monkeypatch.setattr(main, "search", fail)
    assert main.main() == 1
    assert "offline" in capsys.readouterr().err
    assert output.read_text("utf-8") == "previous result"


def test_search_without_xml_link_returns_one_and_preserves_notice(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "Meine Recherche"
    output = output_dir / "ted-results.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "search",
            "--config",
            str(profile_path),
            "--output-dir",
            str(output_dir),
            "--as-of",
            "2026-11-15",
        ],
    )
    # Synthetischer Treffer; nur die Netzwerkgrenze wird ersetzt.
    response = {
        "notices": [
            {
                "publication-number": "123-2026",
                "notice-title": {"deu": "Schulung für KI-Assistenten"},
                "buyer-name": {"deu": ["Test-Auftraggeber"]},
                "publication-date": "2026-11-13+01:00",
                "links": {"html": {"DEU": "https://example.org/bekanntmachung/123"}},
            }
        ],
        "totalNoticeCount": 1,
    }
    requests: list[Request] = []

    def respond(request: Request, *, timeout: int) -> BytesIO:
        requests.append(request)
        return BytesIO(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    monkeypatch.setattr("ausschreibungen.ted.urlopen", respond)
    assert main.main() == 1
    result = json.loads(output.read_text("utf-8"))
    assert result["status"] == "incomplete"
    run_dir = Path(result["run_directory"])
    assert run_dir.parent == output_dir / "runs"
    assert (run_dir / "results.json").is_file()
    assert result["as_of"] == "2026-11-15"
    assert result["profile"]["name"] == "Testprofil"
    assert result["limited"] is False
    assert len(result["notices"]) == 1
    notice = result["notices"][0]
    assert notice["document"]["status"] == "unavailable"
    assert notice["publication_number"] == "123-2026"
    assert notice["title"] == "Schulung für KI-Assistenten"
    assert notice["buyer"] == ["Test-Auftraggeber"]
    assert notice["matched_queries"] == ["KI-Beratung", "Schulungen"]
    assert [run["response"] for run in result["queries"]] == [response, response]
    assert len(requests) == 2
    for request in requests:
        assert request.data is not None
        sent = json.loads(request.data)
        assert "buyer-name" in sent["fields"]
        assert "publication-date <= 20261115" in sent["query"]
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "1 Bekanntmachung gefunden." in captured.out
    assert "123-2026: Schulung für KI-Assistenten" in captured.out
    assert "https://example.org/bekanntmachung/123" in captured.out
    assert "KI-Beratung, Schulungen" in captured.out
    assert "Trefferlimit erreicht" not in captured.out
    assert str(output) in captured.out


@pytest.mark.parametrize(
    ("responses", "expected_status", "expected_code", "expected_conflicts"),
    [
        pytest.param(
            [response(row(100, 15)), response()], "complete", 0, [[]], id="complete-original"
        ),
        pytest.param([response(), response()], "empty", 0, [], id="empty-search"),
        pytest.param(
            [response(row(100, 15)), response(row(100, 15, "Abweichender Titel"))],
            "incomplete",
            1,
            [["notice-title"]],
            id="conflicting-titles",
        ),
    ],
)
def test_search_exit_code_with_successful_downloads(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    responses: list[dict[str, Any]],
    expected_status: str,
    expected_code: int,
    expected_conflicts: list[list[str]],
) -> None:
    monkeypatch.setattr(main, "PROJECT_DIR", tmp_path)
    output = tmp_path / "Berichte" / "ted-results.json"
    network = Network(responses, {"https://ted.europa.eu/en/notice/100-2026/xml": xml()})
    monkeypatch.setattr(main, "search", partial(search, transport=network.search))
    monkeypatch.setattr(main, "collect", partial(main.collect, download=network.download))
    monkeypatch.setattr(sys, "argv", ["main.py", "search", "--config", str(profile_path)])

    exit_code = main.main()
    result = json.loads(output.read_text("utf-8"))
    assert Path(result["run_directory"]).parent == tmp_path / "Berichte" / "runs"
    assert result["status"] == expected_status
    assert [notice["conflicts"] for notice in result["notices"]] == expected_conflicts
    assert all(notice["document"]["status"] == "ok" for notice in result["notices"])
    assert exit_code == expected_code


@pytest.mark.parametrize("action", [["analyze", "."], ["--analyze", "."], ["--analyze=."]])
def test_analyze_relative_run_path_saves_inspectable_incomplete_result(
    action: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tests.support.notices import PROFILE, lot, saved_run, xml

    saved_run(tmp_path, xml(lot()))
    saved = tmp_path / "results.json"
    research = json.loads(saved.read_bytes())
    research["notices"].append(
        {"publication_number": "200-2026", "document": {"status": "unavailable"}}
    )
    saved.write_text(json.dumps(research), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            *action,
            "--analysis-config",
            str(PROFILE),
            "--structured-only",
            "--notice",
            "100-2026",
        ],
    )
    assert main.main() == 1
    files = list((tmp_path / "analyses").glob("*/analysis.json"))
    assert len(files) == 1
    result = json.loads(files[0].read_text("utf-8"))
    [doc] = result["documents"]
    assert doc["publication_number"] == "100-2026"
    assert doc["status"] == "incomplete"
    assert doc["provenance"]["original_file"] == "documents/100-2026.xml"
    assert "error" not in doc
    output = capsys.readouterr()
    assert "Analysestatus: incomplete" in output.out
    assert output.err == ""
