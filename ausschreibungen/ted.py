"""Kleine TED-Anbindung ohne Laufzeitabhängigkeiten.

API-Felder bleiben in den Rohantworten erhalten: keine erfundenen Ergänzungen,
keine Zusammenführung verschiedener Bekanntmachungen eines Verfahrens.
"""

import json
import re
import time
import tomllib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
FIELDS = [
    "publication-number",
    "notice-title",
    "buyer-name",
    "publication-date",
    "notice-type",
    "deadline-receipt-tender-date-lot",
]


class SearchError(Exception):
    """Ein Abruffehler ist kein leeres Suchergebnis."""


@dataclass(frozen=True)
class Query:
    name: str
    term_groups: list[list[str]]


@dataclass(frozen=True)
class Profile:
    name: str
    countries: list[str]
    country_field: str
    days_back: int
    max_results: int
    scope: str
    language: str
    timeout_seconds: int
    cpv_codes: list[str]
    queries: list[Query]
    report_limit: int = 20


def strings(value: Any, label: str, *, nonempty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or (nonempty and not value)
    ):
        raise ValueError(f"{label}: Liste mit nichtleeren Texten erwartet.")
    return [item.strip() for item in value]


def load_profile(path: Path) -> Profile:
    with path.open("rb") as file:
        data = tomllib.load(file)
    expected = set(Profile.__dataclass_fields__)
    data.setdefault("report_limit", Profile.report_limit)
    if set(data) != expected:
        raise ValueError(
            f"Profilfelder fehlen: {sorted(expected - set(data))}; "
            f"unbekannt: {sorted(set(data) - expected)}"
        )
    for key in ("name", "country_field", "scope", "language"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key}: nichtleerer Text erwartet.")
    for key, maximum in (
        ("days_back", 36500),
        ("max_results", 250),
        ("report_limit", 250),
        ("timeout_seconds", 300),
    ):
        if type(data[key]) is not int or not 1 <= data[key] <= maximum:
            raise ValueError(f"{key}: ganze Zahl zwischen 1 und {maximum} erwartet.")
    if data["scope"] not in {"ACTIVE", "ALL", "LATEST"}:
        raise ValueError("scope: ACTIVE, ALL oder LATEST erwartet.")
    if data["country_field"] not in {"buyer-country", "place-of-performance"}:
        raise ValueError("country_field: buyer-country oder place-of-performance erwartet.")
    if not re.fullmatch(r"[a-z]{3}", data["language"]):
        raise ValueError("language: dreistelliger Sprachcode erwartet, z. B. deu.")
    for key, pattern in (("countries", r"[A-Z]{3}"), ("cpv_codes", r"\d{8}")):
        data[key] = strings(data[key], key)
        if any(not re.fullmatch(pattern, item) for item in data[key]):
            raise ValueError(f"{key}: ungültiges Codeformat.")
    if not isinstance(data["queries"], list) or not data["queries"]:
        raise ValueError("Mindestens eine Suchgruppe ist erforderlich.")
    queries = []
    for item in data["queries"]:
        if not isinstance(item, dict) or set(item) != {"name", "term_groups"}:
            raise ValueError("Suchgruppe benötigt name und term_groups.")
        name = item["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Suchgruppenname darf nicht leer sein.")
        if not isinstance(item["term_groups"], list) or not item["term_groups"]:
            raise ValueError("term_groups: mindestens eine Begriffsgruppe erforderlich.")
        term_groups = [
            strings(group, f"term_groups[{index}]", nonempty=True)
            for index, group in enumerate(item["term_groups"], start=1)
        ]
        if any(
            '"' in term or "\\" in term or any(ord(c) < 32 for c in term)
            for group in term_groups
            for term in group
        ):
            raise ValueError("Suchbegriffe dürfen keine Anführungs-/Steuerzeichen enthalten.")
        queries.append(Query(name.strip(), term_groups))
    if len({query.name for query in queries}) != len(queries):
        raise ValueError("Suchgruppennamen müssen eindeutig sein.")
    data["queries"] = queries
    return Profile(**data)


def build_query(profile: Profile, query: Query, today: date) -> str:
    # Inklusive heute genau days_back Kalendertage.
    start = today - timedelta(days=profile.days_back - 1)
    parts = [f"publication-date >= {start:%Y%m%d}", f"publication-date <= {today:%Y%m%d}"]
    parts.append("form-type != result")
    if profile.countries:
        parts.append(f"{profile.country_field} IN ({' '.join(profile.countries)})")
    if profile.cpv_codes:
        parts.append(f"classification-cpv IN ({' '.join(profile.cpv_codes)})")
    for terms in query.term_groups:
        parts.append("(" + " OR ".join(f'FT ~ "{term}"' for term in terms) + ")")
    return " AND ".join(parts) + " SORT BY publication-date DESC"


