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
2. **„Mitgliedschaft und Austritt verwaltest du in deiner Organisation.“ mit „Organisation öffnen“ fehlt.** Es widerspricht der Entscheidung zu #65: An dieser Stelle steht seit #286 der Knopf „Austreten“ in der Fläche der Mitgliedschaft, zart rot wie „Entfernen“ (Baustein „Knopf „Entfernen““), ohne den Satz davor.
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
    - **Fehler am Feld** (mehr als 50 Zeichen; seit #214 mehr als 30) steht rot unter dem Feld, das offen bleibt; das Zielbild zeigt keinen Fehler.


### Vorbild für den Regler der Einwilligung (#98)

Der Regler bei „Profil freigeben“ (CSS-Klasse `toggle`) ist Vorbild für den Schalter der Einwilligung im Dialog „Verwaltete Person anlegen“ (#98, [Zielbild-Kommentar](https://github.com/sebivtt/dpv-participant-management/issues/98#issuecomment-6522707882)); im Tool ist er der Baustein „Schalter“ aus #95, erweitert (Sebastian, 12.11.2026: „Schalter erweitern“). Bleibende Abweichungen nach der [Nachklärung](https://github.com/sebivtt/dpv-participant-management/issues/98#issuecomment-6522708153) N1 bis N5:

1. **Kein „i“-Hinweis**, nur der Satz aus DSG-02, ohne Hilfesatz.
2. **Beim Öffnen immer auf „aus“:** Eine Einwilligung ist nie vorbelegt.
3. **Fehlermeldung rot unter dem Regler**, mit ihm verbunden, wie bei den Textfeldern; das Zielbild zeigt keinen Fehler.
4. **Wirkung erst beim Speichern:** Er zählt erst mit „Anlegen“; Vorleseprogramme sagen ihn deshalb als Ankreuzfeld an. Im Zielbild schaltet er sofort.
5. **Ohne Kleintext und ohne gesperrten Zustand;** der Baustein kann beides für spätere Seiten (#137).
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

## Organisation

- **Datei:** [`organisation.html`](organisation.html)
- **Stand:** 27.10.2026. Sebastian hat mit Gemini vier Varianten entworfen; die Klärungs-Session hat daraus zwei nach den Szenarien und der Rechtematrix neu aufgebaut, Sebastian hat Variante 1 (Gliederung links, Seite rechts) gewählt und als Vorlage für #93 bestimmt. Eingespielt mit #189 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441100484)).
- **Prüfsumme (SHA-256):** `6588b56761e8906246d416edec3c60a15bd4aa2fc9f69e2b90f23c6d13ad5d2d`
- **Inhalt der Datei:** nur erfundene Personen und Organisationen (Pfadfinderbund Boreas, Wanda, Fiete …), alle Mails auf `example.org`. Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript schaltet nur zwischen Personen und Fällen um; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #93 ([Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/93#issuecomment-6436014693), [Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441101266)), umgesetzt in #189 ([Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441094033)).

### Abweichungen der Seite vom Zielbild

1. **Immer zugeklappt:** Organisationen ohne Zugriff stehen immer unter „… weitere ohne Zugriff“, auch eine einzelne; das Zielbild klappt erst ab drei zu (Nachklärung, N5).
2. **Nur Anzeige in #189:** Der Knopf „… benennen“ mit seinem Dialog kam mit #190 (Abweichungen unten); „Entfernen“ und „Rolle abgeben“ kamen mit #191.
3. **Nicht Teil von #93, nur Ausblick im Zielbild:** der Abschnitt „Personen“ (seit #285 nach seinem eigenen Zielbild, unten), die Sicht der Verbandsleitung (#94), das dunkle Steuerband und der gelbe Hinweiskasten.
4. **Rolle als Rollenmarke:** Hinter jeder Leitung steht die Rolle als Rollenmarke wie auf „Mein Profil“, nicht als runde Pille (Sebastian, 28.10.2026, bei der Umsetzung von #189).
5. **„Organisationen darunter“ als Rollenkachel:** wie die Kacheln auf „Mein Profil“, klein die Art als Rollenmarke, groß der Name, darunter die Leitung; ohne Zugriff grau, ohne blauen Streifen und nicht anklickbar (Sebastian, 28.10.2026, bei der Umsetzung von #189). Im Zielbild steht die Art in Großbuchstaben.
6. **Übersicht:** Am PC steht neben der Gliederung die oberste Organisation, die man selbst leitet; am Handy nur die Gliederung. Für Vorleseprogramme heißt die Seite „Organisation“.
7. **Pfad und Organisationen** sind Links mit eigener Adresse statt Knöpfen, damit jede Organisation ihre eigene Adresse hat (#189).
8. **Navigation und Fußbereich** kommen wie auf jeder Seite aus dem Tool; der Punkt „Organisation“ ist hervorgehoben wie jeder aktive Punkt.
9. **Höhe der Gliederung:** Im Zielbild richtet sie sich nach der Seite rechts. Im Tool ist sie am PC so hoch wie der Bildschirm abzüglich des Rands und bleibt beim Rollen stehen, damit sie beim Wechsel zwischen Seiten nicht springt (Sebastian, 28.10.2026, beim Testen von #189).

### Abweichungen des Dialogs „… benennen“ vom Zielbild (#190)

1. **Kurze Meldung statt fester Meldung oben:** Nach dem Benennen steht die Erfolgsmeldung unten als kurze Meldung (#186); das Zielbild zeigt sie fest oben mit ×, damals mit „Wortlaut noch offen“ (Sebastian, 28.10.2026, bei der Umsetzung von #190).
2. **Eigene Adresse:** Der Dialog ist eine eigene Seite über der Organisation, damit er ohne Skript geht; „Abbrechen“ und × führen zur Seite der Organisation zurück.
3. **Ablehnungen nach dem Benennen** stehen als Warnung im Dialog ohne die Trefferliste darüber; die Suche beginnt danach neu.
4. **Ohne Skript keine Vorschläge beim Tippen;** „Suchen“ geht.
5. **Kein Kasten „Zum Ausprobieren“** und kein Zähler der Suchen: Sie gehören wie das Steuerband nicht zur Seite.
6. **„Benennen“ als weißer Knopf mit feinem Rand** (wie „Verwerfen“ auf „Mein Profil“) statt hellblau; ein hellblauer Knopf ist kein entschiedener Baustein.

## Personen

- **Datei:** [`personen.html`](personen.html)
- **Stand:** 28.10.2026, Fassung 2: der grobe Entwurf der Klärungs-Session zu #65 mit Sebastians Änderung, dass „Austragen“ wie „Verschieben“ eine zarte Fläche bekommt, rot in den Farben der Fehlermeldung. Übernommen in #285 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/285#issuecomment-6766981320)), eingespielt mit #285 aus dem Zweig `claude/personen-65` (`f0279b1`).
- **Prüfsumme (SHA-256):** `93e97f1d2ec233ebe02c029e7da3f1c61aa5da9e0cc617b9b8aa726c50f9c79a`
- **Inhalt der Datei:** nur erfundene Personen und Organisationen (Pfadfinderbund Boreas, Wanda, Finn …), alle Mails auf `example.org`. Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript schaltet nur zwischen Personen und Fällen um; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #65 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/285#issuecomment-6766981714), N1 bis N5), umgesetzt in #285 ([Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/285#issuecomment-6766975648)); „Austragen“ umgesetzt in #286 ([Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/286#issuecomment-6766976020)), „Verschieben“ umgesetzt in #287 ([Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/287#issuecomment-6766976342)).

### Abweichungen des Abschnitts „Personen“ und des Dialogs „Person aufnehmen“ vom Zielbild (#285)

1. **„Verschieben“ und „Austragen“ kamen später:** „Austragen“ mit #286, „Verschieben“ mit #287, beide rechts im Baustein (Abweichungen unten).
2. **Person als Baustein „Person in einer Liste“:** wie die Leitungen darüber (#189), die Rollen als Rollenmarken statt runder Pillen, die Mail in der zweiten Zeile rechts statt neben dem Namen.
3. **Eigene Adresse:** Der Dialog ist eine eigene Seite über der Organisation, damit er ohne Skript geht, wie „… benennen“ (#190); „Abbrechen“ und × führen zur Seite der Organisation zurück.
4. **„Aufnehmen“ als weißer Knopf mit feinem Rand** wie „Benennen“ in der Trefferliste (#190) statt dunkelblau.
5. **„Kein Konto gefunden …“ als Warnung** wie im Dialog „… benennen“ (#190) statt als Information, damit dieselbe Meldung überall gleich aussieht.
6. **Kein Kasten „Zum Ausprobieren“** und kein Zähler der Suchen: Sie gehören wie das Steuerband nicht zur Seite.

### Abweichungen von „Austragen“ vom Zielbild (#286)

1. **„Austragen“ auch beim eigenen Eintrag** (Sebastian bei der Umsetzung, 10.11.2026); im Zielbild fehlt der Knopf dort.
2. **Eigene Adresse:** Der Dialog ist eine eigene Seite über der Organisation, damit er ohne Skript geht, wie „Person aufnehmen“ (oben, Punkt 3).
3. **Vorschau je Möglichkeit:** Sie kommt fertig vom Server und wechselt mit der Wahl allein über das Aussehen, auch ohne Skript (Baustein „Auswahl im Dialog“); die Wahl ist nicht in ein umrandetes Feld mit Text gefasst, sondern Optionsfeld und Beschriftung stehen nebeneinander in einer umrandeten Zeile.
4. **Satz zur letzten Leitung** wie beim Entfernen (#191), nicht wie im Zielbild: beim Bund „… und niemand springt ein. Eine neue Bundesleitung kann nur die Verbandsleitung benennen.“, ohne „Trotzdem …?“.

### Abweichungen von „Verschieben“ vom Zielbild (#287)

1. **Eigene Adresse:** Der Dialog ist eine eigene Seite über der Organisation, damit er ohne Skript geht, wie „Austragen“ (oben, Punkt 2).
2. **Wahl als Baustein „Auswahl im Dialog“ ohne Vorschau** (Sebastian bei der Umsetzung, 10.11.2026, „2a“): Optionsfeld und Beschriftung nebeneinander in einer umrandeten Zeile, wie beim Austragen.
3. **Fehlermeldung als Baustein „Meldungen“** (Art Fehler) unter der Wahl statt einer roten Zeile mit ×, damit sie aussieht wie jede Fehlermeldung an der Stelle der Handlung (#186). Die abgelehnte Organisation bleibt gewählt, wie im Zielbild (Sebastian: „Ja, gewählt lassen“).

## Verwaltete Personen

- **Datei:** [`verwaltete-personen.html`](verwaltete-personen.html)
- **Stand:** 28.10.2026, Fassung 2: Sebastians Fassung 1 (`entwurf-117-v3.html`, aus dem groben Entwurf der Klärung), von der KI an die Nachklärung N1 bis N7 angepasst; Sebastian hat sie gewählt („Ja, Fassung 2“). Übernommen in #117 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6478711946)), eingespielt mit #117.
- **Prüfsumme (SHA-256):** `be89525874bdcbb10c4c2bc5a37170c98d59eb868013040278ced48a590b005b`
- **Inhalt der Datei:** nur erfundene Personen und Organisationen (Pfadfinderbund Boreas, Lena Probe „Kiwi“, Wanda …), alle Mails auf `example.org`. Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript schaltet nur zwischen Personen und Fällen um; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #117 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6478724205), N1 bis N7; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6478724730)). Es zeigt den Abschnitt „Personen“ und den Dialog; der Rest der Seite kommt aus `organisation.html` und `personen.html`.

### Abweichungen vom Zielbild (#117)

Alle folgen daraus, dass die Seite die Bausteine aus dem Bausteinkatalog einbindet (`docs/gestaltung.md`), statt das Aussehen des Zielbilds nachzubauen.

1. **Eigene Adresse:** Beide Dialoge sind eigene Seiten über der Organisation, damit sie ohne Skript gehen, wie „Person mit Konto aufnehmen“. Nach dem Dialog führen ×, „Abbrechen“, Escape und das Speichern zur Seite mit der Kennung des Knopfs, der ihn geöffnet hat, in der Adresse; das Skript gibt diesem Knopf wieder den Fokus.
2. **Felder aus den Bausteinen „Textfeld“ und „Datumsfeld“:** Pflichtfelder tragen „(Pflicht)“ statt eines Sternchens, der Satz „* Pflichtangabe“ fehlt, und der Fahrtenname steht ohne „(freiwillig)“. Unter Vorname, Nachname und Fahrtenname steht beim Tippen die Zahl der Zeichen (#215); nichts wird beim Einfügen abgeschnitten, das Zielbild schneidet mit `maxlength` ab. Der Fehler steht rot unter dem Feld wie bei jedem Textfeld, ohne × davor.
3. **„… wurde inzwischen von jemand anderem geändert …“** steht wie im Zielbild oben im Dialog, im Aussehen des Bausteins „Meldungen“ (Art Fehler).
4. **Marke „verwaltet“ in der zweiten Zeile,** wo bei Personen mit Konto die Rollen und „gesperrt“ stehen (Baustein „Person in einer Liste“), nicht hinter dem Namen.
5. **„Bearbeiten“ ohne Stift,** als Baustein „Knopf „Verschieben““: gleiche zarte blaue Fläche, aber ohne Symbol.
6. **Kein Kasten „Zum Ausprobieren“:** Er gehört wie das Steuerband nicht zur Seite.
