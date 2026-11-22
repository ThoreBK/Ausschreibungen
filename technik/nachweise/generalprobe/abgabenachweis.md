# Abgabenachweis für TASK-7

Projektbasis: `00fda0d8564a8169f7d70de25c9f6a9d65ef242a`.
Stand der Prüfung: 21.11.2026.

## Pflichtanforderungen

| ID | Konkreter Nachweis oder offene Lücke |
| --- | --- |
| P-01 | Die Generalprobe lieferte vier erfolgreiche Suchanfragen und fünf Original-XMLs. Der anonyme `POST /v3/notices/search` ist für Weiterverwendung vorgesehen. Die gemessene Abrufmenge liegt innerhalb der für den Lauf relevanten TED-Obergrenzen. Die Weiterverwendung veröffentlichter Bekanntmachungen ist vorbehaltlich abweichender Hinweise und Drittrechte grundsätzlich zulässig. [Search API](https://docs.ted.europa.eu/api/latest/search.html), [Fair Usage](https://ted.europa.eu/en/news/fair-usage-policy-on-ted), [Nutzungshinweise](https://ted.europa.eu/en/legal-notice). |
| P-02 | [Standard-Suchprofil](../../search-profile.toml) mit vier Leistungsblöcken, [Demoprofil](suchprofil.toml) und [Analyseprofil](../../analysis-profile.toml) sind TOML-Dateien. Die Generalprobe archiviert die geänderten Anfragen und das bytegleiche Suchprofil. `test_t2_01_changed_config_is_sent_and_archived` prüft die gesendete Abfrage und die gespeicherten Eingaben. `test_t4_06_profile_is_really_passed_to_both_model_steps` prüft die Profilübergabe in beiden Modellschritten. Beim historischen Vergleich zu TASK-4 ergab dieselbe Originaldatei `773064-2026.xml` unter dem KI-Profil „passend“ und mit dem Dachdeckerprofil „unpassend“. Die SHA-256 war identisch. Im zweiten Lauf blieben zwei andere Aussagen unbestätigt. |
| P-03 | Quellenorakel für Hamburg Tourismus (passend), Pfalzwerke (unpassend), Merzig-Wadern (unklar) und Chemnitz (thematisch passend, Betriebsnachweis offen) in [expectations.json](../../tests/fixtures/real/expectations.json). `test_report_selects_and_consolidates_before_applying_limit` prüft die Auswahl und Ausschlussgründe. Im frischen Lauf belegen die Losbeschreibungen die Passung bei Hamburg Tourismus, Chemnitz und HPA. Alle Pfalzwerke-Lose wurden korrekt ausgeschlossen. **Offene Lücke:** Merzig-Wadern wurde ohne ausreichenden Beleg als passend in die Übersicht aufgenommen. |
| P-04 | `test_t4_01_saved_complete_fields_and_unchanged_original` und `test_real_oracles_match_original_and_structured_extraction` prüfen Feldwerte, Originale und Fundstellen. `test_report_includes_scoped_decisions_fields_and_sources` prüft die Darstellung. Der Quellenabgleich der vier Steckbriefe bestätigt insbesondere Fristarten, Termine, Laufzeit und Zuschlagsgewichtung in den unten genannten Stichproben. **Offene Lücken:** Der Hamburger Steckbrief zeigt eine Sprachanforderung als Leistungsort. Bei Chemnitz steht die Pflicht zur elektronischen Abgabe im Detailbeleg, während der Steckbrief nur „zulässig“ sagt. |
| P-05 | Fünf vollständige Bekanntmachungen samt URL, Abrufzeit, XML und SHA-256 in der Generalprobe. `test_t2_05_document_links_keep_lots_without_fetch` prüft, dass Unterlagenlinks mit Losbezug erhalten bleiben. `test_t4_09_references_and_links_need_no_downloads` prüft die Umfangsgrenze. |
| P-06 | Sieben Suchvorkommen ergaben fünf verschiedene Bekanntmachungen mit sieben Losen. Die XMLs von Merzig-Wadern und Hamburg Tourismus wurden jeweils einmal gespeichert und beiden Suchgruppen zugeordnet. `test_report_selects_and_consolidates_before_applying_limit` prüft Zusammenführung, nachgelagertes Berichtslimit und früheren Berichtigungsstand. `test_reused_technical_lot_id_keeps_independent_deadlines` prüft die Losabgrenzung. Die Berichtigungen 799785-2026 und 810275-2026 enthalten referenzierte Vorgänger, die im Lauf fehlen. Der Beispielbericht zeigt dazu den offenen Prüfpunkt. Die Übersicht priorisiert den Teilnahmestand, die belegte Passung und die jeweils nächste eindeutige Einreichungsfrist. Eine vollständige Berichtigungskette wurde im Live-Lauf nicht gefunden. |
| P-07 | `test_overview_prioritizes_open_matches_and_links_to_each_lot` prüft Reihenfolge und Verweise im Mehrtrefferbericht. `test_report_includes_scoped_decisions_fields_and_sources` prüft Steckbrieffelder und Belegverweise. Beispiel-PDF S. 1 mit vier ausgewählten Losen, S. 2–7 mit Steckbriefen, Quelle und Abrufzeit, S. 7–29 mit Belegverzeichnissen und Recherchegrenzen. Alle 29 gerenderten Seiten visuell geprüft. |
| P-08 | `test_t4_02_citations_need_existence_content_and_scope` prüft Fundstellen und Losbezug. `test_t4_04_missing_uncertain_conflicting_and_errors` unterscheidet fehlend, unsicher, widersprüchlich und fehlerhaft. `test_partial_deadline_preserves_date_and_detects_conflict` verlangt, dass beide Quellen erhalten bleiben. HPA: Frist- und Referenzkonflikt werden mit den Originalwerten gezeigt. Pfalzwerke: Die Gegenprüfung verwirft eine vermeintliche Rückfragefrist. **Offene Lücke:** Bei Merzig-Wadern existiert das Zitat, trägt aber das positive Passungsurteil nicht. |
| P-09 | `main.py --report` sucht öffentliche Daten, lädt Bekanntmachungen, analysiert sie und schreibt lokale Dateien. Abgabe- und Unterlagenlinks sind Information. `test_t4_07_bad_response_and_tool_actions_are_not_success` prüft die Abweisung unerwarteter Werkzeugaktionen. Die zehn gespeicherten Modellantworten enthalten die übergebenen Daten, Modellaktivität und JSON-Antworten. Der Ablauf löst keine Abgabe, Nachricht oder Zusage aus. |
| P-10 | TED anonym. `codex login status` bestätigt ChatGPT. `test_other_auth_never_runs_a_model_or_api_fallback` prüft das Sperren anderer Anmeldearten. Git ignoriert Laufdaten, Umgebungs- und Schlüsseldateien. Im Git-Baum und in der Historie von `main` ergaben die geprüften Pfade und Schlüssel-/Tokenmuster keinen Fund außer der nur aus Kommentaren bestehenden `.env.example` beim Dateinamencheck. Das Analyseprofil enthält eine allgemeine Leistungsbeschreibung. Der Nutzer hat die Übermittlung an OpenAI für diese Generalprobe freigegeben. Anmeldeinformationen werden nicht in den Laufdaten abgelegt. |
| P-11 | Die [Kurzanleitung](README.md) enthält Einrichtung, Start und PDF-Pfad. Das Demoprofil wurde ohne Python-Änderung geladen und der Berichtseinstieg lokal nachvollzogen. Das 29-seitige Beispiel-PDF wurde auf Lesbarkeit, Umbrüche und nutzbare Verweise geprüft. Der Hinweis zum unvollständigen Lauf ist auf S. 1 sichtbar. Bei Merzig-Wadern bleibt die Bewertung fachlich nachzuprüfen. |
| P-12 | [Kurzanleitung](README.md) und [Projektdokumentation](../../../DOKU.md) dokumentieren ungefähr 0 USD zusätzliche API-Gebühren bei Verwendung des ChatGPT-Kontos ohne API-Fallback. Codex-Kontingent oder vorhandene Guthaben werden entsprechend dem Tarif belastet. Im Beispielablauf wurden 312.007 Eingabe- und 47.287 Ausgabetokens für zehn Aufrufe gemessen. Die Recherche und Analyse dauerten rund 17 Minuten. [Codex-Nutzung nach Tarif](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan). |
| P-13 | Repository im eigenen Worktree, [Kurzanleitung](README.md), [Zusammenarbeit](zusammenarbeit.md) und dieser Nachweis. Beispiel-PDF und ein lokal klonbares Git-Bundle liegen im Abgabepaket. **Offen:** Empfängerkreis und Zugang zum vorgesehenen Repository. |
| P-14 | Offene Definition. `PROJECT.md` und TASK-7 enthalten keinen verbindlichen Wortlaut für P-14. |
| P-15 | Die [Kurzanleitung](README.md) erklärt den Einstieg und drei Entscheidungen. Der in diesem Dokument protokollierte Lauf erreichte mit echter Gegenprüfung das visuell geprüfte Beispiel-PDF. Die Auswertung meldet `incomplete` mit Exitcode 1. Die offenen Fachbefunde stehen weiter unten. |
| P-16 | Offene Definition. `PROJECT.md` und TASK-7 enthalten keinen verbindlichen Wortlaut für P-16. |

## Generalprobe vom 21.11.2026

Historischer Aufruf mit der damaligen Ordnerstruktur. Der aktuelle Aufruf steht in
der [Anleitung zur Generalprobe](README.md).

~~~powershell
. .\dev.ps1
uv run main.py --report --config demo/suchprofil.toml --as-of 2026-11-21 --output reports/task-7/ted-results.json
~~~

Lauf `20261121T183204101192Z-03419e90`, Analyse `20261121T183213-cd408336`.
Die Recherche startete um 19:32 MEZ. Vier öffentliche TED-Suchabfragen lieferten
2, 2, 2 und 1 Vorkommen ohne Trefferlimit. Fünf eindeutige Bekanntmachungen
wurden als vollständige XML-Dateien gespeichert. Die beiden Doppelvorkommen
von Merzig-Wadern und Hamburg Tourismus behalten ihre zwei Suchgruppen in der
Herkunft.

Der Laufordner `reports/task-7/runs/20261121T183204101192Z-03419e90/`
enthält `overview.html`, `results.json` mit TED-Anfragen und Rohantworten,
das Suchprofil und die unveränderten XMLs mit SHA-256. Im Unterordner
`analyses/20261121T183213-cd408336/` liegen Analyseprofil, `analysis.html`,
`analysis.json`, `bericht.pdf` und die archivierten Modellanfragen und Antworten
unter `model/`. Der Bericht verweist auf die lokale Auswertung und auf TED.
Die Rohdaten enthalten veröffentlichte Angaben aus den Bekanntmachungen.

Die Suche war vollständig. Alle fünf Erstanalysen und fünf Gegenprüfungen
mit `gpt-6.2-sol` über ChatGPT antworteten erfolgreich. Der fachliche
Analysestatus lautet `incomplete` mit Exitcode 1. Bei HPA, Pfalzwerke und
Hamburg Tourismus wurden zusätzliche Vorschläge verworfen oder blieben
unbestätigt. Das PDF zeigt vorne den unvollständigen Status.
`analysis.json` belegt 312.007 Eingabe- und 47.287 Ausgabetokens. Davon
entfielen 158.907 Eingabe- und 21.501 Ausgabetokens auf die Erstanalyse,
153.100 Eingabe- und 25.786 Ausgabetokens auf die Gegenprüfung.

Die PDF-Erstfassung hatte 32 Seiten und enthielt eine Seite mit nur einem
verwaisten Zitatrest. Kurze Fortsetzungen können jetzt auf derselben Seite
mit dem nächsten Abschnitt stehen. Der überarbeitete Generator hat das
29-seitige Beispiel aus denselben archivierten TED- und Analysedaten erzeugt.
Die Modellantworten und die Erstfassung bleiben im Worktree archiviert.
Alle Seiten wurden gerendert und visuell kontrolliert. SHA-256 des Beispiels:
`86cf5d72d9ec3c25bfdae015d27df9917285851de101026ab104e23c45552267`.

## Abgleich des Beispiels mit den Originalen

- **Hamburg Tourismus, S. 2–3.** Die Leistungsbeschreibung trägt den Profilbezug.
  `ParticipationRequestReceptionPeriod` belegt den 07.12.2026, 11:00 MEZ.
  Die Rückfragefrist steht getrennt. `PlannedPeriod` nennt unbefristet.
  Die Versicherungssummen von je 3 Mio. EUR haben einen Originalbeleg.
  Die Angabe zur deutschen Sprache steht im XML als Freitext bei `RealizedLocation`.
  Sie beschreibt die Plattform. Im Steckbrief erscheint sie irreführend als Leistungsort.
- **Merzig-Wadern, S. 3.** Die strukturierte Angebotsfrist, 48 Monate
  Laufzeit sowie 60 % Leistung/Qualität und 40 % Preis stimmen mit dem
  Original überein. Die Eignungsdetails sind an die Vergabeunterlagen
  verwiesen. `claim_reviews` für `fit` zeigt die KI-Bestätigung „passend“.
  Beleg [3] nennt Einführung und Lizenzen. Eine konkrete Beratungs- oder
  Entwicklungsleistung bleibt offen. Der Steckbrief empfiehlt die
  Nachprüfung des Einführungsumfangs. Die Übersicht zählt das Los dennoch
  zu den drei fachlich passenden Losen mit offener Frist.
- **Chemnitz, S. 4–5.** Belege [3, 4] tragen die thematische Passung über
  die semantische Analyse der Eingangspost. Angebotsfrist 18.12.2026,
  09:00 MEZ, Bindefrist 43 Tage und unbefristete Laufzeit sind getrennt.
  Die Zuschlagsgewichte 60/20/20 stimmen. Der Steckbrief zeigt „elektronische
  Abgabe zulässig“. `cbc:Note` in Beleg [68] verlangt die ausschließliche
  elektronische Abgabe über das Portal. Diese Einschränkung steht im Detail.
- **Hamburg Port Authority, S. 5–7.** Beleg [3] unterscheidet
  Initialabruf und optionale Agentenentwicklung. [1, 2] belegen
  die Zeitzonenabweichung. [21, 22, 23, 24] belegen zwei bzw. drei Jahre
  Erfahrung für denselben Referenznachweis. Der Teilnahmestand und die
  genaue Eignungsanforderung bleiben offen.
- **Pfalzwerke, `analysis.html`.** Alle drei Lose wurden in der Analyse
  als sachlich unpassend und abgelaufen ausgeschlossen. Die Dauer 20,
  21 bzw. 21 Monate bleibt je Los zugeordnet. Der Prüfvermerk zu `facts:0`
  begründet die Ablehnung einer angeblichen Rückfragefrist je Los.
  Die Passage fordert lediglich die Klärung alternativer Zertifizierungen
  vor der Angebotsfrist.

Die Prüfung umfasst die oben genannten konkreten Stichproben sowie die
sichtbare Feldabdeckung aller vier Steckbriefe. Vollständige Originale stehen
neben der Auswertung. Zusätzliche Vergabeunterlagen bleiben verlinkt.

## Sollwerte vor dem Modelllauf

| TED und Los | Erwartung aus dem Original |
| --- | --- |
| 810275-2026, LOT-0000 | Hamburg Port Authority. Beratung, Konzeption, Pilotierung, Umsetzung und Befähigung für KI-Agenten im Bauwesen. Thematisch passend. Beim Fristdatum `2027-01-07+01:00` und der Uhrzeit `10:00:00+02:00` widersprechen sich die Offsets im selben Fristknoten. Teilnahmefrist bleibt ungeklärt. [TED](https://ted.europa.eu/de/notice/-/detail/810275-2026). |
| 800874-2026, LOT-0000 | Stadt Chemnitz. Die Losbeschreibung verlangt semantische LLM-Analyse gescannter Posteingänge. Thematisch passend. Betrieb des Inferenzdienstes bleibt ungeklärt. Einreichung laut XML 18.12.2026, 09:00 MEZ. [TED](https://ted.europa.eu/de/notice/-/detail/800874-2026). |
| 799785-2026, LOT-0000 | Landkreis Merzig-Wadern. Beschaffung und Einführung einer Assistenzplattform mit zunächst 180 Lizenzen. Konkrete Beratungs- oder Entwicklungsleistungen bleiben auf Grundlage der Losbeschreibung offen. Einreichung 16.12.2026, 23:59 MEZ, Planlaufzeit 48 Monate, Gewichtung Leistung/Qualität 60 und Preis 40. [TED](https://ted.europa.eu/de/notice/-/detail/799785-2026). |
| 798622-2026, LOT-0001 bis LOT-0003 | Pfalzwerke Netz. Stahl, Leiterseile und Erdseil mit Lichtwellenleitern. Microsoft 365 wird im Zusammenhang mit einer Fristverlängerung genannt. Alle drei Lose unpassend. Einreichungsfrist je 17.11.2026, 11:00 MEZ, am Stichtag abgelaufen. Planlaufzeit je Los 20, 21 und 21 Monate. [TED](https://ted.europa.eu/de/notice/-/detail/798622-2026). |
| 773064-2026, LOT-0001 | Hamburg Tourismus. Multi-LLM-Plattform mit Beratung, Migration, Entwicklung und Enablement. Thematisch passend. Teilnahmeantrag 07.12.2026, 11:00 MEZ. Betrieb und Teilnahmevoraussetzungen bedürfen der gesonderten Prüfung. [TED](https://ted.europa.eu/de/notice/-/detail/773064-2026). |

Die Losbeschreibungen stehen in den XMLs unter
`/ContractNotice/cac:ProcurementProjectLot[n]/cac:ProcurementProject[1]/cbc:Description[1]`.
Die vollständigen indizierten Frist- und Kriterienpfade stehen im
Quellenverzeichnis der Analyse.

## Automatisierte Prüfungen

`uv run pytest`: 245 bestanden, 9 optionale Live-Modelltests übersprungen.
`uv run ruff check .` und `uv run ruff format --check .`: erfolgreich.
Pytest verwendete einen kurzen temporären Pfad im Worktree. Der übliche
Windows-Temp-Pfad war in dieser Sitzung nicht zugänglich.

| Prüffall aus TASK-7 #3 | Test und fachliches Ergebnis |
| --- | --- |
| Leere Suche und Abruffehler | `test_report_cli_distinguishes_empty_and_failed` prüft PDF-Text und unterschiedliche Exitcodes. `test_partial_download_keeps_success_and_failed_notice` behält den erfolgreichen Treffer und meldet den Abruffehler. |
| Verarbeitungsfehler | `test_t4_07_invalid_model_never_becomes_complete` hält unbrauchbare Modellausgaben vom erfolgreichen Analysestatus fern. `test_original_integrity_failure_is_visible` prüft den sichtbaren Prüfsummenfehler. |
| Fehlende und widersprüchliche Angaben | `test_t4_04_missing_uncertain_conflicting_and_errors` unterscheidet die Zustände. `test_duration_conflict_from_duplicate_reaches_brief` erhält den in der Dublette gefundenen Konflikt bis ins PDF. |
| Unklare und falsche Fristarten | `test_deadline_in_finished_pdf` prüft Text und Teilnahmestand bei Zeitkonflikten, ohne Uhrzeit und mit abweichenden Zeitzonen. `test_request_for_questions_does_not_replace_participation_deadline` hält Rückfrage- und Einreichungsfrist getrennt. |
| Bekanntmachungsarten | `test_award_with_historical_questions_stays_closed_in_pdf` lässt einen Zuschlag mit historischen Rückfragen geschlossen. `test_prior_information_distinguishes_planning_and_call_for_competition` unterscheidet Planung und Teilnahmeaufruf. |
| Lose, Dubletten und Berichtigungen | `test_report_selects_and_consolidates_before_applying_limit` prüft konkrete Loszuordnungen, Berichtsauswahl und beide Stände. `test_real_correction_without_predecessor_leaves_source_and_open_question` behält den Hinweis bei fehlendem Vorgänger. |

## Offene Angaben zur Abgabe

Empfangsdatum, Fristregel, konkreter Termin, Übermittlungsweg und Empfängerkreis
sind abzustimmen. Den Repository-Zugang für die Empfänger stellt der Nutzer bereit.
Die Beispiel-PDF-Navigation zur lokalen Analyse benötigt die benachbarte
`analysis.html`. Originale und Fundstellen bleiben im Laufordner nachvollziehbar.
