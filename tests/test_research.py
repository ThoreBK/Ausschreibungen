"""T2-01 bis T2-09: Recherche mit kontrollierten Netzwerkantworten und HTTP-Abbrüchen."""

import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from datetime import datetime
from html.parser import HTMLParser
from http.client import HTTPResponse
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest

import main
from ausschreibungen.notices import inspect_document
from ausschreibungen.ted import Profile, SearchError, load_profile
from tests.support.notices import FIXTURES
from tests.support.research import RETRIEVED, Network, execute, response, row, xml


def test_t2_01_changed_config_is_sent_and_archived(tmp_path: Path, profile_path: Path) -> None:
    source = profile_path.read_text("utf-8")
    changed = (
        source.replace('countries = ["DEU"]', 'countries = ["AUT"]')
        .replace("days_back = 90", "days_back = 7")
        .replace('term_groups = [["Copilot"], ["Schulung"]]', 'term_groups = [["Power Automate"]]')
    )
    config = tmp_path / "changed.toml"
    config.write_text(changed, encoding="utf-8")
    network = Network([response(), response()], {})
    result, directory = execute(tmp_path, load_profile(config), network, config.read_bytes())
    assert network.search_requests[1]["query"] == (
        "publication-date >= 20261110 AND publication-date <= 20261116 "
        "AND form-type != result "
        'AND buyer-country IN (AUT) AND (FT ~ "Power Automate") SORT BY publication-date DESC'
    )
    assert result["profile"]["countries"] == ["AUT"]
    assert result["profile"]["days_back"] == 7
    assert result["profile"]["queries"][1]["term_groups"] == [["Power Automate"]]
    assert (directory / "profile.toml").read_bytes() == config.read_bytes()


