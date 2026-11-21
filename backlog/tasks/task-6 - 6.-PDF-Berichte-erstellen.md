---
id: TASK-6
title: 4. Ersten vollstaendigen Lauf bis zum PDF ermoeglichen
status: Done
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-21T17:48:00Z'
labels:
  - roadmap
dependencies:
  - TASK-4
documentation:
  - PROJECT.md
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Den ersten manuell startbaren Durchlauf vom konfigurierten Profil ueber eine echte TED-Bekanntmachung und ihre Auswertung bis zum lesbaren PDF herstellen. Regeln: PROJECT.md P-04, P-05, P-07, P-08 und P-11. Die einfache Passungsbegruendung aus TASK-4 genuegt; TASK-5 blockiert diesen ersten Bericht nicht. Das PDF kann anschliessend auch die von TASK-5 zusammengefuehrte Trefferliste darstellen. Oberflaeche, PDF-Technik und Layoutdetails bleiben offen. Der erste Bericht ist ein Zwischenergebnis; die Abgabereife aller Pflichtanforderungen wird in TASK-7 geprueft.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ein dokumentierter manueller Start fuehrt vom Profil ueber Live-Suche, Abruf und Auswertung einer echten Bekanntmachung bis zum erzeugten PDF. Der Bericht ist dem Lauf und seinen Quellen zugeordnet.
- [x] #2 Das PDF enthaelt vorne eine Uebersicht aller ausgewaehlten Treffer und danach je Ausschreibung einen kompakten Steckbrief mit saemtlichen Pflichtangaben nach P-04. Quellen und Abrufdaten sind jeweils enthalten. Die Darstellung funktioniert mit einem und mehreren Treffern; Losbezuege bleiben eindeutig.
- [x] #3 Je Treffer sind Passungsbegruendung, Belege, Informationsluecken und offene Pruefpunkte verstaendlich sichtbar. Fehlende Angaben heissen nicht angegeben; Unsicherheit, Widersprueche und Verarbeitungsfehler werden davon unterschieden. Fachliche Passung und Informationsqualitaet sind getrennt erkennbar.
- [x] #4 Suchprofil, Recherchezeitpunkt, Quellenabdeckung und Recherchegrenzen sind angegeben. Vollstaendige TED-Bekanntmachungen sind als Analysegrundlage benannt. Links auf zusaetzliche Unterlagen tragen den Hinweis in dieser Version nicht abgerufen und nicht ausgewertet; diese Umfangsgrenze gilt nicht als Abruffehler oder erfolgte Pruefung.
- [x] #5 Erzeugte PDFs sind visuell auf Lesbarkeit, Vollstaendigkeit und brauchbare Belegverweise geprueft, auch bei langen Inhalten und mehreren Treffern. Eine leere Trefferliste und unvollstaendige Laeufe werden ehrlich dargestellt; ein fehlgeschlagener Abruf erscheint nicht als erfolgreiche Suche ohne Treffer. Mehrsprachige Titel, Pflichtfelder und Belegzitate sind im fertigen PDF in Normal- und Fettschrift visuell lesbar und im Originalwortlaut kopierbar.
- [x] #6 Die automatisch erzeugte Übersicht stellt Passung, Teilnahmestand und Teilnahmevoraussetzungen getrennt und verständlich dar.
- [x] #7 Ein dokumentierter Live-Durchlauf verarbeitet fünf echte Ausschreibungen von der TED-Suche bis zum visuell geprüften PDF.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Das einmalige Python-Skript für reports/ki-analyse-5-20261117-f3d2e93e/passung.html war eine temporäre Hilfslösung und gehört nicht zum regulären Berichtsgenerator.

Nachweise zu den Akzeptanzkriterien

- #1 und #7 (P-05, P-07, P-11): Der manuelle Start ist in README.md unter „Von der Suche zum PDF“ dokumentiert. Der Live-Lauf 20261120T002152076322Z-66ea73d6 vom 20.11.2026 umfasst vier erfolgreiche TED-Suchgruppen, fünf erfolgreich abgerufene Originale und zehn erfolgreiche Modellaufrufe einschließlich Gegenprüfung. Laufdaten, Analyse und PDF liegen lokal unter reports/live-review-20261120-0121/runs/20261120T002152076322Z-66ea73d6, die ursprüngliche Analyse unter analyses/20261120T002201-d1a090f7.
- #2 und #3 (P-04, P-07, P-08): Das Live-PDF zeigt sieben Lose aus fünf Bekanntmachungen mit TED-Quelle und Abrufzeit in Übersicht und Steckbriefen. tests/test_report.py prüft den Einzel- und Mehrlosbericht, Pflichtfelder, losbezogene Belege und Konflikte. Das aus denselben Originalen mit TASK-13 neu erzeugte PDF (Analyse 20261121T160037-441b5c6e) zeigt weiter ungeklärte Angaben und die unvollständige Auswertung ausdrücklich.
- #4 (P-05): Übersicht und Abschnitt „Suchprofil und Recherchegrenzen“ zeigen Recherchezeit, Suchgruppen, Abdeckung, Ergebnisgrenzen und die ausgewerteten vollständigen TED-Bekanntmachungen. Bei den Links auf zusätzliche Unterlagen steht der Hinweis, dass sie in dieser Version nicht abgerufen und nicht ausgewertet wurden.
- #5 (P-07, P-08, P-11): Die gerenderten Seiten mit Übersicht, langen Steckbriefen und Belegverzeichnis wurden visuell geprüft. tests/test_report.py prüft PDF-Ausgaben bei leerer Suche und Abruffehlern sowie lange Kriterien und interne Verweise. tests/test_report_fonts.py prüft mehrsprachige Titel, Pflichtfelder und Belege im gerenderten PDF und bei der Textextraktion in Normal- und Fettschrift.
- #6 (P-07, P-11): Die Übersicht führt Passung und Teilnahmestand je Los getrennt und nennt den gemeinsamen Status ungeklärter Teilnahmevoraussetzungen. test_overview_prioritizes_open_matches_and_links_to_each_lot prüft die Sortierung, den sichtbaren Status und die Verweise auf die jeweiligen Lossteckbriefe.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Der dokumentierte TED-Durchlauf erzeugte aus fünf echten Bekanntmachungen einen visuell geprüften PDF-Bericht mit sieben Lossteckbriefen. Verbleibende Informationslücken sind im Bericht sichtbar. Die Chemnitzer Passungsbewertung wird in TASK-14 verfolgt, die Demo-Abnahme in TASK-7. Auf 1ef68a8 bestanden 245 Tests sowie Ruff-Lint und Formatprüfung. Neun optionale Live-KI-Tests wurden beim Prüflauf übersprungen.
<!-- SECTION:FINAL_SUMMARY:END -->
