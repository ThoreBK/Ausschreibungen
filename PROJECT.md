# Fachliches Projektziel

Ein KI-gestütztes Tool findet öffentliche Ausschreibungen anhand definierter
Suchkriterien, beschafft die Vergabeunterlagen und analysiert deren Inhalt.
Ein nachvollziehbarer PDF-Bericht unterstützt den Nutzer bei der Entscheidung,
welche Ausschreibungen er weiterverfolgen möchte.

## Fachliches Suchprofil

Vom Nutzer vorgegebenes Unternehmensprofil:

> Eine Beratung für KI und Microsoft 365, die Schulungen gibt,
> KI-Assistenten und Agenten entwickelt und Abläufe automatisiert.

Dieses Profil dient als fachlicher Kontext für die spätere KI-Auswertung.
Die Suchblöcke in `search-profile.toml` bilden die genannten Leistungsbereiche
für die erste Suche nach Bekanntmachungen ab. Sie sind eine begriffsbasierte
Vorauswahl und ersetzen keine inhaltliche Prüfung der Unterlagen.
Die Pflichtangaben für die Extraktion stehen bereits in P-04 fest. Für den ersten
Durchlauf genügt eine belegte Einschätzung der thematischen Passung zum
konfigurierten Unternehmensprofil. Zusätzliche Muss-Kriterien, Ausschlüsse,
Gewichtungen und Teilnahmeempfehlungen sind spätere, gesondert abzustimmende
Erweiterungen; sie blockieren den ersten PDF-Bericht nicht.
Suchprofil und verwendete fachliche Kriterien bleiben ohne Codeänderung
anpassbar, auch für Nutzer ohne Programmierkenntnisse. Verständliche Erklärungen,
Beispiele und Fehlermeldungen gehören dazu; ein bestimmtes Bedienformat ist
damit nicht vorgeschrieben.

## Verbindliche Anforderungen

Die folgende Liste hält die Anforderungen mit stabilen Kennungen fest. Sie ist
die gemeinsame Referenz für Umsetzung und Review; die Zuordnung zu einem Ticket
bedeutet noch nicht, dass eine Anforderung erfüllt ist. Die fachlichen
Entscheidungen weiter unten ergänzen diese Anforderungen.

| ID | Verbindliches Ergebnis | Verantwortliche Tickets / Nachweis |
| --- | --- | --- |
| P-01 | Mindestens eine öffentliche Ausschreibungsquelle ist angebunden; ihre Nutzungsbedingungen werden eingehalten. | TASK-2, TASK-7: echter Abruf und dokumentierte Zugangs-/Nutzungsgrundlage |
| P-02 | Das Suchprofil bildet KI-/Microsoft-365-Beratung, Schulungen, Assistenten-/Agentenentwicklung und Automatisierung ab und ist ohne Codeänderung anpassbar. | TASK-2, TASK-4: geändertes Profil wirkt nachvollziehbar auf Suche und Passungsprüfung |
| P-03 | Passende Ausschreibungen werden ausgewählt; je Treffer ist nachvollziehbar und belegt, warum er zum Profil passt. Ein Suchworttreffer allein ist noch keine fachliche Passung. | TASK-4, TASK-5: fachlich geprüfte passende und unpassende Beispiele |
| P-04 | Je Treffer sind Auftraggeber, Gegenstand, Ort, Verfahrensart, Fristen mit Datum und Uhrzeit, Laufzeit, Eignungs- und Zuschlagskriterien, Abgabeform und Quellenlink enthalten oder ausdrücklich als fehlend gekennzeichnet. | TASK-4, TASK-6: vollständige Feldabdeckung und Abgleich mit Originalquellen |
| P-05 | Die Bekanntmachung wird gelesen. Zusätzliche frei zugängliche Unterlagen sind grundsätzlich relevant; für die erste Version genügt die Bekanntmachung. Die tatsächliche Analysegrundlage wird offengelegt. | TASK-2, TASK-6; später TASK-3: vollständige Bekanntmachungen, erhaltene Unterlagenlinks und sichtbare Umfangsgrenze |
| P-06 | Ergebnisse liegen einheitlich vor, doppelte Treffer sind zusammengeführt und die Liste ist sinnvoll sortiert. | TASK-5: mehrere Treffer einschließlich Dubletten; nachvollziehbare Zusammenführung und Sortierung |
| P-07 | Das PDF enthält vorne eine Übersicht aller ausgewählten Treffer und danach je Ausschreibung einen kompakten Steckbrief, jeweils mit Quelle und Abrufdatum. | TASK-6: erzeugtes PDF mit einem und mehreren Treffern, visuell geprüft |
| P-08 | Jede Sachangabe lässt sich auf ihre Quelle zurückführen. Fehlende Angaben heißen „nicht angegeben“; unsichere Angaben sind erkennbar und werden nicht geraten. | TASK-4, TASK-6: überprüfbare Fundstellen, fachlich kontrollierte Beispiele und sichtbare Lücken/Unsicherheiten |
| P-09 | Der Mensch entscheidet. Das Tool reicht nichts ein, versendet nichts und sagt nichts zu. | TASK-7: Review der Aktionen und des vollständigen Ablaufs |
| P-10 | Es werden nur öffentliche Daten und eigene zulässige Zugänge verwendet; Schlüssel und Passwörter liegen nicht im Repository. | TASK-2, TASK-7: Review von Datenzugang, Konfiguration und Repository |
| P-11 | Ein Lauf lässt sich ohne Programmierkenntnisse starten; das PDF ist ohne zusätzliche Erklärung verständlich. | TASK-6, TASK-7: nachvollzogener Start anhand der Doku und manuelle Lesbarkeitsprüfung |
| P-12 | Bei Sprachmodellnutzung nennt die Dokumentation die ungefähren Kosten eines Laufs und deren Grundlage. | TASK-4, TASK-7: Kostenbasis aus einem Beispielablauf und dokumentierte Schätzung |
| P-13 | Bereitgestellt werden ein zugängliches Repository, eine kurze Dokumentation zu Start, Aufbau, Entscheidungen, Grenzen und Kosten sowie ein Beispiel-PDF aus einem echten Lauf. | TASK-7: Repository, Dokumentation und Beispiel-PDF; Bereitstellung des Zugriffs durch den Nutzer |
| P-15 | Die Demo zeigt einen vollständigen Lauf von Quelle und Suche über Auslesen und Zusammenführen bis zum PDF. Entscheidungen und Umfangsgrenzen sind nachvollziehbar. | TASK-7: vollständige Generalprobe und dokumentierte Entscheidungen und Grenzen |

