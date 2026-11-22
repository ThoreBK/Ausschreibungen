import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ausschreibungen.extraction import extract as extract_notice

NOW = datetime(2026, 11, 17, 14, tzinfo=UTC)
FIXTURES = Path(__file__).parents[1] / "fixtures"
PROFILE = Path(__file__).parents[2] / "analysis-profile.toml"


def xml(lots: str = "", *, extra: str = "", version: str = "01") -> bytes:
    return f"""<ContractNotice xmlns="urn:oasis:names:specification:ubl:schema:xsd:ContractNotice-2"
      xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
      xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
      xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
      xmlns:efext="http://data.europa.eu/p27/eforms-ubl-extensions/1"
      xmlns:efac="http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1"
      xmlns:efbc="http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1">
      <ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent><efext:EformsExtension>
      <efac:Publication><efbc:NoticePublicationID>100-2026</efbc:NoticePublicationID>
      </efac:Publication></efext:EformsExtension></ext:ExtensionContent></ext:UBLExtension>
      </ext:UBLExtensions><cbc:ID>notice</cbc:ID><cbc:VersionID>{version}</cbc:VersionID>
      {extra}{lots}</ContractNotice>""".encode()


def lot(
    identifier: str = "LOT-1",
    day: str = "2026-12-01Z",
    clock: str = "12:00:00Z",
    *,
    subject: str = "KI-Beratung",
    criterion: str = "Referenz über zwei KI-Schulungen",
) -> str:
    return f"""<cac:ProcurementProjectLot><cbc:ID>{identifier}</cbc:ID>
      <cac:ProcurementProject><cbc:Description>{subject}</cbc:Description>
      </cac:ProcurementProject><cac:TenderingProcess><cac:TenderSubmissionDeadlinePeriod>
      <cbc:EndDate>{day}</cbc:EndDate><cbc:EndTime>{clock}</cbc:EndTime>
      </cac:TenderSubmissionDeadlinePeriod></cac:TenderingProcess><cac:TenderingTerms>
      <cac:TendererQualificationRequest><cac:SpecificTendererRequirement>
      <cbc:Description>{criterion}</cbc:Description></cac:SpecificTendererRequirement>
      </cac:TendererQualificationRequest></cac:TenderingTerms></cac:ProcurementProjectLot>"""


def citation(document: dict[str, Any], text: str) -> dict[str, str]:
    return {
        "path": next(r["path"] for r in document["records"] if text in r["value"]),
        "quote": text,
    }


def proposal(document: dict[str, Any], *, status: str = "passend") -> dict[str, Any]:
    return {
        "facts": [],
        "fit": {
            "status": status,
            "reason": "Beauftragte KI-Beratung passt zum Profil.",
            "evidence": [citation(document, "KI-Beratung")],
        },
        "checkpoints": [],
    }


def saved_run(tmp_path: Path, content: bytes, number: str = "100-2026") -> Path:
    (tmp_path / "documents").mkdir()
    (tmp_path / "documents" / f"{number}.xml").write_bytes(content)
    (tmp_path / "results.json").write_text(
        json.dumps(
            {
                "run_id": "fixed-research-run",
                "notices": [
                    {
                        "publication_number": number,
                        "document": {
                            "status": "ok",
                            "file": f"documents/{number}.xml",
                            "sha256": hashlib.sha256(content).hexdigest(),
                            "retrieved_at": "2026-11-17T11:05:48+00:00",
                            "source_url": f"https://ted.europa.eu/en/notice/{number}/xml",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def two_lots() -> dict[str, Any]:
    return extract_notice(
        xml(
            lot("LOT-A") + lot("LOT-B", subject="Bauarbeiten"),
            extra="<cbc:Note>Gemeinsam 🙂</cbc:Note>",
        ),
        "100-2026",
        now=NOW,
    )
