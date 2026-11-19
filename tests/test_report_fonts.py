import json
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from PIL import Image
from pypdf import PdfReader

from ausschreibungen.analysis import analyze_run
from ausschreibungen.report import write_report
from ausschreibungen.ted import Profile
from tests.test_analysis import NOW, PROFILE, lot, xml
from tests.test_research import Network, execute, response, row

SAMPLE = "Łódź | Υπηρεσίες | София | 𝑃𝐵𝑖𝑒𝑡𝑒𝑟"
REFERENCES = Path(__file__).parent / "fixtures" / "pdf-fonts"


def sample_report(tmp_path: Path, profile: Profile) -> Path:
    network = Network(
        [response(row(100, 14, SAMPLE)), response()],
        {"https://ted.europa.eu/en/notice/100-2026/xml": xml(lot(subject=SAMPLE))},
    )
    research, run = execute(tmp_path, profile, network)
    directory = analyze_run(run, PROFILE, structured_only=True, now=NOW)
    analysis = json.loads((directory / "analysis.json").read_bytes())
    return write_report(research, analysis, directory)


def rendered_lines(pdf: Path) -> dict[str, Image.Image]:
    result = {}
    with pdfium.PdfDocument(pdf) as document:
        for index, roles in enumerate([["overview"], ["title", "subject"], ["quote"]]):
            page = document[index]
            text = page.get_textpage()
            search = text.search("Łódź")
            image = page.render(scale=3).to_pil()
            for role in roles:
                match = search.get_next()
                assert match, role
                left, bottom, _, _ = text.get_charbox(match[0])
                x = round(left * 3) - 2
                y = round((page.get_height() - bottom) * 3)
                result[role] = image.crop((x, y - 32, x + 640, y + 8)).convert("L")
    return result


def test_unicode_report(tmp_path: Path, profile: Profile) -> None:
    pdf = sample_report(tmp_path, profile)
    overview, brief, quotes = [page.extract_text().splitlines() for page in PdfReader(pdf).pages]
    assert SAMPLE in overview
    assert SAMPLE in brief
    assert f"Gegenstand: {SAMPLE} [3]" in brief
    assert SAMPLE in quotes
    for role, image in rendered_lines(pdf).items():
        with Image.open(REFERENCES / f"{role}.png") as expected:
            assert image.tobytes() == expected.tobytes(), role


def test_missing_title_glyph_reports_notice_and_codepoint(tmp_path: Path, profile: Profile) -> None:
    network = Network(
        [response(row(100, 14, "木")), response()],
        {"https://ted.europa.eu/en/notice/100-2026/xml": xml(lot())},
    )
    research, run = execute(tmp_path, profile, network)
    with pytest.raises(ValueError, match=r"U\+6728 in Titel · TED 100-2026"):
        write_report(research, None, run)
