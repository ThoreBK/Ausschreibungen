"""Offline-Tests, einschließlich einer am 15.11.2026 abgerufenen TED-Antwort."""

import json
from dataclasses import replace
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from ted import Profile, SearchError, build_query, fetch, load_profile, search

ROOT = Path(__file__).resolve().parents[1]


def test_example_profile_is_valid() -> None:
    # Nur dieser Test liest bewusst das vom Nutzer editierbare Beispielprofil.
    load_profile(ROOT / "search-profile.toml")


@pytest.mark.parametrize(
    ("groups", "expected"),
    [
        ('[[" Copilot ", "Microsoft 365"]]', '(FT ~ "Copilot" OR FT ~ "Microsoft 365")'),
        (
            '[["Copilot"], ["Beratung", "Schulung"]]',
            '(FT ~ "Copilot") AND (FT ~ "Beratung" OR FT ~ "Schulung")',
        ),
        (
            '[["Copilot"], ["Beratung", "Schulung"], ["Klinik"]]',
            '(FT ~ "Copilot") AND (FT ~ "Beratung" OR FT ~ "Schulung") AND (FT ~ "Klinik")',
        ),
    ],
)
def test_term_groups_query_and_recorded_profile(
    tmp_path: Path, profile_path: Path, groups: str, expected: str
) -> None:
    config = tmp_path / "profile.toml"
    header = profile_path.read_text("utf-8").split("\n[[queries]]")[0] + "\n"
    config.write_text(header + f'[[queries]]\nname = "Test"\nterm_groups = {groups}\n', "utf-8")
    profile = load_profile(config)
    query = build_query(profile, profile.queries[0], date(2026, 11, 15))
    assert query == (
        "publication-date >= 20260818 AND publication-date <= 20261115 "
        "AND buyer-country IN (DEU) AND " + expected + " SORT BY publication-date DESC"
    )
    result = search(profile, transport=lambda *_: {"notices": [], "totalNoticeCount": 0})
    assert result["profile"]["queries"] == [
        {"name": "Test", "term_groups": profile.queries[0].term_groups}
    ]
    assert profile.queries[0].term_groups[0][0] == "Copilot"


@pytest.mark.parametrize(
    "fields",
    [
        "term_groups = []",
        "term_groups = [[]]",
        'term_groups = [["Copilot"], []]',
        'term_groups = "Copilot"',
        'term_groups = ["Copilot"]',
        "term_groups = [[123]]",
        'term_groups = [[""]]',
        'term_groups = [["   "]]',
        """term_groups = [['bad"quote']]""",
        r"term_groups = [['bad\slash']]",
        r'term_groups = [["bad\nnewline"]]',
        'terms = ["Copilot"]\nrequire_any = []',
        'term_groups = [["Copilot"]]\nrequire_any = []',
        "",
    ],
)
def test_invalid_term_groups(tmp_path: Path, profile_path: Path, fields: str) -> None:
    config = tmp_path / "invalid.toml"
    header = profile_path.read_text("utf-8").split("\n[[queries]]")[0] + "\n"
    config.write_text(header + f'[[queries]]\nname = "Test"\n{fields}\n', "utf-8")
    with pytest.raises(ValueError, match="term_groups|Suchgruppe|Suchbegriffe"):
        load_profile(config)


def test_query_filters_and_alternatives(profile: Profile) -> None:
    profile = replace(profile, countries=["DEU", "AUT"], cpv_codes=["72000000"])
    query = build_query(profile, profile.queries[0], date(2026, 11, 15))
    assert "publication-date >= 20260818" in query
    assert "publication-date <= 20261115" in query
    assert "buyer-country IN (DEU AUT)" in query
    assert "classification-cpv IN (72000000)" in query
    assert '(FT ~ "künstliche Intelligenz" OR' in query
    assert ') AND (FT ~ "Beratung" OR' in query
    unrestricted = replace(profile, countries=[], cpv_codes=[])
    query = build_query(unrestricted, profile.queries[0], date(2026, 11, 15))
    assert "buyer-country" not in query
    assert "classification-cpv" not in query


