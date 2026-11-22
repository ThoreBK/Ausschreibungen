---
id: TASK-8
title: 8. Optionale KI-Vorpruefung anhand der Metadaten
status: To Do
assignee: []
created_date: '2026-11-15T17:55:00Z'
updated_date: '2026-11-15T22:27:00Z'
labels:
  - zukunft
dependencies:
  - TASK-7
documentation:
  - PROJECT.md
priority: low
type: feature
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Zukuenftige Erweiterung nach der manuell startbaren Demo: Bei groesseren Treffermengen unnoetige Dokumentdownloads und vollstaendige KI-Analysen reduzieren. Nach Schritt 3 des Workflows in PROJECT.md prueft eine optionale grobe KI-Analyse die Metadaten anhand der bereits in TASK-4 abgestimmten fachlichen Suchanweisung. Zusaetzliche Anforderungen und Bewertungsmassstaebe fuer die Vorpruefung werden vor Umsetzung abgestimmt; nicht Teil der ersten Demo.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Die optionale Vorpruefung unterscheidet potenziell passende, klar unpassende und unklare Treffer anhand der fachlichen Suchanweisung; die Einstufung und ihre Grundlage bleiben nachvollziehbar.
- [ ] #2 Nur klar unpassende Treffer werden mit belegter Begruendung ausgesondert; passende und unklare Treffer sowie Treffer mit unzureichenden Angaben gehen weiter zur Dokumentanalyse. Ohne aktivierte Vorpruefung bleibt der bisherige Ablauf erhalten.
<!-- AC:END -->
