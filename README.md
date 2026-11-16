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

Titel, Links, Abrufstatus und der Pfad zur Übersicht erscheinen im Terminal.
**Zum Prüfen die dort genannte `overview.html` im Browser öffnen.** Das geht auch
nach Programmende und ohne Internet. Die Übersicht zeigt Suchprofil, Grenzen,
Suchgruppen sowie für jeden Kandidaten Herkunft und Abrufstatus.

Jeder Lauf erhält einen eigenen Ordner unter `reports/runs/<Laufkennung>/`:

| Datei | Inhalt |
| --- | --- |
| `overview.html` | Lesbare Übersicht; Links zu Originalen und lokalen Lesekopien. |
| `profile.toml` | Kopie der für diesen Lauf verwendeten Konfigurationsdatei. |
| `results.json` | Einstellungen, tatsächliche Anfragen, TED-Rohantworten, Treffer und Fehler. |
| `documents/<Nummer>.xml` | Unveränderte vollständige Bekanntmachung. |
| `documents/<Nummer>.html` | Lesekopie der XML-Textwerte mit Fundstellen, ohne fachliche Interpretation. |
| `documents/<Nummer>.response` | Erhaltene, aber bei der Dokumentprüfung verworfene Antwort, sofern vorhanden. |

Frühere Laufordner werden nicht überschrieben. Erfolgreiche Suchgruppen und
Dokumentabrufe bleiben auch erhalten, wenn andere Abrufe scheitern. Nach jeder
Suchgruppe und jedem Dokument wird ein Zwischenstand gespeichert. Bei einem harten
Prozessabbruch kann die letzte Anfrage fehlen; der letzte gespeicherte Stand bleibt
als nicht abgeschlossener Lauf erkennbar.

`reports/ted-results.json` bleibt als zusätzliche aktuelle Ergebniskopie erhalten.
Sie wird nur aktualisiert, wenn alle Suchgruppen erfolgreich waren; sie kann trotzdem
Dokumentfehler enthalten. `run_directory` verweist auf den zugehörigen Laufordner.
Mit `--output reports/meine-ergebnisse.json` ändern sich Name und übergeordneter
Ordner dieser Kopie; die Laufordner liegen jeweils im benachbarten Unterordner `runs`.

Ein leerer erfolgreicher Lauf heißt `empty`, ein Lauf mit vollständig abgerufenen
Kandidaten `complete`. `incomplete` kennzeichnet Such-/Dokumentfehler, fehlende
XML-Links oder ungeklärte abweichende Suchangaben. Das Trefferlimit wird separat
angezeigt: Auch `complete` verspricht keine vollständige Marktabdeckung.
Bei Such- oder Dokumentabruffehlern endet der Befehl mit Rückgabecode 1. Fehlende
Links und ungeklärte Angaben werden im Laufstatus angezeigt; sie sind keine
technischen Abruffehler und führen allein nicht zu einem Fehlercode.

Die neuesten Bekanntmachungen stehen zuerst; bei erreichtem Trefferlimit ist die
Liste nur eine Auswahl. Gleiche Veröffentlichungsnummern werden zusammengeführt;
Suchherkünfte und abweichende Angaben bleiben erhalten. Verschiedene Bekanntmachungen
eines Verfahrens bleiben getrennt. Fachliche Eignung und offene Teilnahme sind
ungeprüft; auch Ergebnisbekanntmachungen können Kandidaten sein.

Zusätzliche Vergabeunterlagen werden **nicht heruntergeladen und nicht ausgewertet**.
Strukturierte Unterlagenlinks aus der Bekanntmachung bleiben mit ihren Losbezügen
erhalten. Sonstige Verweise, etwa im Freitext, bleiben im Original und der Lesekopie
sichtbar; eine umfassende fachliche Extraktion folgt in TASK-4.

## Aufbau und bewusste Grenzen

`ted.py` liest das Profil und sucht Kandidaten. `notices.py` lädt und prüft
Bekanntmachungen. `research.py` speichert Läufe und erzeugt die lokale Übersicht;
`main.py` verbindet diese Schritte. Es gibt keine zusätzlichen Laufzeitabhängigkeiten.

Die Dokumentprüfung unterstützt eForms-XML für `ContractNotice`,
`ContractAwardNotice` und `PriorInformationNotice`. Sie prüft Lesbarkeit, Dokumentart
und die Veröffentlichungsnummer der eigenen Bekanntmachung; sie ist keine vollständige
XML-Schema- oder Inhaltsprüfung. Andere Formate, fehlende Identität und abweichende
Nummern werden sichtbar zurückgewiesen. Die erhaltenen Antwortbytes bleiben gespeichert.
Historische TED-Schemaformulare werden noch nicht erschlossen. XML-DTDs werden nicht
verarbeitet; externe Inhalte werden in den HTML-Lesekopien nur als Text dargestellt.

