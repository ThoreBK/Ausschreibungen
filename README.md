# Ausschreibungen suchen

Der Agent sucht öffentliche Ausschreibungen auf TED anhand eigener Suchbegriffe.
Die Suche speichert vollständige TED-Bekanntmachungen samt Herkunft in getrennten
Läufen. Eine lokale HTML-Übersicht und Lesekopien machen die Ergebnisse prüfbar.
Die fachliche Analyse, Bewertung und PDF-Berichte sind noch in Entwicklung.

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

Die übrigen Einstellungen können für den ersten Lauf unverändert bleiben.

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

Titel, Links, Abrufstatus und der Pfad zur Übersicht erscheinen im Terminal.
**Zum Prüfen die dort genannte `overview.html` im Browser öffnen.** Das geht auch
nach Programmende und ohne Internet. Die Übersicht zeigt Suchprofil, Grenzen,
Suchgruppen sowie für jeden Kandidaten Herkunft und Abrufstatus.

Jeder Lauf bleibt in einem eigenen Ordner unter `reports/runs/` erhalten,
zusammen mit dem verwendeten Profil und den heruntergeladenen Bekanntmachungen.
Auch bei einzelnen Abruffehlern bleiben erfolgreiche Ergebnisse gespeichert.
Fehler und offene Prüfpunkte stehen in der Übersicht; bei einem Abbruch die
Übersicht des betreffenden Laufs prüfen.

## Wichtige Grenzen

- Die Treffer sind eine Vorauswahl. Fachliche Eignung und offene Teilnahme sind
  noch ungeprüft; auch Ergebnisbekanntmachungen können enthalten sein.
- Bei erreichtem Trefferlimit zeigt die Liste nur einen Ausschnitt. Ein vollständig
  abgerufener Lauf bedeutet keine vollständige Abdeckung aller Ausschreibungen.
- Zusätzliche Vergabeunterlagen werden **nicht heruntergeladen oder ausgewertet**.
  Vorhandene Unterlagenlinks lassen sich in der Übersicht öffnen.
- Nicht alle älteren Bekanntmachungsformate werden unterstützt. Fehlgeschlagene
  oder fehlende Abrufe sind in der Übersicht gekennzeichnet.

TED stellt einen [öffentlichen Such- und Downloadzugang](https://ted.europa.eu/en/simap/developers-corner-for-reusers)
bereit, den das Tool verwendet. Bei einer
Weiterverwendung der Inhalte die [TED-Nutzungshinweise](https://ted.europa.eu/en/legal-notice)
beachten. Mehrere Suchen möglichst nacheinander starten, um die TED-Abrufgrenzen
einzuhalten.

## Häufige Probleme

- **`uv` nicht gefunden:** `. .\dev.ps1` laden; auf einem neuen Rechner `uv` installieren.
- **Datei nicht gefunden:** PowerShell im Projektordner mit `main.py` und `search-profile.toml` öffnen.
- **Konfigurationsfehler:** Genannte Einstellung sowie Anführungszeichen, Kommas und Klammern prüfen.
- **TED-/HTTP-Fehler:** Internetverbindung prüfen und später erneut versuchen.
- **Keine Treffer:** Weniger Pflichtgruppen, mehr alternative Begriffe oder einen längeren Zeitraum verwenden.

Das fachliche Ziel und den geplanten Ablauf beschreibt [PROJECT.md](PROJECT.md).
