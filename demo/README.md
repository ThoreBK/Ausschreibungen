# Demo und Abgabe

Die Demo recherchiert öffentliche Ausschreibungen für eine KI- und Microsoft-365-Beratung.
Sie liefert eine Vorauswahl mit Belegen. Der Mensch entscheidet über die weitere
Prüfung und eine mögliche Teilnahme.

## Einrichtung und Start

Im Projektordner PowerShell öffnen. Benötigt werden Internetzugang,
[uv](https://docs.astral.sh/uv/getting-started/installation/) und für die Auswertung
[Codex CLI](https://developers.openai.com/codex/cli) mit einer eigenen ChatGPT-Anmeldung.

~~~powershell
. .\dev.ps1
uv sync --locked
codex login status
uv run main.py --report --config demo/suchprofil.toml
~~~

Falls die Anmeldung fehlt, einmal `codex login` ausführen. Den am Ende angezeigten
PDF-Pfad öffnen. Die gespeicherte `overview.html` zeigt TED-Abfragen und
Originale, die `analysis.html` zusätzlich Belege und ausgeschlossene Fälle.
Mit `--as-of 2026-11-21` lässt sich der Suchzeitraum der Generalprobe erneut
abfragen. Die archivierten Eingaben und Ergebnisse halten den ursprünglichen
Stand fest. Bei neuen Läufen können sich TED-Treffer und Modellausgaben ändern.

Das Demoprofil begrenzt die Treffermenge und enthält einen Kontrollfall mit
thematisch nebensächlichem Suchwort. Für die gewöhnliche Recherche verwendet
`uv run main.py --report` das breitere Standardprofil. Wie man Suchbegriffe und
Grenzen im Texteditor anpasst, steht in der [Anleitung](../README.md).

## Aufbau und Entscheidungen

Für die Demo eignet sich der `--report`-Pfad in [main.py](../main.py).
Dort sammelt `collect` die TED-Ergebnisse und Originale, `analyze_run`
wertet sie aus und `write_report` erzeugt das PDF. Die Auswahl in
[selection.py](../ausschreibungen/selection.py) arbeitet je Los oder Verfahren.

- **Belegbarkeit.** Das Programm übernimmt eindeutig strukturierte XML-Angaben
  mit Fundstellen. Das Modell interpretiert Freitext und Passung. Eine zweite
  Anfrage prüft, ob die Quellen die vorgeschlagenen Aussagen tragen.
- **Nachvollziehbare Auswahl.** Die Suche führt sichere Mehrfachtreffer zusammen
  und bewahrt ihre Herkunft. Die Übersicht unterscheidet thematische Passung,
  Teilnahmestand und Voraussetzungen. Das Berichtslimit greift nach der Auswahl.
- **Begrenzte Recherche.** Die Auswertung verwendet vollständige TED-Bekanntmachungen.
  Zusätzliche Vergabeunterlagen werden verlinkt. Fehlende Zeitbestandteile
  werden offengelegt. Die Teilnahmeentscheidung bleibt beim Menschen.

TED-Suche und Download benötigen keine Zugangsdaten. Die KI-Auswertung übermittelt
öffentliche Bekanntmachungstexte und das Unternehmensprofil an OpenAI. Für das
Profil genügen zur Veröffentlichung geeignete Leistungsbeschreibungen. Die
Anmeldung erfolgt über das persönliche Codex-Konto. Die Anleitung dokumentiert
Zugang, Nutzungsgrundlage und Grenzen.

Pro Lauf fallen ungefähr **0 USD zusätzliche API-Gebühren** an. Der Lauf
verbraucht das bestehende ChatGPT-Kontingent oder gegebenenfalls vorhandene
Guthaben. Die Schätzung enthält keinen anteiligen Abopreis.

[Abgabenachweis](abgabenachweis.md) · [Zusammenarbeit mit dem Coding-Agenten](zusammenarbeit.md)
