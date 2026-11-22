# Kurzdokumentation zum Ausschreibungsagenten

Der Agent durchsucht das europäische Vergabeportal TED mit den Suchbegriffen, die
du festlegst. Im PDF siehst du, welche Aufträge zu deinem Unternehmensprofil passen,
welche Fristen gelten und wo du die Angaben in der Bekanntmachung findest.

## Den ersten Bericht erstellen

Du brauchst eine Internetverbindung, uv und für die KI-Auswertung die Codex CLI
mit eigener ChatGPT-Anmeldung. [uv installieren](https://docs.astral.sh/uv/getting-started/installation/) · [Codex CLI installieren](https://developers.openai.com/codex/cli)

1. Öffne PowerShell im Projektordner und führe zur einmaligen Einrichtung diese Befehle aus.

   ~~~powershell
   . .\dev.ps1
   uv sync --locked
   codex login
   ~~~

2. Doppelklicke im Projektordner auf **Ausschreibungen starten.cmd**. Lass das
   Startfenster geöffnet. Im Browser kannst du unter **Profil bearbeiten** die
   Suchbegriffe und das Unternehmensprofil anpassen.
3. Klicke auf **Recherche starten** und nach dem Lauf auf **PDF öffnen**.
   Der Bericht beginnt mit einer Übersicht. Danach folgen Steckbriefe und Belege.

Für einen kleinen Beispiellauf in PowerShell verwende nach der Einrichtung
`uv run main.py report --config demo/suchprofil.toml`. Das Terminal zeigt den
PDF-Pfad.

## Aufbau und Entscheidungen

Oberfläche und Kommandozeile starten denselben Ablauf. Der Einstieg im Code ist
die Funktion `generate_report`. [main.py](main.py)

1. **Treffer suchen und speichern.** Für jeden Lauf legt der Agent unter
   `reports/runs/` einen Ordner an. Dort speichert er die Suchergebnisse in
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
   Laufordner einsehbar. [Auswahl](ausschreibungen/selection.py)

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

[Suchprofil und Hilfe bei Problemen](README.md) · [Zusammenarbeit mit dem Coding-Agenten](demo/zusammenarbeit.md)