def test_t2_01_invalid_config_fails_before_network(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    invalid = tmp_path / "invalid.toml"
    invalid.write_text(
        profile_path.read_text("utf-8").replace("days_back = 90", "days_back = 0"), "utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["main.py", "--search", "--config", str(invalid)])

    def unexpected(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Netzabruf trotz ungültiger Konfiguration")

    monkeypatch.setattr(main, "search", unexpected)
    assert main.main() == 1
    assert "days_back" in capsys.readouterr().err


def test_t2_02_limit_and_complete_originals(tmp_path: Path, profile: Profile) -> None:
    # Zwei regelgerecht begrenzte Suchantworten ergeben drei verschiedene Kandidaten.
    network = Network(
        [response(row(200, 14), row(300, 13)), response(row(100, 15), row(200, 14))],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(),
            "https://ted.europa.eu/en/notice/200-2026/xml": xml(200),
        },
    )
    result, directory = execute(tmp_path, replace(profile, max_results=2), network)
    assert network.document_requests == [
        "https://ted.europa.eu/en/notice/100-2026/xml",
        "https://ted.europa.eu/en/notice/200-2026/xml",
    ]
    assert result["limited"] is True
    assert (directory / "documents/100-2026.xml").read_bytes() == xml()
    assert (directory / "documents/200-2026.xml").read_bytes() == xml(200)
    assert "zwölf Workshops" in (directory / "documents/100-2026.html").read_text("utf-8")
    assert not (directory / "documents/300-2026.xml").exists()


def test_t2_03_runs_are_immutable_and_traceable(tmp_path: Path, profile: Profile) -> None:
    one_query = replace(profile, queries=profile.queries[:1])
    url = "https://ted.europa.eu/en/notice/100-2026/xml"
    first_network = Network([response(row(100, 15))], {url: xml()})
    first, first_dir = execute(tmp_path, one_query, first_network, b"first profile")
    before = {p.relative_to(first_dir): p.read_bytes() for p in first_dir.rglob("*") if p.is_file()}
    second_xml = xml().replace(b"<cbc:VersionID>01", b"<cbc:VersionID>02")
    second, second_dir = execute(
        tmp_path,
        replace(one_query, name="Anderes Profil"),
        Network([response(row(100, 15))], {url: second_xml}),
        b"second profile",
    )
    assert first_dir != second_dir
    assert before == {
        p.relative_to(first_dir): p.read_bytes() for p in first_dir.rglob("*") if p.is_file()
    }
    assert (second_dir / "profile.toml").read_bytes() == b"second profile"
    assert (second_dir / "documents/100-2026.xml").read_bytes() == second_xml
    stored = json.loads((first_dir / "results.json").read_text("utf-8"))
    assert stored["queries"][0]["request"] == first_network.search_requests[0]
    assert stored["queries"][0]["response"] == response(row(100, 15))
    doc = first["notices"][0]["document"]
    assert doc["source_url"] == url
    assert doc["retrieved_at"] == RETRIEVED
    assert datetime.fromisoformat(stored["queries"][0]["retrieved_at"]).utcoffset() is not None
    assert doc["sha256"] == hashlib.sha256(xml()).hexdigest()
    assert doc["metadata"]["notice_ids"] == ["notice-alpha"]
    assert doc["metadata"]["procedure_ids"] == ["procedure-shared"]
    assert doc["metadata"]["versions"] == ["01"]
    assert doc["metadata"]["lot_ids"] == ["LOT-0001", "LOT-0002"]
    assert second["notices"][0]["document"]["metadata"]["versions"] == ["02"]


@pytest.mark.parametrize("different", [False, True])
def test_t2_04_duplicates_and_conflicts(tmp_path: Path, profile: Profile, different: bool) -> None:
    other_title = "Abweichender Titel" if different else "Beratung"
    network = Network(
        [response(row(100, 15)), response(row(100, 15, other_title), row(200, 14))],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(),
            "https://ted.europa.eu/en/notice/200-2026/xml": xml(200),
        },
    )
    result, directory = execute(tmp_path, profile, network)
    assert len(result["notices"]) == 2
    assert len(network.document_requests) == 2
    first = result["notices"][0]
    assert first["matched_queries"] == ["KI-Beratung", "Schulungen"]
    assert [entry["raw"]["notice-title"]["deu"] for entry in first["occurrences"]] == [
        "Beratung",
        other_title,
    ]
    assert first["conflicts"] == (["notice-title"] if different else [])
    if different:
        assert "Ungeklärte abweichende Suchangaben" in (directory / "overview.html").read_text(
            "utf-8"
        )
        assert result["status"] == "incomplete"
    else:
        assert result["status"] == "complete"


def test_t2_05_document_links_keep_lots_without_fetch(tmp_path: Path, profile: Profile) -> None:
    # Zweites Dokument hat überhaupt keine CallForTendersDocumentReference-Elemente.
    no_links = xml(200).split(b" <cac:ProcurementProjectLot>")[0] + b"</ContractNotice>"
    network = Network(
        [response(row(100, 15), row(200, 14))],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(),
            "https://ted.europa.eu/en/notice/200-2026/xml": no_links,
        },
    )
    result, directory = execute(tmp_path, replace(profile, queries=profile.queries[:1]), network)
    refs = result["notices"][0]["document"]["metadata"]["additional_documents"]
    assert [(r["url"], r["lot_id"]) for r in refs] == [
        ("https://example.org/unterlagen/los-1", "LOT-0001"),
        ("https://example.org/unterlagen/los-2", "LOT-0002"),
    ]
    assert all(r["status"] == "not_retrieved_not_evaluated" for r in refs)
    assert len(network.document_requests) == 2
    assert all(url.startswith("https://ted.europa.eu/") for url in network.document_requests)
    page = (directory / "overview.html").read_text("utf-8")
    assert "verlinkt, nicht abgerufen und nicht ausgewertet" in page
    assert "Kein Unterlagenlink angegeben" in page


def test_t2_06_empty_search_is_success(tmp_path: Path, profile: Profile) -> None:
    network = Network([response(), response()], {})
    result, directory = execute(tmp_path, profile, network)
    assert result["status"] == "empty"
    assert result["notices"] == []
    assert network.document_requests == []
    assert "Suche erfolgreich: keine Treffer" in (directory / "overview.html").read_text("utf-8")


