---
id: TASK-12
title: Prüfkontext gezielt reduzieren und fachliche Qualität nachweisen
status: To Do
assignee: []
created_date: '2026-11-17T21:43:00Z'
updated_date: '2026-11-17T23:00:00Z'
labels: []
dependencies: []
references:
  - reports/task11-compact-check-ac9536c2/measured-comparison.json
  - reports/task11-compact-check-ac9536c2/comparison.json
  - reports/task11-compact-check-ac9536c2/bundle-replay.json
  - tests/fixtures/real/verification-cases.json
  - reports/task12-context-386cb9bd/measured-comparison.json
  - reports/review-69d7996-gpt62-5e03f719/live-source-audit.json
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
- [ ] #1 Die Erstanalyse verarbeitet weiterhin die vollständige Bekanntmachung. Originalquellen und Fundstellen bleiben vollständig erhalten; der tatsächlich übergebene Prüfkontext ist nachvollziehbar.
- [ ] #2 Die Quellenauswahl berücksichtigt neben den zitierten Belegen auch unabhängig ermittelte relevante Stellen, mögliche Gegenbelege, globale Angaben und erforderliche Losvergleiche. Sie benötigt keinen zusätzlichen Modellaufruf.
- [ ] #3 Unsichere Quellenauswahl führt zu einem erweiterten Prüfkontext oder einem ausdrücklich ungeklärten Urteil. Aussagen über fehlende Angaben werden nicht allein aus einem begrenzten Ausschnitt abgeleitet.
- [ ] #4 Jede geprüfte Aussage erhält weiterhin ein begründetes Urteil mit Fundstellen. Strittige Aussagen, widersprüchliche Belege, Feldbedeutungen und Loszuordnungen bleiben erhalten.
- [ ] #5 Offline-Tests prüfen entfernte Gegenbelege, Anforderungen an unerwarteten XML-Stellen, widersprüchliche Losbezüge und fälschlich behauptete fehlende Angaben. Erwartete Ergebnisse und notwendige Fundstellen sind unabhängig vom Auswahlcode festgelegt. Bestehende Tests und beide Ruff-Prüfungen bestehen.
- [ ] #6 Vollständige und reduzierte Gegenprüfung werden anhand derselben gespeicherten Analyseantworten und fachlich geprüfter Erwartungen verglichen. Qualitätsabweichungen sowie Eingabe-/Ausgabetokens und Laufzeiten werden getrennt dokumentiert. Offline-Nachweise und echte Modellmessungen bleiben unterscheidbar.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Versuchsergebnis und Entscheidung vom 18.11.2026. Im historischen Vergleich mit identischen Vorschlägen sank die Eingabe der Gegenprüfung bei 798622 von 49.028 auf 41.331 Tokens und bei 788030 von 19.201 auf 18.611 Tokens. Beide Varianten übergaben jeweils alle 333 bzw. 107 Quellen. Die Einsparung von 15,7 bzw. 3,1 Prozent entstand hauptsächlich durch das Weglassen der abgeleiteten structured_fields. Im separaten Fünferlauf mit gpt-6.2-sol wurden alle 1.293 Quellen erneut übergeben. Der skalare Quellenfilter wurde daraufhin entfernt. Analyse und Gegenprüfung erhalten die vollständigen Originalquellen. Die Gegenprüfung erhält die prüfpflichtigen Aussagen und spart die Wiederholung der abgeleiteten Ergebnisfelder. Das Versuchsziel von 50 bis 70 Prozent wurde verfehlt. Für den vereinfachten Stand liegt ein Offline-Nachweis vor. Sein Tokenverbrauch wurde nicht erneut live gemessen.
<!-- SECTION:NOTES:END -->
