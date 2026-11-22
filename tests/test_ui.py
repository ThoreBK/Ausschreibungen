"""UI-Profil, Berichtslauf und Ergebniszugriff am lokalen HTTP-Einstieg."""

import json
import shutil
import sys
import threading
import time
from collections.abc import Iterator
from copy import deepcopy
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pytest
from pypdf import PdfReader

import main
from ausschreibungen import ui
from ausschreibungen.extraction import extract
from ausschreibungen.ted import SearchError, search
from tests.support.models import ControlledModel
from tests.support.notices import NOW, PROFILE, lot, proposal, xml
from tests.support.research import Network, response, row


@pytest.fixture
def site(tmp_path: Path, profile_path: Path) -> Iterator[str]:
    shutil.copyfile(profile_path, tmp_path / "search-profile.toml")
    shutil.copyfile(PROFILE, tmp_path / "analysis-profile.toml")
    with ui.LocalServer(("127.0.0.1", 0), partial(ui.Handler, ui.Application(tmp_path))) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


def api(site: str, route: str, data: dict[str, Any] | None = None) -> Any:
    request = Request(
        site + "/api/" + route,
        headers={"Origin": site, "Content-Type": "application/json"},
        data=None if data is None else json.dumps(data).encode(),
    )
    with urlopen(request, timeout=5) as reply:
        return json.load(reply)


@pytest.mark.parametrize(
    "viewport", [{"width": 1280, "height": 720}, {"width": 360, "height": 640}]
)
def test_profile_and_start_in_first_view(site: str, viewport: dict[str, int]) -> None:
    """Browserprüfung mit uv run --group ui-test pytest tests/test_ui.py."""
    browser_api = pytest.importorskip("playwright.sync_api")
    with browser_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge" if sys.platform == "win32" else None)
        page = browser.new_page(viewport=viewport)
        page.goto(site)
        expect = browser_api.expect
        start = page.get_by_role("button", name="Recherche starten")
        expect(start).to_be_enabled()
        expect(start).to_be_in_viewport(ratio=1)
        expect(page.get_by_role("heading", name="Testprofil")).to_be_in_viewport(ratio=1)
        coverage = page.locator("#coverage")
        expect(coverage).to_have_text(
            "TED · Aktive Bekanntmachungen · Sitz des Auftraggebers: Deutschland · Letzte 90 Tage"
        )
        expect(page.locator("#cpv-filter")).to_be_hidden()
        topic = page.locator("details").filter(has=page.get_by_text("KI-Beratung", exact=True))
        rows = topic.get_by_role("listitem")
        expect(rows).to_have_count(0)
        topic.locator("summary").click()
        expect(rows).to_have_text(
            ["künstliche Intelligenz, artificial intelligence", "Beratung, consulting"]
        )

        page.get_by_role("button", name="Profil bearbeiten").click()
        page.get_by_text("Weitere Einstellungen", exact=True).click()
        page.get_by_label("TED-Suchbereich").select_option("ALL")
        page.get_by_label("CPV-Codes").fill("72000000, 80000000")
        page.get_by_role("button", name="Einstellungen speichern").click()
        expect(coverage).to_contain_text("Einschließlich historischer Bekanntmachungen")
        expect(page.locator("#cpv-filter")).to_have_text("CPV-Filter: 72000000, 80000000")
        expect(page.locator("#cpv-filter")).to_be_visible()
        expect(start).to_be_in_viewport(ratio=1)


def test_ui_profile_rejects_invalid_and_stale_edits(site: str, tmp_path: Path) -> None:
    initial = api(site, "settings")
    changed = deepcopy(initial)
    changed["search"]["queries"] = []
    with pytest.raises(HTTPError) as invalid:
        api(site, "settings", {"base": initial, "settings": changed})
    assert invalid.value.code == 400
    assert api(site, "settings") == initial
    changed["search"] = dict(initial["search"], countries=[])
    api(site, "settings", {"base": initial, "settings": changed})
    assert ui.read_settings(tmp_path) == changed
    with pytest.raises(HTTPError) as stale:
        api(site, "report", {"base": initial})
    assert stale.value.code == 409
    assert api(site, "status")["status"] == "idle"