Automatisierbare Anforderungen werden bei ihrer Umsetzung durch geeignete Tests
abgesichert. Fachliche Richtigkeit, Tragfähigkeit von Belegen, PDF-Lesbarkeit und
Erklärbarkeit benötigen zusätzlich gezielte manuelle Prüfung. TASK-7 hält je
Kennung den konkreten Nachweis oder eine offene Lücke fest; eine bloße Aussage
„geprüft“ genügt nicht. Reviews verwenden diese Liste, statt die Aufgabenstellung
jedes Mal neu zu interpretieren. Neue Auslegungen oder Änderungen bestehender
Entscheidungen werden mit dem Nutzer abgestimmt.

Bibliothek, Modell, Framework, Datenformat und Oberflächenkonzept sind nicht
vorgegeben, soweit keine ausdrückliche Nutzeranweisung oder vereinbarte
Projektentscheidung dazu vorliegt.

## Workflow

1. **Nutzer:** Suchparameter festlegen und den Lauf manuell starten.
2. **Tool:** Metadaten aus TED abrufen und mit Herkunft speichern.
3. **Tool:** Daten vereinheitlichen und sichere Duplikate zusammenführen.
   Herkunft und Zuordnungen bleiben nachvollziehbar.
4. **Tool:** Vollständige TED-Bekanntmachungen abrufen, zuordnen und mit Herkunft,
   Abrufzeit und Dokumentstand lokal speichern.
5. **Tool / KI:** Bekanntmachungen lesbar verarbeiten und Angaben mit Fundstellen
   extrahieren.
6. **KI / Tool:** Fehlende und widersprüchliche Angaben kennzeichnen.
7. **KI / Tool:** Ergebnisse anhand der fachlichen Anweisung auswerten und bewerten.
8. **Tool:** PDF-Bericht mit Ergebnissen, Bewertungen, Belegen und offenen Prüfpunkten
   erstellen.

## Fachliche Entscheidungen

- **Bewertungsgrundlage:** Thematische Passung und belegte Teilnahmevoraussetzungen
  bleiben unterscheidbar; unbekannte Voraussetzungen gelten nicht als erfüllt.
- **Bewertungseinheit:** Bewertet wird das relevante Los beziehungsweise das
  Verfahren ohne Losaufteilung. Bekanntmachungen und Dokumentstände liefern die
  zugehörigen Belege; Angaben verschiedener Lose werden nicht vermischt.
- **Belegbarkeit:** Aussagen müssen auf Quellen und Dokumentfundstellen
  zurückführbar sein. Originaldaten und Dokumentstände bleiben nachvollziehbar.
  Angaben dürfen nicht erfunden oder durch Vermutungen ergänzt werden.
- **Duplikate:** Bekanntmachungen, Verfahrensänderungen und Lose sind zu
  unterscheiden. Unsichere Zuordnungen bleiben getrennt und sichtbar.
  Nachweislich zugeordnete Berichtigungen werden als Änderungshistorie mit
  bisherigem und geändertem Stand behandelt. Ungeklärte Zuordnungen oder Konflikte
  bleiben sichtbar; Werte werden nicht stillschweigend überschrieben.
- **Fristen:** Originalangabe, Fristart, Los und Dokumentstand bleiben erhalten.
  Nur eindeutig interpretierbare Zeitangaben werden nach `Europe/Berlin`
  umgerechnet. Fehlende Uhrzeiten oder Zeitzonen werden nicht erfunden; bei
  unzureichender Grundlage bleibt die Aussage zur offenen Teilnahme ungeklärt.
