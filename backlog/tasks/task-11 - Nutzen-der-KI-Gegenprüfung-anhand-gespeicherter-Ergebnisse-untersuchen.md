---
id: TASK-11
title: KI-Gegenprüfung verbessern und Anfrageumfang reduzieren
status: To Do
assignee: []
created_date: '2026-11-17T17:09:00Z'
updated_date: '2026-11-17T23:00:00Z'
labels: []
dependencies: []
references:
  - reports/acceptance/
  - reports/full-check-988aaffb/
  - reports/ki-analyse-5-20261117-f3d2e93e/
  - reports/gegenpruefung-nutzen-69d7996-offline/vergleich.json
documentation:
  - PROJECT.md
type: enhancement
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Die Gegenprüfung aus TASK-4 erkennt fachliche Fehler, verwirft jedoch auch belegte Aussagen und bestätigt teilweise falsche Feldzuordnungen. Auf Grundlage der gespeicherten Protokolle sollen ihre Nachvollziehbarkeit und ihr gezielter Einsatz verbessert sowie doppelte Anfrageinhalte reduziert werden (P-03/P-04/P-08/P-12; Projektentscheidungen zu Extraktion, Belegbarkeit und Informationsqualität).

Vereinbarter Umfang:
- Doppelte Inhalte innerhalb einzelner Anfragen reduzieren: Originaltexte einmal übergeben und strukturierte Angaben sowie Vorschläge möglichst über eindeutige Fundstellen darauf beziehen. Quellenabdeckung, Feldbedeutung, Loszuordnung, Dokumentstand und Unsicherheiten erhalten; keine stille Textkürzung.
- Gegenprüfung nachvollziehbar machen: je geprüfter Aussage bestätigt, widerlegt oder nicht entscheidbar mit kurzer Begründung und betroffener Fundstelle. Lokale Belegprüfung und fachliches Modellurteil getrennt behandeln. Belegte, strittige Aussagen als offene Prüfpunkte erhalten; Ablehnung nicht mit fehlender Quellenangabe verwechseln.
- Gegenprüfung gezielter einsetzen: bereits regelbasiert geprüfte strukturierte Fakten und identische Wiederholungen davon nicht erneut durch das Modell prüfen. Fachliche Interpretationen einschließlich Feldzuordnung, Passungsbegründung, Negationen, Widersprüchen und losübergreifenden Aussagen weiterhin prüfen. Ein Originalzitat allein rechtfertigt keine Ausnahme. Prüfbedarf anhand transparenter Regeln bestimmen, ohne zusätzlichen Modellaufruf zur Auswahl.
- Qualität und Kosten mit festen Referenzfällen, geeigneten Offline-Tests und getrennter Verbrauchs-/Laufzeiterfassung für Analyse und Gegenprüfung nachweisen. Grenzen von Offline-Nachweisen ausdrücklich festhalten.

Nicht im Umfang: Caching oder Wiederverwendung früherer Modellantworten. Die identischen Anfragen stammen aus getrennten Abnahme- und Prüfläufen; unnötige Doppelaufrufe innerhalb eines regulären Laufs sind nicht nachgewiesen. Losbündelung beziehungsweise die einmalige Übergabe gemeinsamer Angaben mehrerer Lose wird auf später verschoben und separat abgestimmt; hierfür wird jetzt kein neues Ticket angelegt.

Aktuelle Freigabe: ausschließlich diese Ticketanpassung. Noch keine Codeänderungen und keine neuen Modellaufrufe. Umsetzung und ein späterer kontrollierter Modellvergleich benötigen eine gesonderte ausdrückliche Freigabe.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Doppelte Anfrageinhalte sind reduziert, ohne Quellen still zu kürzen oder relevante Angaben zu verlieren. Offline-Vergleiche belegen vollständige Quellenabdeckung sowie erhaltene Fundstellen, Feldbedeutungen, Loszuordnungen, Dokumentstände und Unsicherheiten.
- [ ] #2 Die Gegenprüfung liefert je geprüfter Aussage bestätigt, widerlegt oder nicht entscheidbar mit kurzer Begründung und betroffener Fundstelle; Ausgabe und Protokolle unterscheiden fachliches Modellurteil von lokaler Belegprüfung.
- [ ] #3 Belegte, strittige Aussagen und Widersprüche bleiben mit Belegen als offene Prüfpunkte sichtbar. Eine Ablehnung wird weder als gesicherte Tatsache übernommen noch als nicht angegeben dargestellt.
- [ ] #4 Transparente Regeln sparen die erneute Modellprüfung bereits regelbasiert geprüfter strukturierter Fakten und identischer Wiederholungen davon. Fachliche Interpretationen, Feldzuordnung, Passung, Negationen, Widersprüche und losübergreifende Aussagen bleiben prüfpflichtig; ein wörtliches Zitat allein befreit nicht davon. Es gibt keinen zusätzlichen Modellaufruf zur Auswahl des Prüfbedarfs.
- [ ] #5 Die dokumentierten Referenzfälle zu Rahmenvereinbarungswiderspruch, E-Mail-Abgabeform, Frist ohne Zeitzone, Rechtsbehelfsfristen und Unterlageninhalt versus Abgabeform sind mit Originalfundstellen und fachlich unabhängigen Erwartungen hinterlegt. Offline-Tests prüfen insbesondere notwendige Quellen, Verarbeitung unterschiedlicher Prüfurteile, sichtbare Unsicherheit und Loszuordnung; Mocks gelten nicht als Nachweis fachlicher Modellqualität.
- [ ] #6 Verbrauch und Laufzeit werden getrennt für Analyse und Gegenprüfung nachvollziehbar ausgewiesen. Ausgangswerte, gemessene Ergebnisse und Einsparschätzungen bleiben unterscheidbar; Nutzdatenbytes gelten nicht als gemessene Tokenersparnis. P-12 bleibt auf die tatsächliche Abrechnungsgrundlage bezogen.
- [ ] #7 Ein ausdrücklich freigegebener kontrollierter Modellvergleich bewertet später fachliche Urteile und tatsächlichen Tokenverbrauch an den festen Referenzfällen. Bis dahin bleiben verbesserte Modellqualität und reale Token-/Laufzeitersparnis ausdrücklich unbestätigt. Caching und Losbündelung werden in diesem Ticket nicht umgesetzt.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Untersuchung der gespeicherten Protokolle: 31 unterschiedliche Gegenprüfungsantworten mit 321 Einzelentscheidungen, davon 28 Ablehnungen. Fachliche Einordnung: 8 berechtigt, 17 fälschlich, 3 ungeklärt. Das Replay unter missing-53379306 zählt einmal. Wiederholungen derselben Quellen und unterschiedliche Promptstände erlauben keine allgemeine Fehlerquote. Ein ungeklärter Auslassungshinweis wurde bereits lokal wegen fehlenden Belegs abgewiesen; dies belegt keinen zusätzlichen Nutzen der Modellprüfung.

