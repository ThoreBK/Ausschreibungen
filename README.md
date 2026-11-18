# Ausschreibungen suchen

Der Agent sucht öffentliche Ausschreibungen auf TED anhand eigener Suchbegriffe.
Die Suche speichert vollständige TED-Bekanntmachungen samt Herkunft in getrennten
Läufen. Eine lokale HTML-Übersicht und Lesekopien machen die Ergebnisse prüfbar.
Gespeicherte Bekanntmachungen können anschließend mit belegten Pflichtangaben und
einer KI-Einschätzung der thematischen Passung ausgewertet werden.

## Von der Suche zum PDF

Nach der Einrichtung und der ChatGPT-Anmeldung (`codex login`) im Projektordner starten:

```powershell
. .\dev.ps1
uv run main.py --report
```

Für einen Lauf mit höchstens fünf Bekanntmachungen in `search-profile.toml`
`max_results = 5` setzen. Das Programm sucht live auf TED, lädt die Originale,
wertet die gefundenen Bekanntmachungen aus und zeigt den Pfad zu **bericht.pdf**.
Bei der KI-Auswertung werden die Bekanntmachungstexte und das konfigurierte
Unternehmensprofil über die bestehende ChatGPT-Anmeldung an OpenAI gesendet.
Mit `--report --structured-only` bleibt die Auswertung lokal und die Passung ungeklärt.

Die erste Übersicht zeigt je Los die fachliche Passung, den Teilnahmestand und den
Stand der Teilnahmevoraussetzungen. Danach folgen Pflichtangaben und Prüfpunkte.
Nummern in eckigen Klammern führen zum Belegverzeichnis der jeweiligen Bekanntmachung.
Der Laufordner enthält die Originale. Auch eine erfolgreiche Suche ohne Treffer
und ein unvollständiger Abruf erzeugen einen Bericht. Bei unvollständiger Recherche
oder Analyse meldet das Programm Exitcode 1.

## Einrichten und starten

