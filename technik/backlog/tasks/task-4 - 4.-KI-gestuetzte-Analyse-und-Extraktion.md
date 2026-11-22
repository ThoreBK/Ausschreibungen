---
id: TASK-4
title: 3. Pflichtangaben und belegte Passung fuer den ersten Bericht liefern
status: Done
assignee: []
created_date: '2026-11-13T17:25:00Z'
updated_date: '2026-11-17T22:07:00Z'
labels:
  - roadmap
dependencies:
  - TASK-2
documentation:
  - PROJECT.md
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Aus vollstaendigen Bekanntmachungen die Pflichtangaben und eine begruendete thematische Passung zum konfigurierten Profil liefern. Regeln: PROJECT.md P-02 bis P-05, P-08 und P-12 sowie die fachlichen Entscheidungen zu Extraktion, Belegen, Fristen und Dokumentinhalten. Das Ergebnis soll direkt fuer TASK-6 nutzbar sein. Die Pflichtangaben stehen bereits fest; zusaetzliche Gewichtungen, wirtschaftliche oder strategische Bewertungen und Teilnahmeempfehlungen sind keine Voraussetzung. Modell, Bibliotheken und interne Strukturen werden hier nicht vorgeschrieben.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Fuer mindestens eine echte Bekanntmachung sind alle Pflichtangaben aus P-04 vorhanden oder als nicht angegeben gekennzeichnet: Auftraggeber, Gegenstand, Ort, Verfahrensart, Fristen mit Datum und Uhrzeit, Laufzeit, Eignungs- und Zuschlagskriterien, Abgabeform und Quellenlink.
- [x] #2 Jede Sachangabe hat einen nachvollziehbaren Dokument- und Fundstellenbezug. Fundstellen werden auf Existenz und inhaltliche Stuetzung geprueft. Fehlende Angaben, Unsicherheit, Widersprueche und Verarbeitungsprobleme bleiben unterscheidbar; Angaben verschiedener Lose oder Dokumentstaende werden nicht vermischt.
- [x] #3 Fristen behalten Originalangabe, Fristart, Losbezug und Dokumentstand. Nur eindeutig interpretierbare Zeitangaben werden nach Europe/Berlin umgerechnet. Fehlende Uhrzeiten oder Zeitzonen werden nicht ergaenzt. ACTIVE allein begruendet keine offene Teilnahme; Bekanntmachungsart und belastbare Fristen werden beruecksichtigt, sonst bleibt die Teilnahmemoeglichkeit ungeklaert.
- [x] #4 Die thematische Passung wird anhand des ohne Codeaenderung anpassbaren Unternehmensprofils mit Belegen begruendet. Passende, unpassende und unklare Faelle sind unterscheidbar. Thematische Passung, Informationsqualitaet und belegte Teilnahmevoraussetzungen bleiben getrennt; ein Suchworttreffer allein gilt nicht als Passungsnachweis.
- [x] #5 Die Auswertung ist an echten, fachlich von Hand geprueften Beispielen mit erwarteten Angaben und Fundstellen abgesichert, einschliesslich eines unpassenden Treffers und fehlender Angaben. Die Grundlage fuer eine ungefaehre Kostenschaetzung des Beispielablaufs ist verfuegbar. Spaet erkannte Zusammenhaenge und nicht ausgewertete Unterlagen werden als belegte offene Pruefpunkte weitergegeben, ohne automatisches Nachladen.
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Vom Nutzer am 17.11.2026 freigegebener Umfang und konkretisierter Testkatalog. TASK-2 ist abgeschlossen. Dieser Plan bereitet die Umsetzung vor; der Ticketstatus bleibt To Do. Modell, Bibliotheken und interne Datenstrukturen bleiben im vereinbarten Rahmen offen.

