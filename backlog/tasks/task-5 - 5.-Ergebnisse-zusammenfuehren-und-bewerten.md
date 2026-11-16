---
id: TASK-5
title: 5. Mehrere Treffer verlaesslich auswaehlen und zusammenfuehren
status: To Do
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-16T12:56:00Z'
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
- [ ] #1 Ausgewertete Kandidaten werden anhand ihrer belegten Passung und der erkennbaren Verfahrenssituation nachvollziehbar ausgewaehlt. Ergebnisbekanntmachungen, Vorinformationen, eindeutig abgelaufene Faelle und unklare Teilnahmemoeglichkeiten werden nicht unterschiedslos als aktuell bewerbbare Ausschreibungen dargestellt. Fachlich unklare Faelle bleiben als solche sichtbar.
- [ ] #2 Die Ergebnisse liegen einheitlich je relevantem Los beziehungsweise Verfahren ohne Losaufteilung vor. Sichere doppelte Treffer sind zusammengefuehrt; verschiedene Lose und unsichere Zuordnungen bleiben unterscheidbar. Herkunft und Zusammenfuehrungsgruende sind nachvollziehbar.
- [ ] #3 Nachweislich zugeordnete Berichtigungen behalten bisherigen und geaenderten Stand als nachvollziehbare Aenderungshistorie. Ungeklaerte Zuordnungen und Widersprueche bleiben mit ihren Belegen sichtbar; Werte werden nicht stillschweigend ueberschrieben.
- [ ] #4 Die Berichtsliste ist nach einem dokumentierten, fachlich sinnvollen Kriterium sortiert. Abrufbegrenzung und endgueltige Berichtsauswahl sind unterscheidbar; das Berichtslimit greift erst nach der fachlichen Auswahl innerhalb des abgerufenen Kandidatenbestands. Grenzen der Recherche bleiben sichtbar.
- [ ] #5 Mehrere fachlich gepruefte Beispiele belegen Auswahl und Zusammenfuehrung einschliesslich Dubletten, Losabgrenzung und einer Berichtigung. Die konsolidierten Ergebnisse enthalten weiterhin alle fuer den Bericht benoetigten Angaben, Belege und offenen Pruefpunkte. Ihre gemeinsame Darstellung mit TASK-6 wird in TASK-7 geprueft.
<!-- AC:END -->
