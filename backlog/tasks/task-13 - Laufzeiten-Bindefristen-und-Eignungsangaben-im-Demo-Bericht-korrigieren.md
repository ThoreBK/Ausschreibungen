---
id: TASK-13
title: Laufzeiten, Bindefristen und Eignungsangaben im Demo-Bericht korrigieren
status: In Progress
assignee: []
created_date: '2026-11-21T14:07:00Z'
updated_date: '2026-11-21T15:23:00Z'
labels: []
dependencies: []
references:
  - >-
    reports/live-review-20261120-0121/runs/20261120T002152076322Z-66ea73d6/documents
  - >-
    reports/live-review-20261120-0121/runs/20261120T002152076322Z-66ea73d6/analyses/20261120T002201-d1a090f7/bericht.pdf
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Der fachliche Review des Live-Laufs vom 20.11.2026 hat vier Korrekturen für die Demo ergeben. Wer ein Los aus der Übersicht auswählt, soll im Steckbrief die mögliche Vertragsdauer, die Bindung an ein Angebot und die belegten Eignungsanforderungen erkennen. Die vier Befunde betreffen P-04, P-08 und P-11. Die Seitenangaben beziehen sich auf das Referenz-PDF.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Vertragslaufzeiten (S. 2, 3, 8, 10, 11). BARMER Los 1 nennt vier Jahre ab dem Monat nach Abnahme von AG 7 sowie die automatische Verlängerung um zweimal ein Jahr bei ausbleibender fristgerechter Kündigung. FAVIS Los 1 zeigt die Plantermine 01.07.2027 bis 29.06.2029, die Mindestlaufzeit von 24 Monaten und die Optionen von 24, 12 und 12 Monaten bis maximal 72 Monate. Die Abweichung zwischen Planende und Mindestlaufzeit ist als offener Punkt sichtbar. Alle drei AOK-Steckbriefe unterscheiden das reguläre Höchstdatum 31.05.2031 von der bedingten Verlängerung bei Nachprüfung des Anschlussauftrags bis längstens 30.11.2031.
- [ ] #2 Angebotsbindefrist (S. 3, 5, 7). Ergebnisdaten und Steckbrief führen die Angebotsbindefrist als eigene Angabe mit XML-Beleg. Die Werte betragen 102 Tage für FAVIS (LOT-0001), 43 Tage für Chemnitz (LOT-0000) und 30 Tage für Merzig (LOT-0000).
- [ ] #3 Eignungsnachweise (S. 3, 5, 7, 8, 10, 11). FAVIS Los 1 zeigt die Mindestdeckung für Personen-, Sach- und Vermögensschäden von 0,5, 3 und 5 Mio. Euro sowie die zweifache Jahresgesamtleistung. Chemnitz nennt PQ-Nummer, Eigenerklärung oder Einheitliche Europäische Eigenerklärung sowie die Möglichkeit gleichwertiger Nachweise bei belegter Gleichwertigkeit. Merzig weist direkt im Eignungsfeld auf die Vergabeunterlagen und die dort zu prüfenden Einzelanforderungen hin. Alle drei AOK-Lose nennen bei bestehender Eintragungspflicht den höchstens sechs Monate alten Registerbeleg, gerechnet vom Tag der Teilnahmefrist, und den Versicherungsnachweis spätestens acht Wochen nach Zuschlag. Jede Angabe ist belegt und ohne Verweis auf eine verworfene KI-Kurzfassung verständlich.
- [ ] #4 BARMER-Rückfragen (Los 1, S. 2). Der Steckbrief gibt den Freitext sinngemäß als Bitte wieder, Fragen zum Teilnahmewettbewerb bis 11.12.2026 zu stellen. Die Uhrzeit bleibt offen. Die separate Frist für Teilnahmeanträge ist mit 21.12.2026, 10:00 MEZ ausgewiesen.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Nach der Umsetzung werden alle fünf gespeicherten TED-Originale des Referenzlaufs mit dem regulären Analyseablauf, echten Modellaufrufen und der vorgesehenen KI-Gegenprüfung erneut ausgewertet. Aus den dabei entstandenen Ergebnisdaten wird mit dem regulären Berichtsgenerator ein neues PDF erstellt. Für alle vier Korrekturpunkte werden Ergebnisdaten und sichtbarer Steckbrief mit den jeweiligen XML-Fundstellen verglichen. Maßgeblich sind die fachlich richtige Aussage, der richtige Losbezug und die Erkennbarkeit verbleibender Unsicherheit. Der tatsächliche Analysestatus und gegebenenfalls verbleibende Lücken werden festgehalten.
<!-- DOD:END -->