def test_real_response_preserves_facts_and_sources(profile: Profile) -> None:
    profile = replace(profile, queries=profile.queries[:1])
    response = json.loads((ROOT / "tests/fixtures/ted-search.json").read_text("utf-8"))
    result = search(profile, today=date(2026, 11, 15), transport=lambda *_: response)
    notices = {notice["publication_number"]: notice for notice in result["notices"]}
    assert set(notices) == {"789644-2026", "792304-2026"}
    assert notices["789644-2026"]["buyer"] == ["Wald und Holz NRW"]
    notice = notices["792304-2026"]
    assert notice["buyer"] == ["Deutsches Rotes Kreuz e.V. Generalsekretariat"]
    assert notice["title"] == (
        "Deutschland – Dienstleistungen von Archiven – Rahmenvereinbarung für die "
        "Archiv- und Bibliothekbetreuung des DRK-Generalsekretariats"
    )
    assert notice["publication_date"] == "2026-11-13+01:00"
    assert notice["notice_type"] == "cn-standard"
    assert notice["deadlines"] == ["2026-12-14+01:00"]
    assert notice["links"]["xml"]["MUL"] == "https://ted.europa.eu/en/notice/792304-2026/xml"
    assert notice["links"]["html"]["DEU"] == (
        "https://ted.europa.eu/de/notice/-/detail/792304-2026"
    )
    assert result["source"] == "TED"
    assert result["as_of"] == "2026-11-15"
    assert result["queries"][0]["response"] == response
    assert datetime.fromisoformat(result["queries"][0]["retrieved_at"]).utcoffset() is not None


@pytest.fixture
def overlapping_responses() -> list[dict[str, Any]]:
    """Synthetische Treffer: Nummernfolge und Datumsfolge weichen bewusst ab."""
    older = {"publication-number": "900-2026", "publication-date": "2026-11-10+01:00"}
    middle = {"publication-number": "200-2026", "publication-date": "2026-11-12+01:00"}
    newer = {"publication-number": "100-2026", "publication-date": "2026-11-14+01:00"}
    return [
        {"notices": [middle, older], "totalNoticeCount": 2},
        {"notices": [newer, middle], "totalNoticeCount": 2},
    ]


def test_merges_only_shared_notices_and_preserves_query_origins(
    profile: Profile, overlapping_responses: list[dict[str, Any]]
) -> None:
    responses = iter(overlapping_responses)
    result = search(profile, transport=lambda *_: next(responses))
    assert result["unique_retrieved"] == 3
    assert len(result["notices"]) == 3
    assert {
        notice["publication_number"]: notice["matched_queries"] for notice in result["notices"]
    } == {
        "900-2026": ["KI-Beratung"],
        "200-2026": ["KI-Beratung", "Schulungen"],
        "100-2026": ["Schulungen"],
    }
    assert [run["response"] for run in result["queries"]] == overlapping_responses
    assert [run["name"] for run in result["queries"]] == ["KI-Beratung", "Schulungen"]


def test_sorts_combined_results_by_newest_publication(
    profile: Profile, overlapping_responses: list[dict[str, Any]]
) -> None:
    responses = iter(overlapping_responses)
    result = search(profile, transport=lambda *_: next(responses))
    assert [notice["publication_number"] for notice in result["notices"]] == [
        "100-2026",
        "200-2026",
        "900-2026",
    ]