def test_t2_06_partial_search_keeps_data_and_continues(tmp_path: Path, profile: Profile) -> None:
    network = Network(
        [SearchError("HTTP 503"), response(row(100, 15, None))],
        {"https://ted.europa.eu/en/notice/100-2026/xml": xml()},
    )
    result, directory = execute(tmp_path, profile, network)
    stored = json.loads((directory / "results.json").read_text("utf-8"))
    assert result["status"] == "incomplete"
    assert len(network.search_requests) == 2
    assert stored["queries"][0]["error"] == "HTTP 503"
    assert stored["queries"][1]["response"] == response(row(100, 15, None))
    assert (directory / "documents/100-2026.xml").read_bytes() == xml()
    page = (directory / "overview.html").read_text("utf-8")
    assert "100-2026 — nicht angegeben" in page
    assert "HTTP 503" in page
    assert "Suche erfolgreich: keine Treffer" not in page


def test_t2_06_document_failure_does_not_stop_remaining(tmp_path: Path, profile: Profile) -> None:
    network = Network(
        [response(row(100, 15), row(200, 14), row(300, 13))],
        {
            "https://ted.europa.eu/en/notice/100-2026/xml": xml(),
            "https://ted.europa.eu/en/notice/200-2026/xml": SearchError("HTTP 404"),
            "https://ted.europa.eu/en/notice/300-2026/xml": xml(300),
        },
    )
    result, directory = execute(tmp_path, replace(profile, queries=profile.queries[:1]), network)
    assert len(network.document_requests) == 3
    assert [n["document"]["status"] for n in result["notices"]] == ["ok", "error", "ok"]
    assert result["status"] == "incomplete"
    assert (directory / "documents/100-2026.xml").read_bytes() == xml()
    assert (directory / "documents/300-2026.xml").read_bytes() == xml(300)
    assert not (directory / "documents/200-2026.xml").exists()


@pytest.mark.parametrize("payload", [b"<html>Serverfehler</html>", b"<ContractNotice>", xml(999)])
def test_t2_07_invalid_download_is_not_a_notice(
    tmp_path: Path, profile: Profile, payload: bytes
) -> None:
    network = Network(
        [response(row(100, 15))], {"https://ted.europa.eu/en/notice/100-2026/xml": payload}
    )
    result, directory = execute(tmp_path, replace(profile, queries=profile.queries[:1]), network)
    doc = result["notices"][0]["document"]
    assert doc["status"] == "error"
    assert doc["error"]
    assert "file" not in doc
    assert "metadata" not in doc
    assert (directory / doc["response_file"]).read_bytes() == payload
    assert not (directory / "documents/100-2026.xml").exists()


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.hrefs.extend(value for key, value in attrs if key == "href" and value is not None)


def test_t2_08_files_remain_readable_after_program_exit(tmp_path: Path, profile_path: Path) -> None:
    # Eigenständiger Prozess mit echten CLI-/Such-/Speicherpfaden, nur HTTP simuliert.
    runner = tmp_path / "run_offline.py"
    runner.write_text(
        """
import io, json, sys
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0, sys.argv.pop(1))
fixture = Path(sys.argv.pop(1)).read_bytes()
import main
from ausschreibungen import notices, ted
rows = [{"publication-number": f"{n}-2026", "notice-title": {"deu": title},
         "links": {"xml": {"MUL": f"https://ted.europa.eu/en/notice/{n}-2026/xml"}}}
        for n, title in [(100, "Offline-Schulung"), (200, None)]]
ted.urlopen = lambda *args, **kwargs: io.BytesIO(
    json.dumps({"notices": rows, "totalNoticeCount": 2}).encode())
class Response(io.BytesIO):
    headers = {"Content-Type": "application/xml"}
    def geturl(self): return "https://ted.europa.eu/en/notice/100-2026/xml"
class Opener:
    def open(self, request, **kwargs):
        if "200-2026" in request.full_url:
            raise HTTPError(request.full_url, 404, "missing", {}, None)
        return Response(fixture)
notices.build_opener = lambda *args: Opener()
sys.exit(main.main())
""",
        encoding="utf-8",
    )
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "output" / "latest.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(runner),
            str(root),
            str(FIXTURES / "notice.xml"),
            "--search",
            "--config",
            str(profile_path),
            "--output",
            str(output),
            "--as-of",
            "2026-11-16",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 1
    directories = list((output.parent / "runs").iterdir())
    assert len(directories) == 1
    directory = directories[0]
    page = (directory / "overview.html").read_text("utf-8")
    for text in [
        "Testprofil",
        "2026-11-16",
        "Abruflimit: 20",
        "100-2026",
        "200-2026",
        "Offline-Schulung",
        "nicht angegeben",
        "KI-Beratung",
        "Schulungen",
        "HTTP 404",
        "Kandidaten",
        "Fachliche Eignung und offene Teilnahme sind ungeprüft",
    ]:
        assert text in page
    anchors = Links()
    anchors.feed(page)
    local_links = [href for href in anchors.hrefs if not href.startswith("https://")]
    assert "documents/100-2026.xml" in local_links
    assert "documents/100-2026.html" in local_links
    for href in local_links:
        assert (directory / href).is_file()
    assert (directory / "documents/100-2026.xml").read_bytes() == (
        FIXTURES / "notice.xml"
    ).read_bytes()
    assert "zwölf Workshops" in (directory / "documents/100-2026.html").read_text("utf-8")


