---
id: TASK-2
title: 2. TED-Bekanntmachungen fuer den ersten PDF-Lauf beschaffen
status: Done
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-17T11:47:00Z'
labels:
  - roadmap
dependencies:
  - TASK-1
documentation:
  - PROJECT.md
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ersten echten Recherchefall vorbereiten: Das konfigurierbare Profil liefert Kandidaten und vollstaendige TED-Bekanntmachungen mit nachvollziehbarer Herkunft. Regeln: PROJECT.md P-01, P-02, P-05 und P-10 sowie die dort festgehaltenen Projektentscheidungen. Sichere Mehrfachtreffer derselben Bekanntmachung werden bereits hier zusammengefuehrt; die weitergehende Konsolidierung von Verfahren, Losen und Berichtigungen gehoert zu TASK-5. Die Ergebnisliste ist eine Vorauswahl, keine Aussage ueber fachliche Eignung oder offene Teilnahme. Technische Umsetzung bleibt im vereinbarten Rahmen offen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ein ohne Codeaenderung anpassbares Suchprofil liefert echte TED-Kandidaten. Verwendetes Profil, Suchgrenzen, Herkunft und Abrufzeit sind nachvollziehbar; eine geaenderte Konfiguration wirkt auf die Suche.
- [x] #2 Fuer mindestens einen echten Kandidaten liegt die vollstaendige Bekanntmachung fuer die weitere Auswertung vor. Eingaben und abgerufene Inhalte bleiben dem jeweiligen Lauf nachvollziehbar zugeordnet und fuer dessen spaetere Pruefung erhalten.
- [x] #3 Sichere Mehrfachtreffer derselben Bekanntmachung werden zusammengefuehrt. Vorhandene Identitaets-, Los- und Versionshinweise bleiben erhalten; unsichere Zusammenhaenge werden nicht als geklaert ausgegeben.
- [x] #4 Vorhandene Links auf zusaetzliche Unterlagen bleiben erhalten. Nicht abgerufene zusaetzliche Unterlagen, fehlende Angaben, Abruffehler und eine leere Suche bleiben unterscheidbar. Es werden nur zulaessige oeffentliche Quellen verwendet; die Zugangs- und Nutzungsgrundlage ist dokumentiert.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Vom Nutzer am 16.11.2026 freigegebener Rahmen und verbindlicher Testkatalog.
Änderungen an den vereinbarten Tests und Erwartungen nur nach vorheriger ausdrücklicher Abstimmung mit dem Nutzer.

Umsetzungsplan:
1. Bestehende konfigurierbare TED-Suche weiterverwenden. Standard: Auftraggeber Deutschland, 90 Tage, maximal 20 Kandidaten. P-01/P-02/P-10.
2. Für alle Kandidaten innerhalb des Limits die vollständige TED-Bekanntmachung bevorzugt als Original-XML abrufen, prüfen und mit Herkunft zuordnen. Keine fest eingebauten Live-Treffer. P-05.
3. Jeden Lauf separat lokal erhalten: originales Profil, verwendete Einstellungen, Suchanfragen, Rohantworten, Dokumente, Quellen und Abrufzeiten. Teilweise erfolgreiche Läufe speichern; nach einzelnen Dokumentfehlern fortsetzen.
4. Nur sichere Mehrfachtreffer derselben Bekanntmachung zusammenführen. Suchherkünfte und vorhandene Identitäts-, Los- und Versionshinweise erhalten; Abweichungen und ungeklärte Zusammenhänge sichtbar lassen.
5. Zusätzliche Unterlagen ausschließlich verlinken. Nicht abgerufen/nicht ausgewertet, fehlende Angaben, leere Suche und Abruffehler unterscheiden.
6. Lesbare lokale Ergebnisübersicht mit Profil, Suchgrenzen, Kandidaten, Abrufstatus, Quellen und Verweisen auf gespeicherte Originale bereitstellen. Keine eigene Oberfläche zum Laden alter Läufe.
7. Automatisierte Tests mit kontrollierten Netzwerkantworten ausführen; echte TED-Abnahme und Live-Lauf mit geänderter Konfiguration dokumentieren. Offizielle Zugangs-/Nutzungsgrundlage prüfen. Bestehende Tests, Ruff und Formatprüfung ausführen.
Außerhalb: KI-Auswertung, Teilnahmeprüfung, PDF-Bericht, Download zusätzlicher Vergabeunterlagen und Konsolidierung verschiedener Bekanntmachungen eines Verfahrens.

