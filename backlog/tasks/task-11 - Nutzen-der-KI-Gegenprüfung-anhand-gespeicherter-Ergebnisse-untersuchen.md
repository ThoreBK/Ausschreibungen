---
id: TASK-11
title: Nutzen der KI-Gegenprüfung anhand gespeicherter Ergebnisse untersuchen
status: To Do
assignee: []
created_date: '2026-11-17T17:09:00Z'
updated_date: '2026-11-17T18:03:00Z'
labels: []
dependencies: []
references:
  - reports/acceptance/
  - reports/full-check-988aaffb/
  - reports/ki-analyse-5-20261117-f3d2e93e/
documentation:
  - PROJECT.md
type: spike
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Die Gegenprüfung aus TASK-4 nutzt dasselbe Modell wie die Analyse; ihr tatsächlicher Qualitätsgewinn ist bisher nicht belegt. Gespeicherte Vorschläge und Prüfentscheidungen fachlich mit den Originalbekanntmachungen abgleichen (P-03/P-08). Zunächst keine neuen Modellaufrufe und keine Codeänderungen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ablehnungen anhand konkreter Aussagen, Originalfundstellen und Protokollpfade als berechtigt, fälschlich oder ungeklärt einordnen; bestätigte Aussagen stichprobenartig auf übersehene Fehler prüfen. Doppelte Protokolle nicht als unabhängige Fälle zählen.
- [ ] #2 Kurzes Fazit mit Fallzahlen und Beispielen: Welche Fehler wurden verhindert, welche richtigen Aussagen verworfen und welche Grenzen bleiben? Daraus eine Empfehlung zum weiteren Einsatz der Gegenprüfung ableiten.
- [ ] #3 Kostenreduzierung (P-12) anhand der gespeicherten Protokolle untersuchen: Gegenprüfung gezielt einsetzen, doppelte Anfrageinhalte reduzieren, gemeinsame Angaben mehrerer Lose einmalig übergeben und Ergebnisse bei unveränderten Eingaben wiederverwenden. Einsparpotenzial bei Tokenverbrauch und Laufzeit sowie Risiken für die Ergebnisqualität kurz bewerten; zunächst ohne neue Modellaufrufe oder Codeänderungen.
<!-- AC:END -->