Originaldateien, SHA-256-Prüfsummen, Abrufzeit, Quell-/Zieladresse sowie vorhandene
Verfahrens-, Los- und Versionskennungen stehen je Dokument in `results.json`.
Nur aktuelle Versionen laut TED-Suche werden angefragt; frühere Verfahrensstände
werden nicht automatisch nachgeladen. Ein erneuter Live-Lauf kann andere Treffer liefern.

## Öffentlicher TED-Zugang und Nutzung

Geprüft am 16.11.2026 für P-01/P-10:

- Die [offizielle Search-API-Dokumentation](https://docs.ted.europa.eu/api/latest/search.html)
  erlaubt den anonymen Abruf veröffentlichter Bekanntmachungen zur Analyse und Wiederverwendung.
  Verwendet wird ausschließlich `POST https://api.ted.europa.eu/v3/notices/search`.
- Die [TED-Dokumentation für Datennutzer](https://ted.europa.eu/en/simap/developers-corner-for-reusers)
  beschreibt den öffentlichen XML-Direktdownload. Das Tool ruft nur die zu den Kandidaten
  gehörenden TED-XML-Adressen ab und lehnt Weiterleitungen auf fremde Hosts ab.
  Die dort genannten Grenzen sind 600 Ansichten/Downloads in sechs Minuten und
  700 HTTP-Anfragen pro Minute. Anfragen laufen seriell mit mindestens 0,65 Sekunden
  Pause; mehrere parallel gestartete Prozesse teilen sich diese Begrenzung nicht.
- Laut [TED-Nutzungshinweisen](https://ted.europa.eu/en/legal-notice) dürfen veröffentlichte
  Bekanntmachungen grundsätzlich kommerziell und nichtkommerziell wiederverwendet werden,
  sofern nichts anderes angegeben ist. Rechte Dritter und besondere Hinweise bleiben
  zu beachten. Die Übersicht nennt TED als Quelle und unterscheidet unveränderte
  Originale von erzeugten Lesekopien. Dies erteilt keine Rechte an zusätzlichen Unterlagen.

Es werden keine Zugangsdaten benötigt oder gespeichert. Laufdaten bleiben lokal unter
dem bereits von Git ausgeschlossenen Ordner `reports`. Pro Dokument gilt ein Limit
von 20 MiB; Überschreitungen und HTTP-Fehler werden gemeldet, nicht automatisch umgangen.

## Tests und Nachweise für Task 2

Der mit dem Nutzer vereinbarte Testkatalog T2-01 bis T2-08 steht verbindlich in TASK-2.
`tests/test_research.py` setzt diese Fälle mit festen Netzwerkantworten um; Suche,
Auswahl, Prüfung und Speicherung laufen dabei tatsächlich. T2-08 startet einen eigenen
Programmprozess und prüft danach Übersicht, Lesekopie, Original und lokale Links.
Die ursprünglichen Tests bleiben unverändert. Änderungen an den vereinbarten
Testfällen oder Erwartungen erfordern vorherige Nutzerfreigabe.

Die Live-Abnahme vom 16.11.2026 lieferte mit dem Standardprofil 20 gespeicherte
Bekanntmachungen. Ein separates Profil mit `Copilot UND Schulung`, 30 Tagen und
höchstens drei Treffern lieferte eine Bekanntmachung. Die konkreten Laufdaten
liegen lokal unter `reports/runs`; sie sind keine fest eingebauten Anwendungstreffer.
Die Auswertung von Pflichtangaben und fachlicher Passung folgt erst in TASK-4.

## Häufige Probleme

- **`uv` nicht gefunden:** `. .\dev.ps1` laden; auf einem neuen Rechner `uv` installieren.
- **Datei nicht gefunden:** PowerShell im Projektordner mit `main.py` und `search-profile.toml` öffnen.
- **Konfigurationsfehler:** Genannte Einstellung sowie Anführungszeichen, Kommas und Klammern prüfen.
- **TED-/HTTP-Fehler:** Internetverbindung prüfen und später erneut versuchen.
- **Keine Treffer:** Weniger Pflichtgruppen, mehr alternative Begriffe oder einen längeren Zeitraum verwenden.

Das fachliche Ziel und den geplanten Ablauf beschreibt [PROJECT.md](PROJECT.md).
