# Kurzdokumentation zum Ausschreibungsagenten

Der Agent durchsucht das europäische Vergabeportal TED mit den Suchbegriffen, die
du festlegst. Im PDF siehst du, welche Aufträge zu deinem Unternehmensprofil passen,
welche Fristen gelten und wo du die Angaben in der Bekanntmachung findest.

## Den ersten Bericht erstellen

Du brauchst eine Internetverbindung, uv und für die KI-Auswertung die Codex CLI
mit eigener ChatGPT-Anmeldung. [uv installieren](https://docs.astral.sh/uv/getting-started/installation/) · [Codex CLI installieren](https://developers.openai.com/codex/cli)

1. Öffne PowerShell im Projektordner und führe zur einmaligen Einrichtung diese Befehle aus.

   ~~~powershell
   cd technik
   . .\dev.ps1
   uv sync --locked
   codex login
   ~~~

2. Doppelklicke im Projektordner auf **Ausschreibungen starten.cmd**. Lass das
   Startfenster geöffnet. Im Browser kannst du unter **Profil bearbeiten** die
   Suchbegriffe und das Unternehmensprofil anpassen.
3. Klicke auf **Recherche starten** und nach dem Lauf auf **PDF öffnen**.
   Der Bericht beginnt mit einer Übersicht. Danach folgen Steckbriefe und Belege.
   Zum Beenden das Startfenster schließen.

Für einen kleinen Beispiellauf in PowerShell verwende im Ordner `technik`
`uv run main.py report --config nachweise/generalprobe/suchprofil.toml`. Das Terminal zeigt den
PDF-Pfad.

## Aufbau und Entscheidungen

Oberfläche und Kommandozeile starten denselben Ablauf. Der Einstieg im Code ist
die Funktion `generate_report`. [main.py](technik/main.py)

1. **Treffer suchen und speichern.** Für jeden Lauf legt der Agent unter
   `Berichte/runs/` einen Ordner an. Gibt es im Projekt bereits den Ordner
   `reports/`, verwendet der Agent weiterhin `reports/runs/`. Dort speichert er die Suchergebnisse in
   `results.json` und die vollständigen Bekanntmachungen als XML-Dateien.
   Bei Mehrfachtreffern speichert er das Original einmal und vermerkt alle Suchgruppen.
2. **Angaben auslesen und prüfen.** Fristen und andere strukturierte Angaben liest
   der Agent direkt aus dem XML. Das Sprachmodell liest die Leistungsbeschreibung,
   vergleicht sie mit deinem Unternehmensprofil und nennt die Textstellen, auf die
   es seine Einschätzung stützt. In einem zweiten Schritt prüft das Modell jede
   Aussage anhand der zitierten Passage.
3. **Lose für den Bericht auswählen.** Ein Auftrag kann in mehrere Teilaufträge
   (Lose) mit eigenen Leistungen und Fristen aufgeteilt sein. Der Agent bewertet
   jedes Los einzeln. Ohne Losaufteilung bewertet er den gesamten Auftrag.
   Du legst fest, wie viele Treffer höchstens im PDF erscheinen. Diese Obergrenze
   wendet der Agent nach der Auswahl und Sortierung an. Alle Treffer bleiben im
   Laufordner einsehbar. [Auswahl](technik/ausschreibungen/selection.py)

## Grenzen

Die Recherche deckt TED im eingestellten Zeitraum und bis zum Trefferlimit ab.
Der Agent wertet die Bekanntmachung aus und verlinkt zusätzliche Dokumente wie
das Leistungsverzeichnis. Steht nur dort, welche Referenzen ein Bieter vorlegen
muss, fehlen diese Anforderungen im Bericht. Das Modell kann außerdem eine
Textstelle falsch verstehen. Prüfe bei einem interessanten Los deshalb die
zitierten Passagen und die zusätzlichen Unterlagen, bevor du über eine Teilnahme
entscheidest. Das Angebot reichst du selbst ein.

## Was kostet ein Lauf?

Bei einem Beispiellauf mit fünf Bekanntmachungen verbrauchten Auswertung und
Gegenprüfung in zehn Modellaufrufen **312.007 Eingabetokens und 47.287
Ausgabetokens**. Der Agent und die Codex CLI laufen auf deinem Rechner. Die CLI
ruft das Modell bei OpenAI über deine ChatGPT-Anmeldung auf, ohne separaten
API-Schlüssel. Den Tokenverbrauch deines eigenen Laufs findest du in
`analysis.json` im Analyseordner.

## Hilfe bei Problemen

- **Die Oberfläche startet nicht.** Die Meldung im Startfenster nennt den Fehler.
  Fehlt `uv`, installiere es über den Link oben. Bei Anmeldeproblemen prüfe
  den Zugang mit `codex login status`.
- **Die Suche findet keine Treffer.** Öffne **Profil bearbeiten**, erweitere den
  Zeitraum oder entferne eine zu enge Pflichtgruppe.
- **Der Lauf ist unvollständig.** Öffne die Laufdetails im Browser. Die
  `overview.html` im Laufordner zeigt Abruffehler, die `analysis.html` im
  Analyseordner zeigt offene Punkte der Auswertung.

[Generalprobe mit Beispielprofil](technik/nachweise/generalprobe/README.md) ·
[Zusammenarbeit mit dem Coding-Agenten](technik/nachweise/generalprobe/zusammenarbeit.md)