Umsetzungsplan:
1. Vollständige gespeicherte TED-Bekanntmachungen samt Herkunft aus TASK-2 als Eingabe verwenden. Auswertung dem jeweiligen Lauf, Original und Dokumentstand nachvollziehbar zuordnen und für TASK-6 nutzbar speichern. Originale erhalten. P-05/P-08.
2. Sämtliche Pflichtangaben aus P-04 abdecken: Auftraggeber, Gegenstand, Ort, Verfahrensart, Fristen mit Datum und Uhrzeit, Laufzeit, Eignungs- und Zuschlagskriterien, Abgabeform und Quellenlink. Eindeutig strukturierte Fakten regelbasiert übernehmen; KI für Freitext und fachliche Zusammenhänge einsetzen. Fehlende Angaben ausdrücklich als nicht angegeben ausweisen.
3. Jede Sachangabe mit Dokument und konkreter Fundstelle verknüpfen. Fundstellen auf Existenz und inhaltliche Unterstützung prüfen; eine vorhandene Fundstelle allein genügt nicht. Unsicherheit, Widersprüche, fehlende Angaben und Verarbeitungsprobleme unterscheiden. Lose und Dokumentstände getrennt halten; ungeklärte Zusammenhänge als offene Prüfpunkte weitergeben. P-04/P-08.
4. Fristen mit Originalangabe, Fristart, Los und Dokumentstand erhalten. Nur eindeutige Zeitangaben nach Europe/Berlin umrechnen. Fehlende Uhrzeiten oder Zeitzonen nicht ergänzen. Bekanntmachungsart und belastbare Fristen berücksichtigen; ACTIVE allein begründet keine offene Teilnahme. Bei unzureichender Grundlage bleibt die Teilnahmemöglichkeit ungeklärt.
5. Unternehmensprofil als tatsächlich ausgelesene, ohne Codeänderung anpassbare Konfiguration bereitstellen und seine Verwendung verständlich dokumentieren. Thematische Passung mit Belegen als passend, unpassend oder unklar begründen. Suchworttreffer allein genügen nicht. Passung, Informationsqualität und belegte Teilnahmevoraussetzungen getrennt halten; unbekannte Voraussetzungen gelten nicht als erfüllt. P-02/P-03.
6. Mindestens eine echte Bekanntmachung vollständig auswerten. Verwendetes Profil, Modell und Verbrauch nachvollziehbar festhalten; ungefähre Kosten des Beispielablaufs mit Preisgrundlage und Stand dokumentieren. Zusätzliche Unterlagen als in dieser Version nicht abgerufen und nicht ausgewertet kennzeichnen; keine automatischen Nachlade- oder erneuten Analyseschleifen aufgrund später erkannter Zusammenhänge. P-05/P-12.
7. Automatisierte Tests mit unabhängig festgelegten Erwartungen und fachliche Prüfung echter Beispiele durchführen. Echte KI-Ergebnisse mit den Originalen abgleichen; simulierte KI-Antworten allein sind kein Qualitätsnachweis. Relevante Tests sowie uv run ruff check . und uv run ruff format --check . ausführen.

Abgrenzung:
- PDF-Erzeugung und vollständiger Start bis zum PDF: TASK-6.
- Auswahl, Zusammenführung und Sortierung mehrerer Bekanntmachungen einschließlich Berichtigungshistorien: TASK-5. Korrekte Losbezüge innerhalb der Auswertung gelten bereits hier.
- Download und Auswertung zusätzlicher Vergabeunterlagen: TASK-3.
- Ergebnisbekanntmachungen am Trefferlimit: eigenständiger Suchfehler in TASK-10; keine Erweiterung dieses Tickets um die Suchkorrektur.
- Keine zusätzlichen Gewichtungen, wirtschaftlichen oder strategischen Bewertungen oder Teilnahmeempfehlungen.