Voraussetzung: Projektdateien, [uv](https://docs.astral.sh/uv/getting-started/installation/)
und eine Internetverbindung. Python wird bei Bedarf von `uv` heruntergeladen.
Die Suche benötigt keinen API-Schlüssel. Die KI-Auswertung verwendet dein bestehendes
ChatGPT-Konto über die offizielle Codex-Schnittstelle.

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

## Gespeicherten Lauf analysieren

In [analysis-profile.toml](analysis-profile.toml) beschreibt `company_profile` die
angebotenen Leistungen. Änderungen wirken auf die nächste Passungsprüfung;
die Suchbegriffe werden weiterhin separat in `search-profile.toml` gepflegt.
Das mitgelieferte Profil entspricht dem fachlichen Unternehmensprofil in PROJECT.md.

Für KI-Auswertungen einmal mit `codex login` bei ChatGPT anmelden, falls du noch
nicht angemeldet bist. Die Codex-Desktop-App stellt diesen Befehl auf diesem Rechner
bereits bereit; alternativ die [Codex CLI installieren](https://developers.openai.com/codex/cli).
`codex login status` zeigt die Anmeldeart. API-Anmeldung ist im Programm gesperrt;
es gibt keinen kostenpflichtigen API-Fallback. Eine `.env`-Datei wird nicht benötigt
oder gelesen. Die vollständigen Bekanntmachungstexte und das Unternehmensprofil
werden über Codex an OpenAI gesendet.

Den Laufordner aus der Suchausgabe einsetzen, optional auf einen Treffer begrenzen:

```powershell
uv run main.py --analyze reports/runs/LAUFORDNER --notice 773064-2026
```

Ohne `--notice` werden alle gespeicherten Treffer ausgewertet. Mit
`--analysis-config anderes-profil.toml` ein anderes Analyseprofil verwenden.
`--structured-only` liest ausschließlich strukturierte XML-Angaben ohne Modellzugriff;
die fachliche Auswertung bleibt dabei ausdrücklich unvollständig.

Jede Analyse liegt unter `LAUFORDNER/analyses/` in einem eigenen Ordner.
`analysis.html` lokal öffnen; `analysis.json` enthält alle Pflichtfelder, Originalzitate,
XML-Fundstellen, Losbezüge, Herkunft und Dokumentstände für die spätere Berichterstellung.
Profil, Modellanfragen, Antworten und Tokenverbrauch bleiben im Analyseordner erhalten.
Fehlende Angaben heißen **nicht angegeben**; Unsicherheiten, Widersprüche,
abgelehnte Aussagen und Verarbeitungsfehler sind getrennt sichtbar. Ein unvollständiger
Lauf liefert Exitcode 1 und bewahrt seine bisherigen Ergebnisse.

Die KI interpretiert Freitext und Passung; ein zweiter Modellaufruf prüft die
inhaltliche Stützung. Zusätzlich prüft das Tool Zitate, Fundstellen und Losbezug.
Auch bestätigte KI-Interpretationen können falsch sein und benötigen fachliche Kontrolle.
Thematische Passung ist keine Teilnahmeempfehlung. Unternehmensnachweise werden nicht
geprüft. „Frist offen“ bedeutet nur: Aufruf zur Teilnahme mit eindeutig datierter,
noch nicht abgelaufener Einreichungsfrist. Fehlende Zeitbestandteile werden nicht ergänzt.

Kostenbasis (17.11.2026): Die Analyse nutzt das vorhandene ChatGPT-Kontingent und
verursacht **0 USD zusätzliche API-Kosten**. Ein vorhandener Abopreis wird nicht
auf einzelne Läufe umgerechnet; Tarifgrenzen und gegebenenfalls bereits vorhandene
Nutzungsguthaben gelten weiterhin. Es werden keine Guthaben gekauft.
[Codex mit ChatGPT verwenden](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan).
Je Bekanntmachung erfolgen eine gemeinsame Analyse aller Lose und, bei prüfpflichtigen
Aussagen, eine gemeinsame Gegenprüfung. Ergebnisse und Belege bleiben je Los getrennt.
Kurze Quellenkennungen werden lokal in Originalzitate und XML-Fundstellen aufgelöst.
Die Gegenprüfung erhält alle Originalquellen und die prüfpflichtigen Aussagen.
Die bereits daraus abgeleiteten Ergebnisfelder werden nur in der Erstanalyse übergeben.
Das tatsächliche Modell, die Anmeldeart und der
Tokenverbrauch stehen in `analysis.json`; unbekannter Verbrauch bleibt gekennzeichnet.
`model = "default"` verwendet das für dein Konto angebotene Standardmodell.

## Wichtige Grenzen

- Die Suchtreffer sind eine Vorauswahl; auch Ergebnisbekanntmachungen können
  enthalten sein. Erst die Analyse prüft Passung und interpretierbare Fristen.
- Bei erreichtem Trefferlimit zeigt die Liste nur einen Ausschnitt. Ein vollständig
  abgerufener Lauf bedeutet keine vollständige Abdeckung aller Ausschreibungen.
- Zusätzliche Vergabeunterlagen werden **nicht heruntergeladen oder ausgewertet**.
  Vorhandene Unterlagenlinks lassen sich in der Übersicht öffnen.
- Nicht alle älteren Bekanntmachungsformate werden unterstützt. Fehlgeschlagene
  oder fehlende Abrufe sind in der Übersicht gekennzeichnet.
- Sehr große Analysepakete können die Modellgrenze überschreiten. Das wird als
  Verarbeitungsfehler ausgegeben; eine gekürzte Fassung gilt nicht als vollständige Analyse.

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
- **Analyse unvollständig:** `analysis.html` prüfen. `codex login status`,
  ChatGPT-Anmeldung, Modellzugang und verbleibendes Kontingent kontrollieren;
  Originale bleiben erhalten. Bei erschöpftem Kontingent später erneut starten.
- **Keine Treffer:** Weniger Pflichtgruppen, mehr alternative Begriffe oder einen längeren Zeitraum verwenden.

Der Programmcode liegt in `ausschreibungen/`, der Einstieg bleibt `main.py`.
`tests/` enthält Tests und feste Beispieldaten, `reports/` die lokal erzeugten
Ergebnisse und `tmp/` temporäre Arbeits- und Review-Dateien.

Das fachliche Ziel und den geplanten Ablauf beschreibt [PROJECT.md](PROJECT.md).
