---
id: TASK-12
title: Prüfkontext gezielt reduzieren und fachliche Qualität nachweisen
status: Done
assignee: []
created_date: '2026-11-17T21:43:00Z'
updated_date: '2026-11-18T23:10:00Z'
labels: []
dependencies: []
references:
  - reports/task11-compact-check-ac9536c2/measured-comparison.json
  - reports/task11-compact-check-ac9536c2/comparison.json
  - reports/task11-compact-check-ac9536c2/bundle-replay.json
  - tests/fixtures/real/verification-cases.json
  - reports/task12-context-386cb9bd/measured-comparison.json
  - reports/review-69d7996-gpt62-5e03f719/live-source-audit.json
  - reports/review-f121c86-gpt62-1a97de77/live-vergleich.json
  - reports/task12-context-offline/comparison.json
documentation:
  - PROJECT.md
type: enhancement
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Die Gegenprüfung erhält derzeit erneut die vollständige Analyseingabe. Bei der zuletzt gemessenen Ausschreibung mit drei Losen benötigte sie 48.889 Eingabetokens. Der Prüfkontext soll kleiner werden, ohne Gegenbelege, Einschränkungen oder Losbezüge zu verlieren. Relevant sind P-03, P-04, P-05, P-08 und P-12.

Vereinbarter Umfang:
Ein gemeinsamer Gegenprüfungsaufruf je Ausschreibung bleibt das normale Vorgehen. Modellwechsel, Caching, Vorauswahl nach TASK-8 und Änderungen an der Erstanalyse gehören nicht dazu. 50–70 % weniger Eingabetokens der Gegenprüfung sind ein Versuchsziel, keine zugesicherte Einsparung oder Rechtfertigung für Qualitätsverluste.

Übergabe:
Ausgangspunkt sind der aktuelle uncommittete Arbeitsstand und die vorhandenen Messartefakte. Der Validierungsfix nach dem bisherigen Live-Benchmark wurde mit unveränderten Modellantworten offline geprüft; dies war kein erneuter Live-Lauf. Das bisherige Tokenbudget greift nur zwischen Aufrufen und ist keine harte Obergrenze. TASK-11 wird im Rahmen dieses Auftrags nicht verändert.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Die Erstanalyse verarbeitet weiterhin die vollständige Bekanntmachung. Originalquellen und Fundstellen bleiben vollständig erhalten; der tatsächlich übergebene Prüfkontext ist nachvollziehbar.
- [x] #2 Die gemeinsame Gegenprüfung erhält alle Originalquellen, einschließlich globaler Angaben, möglicher Gegenbelege und Vergleichsstellen anderer Lose. Sie erhält die prüfpflichtigen Aussagen und verzichtet auf die erneute Übergabe von structured_fields. Die Kontextbildung benötigt keinen Modellaufruf.
- [x] #3 Aussagen über fehlende Angaben werden anhand der vollständigen Bekanntmachung geprüft. Bei unzureichender Grundlage bleibt das fachliche Urteil ausdrücklich ungeklärt.
- [x] #4 Jede geprüfte Aussage erhält weiterhin ein begründetes Urteil mit Fundstellen. Strittige Aussagen, widersprüchliche Belege, Feldbedeutungen und Loszuordnungen bleiben erhalten.
- [x] #5 Offline-Tests prüfen entfernte Gegenbelege, Anforderungen an unerwarteten XML-Stellen, widersprüchliche Losbezüge und fälschlich behauptete fehlende Angaben. Erwartete Ergebnisse und notwendige Fundstellen sind unabhängig vom Auswahlcode festgelegt. Bestehende Tests und beide Ruff-Prüfungen bestehen.
- [x] #6 Die Gegenprüfung mit und ohne abgeleitete Ergebnisfelder wird mit denselben gespeicherten Analysevorschlägen gegen fachlich geprüfte Erwartungen verglichen. Quellenabdeckung, Qualitätsabweichungen, Eingabe- und Ausgabetokens sowie Laufzeiten werden je Stufe dokumentiert. Offline-Replays und echte Modellmessungen sind unterscheidbar.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Versuchsergebnis und Entscheidung vom 18.11.2026. Im historischen Vergleich mit identischen Vorschlägen sank die Eingabe der Gegenprüfung bei 798622 von 49.028 auf 41.331 Tokens und bei 788030 von 19.201 auf 18.611 Tokens. Beide Varianten übergaben jeweils alle 333 bzw. 107 Quellen. Die Einsparung von 15,7 bzw. 3,1 Prozent entstand hauptsächlich durch das Weglassen der abgeleiteten structured_fields. Im separaten Fünferlauf mit gpt-6.2-sol wurden alle 1.293 Quellen erneut übergeben. Der skalare Quellenfilter wurde daraufhin entfernt. Analyse und Gegenprüfung erhalten die vollständigen Originalquellen. Die Gegenprüfung erhält die prüfpflichtigen Aussagen und spart die Wiederholung der abgeleiteten Ergebnisfelder. Das Versuchsziel von 50 bis 70 Prozent wurde verfehlt. Für den vereinfachten Stand liegt ein Offline-Nachweis vor. Sein Tokenverbrauch wurde nicht erneut live gemessen.

Live-Nachweis nach Entfernen des Skalarfilters (f121c86, P-05/P-12). Dieselben fünf Bekanntmachungen und dasselbe Profil ergaben fünf Analyse- und fünf Gegenprüfungsaufrufe mit gpt-6.2-sol. Die Analyse verbrauchte 185.281 Eingabe- und 11.122 Ausgabetokens in 284,4 Sekunden. Die Gegenprüfung erhielt sämtliche 1.293 Quellen und verbrauchte 169.017 Eingabe- und 15.565 Ausgabetokens in 357,4 Sekunden. Insgesamt 380.985 Tokens und 10:42 Minuten gegenüber 386.123 Tokens und 10:44 Minuten im Vorlauf. Wegen neu erzeugter Vorschläge lässt sich diese Differenz keiner einzelnen Änderung zuschreiben. Für die Wirkung der entfallenen Ergebnisfelder ist der kontrollierte Vergleich vom 18.11. maßgeblich.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Abgenommen ist die vollständige Quellenübergabe ohne wiederholte Ergebnisfelder. Im kontrollierten Vergleich sanken die Eingabetokens der Gegenprüfung um 15,7 bzw. 3,1 Prozent. Das Versuchsziel von 50–70 Prozent wurde verfehlt. Der zusätzliche Skalarfilter entfiel, weil er in den Live-Fällen keine Quellen einsparte.
<!-- SECTION:FINAL_SUMMARY:END -->
