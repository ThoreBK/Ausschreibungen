"""TED-Originale prüfen; nur Herkunft, Identität und Unterlagenverweise erschließen."""

import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from html import escape
from http.client import HTTPException
from typing import IO, Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from ted import SearchError

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "efext": "http://data.europa.eu/p27/eforms-ubl-extensions/1",
}
PUBLICATION_PATH = (
    "./ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/"
    "efext:EformsExtension/efac:Publication/efbc:NoticePublicationID"
)
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024


@dataclass(frozen=True)
class Download:
    content: bytes
    final_url: str
    content_type: str
    retrieved_at: str


def is_ted_url(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "https" and parsed.netloc == "ted.europa.eu" and not parsed.username


class TedRedirects(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: IO[bytes], code: int, msg: str, headers: Message, newurl: str
    ) -> Request | None:
        if not is_ted_url(newurl):
            raise SearchError("TED-Download verweist auf eine nicht zugelassene Adresse.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_document(url: str, timeout: int) -> Download:
    if not is_ted_url(url):
        raise SearchError("Für Bekanntmachungen sind nur öffentliche TED-URLs zugelassen.")
    request = Request(url, headers={"Accept": "application/xml"})
    try:
        time.sleep(0.65)  # Seriell: weniger als 600 Downloads in sechs Minuten.
        with build_opener(TedRedirects()).open(request, timeout=timeout) as response:
            content = response.read(MAX_DOCUMENT_BYTES + 1)
            if len(content) > MAX_DOCUMENT_BYTES:
                raise SearchError("Bekanntmachung überschreitet das Downloadlimit von 20 MiB.")
            return Download(
                content,
                response.geturl(),
                response.headers.get("Content-Type", ""),
                datetime.now(UTC).isoformat(),
            )
    except HTTPError as error:
        raise SearchError(f"TED-Dokumentabruf: HTTP {error.code}.") from error
    except (URLError, OSError, HTTPException) as error:
        raise SearchError(f"TED-Dokumentabruf fehlgeschlagen: {error}") from error


class NoDoctype(ET.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("DTD/Entitäten werden in externen Dokumenten nicht verarbeitet.")


def publication_number(value: str) -> str:
    match = re.fullmatch(r"0*(\d+)-(\d{4})", value.strip())
    if not match:
        raise ValueError(f"Ungültige Veröffentlichungsnummer im XML: {value}")
    return f"{int(match[1])}-{match[2]}"


def short_tag(tag: str) -> str:
    for prefix, namespace in NS.items():
        if tag.startswith("{" + namespace + "}"):
            return prefix + ":" + tag.split("}", 1)[1]
    return tag.split("}")[-1]


def inspect_document(content: bytes, expected_number: str) -> tuple[dict[str, Any], str]:
    """Keine Vollschema-/Eignungsprüfung. Fehlende Identität gilt nicht als bestätigt."""
    try:
        root = ET.fromstring(content, parser=ET.XMLParser(target=NoDoctype()))
    except (ET.ParseError, ValueError) as error:
        raise ValueError(f"Kein lesbares Bekanntmachungs-XML: {error}") from error
    supported = {
        f"{{urn:oasis:names:specification:ubl:schema:xsd:{name}-2}}{name}"
        for name in ("ContractNotice", "ContractAwardNotice", "PriorInformationNotice")
    }
    if root.tag not in supported:
        raise ValueError("Kein unterstütztes eForms-Bekanntmachungs-XML.")
    numbers = [node.text or "" for node in root.findall(PUBLICATION_PATH, NS)]
    if not numbers:
        raise ValueError("Veröffentlichungsnummer im XML fehlt; Identität ungeklärt.")
    if {publication_number(value) for value in numbers} != {expected_number}:
        raise ValueError(f"Abweichende Bekanntmachungsidentität im XML: {numbers}")

    def values(path: str) -> list[str]:
        return [node.text.strip() for node in root.findall(path, NS) if node.text]

    metadata = {
        "publication_numbers": numbers,
        "notice_ids": values("./cbc:ID"),
        "procedure_ids": values("./cbc:ContractFolderID"),
        "versions": values("./cbc:VersionID"),
        "lot_ids": values("./cac:ProcurementProjectLot/cbc:ID"),
        "additional_documents": [],
    }
    display: list[str] = []

    def walk(node: ET.Element, path: str, lot: str | None = None) -> None:
        if node.tag == "{" + NS["cac"] + "}ProcurementProjectLot":
            lot = node.findtext("./cbc:ID", namespaces=NS)
        if node.tag == "{" + NS["cac"] + "}CallForTendersDocumentReference":
            for uri in node.findall("./cac:Attachment/cac:ExternalReference/cbc:URI", NS):
                if uri.text and uri.text.strip():
                    metadata["additional_documents"].append(
                        {
                            "url": uri.text.strip(),
                            "lot_id": lot,
                            "document_id": node.findtext("./cbc:ID", namespaces=NS),
                            "source_path": path + "/cac:Attachment/cac:ExternalReference/cbc:URI",
                            "status": "not_retrieved_not_evaluated",
                        }
                    )
        # Eine reine Lesekopie: alle Textwerte in Originalreihenfolge, ohne Interpretation.
        if node.text and node.text.strip():
            attributes = " ".join(f"{key}={value}" for key, value in node.attrib.items())
            display.append(
                f"<dt>{escape(path)} {escape(attributes)}</dt><dd>{escape(node.text.strip())}</dd>"
            )
        counters: dict[str, int] = {}
        for child in node:
            tag = short_tag(child.tag)
            counters[tag] = counters.get(tag, 0) + 1
            walk(child, f"{path}/{tag}[{counters[tag]}]", lot)

    walk(root, "/" + short_tag(root.tag))
    return metadata, "<dl>" + "".join(display) + "</dl>"


def html_page(title: str, body: str) -> str:
    return (
        '<!doctype html><html lang="de"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'\">"
        f"<title>{escape(title)}</title><style>"
        "body{font:16px/1.55 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 24px;"
        "color:#172a3a;background:#fff;overflow-wrap:anywhere}"
        "h1,h2{line-height:1.25}article{border-top:2px solid #ccd6df;"
        "padding:20px 0}a{color:#07559c}pre,dd{white-space:pre-wrap;overflow-wrap:anywhere}"
        "dt{font-size:12px;color:#526779;overflow-wrap:anywhere;margin-top:18px}"
        "dd{margin:4px 0 16px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #ccd6df;padding:8px;text-align:left;vertical-align:top}"
        ".warning{background:#fff0d2;padding:12px}small{color:#526779}"
        "</style><body>" + body + "</body></html>"
    )
