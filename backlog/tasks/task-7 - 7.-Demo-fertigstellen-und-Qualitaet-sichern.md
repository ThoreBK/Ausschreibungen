---
id: TASK-7
title: 6. Pflichtanforderungen pruefen und abgabefaehige Demo fertigstellen
status: To Do
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-16T12:55:00Z'
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
Den gemeinsamen Ablauf aus Recherche, Extraktion, Auswahl, Konsolidierung und PDF absichern und die Abgabe vervollstaendigen. Verbindliche Pruefgrundlage sind PROJECT.md P-01 bis P-16 sowie die dort vereinbarten Projektentscheidungen. Fuer jede Kennung wird ein konkreter Nachweis oder eine offene Luecke festgehalten; die Regeln muessen nicht erneut aus der Aufgabenstellung abgeleitet werden. Dieses Ticket prueft die vollstaendige Demo, waehrend TASK-6 bereits vorher einen ersten Bericht liefert. Zusaetzliche Unterlagen, KI-Vorpruefung und Zeitsteuerung bleiben nachgelagerte Erweiterungen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Eine Generalprobe zeigt einen manuell gestarteten echten Lauf vom ohne Codeaenderung angepassten Profil ueber TED, Auswertung und Zusammenfuehrung mehrerer Treffer bis zum PDF. Der Lauf ist anhand der dokumentierten Einrichtung wiederholbar; gespeicherte Eingaben und Ergebnisse machen ihn nachvollziehbar. Eine Code-Stelle und zwei bis drei wesentliche Entscheidungen koennen erklaert werden.
- [ ] #2 Fuer P-01 bis P-16 ist im Ticket jeweils der konkrete Nachweis verlinkt oder beschrieben: geeignete Tests, Beispieldaten, Bericht, Dokumentation oder manuelle Pruefung. Offene Luecken werden ausdruecklich genannt; unbelegte Erfuellungsaussagen genuegen nicht. Automatisierte Pruefungen ersetzen keine fachliche Beleg- oder visuelle PDF-Pruefung.
- [ ] #3 Die relevanten Tests sowie ruff check und ruff format --check bestehen. Fachliche Prueffaelle umfassen passende und unpassende Treffer, leere Ergebnisse, Abruf-/Verarbeitungsfehler, fehlende und widerspruechliche Angaben, unklare Fristen, Bekanntmachungsarten, mehrere Lose, Dubletten und Berichtigungen. Grundlegende Tests entstehen bereits in den umsetzenden Tickets.
- [ ] #4 Das Abgabepaket enthaelt Repository, kurze Doku zu Einrichtung, Start, Aufbau, Entscheidungen, Grenzen und ungefaehren Laufkosten sowie ein Beispiel-PDF aus einem echten Lauf. Der Nutzer kann den Zugriff fuer die Empfaenger bereitstellen. Der Start ist ohne Programmierkenntnisse nachvollzogen und das PDF ohne Zusatzwissen verstaendlich.
- [ ] #5 Eine halbe Seite dokumentiert anhand tatsaechlicher Beispiele die Arbeit mit dem Coding-Agenten, dessen Hilfe und bewusste abweichende Entscheidungen des Nutzers. Fehlende Beispiele werden mit dem Nutzer geklaert und nicht erfunden.
- [ ] #6 Oeffentliche und zulaessige Datenzugaenge, fehlende Geheimnisse im abzugebenden Repository, Vertraulichkeit und die Grenze zur menschlichen Entscheidung sind geprueft. Der Ablauf reicht nichts ein, versendet nichts und sagt nichts zu. Der konkrete Abgabetermin wird aus dem tatsaechlichen Empfangsdatum mit dem Nutzer geklaert; ein Datum wird nicht angenommen.
<!-- AC:END -->
