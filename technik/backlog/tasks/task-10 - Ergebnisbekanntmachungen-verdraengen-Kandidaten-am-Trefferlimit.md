---
id: TASK-10
title: Ergebnisbekanntmachungen verdraengen Kandidaten am Trefferlimit
status: Done
assignee: []
created_date: '2026-11-16T22:35:00Z'
updated_date: '2026-11-20T00:07:00Z'
labels: []
dependencies: []
references:
  - backlog/tasks/task-2 - 2.-Ausschreibungsquellen-anbinden.md
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bezug: TASK-2 (Review von Commit c744f7c). Im gespeicherten Standardlauf vom 16.11.2026 waren sieben der 20 ausgewaehlten Kandidaten Ergebnisbekanntmachungen. Das Trefferlimit greift je Suchgruppe und fuer die gemeinsame Ergebnisliste vor der spaeteren fachlichen Auswahl. Dadurch koennen Ergebnisbekanntmachungen Plaetze belegen und moeglicherweise noch relevante Ausschreibungen verdraengen. Werden diese Treffer erst nachtraeglich aussortiert, kommen die bereits durch das Limit ausgeschlossenen Kandidaten nicht wieder hinzu.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Eindeutig als Ergebnisbekanntmachung erkannte Meldungen belegen im Standardlauf keinen Platz im Trefferlimit, lösen keine KI-Analyse aus und erscheinen nicht als Treffer im PDF. Bei unklarer Bekanntmachungsart bleibt der Kandidat für die fachliche Prüfung erhalten.
<!-- AC:END -->
