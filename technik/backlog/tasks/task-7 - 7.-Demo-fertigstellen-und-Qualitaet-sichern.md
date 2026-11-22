---
id: TASK-7
title: 6. Generalprobe und fachliche Richtigkeit des PDF-Berichts prüfen
status: Done
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-22T11:27:00Z'
labels:
  - roadmap
dependencies:
  - TASK-5
  - TASK-6
documentation:
  - PROJECT.md
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Die dokumentierte Generalprobe zeigt den vollständigen Weg vom angepassten Suchprofil über TED und die Auswertung mehrerer Treffer bis zum PDF. Maßgeblich für den Abschluss ist, dass die Angaben im aktuellen Bericht mit den Originalbekanntmachungen übereinstimmen und die Fundstellen die jeweiligen Aussagen tragen. Die Prüfung orientiert sich an den fachlichen Anforderungen und Entscheidungen in PROJECT.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Eine Generalprobe zeigt einen manuell gestarteten echten Lauf vom ohne Codeaenderung angepassten Profil ueber TED, Auswertung und Zusammenfuehrung mehrerer Treffer bis zum PDF. Der Lauf ist anhand der dokumentierten Einrichtung wiederholbar; gespeicherte Eingaben und Ergebnisse machen ihn nachvollziehbar. Eine Code-Stelle und zwei bis drei wesentliche Entscheidungen koennen erklaert werden.
- [x] #2 Die Nachweise zur Generalprobe und zur fachlichen Prüfung sind im Ticket verlinkt oder beschrieben und den einschlägigen Anforderungen aus PROJECT.md zugeordnet. Der Abgleich mit den Originalen und die Sichtprüfung des aktuellen PDF sind nachvollziehbar. Offene fachliche Fragen sind benannt.
- [x] #3 Die relevanten Tests sowie ruff check und ruff format --check bestehen. Fachliche Prueffaelle umfassen passende und unpassende Treffer, leere Ergebnisse, Abruf-/Verarbeitungsfehler, fehlende und widerspruechliche Angaben, unklare Fristen, Bekanntmachungsarten, mehrere Lose, Dubletten und Berichtigungen. Grundlegende Tests entstehen bereits in den umsetzenden Tickets.
- [x] #4 Übersicht und Steckbriefe des aktuellen Beispiel-PDF sind für jeden ausgewählten Treffer mit der zugehörigen TED-Bekanntmachung und dem richtigen Los abgeglichen. Pflichtangaben, Fristen, Abgabeform und Passungsurteil sind korrekt und durch die angegebenen Fundstellen belegt. Fehlende, unsichere und widersprüchliche Angaben sind im Bericht erkennbar. Die in der Generalprobe gefundenen Fehler sind im aktuellen PDF nachgeprüft. Der dokumentierte Start ist ohne Programmierkenntnisse nachvollziehbar und das PDF ohne Zusatzwissen verständlich.
- [x] #5 Eine halbe Seite dokumentiert anhand tatsaechlicher Beispiele die Arbeit mit dem Coding-Agenten, dessen Hilfe und bewusste abweichende Entscheidungen des Nutzers. Fehlende Beispiele werden mit dem Nutzer geklaert und nicht erfunden.
- [x] #6 Öffentliche und zulässige Datenzugänge, Vertraulichkeit und der Umgang mit Zugangsdaten im Repository sind geprüft. Die Entscheidung über eine Teilnahme bleibt beim Menschen. Die Demo reicht nichts ein, versendet nichts und sagt nichts zu.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Abnahme am 22.11.2026 auf main (a2f03c0). Der [Nachweis der Generalprobe](../../demo/abgabenachweis.md) dokumentiert den ersten Lauf vom 21.11. Die folgenden Ergebnisse beziehen sich auf den nachgeprüften Bericht.

