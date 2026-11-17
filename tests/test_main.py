"""Programmeinstieg und Ausgabe mit kontrollierten Antworten ohne Netzwerk."""

import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from urllib.request import Request

import pytest

import main
from ted import SearchError


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
    assert "Tender Research Agent" in result.stdout
    assert result.stderr == ""


def test_failed_search_preserves_previous_output(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "results.json"
    output.write_text("previous result", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["main.py", "--search", "--config", str(profile_path), "--output", str(output)]
    )

    def fail(*args: object, **kwargs: object) -> None:
        raise SearchError("offline")

    monkeypatch.setattr(main, "search", fail)
    assert main.main() == 1
    assert "offline" in capsys.readouterr().err
    assert output.read_text("utf-8") == "previous result"


def test_successful_search_writes_results_and_displays_notices(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "reports" / "results.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "--search",
            "--config",
            str(profile_path),
            "--output",
            str(output),
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

    monkeypatch.setattr("ted.urlopen", respond)
    assert main.main() == 0
    result = json.loads(output.read_text("utf-8"))
    assert result["as_of"] == "2026-11-15"
    assert result["profile"]["name"] == "Testprofil"
    assert result["limited"] is False
    assert len(result["notices"]) == 1
    notice = result["notices"][0]
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
    assert "1 Bekanntmachungen" in captured.out
    assert "123-2026: Schulung für KI-Assistenten" in captured.out
    assert "https://example.org/bekanntmachung/123" in captured.out
    assert "KI-Beratung, Schulungen" in captured.out
    assert "Trefferlimit erreicht" not in captured.out
    assert str(output) in captured.out


def test_analyze_relative_run_path_saves_inspectable_incomplete_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tests.test_analysis import PROFILE, lot, saved_run, xml

    saved_run(tmp_path, xml(lot()))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "--analyze", ".", "--analysis-config", str(PROFILE), "--structured-only"],
    )
    assert main.main() == 1
    files = list((tmp_path / "analyses").glob("*/analysis.json"))
    assert len(files) == 1
    result = json.loads(files[0].read_text("utf-8"))
    doc = result["documents"][0]
    assert doc["status"] == "incomplete"
    assert doc["provenance"]["original_file"] == "documents/100-2026.xml"
    assert "error" not in doc
    output = capsys.readouterr()
    assert "Analysestatus: incomplete" in output.out
    assert output.err == ""