def fetch(body: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = Request(
        ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        time.sleep(0.65)  # Auch bei sehr vielen Suchblöcken unter TED-Fair-Use bleiben.
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except HTTPError as error:
        raise SearchError(f"TED antwortet mit HTTP {error.code}.") from error
    except (URLError, OSError, ValueError) as error:
        raise SearchError(f"TED-Abruf fehlgeschlagen: {error}") from error
    if not isinstance(result, dict):
        raise SearchError("Unerwartetes TED-Antwortformat.")
    return result


def localized(value: Any, language: str) -> Any:
    """Keine Übersetzung erfinden; Originalsprachen bleiben in raw erhalten."""
    if isinstance(value, dict):
        return value.get(language) or value.get("eng") or next(iter(value.values()), None)
    return value


def search(
    profile: Profile,
    *,
    today: date | None = None,
    transport: Callable[[dict[str, Any], int], dict[str, Any]] = fetch,
    continue_on_error: bool = False,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
    all_returned: bool = False,
) -> dict[str, Any]:
    today = today or date.today()
    runs: list[dict[str, Any]] = []
    notices: dict[str, dict[str, Any]] = {}

    def snapshot() -> dict[str, Any]:
        ordered = sorted(
            notices.values(),
            key=lambda item: (item["publication_date"] or "", item["publication_number"]),
            reverse=True,
        )
        return {
            "source": "TED",
            "endpoint": ENDPOINT,
            "as_of": today.isoformat(),
            "profile": asdict(profile),
            "queries": runs,
            "unique_retrieved": len(ordered),
            "all_returned": all_returned,
            "limited": (not all_returned and len(ordered) > profile.max_results)
            or any(run.get("limited", False) for run in runs),
            "search_incomplete": any(run["status"] == "error" for run in runs),
            "notices": ordered if all_returned else ordered[: profile.max_results],
        }

    for query in profile.queries:
        body = {
            "query": build_query(profile, query, today),
            "fields": FIELDS,
            "limit": profile.max_results,
            "page": 1,
            "scope": profile.scope,
            "paginationMode": "PAGE_NUMBER",
            "onlyLatestVersions": True,
        }
        run = {
            "name": query.name,
            "request": body,
            "started_at": datetime.now(UTC).isoformat(),
            "status": "running",
        }
        runs.append(run)
        try:
            response = transport(body, profile.timeout_seconds)
            run["response"] = response
            run["retrieved_at"] = datetime.now(UTC).isoformat()
            rows, total = response.get("notices"), response.get("totalNoticeCount")
            if response.get("timedOut"):
                raise SearchError(f"TED-Zeitlimit bei Suchgruppe {query.name}.")
            if not isinstance(rows, list) or type(total) is not int or total < len(rows):
                raise SearchError("Unvollständige oder ungültige TED-Antwort.")
            if total and not rows:
                raise SearchError("TED meldet Treffer, liefert aber keine Bekanntmachungen.")
            for raw in rows:
                if not isinstance(raw, dict):
                    raise SearchError("Ungültige Bekanntmachung.")
                number = raw.get("publication-number")
                if not isinstance(number, str) or not re.fullmatch(r"\d+-\d{4}", number):
                    raise SearchError("Bekanntmachung ohne gültige Veröffentlichungsnummer.")
            run.update(status="ok", total=total, returned=len(rows), limited=total > len(rows))
        except SearchError as error:
            run.update(status="error", error=str(error), finished_at=datetime.now(UTC).isoformat())
            if on_progress:
                on_progress(snapshot())
            if not continue_on_error:
                raise
            continue
        for raw in rows:
            serial, year = raw["publication-number"].split("-")
            number = f"{int(serial)}-{year}"
            if number not in notices:
                notices[number] = {
                    "publication_number": number,
                    "title": localized(raw.get("notice-title"), profile.language),
                    "buyer": localized(raw.get("buyer-name"), profile.language),
                    "publication_date": raw.get("publication-date"),
                    "notice_type": raw.get("notice-type"),
                    "deadlines": raw.get("deadline-receipt-tender-date-lot"),
                    "links": raw.get("links"),
                    "matched_queries": [],
                    "occurrences": [],
                    "conflicts": [],
                }
            notice = notices[number]
            for occurrence in notice["occurrences"]:
                previous = occurrence["raw"]
                for field in previous.keys() & raw.keys() - {"publication-number"}:
                    if (
                        previous[field] is not None
                        and raw[field] is not None
                        and previous[field] != raw[field]
                        and field not in notice["conflicts"]
                    ):
                        notice["conflicts"].append(field)
            notice["conflicts"].sort()
            notice["occurrences"].append({"query": query.name, "raw": raw})
            if query.name not in notice["matched_queries"]:
                notice["matched_queries"].append(query.name)
        if on_progress:
            on_progress(snapshot())
    return snapshot()