- **#1 · Generalprobe (P-01, P-02, P-05, P-15).** Lauf 20261121T183204101192Z-03419e90 mit dem [Demoprofil](../../demo/suchprofil.toml). Vier erfolgreiche TED-Suchabfragen, sieben Suchvorkommen, fünf verschiedene Originalbekanntmachungen, sieben Lose. Die gespeicherte Suchkonfiguration stimmt inhaltlich mit dem Demoprofil überein. Die [Kurzanleitung](../../demo/README.md) enthält Startbefehl, Programmeinstieg und die Entscheidungen zu Belegen, Auswahl und Rechercheumfang.
- **#2 und #4 · Prüfgrundlage (P-03, P-04, P-06, P-07, P-08, P-11).** Geprüft wurde bericht.pdf im lokalen Worktree 12a2, unter reports/task-7-nachpruefung/28556ce4/analyses/nachpruefung/. SHA-256 der PDF: 64a37c1e8d25f495d0ce2326b7fd001d4457583a23d151e349a915b54862162b. Die Nachprüfung verwendet die fünf gespeicherten Original-XMLs unter documents/ desselben Laufs. Alle fünf SHA-256 stimmen mit den Abrufdaten überein. Für alle sieben Lose ließen sich 402 unterschiedliche Kombinationen aus Dokument, XML-Pfad und Zitat im jeweiligen Original auflösen. Alle 32 PDF-Seiten gerendert und gesichtet. Die vier TED-Quellenlinks stimmen mit den ausgewählten Bekanntmachungen überein, die lokalen Linkziele sind vorhanden.
- **Übersicht, S. 1.** Vier ausgewählte Lose, davon zwei mit belegter Passung und offener Frist zum Prüfzeitpunkt der Generalprobe. Die drei Pfalzwerke-Lose (798622-2026) sind als profilfremde Materiallieferungen mit abgelaufener Frist ausgeschlossen. Für keinen Treffer wird die Teilnahmeberechtigung zugesagt.
- **Hamburg Tourismus, 773064-2026, LOT-0001, S. 2–3.** Der Leistungsort „Beliebiger Ort“ entspricht dem XML-Wert anyw. Die deutsche Bedienoberfläche ist als Produktanforderung ausgewiesen. Beratungsleistungen und bedarfsabhängige Schulungen stützen die Passung. Teilnahmeanträge bis 07.12.2026, 11:00 MEZ. Zur Rückfragenfrist am 13.11.2026 zeigt der Steckbrief 23:59 MEZ, Original und Beleg [11] auf S. 11 enthalten 23:59:59+01:00. Der Nutzer hat die minutengenaue Anzeige mit Verweis auf den sekundengenauen Originalbeleg ausdrücklich akzeptiert.
- **Chemnitz, 800874-2026, LOT-0000, S. 4–5.** Die semantische Analyse eingescannter Posteingänge trägt das positive Passungsurteil. Angebotsfrist 18.12.2026, 09:00 MEZ, Bindefrist 43 Tage, Zuschlagsgewichtung 60/20/20. Der Steckbrief zeigt sowohl die ausschließlich elektronische Einreichung laut Freitext als auch den abweichenden XML-Code allowed mit Quellen [65, 66].
- **Merzig-Wadern, 799785-2026, LOT-0000, S. 6.** Beschaffung von Plattformlizenzen und Einführung sind belegt. Ob Beratung oder individuelle Entwicklung beauftragt wird, bleibt offen. Übersicht und Steckbrief weisen die Passung als „unklar“ aus. Angebotsfrist 16.12.2026, 23:59 MEZ, Bindefrist 30 Tage, Laufzeit 48 Monate, Zuschlag 60 % Leistung/Qualität und 40 % Preis.
- **Hamburg Port Authority, 810275-2026, LOT-0000, S. 7–9.** Verbindlicher Initialabruf und optionale Agentenentwicklung sind getrennt. Bei der Teilnahmeantragsfrist am 07.01.2027 stehen im XML die Offsets +01:00 und +02:00, die Änderungsnotiz nennt 10:00 Uhr ohne Zeitzone. Der Teilnahmestand bleibt ungeklärt. Beim Erfahrungsnachweis sind zwei bzw. drei Jahre sichtbar. Zwei Jahre Mindestlaufzeit, höchstens acht Jahre und die Zuschlagsformel L/P stimmen mit dem Original überein. Die im PDF ausgewiesene unvollständige Auswertung macht solche offenen Punkte sichtbar.
- **#3 · Automatisierte Prüfung.** Auf main 255 Offline-Tests bestanden. Die neun optionalen Live-Modelltests blieben wie beauftragt ausgeschaltet. Ruff-Lint und Formatprüfung bestanden. Die Prüffallmatrix im Nachweis der Generalprobe ordnet die Tests den fachlichen Fällen zu. Für diese Abnahme waren die archivierten Modellantworten und Originale die Grundlage.
- **#5 · Zusammenarbeit.** [Zusammenarbeit mit dem Coding-Agenten](../../demo/zusammenarbeit.md) belegt anhand von TASK-5, TASK-13 und TASK-14 den Beitrag des Agenten und die eigenständigen Entscheidungen des Nutzers.
- **#6 · Zugänge und menschliche Entscheidung (P-01, P-09, P-10).** Die Abrufdaten belegen fünf öffentliche TED-XMLs. In der nachgeprüften Analyse sind zehn erfolgreiche Modellaufrufe mit ChatGPT-Anmeldung protokolliert. Der Berichtspfad ruft Daten ab und schreibt lokale Ergebnisse. Der Test gegen unerwartete Werkzeugaktionen ist Teil der bestandenen Offline-Suite. Ergänzend ergab die Prüfung der 86 Git-Dateien auf typische Schlüssel- und Tokenmuster keinen Treffer. Nutzungsgrundlage, Vertraulichkeit und Kostenbasis (P-12) sind im Nachweis der Generalprobe dokumentiert.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Generalprobe und Quellenabgleich abgeschlossen. Die vier Steckbriefe und die Übersicht der nachgeprüften PDF geben die Ergebnisse mit den belegten Unsicherheiten wieder. Die akzeptierte Minutenanzeige der Hamburger Rückfragenfrist ist mit dem sekundengenauen Originalbeleg dokumentiert. Alle sechs Kriterien sind geprüft.
<!-- SECTION:FINAL_SUMMARY:END -->
