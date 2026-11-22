# Zusammenarbeit mit dem Coding-Agenten

Bei TASK-5 setzte der Coding-Agent die Treffer- und Berichtsauswahl um und
übersetzte fachliche Vorgaben in Tests. Ein unabhängiger Review zeigte, dass
unterschiedliche Lose mit derselben technischen Kennung einander bei der
Fristbewertung beeinflussen konnten. Der Nutzer beauftragte die Korrektur und
gezielte Regressionstests. Einer davon verlangt, dass bei Berichtslimit 1 das
offene Los erscheint und das abgelaufene ausgeschlossen bleibt, obwohl beide
dieselbe technische Losnummer tragen. Beleg: Commit `2787bf3` und
`test_reused_technical_lot_id_keeps_independent_deadlines`.

Der Agent empfahl zunächst, TASK-13 vor TASK-5 umzusetzen. Der Nutzer
entschied, beide Entwicklungen in eigenen Worktrees parallel zu starten.
Er behielt sich das Go für die fachliche Abschlussprüfung von TASK-5 vor
und gab dafür die bereits für TASK-13 geprüften `analysis.json` und
`results.json` vor. So ließ sich die Trefferauswahl mit gleichbleibenden
Eingaben prüfen. Für die vollständige Generalprobe in TASK-7 beauftragte
er später einen neuen Live-Lauf. Belege: „Nächsten Task auswählen“ und
„Trefferauswahl zusammenführen und sortieren“.

Bei TASK-13 half der Agent, Fristen, Laufzeiten und Eignungsangaben mit
Originalen und PDF abzugleichen. Der Nutzer entschied, die vorhandene
Extraktion und Gegenprüfung auch für die Korrekturen zu verwenden, um
Sonderfalllogik zu vermeiden. Für Chemnitz beauftragte er ein eigenes Ticket
mit Regressionstest. Dort hatte das Modell die semantische Posteingangsanalyse
erkannt, aber wegen der ungeklärten Lieferfähigkeit den Auftrag insgesamt
als unpassend gewertet. Der Prüffall unterscheidet die thematische
Überschneidung und den offenen Betriebsnachweis. Belege: Commit `4ace9c0`
und „Review von Task 13 durchführen“.
