# Ausschreibungen suchen

Das Tool sucht öffentliche TED-Bekanntmachungen zu einem einstellbaren Unternehmensprofil.
Der PDF-Bericht zeigt passende Lose, Teilnahmefristen und die Belege aus dem Original.

## Einrichten und den ersten Bericht erstellen

Du brauchst [uv](https://docs.astral.sh/uv/getting-started/installation/), eine Internetverbindung
und für die KI-Auswertung die [Codex CLI](https://developers.openai.com/codex/cli) mit
ChatGPT-Anmeldung. Öffne PowerShell im Projektordner. Einmalig einrichten:

~~~powershell
. .\dev.ps1
uv sync --locked
codex login
~~~

Für jeden Bericht im Projektordner starten:

~~~powershell
. .\dev.ps1
uv run main.py report
~~~

Öffne die am Ende angezeigte **bericht.pdf**. Für eine reine TED-Suche ohne KI
verwende `uv run main.py search`. Mit `uv run main.py report --structured-only` entsteht ein PDF aus den
strukturierten XML-Angaben. Die thematische Passung bleibt dabei ungeklärt.

## Suchbegriffe und Profil anpassen

Bearbeite [search-profile.toml](search-profile.toml) im Texteditor. Standardmäßig sucht
das Tool für Auftraggeber in Deutschland über die letzten 90 Tage. Jeder
`[[queries]]`-Block ist eine eigene Suche mit einem eindeutigen Namen.

~~~toml
[[queries]]
name = "Microsoft-Beratung und Schulung"
term_groups = [
    ["Microsoft 365", "Copilot"],
    ["Beratung", "Schulung"],
]
~~~

Innerhalb einer Gruppe gilt **ODER**, zwischen den Gruppen **UND**. Das Beispiel
findet etwa „Copilot“ zusammen mit „Schulung“. Soll „Copilot“ allein genügen,
entferne die zweite Gruppe. Mehrere Suchblöcke liefern alternative Treffer.
Ersetze die mitgelieferten Blöcke für eine eigene Suche. Mindestens ein Block mit
einer nichtleeren Begriffsgruppe muss bleiben.

| Einstellung | Wirkung |
| --- | --- |
| `countries`, `country_field` | `["DEU", "AUT"]` für Deutschland und Österreich, `[]` für alle Länder. `buyer-country` filtert nach Auftraggeberland, `place-of-performance` nach Leistungsort. |
| `days_back` | Suchzeitraum in Kalendertagen einschließlich Stichtag. |
| `max_results` | 1–250 Bekanntmachungen je Suchgruppe. Bei `search` gilt das Limit auch für die gemeinsame Kandidatenliste. |
| `report_limit` | 1–250 Lose oder Verfahren nach fachlicher Auswahl und Sortierung. Für höchstens fünf Lose oder Verfahren auf `5` setzen. |
| `scope`, `language` | `ACTIVE` für laut TED aktive Bekanntmachungen, `ALL` einschließlich historischer, `LATEST` für die aktuelle Amtsblattausgabe. Die Sprache steuert die bevorzugten Ergebnisfelder und Links. |

Beschreibe in [analysis-profile.toml](analysis-profile.toml) unter `company_profile`
die angebotenen Leistungen. Die KI verwendet dieses Profil zur Passungsprüfung.
Die Suchbegriffe auf TED werden separat im Suchprofil gepflegt.

## Ergebnisse lesen

- **bericht.pdf** beginnt mit der Übersicht. Offene Fristen stehen zuerst, innerhalb
  dieser Gruppe folgen belegte Passung und die nächste eindeutige Einreichungsfrist.
  Die Nummern in den Steckbriefen führen zu Originalzitaten und XML-Fundstellen.
- **overview.html** zeigt Suchprofil, Suchgruppen, Kandidaten, Abruffehler und
  gespeicherte Originale. Bei `search` erscheint der Pfad im Terminal.
- **analysis.html** zeigt auch ausgeschlossene Einträge, frühere zugeordnete
  Dokumentstände und Treffer außerhalb des Berichtslimits. Fehlende Angaben,
  Unsicherheiten und Widersprüche sind gekennzeichnet.

Jeder Lauf liegt standardmäßig unter `reports/runs/`. Dort bleiben das Suchprofil,
die TED-Rohantworten in `results.json` und die Originale erhalten. Die Analyse liegt
unter `analyses/` im jeweiligen Lauf. Ein unvollständiger Lauf meldet Exitcode 1.
Auch bei einzelnen Abruffehlern bleiben erfolgreiche Ergebnisse verfügbar.

Um einen gespeicherten Lauf erneut zu analysieren, ersetze `LAUFORDNER` durch den
tatsächlichen Namen. Ohne `--notice` werden alle Bekanntmachungen des Laufs ausgewertet.

~~~powershell
uv run main.py analyze reports/runs/LAUFORDNER --notice 773064-2026
~~~

Für ein anderes Suchprofil verwende bei `search` oder `report` die Option `--config DATEI`.
Mit `--as-of YYYY-MM-DD` legst du den Suchstichtag fest. Für ein anderes Unternehmensprofil
verwende bei `report` oder `analyze` die Option `--analysis-config DATEI`.

Mit `uv run main.py report --output-dir meine-berichte` landen die Laufarchive unter
`meine-berichte/runs/`. Bei vollständiger TED-Suche liegt die aktuelle Ergebniskopie
daneben als `meine-berichte/ted-results.json`. Das Terminal zeigt den PDF-Pfad im Laufarchiv.

`uv run main.py --help` zeigt die drei Befehle. Ihre Optionen findest du zum Beispiel mit
`uv run main.py analyze --help`. Vorhandene Aufrufe mit `--report`, `--search` oder
`--analyze` funktionieren weiterhin. Bei `search` und `report` unterstützt `--output DATEI`
weiterhin einen eigenen Dateinamen für die JSON-Kopie.

## Kosten und Grenzen

Die KI-Auswertung sendet die vollständigen Bekanntmachungstexte und das konfigurierte
Unternehmensprofil über die eigene ChatGPT-Anmeldung an OpenAI. Der Lauf verbraucht
Kontingent oder vorhandenes Guthaben. Die Schätzung beträgt **0 USD zusätzliche
API-Gebühren** bei Nutzung des bestehenden Kontos, ohne anteiligen Abopreis. Die
Generalprobe benötigte für fünf Bekanntmachungen zehn Modellaufrufe mit zusammen
312.007 Eingabe- und 47.287 Ausgabetokens. Den Verbrauch deines Laufs findest du in
`analysis.json`. [Abgabenachweis](demo/abgabenachweis.md) ·
[Codex-Nutzung nach Tarif](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)

- Grundlage sind die erfolgreich abgerufenen TED-Bekanntmachungen. Zusätzliche
  Vergabeunterlagen sind verlinkt und werden in dieser Version nicht ausgewertet.
- Suchbereich, Trefferlimit und unterstützte XML-Formate begrenzen die Abdeckung.
  Fehlende Vorgänger einer Berichtigung erscheinen als offene Prüfpunkte.
- Die KI prüft vorgeschlagene Aussagen gegen die Quellen. Auch bestätigte Deutungen
  können falsch sein. Eine offene Frist sagt nichts über die Erfüllung der
  Teilnahmevoraussetzungen aus. Die Teilnahmeentscheidung bleibt beim Menschen.

Für die Weiterverwendung gelten die [TED-Nutzungshinweise](https://ted.europa.eu/en/legal-notice).
Suchen möglichst nacheinander starten, um die Abrufgrenzen des
[öffentlichen TED-Zugangs](https://ted.europa.eu/en/simap/developers-corner-for-reusers) einzuhalten.

## Hilfe bei Problemen

| Problem | Was hilft |
| --- | --- |
| `uv` oder Projektdatei fehlt | PowerShell im Ordner mit `main.py` öffnen und `. .\dev.ps1` laden. Bei Bedarf `uv` installieren. |
| Ungültiges Profil oder keine Treffer | Bei Konfigurationsfehlern die genannte Einstellung und TOML-Schreibweise prüfen. Bei leeren Ergebnissen Pflichtgruppen reduzieren, Begriffe ergänzen oder den Zeitraum verlängern. |
| TED-Abruffehler | Betroffene Suchgruppe oder Bekanntmachung in `overview.html` prüfen. Bei Verbindungsproblemen später erneut starten. |
| Analyse unvollständig | Den konkreten Hinweis in `analysis.html` prüfen. Bei Anmelde- oder Kontingentproblemen helfen `codex login status` und die Kontoprüfung. Sehr große Bekanntmachungen können die Modellgrenze überschreiten. |

[Demo mit Beispielprofil](demo/README.md) · [Projektziel und fachliche Entscheidungen](PROJECT.md)