Testkatalog:
T4-01 - Pflichtangaben und Übergabe. Eine gespeicherte vollständige Bekanntmachung mit vorab von Hand festgelegten Feldwerten und Fundstellen auswerten, darunter Angaben außerhalb der Suchmetadaten. Erwartung: Alle P-04-Felder sind im gespeicherten Ergebnis vorhanden; enthaltene Angaben stimmen mit dem Original überein, tatsächlich fehlende heißen nicht angegeben. Quellenlink, Abrufzeit, Lauf und Dokumentstand sind zugeordnet. Ergebnis nach Programmende ohne erneuten Abruf lesbar; Original unverändert. Deckt ausgelassene Felder, bloße Metadatenauswertung und verlorene Herkunft ab.
T4-02 - Belege tragen die Aussage. Kontrollierte KI-Ausgaben mit korrekter Fundstelle, nicht existierender Fundstelle sowie existierender, aber sachlich unpassender Fundstelle prüfen. Erwartung: Nur die tatsächlich gestützte Aussage gilt als belegt. Die übrigen werden als unbestätigt oder fehlerhaft kenntlich und gelangen nicht als gesicherte Fakten in das Ergebnis. Fachliche Erwartungen vorab aus dem Dokument bestimmen, nicht aus der Extraktionsimplementierung ableiten. P-08.
T4-03 - Lose und Dokumentstände. Eine Bekanntmachung mit zwei Losen und unterschiedlichen Fristen bzw. Kriterien sowie zwei Dokumentstände mit abweichenden Angaben verwenden. Erwartung: Werte und Belege bleiben beim richtigen Los und Stand; keine Übertragung zwischen Losen, kein stilles Überschreiben oder Zusammenführen der Stände. Ungeklärte Zuordnungen bleiben sichtbar. P-04/P-08.
T4-04 - Informationsqualität. Getrennte Fälle mit tatsächlich fehlender Angabe, mehrdeutigem Text, zwei widersprüchlichen belegten Angaben und nicht verarbeitbarer Eingabe prüfen. Erwartung: Fehlend, unsicher, widersprüchlich und Verarbeitungsfehler sind unterscheidbar; beim Widerspruch bleiben beide Aussagen samt Belegen erhalten. Fehlende Voraussetzungen werden nicht als erfüllt oder automatisch als nicht erfüllt bewertet.
T4-05 - Fristen. Bei festem Prüfzeitpunkt eindeutig datierte Fristen mit Zeitzone im Winter und Sommer sowie fehlende Uhrzeit, fehlende Zeitzone, verschiedene Fristarten und bereits abgelaufene Frist prüfen. Erwartung: Vorab unabhängig bestimmte Berliner Zeiten stimmen; Original, Fristart, Los und Stand bleiben erhalten. Keine erfundenen Zeitbestandteile. Ergebnisbekanntmachung oder ACTIVE-Metadatum allein führen nicht zur Aussage einer offenen Teilnahme; unzureichende Grundlage bleibt ungeklärt.
T4-06 - Fachliche Passung und Konfigurationswirkung. Echte passende, unpassende und unklare Beispiele von Hand beurteilen; beim unpassenden Beispiel kommt ein Suchwort ohne passende Leistung vor. Dieselbe Bekanntmachung zusätzlich mit einem fachlich deutlich anderen Unternehmensprofil auswerten. Erwartung: Passung und Begründung berücksichtigen das tatsächlich geänderte Profil und die belegte Leistung. Fachliche Passung, Informationsqualität und Teilnahmevoraussetzungen bleiben getrennt. Bei kontrollierten Modellantworten die tatsächlich übergebene Profilkonfiguration prüfen; die fachliche Wirkung zusätzlich an echten KI-Ausgaben beurteilen. P-02/P-03.
T4-07 - Fehlerhafte KI-Ausgaben. Ungültige oder unvollständige Antwort, unbelegte zusätzliche Sachangabe und API-Ausfall simulieren. Erwartung: Keine scheinbar vollständige erfolgreiche Auswertung und keine erfundenen Ersatzwerte; betroffene Angaben bzw. Auswertung als fehlerhaft oder ungeklärt erkennbar. Bereits vorhandene Originale und nachvollziehbare Ergebnisse bleiben erhalten. P-08.
T4-08 - Dokumentinhalte sind Daten. Eine kontrollierte Dokumentvariante enthält eine Anweisung, das Profil zu ignorieren oder eine unbelegte positive Bewertung auszugeben. Erwartung: Keine Änderung der Toolsteuerung oder fachlichen Kriterien aufgrund dieser Anweisung; keine Übernahme unbelegter Aussagen als Fakten. Automatisierte Prüfungen um einen echten Modellversuch ergänzen; ein einzelner Versuch ist kein allgemeiner Sicherheitsnachweis.
T4-09 - Umfangsgrenzen und offene Prüfpunkte. Bekanntmachung mit Unterlagenlinks und belegtem Hinweis auf einen ungeklärten Zusammenhang auswerten. Erwartung: Links, Losbezug und Fundstellen bleiben erhalten; zusätzliche Unterlagen sind ausdrücklich nicht abgerufen und nicht ausgewertet. Relevante Lücken erscheinen als offene Prüfpunkte. Keine Anfrage an zusätzliche Unterlagen und kein dadurch ausgelöster weiterer Analyselauf. P-05/P-08.
T4-10 - Echte Abnahme und Kostenbasis. Mindestens einen echten passenden und einen echten unpassenden Fall sowie fehlende Angaben anhand gespeicherter Originale fachlich prüfen; mindestens eine Bekanntmachung vollständig auswerten. Erwartete Angaben und Fundstellen unabhängig von den erzeugten Ergebnissen festhalten und Abweichungen benennen. Verwendetes Profil, Modell, Verbrauch und datierte Preisgrundlage ermöglichen eine nachvollziehbare ungefähre Kostenschätzung des Beispielablaufs. P-02/P-03/P-04/P-05/P-08/P-12.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Abschluss am 17.11.2026 vom Nutzer ausdrücklich freigegeben. Die frühere Planangabe zum unveränderten Status To Do ist historisch; diese Freigabe erlaubt jetzt den Abschluss.