Verbindlicher Testkatalog:
T2-01 - Profil wirkt auf die Suche. Bei festem Stichtag Suchbegriff, Land und Zeitraum in einer Testkonfiguration ändern und die tatsächlich gesendete Anfrage prüfen. Erwartung: Anfrage enthält exakt die geänderten Kriterien; gespeichertes Profil entspricht dieser Konfiguration. Ungültige Einstellungen erzeugen vor dem Abruf eine verständliche Fehlermeldung.
T2-02 - Bekanntmachungen vollständig beschaffen. Drei unterschiedliche Kandidaten liefern; Trefferlimit zwei. Für beide ausgewählten Kandidaten bekannte vollständige Dokumente bereitstellen. Erwartung: Genau diese beiden Bekanntmachungen werden abgerufen. Gespeicherte Originalinhalte stimmen vollständig mit den gelieferten Dokumenten überein; auch Inhalte außerhalb der Suchergebnisfelder bleiben erhalten. Nur die Netzwerkantworten werden im Test simuliert; echte Such-, Auswahl- und Speicherlogik läuft. Keine hardgecodeten TED-Treffer im Anwendungscode.
T2-03 - Läufe und Herkunft erhalten. Zwei Läufe mit unterschiedlichen Profilen und Dokumentständen ausführen. Erwartung: Beide Läufe bleiben getrennt; der zweite verändert keine Dateien des ersten. Profil, Suchanfragen, Rohantworten, Dokumente, Quellenadresse und Abrufzeit sind eindeutig zugeordnet. Vorhandene Identitäts-, Los- und Versionshinweise bleiben erhalten.
T2-04 - Nur sichere Dubletten zusammenführen. Dieselbe Veröffentlichungsnummer in zwei Suchgruppen liefern; zusätzlich eine andere Bekanntmachung desselben Verfahrens. Eine Variante enthält abweichende Angaben zur doppelten Nummer. Erwartung: Identische Bekanntmachung erscheint einmal und wird einmal heruntergeladen; beide Suchherkünfte bleiben erhalten. Andere Bekanntmachung bleibt getrennt. Abweichende Angaben bleiben nachvollziehbar und als ungeklärt sichtbar.
T2-05 - Zusätzliche Unterlagen nur verlinken. Eine Bekanntmachung enthält zwei Unterlagenlinks mit unterschiedlichen Losbezügen; eine weitere keine. Erwartung: Beide Links und Losbezüge bleiben erhalten; keine Anfrage an diese Unterlagen. Übersicht unterscheidet verlinkt/nicht abgerufen/nicht ausgewertet von kein Unterlagenlink angegeben.
T2-06 - Fehler und leere Ergebnisse unterscheiden. Getrennte Fälle: erfolgreiche Suche ohne Treffer; fehlender Titel; Ausfall einer Suchgruppe; drei Dokumentabrufe mit einem Fehler. Erwartung: Leere Suche, fehlende Angabe und Abruffehler unterscheidbar. Bereits erhaltene Daten bleiben gespeichert. Nach einem einzelnen Dokumentfehler werden übrige Dokumente weiter abgerufen; Lauf zeigt Unvollständigkeit.
T2-07 - Falsche Downloads erkennen. HTML-Fehlerseite, beschädigtes XML oder Dokument mit eindeutig abweichender Bekanntmachungsidentität liefern. Erwartung: Kein Fall gilt als erfolgreich beschaffte Bekanntmachung. Fehler und betroffener Kandidat nachvollziehbar; keine falsche Dokumentzuordnung.
T2-08 - Nach Programmende die Ergebnisübersicht und heruntergeladenen Bekanntmachungen eines abgeschlossenen Laufs lokal öffnen und prüfen. Lauf mit erfolgreichen und fehlgeschlagenen Abrufen verwenden. Erwartung: Übersicht zeigt Profil, Zeitpunkt, Grenzen und je Kandidat Titel bzw. nicht angegeben, Veröffentlichungsnummer, Suchgruppen, Quelle und Abrufstatus. Verweise auf gespeicherte Originale funktionieren. Kandidaten werden nicht als fachlich geeignet oder zur Teilnahme offen bezeichnet. Keine erneute Suche nötig.

Zusätzliche echte TED-Abnahme: Mindestens eine vollständige Bekanntmachung aus aktueller konfigurierter Suche abrufen, lokal öffnen und Identität sowie ausgewählte Inhalte mit Quelle vergleichen. Geänderte Konfiguration ebenfalls live ausführen und dokumentieren; unterschiedliche Trefferzahlen sind keine Voraussetzung. Offizielle Zugangs- und Nutzungsgrundlage für P-01/P-10 prüfen und dokumentieren. Live-Nachweise ergänzen automatisierte Tests für P-01/P-02/P-05.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Umgesetzt in c744f7c und 951c2a0: konfigurierbare TED-Suche mit getrennten Laufarchiven und vollstaendigen Bekanntmachungen. P-01/P-02/P-05/P-10: Standardlauf mit 20 Originalen unter reports/runs/20261117T110548605638Z-5e2b0549; geaendertes Copilot-Schulungsprofil mit einem Original unter reports/runs/20261116T155344846375Z-1aa8d91e. Dateien, Herkunft und Pruefsummen kontrolliert; oeffentliche TED-Zugangs- und Nutzungsgrundlage anhand offizieller Quellen geprueft, Links in README.md. T2-01 bis T2-09 sichern Konfigurationswirkung, Dubletten, Losbezuege, Unterlagenlinks und Fehlerfaelle ab. HTTP-Abbruchfehler behoben; 61 Tests, Ruff und Formatpruefung erfolgreich. Nutzer bestaetigt funktionierende Links in Chrome. Das Trefferlimit-Thema bleibt separat in TASK-10; KI-Auswertung und PDF sind nicht Teil dieses Tickets.
<!-- SECTION:FINAL_SUMMARY:END -->
