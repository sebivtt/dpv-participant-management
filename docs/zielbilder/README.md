# Zielbilder

Ein Zielbild ist Sebastians fertiger Entwurf einer Seite als HTML-Datei, mit erfundenen Daten. Es zeigt, wie die Seite aussehen soll und wohin sie wächst, oft mit mehr, als das Tool heute speichert. Ablauf „Zielbild vor Gestaltung“: `docs/entscheidungen.md`, Eintrag vom 25.10.2026 zu #161.

Ein Zielbild ist **Orientierung, keine Anforderung.** Was es zeigt, gibt niemandem ein Recht und ändert keine Entscheidung. Es gehen vor: `docs/rechtematrix.md`, `docs/anforderungen.md`, `docs/entscheidungen.md`, `docs/gestaltung.md`. Gebaut wird nur, was das Tool speichert; Teile ohne Daten fehlen ganz, ohne leere Platzhalter.

Die Dateien liegen unverändert so im Repo, wie Sebastian sie geliefert hat; sie öffnen sich mit Doppelklick im Browser. Das Tool lädt sie nie. Für jede Datei steht hier, von wann sie ist, woher sie kommt, ihre Prüfsumme und wo die Seite bewusst abweicht. Eine neue Fassung ersetzt die Datei; die alte bleibt in der Versionsgeschichte, und Datum und Prüfsumme hier werden fortgeschrieben. Ein Test (`tests/test_mein_profil.py`) prüft, dass Datei und Prüfsumme zusammenpassen und die Datei nichts von fremden Servern lädt.

## Mein Profil

- **Datei:** [`mein-profil.html`](mein-profil.html)
- **Stand:** 25.10.2026, von Sebastian mit ChatGPT gebaut (`mein_profil_entwurf_v12_profilseite.html`), eingespielt mit #161. Danach hat Sebastian bei der Klärung von #161 die Farben von „Organisation und Rollen“ angepasst (unten, Punkt 5); diese Anpassung steht nur hier, nicht in der Datei.
- **Prüfsumme (SHA-256):** `b27e218f23ea6647ee0053ded40057b036d6f205ac8f8a7e6caec9cf1746c477`
- **Inhalt der Datei:** nur erfundene Daten (Erika Testfrau, `erika.testfrau@example.org`, „Musterweg 12“). Nichts von fremden Servern: Bootstrap 5.3.6 ist unverändert eingebettet (Lizenz MIT, Hinweis in der Datei), die Symbole sind eingebettete Grafiken, die Schrift ist die Systemschrift. Ein eingebettetes Skript bewegt nur die Vorschau; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #161 ([Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102089), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102282), [Nachklärung Kacheln](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403407168)).

### Abweichungen der Seite vom Zielbild

1. **Fehlt, weil das Tool die Daten nicht hat:** „Profil freigeben“ und die Freigaben je Feld (#137), Fahrtenname als Feld und vor dem Namen (#111), Geburtsdatum (#143), Adresse und Gesundheitsangaben (FRM-02 bis FRM-04). Sie kommen mit ihren Issues und folgen dann dem Zielbild.
2. **„Mitgliedschaft und Austritt verwaltest du in deiner Organisation.“ mit „Organisation öffnen“ fehlt.** Es widerspricht der Entscheidung zu #65: „Austreten“ kommt als Knopf direkt in die Fläche der Mitgliedschaft, an diese Stelle. Eine Seite „Organisation“ gibt es noch nicht (#93).
3. **Reihenfolge der Rollen von klein nach groß** (Gruppenleitung zuerst, Admin zuletzt), nicht wie im Zielbild von groß nach klein; so in den Szenarien zu #96 entschieden und in #161 bestätigt.
4. **Feste Sätze statt der Beschreibungen** unter Rollen im DPV ([Nachklärung Kacheln](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403407168)): Verbandsleitung „Leitung des Verbands“ statt „Verantwortung auf Verbandsebene“, DPV-Veranstaltungsteam „Veranstaltungen des Verbands“ statt „Verbandsweite Funktion“. Admin hängt an keiner Organisation und fehlt im Zielbild; die Kachel zeigt klein „Admin“, groß „DPV Anmeldetool“, darunter „Verwaltung des ganzen Tools“. Es sind feste Texte, keine gespeicherten Daten.
5. **Farben in „Organisation und Rollen“** (Sebastian bei der Klärung von #161): Mitgliedschaft zart blau `#e9eff6` wie im Zielbild; die Rollen-Kacheln weiß mit feinem Rand `#dbe2ea` und oben einem schmalen blauen Streifen (3 Pixel, `#1a4b7e`) statt grauer Fläche. Der Rand ist eine bewusste Ausnahme von „Flächen statt Rahmen“ (`docs/gestaltung.md`). Die kleine Rollenmarke ist in den Kacheln zart blau statt weiß, weil sie auf weißer Kachel sonst verschwände.
6. **Texte:** wie im Zielbild „E-Mail-Adresse“ und „Name und E-Mail-Adresse stammen aus deinem DPV-Konto …“. Dazu kommen die Hinweise aus #96, die das Zielbild nicht zeigt: gelb „Ergänze deinen Namen …“, wenn ein Name fehlt, grau „nicht angegeben“ im Feld, und „Du bist noch keiner Organisation zugeordnet. …“ ohne jede Zuordnung. Fehlen beide Namen, steht in der Kopfzeile der Benutzername.
7. **Keine Überschrift je Kachel:** Im Zielbild ist jede Organisation eine Unterüberschrift. Die Seite zeigt Mitgliedschaft und Kacheln als Liste ohne eigene Überschriften; Vorleseprogramme lesen Rolle, Organisation und Weg zusammen vor, und die Liste der Überschriften bleibt kurz. Sichtbar ist es gleich.
8. **Lange Namen brechen um,** statt mit „…“ abgeschnitten zu werden, damit am Handy nichts versteckt ist.
9. **Symbole und Spalten:** eigene Symbole des Tools (Lizenz wie das Tool), für „Organisation und Rollen“ das Symbol der Navigation statt der Ebenen. Die Kacheln passen ihre Spaltenzahl der Breite an (am PC mehrere nebeneinander, am Handy untereinander), statt fester vier, zwei oder einer Spalte. Navigation und Fußbereich kommen wie auf jeder Seite aus dem Tool.
