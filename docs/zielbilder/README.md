# Zielbilder

Ein Zielbild ist Sebastians fertiger Entwurf einer Seite als HTML-Datei, mit erfundenen Daten. Es zeigt, wie die Seite aussehen soll und wohin sie wächst, oft mit mehr, als das Tool heute speichert. Ablauf „Zielbild vor Gestaltung“: `CLAUDE.md`; entschieden in `docs/entscheidungen.md`, Einträge vom 25.10.2026 zu #161 und vom 26.10.2026 zu #162.

Ein Zielbild ist **Orientierung, keine Anforderung.** Was es zeigt, gibt niemandem ein Recht und ändert keine Entscheidung. Es gehen vor: `docs/rechtematrix.md`, `docs/anforderungen.md`, `docs/entscheidungen.md`, `docs/gestaltung.md`. Gebaut wird nur, was das Tool speichert; Teile ohne Daten fehlen ganz, ohne leere Platzhalter.

Die Dateien liegen unverändert so im Repo, wie Sebastian sie geliefert hat; sie öffnen sich mit Doppelklick im Browser. Das Tool lädt sie nie. Für jede Datei steht hier, von wann sie ist, woher sie kommt, ihre Prüfsumme und wo die Seite bewusst abweicht. Eine neue Fassung ersetzt die Datei; die alte bleibt in der Versionsgeschichte, und Datum und Prüfsumme hier werden fortgeschrieben. Je Datei prüft ein Test (`tests/test_mein_profil.py`, `tests/test_meldungen.py`, `tests/test_kurzmeldung.py`), dass Datei und Prüfsumme zusammenpassen und die Datei nichts von fremden Servern lädt.

## Mein Profil

- **Datei:** [`mein-profil.html`](mein-profil.html)
- **Stand:** 25.10.2026, von Sebastian mit ChatGPT gebaut (`mein_profil_entwurf_v12_profilseite.html`), eingespielt mit #161. Danach hat Sebastian bei der Klärung von #161 die Farben von „Organisation und Rollen“ angepasst (unten, Punkt 5); diese Anpassung steht nur hier, nicht in der Datei.
- **Prüfsumme (SHA-256):** `b27e218f23ea6647ee0053ded40057b036d6f205ac8f8a7e6caec9cf1746c477`
- **Inhalt der Datei:** nur erfundene Daten (Erika Testfrau, `erika.testfrau@example.org`, „Musterweg 12“). Nichts von fremden Servern: Bootstrap 5.3.6 ist unverändert eingebettet (Lizenz MIT, Hinweis in der Datei), die Symbole sind eingebettete Grafiken, die Schrift ist die Systemschrift. Ein eingebettetes Skript bewegt nur die Vorschau; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #161 ([Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102089), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102282), [Nachklärung Kacheln](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403407168)).

### Abweichungen der Seite vom Zielbild

