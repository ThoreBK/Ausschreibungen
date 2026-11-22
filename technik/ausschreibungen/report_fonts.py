"""Eingebettete Berichtsschriften aus matplotlib 3.10.8 (Lizenzen unter fonts/)."""

from collections.abc import Iterator
from itertools import groupby
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import PDFDocument
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

REGULAR = "TED-Sans"
BOLD = "TED-Sans-Bold"
MATH = "TED-STIX"


class ReportFont(TTFont):
    def addObjects(self, doc: PDFDocument) -> None:
        # ReportLab 5.1 writes scalar hex values in ToUnicode. PDF requires UTF-16BE.
        corrections = {}
        for index, subset in enumerate(self.state[doc].subsets):
            changes = {}
            for slot, code in enumerate(subset):
                if code > 0xFFFF:
                    encoded = chr(code).encode("utf-16-be").hex().upper()
                    changes[f"<{slot:02X}> <{code:04X}>"] = f"<{slot:02X}> <{encoded}>"
            if changes:
                corrections[self.getSubsetInternalName(index, doc)[1:]] = changes
        super().addObjects(doc)
        for name, changes in corrections.items():
            stream = doc.idToObject[doc.idToObject[name].ToUnicode.name]
            for original, encoded in changes.items():
                stream.content = stream.content.replace(original, encoded)


def register_fonts() -> None:
    directory = Path(__file__).with_name("fonts")
    for name, filename in (
        (REGULAR, "DejaVuSans.ttf"),
        (BOLD, "DejaVuSans-Bold.ttf"),
        (MATH, "STIXGeneral.ttf"),
    ):
        pdfmetrics.registerFont(ReportFont(name, str(directory / filename)))
    pdfmetrics.registerFontFamily(REGULAR, normal=REGULAR, bold=BOLD)


def font_runs(text: str, preferred: str, field: str) -> Iterator[tuple[str, str]]:
    primary = pdfmetrics.getFont(preferred).face.charToGlyph
    fallback = pdfmetrics.getFont(MATH).face.charToGlyph

    def select(char: str) -> str:
        if primary.get(ord(char)):
            return preferred
        if fallback.get(ord(char)):
            return MATH
        raise ValueError(f"PDF-Schrift ohne Zeichen U+{ord(char):04X} in {field}")

    for name, chars in groupby(text, key=select):
        yield name, "".join(chars)


def apply_fonts(paragraph: Paragraph, field: str) -> None:
    fragments = []
    for fragment in paragraph.frags:
        if not fragment.text:  # Auch leere Sprungmarken erhalten.
            fragments.append(fragment)
            continue
        for name, text in font_runs(fragment.text, fragment.fontName, field):
            fragments.append(fragment.clone(fontName=name, text=text))
    paragraph.frags = fragments