Nachweise zu den Akzeptanzkriterien:
1. P-04/P-05: Vollständiger echter Fall 773064-2026 unter reports/acceptance/positive-ae1ecf21/analyses/20261117T152629-0ca6c69b/analysis.json. Unabhängige Feld- und Fundstellenerwartungen stehen in tests/fixtures/real/expectations.json; test_t4_01_saved_complete_fields_and_unchanged_original und test_real_oracles_match_original_and_structured_extraction sichern Pflichtfelder und Originale ab.
2. P-08: Fundstellen-, Inhalts- und Losprüfung sowie sichtbare fehlende, unsichere, widersprüchliche und fehlerhafte Angaben sind durch T4-02 bis T4-04, T4-07 und die Regressionen in tests/test_verification.py und tests/test_bundled_analysis.py abgesichert. Gespeicherte Modellurteile ergänzen die lokale Belegprüfung. Strittige Aussagen bleiben erhalten. Mocks belegen Verarbeitung, nicht fachliche Modellqualität.
3. Fristen: T4-05 und ergänzende Fristtests prüfen Winter-/Sommerzeit, fehlende Zeitbestandteile, Fristarten, Losbezug und Teilnahmebewertung unabhängig von ACTIVE. Der echte Fall 788030-2026 erhält die Frist ohne Zeitzone als ungeklärt; Nachweis unter reports/acceptance/missing-b7bec142/analyses/20261117T154352-81954872/analysis.json.
4. P-02/P-03: Fachliche Erwartungen für passende, unpassende und unklare Fälle sind in tests/fixtures/real/expectations.json festgehalten. Echte Ergebnisse: positive-ae1ecf21 (passend), negative-2ed6b621 (alle drei Lose unpassend), unclear-a297f799 (unklar). changed-profile-7737695a zeigt die geänderte Passung bei geändertem Profil; dieser historische Lauf enthält zugleich offene fachliche Gegenprüfpunkte und wird nicht als vollständig fehlerfrei dargestellt. T4-06 prüft die tatsächliche Profilübergabe; Passung, Informationsqualität und Teilnahmevoraussetzungen bleiben getrennt.
5. P-05/P-12: Echte Beispiele und Originalquellen liegen unter reports/acceptance/; tests/fixtures/real/expectations.json enthält unabhängig festgelegte Sollwerte. T4-09 prüft offene Prüfpunkte und Unterlagenlinks ohne Nachladen. README.md dokumentiert die Umfangsgrenze und die datierte Kostenbasis: ChatGPT-Kontingent, keine zusätzlichen API-Kosten. Gemessene Verbrauchs- und Laufzeitdaten stehen unter reports/task11-compact-check-ac9536c2/measured-comparison.json. Der dort dokumentierte Validierungsfix ist per Offline-Replay geprüft, nicht durch einen erneuten Live-Lauf.

Unmittelbar vor der Abschlussfreigabe: uv run pytest -q mit 172 bestandenen und 8 übersprungenen Tests; uv run ruff check . und uv run ruff format --check . erfolgreich. In diesem Abschlussvorgang keine neuen Modellaufrufe.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pflichtangaben und begründete thematische Passung aus vollständigen Bekanntmachungen sind für die Weiterverarbeitung in TASK-6 verfügbar. Originale, Fundstellen, Lose, Dokumentstände, Unsicherheiten und Fristen bleiben nachvollziehbar. Echte passende, unpassende, unklare und unvollständige Beispiele sowie unabhängige Erwartungen und Offline-Tests bilden die Nachweisgrundlage; Kostenbasis und Modellverbrauch sind dokumentiert.

Alle fünf Akzeptanzkriterien sind mit den oben zugeordneten Nachweisen abgeschlossen. KI-Urteile bleiben fachlich kontrollbedürftig. PDF-Erstellung, Mehrtrefferauswahl und zusätzliche Unterlagen gehören weiterhin zu TASK-6, TASK-5 und TASK-3. Das gemeinsame Review von TASK-11/TASK-12 sowie weitere Verbrauchsoptimierung werden separat behandelt; deren Ticketstatus wird hier nicht verändert.
<!-- SECTION:FINAL_SUMMARY:END -->
