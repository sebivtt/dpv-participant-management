# Zielbilder

Ein Zielbild ist Sebastians fertiger Entwurf einer Seite als HTML-Datei, mit erfundenen Daten. Es zeigt, wie die Seite aussehen soll und wohin sie wächst, oft mit mehr, als das Tool heute speichert. Ablauf „Zielbild vor Gestaltung“: `CLAUDE.md`; entschieden in `docs/entscheidungen.md`, Einträge vom 25.10.2026 zu #161 und vom 26.10.2026 zu #162.

Ein Zielbild ist **Orientierung, keine Anforderung.** Was es zeigt, gibt niemandem ein Recht und ändert keine Entscheidung. Es gehen vor: `docs/rechtematrix.md`, `docs/anforderungen.md`, `docs/entscheidungen.md`, `docs/gestaltung.md`. Gebaut wird nur, was das Tool speichert; Teile ohne Daten fehlen ganz, ohne leere Platzhalter.

Die Dateien liegen unverändert so im Repo, wie Sebastian sie geliefert hat; sie öffnen sich mit Doppelklick im Browser. Das Tool lädt sie nie. Für jede Datei steht hier, von wann sie ist, woher sie kommt, ihre Prüfsumme und wo die Seite bewusst abweicht. Eine neue Fassung ersetzt die Datei; die alte bleibt in der Versionsgeschichte, und Datum und Prüfsumme hier werden fortgeschrieben. Je Datei prüft ein Test (`tests/test_mein_profil.py`, `tests/test_meldungen.py`, `tests/test_kurzmeldung.py`, `tests/test_adressfeld.py` u. a.), dass Datei und Prüfsumme zusammenpassen und die Datei nichts von fremden Servern lädt.

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

### Abweichungen beim Löschen vom Zielbild zu #117, Fassung 1 (#118)