def test_analysis_progress_survives_reload(site: str, monkeypatch: pytest.MonkeyPatch) -> None:
    browser_api = pytest.importorskip("playwright.sync_api")
    content = xml(lot())
    network = Network(
        [response(row(101, 16), row(100, 15)), response()],
        {
            "https://ted.europa.eu/en/notice/101-2026/xml": SearchError("Original fehlt"),
            "https://ted.europa.eu/en/notice/100-2026/xml": content,
        },
    )
    model = ControlledModel(proposal(extract(content, "100-2026", now=NOW)))
    proceed = threading.Event()

    def paused_model(instructions: str, payload: dict[str, Any], schema: dict[str, Any]) -> Any:
        assert proceed.wait(30)
        return model(instructions, payload, schema)

    monkeypatch.setattr(main, "search", partial(search, transport=network.search))
    monkeypatch.setattr(main, "collect", partial(main.collect, download=network.download))
    monkeypatch.setattr(main, "analyze_run", partial(main.analyze_run, model=paused_model))
    with browser_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge" if sys.platform == "win32" else None)
        page = browser.new_page()
        page.goto(site)
        page.get_by_role("button", name="Recherche starten").click()
        bar = page.get_by_role("progressbar", name="1 von 2 Bekanntmachungen bearbeitet")
        expect = browser_api.expect
        try:
            expect(bar).to_be_visible()
            page.reload()
            expect(bar).to_be_visible()
            expect(bar).to_have_attribute("value", "1")
            expect(bar).to_have_attribute("max", "2")
        finally:
            proceed.set()
        expect(page.get_by_role("link", name="PDF öffnen")).to_be_visible()
        expect(page.get_by_role("progressbar")).to_be_hidden()
        assert api(site, "status")["analysis_progress"] == {"processed": 2, "total": 2}


@pytest.mark.parametrize("partial_failure", [False, True])
def test_ui_report_uses_settings_and_serves_pdf(
    site: str, monkeypatch: pytest.MonkeyPatch, partial_failure: bool
) -> None:
    initial = api(site, "settings")
    updated = deepcopy(initial)
    updated["search"].update(
        countries=["AUT"],
        country_field="place-of-performance",
        queries=[
            {"name": "Weiterbildung", "term_groups": [["Copilot"], ["Kurs", "Seminar"]]},
            {"name": "Alternative", "term_groups": [["KI-Beratung"]]},
        ],
    )
    updated["analysis"]["company_profile"] = 'Beratung für "KI"\nSchulung und Prüfung'
    api(site, "settings", {"base": initial, "settings": updated})
    content = xml(lot())
    model = ControlledModel(proposal(extract(content, "100-2026", now=NOW)))
    network = Network(
        [response(row(100, 15)), SearchError("TED offline") if partial_failure else response()],
        {"https://ted.europa.eu/en/notice/100-2026/xml": content},
    )
    entered = threading.Event()
    proceed = threading.Event()

    def transport(body: dict[str, Any], timeout: int) -> dict[str, Any]:
        entered.set()
        assert proceed.wait(10)
        return network.search(body, timeout)

    monkeypatch.setattr(main, "search", partial(search, transport=transport))
    monkeypatch.setattr(main, "collect", partial(main.collect, download=network.download))
    monkeypatch.setattr(main, "analyze_run", partial(main.analyze_run, model=model))
    assert api(site, "status")["status"] == "idle"
    api(site, "report", {"base": updated})
    try:
        assert entered.wait(5)
        state = api(site, "status")
        assert state["status"] == "running"
        assert state["analysis_progress"] is None
        with pytest.raises(HTTPError) as duplicate:
            api(site, "report", {"base": updated})
        assert duplicate.value.code == 409
    finally:
        proceed.set()
    deadline = time.monotonic() + 10
    while (state := api(site, "status"))["status"] == "running" and time.monotonic() < deadline:
        time.sleep(0.03)
    assert state["status"] == ("incomplete" if partial_failure else "complete"), state
    assert state["analysis_progress"] == {"processed": 1, "total": 1}
    assert len(network.search_requests) == 2
    query = network.search_requests[0]["query"]
    assert "place-of-performance IN (AUT)" in query
    assert '(FT ~ "Copilot") AND (FT ~ "Kurs" OR FT ~ "Seminar")' in query
    assert model.payloads[0]["company_profile"] == updated["analysis"]["company_profile"]
    pdf_url = site + state["pdf"]
    with urlopen(pdf_url, timeout=5) as pdf:
        assert pdf.headers.get_content_type() == "application/pdf"
        reader = PdfReader(BytesIO(pdf.read()))
    assert "Weiterbildung" in " ".join(p.extract_text() for p in reader.pages)
    with urlopen(urljoin(pdf_url, "../../overview.html"), timeout=5) as overview:
        assert "Weiterbildung" in overview.read().decode()
    if partial_failure:
        assert any("TED offline" in line for line in state["messages"])