@pytest.mark.parametrize(
    ("limit", "expected_numbers", "limited"),
    [(2, ["100-2026", "200-2026"], True), (3, ["100-2026", "200-2026", "900-2026"], False)],
)
def test_global_limit_after_complete_individual_searches(
    profile: Profile,
    overlapping_responses: list[dict[str, Any]],
    limit: int,
    expected_numbers: list[str],
    limited: bool,
) -> None:
    responses = iter(overlapping_responses)
    result = search(replace(profile, max_results=limit), transport=lambda *_: next(responses))
    assert [run["limited"] for run in result["queries"]] == [False, False]
    assert result["unique_retrieved"] == 3
    assert result["limited"] is limited
    assert [notice["publication_number"] for notice in result["notices"]] == expected_numbers


@pytest.mark.parametrize(("total", "limited"), [(1, False), (2, True)])
def test_individual_search_limit(profile: Profile, total: int, limited: bool) -> None:
    profile = replace(profile, max_results=1, queries=profile.queries[:1])
    response = {"notices": [{"publication-number": "123-2026"}], "totalNoticeCount": total}
    result = search(profile, transport=lambda *_: response)
    assert result["unique_retrieved"] == 1
    assert len(result["notices"]) == 1
    assert result["queries"][0]["returned"] == 1
    assert result["queries"][0]["total"] == total
    assert result["queries"][0]["limited"] is limited
    assert result["limited"] is limited


def test_fetch_posts_json_and_decodes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {"query": 'FT ~ "künstliche Intelligenz"', "fields": ["buyer-name"], "limit": 2}
    response = {"notices": [{"buyer-name": {"deu": ["Öffentlicher Auftraggeber"]}}]}
    requests: list[tuple[Request, int]] = []

    def respond(request: Request, *, timeout: int) -> BytesIO:
        requests.append((request, timeout))
        return BytesIO(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    monkeypatch.setattr("ted.urlopen", respond)
    assert fetch(body, 17) == response
    assert len(requests) == 1
    request, timeout = requests[0]
    assert request.full_url == "https://api.ted.europa.eu/v3/notices/search"
    assert request.get_method() == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Accept") == "application/json"
    assert request.data is not None
    assert json.loads(request.data) == body
    assert timeout == 17


def test_missing_optional_fields_and_zero_results(profile: Profile) -> None:
    result = search(profile, transport=lambda *_: {"notices": [], "totalNoticeCount": 0})
    assert result["notices"] == []
    assert not result["limited"]
    response = {"notices": [{"publication-number": "123-2026"}], "totalNoticeCount": 1}
    result = search(profile, transport=lambda *_: response)
    assert result["notices"][0]["title"] is None
    assert result["notices"][0]["deadlines"] is None


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"notices": [], "totalNoticeCount": 1},
        {"notices": [], "totalNoticeCount": 0, "timedOut": True},
        {"notices": [{}], "totalNoticeCount": 1},
    ],
)
def test_invalid_responses_are_errors(profile: Profile, response: dict[str, Any]) -> None:
    with pytest.raises(SearchError):
        search(profile, transport=lambda *_: response)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('countries = ["DEU"]', 'countries = ["DE"]'),
        ("max_results = 20", "max_results = 251"),
        ("days_back = 90", "days_back = true"),
        ('scope = "ACTIVE"', 'scope = "OPEN"'),
        ('name = "Schulungen"', 'name = "KI-Beratung"'),
        ("term_groups = [", "unknown_groups = ["),
        ("days_back = 90", "days_bak = 90"),
    ],
)
def test_invalid_configuration(tmp_path: Path, profile_path: Path, old: str, new: str) -> None:
    config = tmp_path / "invalid.toml"
    original = profile_path.read_text("utf-8")
    assert old in original
    config.write_text(original.replace(old, new), "utf-8")
    with pytest.raises(ValueError):
        load_profile(config)


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("https://example.org", 429, "rate limit", {}, None),
        URLError("offline"),
        TimeoutError("timeout"),
    ],
)
def test_network_errors(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    def fail(*args: Any, **kwargs: Any) -> None:
        raise error

    monkeypatch.setattr("ted.urlopen", fail)
    with pytest.raises(SearchError):
        fetch({}, 1)
