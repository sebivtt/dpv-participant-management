# Gestaltung des DPV Anmeldetools

Leitlinie für alle Seiten. Abschnitt 1 hält fest, was bei der Klärung von #7 am 21.10.2026 konkret entschieden wurde. Abschnitt 2 ist Sebastians Gestaltungskonzept vom 21.10.2026, unverändert übernommen. Gebaut sind bisher die Grundgestaltung und der Bausteinkatalog (`/bausteine/`, #176). Dashboard, „Veranstaltung anlegen“ und Teilnehmendenverwaltung kommen in eigenen Issues, wenn sie laut `docs/fahrplan.md` dran sind (#28, #29, #30).

Wer eine Seite baut, nimmt die Bausteine aus dem Bausteinkatalog (unten) und die Farben aus `core/static/core/app.css`. Ob und wann vorher ein Zielbild nötig ist: `CLAUDE.md`, „Zielbild vor Gestaltung“ (Entscheidung in `docs/entscheidungen.md`, Eintrag vom 26.10.2026 zu #162); die Zielbilder liegen unter `docs/zielbilder/`.

## Bausteinkatalog (#176, 27.10.2026)

Protokoll und Szenarien in #176, Entscheidung mit Begründung in `docs/entscheidungen.md`, Eintrag vom 27.10.2026 zu #176. Jeder Baustein steht einmal als Vorlagenstück unter `core/templates/core/`, sein Aussehen in `core/static/core/app.css`. Der Katalog unter `/bausteine/` (`core/templates/core/bausteine.html`) zeigt jeden über dasselbe Vorlagenstück wie die echten Seiten, mit erfundenen Daten, je Baustein mit einem Satz zum Zweck, dem Issue, das ihn entschieden hat, und den Seiten, die ihn nutzen. Es gibt ihn nur für Angemeldete auf dem eigenen Rechner und in der Testumgebung; im Betrieb zeigt die Adresse allen „Diese Seite gibt es nicht.“

- **Regel: einbinden, nicht kopieren.** Eine Seite bindet den Baustein ein, statt sein Aussehen nachzubauen. Eingabefelder kommen immer aus einem Baustein (Textfeld, Feld zum Antippen). Zwei Tests in `tests/test_bausteinkatalog.py` werden rot, wenn eine Seite ein eigenes Eingabefeld hat oder ein Vorlagenstück einbindet, das nicht im Katalog steht.
- **Nur Entschiedenes:** ein Baustein, den Sebastian an einem Zielbild (#162) oder in einer Klärung mit `grill-me` ausdrücklich freigegeben hat und den das Issue dazu nennt. Er kommt in den Katalog, sobald Sebastian ihn entschieden hat, spätestens mit seiner ersten Seite. Bis eine Seite ihn einbindet, trägt er den Vermerk „noch auf keiner Seite“.
- **Passt ein vorhandener Baustein nicht genau,** wird er erweitert oder es entsteht ein neuer; das entscheidet Sebastian, nie eine stille Kopie (für die KI: `CLAUDE.md`, „Ablauf je Aufgabe“).
- **Prüfung:** Im Katalog läuft die Prüfung auf Barrierefreiheit am PC und am Handy, am Handy auch mit offenem Menü. Mit der Tastatur geprüft wird ein Baustein auf seiner ersten echten Seite.
- **Überholt:** Die Vorschauen aus #7 (Dashboard, Veranstaltungszeilen, Statuskennzeichen, Schritte von „Veranstaltung anlegen“, Teilnehmendentabelle, Beispiel-Navigation) sind entfallen. Ihre Regeln stehen in Abschnitt 1 als Text und kommen über die Zielbilder von #28, #29 und #30 wieder.
- **Alter Name:** Wo ein Issue „Musterseite“ oder `/muster/` sagt, ist seit #176 der Bausteinkatalog gemeint.

## 1. Festgelegt bei der Klärung von #7

Protokolle in #7. Entscheidungen mit Begründung in `docs/entscheidungen.md`, Eintrag vom 21.10.2026.

- **Grundlage:** Bootstrap 5.3, ohne Build-Schritt, alle Dateien vom eigenen Server. Schrift: die Systemschrift des Geräts.
- **Farben:** DPV-Blau `#1a4b7e` trägt die Gestaltung, dazu Weiß und kühle Grautöne. Eine Akzentfarbe, Sonnengelb `#f0ad2c`, sparsam: aktiver Navigationspunkt, Symbol von „Veranstaltung erstellen“, aktueller Schritt; als Fläche nur für das gestreifte Band der Testumgebung, nie für Meldungen (#165). Sonnengelb trägt nie Text auf Weiß. Statusfarben sind gedeckt und stehen immer mit Wort und Symbol. Alle Farben stehen an einer Stelle; nur heller Modus, ein dunkler ist vorbereitet (#15).
- **Formen:** abgerundete Ecken, Flächen statt Rahmen, kaum Schatten, lieber Luft als Fülle. Einzige Ausnahme mit deutlichem Schatten ist die kurze Meldung (#186), damit man sie ohne Farbe als schwebend erkennt.
- **Aufbau am PC:** feste Seitenleiste links, keine Kopfzeile über dem Inhalt. Oben Lilie und „DPV Anmeldetool“, darunter die Navigation, unten Profilkreis mit Vornamen und „Abmelden“ mit Symbol und Wort. Der Profilkreis führt am PC und am Handy zu „Mein Profil“ und ist dort hervorgehoben wie der aktive Navigationspunkt, mit zarter Fläche und gelbem Ring; einen eigenen Punkt in der Navigation hat „Mein Profil“ nicht (#13).
- **Aufbau am Handy:** schmale Leiste oben mit „Menü“, Lilie mit Namen und Profilkreis. „Menü“ öffnet die Navigation von links; „Abmelden“ steht darin mit Symbol und Wort. Die Leiste wechselt unter 992 Pixel Breite.
- **Navigation:** Auf echten Seiten steht nur, was es gibt, und nur für Personen, die es nutzen dürfen (`core/navigation.py`). Keine leeren Platzhalter. Ausblenden ersetzt nie die Rechteprüfung auf dem Server.
- **Fußbereich:** eine flache Zeile am Ende des Inhalts, links „Impressum“ und „Datenschutz“, rechts „© DPV e.V. · Anmeldetool 2026“; die Jahreszahl zählt weiter.
- **Login- und Fehlerseite:** ruhig und mittig, ohne Seitenleiste.
- **Dashboard (gebaut in #28):** oben die Begrüßung, darunter einige Statusmeldungen, darunter am PC zwei Drittel „Kommende Veranstaltungen“ und ein Drittel „Schnellaktionen“; am Handy untereinander, Schnellaktionen zuerst.
- **Veranstaltungen in Übersichten:** breite, flache Zeilen. Links ein Bild (Ausschnitt aus dem Banner oder eigenes Logo, #31), ohne Bild die Lilie; in der Mitte Name, Zeitraum, Ort, Organisation; rechts Zustand und Anmeldezahl. Mit Obergrenze „23 von 40 angemeldet“ mit Balken, voll zusätzlich „ausgebucht“; ohne Obergrenze nur „23 angemeldet“. Entwürfe gestrichelt umrandet und mit dem Wort „Entwurf“.
- **Zustände (vorläufig, endgültig in #29):** „Entwurf“, „Anmeldung ab 01.12.“, „Anmeldung offen“, „Anmeldung geschlossen“.
- **Menüs:** öffnen am PC beim Darüberfahren und zusätzlich per Klick, Antippen und Tastatur; sie schließen mit kurzer Verzögerung.
- **Sprache:** neutrale Wörter („Teilnehmende“, „Leitung“, „Person“), sonst beide Formen oder umformulieren; kein Sternchen, kein Doppelpunkt. Die Texte duzen.
- **Browser:** die gängigen der letzten rund zwei Jahre: Safari auf iPhone und Mac, Chrome und Samsung Internet auf Android, Chrome, Firefox und Edge am PC.

### Meldungen (Klärung von #165, 26.10.2026)

Protokoll und Zielbild in #165, Zielbild als `docs/zielbilder/meldungen.html`. Entscheidungen mit Begründung in `docs/entscheidungen.md`, Eintrag vom 26.10.2026 zu #165. Jede Meldung im Tool gehört zu genau einer von vier Arten und nutzt deren Baustein (`{% meldung %}` in `core/templatetags/layout.py`, im Bausteinkatalog unter „Meldungen“):

| Art | Wann | Aussehen |
|---|---|---|
| Informationsmeldung | neutraler Hinweis, nichts zu tun | zart blaue Fläche, dunkle Schrift, Symbol „i“; ein passenderes Symbol darf stehen (z. B. Schloss) |
| Warnmeldung | etwas fehlt, die Person muss selbst etwas tun | helles Gelb, Schrift und Symbol in Braun, Warndreieck |
| Fehlermeldung | etwas hat nicht geklappt; nur neu versuchen oder warten | gedecktes Rot, Kreuz |
| Erfolgsmeldung | etwas hat geklappt | gedecktes Grün, Haken |

- **Fehler am Feld** ist keine Meldung dieser Arten: rote Schrift direkt unter dem Feld, mit dem Feld verknüpft (Bausteinkatalog, „Textfeld“).
- **Eine Farbfamilie:** Meldungen und Statuskennzeichen teilen sich die Farben: Warnung wie „Warteliste“, Fehler wie „abgemeldet“, Erfolg wie „angemeldet“. Unterschieden wird über die Form, kleine Pille gegen Fläche mit Satz.
- **Aufbau:** das Symbol in einem hellen Kästchen links, daneben der Text; ein fetter erster Satz steht als eigene Zeile über dem Rest. Mehrere Meldungen stehen getrennt untereinander, am Handy bricht der Text um und das Symbol bleibt links.
- **Ohne Farbe erkennbar:** Jede Art hat ihr eigenes Symbol, und Vorleseprogramme hören vorweg ihr Wort („Information:“, „Warnung:“, „Fehler:“, „Erfolg:“), das unsichtbar bleibt.
- **Ansagen:** Meldungen nach einer Handlung (Login-Seite) sagen Vorleseprogramme sofort an; fest auf einer Seite stehende nicht.
- **Band der Testumgebung** ist keine Meldung: Sonnengelb mit schrägen Streifen wie ein Absperrband und eigenem Laborsymbol.

### Kurze Meldungen und Fehlermeldungen an der Stelle der Handlung (#186, 27.10.2026)

Protokoll, Szenarien und Zielbild in #186, Zielbild als `docs/zielbilder/kurze-meldungen.html`. Entscheidung mit Begründung in `docs/entscheidungen.md`, Eintrag vom 27.10.2026 zu #186. Die kurze Meldung ist ein eigener Baustein (`{% kurzmeldung %}` in `core/templatetags/layout.py`, im Bausteinkatalog unter „Kurze Meldung“); Art, Farbe, Symbol und Aufbau bleiben die der Meldungen oben.

| Form | Wann | Wo und wie |
|---|---|---|
| Kurze Meldung | Erfolg oder Information, die eine eigene Handlung bestätigt (z. B. „Dein Fahrtenname ist gespeichert.“) | unten mittig über dem Inhalt, mit deutlichem Schatten und ×; verschwindet nach rund 6 Sekunden |
| Feste Meldung | ein dauerhafter Zustand (z. B. „Du bist noch keiner Organisation zugeordnet.“); jede Warnung | fest auf der Seite |
| Fehlermeldung nach einer Handlung | etwas hat technisch nicht geklappt | fest, direkt an der Stelle der Handlung: unter dem Feld, auf späteren Seiten unter der betroffenen Zeile |
| Fehler am Feld | die Eingabe ist falsch | rote Schrift direkt unter dem Feld (unverändert, „Textfelder“ unten) |

- **Kurz nur nach einer eigenen Handlung:** Fehler und Warnungen werden nie kurz; bei ihnen muss man etwas tun, und verschwänden sie, übersähe man sie. Die Login-Seite bekommt keine kurzen Meldungen; ihre Meldungen bleiben fest direkt über dem Knopf.
- **Dauer und Bedienung:** rund 6 Sekunden, mit × zum Schließen. Solange die Maus darüber oder der Fokus darin ist, bleiben alle stehen und zählen danach neu. Schließt man sie mit der Tastatur, geht der Fokus dorthin zurück, wo er war, als sie erschien. Kein Zeitbalken.
- **Lage:** am PC unten mittig im Inhaltsbereich, die Seitenleiste bleibt frei, höchstens 560 Pixel breit; am Handy unten über fast die ganze Breite mit etwas Rand. Langer Text bricht um.
- **Mehrere:** stapeln sich, die neueste unten, höchstens drei; bei einer vierten verschwindet die älteste sofort.
- **Vorleseprogramme** sagen sie an („Erfolg:“ bzw. „Information:“ vorweg), ohne dass der Cursor sich bewegt.
- **Bewegung:** sanftes Ein- und Ausblenden; ist im Gerät „Bewegung reduzieren“ eingestellt, ohne Bewegung.
- **Ohne Skript** steht sie fest oben auf der Seite wie eine feste Meldung, bis zum nächsten Seitenwechsel.
- **Fehlermeldung an der Stelle der Handlung:** Der Bildschirm zeigt die Stelle, der Cursor steht im Feld, und Vorleseprogramme sagen sie an. Sie verschwindet erst beim erneuten Versuch oder beim Seitenwechsel. So übersieht man sie auch auf einer langen Seite nicht und wird nicht nach oben geholt.

### Seite „Organisation“ (#189, 28.10.2026)

Zielbild als `docs/zielbilder/organisation.html`, Entscheidungen in `docs/entscheidungen.md`, Eintrag vom 28.10.2026 zu #189. Neue Bausteine im Bausteinkatalog: Gliederung, Marke, Leitung in einer Liste, Kopf einer Organisationsseite; die Rollenkachel kann seitdem anklickbar und „ohne Zugriff“ sein.

- **Aufbau am PC:** links die Gliederung, rechts die Seite der Organisation; die Seite bestimmt die Höhe, die Gliederung ist mindestens 360 Pixel hoch und rollt innen.
- **Am Handy** zuerst nur die Gliederung; die Seite einer Organisation steht allein, mit „‹ Gliederung“ zurück.
- **Marken** sind kleine runde Pillen mit Wort: „Du springst ein“ (gelblich), „nur lesen“ (grau, mit Schloss), „gesperrt“ (rot). Die eigene Rolle bekommt keine Marke.
- **Leitungen** in zwei Zeilen: oben Fahrtenname, Name und „das bist du“, darunter links die Rolle als Rollenmarke, rechts die Mail.

### Textfelder (#111, 26.10.2026)

Jedes Formular bindet seine Textfelder über den gemeinsamen Baustein ein (`{% textfeld form.feld %}` in `core/templatetags/layout.py`, im Bausteinkatalog unter „Textfeld“), statt sein Feld selbst zu schreiben. Entscheidungen mit Begründung in `docs/entscheidungen.md`, Eintrag vom 26.10.2026 zu #111.

- **Beschriftung** über dem Feld, bei Pflichtfeldern mit „(Pflicht)“; freiwillige Felder ohne Zusatz.
- **Fehler am Feld** rot direkt darunter, mit dem Feld verknüpft; die Eingabe bleibt stehen.
- **Passende Handy-Tastatur:** Das Formular legt sie am Feld fest, z. B. bei Namen Großbuchstabe am Wortanfang, ohne Autokorrektur. Jedes neue Feld wird auch wie am Handy geprüft, mit Autokorrektur und Wortvorschlägen (Rauchtest).
- **Weiß** auf grauem oder weißem Grund, damit es sich von gesperrten Feldern (grau, mit Schloss) abhebt.
- Gleiches gilt später für Datumsfelder (#100) und das Adressfeld (#163).

### Felder zum Antippen (#180, 26.10.2026)

Ein einzelnes Feld, das man auf einer Seite mit Angaben ändern kann, ist ein Feld zum Antippen (`{% antippfeld form.feld saved=… icon=… %}` in `core/templatetags/layout.py`, im Bausteinkatalog unter „Feld zum Antippen“). Vorbild ist das Zielbild „Mein Profil“; zuerst genutzt für den Fahrtennamen. Entscheidungen mit Begründung in `docs/entscheidungen.md`, Eintrag vom 26.10.2026 zu #180.

- **In Ruhe** sieht es aus wie die gesperrten Angaben daneben, aber weiß: Beschriftung, Symbol, Wert oder „Noch nicht angegeben“, rechts ein ×-Knopf zum Leeren (ausgegraut, wenn leer).
- **Antippen** öffnet die Eingabe im selben Rahmen, darunter „Verwerfen“ und „Speichern“ in einer kleinen Fläche über dem Inhalt darunter.
- **Speichern** mit dem Knopf oder Enter; **Verwerfen** mit dem Knopf, Esc oder Tippen außerhalb, mit Ansage für Vorleseprogramme. Danach liegt der Fokus wieder auf dem Feld. Der ×-Knopf löscht nie selbst: Er öffnet das Feld leer, gelöscht wird erst mit „Speichern“.
- **Ohne Skript** bleibt ein einfaches Formular mit Eingabe und „Speichern“; die Eingabe ist ein Textfeld wie oben.
- **Kopfzeile** auf „Mein Profil“: der Fahrtenname groß, „(Vorname Nachname)“ kleiner und grauer dahinter.

**Offener Widerspruch:** LIS-01 und das Abschlusskriterium von P5 verlangen, lebensbedrohliche Allergien in der Teilnehmendenliste hervorzuheben. Abschnitt 5 unten sagt, Gesundheitsdaten erscheinen nicht in der allgemeinen Übersicht. Geklärt wird das in #30, bevor die Liste gebaut wird.

## 2. Gestaltungskonzept: DPV Anmeldetool

Von Sebastian am 21.10.2026.

### 1. Gestalterische Grundidee

Das DPV Anmeldetool erhält eine klare, moderne und funktionale Oberfläche. Im Mittelpunkt stehen eine einfache Bedienung, eine gute Übersicht über Veranstaltungen und Anmeldungen sowie kurze, nachvollziehbare Arbeitsabläufe.

Die Gestaltung soll ruhig und aufgeräumt wirken. Informationen werden in klar abgegrenzten Bereichen dargestellt. Wiederkehrende Elemente und ein einheitliches Layout sorgen dafür, dass sich Nutzende schnell orientieren können.

Verbindlich gesetzt sind die DPV-Farbe und das DPV-Logo. Die übrige Gestaltung soll sich daran orientieren, ohne unnötig komplex zu werden.

### 2. Grundlayout und Navigation

#### Desktop

Das Desktop-Layout verwendet eine feste linke Seitenleiste. Es gibt keine zusätzliche, über die gesamte Inhaltsfläche laufende Kopfzeile oder ein separates Banner.

Die Seitenleiste enthält:

- DPV-Logo und Produktbezeichnung „DPV Anmeldetool“ im oberen Bereich
- Hauptnavigation mit den zentralen Bereichen
- Profil- und Kontobereich am unteren Rand
- Abmeldefunktion

Die Navigation soll mindestens folgende Bereiche vorsehen, soweit sie für die jeweilige Rolle verfügbar sind:

- Startseite
- Veranstaltungen
- Teilnehmende
- Organisation
- Einstellungen

Der aktive Navigationspunkt wird deutlich hervorgehoben. Die Seitenleiste bleibt über die verschiedenen Ansichten hinweg konsistent.

Der eigentliche Seiteninhalt beginnt direkt rechts neben der Seitenleiste. Er besitzt eine klare Überschriftenhierarchie und ausreichend Abstand zwischen den einzelnen Bereichen.

#### Smartphone und kleinere Bildschirme

Auf mobilen Geräten wird die feste Seitenleiste durch eine kompakte Navigation ersetzt. Diese bietet einen Menüzugang, die Produktidentität und den Profilzugang.

Listen und Tabellen werden für kleine Bildschirme angepasst. Insbesondere die Teilnehmendenverwaltung soll auf Smartphones mit kompakten Karten anstelle einer breiten Tabelle funktionieren.

### 3. Startseite / Dashboard

Das Dashboard ist der zentrale Einstiegspunkt nach der Anmeldung. Es soll die wichtigsten Aufgaben zugänglich machen, ohne eine überladene Übersichtsseite zu erzeugen.

#### Begrüßung und Einstieg

Im oberen Bereich des Inhalts erscheint eine kurze Begrüßung mit einem knappen Hinweis auf die wichtigsten Informationen. Eine zusätzliche globale Kopfzeile ist nicht vorgesehen.

#### Kommende Veranstaltungen

Der Bereich „Kommende Veranstaltungen“ ist ein zentrales Element des Dashboards.

Veranstaltungen werden in übersichtlichen Karten dargestellt. Diese können abhängig von den verfügbaren Daten enthalten:

- Veranstaltungsname
- Zeitraum
- Veranstaltungsort
- Organisationszuordnung
- Anmeldestatus bzw. Veröffentlichungsstatus
- Anzahl der angemeldeten Personen und gegebenenfalls die verfügbare Kapazität
- Direkten Zugang zur jeweiligen Veranstaltungsansicht

Entwürfe und veröffentlichte Veranstaltungen müssen klar voneinander unterscheidbar sein. Die Darstellung soll sich auf die Informationen konzentrieren, die für die schnelle Orientierung tatsächlich relevant sind.

#### Schnellaktionen

Der Bereich „Schnellaktionen“ ermöglicht den direkten Zugriff auf häufig benötigte Funktionen.

Dazu gehören insbesondere:

- Veranstaltung erstellen
- Eigene Anmeldungen aufrufen
- Veranstaltungen verwalten
- Organisationsbereich öffnen

Die verfügbaren Aktionen können abhängig von Rolle und Berechtigungen variieren. Die Aktion „Veranstaltung erstellen“ soll besonders gut auffindbar sein.

#### Schrittweise erweiterbare Informationsbereiche

Zusätzliche Übersichtsbereiche oder Kennzahlen sind optional. Sie sollen nicht allein deshalb dauerhaft vorgesehen werden, weil sie gestalterisch möglich sind.

Stattdessen soll das Dashboard modular aufgebaut sein: Wenn ein neues fachliches Modul hinzukommt, kann es einen passenden Übersichtsbereich, eine Schnellaktion oder einen direkten Verweis auf die entsprechende Funktion erhalten.

So wächst das Dashboard mit dem Funktionsumfang des Anmeldetools. Nicht verfügbare oder für eine Person irrelevante Bereiche werden nicht als leere Platzhalter angezeigt.

### 4. Veranstaltung anlegen

Das Anlegen einer Veranstaltung soll als klar geführter, mehrstufiger Ablauf gestaltet werden.

Die einzelnen Schritte werden durch eine Fortschrittsanzeige kenntlich gemacht. Als Grundstruktur bietet sich an:

1. Grunddaten
2. Anmeldung und weitere Einstellungen
3. Zusammenfassung und Veröffentlichung

Die konkreten Felder richten sich nach den fachlichen Anforderungen. Grunddaten umfassen insbesondere den Veranstaltungstitel, die organisatorische Zuordnung, Zeitraum, Ort und Beschreibung.

#### Bedienung und Navigation

- Die primäre Aktion „Weiter“ führt zum nächsten Schritt.
- Ab dem zweiten Schritt wird eine Zurück-Funktion angeboten, über die vorherige Eingaben erneut bearbeitet werden können.
- Abbrechen und Weiter sollen klar unterscheidbar sein.
- Eingaben dürfen beim Wechsel zwischen den Schritten nicht unbeabsichtigt verloren gehen.
- Fehler werden verständlich und möglichst direkt am betroffenen Feld angezeigt.
- Pflichtfelder werden eindeutig gekennzeichnet.

Vor einer Veröffentlichung soll eine Zusammenfassung der eingegebenen Daten möglich sein. Das Speichern eines Entwurfs und das Veröffentlichen einer Veranstaltung müssen klar voneinander getrennt sein.

### 5. Teilnehmendenverwaltung

Die Teilnehmendenverwaltung soll die effiziente Bearbeitung von Anmeldungen ermöglichen.

#### Übersicht

Die Übersicht enthält insbesondere:

- Auswahl der Veranstaltung
- Suche nach Namen
- Filtermöglichkeiten, beispielsweise nach Status oder Gruppe
- Eine übersichtliche Liste der Teilnehmenden
- Statuskennzeichnungen, etwa angemeldet, Warteliste oder abgemeldet
- Pagination oder eine vergleichbare Lösung bei größeren Listen

Auf dem Desktop kann eine tabellarische Darstellung verwendet werden. Auf mobilen Geräten werden die Informationen in kompakte Karten überführt.

#### Detailansicht

Die Auswahl einer Person öffnet eine Detailansicht mit den für die jeweilige Rolle zugänglichen Informationen. Die Darstellung soll klar zwischen allgemeinen Anmeldedaten und besonders schützenswerten Angaben unterscheiden.

Gesundheitsdaten und andere besonders sensible Angaben dürfen nicht in der allgemeinen Teilnehmendenübersicht erscheinen. Der Zugriff auf solche Daten muss auf berechtigte Veranstaltungsleitungen beschränkt sein und serverseitig geprüft werden.

Aktionen wie Statusänderungen oder Nachrichtenversand sollen nur dort angeboten werden, wo sie fachlich vorgesehen und durch die jeweilige Berechtigung erlaubt sind.

### 6. Visuelle Gestaltung

#### Farben und Kontraste

- DPV-Blau als zentrale Markenfarbe
- Weiß und dezente Grautöne für Hintergründe, Flächen und Trennlinien
- Statusfarben als ergänzende Orientierung, nicht als alleinige Informationsquelle
- Ausreichender Kontrast für Texte, Bedienelemente und Fokusmarkierungen

#### Karten und Inhaltsbereiche

Karten dienen der Gruppierung zusammengehöriger Informationen, beispielsweise bei Veranstaltungen, Schnellaktionen und Teilnehmenden.

Sie sollen einheitlich gestaltet sein und nicht unnötig viele Rahmen, Schatten oder dekorative Elemente verwenden. Die visuelle Hierarchie entsteht vor allem durch Abstände, Typografie, Ausrichtung und gezielte Hervorhebungen.

#### Typografie und Symbole

Überschriften, Beschreibungstexte, Statusinformationen und Aktionen müssen klar unterscheidbar sein. Symbole unterstützen die Orientierung, ersetzen jedoch keine verständlichen Beschriftungen, wenn deren Bedeutung nicht eindeutig ist.

### 7. Barrierefreiheit und Bedienbarkeit

Die Gestaltung berücksichtigt insbesondere:

- vollständige Bedienbarkeit per Tastatur
- gut sichtbare Fokuszustände
- verständlich beschriftete Formulare und Bedienelemente
- nachvollziehbare Fehlermeldungen
- ausreichende Kontraste und gut lesbare Schriftgrößen
- verständliche, inklusive Sprache
- responsives Verhalten auf Desktop, Tablet und Smartphone

Die Oberfläche soll auch ohne ausschließlich farbliche Hinweise verständlich bleiben.

### 8. Technische Leitlinien

Die Gestaltung soll zur vorgesehenen Architektur mit Django-Templates und htmx passen. Serverseitig gerenderte Seiten bilden die Grundlage; dynamische Interaktionen werden dort ergänzt, wo sie einen konkreten Bedienungsvorteil bieten.

Berechtigungen werden serverseitig geprüft und nicht allein durch das Ausblenden von Navigationselementen oder Aktionen abgesichert.

Die Umsetzung soll möglichst einfach, wartbar und modular bleiben. Neue fachliche Funktionen sollen sich in die bestehende Navigation und das Dashboard integrieren lassen, ohne das gesamte Layout neu gestalten zu müssen.

### 9. Zielbild

Das Ergebnis soll ein ruhiges, modernes und funktionales Anmeldetool sein, das die Veranstaltungsverwaltung in den Mittelpunkt stellt.

Besonders wichtig sind:

- eine feste linke Desktop-Seitenleiste ohne zusätzliches Banner
- eine kompakte mobile Navigation
- ein Dashboard mit „Kommende Veranstaltungen“ und „Schnellaktionen“ als zentralen Elementen
- ein geführtes Veranstaltungsformular mit Vor- und Zurücknavigation
- eine übersichtliche, responsive Teilnehmendenverwaltung
- modular erweiterbare Übersichtsbereiche
- konsequente Beachtung von Barrierefreiheit, Rollen und Datenschutz

Das Konzept beschreibt die gewünschte Gestaltung und Bedienung. Die konkrete Umsetzung soll sich an den fachlichen Anforderungen und dem schrittweisen Ausbau der Anwendung orientieren.
