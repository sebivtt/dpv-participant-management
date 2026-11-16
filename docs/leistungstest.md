# Ergebnisse des Leistungstests

Hier steht am Ende jeder Phase das Ergebnis des Leistungstests (#145, NFA-05): je Seite die Zeit, der Wert vom Ende der vorigen Phase und die Abweichung. Beide Werte stammen aus demselben Lauf auf demselben Rechner. Wie der Test läuft, steht im `README.md` („Leistungstest (am Ende einer Phase)“), der Schritt am Phasenende im Skill `phase-steuern`, Abschnitt 5, die Gründe in `docs/entscheidungen.md` (14.11.2026, #145).

Jeder Abschnitt ist die Zusammenfassung des Laufs auf GitHub, unverändert übernommen. Ist eine Seite mehr als 25 % langsamer geworden, steht darunter Sebastians Entscheidung mit Begründung und Link.

## P2

Lauf vom 16.11.2026, Commit `9b95975`. Ausgangswert: Es gibt noch keine vorige Phase, jede Seite prüft nur gegen die 2 Sekunden.

| Seite | Zeit | Wert der vorigen Phase | Abweichung | Ergebnis |
|---|---|---|---|---|
| Gliederung „Organisation“ | 0,05 s | – | – | im Rahmen |
| Seite mit 500 Personen | 0,10 s | – | – | im Rahmen |
| Namensvorschläge zu „Pro“ | 0,03 s | – | – | im Rahmen |
| Suche bei „Person aufnehmen“ | 0,05 s | – | – | im Rahmen |
| Veranstaltung mit 40 Anmeldungen | 0,06 s | – | – | im Rahmen |
| Anmeldung mit 595 Personen | 0,02 s | – | – | im Rahmen |
| Dialog „Verschieben“ auf der Seite mit 500 Personen | 0,14 s | – | – | im Rahmen |

Seiten mit Personen ohne Messung: keine.
