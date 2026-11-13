# Tender Research Agent

Lokale Demo eines KI-gestützten Ausschreibungs-Recherche-Agenten. Langfristig:
öffentliche Quellen recherchieren, Dokumente verarbeiten, Angaben mit Fundstellen
extrahieren, Ergebnisse bewerten und PDF-Berichte erstellen. Aktuell existiert nur
das Entwicklungsgrundgerüst; es benötigt keinen API-Key und verursacht keine API-Kosten.

## Voraussetzungen und Einrichtung

Python 3.12+, uv und Git. Node.js LTS/npm werden ausschließlich für Backlog.md
benötigt. Auf diesem Rechner liegen uv, Python und Node unter `.tools/`;
Systeminstallationen werden nicht ersetzt. In PowerShell im Projektordner:

```powershell
. .\dev.ps1
uv sync --locked
npm.cmd ci
```

`dev.ps1` setzt Toolpfade und Cache-Verzeichnisse nur für das aktuelle Terminal.
Bei einem frischen Clone zuerst [uv](https://docs.astral.sh/uv/getting-started/installation/)
und [Node.js LTS](https://nodejs.org/en/download) installieren. Danach funktionieren
dieselben Befehle; uv lädt Python bei Bedarf gemäß `.python-version` herunter.
Eine Aktivierung der virtuellen Umgebung ist für `uv run` nicht erforderlich.
`.env.example` dokumentiert spätere Konfiguration; aktuell ist keine `.env` nötig.

## Start und Prüfungen

```powershell
uv run main.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
# Formatierung anwenden:
uv run ruff format .
```

Python-Konfiguration: `pyproject.toml`; reproduzierbare Abhängigkeiten: `uv.lock`.
Es gibt keine Laufzeitabhängigkeiten, nur Pytest und Ruff als Entwicklungswerkzeuge.
Der Smoke-Test startet den tatsächlichen Programmeinstieg als separaten Prozess.

## Backlog.md

Nach `. .\dev.ps1`:

```powershell
backlog.cmd browser
backlog.cmd board
backlog.cmd task list --plain
backlog.cmd task view task-1 --plain
```

Das Web-Kanban öffnet sich unter <http://127.0.0.1:6420>; mit `Ctrl+C` beenden.
Tickets liegen als versionierbare Markdown-Dateien unter `backlog/tasks/`.
Die CLI ist in `package.json` und `package-lock.json` festgehalten.
Codex verwendet die CLI-Integration in `AGENTS.md`; MCP ist nicht erforderlich.
CLI-Referenz: [Backlog.md](https://github.com/MrLesk/Backlog.md/blob/main/CLI-INSTRUCTIONS.md).

Die sieben Roadmap-Tickets bilden nur die beauftragten Entwicklungsphasen ab,
jeweils mit einem groben Abnahmekriterium und Abhängigkeit zur vorherigen Phase.
Detailtickets werden zum Phasenbeginn abgestimmt. **Codex darf Ticket-Inhalte und
Status nur nach ausdrücklicher Abstimmung mit dem Nutzer ändern.** Deshalb bleibt
auch das technisch erledigte Grundlagen-Ticket bis zur Freigabe auf „To Do“.

## Entscheidungen zum Setup

- Ein Einstiegspunkt `main.py` und `tests/` reichen zunächst aus; keine vorgezogene
  Modularchitektur und kein Build-Framework.
- Python 3.12 ist als lokale Basis gepinnt; das Projekt erlaubt Python ab 3.12.
- Backlog.md ist ein lokales Entwicklungswerkzeug, kein Teil der Python-Laufzeit.
- `.gitignore` schließt lokale Tools, Umgebungen, Secrets und erzeugte Ausgaben
  aus. Dokumentation, Backlog und Lockdateien werden versioniert.