Referenzfälle (jeweils call-2.request.json und call-2.response.json unter model/):
- reports/acceptance/changed-profile-7737695a/analyses/20261117T152414-83a81746/: belegter Rahmenvereinbarungswiderspruch abgelehnt. Original 773064-2026.xml: globale ProcurementProject/Description versus losbezogenes ContractingSystemTypeCode mit listName=framework-agreement und Wert none.
- reports/acceptance/missing-29381c9b/analyses/20261117T151538-d1f972b6/: explizite E-Mail-Abgabeform abgelehnt, Unterlageninhalte als submission bestätigt. Original 788030-2026.xml: globale ProcurementProject/Note.
- reports/acceptance/missing-53379306/analyses/20261117T152834-21aeff21/: ausdrücklich unsicheres Originalzitat der Einreichungsfrist ohne Zeitzone abgelehnt. Das spätere Replay ist kein weiterer Modellversuch.
- reports/acceptance/unclear-51ff3ba0/analyses/20261117T151117-b927dfd1/: allgemeine Rechtsbehelfsfristen zu Recht als ungeeigneter Inhalt für konkrete Einreichungsfristen abgelehnt. Original 799785-2026.xml: AppealTerms/PresentationPeriod/Description.
Die Originale liegen jeweils im documents/-Verzeichnis des zugehörigen Laufs.

Kostenbasis: reports/ki-analyse-5-20261117-f3d2e93e/analyses/20261117T163659-c8a8a3bd/analysis.json und model/. 18 Aufrufe, 774.079 Eingabe- und 54.221 Ausgabetokens, Gesamtlaufzeit rund 20:17 Minuten. Gegenprüfung: 403.038 Eingabe- und 2.507 Ausgabetokens, rund 49 Prozent aller Tokens; protokollierte Antwortspannen zusammen rund 97 Sekunden, ohne vollständige Aufrufnebenzeiten. Keine Ablehnungen in diesem Lauf. structured_fields machen rund 38 Prozent der JSON-Nutzdatenbytes beider Stufen aus; dies ist keine gemessene Tokenersparnis. Verbrauch betrifft ChatGPT-Kontingent, keine zusätzliche API-Abrechnung. Einsparpotenziale nicht ungeprüft addieren oder proportional in Laufzeit umrechnen.

Bisherige Prüfung: 124 Offline-Tests bestanden, 6 Live-Tests übersprungen; Ruff und Formatprüfung erfolgreich. Gemockte Prüfurteile belegen ihre Verarbeitung, nicht die fachliche Urteilsgüte. Für die Untersuchung wurden keine neuen Modellaufrufe ausgeführt und keine Codeänderungen vorgenommen.

Stand 18.11.2026 nach Freigabe von Umsetzung und Losbündelung. Ein Prüfpunkt darf mit eigenem Losanker eine Vergleichsstelle aus einem anderen Los zitieren. Bei Pfalzwerke 798622-2026 erreichen dadurch der widersprüchliche Dateiverweis in Los 3 und der CPV-Vergleich die Gegenprüfung. Bei AOK 794059-2026 bleiben Eignungsblöcke mit eindeutig abweichender Losüberschrift als Prüfpunkte erhalten. Gegenbelege behalten den relevanten Wortlaut. Ein widerlegter Zusatz entwertet keine unabhängig belegte Frist. Der Live-Lauf vor dem Fix umfasste 105 Modellurteile. Vier von fünf Bekanntmachungen ließen sich nach dem Fix mit beiden gespeicherten Antworten verarbeiten. Für die beiden neu zugelassenen Pfalzwerke-Prüfpunkte fehlt ein echtes Modellurteil. 167 Offline-Tests bestanden, acht Live-Tests übersprungen, beide Ruff-Prüfungen erfolgreich.
<!-- SECTION:NOTES:END -->
