from datetime import date
from functools import partial
from pathlib import Path
from typing import Any

from ausschreibungen.notices import Download
from ausschreibungen.research import collect
from ausschreibungen.ted import Profile, search
from tests.support.notices import FIXTURES

AS_OF = date(2026, 11, 16)
RETRIEVED = "2026-11-16T15:00:00+00:00"


def xml(number: int = 100) -> bytes:
    return (
        (FIXTURES / "notice.xml").read_bytes().replace(b"00000100-2026", f"{number}-2026".encode())
    )


def row(number: int, day: int, title: str | None = "Beratung") -> dict[str, Any]:
    return {
        "publication-number": f"{number}-2026",
        "publication-date": f"2026-11-{day:02d}+01:00",
        "notice-title": {"deu": title},
        "procedure-identifier": "procedure-shared",
        "links": {"xml": {"MUL": f"https://ted.europa.eu/en/notice/{number}-2026/xml"}},
    }


def response(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"notices": list(rows), "totalNoticeCount": len(rows)}


class Network:
    """Feste Antworten und vollständiges Anfrageprotokoll, keine Produktionslogik."""

    def __init__(
        self, responses: list[dict[str, Any] | Exception], documents: dict[str, bytes | Exception]
    ) -> None:
        self.responses = iter(responses)
        self.documents = documents
        self.search_requests: list[dict[str, Any]] = []
        self.document_requests: list[str] = []

    def search(self, request: dict[str, Any], timeout: int) -> dict[str, Any]:
        self.search_requests.append(request)
        answer = next(self.responses)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def download(self, url: str, timeout: int) -> Download:
        self.document_requests.append(url)
        answer = self.documents[url]
        if isinstance(answer, Exception):
            raise answer
        return Download(answer, url, "application/xml", RETRIEVED)


def execute(
    tmp_path: Path, profile: Profile, network: Network, config: bytes = b"test input"
) -> tuple[dict[str, Any], Path]:
    return collect(
        profile,
        config,
        tmp_path / "runs",
        today=AS_OF,
        search_fn=partial(search, transport=network.search),
        download=network.download,
    )
