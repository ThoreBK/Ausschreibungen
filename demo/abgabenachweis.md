# Abgabenachweis für TASK-7

Projektbasis: `00fda0d8564a8169f7d70de25c9f6a9d65ef242a`.
Stand der Prüfung: 21.11.2026.

## Pflichtanforderungen

| ID | Konkreter Nachweis oder offene Lücke |
| --- | --- |
| P-01 | Der TED-Vorlauf lieferte vier erfolgreiche Suchanfragen und fünf Original-XMLs. Der anonyme `POST /v3/notices/search` ist für Weiterverwendung vorgesehen. Die gemessene Abrufmenge liegt innerhalb der für den Lauf relevanten TED-Obergrenzen. Die Weiterverwendung veröffentlichter Bekanntmachungen ist vorbehaltlich abweichender Hinweise und Drittrechte grundsätzlich zulässig. [Search API](https://docs.ted.europa.eu/api/latest/search.html), [Fair Usage](https://ted.europa.eu/en/news/fair-usage-policy-on-ted), [Nutzungshinweise](https://ted.europa.eu/en/legal-notice). |
| P-02 | [Standard-Suchprofil](../search-profile.toml) mit vier Leistungsblöcken, [Demoprofil](suchprofil.toml) und [Analyseprofil](../analysis-profile.toml) sind TOML-Dateien. Der TED-Vorlauf archiviert die geänderten Anfragen und das bytegleiche Suchprofil. `test_t2_01_changed_config_is_sent_and_archived` prüft die gesendete Abfrage und die gespeicherten Eingaben. `test_t4_06_profile_is_really_passed_to_both_model_steps` prüft die Profilübergabe in beiden Modellschritten. TASK-4 dokumentiert einen historischen Vergleich beim Profilwechsel mit einer offenen Gegenprüflücke. |
| P-03 | Quellenorakel für Hamburg Tourismus (passend), Pfalzwerke (unpassend), Merzig-Wadern (unklar) und Chemnitz (thematisch passend, Betriebsnachweis offen) in [expectations.json](../tests/fixtures/real/expectations.json). `test_report_selects_and_consolidates_before_applying_limit` prüft die Auswahl und Ausschlussgründe. Der Quellenabgleich der aktuellen Modellausgaben steht aus. Die bekannte Fehlbewertung von Chemnitz wird in TASK-14 verfolgt. |
| P-04 | `test_t4_01_saved_complete_fields_and_unchanged_original` und `test_real_oracles_match_original_and_structured_extraction` prüfen Feldwerte, Originale und Fundstellen. `test_report_includes_scoped_decisions_fields_and_sources` prüft die Darstellung. Der Quellenabgleich des frischen Beispiel-PDFs steht aus. |
| P-05 | Fünf vollständige Bekanntmachungen samt URL, Abrufzeit, XML und SHA-256 im TED-Vorlauf. `test_t2_05_document_links_keep_lots_without_fetch` prüft, dass Unterlagenlinks mit Losbezug erhalten bleiben. `test_t4_09_references_and_links_need_no_downloads` prüft die Umfangsgrenze. |
| P-06 | Sieben Suchvorkommen im TED-Vorlauf ergaben fünf verschiedene Bekanntmachungen. Die XMLs von Merzig-Wadern und Hamburg Tourismus wurden jeweils einmal gespeichert und beiden Suchgruppen zugeordnet. `test_report_selects_and_consolidates_before_applying_limit` prüft Zusammenführung, nachgelagertes Berichtslimit und früheren Berichtigungsstand. `test_reused_technical_lot_id_keeps_independent_deadlines` prüft die Losabgrenzung. Die Berichtigungen 799785-2026 und 810275-2026 enthalten referenzierte Vorgänger, die im Lauf fehlen. Der lokale Bericht zeigt dazu den offenen Prüfpunkt. Eine Berichtigung mit beiden Ständen ist im Vorlauf nicht belegt. |
| P-07 | `test_overview_prioritizes_open_matches_and_links_to_each_lot` prüft Reihenfolge und Verweise im Mehrtrefferbericht. `test_report_includes_scoped_decisions_fields_and_sources` prüft Steckbrieffelder und Belegverweise. Das visuell geprüfte Live-KI-Beispiel-PDF steht aus. |
| P-08 | `test_t4_02_citations_need_existence_content_and_scope` prüft Fundstellen und Losbezug. `test_t4_04_missing_uncertain_conflicting_and_errors` unterscheidet fehlend, unsicher, widersprüchlich und fehlerhaft. `test_partial_deadline_preserves_date_and_detects_conflict` verlangt, dass beide Quellen erhalten bleiben. Der fachliche Abgleich des aktuellen Modellurteils steht aus. |
| P-09 | `main.py --report` sucht öffentliche Daten, lädt Bekanntmachungen, analysiert sie und schreibt lokale Dateien. Abgabe- und Unterlagenlinks sind Information. `test_t4_07_bad_response_and_tool_actions_are_not_success` prüft die Abweisung unerwarteter Werkzeugaktionen. Im Anwendungsablauf gibt es keine Angebote, Zusagen oder Nachrichten. |
| P-10 | TED anonym. `codex login status` bestätigt ChatGPT. `test_other_auth_never_runs_a_model_or_api_fallback` prüft das Sperren anderer Anmeldearten. Git ignoriert Laufdaten, Umgebungs- und Schlüsseldateien. Im Git-Baum und in der Historie von `main` ergaben die geprüften Pfade und Schlüssel-/Tokenmuster keinen Fund außer der nur aus Kommentaren bestehenden `.env.example` beim Dateinamencheck. Das Analyseprofil enthält eine allgemeine Leistungsbeschreibung. Die KI-Übermittlung für die Generalprobe ist gesondert abzustimmen. |
| P-11 | Die [Kurzanleitung](README.md) enthält Einrichtung, Start und PDF-Pfad. Das Demoprofil wurde ohne Python-Änderung geladen und der Berichtseinstieg lokal nachvollzogen. Der strukturierte Vorlauf wurde in 22 A4-Seiten gerendert und auf Übersicht, Steckbriefe, Belege, Umbrüche und lesbare Zeichen geprüft. Die Prüfung des Beispiel-PDFs mit frischer KI-Auswertung steht aus. |
| P-12 | [Kurzanleitung](README.md) und [Projekt-README](../README.md) dokumentieren ungefähr 0 USD zusätzliche API-Gebühren bei Verwendung des ChatGPT-Kontos ohne API-Fallback. Codex-Kontingent oder vorhandene Guthaben werden entsprechend dem Tarif belastet. Messwerte aus aktueller Erstanalyse und Gegenprüfung stehen aus. [Codex-Nutzung nach Tarif](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan). |
| P-13 | Repository im eigenen Worktree, [Kurzanleitung](README.md), [Zusammenarbeit](zusammenarbeit.md) und dieser Nachweis. Beispiel-PDF aus der frischen Generalprobe und Repository-Zugang für die Empfänger stehen aus. |
| P-14 | Offene Definition. `PROJECT.md` und TASK-7 enthalten keinen verbindlichen Wortlaut für P-14. |
| P-15 | Die [Kurzanleitung](README.md) erklärt den Einstieg und drei Entscheidungen. Der TED-Vorlauf belegt Quelle, Profilwirkung, Abruf und Deduplizierung. Die Generalprobe mit KI-Gegenprüfung bis zum fachlich und visuell geprüften Beispiel-PDF steht aus. |
| P-16 | Offene Definition. `PROJECT.md` und TASK-7 enthalten keinen verbindlichen Wortlaut für P-16. |

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
