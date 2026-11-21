---
id: TASK-14
title: Thematische Passung und Lieferfähigkeit getrennt bewerten (Chemnitz)
status: To Do
assignee: []
created_date: '2026-11-21T16:35:00Z'
labels: []
dependencies: []
references:
  - tests/fixtures/real/800874-2026.xml
  - tests/test_analysis_live.py
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Im Prüflauf von TASK-13 erhielt Chemnitz (TED 800874-2026, LOT-0000) nach der Gegenprüfung die Einstufung unpassend. Laut Losbeschreibung analysiert das beauftragte LLM gescannte Posteingänge semantisch. Das überschneidet sich mit der Prozessautomatisierung im Unternehmensprofil. Ob das Unternehmen den geforderten Inferenzdienst betreiben kann, ist offen. Analyse und Gegenprüfung sollen diese Unterscheidung gemäß P-03 und P-08 unabhängig vom konkreten Ort oder Anbieter treffen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Beim Chemnitzer Original mit dem Profil des Prüflaufs ergibt der reguläre Analyse- und Gegenprüfungslauf für LOT-0000 thematisch passend. Die Begründung belegt die beauftragte Dokumentenanalyse anhand der Leistungsbeschreibung.
- [ ] #2 Die Lieferfähigkeit für den geforderten Betrieb bleibt bei fehlendem Unternehmensnachweis offen. Aus der thematischen Passung folgt weder eine Teilnahmeberechtigung noch eine Lieferzusage.
- [ ] #3 Der Regressionstest mit dem gespeicherten Original erkennt die im Prüflauf beobachtete Einstufung unpassend als Fehler. Der vorhandene Negativfall eines bloßen Suchworttreffers bleibt unpassend.
<!-- AC:END -->
