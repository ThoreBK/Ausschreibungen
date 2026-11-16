# Ausschreibungen suchen

Der Agent sucht öffentliche Ausschreibungen auf TED anhand eigener Suchbegriffe.
Aktuell verfügbar: Suche mit Titeln, Links und JSON-Ausgabe. Die automatische
Analyse, Bewertung und PDF-Berichte sind noch in Entwicklung.

## Einrichten und starten

Voraussetzung: Projektdateien, [uv](https://docs.astral.sh/uv/getting-started/installation/)
und eine Internetverbindung. Python wird bei Bedarf von `uv` heruntergeladen.
Ein API-Schlüssel oder eine `.env`-Datei ist derzeit nicht nötig.

PowerShell im Projektordner öffnen und ausführen:

```powershell
. .\dev.ps1
uv sync --locked
uv run main.py --search
```

`uv sync --locked` richtet die Abhängigkeiten ein. Für weitere Suchen genügt
`uv run main.py --search`; in einem neuen PowerShell-Fenster zuerst wieder
`. .\dev.ps1` laden. Ohne `--search` erscheint nur die Befehlsübersicht.

## Suche konfigurieren

[search-profile.toml](search-profile.toml) im Texteditor bearbeiten, speichern und
die Suche erneut starten. Standard: KI- und Microsoft-365-Themen, Auftraggeber
in Deutschland, letzte 90 Kalendertage, höchstens 20 Treffer.

Die allgemeinen Einstellungen stehen vor dem ersten `[[queries]]`-Block:

| Einstellung | Bedeutung / Beispiel |
| --- | --- |
| `name` | Frei wählbarer Name des Suchprofils. |
| `countries = ["DEU"]` | Ländercodes, z. B. `["DEU", "AUT"]`; `[]` für alle Länder. |
| `country_field = "buyer-country"` | Land des Auftraggebers; `"place-of-performance"` für den Leistungsort. |
| `days_back = 90` | Zeitraum in Kalendertagen einschließlich heute. |
| `max_results = 20` | 1–250 Treffer; begrenzt jede Suche und die gemeinsame Ergebnisliste. |
| `scope = "ACTIVE"` | Laut TED aktive Bekanntmachungen; `"ALL"` einschließlich historischer, `"LATEST"` nur aktuelle Amtsblattausgabe. |
| `language = "deu"` | Bevorzugte Sprache für Ergebnisse und Links; kein Sprachfilter und keine Übersetzung. |
| `cpv_codes = []` | Optionaler Filter mit exakten achtstelligen CPV-Codes (Auftragskategorien). |
| `timeout_seconds = 30` | Maximale Wartezeit je TED-Anfrage in Sekunden. |

### Suchbegriffe

Jeder `[[queries]]`-Block ist eine eigene Suche mit eindeutigem Namen:

```toml
[[queries]]
name = "Microsoft-Beratung und Schulung"
term_groups = [
    ["Microsoft 365", "Copilot"],
    ["Beratung", "Schulung"],
]
```

**Innerhalb einer Gruppe gilt ODER, zwischen den Gruppen UND.** Das Beispiel
findet also etwa „Copilot“ zusammen mit „Schulung“. Soll „Copilot“ allein genügen,
die zweite Gruppe entfernen. Alternative und englische Begriffe bei Bedarf ergänzen.

Mehrere Suchblöcke sind Alternativen; ihre Treffer werden zusammengeführt.
Die vier mitgelieferten Blöcke ersetzen oder entfernen, wenn nur eigene Themen
gewünscht sind. Mindestens ein Block mit einer nichtleeren Begriffsgruppe muss bleiben.
Anführungszeichen, Kommas und Klammern wie im Beispiel beibehalten; Suchbegriffe
dürfen keine zusätzlichen Anführungszeichen, Rückwärts-Schrägstriche oder Zeilenumbrüche enthalten.

### Andere Konfigurations- oder Ergebnisdatei verwenden

```powershell
uv run main.py --search --config meine-suche.toml --output reports/meine-ergebnisse.json
```

Mit `--as-of 2026-11-15` lässt sich optional der Stichtag für den Suchzeitraum
festlegen. Alle Optionen zeigt `uv run main.py --help`.

## Ergebnisse

Titel und Links erscheinen im Terminal. Zusätzlich enthält
`reports/ted-results.json` die Treffer, verwendeten Einstellungen und TED-Rohantworten.
**Eine erfolgreiche Suche überschreibt diese Datei**; frühere Ergebnisse bei Bedarf
vorher sichern oder `--output` verwenden. Bei Abruffehlern bleibt die bisherige Datei erhalten.

Die neuesten Bekanntmachungen stehen zuerst; bei erreichtem Trefferlimit ist die
Liste nur eine Auswahl. Fachliche Eignung, Angebotsfristen und vollständige
Vergabeunterlagen müssen selbst geprüft werden.

## Häufige Probleme

- **`uv` nicht gefunden:** `. .\dev.ps1` laden; auf einem neuen Rechner `uv` installieren.
- **Datei nicht gefunden:** PowerShell im Projektordner mit `main.py` und `search-profile.toml` öffnen.
- **Konfigurationsfehler:** Genannte Einstellung sowie Anführungszeichen, Kommas und Klammern prüfen.
- **TED-/HTTP-Fehler:** Internetverbindung prüfen und später erneut versuchen.
- **Keine Treffer:** Weniger Pflichtgruppen, mehr alternative Begriffe oder einen längeren Zeitraum verwenden.

Das fachliche Ziel und den geplanten Ablauf beschreibt [PROJECT.md](PROJECT.md).