def test_t2_09_truncated_http_response_keeps_other_documents(
    tmp_path: Path,
    profile_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Echte HTTP-Dekodierung: Der zweite Body endet mitten in einem angekündigten Chunk.
    class Socket:
        def __init__(self, wire: bytes) -> None:
            self.wire = wire

        def makefile(self, mode: str) -> BytesIO:
            return BytesIO(self.wire)

    requested: list[str] = []

    class Opener:
        def open(self, request: Request, *, timeout: int) -> HTTPResponse:
            requested.append(request.full_url)
            if request.full_url.endswith("/200-2026/xml"):
                wire = (
                    b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n"
                    b"Content-Type: application/xml\r\n\r\n64\r\n<ContractNotice"
                )
            else:
                payload = xml(100 if request.full_url.endswith("/100-2026/xml") else 300)
                wire = (
                    b"HTTP/1.1 200 OK\r\nContent-Type: application/xml\r\nContent-Length: "
                    + str(len(payload)).encode()
                    + b"\r\n\r\n"
                    + payload
                )
            answer = HTTPResponse(Socket(wire))
            answer.url = request.full_url
            answer.begin()
            return answer

    search_response = response(row(100, 15), row(200, 14), row(300, 13))
    monkeypatch.setattr(
        "ausschreibungen.ted.urlopen",
        lambda *args, **kwargs: BytesIO(json.dumps(search_response).encode()),
    )
    monkeypatch.setattr("ausschreibungen.notices.build_opener", lambda *args: Opener())
    monkeypatch.setattr("ausschreibungen.notices.time.sleep", lambda _: None)
    output = tmp_path / "latest.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["main.py", "--search", "--config", str(profile_path), "--output", str(output)],
    )

    assert main.main() == 1
    assert requested == [
        "https://ted.europa.eu/en/notice/100-2026/xml",
        "https://ted.europa.eu/en/notice/200-2026/xml",
        "https://ted.europa.eu/en/notice/300-2026/xml",
    ]
    directory = next((tmp_path / "runs").iterdir())
    stored = json.loads((directory / "results.json").read_text("utf-8"))
    assert json.loads(output.read_text("utf-8")) == stored
    assert stored["status"] == "incomplete"
    assert stored["stage"] == "finished"
    assert datetime.fromisoformat(stored["finished_at"]).utcoffset() is not None
    assert [n["document"]["status"] for n in stored["notices"]] == ["ok", "error", "ok"]
    error = stored["notices"][1]["document"]["error"]
    assert "TED-Dokumentabruf fehlgeschlagen" in error
    assert "IncompleteRead" in error
    assert (directory / "documents/100-2026.xml").read_bytes() == xml(100)
    assert (directory / "documents/300-2026.xml").read_bytes() == xml(300)
    assert not (directory / "documents/200-2026.xml").exists()
    page = (directory / "overview.html").read_text("utf-8")
    assert "Lauf unvollständig / offene Prüfpunkte" in page
    assert error in page
    assert "Abruffehler" in capsys.readouterr().err


def test_external_markup_is_text_and_dtd_is_rejected() -> None:
    malicious = xml().replace(b"Beratung und Schulung", b"&lt;script&gt;alert(1)&lt;/script&gt;")
    _, reading = inspect_document(malicious, "100-2026")
    assert "<script>" not in reading
    assert "&lt;script&gt;" in reading
    with pytest.raises(ValueError, match="DTD"):
        inspect_document(b'<!DOCTYPE x [<!ENTITY a "value">]><x>&a;</x>', "100-2026")