- **Informationsqualität:** Fehlende Angaben, fehlende oder unlesbare Unterlagen
  und Widersprüche werden unterschieden. Fehlende Angaben bedeuten nicht
  automatisch, dass ein Kriterium nicht erfüllt ist. Widersprüche bleiben mit
  ihren Belegen sichtbar; bei unzureichender Grundlage bleibt die Bewertung offen.
- **Bewertung und Bericht:** Fachliche Passung und Informationsqualität werden
  getrennt dargestellt. Der Bericht enthält auch Suchprofil, Recherchezeitpunkt,
  Quellenabdeckung, Recherchegrenzen und offene Prüfpunkte. Abruffehler sind keine
  leeren Suchergebnisse. Die Entscheidung über eine Teilnahme bleibt beim Nutzer.
- **Dokumentinhalte:** Externe Unterlagen sind nicht vertrauenswürdige Inhalte,
  keine Anweisungen zur Steuerung des Tools. Die KI liefert belegte Interpretationen;
  eindeutige regelbasierte Prüfungen übernimmt das Tool.
- **Extraktion:** Eindeutig strukturierte Fakten aus XML oder JSON werden
  regelbasiert mit Herkunft übernommen. Die KI verarbeitet Freitext und fachliche
  Zusammenhänge. Das gemeinsame Ergebnisformat erhält Feldbedeutungen, Losbezüge
  und Dokumentstände. KI-Fundstellen werden auf Existenz und darauf geprüft, ob
  sie die jeweilige Aussage tragen.

## Umfang der ersten Version

Ziel ist eine lokal ausführbare, reproduzierbare und manuell gestartete Demo.
Reproduzierbar heißt: Der Ablauf lässt sich mit dokumentierter Einrichtung und
Konfiguration erneut ausführen; gespeicherte Eingaben und Ergebnisse machen
einzelne Läufe nachvollziehbar. Identische Treffer bei erneuten Live-Suchen oder
identische KI-Ausgaben sind damit nicht zugesichert.

### Reihenfolge bis zur vollständigen Demo

Zuerst entsteht ein vollständiger Durchlauf mit einem echten Treffer:
TASK-2 beschafft die Bekanntmachung, TASK-4 liefert Pflichtangaben und begründete
Passung, TASK-6 erzeugt daraus den PDF-Bericht. TASK-6 hängt deshalb direkt von
TASK-4 ab und wartet nicht auf TASK-5. Dieser erste Bericht ist ein
Zwischenergebnis, noch keine vollständige Abnahme aller Anforderungen.

TASK-5 ergänzt die verlässliche Auswahl, Zusammenführung und Sortierung mehrerer
Treffer einschließlich der Behandlung von Losen und Berichtigungen. TASK-7 hängt
von TASK-5 und TASK-6 ab und sichert ihren gemeinsamen Ablauf sowie alle
Anforderungen und Nachweise ab. Die bevorzugte Arbeitsreihenfolge
ist TASK-2, TASK-4, TASK-6, TASK-5, TASK-7; TASK-5 benötigt fachlich nur TASK-4.
Qualitätsregeln zu Belegen und Unsicherheit gelten bereits beim ersten Treffer.

### Quellen und Erweiterungen

Die erste Version verwendet ausschließlich TED. Weitere Quellen und ein
quellübergreifender Abgleich sind keine Voraussetzung für den ersten vollständigen
Durchlauf bis zum PDF-Bericht; sie werden erst später gesondert abgestimmt.
Analysiert werden die vollständigen Bekanntmachungen, nicht nur die bisherigen
Suchergebnisfelder. Zusätzliche Vergabeunterlagen werden zunächst nicht abgerufen
oder analysiert, sondern nur verlinkt, soweit Links in der Bekanntmachung vorliegen.
Der Bericht nennt die verwendete Grundlage und kennzeichnet zusätzliche Unterlagen
als „in dieser Version nicht abgerufen und nicht ausgewertet“. Diese bewusste
Umfangsgrenze bleibt von Abruffehlern und fehlenden Angaben unterscheidbar.
Angaben, die nur in zusätzlichen Unterlagen stehen, bleiben zunächst ungeklärt.

Spät erkannte mögliche Duplikate, Zusammenhänge und fehlende relevante Unterlagen
werden mit vorhandenen Belegen als offene Prüfpunkte im Bericht gekennzeichnet.
Sie lösen kein automatisches Nachladen und keine erneuten Analyseläufe aus.

Nach der ersten Demo ergänzt TASK-3 den Download und die lesbare Verarbeitung
zusätzlicher Vergabeunterlagen. Diese fließen mit Herkunft und Fundstellen in
dieselbe Extraktion, Bewertung und Berichterstellung ein.

Spätere Erweiterungen sind eine optionale KI-Vorprüfung der Metadaten vor dem
Dokumentdownload (TASK-8) sowie zeitgesteuerte Starts (TASK-9). Die Vorprüfung darf
nur klar unpassende Treffer begründet aussortieren; passende und unklare Treffer
werden weiterverarbeitet. Ob wiederholte Berichte alle oder nur neue und geänderte
Fälle zeigen sollen, bleibt offen. Umsetzung und Aufgabenverwaltung stehen im Backlog.