Vorlage für das Löschen ist [Fassung 1 des Zielbilds zu #117](https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6478456757) (Nachklärung N5); im Repo liegt Fassung 2 ohne Löschen. Die Wortlaute hat #118 selbst geklärt ([Protokoll vom 11.11.2026](https://github.com/sebivtt/dpv-participant-management/issues/118#issuecomment-6789855626), Frage 2).

1. **Wortlaut der Rückfrage:** Titel „Kiwi (Lena Probe) endgültig löschen?“ und darunter „Das lässt sich nicht rückgängig machen.“ statt „… löschen?“ mit gelbem Warnkasten „… wirklich löschen? Die verwaltete Person wird dauerhaft … entfernt …“; die kurze Meldung danach heißt „Kiwi (Lena Probe) wurde gelöscht.“ statt „Die verwaltete Person … wurde gelöscht.“.
2. **Eigene Adresse:** Die Rückfrage ist eine eigene Seite über der Organisation, damit sie ohne Skript geht; „Nicht löschen“ führt zurück in den Dialog „Bearbeiten“, × zur Seite. Im Zielbild wechselt derselbe Dialog nur die Knöpfe.
3. **Knöpfe aus den Bausteinen:** „Verwaltete Person löschen“ ist der Baustein „Knopf „Entfernen““ (zart rot, klein), „Nicht löschen“ hat das Aussehen von „Abbrechen“, „Endgültig löschen“ ist der rote Knopf des Dialogs.
4. **Nur für wer löschen darf** (N5): die Leitung der eigenen Organisation der Person oder die einspringende, nicht jede, die bearbeiten darf, wie es das Zielbild zeigt.

## Person aufnehmen

- **Datei:** [`person-aufnehmen.html`](person-aufnehmen.html)
- **Stand:** 14.11.2026, der grobe Entwurf aus der Klärung von #298 (`entwurf-298.html`) mit einer Korrektur der Lage des Dialogs; Sebastian: „Entwurf ist mein Zielbild“. Übernommen in #298 ([Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/298#issuecomment-6875289041)), eingespielt mit #298.
- **Prüfsumme (SHA-256):** `1a9d7d68b79aa79ce5234d341a5c5509a5a139235439b7c39957f923111be547`
- **Inhalt der Datei:** nur erfundene Personen (Fiete Gans, Finn Meise, Kiwi (Lena Probe), Otto), alle Mails auf `example.org`. Nichts von fremden Servern, kein Skript, Systemschrift.
- **Orientierung, keine Anforderung.** Geklärt in #298 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/298#issuecomment-6875289269), N1 bis N5; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/298#issuecomment-6875044923)). Es zeigt den Knopf „Person aufnehmen“, den Dialog mit den zwei großen Flächen (neuer Baustein „Wahl mit großen Flächen“) und „Zurück“ in beiden Wegen; der Rest der Seite kommt aus `organisation.html`, `personen.html` und `verwaltete-personen.html`.

### Abweichungen vom Zielbild (#298)

1. **Symbole** (N1): oben das Symbol „@“ des Tools statt der Lupe, unten das Plus des Tools statt des Schriftzeichens.
2. **Nur im Entwurf** (N2): die gelbe Hinweiszeile, die Leiste mit den vier Ansichten, der Satz „PA1: …“ unter der Fläche und „… darunter der Schalter zur Einwilligung wie heute“ kommen nicht ins Tool.
3. **Was der Entwurf nur andeutet, bleibt wie heute** (N3): die Liste „Personen“, Seitenkopf und Pfad und die beiden Dialoge „Person mit Konto aufnehmen“ und „Verwaltete Person anlegen“ mit ihren Feldern und Knöpfen; dort kommt nur „Zurück“ dazu. Im Dialog „Person mit Konto aufnehmen“ steht wie heute bis zur Suche kein Knopf zum Bestätigen.
4. **Knopf und Überschrift aus den Bausteinen:** „Person aufnehmen“ ist der Knopf der „Überschrift einer Fläche“ mit dem Plus des Tools statt des Schriftzeichens „＋“; der Dialog ist der Baustein „Dialog“ mit eigener Adresse, damit er ohne Skript geht.
5. **Am Handy nur das Plus** (Sebastian bei der Vorschau, 15.11.2026): Im Zielbild steht der Knopf auch am Handy mit Text. Im Tool zeigt er dort nur das Plus und bleibt in der Zeile der Überschrift, wie jeder Knopf in der „Überschrift einer Fläche“; die Zahl „3 Personen“ rückt bei Platzmangel unter den Titel.

## Support-Zugang

- **Datei:** [`support-zugang.html`](support-zugang.html)
- **Stand:** 11.11.2026, grober Entwurf der Klärung von #92, von Sebastian am 12.11.2026 unverändert als Zielbild übernommen („Entwurf passt so“, [Kommentar mit Datei und Prüfsumme](https://github.com/sebivtt/dpv-participant-management/issues/92#issuecomment-6819555590)), eingespielt mit #92 unter dem neuen Namen `support-zugang.html` (vorher `entwurf-92-support-zugang.html`).
- **Prüfsumme (SHA-256):** `5563c461945c2872b2e317386483d28cf46447383152040b5f967825c0449c4c`
- **Inhalt der Datei:** nur erfundene Personen und Organisationen (Max, Pfadfinderbund Boreas, Wanda Muster, Lena Probe „Kiwi“ …), alle Mails auf `example.org`. Nichts von fremden Servern: Gestaltung und Symbole stehen in der Datei, die Schrift ist die Systemschrift. Ein eingebettetes Skript schaltet nur zwischen den Zuständen um; ins Tool ist davon nichts übernommen.
- **Orientierung, keine Anforderung.** Geklärt in #92 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/92#issuecomment-6819688530), N1 bis N4b; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/92#issuecomment-6819688970)). Es zeigt den Kopf einer Organisation mit „Support-Zugang starten“, den Dialog, den Balken und die Meldungen nach Ablauf; Leitungen und Personen deutet es nur an, sie kommen aus `organisation.html`, `personen.html` und `verwaltete-personen.html`.

### Abweichungen vom Zielbild (#92)

Alle folgen daraus, dass die Seite die Bausteine aus dem Bausteinkatalog einbindet (`docs/gestaltung.md`), statt das Aussehen des Zielbilds nachzubauen.

1. **Eigene Adresse:** Der Dialog „Support-Zugang für … starten“ ist eine eigene Seite über der Organisation, damit er ohne Skript geht, wie die übrigen Dialoge der Seite.
2. **„Bitte wähle einen Anlass.“ als Baustein „Meldungen“** (Art Fehler) unter der Wahl statt einer roten Zeile mit ×, wie die Fehlermeldung beim Verschieben (#287).
3. **Gliederung wie auf der Seite „Organisation“:** Marken, Leitungen und zugeklappte Teile kommen aus dem Baustein „Gliederung“ (#189); neben der Überschrift steht wie im Zielbild „alle Bünde“. Auf „Organisation“ steht neben der Gliederung zuerst der erste Bund nach dem Alphabet, nur mit dem Kopf.
4. **Kein Steuerband und kein Hinweiskasten:** Beide gehören nicht zur Seite.

## Veranstaltung

- **Datei:** [`veranstaltung.html`](veranstaltung.html)
- **Stand:** 16.11.2026, der grobe Entwurf 6 aus der Klärung von #356 (`grober-entwurf-veranstaltung-6.html`); Sebastian: „okay, der grobe entwurf 6 passt so und kann als Zielbild hinterlegt werden, danke!“ ([Kommentar „Zielbild (16.11.2026)“](https://github.com/sebivtt/dpv-participant-management/issues/356#issuecomment-6931549673), Datei unverändert aus dem [Kommentar zu Entwurf 6](https://github.com/sebivtt/dpv-participant-management/issues/356#issuecomment-6931507830)), eingespielt mit #379.
- **Prüfsumme (SHA-256):** `9d1c86c1d2a7531e05df07457e8a787d7664ba7476026c92784ec84d1f19184a`
- **Inhalt der Datei:** nur erfundene Personen, Organisationen und Adressen (Wanda, Finn, Stamm Walhall, „Burgweg 1, 99999 Musterhausen“ …). „Burg Ludwigstein“ ist ein echter Ortsname, als Bezeichnung eines Veranstaltungsorts aus dem Beispiel in #163 übernommen, ohne Personendaten. Nichts von fremden Servern, kein Skript, Systemschrift, die Symbole stehen in der Datei.
- **Orientierung, keine Anforderung.** Geklärt in #356 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/356#issuecomment-6931638822), E1 bis E4 und N1 bis N5; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/356#issuecomment-6931639174)). Es zeigt alle Seiten rund um eine Veranstaltung: 1 Liste, 2 bis 5 Anlegen in vier Schritten, 5b Abbrechen, 6 Leitungsseite, 6b bis 6d Veröffentlichen und Zurücknehmen, 7 Einladung. Welches Issue welchen Teil baut, steht in #356 („Welches Unter-Issue baut was“); jedes ergänzt hier seine Abweichungen.

### Abweichungen vom Zielbild (#379)

#379 baut Ansicht 1 nur mit „Von mir geleitet“ und von Ansicht 6 den Kopf und die Kachel „Grunddaten“; dazu Uhrzeiten und Ort im Dialog „Veranstaltung erstellen“.

1. **Plus weiß** (E1 aus #356): „Veranstaltung erstellen“ ist der Knopf der „Überschrift einer Fläche“ mit weißem Plus, wie im Zielbild; die frühere Regel „Sonnengelb für das Symbol von ‚Veranstaltung erstellen‘“ in `docs/gestaltung.md` gilt nicht mehr (`docs/entscheidungen.md`, 17.11.2026, #379).
2. **Noch nicht gebaut, kommt mit seinem Issue:** Zustandsmarken, gestrichelte und graue Zeilen (#359, seit dem 26.11.2026 gebaut, Abschnitt unten), „Für mich ausgeschrieben“ (#362), „Einladung ansehen“ auf der Leitungsseite (#362; Zustand und „Veröffentlicht“ seit dem 26.11.2026 gebaut, #359), die übrigen Kacheln (#358, seit dem 26.11.2026 gebaut, Abschnitt „Einladungstext“; #360, seit dem 27.11.2026 gebaut, Abschnitt unten; #361, #151, #357), die Adresse unter dem Ort (#163, seit dem 18.11.2026 gebaut, Abschnitt „Adressfeld“). Was fehlt, fehlt ganz, ohne Platzhalter.
3. **Kachel allein:** Solange „Grunddaten“ die einzige Kachel ist, steht sie am PC in der linken Spalte, rechts bleibt frei; schmal steht sie über die ganze Breite. Seit #360 steht rechts daneben die Kachel „Anmeldung“.
4. **Bausteine statt nachgebautem Aussehen:** die Zeilen der Liste als neuer Baustein „Veranstaltung in einer Liste“, die Kachel als Fläche mit „Überschrift einer Fläche“ und „Bearbeiten-Symbol“, Beginn und Ende als neuer Baustein „Kalenderblätter“, die Felder im Dialog als „Textfeld“ und „Datumsfeld“ mit Uhrzeit (Sebastian, 17.11.2026, [Kommentar in #379](https://github.com/sebivtt/dpv-participant-management/issues/379#issuecomment-6956297747)). Der Stift öffnet einen Dialog mit eigener Adresse, den das Zielbild nicht zeigt.
5. **Vorleseprogramme** hören vor den Kalenderblättern „Beginn:“ und „Ende:“ und vor dem Ort „Ort:“; sichtbar ist das nicht.
6. **Beschriftung „Ort“** (seit #163 „Bezeichnung“ in einer eigenen Fläche „Ort“, Abschnitt „Adressfeld“) ohne „(freiwillig)“: Freiwillige Felder stehen ohne Zusatz (`docs/gestaltung.md`, „Textfelder“; Sebastian bei der Vorschau, 17.11.2026: „Nur „Ort““). Beim Datum steht „(Pflicht, Uhrzeit freiwillig)“ wie im Zielbild, weil ein Feld dort beides enthält.
7. **Datum und Uhrzeit** wie im Zielbild im Verhältnis 2 zu 1 (Sebastian bei der Vorschau: „Wie Zielbild“); die Uhrzeit ist aber nie schmaler als nötig, damit „18:00“ mit dem Uhr-Symbol des Browsers auch im schmaleren Dialog ganz zu sehen ist. Bei einem Fehler zeigen beide Felder den roten Rahmen ohne das rote Ausrufezeichen von Bootstrap, für das neben Kalender- und Uhr-Symbol kein Platz ist.
8. **Kein Satz „Die Uhrzeiten sind mit 18:00 und 12:00 vorausgefüllt; …“** unter Beginn und Ende: Er erklärt nur den Entwurf (Sebastian bei der Vorschau: „Nur Erklärung“).
9. **Zahl der Zeichen** unter Name und Ort („0/100“), die das Zielbild nicht zeigt: Sie gehört zum Baustein „Textfeld“ bei einer fachlichen Grenze (#215).

### Abweichungen vom Zielbild (#380)

#380 baut die Ansichten 2 (Schritt 1 „Grunddaten“), 5 (Zusammenfassung) und 5b (Dialog „Anlegen abbrechen?“).

1. **Zwei Schritte statt vier:** „Schritt 1 Grunddaten · Schritt 2 Zusammenfassung“; „Einladungstext“ und „Anmeldung“ (Ansichten 3 und 4) bringen ihre Issues (#358, #360, #361, #151) und fügen sich dazwischen ein. Die Zusammenfassung zeigt deshalb nur die Grunddaten. Seit dem 26.11.2026 ist „Einladungstext“ Schritt 2 und die Zusammenfassung Schritt 3 mit dem Einladungstext unter den Grunddaten (#358, Abschnitt „Einladungstext“). Seit dem 27.11.2026 sind es vier Schritte wie im Zielbild, mit „Anmeldung“ als Schritt 3 (#360, Abschnitt unten).
2. **„Zurück“ auch auf der Zusammenfassung** (Frage 4 aus #29, `docs/entscheidungen.md`, 17.11.2026, #380, Nr. 2), blau umrandet zwischen „Abbrechen“ und „Veranstaltung speichern“.
3. **Grunddaten als Kalenderblätter** wie in der Kachel der Leitungsseite statt der Liste mit Name, Zeitraum und Ort (Sebastian, 17.11.2026: „Kalenderblätter“); der Name steht oben im Kopf.
4. **Beschriftung „Ort“** (seit #163 „Bezeichnung“ in einer eigenen Fläche „Ort“, Abschnitt „Adressfeld“) ohne „(freiwillig)“, wie in #379 (Sebastian, 17.11.2026: „Nur „Ort““); kein Satz zu den vorausgefüllten Uhrzeiten (wie #379, Nr. 8); keine Adresse unter dem Ort (#163; seit dem 18.11.2026 gebaut, Abschnitt „Adressfeld“).
5. **Satz im Dialog** „Sommerfahrt 2028 ist als Entwurf gespeichert. …“ ohne „bis Schritt 3“, wie im Text von #380. Darf die Person nicht löschen (Mitleitung, Anmeldung), stehen nur „Entwurf speichern“ und der Satz ohne „oder ihn löschen“.
6. **Kopf von Schritt 1:** „Veranstaltung erstellen“ wie im Zielbild; für einen gespeicherten Entwurf (nach „Zurück“ oder dem Stift) sein Name mit „Entwurf · Veranstaltung erstellen“ wie auf der Zusammenfassung.
7. **Stift** mit dem Baustein „Bearbeiten-Symbol“; Vorleseprogramme hören „Grunddaten ändern“. Er führt zu Schritt 1, nicht zu einem Dialog.

### Abweichungen vom Zielbild (#359)

#359 baut in Ansicht 1 Zustandsmarken und Zeilen unter „Von mir geleitet“, in Ansicht 6 die Fläche „Zustand“ und die Rückfragen der Ansichten 6b und 6d; der Kopf nach dem Veröffentlichen (6c) zeigt „Angekündigt“.

1. **Symbol statt Punkt** in jeder Zustandsmarke (#356 N3, „Regel gilt, Symbol dazu“): „Entwurf“ Blatt, „Angekündigt“ Megafon, „Läuft“ Abspielzeichen, „Beendet“ Zielfahne; die Farben wie im Zielbild.
2. **Schalter als eigener Baustein** „Schalter mit Rückfrage“ (Sebastian, 26.11.2026: „Neuer Baustein“, [Kommentar in #359](https://github.com/sebivtt/dpv-participant-management/issues/359#issuecomment-7185965936)); Aussehen wie im Zielbild, der Titel „Veröffentlicht“ rechts neben dem Schalter.
3. **Noch nicht gebaut, kommt mit seinem Issue:** „Einladung ansehen“ (#362); in Satz und Rückfrage der Teilnahmekreis (#361) und der Beginn der Anmeldung (#360, seit dem 27.11.2026 gebaut, Abschnitt unten), daher „Die Veranstaltung ist veröffentlicht.“ statt „Sichtbar für Stamm Walhall. …“ (6c) und „Danach sieht der Teilnahmekreis die Einladung.“ ohne Namen (6b); „Anmeldung offen“, „Geschlossen“ und die Frist unter der Marke (#360, ebenso gebaut). Was fehlt, fehlt ganz, ohne Platzhalter.
4. **Ohne Hinweis auf P4** in der Rückfrage „… zurücknehmen?“: Der graue Satz „Was mit bestehenden Anmeldungen geschieht, kommt mit P4 (#366).“ ist eine Notiz des Zielbilds, kein Text des Tools.
5. **Fehler in der Rückfrage:** Lehnt der Server ab (Beginn vorbei, schon begonnen), bleibt die Rückfrage offen und zeigt den Satz als Fehlermeldung oben; das Zielbild zeigt diesen Fall nicht.

### Abweichungen vom Zielbild (#360)

#360 baut in Ansicht 4 die Gruppe „Fristen“, in Ansicht 5 den Abschnitt „Anmeldung“ mit den Fristen, in Ansicht 6 die Kachel „Anmeldung“, in Ansicht 1 die Frist unter der Marke und in 6b und 6c die Sätze zur Anmeldung.

1. **Fristen freiwillig und ohne Uhrzeit** (Klärung von #360, Fragen 1 bis 3), abweichend vom Hinweis in Ansicht 4; die Felder stehen ohne „(freiwillig)“, wie alle freiwilligen Felder (`docs/gestaltung.md`, „Textfelder“).
2. **Schritt 3 nur mit „Fristen“:** Teilnahme- und Benachrichtigungskreis (Ansicht 4) bringen #361 und #151; im Abschnitt „Anmeldung“ der Zusammenfassung fehlen sie ebenso. Was fehlt, fehlt ganz, ohne Platzhalter.
3. **Zusammenfassung wie die Leitungsseite:** die Fläche „Anmeldung“ genau wie die Kachel der Leitungsseite, mit der Zeitleiste statt „Anmeldung 01.02.2028 bis 30.04.2028“ und „Änderungsschluss 07.05.2028“, neben „Grunddaten“, der Einladungstext darunter, statt aller Abschnitte untereinander (Vorschau, Sebastian, 27.11.2026: „Neben Grunddaten“ und Zeitleiste wie auf der Leitungsseite; so auch bei den Grunddaten, #380, Nr. 3).
4. **Symbol statt Punkt** in den neuen Zustandsmarken wie in #359, Nr. 1: „Anmeldung offen“ offenes Schloss, „Geschlossen“ Schloss; die Farben wie im Zielbild.
5. **„Heute“ wandert mit:** Im Zielbild steht „Heute“ am 05.01.2028 oben; in der Kachel steht es immer vor der nächsten Frist ab heute, sonst hinter der letzten eingetragenen. Fristen ohne Tag zeigen grau, was dann gilt. Vergangene Fristen haben einen zart grünen Punkt mit dunkelgrünem Haken, den das Zielbild nicht zeigt (Vorschau, Sebastian, 27.11.2026).
6. **Ohne Fettdruck** in der Rückfrage (6b): „Die Anmeldung öffnet am 01.02.2028 und läuft bis 30.04.2028.“ steht als schlichter Satz, wie die übrigen Sätze der Rückfragen.
7. **Dialog „Anmeldung bearbeiten“** mit eigener Adresse, den das Zielbild nicht zeigt; darin dieselben Felder wie in Schritt 3. Vorleseprogramme hören am Stift „Anmeldung bearbeiten“, auf der Zusammenfassung „Anmeldung ändern“.

## Einladungstext

- **Datei:** [`einladungstext.html`](einladungstext.html)
- **Stand:** 17.11.2026, der grobe Entwurf 2 aus der Klärung von #358 (`grober-entwurf-einladungstext-2.html`), nach Sebastians Anmerkung zu Entwurf 1 (Zahl der Zeichen); Sebastian: „Perfekt - passt genau so!“ ([Kommentar „Zielbild (17.11.2026)“](https://github.com/sebivtt/dpv-participant-management/issues/358#issuecomment-6950910175), Datei unverändert daraus), eingespielt mit #358.
- **Prüfsumme (SHA-256):** `ca32a675f7265f55d64aa2fe4e6746a669a1824caa63f66b168ed7ae2412d468`
- **Inhalt der Datei:** nur erfundene Personen, Adressen und Nummern (Wanda, „wanda@example.org“, „0000 000000“ …); „Burg Ludwigstein“ wie im Zielbild „Veranstaltung“. Nichts von fremden Servern, kein Skript, Systemschrift, die Symbole stehen in der Datei.
- **Orientierung, keine Anforderung.** Geklärt in #358 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/358#issuecomment-6951036238), N1 und N2; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/358#issuecomment-6951036732)). Es zeigt den Baustein „Editor“ und den Einladungstext: 1 Schritt 2, 2 Link setzen, 3 zu lang, 4 Zusammenfassung, 5 Kachel, 6 Dialog, 7 gleichzeitig geändert, 8 ohne JavaScript, 9 am Handy. Für die umgebenden Seiten gilt das Zielbild „Veranstaltung“.

### Abweichungen vom Zielbild (#358)

1. **Beschriftung ohne „(freiwillig)“** (N1: „Wie die Regel“): nur „Einladungstext“, wie jedes freiwillige Feld.
2. **Meldung nach dem Speichern als kurze Meldung** (#186) unten statt der blauen Zeile oben (Nachklärung, „Folgt aus geltenden Regeln“).
3. **Hinweis „inzwischen geändert“** im Baustein „Meldungen“, Art Warnung (#165), mit Symbol und vorgelesenem „Warnung:“, statt des gelben Kastens ohne Symbol (Ansicht 7).
4. **Drei Schritte statt vier:** „Schritt 3 Anmeldung“ kommt mit seinem Issue (#360); bis dahin ist die Zusammenfassung Schritt 3. Seit dem 27.11.2026 sind es vier (Abschnitt „Veranstaltung“, Abweichungen #360). Die Zusammenfassung zeigt den Abschnitt „Einladungstext“ als Fläche mit Info-Symbol wie die Kachel der Leitungsseite und unter den Grunddaten aus #380.
5. **Fehler bei einer anderen Adresse für einen Link:** Erlaubt Trix eine Adresse im Feld „Adresse“ nicht, wird das Feld rot und darunter steht „Bitte gib eine Adresse mit https, http, mailto oder tel ein.“; das Zielbild zeigt diesen Fall nicht.
6. **Ohne JavaScript** steht im Textfeld die Formatierung, wie der Editor sie speichert: Absätze als `<div>` statt `<p>`, durchgestrichen als `<del>` statt `<s>`, die Überschrift als `<h3>` statt `<h2>`; von Hand eingegebenes `<p>`, `<s>` und `<h2>` geht ebenso.
7. **Satz „Ohne JavaScript …“ grau** in der Art eines Hinweises unter dem Feld und mit ihm verknüpft, wie die Zeile unter einem Suchfeld.
8. **Feld für einen Link schwebt unter dem gewählten Text** (Vorschau, Sebastian, 26.11.2026: „Ansonsten würde ich hier gerne dieses Feld genau unter dem gewählten Text haben wollen, dass über allem anderen schwebt“), im Aussehen wie die Knöpfe beim Fahrtennamen, statt als Leiste unter der Knopfleiste (Ansicht 2); darin rechtsbündig „Link setzen“ und „Verwerfen“ (Runde 2: „Die Buttons für das Link hinzufügen etc. bitte rechtsbündig.“), bei einem schon gesetzten Link „Link entfernen“ statt „Verwerfen“.

## Adressfeld

- **Datei:** [`adressfeld.html`](adressfeld.html)
- **Stand:** 17.11.2026, der grobe Entwurf 3 aus der Klärung von #163 (`grober-entwurf-adressfeld-3.html`), entstanden aus Entwurf 2 („Entwurf 2 passt so“) mit Sebastians zwei Anmerkungen (Ortssymbol in der Anzeige, kein Satz „Freiwillig …“); [Kommentar „Zielbild (17.11.2026, Fassung 2)“](https://github.com/sebivtt/dpv-participant-management/issues/163#issuecomment-6943103790), Datei unverändert daraus, eingespielt mit #163.
- **Prüfsumme (SHA-256):** `f1810ea5cc05037c140a6cab3919be45ff43c5c82617f2367c1bf4f23a5ce9fb`
- **Inhalt der Datei:** nur erfundene Personen und Adressen (Wanda, „Burgweg 1, 99999 Musterhausen“, „123 45 Exempelby“ …); „Burg Ludwigstein“ wie im Zielbild „Veranstaltung“. Nichts von fremden Servern, kein Skript, Systemschrift, die Symbole stehen in der Datei.
- **Orientierung, keine Anforderung.** Geklärt in #163 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/163#issuecomment-6943257214), Z1 bis Z3 und N1 bis N3; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/163#issuecomment-6943261413)). Es zeigt nur das Adressfeld: 1 leer, 2 Treffer, 3 nach „Übernehmen“, 4 Meldungen der Suche, 5 Fehler beim Speichern, 6 Ausland, 7 Anzeige. Was blau gestrichelt ist, baut #29 (#379, #380).

### Abweichungen vom Zielbild (#163)

1. **Farben und Symbole der Meldungen** aus dem Baustein „Meldungen“: „Zu wenig für die Suche“ ist eine gelbe Warnung statt rot (N1); „Keine Adresse gefunden …“ blau, „… nicht erreichbar …“ rot wie im Zielbild.
2. **Land als Auswahl** aller Länder, „Deutschland“ vorgewählt (N2); das Zielbild ließ offen, ob Text oder Auswahl. Das Bundesland verschwindet bei einem anderen Land auch ohne Skript, nicht nur mit (Zielbild, Ansicht 6: „Ohne Skript bleibt das Feld Bundesland stehen“).
3. **Treffer als Form „Ort“ der Trefferliste** (N3): Ortssymbol im zart blauen Kreis, Bezeichnung, Adresse und „Übernehmen“ wie im Zielbild, aber im Aussehen der Trefferliste des Tools (Rahmen um die Liste, Titel „Treffer“ klein und grau).
4. **Bausteine statt nachgebautem Aussehen:** Felder aus dem „Textfeld“, „Adresse suchen“ als „Zart blauer Knopf“ mit Lupe, Anzeige im Baustein „Kalenderblätter“. Die Zahl der Zeichen unter „Straße und Hausnummer“ und „Ort“ beim Tippen gehört zum Textfeld bei einer Grenze (#215); das Zielbild zeigt sie nicht.
5. **Keine Linie und keine sichtbare Überschrift „Adresse“** (Vorschau, Runde 3, Sebastian: „Ich würde den Trennstrich raus machen“): In der Fläche „Ort“ stehen Bezeichnung und Adresse nur mit ihren Beschriftungen untereinander; „Adresse“ hören nur Vorleseprogramme als Beschriftung der Gruppe.
6. **Anzeige in einer Zeile** steht im Kopf der Leitungsseite; die Zusammenfassung zeigt die Grunddaten seit #380 als Kalenderblätter, also wie die Kachel mehrzeilig (Szenario A1 nennt die Zusammenfassung mit der Zeile). In der Liste „Von mir geleitet“ bleibt es bei der Bezeichnung.
7. **Treffer mit Bundesland** in der Adresszeile („Burgweg 1, 99999 Musterhausen, Hessen“) wie im Zielbild; im Ausland steht dort das Land.
8. **Eigene Fläche „Ort“** (Vorschau, Sebastian, 18.11.2026, „Eigene Fläche“): Die Bezeichnung steht nicht über der Linie wie im Zielbild, sondern zusammen mit der Adresse in einer eigenen Fläche „Ort“ mit Ortssymbol und heißt „Bezeichnung“;  Im Dialog des Stifts ist es ein eigener Abschnitt „Ort“.
9. **Dichter als im Zielbild nötig** (Vorschau: „Die Felder der Suche sind insgesamt sehr weit auseinander“): die Zahl der Zeichen unter ihrem Feld in derselben Zeile wie die Beschriftung des Felds darunter (Runde 3: „sodass sich die zählung und der Titel des darunterliegenden Feldes eine Zeile teilen“), kleinere Abstände.
10. **Ganze Trefferzeile** (Vorschau: „wenn ich auf die Adresszeile klicken kann um die adresse zu übernehmen“): Ein Klick irgendwo in die Zeile übernimmt; mit der Tastatur weiter über „Übernehmen“.

## Kreise

- **Datei:** [`kreise.html`](kreise.html)
- **Stand:** 17.11.2026, Entwurf Fassung 4 aus der Klärung von #141 nach Sebastians Anmerkungen zu den Fassungen 1 bis 3; Sebastian: „Passt. So übernehmen bitte“ ([Kommentar „Zielbild (17.11.2026)“](https://github.com/sebivtt/dpv-participant-management/issues/381#issuecomment-6951024403), Datei unverändert daraus), eingespielt mit #381.
- **Prüfsumme (SHA-256):** `99cc6465246f36f0f433d569d0e600a8ebc790d6d8f36d5559f0fa789cef36c9`
- **Inhalt der Datei:** nur erfundene Personen (Tom, Svea, Wilma, Anton, Finn, Wanda, Otto) mit Mails unter „example.org“. Nichts von fremden Servern; die einzige Adresse ist der Namensraum von SVG. Band, Hinweiskasten und „Zum Ausprobieren“ gehören nicht zur Seite.
- **Orientierung, keine Anforderung.** Geklärt in #381 ([Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/381#issuecomment-6951072934), N1 und N2; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/381#issuecomment-6945396247)). Es zeigt Teil A (#381: Startseite, „Kreise“, Seite eines Kreises, „Kreis anlegen“, „Person einladen“, „Zurücknehmen“) und Teil B (#382: Bearbeiten, Verwalten geben und wegnehmen, Entfernen, Verlassen, Auflösen, Austreten). Der gelb gestrichelte Platz „Öffentliche Kreise“ kommt erst mit #364 (P9).

### Abweichungen vom Zielbild (#381)

1. **„Offene Einladungen“ ohne die graue Zeile „eingeladen von …“** (Sebastian, 27.11.2026, U2: „Ohne die Zeile“): Der Baustein „Person in einer Liste“ hat dafür keinen Platz; die Zeile zeigt Name, Fahrtenname und „Zurücknehmen“.
2. **Beschriftungen wie im Baustein „Textfeld“:** „Name (Pflicht)“ und „Beschreibung“ ohne „(freiwillig)“; die Zahl der Zeichen als „12/60“ rechts unter dem Feld statt „12 von 60 Zeichen“ (vorgelesen wird „12 von 60 Zeichen“).
3. **„Kein Konto gefunden …“ als Warnung** wie im Dialog „Person mit Konto aufnehmen“, statt als Information.
4. **Die Marke „Verwaltend“** im Aussehen der Rollenmarke von „Person in einer Liste“, auch im Baustein „Eintrag zum Öffnen“.
