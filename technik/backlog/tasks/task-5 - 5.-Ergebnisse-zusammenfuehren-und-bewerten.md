---
id: TASK-5
title: 5. Mehrere Treffer verlaesslich auswaehlen und zusammenfuehren
status: Done
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-21T17:37:00Z'
labels:
  - roadmap
dependencies:
  - TASK-4
documentation:
  - PROJECT.md
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nach dem ersten PDF-Durchlauf die Auswahl, Konsolidierung und Sortierung mehrerer ausgewerteter Kandidaten fuer die vollstaendige Demo absichern. Regeln: PROJECT.md P-03 und P-06 sowie die Entscheidungen zu Bewertungseinheit, Duplikaten, Berichtigungen und Informationsqualitaet. Fachliche Voraussetzung ist TASK-4; dieses Ticket blockiert TASK-6 nicht, bleibt aber vor TASK-7 verpflichtend. Die gemeinsame Pruefung mit dem PDF-Bericht erfolgt in TASK-7. Eine komplexe Bewertungslogik mit Gewichtungen oder Teilnahmeempfehlungen ist eine spaetere, gesondert abzustimmende Erweiterung.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ausgewertete Kandidaten werden anhand ihrer belegten Passung und der erkennbaren Verfahrenssituation nachvollziehbar ausgewaehlt. Ergebnisbekanntmachungen, Vorinformationen, eindeutig abgelaufene Faelle und unklare Teilnahmemoeglichkeiten werden nicht unterschiedslos als aktuell bewerbbare Ausschreibungen dargestellt. Fachlich unklare Faelle bleiben als solche sichtbar.
- [x] #2 Die Ergebnisse liegen einheitlich je relevantem Los beziehungsweise Verfahren ohne Losaufteilung vor. Sichere doppelte Treffer sind zusammengefuehrt; verschiedene Lose und unsichere Zuordnungen bleiben unterscheidbar. Herkunft und Zusammenfuehrungsgruende sind nachvollziehbar.
- [x] #3 Nachweislich zugeordnete Berichtigungen behalten bisherigen und geaenderten Stand als nachvollziehbare Aenderungshistorie. Ungeklaerte Zuordnungen und Widersprueche bleiben mit ihren Belegen sichtbar; Werte werden nicht stillschweigend ueberschrieben.
- [x] #4 Die Berichtsliste ist nach einem dokumentierten, fachlich sinnvollen Kriterium sortiert. Abrufbegrenzung und endgueltige Berichtsauswahl sind unterscheidbar; das Berichtslimit greift erst nach der fachlichen Auswahl innerhalb des abgerufenen Kandidatenbestands. Grenzen der Recherche bleiben sichtbar.
- [x] #5 Mehrere fachlich gepruefte Beispiele belegen Auswahl und Zusammenfuehrung einschliesslich Dubletten, Losabgrenzung und einer Berichtigung. Die konsolidierten Ergebnisse enthalten weiterhin alle fuer den Bericht benoetigten Angaben, Belege und offenen Pruefpunkte. Ihre gemeinsame Darstellung mit TASK-6 wird in TASK-7 geprueft.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Regressionstests in tests/test_selection.py, geprüft auf Commit 2787bf3.

P-06 · test_reused_technical_lot_id_keeps_independent_deadlines: Zwei Lose mit derselben technischen LOT-Kennung und verschiedenen internen Kennungen behalten ihre eigenen Fristen. Bei Berichtslimit 1 erscheint das offene Los, das abgelaufene wird ausgeschlossen.

P-06 und P-08 · test_partial_deadline_preserves_date_and_detects_conflict: Ein unvereinbares Originaldatum ohne Uhrzeit macht den Teilnahmestand ungeklärt. Beide Datumsbelege bleiben erhalten. Ein mit dem bekannten Zeitpunkt vereinbarer Kalendertag löst keinen Konflikt aus.

P-08 · test_duration_conflict_from_duplicate_reaches_brief: Der erst in der Dublette erkannte Konflikt zwischen 24 Monaten Mindestlaufzeit und einem Jahr Planlaufzeit erscheint im PDF-Steckbrief. Die konsolidierte Auswahl enthält die TED-Herkunft und alle drei Belege.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Die Auswahl berücksichtigt belegte Passung und Teilnahmestand je Los. Sichere Dubletten und Berichtigungen behalten ihre Herkunft und Historie. Das Berichtslimit greift nach Auswahl und Sortierung. 245 Tests bestanden, 9 optionale Live-KI-Tests übersprungen. Ruff-Prüfung und Formatprüfung bestanden. Die gemeinsame Demo-Abnahme mit TASK-6 erfolgt in TASK-7.
<!-- SECTION:FINAL_SUMMARY:END -->
