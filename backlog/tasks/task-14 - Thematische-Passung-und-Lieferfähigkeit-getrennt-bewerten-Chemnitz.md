---
id: TASK-14
title: Thematische Passung und Lieferfähigkeit getrennt bewerten (Chemnitz)
status: Done
assignee: []
created_date: '2026-11-21T16:35:00Z'
updated_date: '2026-11-21T23:36:00Z'
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
- [x] #1 Beim Chemnitzer Original mit dem Profil des Prüflaufs ergibt der reguläre Analyse- und Gegenprüfungslauf für LOT-0000 thematisch passend. Die Begründung belegt die beauftragte Dokumentenanalyse anhand der Leistungsbeschreibung.
- [x] #2 Die Lieferfähigkeit für den geforderten Betrieb bleibt bei fehlendem Unternehmensnachweis offen. Aus der thematischen Passung folgt weder eine Teilnahmeberechtigung noch eine Lieferzusage.
- [x] #3 Der Regressionstest mit dem gespeicherten Original erkennt die im Prüflauf beobachtete Einstufung unpassend als Fehler. Der vorhandene Negativfall eines bloßen Suchworttreffers bleibt unpassend.
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Geprüfter Stand ce08e165 auf codex/task-14-passung. Im regulären Live-Lauf mit dem gespeicherten TED-Original 800874-2026 bestätigen beide KI-Stufen LOT-0000 als thematisch passend. Belegt ist die semantische Analyse gescannter Posteingänge als Prozessautomatisierung. Der geforderte Betrieb des Inferenzdienstes ist Vertragsleistung. Lieferfähigkeit und Erfüllung der Teilnahmevoraussetzungen bleiben ungeklärt. Bei TED 798622-2026 bleiben alle drei Lose bestätigt unpassend. Die Microsoft-365-Störung begründet die Fristverlängerung. Der Gesamtstatus incomplete beruht auf der fachlich korrekt verworfenen separaten Rückfragenfrist. Die Regression erkennt ein falsches Chemnitz-Urteil. Der Negativkorrekturpfad ist offline geprüft. Der Live-Test sichert Status und Fundstellen ab. Die Begründungen wurden anhand der Originale fachlich geprüft. Prüfergebnis am genannten Stand: 247 Tests bestanden, 9 optionale Live-Tests in der Offline-Suite übersprungen, beide Ruff-Prüfungen erfolgreich.
<!-- SECTION:FINAL_SUMMARY:END -->