1. **Fehlt, weil das Tool die Daten nicht hat:** „Profil freigeben“ und die Freigaben je Feld (#137), Geburtsdatum (#143), Adresse und Gesundheitsangaben (FRM-02 bis FRM-04). Sie kommen mit ihren Issues und folgen dann dem Zielbild. Den Fahrtennamen gibt es seit #111 (Punkt 10).
2. **„Mitgliedschaft und Austritt verwaltest du in deiner Organisation.“ mit „Organisation öffnen“ fehlt.** Es widerspricht der Entscheidung zu #65: „Austreten“ kommt als Knopf direkt in die Fläche der Mitgliedschaft, an diese Stelle. Eine Seite „Organisation“ gibt es noch nicht (#93).
3. **Reihenfolge der Rollen von klein nach groß** (Gruppenleitung zuerst, Admin zuletzt), nicht wie im Zielbild von groß nach klein; so in den Szenarien zu #96 entschieden und in #161 bestätigt.
4. **Feste Sätze statt der Beschreibungen** unter Rollen im DPV ([Nachklärung Kacheln](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403407168)): Verbandsleitung „Leitung des Verbands“ statt „Verantwortung auf Verbandsebene“, DPV-Veranstaltungsteam „Veranstaltungen des Verbands“ statt „Verbandsweite Funktion“. Admin hängt an keiner Organisation und fehlt im Zielbild; die Kachel zeigt klein „Admin“, groß „DPV Anmeldetool“, darunter „Verwaltung des ganzen Tools“. Es sind feste Texte, keine gespeicherten Daten.
5. **Farben in „Organisation und Rollen“** (Sebastian bei der Klärung von #161): Mitgliedschaft zart blau `#e9eff6` wie im Zielbild; die Rollen-Kacheln weiß mit feinem Rand `#dbe2ea` und oben einem schmalen blauen Streifen (3 Pixel, `#1a4b7e`) statt grauer Fläche. Der Rand ist eine bewusste Ausnahme von „Flächen statt Rahmen“ (`docs/gestaltung.md`). Die kleine Rollenmarke ist in den Kacheln zart blau statt weiß, weil sie auf weißer Kachel sonst verschwände (von Sebastian bestätigt, [Nachtrag](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403556335)).
6. **Texte:** wie im Zielbild „E-Mail-Adresse“ und „Name und E-Mail-Adresse stammen aus deinem DPV-Konto …“. Dazu kommen die Hinweise aus #96, die das Zielbild nicht zeigt: gelb „Ergänze deinen Namen …“, wenn ein Name fehlt, grau „nicht angegeben“ im Feld, und „Du bist noch keiner Organisation zugeordnet. …“ ohne jede Zuordnung. Fehlen beide Namen, steht in der Kopfzeile der Benutzername.
7. **Keine Überschrift je Kachel:** Im Zielbild ist jede Organisation eine Unterüberschrift. Die Seite zeigt die Mitgliedschaft als eigene Fläche und die Kacheln als Liste, beide ohne eigene Überschriften; Vorleseprogramme lesen Rolle, Organisation und Weg zusammen vor, und die Liste der Überschriften bleibt kurz. Sichtbar ist es gleich.
8. **Lange Namen brechen um,** statt mit „…“ abgeschnitten zu werden, damit am Handy nichts versteckt ist.
9. **Symbole und Spalten:** eigene Symbole des Tools (Lizenz wie das Tool), für „Organisation und Rollen“ das Symbol der Navigation statt der Ebenen. Die Kacheln passen ihre Spaltenzahl der Breite an (am PC mehrere nebeneinander, am Handy untereinander), statt fester vier, zwei oder einer Spalte. Navigation und Fußbereich kommen wie auf jeder Seite aus dem Tool.
10. **Fahrtenname** (#111, seit #180 wie im Zielbild): als erstes Feld über Vor- und Nachname; in Ruhe mit Personensymbol, dem Fahrtennamen oder „Noch nicht angegeben“ und rechts dem Knopf zum Leeren; Antippen öffnet die Eingabe mit „Verwerfen“ und „Speichern“ darunter. In der Kopfzeile steht der Fahrtenname groß, „(Erika Testfrau)“ kleiner und grauer dahinter. Es bleiben diese Abweichungen:
    - **Knopf zum Leeren in Ruhe:** Er öffnet das Feld leer; gelöscht wird erst mit „Speichern“ (Sebastian, Klärung von #180). Im Zielbild leert er in Ruhe nur die Vorschau.
    - **Texte:** Meldungen nach dem Speichern wie in #111 statt „Vorschau aktualisiert …“; die Ansage beim Leeren heißt „Feld geleert. Mit Speichern übernehmen oder verwerfen.“, beim Verwerfen immer „Änderungen verworfen.“, auch nach Tippen außerhalb. Sie sind nur für Vorleseprogramme zu hören, ohne die schwarze Einblendung am unteren Rand.
    - **Fokus nach Tippen außerhalb:** Er geht zurück aufs Feld, außer man hat einen Link, Knopf oder ein Eingabefeld angetippt. Esc verwirft auch, wenn der Fokus schon außerhalb des Felds liegt.
    - **Ohne Skript** bleibt das einfache Formular aus #111: Eingabe mit „Speichern“ darunter, ohne Knopf zum Leeren und ohne „Verwerfen“.
    - **Lange Namen** brechen in Ruhe um wie in Punkt 8, statt mit „…“ abgeschnitten zu werden.
    - **Fehler am Feld** (mehr als 50 Zeichen) steht rot unter dem Feld, das offen bleibt; das Zielbild zeigt keinen Fehler.

## Meldungen

- **Datei:** [`meldungen.html`](meldungen.html)
- **Stand:** 26.10.2026, von Sebastian aus dem groben Entwurf der Steuerungssession gebaut (`dpv-meldungen-issue-165-entwurf.html`), eingespielt mit #165 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6416562863)).
- **Prüfsumme (SHA-256):** `b0b5ad4a3071dbe24ad071236aa010887ae4b955fbe11e49ae73d00e9cb70498`
- **Inhalt der Datei:** nur erfundene Personen (Max Testmann) und die Hilfeadresse des Tools (`anmeldetool@dpvonline.de`, Grundeinstellung in `config/settings.py`), keine Adresse einer Person. Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript spielt nur die Ansagen für Vorleseprogramme vor; ins Tool ist davon nichts übernommen (`docs/entscheidungen.md`, Eintrag vom 25.10.2026 zu #161).
- **Orientierung, keine Anforderung.** Geklärt in #165 ([Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6415185220), [Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6416568804), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6416569177)).

### Abweichungen der Seite vom Zielbild

1. **Hilfeadresse ohne Link:** Die Warnmeldung „… keine Mail eingetragen ist. Wende dich an …“ nennt die Adresse wie bisher als Text; das Zielbild macht daraus einen Mail-Link. #165 bringt keine neuen Texte und kein neues Verhalten.
2. **Fehler am Feld wie bisher:** rote Schrift direkt unter dem Feld, ohne das Kreuz davor und ohne das unsichtbare „Fehler am Eingabefeld:“ aus dem Zielbild (Tabelle in #165: „wie heute“). Vorleseprogramme lesen den Fehler weiter über die Verknüpfung mit dem Feld vor.
3. **Band der Testumgebung ohne unsichtbares Vorwort:** Das Zielbild sagt vorweg „Hinweis zur Testumgebung:“ an. Der Text des Bands beginnt selbst mit „Testumgebung:“; doppelt angesagt wäre es nur länger.
4. **Probe der Ansagen fehlt:** Die Knöpfe „… simulieren“, „Mit DPV-Konto anmelden (Beispiel)“ und das Skript dahinter zeigen im Zielbild nur, wie Vorleseprogramme Meldungen nach einer Handlung ansagen. Im Tool sagt die Login-Seite ihre Meldungen selbst an.
5. **Erklärende Teile fehlen:** die Tabelle der Regeln, die Umsetzungshinweise, die Liste der Szenarien und der Rahmen „390 Pixel“. Die Regel steht in `docs/gestaltung.md`; die Musterseite zeigt die Bausteine selbst.
6. **Beispieltexte der Musterseite:** Information und Erfolg wie im Zielbild; Warnung und Fehler mit eigenen erfundenen Texten, weil die Texte des Zielbilds echte Meldungen des Tools sind und auf ihren Seiten stehen.
7. **Symbole und Schrift:** Informations-, Erfolgs- und Laborsymbol sind wie im Zielbild ins Symbolset des Tools übernommen (`core/templates/core/_symbole.svg`); Warndreieck, Kreuz und Schloss waren dort schon gleich. Der fette erste Satz nutzt die Schriftstärke des Tools (800 statt 750).

## Kurze Meldungen

- **Datei:** [`kurze-meldungen.html`](kurze-meldungen.html)
- **Stand:** 27.10.2026, der grobe Entwurf der Klärungs-Session (`entwurf-kurze-meldung-186.html`), von Sebastian unverändert als Zielbild übernommen, eingespielt mit #186 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6442085509)).
- **Prüfsumme (SHA-256):** `4b0ae4ad11e369f4043011234afe30f6fed0dfd9323b8c9cb14aa0429629e7e1`
- **Inhalt der Datei:** nur erfundene Daten (Erika Testfrau, Kiwi, `erika@beispiel.invalid`, Sippen- und Meutenamen). Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript führt die Fälle vor; ins Tool ist nur das Verhalten der kurzen Meldung übernommen, neu geschrieben in `core/static/core/app.js`.
- **Orientierung, keine Anforderung.** Geklärt in #186 ([Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6441936833), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6441930967), [Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6442091320)).

### Abweichungen der Seite vom Zielbild

1. **Nur vereinfacht im Zielbild, so in der Nachklärung festgehalten:** Das Feld „Fahrtenname“ bleibt das Feld zum Antippen aus #180; Seitenleiste, Handyleiste und Profilkreis bleiben die Bausteine des Tools; die gestrichelte Fläche „Fälle vorführen“ und die Tabelle „Welche Form wann“ gibt es auf „Mein Profil“ nicht. Die Vorführung steht im Bausteinkatalog, die Regel in `docs/gestaltung.md`. „Mein Profil“ bekommt keine neuen Meldungen.
2. **Fehlermeldung über den Knöpfen:** Im Zielbild steht sie unter „Verwerfen“ und „Speichern“. Im Tool stehen die beiden Knöpfe als kleine Fläche über dem Inhalt darunter (#180); die Fehlermeldung steht deshalb direkt unter der Eingabe, wo auch der Fehler am Feld steht, und die Knöpfe darunter.
3. **Beispiele im Bausteinkatalog:** Erfolg mit dem erfundenen Text „Deine Anmeldung zum Herbstlager ist eingegangen.“ wie bei den Meldungen, Information und Stapel mit den Texten des Zielbilds. Knöpfe „Erfolg zeigen“, „Information zeigen“ und „Vier nacheinander zeigen“ blenden sie ein.
4. **Fokus nach dem Schließen:** Das Zielbild gibt ihn immer ans Feld „Fahrtenname“ zurück; im Tool geht er dorthin, wo er war, als die Meldung erschien. Auf „Mein Profil“ ist das das Feld, im Katalog der Knopf, der sie gezeigt hat.
5. **„Bewegung reduzieren“:** Das Zielbild blendet dann in 0,01 Sekunden über die Deckkraft ein; im Tool erscheint und verschwindet sie ganz ohne Übergang, wie alle Bewegungen des Tools bei dieser Einstellung.
6. **Abstand zum Rand am Handy** berücksichtigt zusätzlich den Rand des Bildschirms bei iPhones mit Aussparung (`env(safe-area-inset-…)`), wie die Leiste oben.
