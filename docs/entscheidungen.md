# Entscheidungen

Fachliche und technische Entscheidungen mit Begründung. Neue Einträge oben. Wer eine Regel ändern will, ergänzt einen neuen Eintrag, statt einen alten zu überschreiben.

Format: Datum · Entscheidung · Begründung · Umsetzung

---

## 2026-11-02 · Sperren für die KI, Freigaben gibt Sebastian selbst (#233)

**Entscheidung** (Paket P-01 der Projektprüfung, Issue #233):

1. Nur Sebastian setzt das Label `geklärt` und übernimmt Pull Requests, jeweils selbst auf GitHub. Die KI bittet ihn darum und schickt den Link. Das löst in `grill-me` den Handgriff ab, mit dem die KI das Label nach seinem Okay selbst setzte.
2. In Claude Code sind gesperrt, auch im Auto-Modus: Pull Request übernehmen (auch über `gh api` und GraphQL), auf `main` hochladen, Hochladen mit Force, `--all`, `--mirror` oder Löschen, Hochladen ohne ausdrückliches Ziel, `.env` lesen, `geklärt` setzen (beim Anlegen und Bearbeiten, auch über `gh api`). Den eigenen Zweig hochladen, Pull Requests und Issues anlegen, andere Labels setzen, `geklärt` entfernen und lesende `gh`-Befehle gehen weiter.

**Begründung:** Diese Grenzen standen nur als Text in `CLAUDE.md`. Im Probelauf ohne Sperrliste (Claude Code 2.1.309, Auto-Modus, erfundener Inhalt) lud die KI auf `main` hoch, übernahm einen Pull Request und las `.env`. Mit Sperrliste und Prüfschritt wurden alle geprüften Sperrfälle abgewiesen, gestartet im Projektordner und in einer frischen Arbeitskopie; die Gegenfälle liefen.

**Grenzen:**

- Startet Claude Code in einem Unterordner des Projekts, wirkt keine Sperre: Claude Code 2.1.309 liest `.claude/settings.json` nur aus dem Ordner, in dem die Sitzung startet (Probe vom 02.11.2026). Die Desktop-App startet im Projektordner bzw. in Arbeitskopien; dort ist die Sperre belegt wirksam.
- Ältere Arbeitskopien, deren Zweig die beiden Dateien noch nicht hat, haben keine Sperre, bis ihr Zweig `main` aufnimmt.
- Die Sperre gilt nur in Claude Code; andere KI-Werkzeuge haben keine und arbeiten im Projekt nur lesend.
- Schutz vor Versehen und Gewohnheit, nicht vor Absicht: Absichtlich verschleierte Befehle (Skript, Variable) kommen durch.
- Mensch und KI teilen ein GitHub-Konto; wer geklickt hat, lässt sich technisch nicht nachweisen.
- Fehlt die Datei des Prüfschritts, weist Claude Code jeden Bash-Befehl ab (Probe), bis sie wieder da ist.

**Technische Wahl** (KI): Zwei Teile, weil die Sperrliste von Claude Code nur nach dem Anfang eines Befehls unterscheidet. `.claude/settings.json` sperrt `Read` auf `.env` und `gh pr merge`; der Prüfschritt `.claude/hooks/sperren.py` (Hook `PreToolUse`, nur Python-Standardbibliothek) zerlegt jeden Bash-Befehl in seine Teile und prüft je Teil die Wirkung, etwa das tatsächliche Ziel eines `git push`. Was er nicht sicher zerlegen kann und `git`, `gh` oder `.env` enthält, weist er ab, ebenso jeden Befehl bei einem eigenen Fehler.

**Umsetzung:** `.claude/settings.json`, `.claude/hooks/sperren.py`, `CLAUDE.md`, `.claude/skills/grill-me/SKILL.md`, `tests/test_sperren.py`, `tests/test_arbeitsregeln.py`.

## 2026-10-31 · Zahl der Zeichen unter Feldern mit fachlicher Grenze (#215)

**Entscheidung** (Sebastian, [Klärung vom 30.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/215#issuecomment-6524812413), Fragen 1 bis 4; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/215#issuecomment-6524812974) mit „Ja, so (Empfehlung)“):

1. Ein Feld mit fachlicher Grenze zeigt beim Tippen rechts unter der Eingabe die Zahl der Zeichen, etwa „12/30“, auch leer („0/30“); in Ruhe keine Zahl.
2. Ist der Text zu lang, wird die Zahl rot, und sofort steht darunter die Meldung, die auch beim Speichern käme. Nichts wird abgeschnitten; „Speichern“ und Enter bleiben möglich, und der Server prüft wie bisher. Der Eintrag vom 26.10.2026 zu #111 (kein `maxlength`) bleibt.
3. **Nur bei fachlicher Grenze:** heute nur der Fahrtenname, nicht das Suchfeld beim Benennen (254 Zeichen sind dort nur technischer Schutz). Jedes neue Feld legt beim Klären fest, ob es eine fachliche Grenze hat.

**Begründung:** Wer einen zu langen Fahrtennamen tippte, erfuhr es erst beim Speichern (gemeldet am 29.10.2026). Eine harte Sperre schnitte beim Einfügen und bei Wortvorschlägen am Handy still ab.

**Technische Wahl** (KI): Die Grenze und die Meldung legt das Formular am Feld fest (`data-hoechstens`, `data-zu-lang`), wie die passende Handy-Tastatur; beide Bausteine (Textfeld, Feld zum Antippen) zeigen dann die Zahl. Gezählt wird genau wie auf dem Server: ohne Leerzeichen am Rand, auch unsichtbare (`trimmed()`, #77), je Unicode-Zeichen; ein Emoji zählt eins, ein zerlegt geschriebener Umlaut zwei, wie in Prüfung und Datenbank (Hinweis aus #214). Vorleseprogramme hören die Zahl als „12 von 30 Zeichen“ beim Betreten der Eingabe, nicht bei jedem Tastendruck; die Meldung „zu lang“ einmal, wenn sie erscheint. Ohne Skript keine Zahl.

**Umsetzung:** `accounts/forms.py`, `core/templatetags/layout.py`, `core/templates/core/_textfeld.html`, `core/templates/core/_antippfeld.html`, `core/static/core/app.js`, `core/static/core/app.css`, `core/views.py` (Bausteinkatalog), `tests/test_zeichenzahl.py`, `rauchtests/test_zeichenzahl.py`.

## 2026-10-31 · Fahrtenname höchstens 30 Zeichen, langer Name bricht im Profilkreis um (#214)

**Entscheidung** (Sebastian, [Klärung vom 30.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/214#issuecomment-6524812008), Fragen 5, 6b und 7; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/214#issuecomment-6524812677) mit „Ja, so (Empfehlung)“):

1. Ein Fahrtenname hat höchstens **30 Zeichen**, überall, auch bei verwalteten Personen (#117). Das löst „höchstens 50 Zeichen“ in Punkt 5 des Eintrags vom 26.10.2026 zu #111 ab; Leerzeichen am Rand, Meldungen und Fehler am Feld bleiben, wie dort entschieden.
2. Gespeicherte Fahrtennamen über 30 Zeichen werden beim Umstellen geleert; danach steht „Noch nicht angegeben“. Bei der Umstellung gab es sie nur in Testkonten.
3. Im Profilkreis in der Seitenleiste und im Menü am Handy bricht ein langer Name um, notfalls mitten im Wort, statt über den Rand zu ragen.

**Begründung:** Ein langer Name ohne Leerzeichen ragte in der Seitenleiste über den Rand (gemeldet am 29.10.2026). Sebastian: „Ich würde sowohl Umbrechen als auch eine engere Grenze verwenden. Die neue Grenze soll 30 Zeichen sein.“ Zum Leeren: Gespeicherte längere Namen gab es nur in Testkonten.

**Technische Wahl** (KI): Die Grenze steht an einer Stelle im Code (`SCOUT_NAME_MAX_LENGTH`) und gilt zusätzlich in der Datenbank, damit auch ein späterer Weg am Formular vorbei keinen längeren Namen speichern kann (Klärung, Frage 6). Weiter kein `maxlength` im Feld (Eintrag vom 26.10.2026 zu #111).

**Umsetzung:** `accounts/models.py`, `accounts/migrations/0005_scout_name_30.py`, `accounts/texts.py`, `core/templates/core/_profilkreis.html`, `core/static/core/app.css`, `tests/test_fahrtenname_grenze.py`, `rauchtests/test_fahrtenname_umbruch.py`.

## 2026-10-30 · Rollenkacheln auf „Mein Profil“ ohne zweite Zeile (#219)

**Entscheidung** (Sebastian, [Klärung vom 30.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/219#issuecomment-6521672121), Frage 4 mit Nachfrage; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/219#issuecomment-6521672415) mit „Alles passt“):

1. Keine Rollenkachel auf „Mein Profil“ zeigt eine zweite Zeile: weder die festen Sätze unter Verbandsleitung, DPV-Veranstaltungsteam und Admin („Leitung des Verbands“, „Veranstaltungen des Verbands“, „Verwaltung des ganzen Tools“) noch den Weg nach oben unter Gruppen-, Stammes- und Ringleitung. Das hebt diese Teile von Punkt 3 im Eintrag zu #161 (25.10.2026, Nachklärung Kacheln) auf.
2. Die Mitgliedschaft behält ihren Weg nach oben (ORG-05), weil Gruppennamen mehrfach vorkommen.
3. Unverändert bleiben: „Rolle abgeben“ in der Kachel des DPV-Veranstaltungsteams, groß „DPV Anmeldetool“ bei Admin und die Kacheln unter „Organisationen darunter“ mit ihrer Zeile „Gruppenleitung: …“ und ihren Marken (#189).

**Begründung:** Sebastian sah beim Test von #94 Kacheln in unterschiedlichem Stil (Verbandsleitung mit Zeile, Bundesleitung ohne) und hält die Zeilen nicht für nötig. Einheitlich wird es nur ohne Zeile: Mit dem Verband im Weg hätten Verbandsrollen und Admin weiter keine Zeile, weil über dem Verband nichts liegt.

**Umsetzung:** `core/views.py` (`_tile()`, Bausteinkatalog), `core/templates/core/_rollenkachel.html`, `tests/test_mein_profil.py`.

## 2026-10-30 · Verbandsleitung: zurück zur Seite „Verband“, ohne Marke am eigenen Bund (#218)

**Entscheidung** (Sebastian, [Klärung vom 30.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/218#issuecomment-6521671528) mit „Alles passt“; [Nachklärung M1, M2](https://github.com/sebivtt/dpv-participant-management/issues/218#issuecomment-6523317158) je mit „Passt“):

1. Für die Verbandsleitung steht im Pfad jeder Organisationsseite der Name des Verbands als erste Ebene und führt zur Seite „Verband“; am Handy heißt der Knopf oben „‹ Verband“.
2. Auf der Seite „Verband“ trägt der eigene Bund keine Marke „Deine Rolle: Bundesleitung“ mehr, wie sonst überall auf der Seite „Organisation“ (28.10.2026, #189, Punkt 4); er bleibt anklickbar. Das ändert Punkt 1 und Punkt 4 des Eintrags zu #94 unten: Die Überschrift einer Fläche behält den Titel als Link, die Marke dahinter und die Art „Deine Rolle: Bundesleitung“ entfallen.

**Umsetzung:** `units/organisation.py` (`Organisation.page()`, `Federation.associations()`), `units/texts.py`, `core/views.py` (Bausteinkatalog), `core/templates/core/_orgakopf.html`, `_flaechenkopf.html`, `_kennmarke.html`, `organisation.html`, `verband.html`, `bausteine.html`, `core/static/core/app.css`, `tests/test_verband.py`, `rauchtests/test_verband.py`.

## 2026-10-30 · Verbandsleitung: Seite „Verband“, Rollen vergeben ohne Personendaten (#94)

**Entscheidung** (Sebastian, [Klärung vom 28.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6466398212), Fragen 1 bis 5, bestätigt mit „Die Entscheidungen passen so.“; [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6475718734) mit „Alle passen“):

1. **Seite „Verband“:** „Organisation“ öffnet für die Verbandsleitung eine Seite mit den Abschnitten Verbandsleitung, DPV-Veranstaltungsteam und Bünde; dort benennt und entfernt sie. Einen Bund öffnet sie nicht, außer sie ist dort Bundesleitung; dann ist genau dieser Bund anklickbar, mit der Marke „Deine Rolle: Bundesleitung“.
2. **Dialog „Benennen“** nur mit „Mail oder Benutzername“, ohne Vorschläge; beim eigenen Treffer „Dir selbst kannst du keine Rolle geben. Das kann eine andere Verbandsleitung.“
3. **Ergänzung von W1:** Auf „Mein Profil“ steht bei der Rolle „DPV-Veranstaltungsteam“ der Knopf „Rolle abgeben“ (Frage 5). Das ist nach dem Fahrtennamen (#111) und „Austreten“ (#65) das dritte Bedienelement dort.

Bei der Umsetzung am 30.10.2026 ([Baustein](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6517597164), [F2 bis F4](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6517616211)):

4. **Baustein erweitern** (Antwort „A: erweitern“): Die „Überschrift einer Fläche“ darf einen Link als Titel und eine Marke dahinter haben; die „Marke“ bekommt die Art „Deine Rolle: Bundesleitung“ in Blau.
   Ebenso die „Rollenkachel“ ([F5](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6518007445), Variante A): Unten darf ein kleiner neutraler Knopf „Rolle abgeben“ stehen, etwa beim DPV-Veranstaltungsteam auf „Mein Profil“.
5. **Zugleich Leitung unterhalb des Bundes** (F2, „Boreas anklickbar“): Ist die Verbandsleitung Leitung einer Einheit in einem Bund, ohne Bundesleitung zu sein, ist dieser Bund ebenfalls anklickbar, ohne Marke, und führt zur Gliederung, wo er nur lesend ist.
6. **Gesperrte Konten** (F3, „Passt so“): Gesperrte Bundesleitungen, Verbandsleitungen und Teammitglieder stehen auf der Seite „Verband“ mit der Marke „gesperrt“ und dem Knopf „Entfernen“; ein Bund, dessen einzige Bundesleitung gesperrt ist, zeigt „… hat keine Bundesleitung.“
7. **Wortlaute** (F4, „Passen so“): „Verbandsleitung benennen“, „Teammitglied benennen“, „Otto ist jetzt im DPV-Veranstaltungsteam.“, „Tom aus dem DPV-Veranstaltungsteam entfernen?“, „Deine Rolle als Verbandsleitung abgeben?“ und die übrigen aus der Frage; beim Abgeben der Verbandsleitung entfällt der Satz über den Zugriff auf Personen.
8. **Nach dem lokalen Test** ([Anmerkungen vom 30.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6520805547), „Ja, so machen“): Auf der Seite „Verband“ fällt die Zeile mit dem Namen des Verbands weg. Der Abschnitt heißt „DPV-Verbandsleitung“, nur als Überschrift; die Rolle heißt weiter Verbandsleitung. „Bünde“ ist so groß wie „Verband“, weil beide gleichrangige Teile der Seite überschreiben (Sebastians Wahl „Beide wie „Verband“ jetzt“ am selben Tag).

**Technische Wahl** (KI):

- **Befehl auf dem Server** `python manage.py federation_lead grant|revoke BENUTZERNAME`, gebaut wie der Befehl für Admins (#89); er braucht den Verband (`federation create`).
- **Eigene Adressen unter `/organisation/verband/`** für die Dialoge (Benennen je Rolle im Verband, Bundesleitung je Bund, Entfernen über die Kennung der Rolle), weil die Verbandsleitung die Seite eines Bundes nicht öffnet. Rolle und Organisation kommen aus der Adresse, nie aus dem Formular. „Rolle abgeben“ des Teams hat die Adresse `/profil/team-abgeben/` ohne Kennung: Jede Person hat höchstens eine Rolle im Team.
- **Wer schon woanders Mitglied ist, behält im Treffer den Knopf „Benennen“** (V5): Ob die Rolle Bundesleitung auf ihrem Pfad liegt, sagt erst das Benennen, mit dem Satz aus BV1 ohne Organisation (VV3). Eine Warnung vorab verriete, dass die Person nicht in diesem Bund ist (PK-16).

**Umsetzung:** `access/rights.py` (`is_federation_lead()`, `sees_menu()`, `appoint_in_federation()`, `remove_in_federation()`, `leave_team()`), `units/organisation.py` (`Federation`), `core/views.py`, `core/templates/core/verband.html`, `roles/management/commands/federation_lead.py`, `tests/test_verband.py`.

## 2026-10-28 · Leitung entfernen und eigene Rolle abgeben (#191)

**Entscheidung** (Sebastian, Klärung in #93 und [Szenarien Teil 3](https://github.com/sebivtt/dpv-participant-management/issues/191) mit „Alle passen“; bei der Umsetzung am 28.10.2026 [drei Antworten](https://github.com/sebivtt/dpv-participant-management/issues/191#issuecomment-6476276104)):

1. **Bausteine erweitern** (Antwort „Erweitern (Empfehlung)“): „Leitung in einer Liste“ bekommt rechts einen kleinen Knopf, „Entfernen“ und beim eigenen Eintrag „Rolle abgeben“ neutral; der „Dialog“ bekommt unten neben „Abbrechen“ einen roten Knopf zum Bestätigen.
2. **Wenn niemand einspringt** (Antwort „Kurz (Empfehlung)“): Für eine Gruppe, einen Stamm oder Ring ohne Leitung darüber bis zum Bund heißt es „Danach hat Walhall keine Stammesleitung mehr, und niemand springt ein. Trotzdem abgeben?“. Den Satz „… kann nur die Verbandsleitung benennen“ gibt es nur beim Bund, weil die Verbandsleitung keine Stammesleitungen benennt (RO-17).
3. **Die Erfolgsmeldung ist eine kurze Meldung** (Antwort „Wie beim Benennen (Empfehlung)“), wie nach dem Benennen; „oben“ in C13 ist damit überholt.
4. **Aussehen von „Entfernen“** ([neuer Inhalt vom 28.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/191), aus der Klärung von #65, Sebastian: „Ja, auch in #191“): zarte rote Fläche mit roter Schrift in den Farben der Fehlermeldung, abweichend vom Zielbild zu #93 (nur rote Schrift). Der Knopf ist ein eigener Baustein im Katalog; #65 bindet ihn für „Austragen“ ein.

**Technische Wahl** (KI):

- **Jede Rolle hat eine zufällige Kennung** (`roles.Role.key`, Migration in drei Schritten wie bei den Einheiten); die Bestätigung hat die Adresse `/organisation/<kennung der Organisation>/entfernen/<kennung der Rolle>/`. Lesend zeigt sie den Dialog, das Formular entfernt. Eine Rolle einer anderen Organisation, eine Mitgliedschaft, Verbandsleitung, DPV-Veranstaltungsteam und Admin sind dort „nicht gefunden“.
- **Wer entfernen darf, ist genau, wer dort benennen darf** (`Rights.may_remove()`, der eigene Bereich); die eigene Leitungsrolle liegt immer darin und heißt dort „Rolle abgeben“.
- **Gleichzeitige Anfragen:** Entfernen sperrt das eigene Konto und das der Person mit der Rolle, nach Nummer geordnet, und prüft das Recht unter der Sperre noch einmal. Benennen sperrt seit #191 ebenso das eigene Konto mit (Hinweis aus der Prüfung von #190): Wer gerade entfernt wird, benennt und entfernt danach niemanden mehr.
- **Wohin es danach geht:** zur Seite der Organisation, wenn sie sich noch öffnet; sonst zur Übersicht „Organisation“; ohne Leitungsrolle zu „Mein Profil“, wo die kurze Meldung steht. Der nächste Klick auf „Organisation“ zeigt dann „kein Zugriff“ (AV9).
- **Wer einspringt,** heißt im Satz wie in den Szenarien „Stamm Walhall“ und „Ring Küste“; ein Bund steht nur mit seinem Namen da („Pfadfinderbund Boreas“, C5).

**Begründung:** Dieselbe Prüfung für Benennen und Entfernen hält beide gleich; die Sperre beider Konten verhindert, dass sich zwei Leitungen gleichzeitig gegenseitig entfernen (CV5).

**Umsetzung:** `access/rights.py`, `roles/models.py` mit Migration, `units/organisation.py`, `units/texts.py`, `core/views.py`, `config/urls.py`, `core/templates/core/organisation.html`, `_leitung.html`, `_knopf_entfernen.html`, `_dialog_auf.html`, `_dialog_zu.html`, `bausteine.html`, `core/static/core/app.css`, `docs/rechtematrix.md`, `docs/gestaltung.md`; Tests in `tests/test_entfernen.py` und `rauchtests/test_entfernen.py`.

## 2026-10-28 · Leitung benennen auf der Seite einer Organisation; Kontosuche (F2) (#190)

**Entscheidung** (Sebastian, Klärung in #93: [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/93#issuecomment-6436014693), [Nachtrag](https://github.com/sebivtt/dpv-participant-management/issues/93#issuecomment-6437451814), [Nachklärung zum Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/93#issuecomment-6440955193), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/190#issuecomment-6441094377); bei der Umsetzung am 28.10.2026 [drei Antworten](https://github.com/sebivtt/dpv-participant-management/issues/190#issuecomment-6468685698)):

1. **Kontosuche (F2 aus der Bestandsaufnahme in #106), soweit nicht schon im Eintrag vom 24.10.2026 zu #136, Nr. 6:** Im Dialog „… benennen“ schlägt das Tool beim Tippen ab 3 Zeichen höchstens 10 Personen mit Konto aus dem eigenen Bereich vor, mit Name, Fahrtenname und Organisation; gesperrte Konten erscheinen nicht, und Vorschläge zählen nicht als Suche. Alle anderen findet „Suchen“ über die genaue Mail oder den genauen Benutzernamen, ohne Groß- und Kleinschreibung, nur Konten, die sich schon einmal angemeldet haben. Der Treffer nennt außerhalb des eigenen Bereichs nie die Organisation, nur „schon woanders Mitglied“. Einladungslinks waren erwogen und sind nicht gewählt.
2. **Suchlimit** (Frage D): höchstens 20 Suchen je Person in den letzten 60 Minuten; Suchen ohne Treffer zählen, abgewiesene nicht. Die Meldung nennt die Minuten bis zur nächsten Suche, aufgerundet und mindestens 1 (PK-24 mit neuem Wortlaut).
3. **Benennen** gilt sofort, ohne Zustimmung und ohne Nachricht; wer noch nirgends Mitglied ist, wird Mitglied der geleiteten Organisation. Zustimmung ist vorgemerkt (#187), Benachrichtigungen kommen mit #188.
4. **Neue Bausteine nach dem Zielbild** (Antwort „Wie Zielbild bauen (Empfehlung)“): Dialog und Trefferliste neu; das Textfeld wird als Suchfeld um den Knopf daneben und einen Satz darunter erweitert, die Überschrift einer Fläche um einen Knopf rechts.
5. **Die Erfolgsmeldung ist eine kurze Meldung** (Antwort „Kurze Meldung (Empfehlung)“), wie nach dem Speichern des Fahrtennamens (#186); „oben“ im Akzeptanzkriterium ist damit überholt.
6. **Wortlaut, wenn die Rolle nicht auf dem Leitungspfad läge** (Antwort „Wie im Issue-Beispiel (Empfehlung)“): „Flink (Finn Muster) ist Mitglied in Sippe Falken und kann deshalb keine Leitung bei Stamm Zugvögel sein.“

**Technische Wahl** (KI):

- **Der Dialog hat eine eigene Adresse** (`/organisation/<kennung>/benennen/`, dazu `…/suchen/` und `…/vorschlaege/`). Er kommt offen vom Server, „Suchen“ und „Benennen“ sind gewöhnliche Formulare; so geht alles außer den Vorschlägen beim Tippen auch ohne Skript. Mit Skript wird er modal (`showModal`), Escape und Tippen daneben führen zurück. Kein htmx, kein neues Paket: Die Vorschläge holt ein kurzes Stück in `core/static/core/app.js`, als Formular (POST) mit Formularschutz, damit ein getippter Name nie in einer Adresse und damit in keinem Protokoll eines Webservers steht (unabhängige Prüfung).
- **Alle Rechte und Personendaten aus der zentralen Prüfung:** `Rights.may_appoint()` (der eigene Bereich), `suggestions()`, `find_accounts()`, `count_search()` und `appoint()`. Wer in der Einheit nicht benennen darf, bekommt auf allen drei Adressen „nicht gefunden“, auch per htmx und mit Formular. Die Person kommt im Formular nur mit ihrer Kennung; die Organisation immer aus der Adresse.
- **Reihenfolge der Ablehnungen:** sich selbst (RO-12), schon Leitung dort, woanders Mitglied außerhalb des eigenen Bereichs (ohne die Organisation zu nennen), dann die Regeln aus #89 beim Speichern der Rolle.
- **Gleichzeitige Anfragen:** Benennen und Zählen sperren das betroffene Konto bis zum Ende der Transaktion; zwei gleichzeitige Benennungen ergeben eine Rolle und einen Eintrag im Protokoll, die 20. und 21. Suche nur eine gezählte.
- **Neue Tabelle `accounts.AccountSearch`:** nur wer und wann, nie wonach, weil der Suchbegriff eine Mail oder ein Benutzername einer anderen Person wäre. Einträge, die älter als 60 Minuten sind, löscht die nächste Suche, egal von wem.
- **„1 Minute“ statt „1 Minuten“** in der Meldung zum Suchlimit, damit der Satz stimmt.

**Begründung:** Eine Adresse je Dialog hält ihn ohne Skript benutzbar und lässt die Rundumtests ihn wie jede Seite prüfen; die Rechte an einer Stelle, damit Entfernen (#191) und die Seite der Verbandsleitung (#94) dieselben Bausteine nutzen.

**Umsetzung:** `access/rights.py`, `accounts/models.py` mit Migration, `roles/models.py` (`LEAD_ROLE`), `units/organisation.py`, `units/texts.py`, `core/views.py`, `core/forms.py`, `core/templatetags/layout.py`, `config/urls.py`, `core/templates/core/organisation.html`, `_dialog_auf.html`, `_dialog_zu.html`, `_treffer.html`, `_textfeld.html`, `_flaechenkopf.html`, `_symbole.svg`, `bausteine.html`, `core/static/core/app.css`, `app.js`, `docs/rechtematrix.md`, `docs/gestaltung.md`, `docs/zielbilder/README.md`; Tests in `tests/test_benennen.py` und `rauchtests/test_benennen.py`.

## 2026-10-28 · Seite „Organisation“: Gliederung und Seite je Organisation, nur Anzeige (#189)

**Entscheidung** (Sebastian, Klärung in #93 und #189: [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441094033), [Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441100484), [Nachklärung](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441101266); bei der Umsetzung am 28.10.2026 [Bausteine und Anmerkungen zum Vorschlag](https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6464928798)):

1. **„Organisationen darunter“** nutzt die Rollenkachel von „Mein Profil“, erweitert um „anklickbar“ und „ohne Zugriff grau“ (Antwort „Rollenkachel erweitern (Empfehlung)“).
2. **Die Rolle hinter jeder Leitung** ist die Rollenmarke von „Mein Profil“ (Antwort „Rollenmarke übernehmen (Empfehlung)“).
3. **Neue Bausteine** nach dem Zielbild: Gliederung, Marke, Leitung in einer Liste, Kopf einer Organisationsseite; Sebastian hat sie an einem Vorschlag aus den echten Vorlagen geprüft.
4. **Keine Marke „Deine Rolle: …“** in Gliederung und Seitenkopf; die eigene Rolle steht bei den Leitungen mit „das bist du“ (ändert A23).
5. **Die Sätze ohne Leitung beginnen mit der Art,** z. B. „Die Gruppe Sippe Falken hat keine Gruppenleitung. …“ (ändert den Wortlaut von A10, A14, A16).
6. **Leitung in zwei Zeilen:** oben Fahrtenname, Name und „das bist du“, darunter links die Rolle und rechts die Mail.
7. **Gliederung so hoch wie der Bildschirm** (beim Testen des Pull Requests): Am PC hat sie eine feste Höhe nach dem Bildschirm und bleibt beim Rollen stehen, statt sich nach der Seite rechts zu richten; sonst sprang sie beim Wechsel zwischen Seiten und rollte innen. Das ersetzt die Wahl aus der Nachklärung zum Zielbild („richtet sich nach der Seite rechts“).

**Technische Wahl** (KI):

- **Alle Rechte aus der zentralen Prüfung:** `Rights.unit_access()` sagt je Einheit „verwalten“ (eigener Bereich), „nur lesen“ (Kette nach oben) oder „nur der Name“ (übriger eigener Bund); `opens_unit()`, `has_lead()` und `covering_unit()` kommen dazu. `leads()` gibt zusätzlich Benutzername, die Kennungen von Konto und Einheit und `locked` heraus, weiter keine Mail und keine internen Nummern; gesperrte Leitungen nur im eigenen Bereich. Die Mail holt die Seite nur über `persons()` und zeigt sie nur im eigenen Bereich.
- **Ein Modul ordnet für die Vorlagen** (`units/organisation.py`): lädt den eigenen Bund, die Leitungen und die Mails mit je einer Abfrage, gleich viele bei jeder Größe des Bundes.
- **Die Seiten stehen in `core/views.py`** bei den übrigen Seiten; die App „units“ hat weiter keine Adressen (S15 aus #88).
- **Nur lesende Aufrufe:** Jede andere Anfrage an die Seite einer Organisation zeigt erst nach der Rechteprüfung „nicht gefunden“, so wie eine Kennung, die es nicht gibt (AV5). Benennen und Entfernen kommen mit eigenen Adressen (#190, #191).
- **Übersicht am PC mit Seite daneben:** Unter `/organisation/` steht neben der Gliederung die oberste Organisation, die man leitet, wie im Zielbild; am Handy nur die Gliederung, für Vorleseprogramme mit unsichtbarer Überschrift „Organisation“.
- **Gliederung rollt zur geöffneten Organisation,** wenn sie kürzer ist als der Baum (am Vorschlag aufgefallen).
- **Höhe der Gliederung:** Bildschirmhöhe minus 80 Pixel (40 oben wie der Rand der Seite, 40 unten), mindestens 360 Pixel; sie bleibt beim Rollen 40 Pixel unter dem oberen Rand stehen. Am Handy wie bisher ohne feste Höhe.
- **Die Rechtematrix** hat neue Zeilen für die Leseseite (EH-28) und gesperrte Leitungen (RO-21, RO-22). Was die Verbandsleitung von gesperrten Leitungen sieht, bleibt wie bisher und entscheidet #94.

**Begründung:** Rechte an einer Stelle, damit Gliederung, Seite und spätere Teile (#190, #191, #95) nicht auseinanderlaufen; bekannte Bausteine statt neuer, wo sie passen.

**Umsetzung:** `access/rights.py`, `units/organisation.py`, `units/texts.py`, `core/views.py`, `core/navigation.py`, `config/urls.py`, `core/templates/core/organisation.html`, `_gliederung.html`, `_knoten.html`, `_kennmarke.html`, `_leitung.html`, `_orgakopf.html`, `_rollenkachel.html`, `bausteine.html`, `core/static/core/app.css`, `app.js`, `docs/rechtematrix.md`, `docs/gestaltung.md`, `docs/zielbilder/`; Tests in `tests/test_organisation.py` und `rauchtests/test_organisation.py`.

## 2026-10-27 · Kurze Meldungen nach einer eigenen Handlung, Fehlermeldungen an der Stelle der Handlung (#186)

**Entscheidung** (Sebastian, Klärung von #186 am 27.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6441936833), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6441930967), [Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6442085509), [Nachklärung](https://github.com/sebivtt/dpv-participant-management/issues/186#issuecomment-6442091320)). Ergänzt den Eintrag zu #165 vom 26.10.2026:

1. **Kurz wird, was eine eigene Handlung bestätigt:** Erfolg und Information (Frage 1; empfohlen war nur Erfolg). Fehler und Warnungen bleiben fest. Was einen dauerhaften Zustand beschreibt, bleibt fest; die Login-Seite bekommt keine kurzen Meldungen (Frage 2).
2. **Dauer und Bedienung:** rund 6 Sekunden, mit ×; Maus darüber oder Fokus darin hält sie an, danach zählt sie neu (Frage 3).
3. **Lage:** unten mittig im Inhaltsbereich, am Handy über fast die ganze Breite (Frage 4).
4. **Erkennbar ohne Farbe** an Lage, deutlichem Schatten und ×, ohne Zeitbalken (Frage 5). Der Schatten ist die einzige Ausnahme von „kaum Schatten“ (`docs/gestaltung.md`).
5. **Ohne Skript** fest oben wie bisher (Frage 6).
6. **Mehrere** stapeln sich, höchstens drei, die neueste unten (Fragen 7 und 8; empfohlen war, dass die neue die alte ersetzt).
7. **Fehlermeldungen nach einer Handlung stehen an der Stelle der Handlung,** unter dem Feld oder der betroffenen Zeile, nicht oben auf der Seite; der Bildschirm springt dorthin (Frage 9, Sebastians Einwand beim Prüfen der Szenarien). Regel für alle Seiten.

**Technische Wahl** (KI):

- **Ein eigener Baustein, der den der Meldungen einbindet:** `{% kurzmeldung %}` nutzt dasselbe Vorlagenstück `core/_meldung.html` und ergänzt nur ein ×, das das Skript sichtbar macht. Für Fehler und Warnungen gibt er eine feste Meldung aus; so kann eine Seite alle Meldungen nach einer Handlung durch ihn schicken, ohne die Regel selbst zu kennen.
- **Der Server schreibt die Meldung an ihren festen Platz,** und das Skript holt sie von dort in den Bereich unten. So bleibt ohne Skript alles wie bisher. Den Bereich gibt es auf jeder Seite mit Login (`base_app.html`), nicht auf der Login-Seite; er ist ein Live-Bereich, der jede neue Meldung einzeln ansagt (`aria-atomic="false"`). Eingeblendet wird 0,1 Sekunden nach dem Laden, weil Vorleseprogramme nur ansagen, was nach dem Bereich selbst dazukommt. Im Bereich verliert die Meldung ihr eigenes `role="status"`, damit sie nicht doppelt angesagt wird.
- **Der Bereich steht in der Reihenfolge der Seite nach dem Inhalt** und vor dem Fußbereich, sichtbar aber unten über allem. So erreicht man das × mit der Tastatur nach wenigen Schritten; auf „Mein Profil“ zwei Mal Tab vom Feld „Fahrtenname“ aus.
- **Fokus zurück** dorthin, wo er war, als die Meldung erschien (Szenario 5: ins Feld „Fahrtenname“), nicht auf das zuletzt besuchte Element davor.
- **Schließen mit × und Verdrängen durch eine vierte** entfernen sofort; nur das Verschwinden nach der Zeit blendet sanft aus.
- **Die Fehlermeldung beim Fahrtennamen** steht im Baustein „Feld zum Antippen“ direkt unter der Eingabe, an derselben Stelle wie der Fehler am Feld, und ist mit der Eingabe verknüpft (`aria-describedby`), damit Vorleseprogramme sie beim Fokus vorlesen. Scheiterte das Speichern, rückt das Skript das Feld mit der Meldung in die Mitte des Bildschirms; beim Fehler am Feld (zu lang) bleibt es wie bisher. „Verwerfen“ lässt die Fehlermeldung stehen und mit der Eingabe verknüpft; sie geht erst beim erneuten Versuch oder beim Seitenwechsel (Akzeptanzkriterium).
- **Tests ohne Warten:** Die Rauchtests stellen die Uhr der Seite (Playwright), statt sechs Sekunden zu warten.

**Begründung:** Kurze Rückmeldungen nach einer Handlung sollen auffallen, ohne die Seite dauerhaft zu füllen; Zustände und Fehler dürfen nicht verschwinden. Eine Fehlermeldung oben auf einer langen Seite holt einen nach oben oder wird übersehen.

**Umsetzung:** `core/templatetags/layout.py` (`kurzmeldung`, `antippfeld` mit `failure`), `core/templates/core/_kurzmeldung.html`, `_meldung.html`, `_antippfeld.html`, `profil.html`, `bausteine.html`, `base_app.html`, `core/static/core/app.js`, `core/static/core/app.css`, `core/views.py` (Bausteinkatalog), `docs/gestaltung.md`, `docs/zielbilder/`; Tests in `tests/test_kurzmeldung.py` und `rauchtests/test_kurzmeldung.py`.

## 2026-10-27 · Zwei Prüfläufe dürfen gleichzeitig laufen (#184)

**Entscheidung** (Sebastian, Klärung von #184 am 27.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/184#issuecomment-6441965054)): Zwei `./pruefen.sh` aus verschiedenen Arbeitskopien dürfen gleichzeitig laufen, und keiner scheitert am anderen (Umfang B). Die normalen Tests laufen gleichzeitig, jede Arbeitskopie mit ihrer eigenen Test-Datenbank. Rauchtest und Container-Prüfung brauchen feste Ports und laufen nacheinander: Ein zweiter Lauf wartet mit einer Meldung, höchstens 30 Minuten, dann bricht er mit einer Meldung ab, was zu tun ist. Das gilt auch für `pytest rauchtests` und `pytest containertests` ohne `./pruefen.sh`. Zwei Läufe in derselben Arbeitskopie gehen weiter nicht gleichzeitig: Sie teilen sich deren Test-Datenbank. Nicht Teil: eigene Ports je Arbeitskopie (Umfang C) und Änderungen am lokalen Keycloak. Der Satz „Zwei Prüfläufe gleichzeitig gehen weiter nicht“ im Eintrag vom 26.10.2026 (#167) gilt damit nicht mehr; der Eintrag selbst bleibt unverändert.

**Begründung:** Am 27.10.2026 brach `./pruefen.sh` bei der Umsetzung von #156 mit „database already exists“ ab, weil ein anderer Lauf gleichzeitig dieselbe Test-Datenbank `test_dpv` nutzte. Mit mehreren Sessions und der unabhängigen Prüfung laufen oft zwei Prüfläufe zugleich. Umfang C hätte etwa 3 bis 4 statt 1,5 Stunden gekostet und das lokale Keycloak geändert.

**Technische Wahl** (KI):

- **Name der Test-Datenbank:** `test_dpv_` und die ersten zwölf Zeichen einer Prüfsumme des Ordners der Arbeitskopie (`config/settings.py`). Derselbe Ordner bekommt immer denselben Namen; so bleibt je Arbeitskopie höchstens eine übrig. Das `README.md` erklärt das Aufräumen („Übrige Test-Datenbanken entfernen“). Eine Prüfsumme statt des Ordnernamens, weil Namen in PostgreSQL höchstens 63 Zeichen lang sind.
- **Wartesperre als Port:** Wer dran ist, belegt Port 8019 (Rauchtest) oder 8029 (Container-Prüfung) auf `127.0.0.1` (`tests/check_ports.py`). Das Betriebssystem gibt den Port frei, sobald der Lauf endet, auch nach einem Absturz; eine Sperre bleibt so nie hängen. Eine Sperrdatei müsste an einem Ort liegen, den alle Arbeitskopien und Sessions gleich sehen; bei den abgeschirmten Sessions von Claude Code ist das nicht sicher, die Ports dieses Rechners aber teilen sich alle. Getrennte Sperren, damit der Rauchtest eines Laufs neben der Container-Prüfung des anderen laufen kann; sie nutzen verschiedene Ports.
- **Ports nach dem vorigen Lauf:** Nach einer Container-Prüfung ist ein Port auf dem Mac noch rund 30 Sekunden belegt (#167). Deshalb wartet die Prüfung bis zu 90 Sekunden, ob ein Prüf-Port frei wird, bevor sie mit der Meldung aus #167 abbricht.

**Umsetzung:** `config/settings.py`, `tests/check_ports.py`, `rauchtests/conftest.py`, `containertests/conftest.py`, `README.md` (Schritt 11); Tests in `tests/test_testdatenbank.py` und `tests/test_pruefports.py`.

## 2026-10-27 · Rauchtest am PC und am Handy, je einmal nur mit der Tastatur (#78)

**Entscheidung** (Sebastian, Klärung von #176 und #78 am 27.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/176#issuecomment-6435571666), Fragen 5 und 6). Ersetzt die Entscheidungen 1 und 2 zu #78 vom 22.10.2026, die sich auf die Musterseite bezogen:

1. **Durchgang am Handy auf den echten Seiten:** In Handy-Größe nur mit der Tastatur von der Login-Seite über Keycloak zur Startseite („Zum Inhalt springen“), über den Profilkreis zu „Mein Profil“, dort den Fahrtennamen öffnen, tippen, mit Esc verwerfen und mit Enter speichern, dann über das Menü abmelden.
2. **Regel für neue Rauchtests:** Jede neue Seite und jede Seite, die neue Bedienelemente bekommt (Knopf, Feld, Dialog), bekommt ihren Rauchtest am PC und am Handy, je einmal nur mit der Tastatur. Ein Durchgang darf mehrere Seiten abdecken. Abgelehnt: nur für neue Seiten.
3. **Gefundene Fehler:** Kleine im selben Pull Request beheben und nennen, größere als eigenes Issue nach Rückfrage (wie am 22.10.2026).

**Technische Wahl** (KI):

- **Reihenfolge von oben nach unten** prüft der Test an der Lage jedes Halts auf der Seite: Er steht unter dem vorigen oder in derselben Zeile rechts davon.
- **Keycloak** gestaltet seine Seite selbst, und das Tool ändert dort nichts (`CLAUDE.md`). Der Test prüft dort nur, dass der Fokus zu sehen ist (Rahmen des Browsers, dicker blauer Strich unter dem Feld statt des dünnen grauen ohne Fokus), nicht die strengere Regel des Tools (Rahmen ab 2 px, Kontrast ab 3 : 1).
- **Mitbehoben (Entscheidung 3):** Eingabefelder des Tools zeigten den Fokus nur mit einem blassen Schatten, weil Bootstrap ihren Rahmen abschaltet. Sie bekommen jetzt denselben blauen Rahmen wie Knöpfe und Links, wie im Zielbild „Meldungen“. Das Zielbild „Mein Profil“ zeigt dort nur Bootstraps Schatten; NFA-03 und `docs/gestaltung.md` („gut sichtbare Fokuszustände“) gehen vor.

**Begründung:** Am Handy sieht das Tool anders aus als am PC (Menü als Dialog, Profilkreis oben). Probleme mit Reihenfolge oder Sichtbarkeit des Fokus dort fielen sonst keinem Test auf (Befund K5 aus dem Review zu P1, #73). Die Musterseite taugt dafür nicht mehr, weil sie zum Bausteinkatalog wurde (#176).

**Umsetzung:** `rauchtests/test_rauchtest.py`, `rauchtests/conftest.py` (`focus_visible` gibt die Lage zurück), `core/static/core/app.css`, `CONTRIBUTING.md`, Abschnitt 3; dazu prüft `test_fahrtenname_nur_mit_der_tastatur` am PC den Fokus in der offenen Eingabe.

## 2026-10-27 · Bausteinkatalog statt Musterseite: nur Entschiedenes, eingebunden statt kopiert (#176)

**Entscheidung** (Sebastian, Klärung von #176 am 27.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/176#issuecomment-6435571666), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/176#issuecomment-6435572131)):

1. **Nur Entschiedenes:** Der Katalog zeigt nur Bausteine, die Sebastian an einem Zielbild oder in einer Klärung ausdrücklich freigegeben hat und die das Issue dazu nennt. Die Vorschauen aus #7 (Dashboard, Veranstaltungszeilen, Statuskennzeichen, Schritte, Teilnehmendentabelle, Beispiel-Navigation) gelten als überholt; ihre Regeln bleiben als Text in `docs/gestaltung.md` und kommen über die Zielbilder von #28, #29 und #30 wieder (Fragen 1 und 8).
2. **Vorab in den Katalog:** Ein Baustein kommt in den Katalog, sobald Sebastian ihn entschieden hat, spätestens mit seiner ersten Seite; bis dahin mit dem Vermerk „noch auf keiner Seite“. Die Empfehlung war „im selben Pull Request wie seine erste Seite“; Sebastian entschied anders (Frage 7).
3. **Einbinden, nicht kopieren:** Jede Seite bindet den Baustein ein. Passt er nicht genau, hält die KI an und fragt Sebastian, ob er erweitert wird oder ein neuer entsteht; nie eine stille Kopie. Dazu ein Prüfpunkt in der unabhängigen Prüfung und ein Test, dass jedes Eingabefeld auf echten Seiten aus einem Baustein kommt (Frage 11).
4. **Wer ihn sieht:** nur Angemeldete auf dem eigenen Rechner und in der Testumgebung; im Betrieb „Diese Seite gibt es nicht.“ für alle, auch Admins (Frage 3).
5. **Prüfung:** im Katalog nur die Prüfung auf Barrierefreiheit am PC und am Handy; mit der Tastatur geprüft wird ein Baustein auf seiner ersten echten Seite (Fragen 4 und 9). Die Rauchtests, die nur an den alten Vorschauen hingen, entfallen; der Tastaturtest am PC auf der Musterseite entfällt, Ersatz auf echten Seiten bringt #78 (Frage 2).
6. **Alter Name:** Die offenen Issues, die „Musterseite“ sagen, bleiben unverändert; `docs/gestaltung.md` ordnet den Namen in einem Satz zu (Frage 12).
7. **Stunden:** rund 4 aus dem Puffer (Frage 10, `docs/fahrplan.md`, Nr. 50).

**Technische Wahl** (KI):

- **Adresse `/bausteine/`** statt `/muster/`; die alte Adresse gibt es nicht mehr.
- **Sichtbar** über die Einstellung `BUILDING_BLOCKS_VISIBLE`: an, wenn `DJANGO_DEBUG=1` (eigener Rechner) oder die Testumgebung eingeschaltet ist; im Betrieb ist beides aus. Der Katalog antwortet dort wie eine Adresse, die es nicht gibt. Die Prüfungen laufen wie auf dem eigenen Rechner, mit sichtbarem Katalog; die Tests für den Betrieb schalten ihn ab.
- **Als gemeinsamer Baustein zählt jedes Vorlagenstück, das Seiten einbinden**, direkt mit `include` oder über einen Baustein aus `core/templatetags/layout.py`. Ausnahmen stehen mit Grund im Test: die Symbole, das Logo und der Rahmen jeder Seite (Marke, Navigation, Konto, Fußbereich), in dem der Katalog selbst steht.
- **Gesperrte Angabe, Kopfzeile mit Name und Überschrift einer Fläche** (#161) standen bisher als kopiertes HTML auf der Musterseite und auf „Mein Profil“. Sie sind jetzt eigene Vorlagenstücke, die beide einbinden; sonst hätte der Katalog sie weiter kopiert.
- **Die Seiten je Baustein** stehen in `core/views.py` (`BUILDING_BLOCKS`); ein Test prüft an den Vorlagen, dass „noch auf keiner Seite“ genau dort steht, wo keine Seite den Baustein einbindet. So steht das Textfeld heute mit diesem Vermerk da: Das Feld zum Antippen nutzt nur seine Eingabe, nicht sein Vorlagenstück.
- **Was nichts mehr nutzt, entfällt:** die Vorlagenstücke Statuskennzeichen und Veranstaltungszeile, die beiden Beispielbilder, das Aussehen der Vorschauen und zwölf Symbole. Die Farben bleiben an ihrer einen Stelle in `core/static/core/app.css`. Alles Entfernte steht in der Git-Historie, falls #28, #29 oder #30 es brauchen.

**Begründung:** Die Musterseite war veraltet und zeigte Vorschauen, die nie entschieden waren. Ein Katalog, der dieselben Vorlagenstücke einbindet wie die Seiten, weicht nie vom echten Aussehen ab, und die Tests machen sichtbar, wenn eine Seite etwas selbst baut.

**Umsetzung:** `core/views.py` (`building_blocks`, `BUILDING_BLOCKS`), `config/urls.py`, `config/settings.py`, `core/templates/core/bausteine.html`, `_katalogeintrag.html`, `_angabe.html`, `_kopfzeile.html`, `_flaechenkopf.html`, `profil.html`, `core/static/core/app.css`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/gestaltung.md`, `docs/fahrplan.md`; Tests in `tests/test_bausteinkatalog.py`, angepasst in den Tests, die die Musterseite nutzten, und in `rauchtests/`.

## 2026-10-27 · Keine internen Nummern auf Seiten, Test „wie nicht vorhanden“ für jede Adresse mit Kennung, Liste der Leitungen ohne Nummern (#156)

**Entscheidung** (Sebastian, Klärung von #156 am 25.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/156#issuecomment-6398716809), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/156#issuecomment-6398716981)). Ergänzt die Einträge zu #90 und #64 vom 25.10.2026:

1. **Keine Nummern, auch nicht außerhalb des Adresspfads:** Keine Seite enthält die interne Nummer eines Kontos oder einer Einheit, weder in einem Link oder angehängten Parameter (`?einheit=17`) noch in einem Formularfeld (auch `hx-vals`) noch im Text oder einer Weiterleitung. Wählt eine Seite einen Eintrag über einen Parameter oder ein Formularfeld, etwa aus einer Auswahlliste, holt sie ihn über `entry()`, das nur Kennungen annimmt; eine Nummer ergibt „nicht gefunden“ wie eine erfundene Kennung.
2. **Jede Adresse mit Kennung hat einen Test „genau gleich wie nicht vorhanden“:** Er prüft ihren verbotenen Fall mit dem Baustein `assert_like_missing` und trägt die Markierung `@pytest.mark.wie_nicht_vorhanden("<Muster der Adresse>")`. Fehlt er, wird der Rundumtest rot, auch für Adressen, die später dazukommen. Ob der Test den richtigen verbotenen Fall wählt, bleibt Sache der unabhängigen Prüfung.
3. **Gleich viele Datenbankabfragen:** Ein Eintrag, den die Person nicht sehen darf, und ein nicht vorhandener lösen auf allen vier Wegen (öffnen, nachladen, Formular, Formular nachladend) gleich viele Abfragen aus. Gezählt wird, nicht gemessen. Ausgenommen sind Einträge, die die Person sieht, aber nicht bearbeiten darf (Protokoll, Frage 2); die Antwort ist dort trotzdem genau gleich „nicht gefunden“.
4. **Liste der Leitungen ohne Nummern:** `leads()` gibt nur noch Vor- und Nachname, Fahrtenname, Rolle und Name der Einheit heraus, nicht mehr `user_id` und `unit_id`. Braucht #93 eine Kennung, kommt die Kennung der Rolle dazu. **Richtigstellung** zum Eintrag zu #90 („Leitungen nur mit Name und Rolle“): Die Liste enthielt dort keine Kennung, sondern die internen Nummern von Konto und Einheit; keine Seite und kein Code nutzte sie.

**Technische Wahl** (KI, von Sebastian in der Klärung bestätigt):

- **Suche an der Ausgabe:** Die Tests in `tests/test_rechte_ohne_seite.py` rufen ohnehin jede Adresse des Tools als sechs Personen auf vielen Wegen auf. Dort bekommen Konten und Einheiten auffällige Nummern ab 7000001 bzw. 7100001, und jede Antwort wird samt Kopfzeilen und Cookies nach diesen Nummern als ganzen Zahlen durchsucht. Adressen mit Kennung ruft die Suche außer mit einer erfundenen auch mit jeder echten Kennung auf, damit auch Seiten mit gefundenem Eintrag geprüft sind. Umkodierte Nummern (z. B. Base64) findet sie nicht; die bleiben Sache der unabhängigen Prüfung. Kennungen enthalten nur die Ziffern 2 bis 7 und können eine solche Nummer nie enthalten; Jahreszahlen und andere Zahlen stören nicht. Was keine Seite zeigt, kann kein Browser zurückschicken. Abgelehnt: eine Suche im Quelltext nach `pk=` oder Auswahllisten (fände nur die Wege, an die man denkt, und meldete erlaubte interne Nutzung) und das Durchprobieren von Parametern (die Namen späterer Parameter sind unbekannt).
- **Prüfung der Tests „wie nicht vorhanden“** in `tests/test_rundumtest.py`, nach dem Vorbild der Prüfung der Rechtematrix: Sie liest die Testdateien und zählt nur Tests mit Markierung, die `assert_like_missing` aufrufen und nicht übersprungen werden. `assert_like_missing` ersetzt dafür jetzt genau die Kennungen in der Adresse; bisher tauschte es das vierte Stück der Adresse aus, was nur für die Testadressen passte.

**Begründung:** Die nachträglichen Szenarien zu #90 und #64 zeigten acht Lücken (#156): Regeln, die der Code schon erfüllte, ohne dass ein Test sie belegte, und Regeln aus #64, die nur für den Adresspfad galten. Mit den Prüfungen aus Punkt 1 und 2 gilt die Regel aus #64 auch für die Seiten, die noch kommen (#65, #93, #117).

**Umsetzung:** `access/rights.py` (`LEAD_FIELDS`, Text zu `entry()`), `pyproject.toml` (Markierung `wie_nicht_vorhanden`), `CONTRIBUTING.md` (Abschnitt 4), `docs/rechtematrix.md` (Tabellenliste bei `units.Unit`), Tests in `tests/test_rechtepruefung.py`, `tests/test_nicht_gefunden.py`, `tests/test_rundumtest.py`, `tests/test_rechte_ohne_seite.py`, `tests/test_rechtematrix.py` und `tests/urls.py`.

## 2026-10-26 · „Zielbild vor Gestaltung“ als feste Regel beim Klären (#162)

**Entscheidung** (Sebastian, Klärung von #162 am 26.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/162#issuecomment-6421454032)):

1. **Zeitpunkt:** Grober Entwurf und Zielbild entstehen während der Klärung, nicht erst bei der Umsetzung. Die klärende Session baut den groben Entwurf und hängt ihn als Kommentar ins Issue; das Zielbild kommt als Kommentar mit Prüfsumme ins Issue.
2. **Wann nötig:** bei einer neuen Seite mit eigener Adresse und bei einem neuen sichtbaren gemeinsamen Baustein für die Musterseite. Bei einem neuen Abschnitt einer bestehenden Seite fragt `grill-me` Sebastian. Proben (#100 bis #102, Entscheidung F1 aus #106) und reine Erweiterungen bestehender Seiten brauchen keins.
3. **Reihenfolge:** Klären und Szenarien → grober Entwurf → Zielbild → Nachklärung jeder Abweichung einzeln mit Sebastian, Issue und Szenarien angepasst → erst dann `geklärt`.
4. **Sperre über `geklärt`:** Ein Issue, das ein Zielbild braucht, bekommt `geklärt` erst mit Zielbild im Issue; die Umsetzung prüft vor dem Start, ob es dort steht, und hält sonst an, wie bei den Szenarien. Aufträge bleiben nur Link und Verweis (#169); das Kriterium „Aufträge nennen den Schritt“ aus dem ersten Text von #162 entfällt.
5. **Kein fachliches Verhalten,** deshalb keine Szenarien.

Unverändert gilt der Eintrag vom 25.10.2026 zu #161: Ein Zielbild ist Orientierung, keine Anforderung, mit nur erfundenen Daten.

**Begründung:** „Mein Profil“ entstand ohne Zielbild und blieb schlicht. Damit der Schritt nicht vom Auftrag einer Session abhängt, steht er wie „Szenarien vor Code“ (#158) fest in den Arbeitsregeln. Bei #165 hat sich gezeigt, dass das Zielbild Abweichungen bringt, die vor dem Label `geklärt` nachgeklärt werden müssen (dort die Farben).

**Technische Wahl** (KI): Zielbilder bleiben unter `docs/zielbilder/` mit Eintrag in `docs/zielbilder/README.md` (Eintrag vom 25.10.2026). Der grobe Entwurf kommt als Kommentar ins Issue, in einem aufklappbaren Codeblock wie das Zielbild bei #165, damit er nachvollziehbar bleibt, ohne das Repo zu füllen. Ist eine Datei zu groß für einen Kommentar, wird sie unverändert auf nummerierte Kommentare verteilt (Befund der unabhängigen Prüfung). Der Satz „Grobe Entwürfe … etwa zwei Gruppen vorher“ in „Klären läuft voraus“ widersprach der neuen Reihenfolge; jetzt kommen Issues mit Zielbild früher in Klärung (ebenso in `phase-steuern`). In `CLAUDE.md` steht die Regel als eigener Absatz nach den nummerierten Schritten, damit sich deren Nummern nicht verschieben; frühere Einträge verweisen auf sie. In `grill-me` kommt ein Abschnitt 6 „Grober Entwurf und Zielbild“ dazu; die bisherigen Abschnitte 6 bis 8 heißen jetzt 7 bis 9.

**Umsetzung:** `CLAUDE.md` („Ablauf je Aufgabe“: Absatz „Zielbild vor Gestaltung“ und „Für die Umsetzung gilt außerdem“; „Ablauf einer Phase“: „Klären läuft voraus“), `.claude/skills/grill-me/SKILL.md` (Abschnitte 2, 5, 6, 9 und „Kurzform“), `.claude/skills/phase-steuern/SKILL.md` (Abschnitt 2), `.github/pull_request_template.md` (neu „Zielbild“), `docs/gestaltung.md` und `docs/zielbilder/README.md` (Verweise), `tests/test_arbeitsregeln.py`.

## 2026-10-26 · Fahrtenname auf „Mein Profil“ wie im Zielbild: Feld zum Antippen (#180)

**Entscheidung** (Sebastian, Klärung von #180 am 26.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/180#issuecomment-6423072701), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/180#issuecomment-6423073029)):

1. **Wie im Zielbild:** Das Feld „Fahrtenname“ sieht in Ruhe aus wie die anderen Angaben (Personensymbol, Fahrtenname oder „Noch nicht angegeben“, rechts ein ×-Knopf). Antippen öffnet die Eingabe mit dem Platzhalter „Fahrtennamen eingeben“, darunter „Verwerfen“ und „Speichern“. Speichern mit Knopf oder Enter; Verwerfen mit Knopf, Esc oder Tippen außerhalb, mit Ansage für Vorleseprogramme; danach liegt der Fokus wieder auf dem Feld. Damit gilt die Abweichung „immer offen, nur ‚Speichern‘“ aus dem Eintrag zu #111 (Technische Wahl, „Speichern“) und aus `docs/zielbilder/README.md` nicht mehr.
2. **×-Knopf in Ruhe** öffnet das Feld leer; gelöscht wird erst mit „Speichern“. Verworfen: sofort löschen.
3. **Kopfzeile wie im Zielbild:** Fahrtenname groß, „(Vorname Nachname)“ kleiner und grauer dahinter; ohne Fahrtenname nur der Name. Listen entscheiden später selbst (#117, #65).
4. Meldungen, 50 Zeichen, Leerzeichen und Rechte bleiben wie in #111.

**Begründung:** So war es mit dem Zielbild vereinbart; PR #177 war davon abgewichen, und Sebastian hat das erst nach der Übernahme bemerkt.

**Technische Wahl** (KI):

- **Baustein** `{% antippfeld form.feld saved=… icon=… open=… focus=… %}` in `core/templatetags/layout.py` mit `core/templates/core/_antippfeld.html`, damit spätere Felder (Geburtsdatum, Adresse) dasselbe Verhalten bekommen. Er baut auf dem Baustein Textfeld auf (gleiches Feld, gleicher Fehler am Feld).
- **Kleines Skript** in `core/static/core/app.js` öffnet und schließt das Feld; gespeichert wird weiter mit dem Formular an `/profil/fahrtenname/`, ohne neue Adresse und ohne htmx. Was nur mit Skript geht (Ruhezustand, ×, „Verwerfen“), ist im HTML versteckt; ohne Skript bleibt das einfache Formular aus #111 (Szenario 11).
- **Nach einem Fehler** (zu lang, Speichern gescheitert) kommt das Feld offen vom Server, mit dem Fokus in der Eingabe. **Nach dem Speichern** bekommt das Feld den Fokus; die Seite erkennt das an einem Kennzeichen an der Erfolgsmeldung (`extra_tags="fahrtenname"`).
- **Tippen außerhalb** gibt den Fokus nur dann ans Feld zurück, wenn kein Link, Knopf oder Eingabefeld angetippt wurde, damit niemandem der Fokus weggenommen wird. Das Skript hört dafür auf das erste Berühren (`pointerdown`), weil Safari am iPhone ein Antippen von Flächen ohne eigene Funktion nicht als Klick meldet. Esc verwirft auch, wenn der Fokus mit Tab schon aus dem offenen Feld hinaus ist (beides aus der unabhängigen Prüfung).
- **Zweiter Knopf** „Verwerfen“ weiß mit feinem Rand wie im Zielbild (`btn-zart` in `core/static/core/app.css`).

**Umsetzung:** `core/templatetags/layout.py`, `core/templates/core/_antippfeld.html`, `core/templates/core/profil.html`, `core/templates/core/muster.html`, `core/views.py`, `core/static/core/app.js`, `core/static/core/app.css`, `accounts/forms.py` (Platzhalter), `docs/gestaltung.md`, `docs/zielbilder/README.md` (Punkt 10); Tests in `tests/test_fahrtenname_feld.py`, `tests/test_fahrtenname.py`, `tests/test_mein_profil.py` und `rauchtests/test_rauchtest.py`.

## 2026-10-26 · Fahrtenname: die Person trägt ihn selbst ein, angezeigt als „Kiwi (Erika Testfrau)“ (#111, #112)

**Entscheidung** (Sebastian, Klärung von #111 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/111#issuecomment-6344762503); [Nachklärung vom 26.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/111#issuecomment-6417655066); [Szenarien vom 26.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/111#issuecomment-6417654692)):

1. **Regel:** Personen haben neben Vor- und Nachnamen oft einen Fahrtennamen, unter Pfadfindern meist der bekanntere Name. Keycloak liefert ihn nicht; er wird im Tool gepflegt. Eine Person mit Konto trägt ihren Fahrtennamen selbst auf „Mein Profil“ ein, ändert oder löscht ihn; er ist freiwillig. Niemand sonst ändert ihn, auch keine Leitung und kein Admin (EP-03, EP-04). Den Fahrtennamen verwalteter Personen tragen die Leitungen ein, die die Person bearbeiten dürfen (#97).
2. **Ergänzung von W1:** „Mein Profil“ bekommt in P2 genau ein Feld zum Bearbeiten, den Fahrtennamen (Eintrag vom 25.10.2026 zu #96, Nr. 2). Vorname, Nachname und Mail kommen weiter aus Keycloak.
3. **Anzeige:** Wo eine Person mit vollem Namen erscheint, steht „Kiwi (Erika Testfrau)“, ohne Fahrtenname „Erika Testfrau“. Wo sonst der Vorname allein stünde (Begrüßung, Profilkreis, später Anreden in Mails), steht der Fahrtenname, wenn er eingetragen ist. Suche und Listen kommen mit ihren Seiten (#93, #94, #65, #117) und nutzen dieselbe Stelle.
4. **Anforderungen:** PER-01 und PER-02 nennen den Fahrtennamen mit dem Wortlaut aus der Klärung (Frage 4, #112).
5. **Grenzen und Meldungen:** höchstens 50 Zeichen; Leerzeichen am Rand werden entfernt, nur Leerzeichen gilt als kein Fahrtenname. Meldungen nach #165 mit Sebastians Wortlauten; zu lang ist ein Fehler am Feld. Der Fahrtenname steht nie im Fehlerprotokoll; Änderungen werden nicht protokolliert, weil er keine Rolle ist.

**Begründung:** Es ist der Name der Person; trägt sie ihn selbst ein, gibt es keinen Streit, wessen Eintrag gilt, und neue Konten müssen auf niemanden warten.

**Technische Wahl** (KI):

- **Code-Namen** (`CONTRIBUTING.md`, Abschnitt 1): Fahrtenname heißt `scout_name`, der volle Name „Kiwi (Erika Testfrau)“ `display_name`. Die gemeinsame Stelle ist `display_name()` in `accounts/models.py` (auch als `User.display_name`); fehlen Vor- und Nachname, steht nur „Kiwi“, ohne leere Klammern. Den Namen für Begrüßung und Profilkreis liefert weiter `User.short_name`.
- **Speichern** über ein Formular ohne Skript an `/profil/fahrtenname/`. Ein Aufruf ohne abgeschicktes Feld führt ohne Speichern zu „Mein Profil“, etwa nach einem Login, der dorthin zurückführt. Die Adresse hat keine Kennung, und das Formular nimmt nur den Fahrtennamen an; wessen Konto sich ändert, bestimmt allein die Anmeldung. Gespeichert wird nur dieses eine Feld, damit ein zweiter Tab nichts anderes überschreibt; danach geht es zurück zu „Mein Profil“ mit der Erfolgsmeldung. Scheitert das Speichern, steht im Log nur „Fahrtenname nicht gespeichert“ mit der Art des Fehlers.
- **Länge erst auf dem Server:** Das Feld hat kein `maxlength`; sonst schnitte der Browser beim Einfügen still ab, statt den Fehler am Feld zu zeigen. Leerzeichen am Rand entfernt dieselbe Funktion wie beim Namen aus Keycloak (`trimmed()`, #77).
- **Gemeinsamer Baustein für Textfelder** (technischer Hinweis vom 25.10.2026): `{% textfeld form.feld %}` in `core/templatetags/layout.py` mit `core/templates/core/_textfeld.html`. Er zeigt Beschriftung, bei Pflichtfeldern „(Pflicht)“, und den Fehler direkt unter dem Feld, mit dem Feld verknüpft. Die passende Handy-Tastatur legt das Formular am Feld fest; beim Fahrtennamen Großbuchstabe am Wortanfang, ohne Autokorrektur und Rechtschreibprüfung, damit „Kiwi“ nicht zu einem anderen Wort wird. Das Feld ist weiß, damit es sich von den grauen, gesperrten Feldern abhebt (Zielbild).
- **Leitungen** liefern den Fahrtennamen mit (`LEAD_NAMES` in `access/rights.py`), weil BER-01, Grund 3 ihn nennt; angezeigt wird er erst mit den Seiten aus #93 und #94.

**Umsetzung:** `accounts/models.py`, `accounts/forms.py`, `accounts/texts.py`, `accounts/migrations/0003_scout_name.py`, `core/views.py`, `core/forms.py` (Beispiel der Musterseite), `core/navigation.py`, `config/urls.py`, `access/rights.py`, `core/templatetags/layout.py`, `core/templates/core/_textfeld.html`, die Vorlagen von „Mein Profil“ und Musterseite, `core/static/core/app.css`, `docs/anforderungen.md` (PER-01, PER-02), `docs/rechtematrix.md` (EP-01, EP-03, EP-04 gebaut), `docs/gestaltung.md`, `docs/zielbilder/README.md`; Tests in `tests/test_fahrtenname.py` und `rauchtests/test_rauchtest.py`.

## 2026-10-26 · Fahrtenname, Austreten und Aufgaben aus #136 aus dem Puffer; zwei Wortlaute im Fahrplan (#113)

**Entscheidung** (Sebastian, 22.10.2026 bei der Klärung von Block 3 aus #106, [Nachtrag in #111](https://github.com/sebivtt/dpv-participant-management/issues/111#issuecomment-6348444653) und [Nachklärung in #106](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6351698512); 25.10.2026 [Zustimmung zu den Stunden aus #136](https://github.com/sebivtt/dpv-participant-management/issues/113#issuecomment-6390119705)):

1. Fahrtenname (#111, rund 5 Stunden), Austreten aus der eigenen Einheit (#65, rund 3 Stunden) und die Aufgaben aus #136 (rund 6 bis 7 Stunden) kommen neu in P2. Sie verdrängen nichts, sondern kosten Stunden aus dem Puffer (Annahme), weil es in P2 nichts gleich Großes gibt, das sich sinnvoll streichen ließe. Rechnung: 611 + 5 + 3 = 619; 619 + 6 = 625 bzw. 619 + 7 = 626 Stunden; Puffer 658 − 625 = 33 bzw. 658 − 626 = 32 Stunden; 33 / 625 ≈ 5,3 %, 32 / 626 ≈ 5,1 %, rund 5 %. Die Stundenspalte der Phasen bleibt unverändert.
2. Am Ende jeder Phase läuft der Leistungstest aus #145; seine Stunden kommen dazu, wenn #145 geklärt ist.
3. **Vorschläge zum Wortlaut** (#113; gelten mit Sebastians Zustimmung im Pull Request zu #111): Das Abschlusskriterium von P2 heißt „Verbandsleitung sieht Personendaten nur nach BER-01, Grund 3, 4 und 7“ statt „Verbandsleitung sieht keine Personen“, weil die Verbandsleitung seit #136 Name, Fahrtenname und Rolle bestimmter Leitungen, Treffer der Kontosuche und das Protokoll der Admin-Zugriffe sieht. In den Übereinstimmungen heißt es „Kreise im Tool“ statt „Eigene Kreise“ (seit #150 „Kreis“); in der Tabelle zum alten Tool bleibt „eigene Kreise“, weil es dessen Stand beschreibt.

**Umsetzung:** `docs/fahrplan.md`, Abschnitt 2 (Übereinstimmungen), Abschnitt 3 (neuer Absatz nach dem zu #131, Abschlusskriterium von P2) und Abschnitt 6 (Nr. 46, 48 und 49). Der Absatz zu #131 bleibt unverändert; wie die früheren nennt er den Stand nach seinem Schritt, der neue Absatz schreibt die Zahlen fort.

## 2026-10-26 · Leerzeichen am Rand von Name, Mail und Benutzername (#77)

**Entscheidung** (Sebastian, Klärung von #77 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/77#issuecomment-6348998015); [Szenarien vom 26.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/77#issuecomment-6417176187)):

1. **Nur am Rand reinigen:** Beim Übernehmen aus Keycloak entfernt das Tool Leerzeichen am Anfang und Ende von Vorname, Nachname, Mail und Benutzername; unsichtbare und geschützte Leerzeichen zählen mit. Innerhalb eines Namens bleibt alles, wie es im DPV-Konto steht („Anna  Lena“ bleibt). Abgelehnt: auch innen mehrere Leerzeichen zusammenfassen, weil das den Namen verändert.
2. **Was danach leer ist, gilt als fehlend:** Warnmeldung „Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an.“ auf Startseite und „Mein Profil“, Begrüßung „Hallo!“, Personensymbol im Profilkreis, auf „Mein Profil“ „nicht angegeben“. Ohne Mail kein Login, wie bisher.
3. **Eine Stelle für den angezeigten Namen,** damit #111 dort den Fahrtennamen vorschalten kann.
4. **Gespeicherte Namen** werden beim nächsten Login bereinigt; eine eigene Bereinigung bestehender Daten gibt es nicht, weil es nur Testdaten gibt.

**Begründung:** Ein Vorname nur aus Leerzeichen galt als vorhanden. Die Startseite begrüßte dann mit „Hallo  !“, der Hinweis zum Ergänzen fehlte, und eine Mail aus Leerzeichen bestand die Prüfung „ohne Mail kein Login“ (Befund K4 des externen Reviews, #73).

**Technische Wahl** (KI): Gereinigt wird beim Übernehmen aus Keycloak, nicht erst bei der Anzeige, damit Suche, Listen und Hinweise dieselben Werte sehen (`trimmed()` in `accounts/keycloak_abgleich.py`, angewendet in `accounts/adapter.py`). Als Leerzeichen gilt alles, was Python als Leerraum kennt, dazu die unsichtbaren Zeichen U+00AD, U+180E, U+200B bis U+200D, U+2060 und U+FEFF. Überlange Angaben werden nach dem Kürzen erneut gereinigt, sonst stünde das Leerzeichen wieder am Ende (Befund der unabhängigen Prüfung). Den angezeigten Namen liefert `User.short_name` (`accounts/models.py`); Begrüßung und Profilkreis fragen nur dort. Das stellt die Stelle aus dem Eintrag vom 25.10.2026 zu #96 richtig: Dort hieß es, #77 regle das in der gemeinsamen Prüfung des fehlenden Namens (`core/views.py`); diese Prüfung bleibt gemeinsam, braucht aber keine eigene Regel mehr, weil die Werte schon beim Login gereinigt werden.

**Umsetzung:** `accounts/keycloak_abgleich.py`, `accounts/adapter.py`, `accounts/models.py`, `core/views.py`, die Vorlagen von Startseite, „Mein Profil“, Musterseite und Profilkreis; Tests in `tests/test_namen_leerzeichen.py`.

## 2026-10-26 · Meldungen als gemeinsame Bausteine; Sonnengelb nie für Meldungen (#165)

**Entscheidung** (Sebastian, Klärung von #165 am 26.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6415185220), [Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6416562863), [Nachklärung nach dem Zielbild](https://github.com/sebivtt/dpv-participant-management/issues/165#issuecomment-6416568804)):

1. **Vier Arten von Meldungen,** je ein gemeinsamer Baustein: Information (neutral, nichts zu tun; zart blau, „i“ oder ein passenderes Symbol), Warnung (etwas fehlt, die Person muss selbst etwas tun; helles Gelb `#fbefd5` mit Braun `#74500c`, Warndreieck), Fehler (hat nicht geklappt, nur neu versuchen oder warten; gedecktes Rot, Kreuz), Erfolg (hat geklappt; gedecktes Grün, Haken). Fehler am Feld bleiben rote Schrift direkt am Feld und sind keine dieser Arten. Die Zuordnung der bestehenden Meldungen steht im Text von #165.
2. **Eine Farbfamilie** mit den Statuskennzeichen: Warnung wie „Warteliste“, Fehler wie „abgemeldet“, Erfolg wie „angemeldet“; unterschieden wird über die Form.
3. **Sonnengelb** bleibt sparsam wie bisher (aktiver Navigationspunkt, Symbol von „Veranstaltung erstellen“, aktueller Schritt). Als Fläche nur für das Band der Testumgebung, nie für Meldungen. Das Band bekommt schräge Streifen und ein eigenes Laborsymbol statt des Warndreiecks.
4. **Ohne Farbe erkennbar:** Jede Art hat ihr Symbol, Vorleseprogramme hören vorweg ihr Wort. Die Regel steht in `docs/gestaltung.md`, Abschnitt 1, „Meldungen“.

Damit ist Frage 5 der ersten Klärung (Sonnengelb auch für Warnmeldungen) durch die Nachklärung nach dem Zielbild ersetzt; der Eintrag vom 21.10.2026 zur Grundgestaltung gilt sonst weiter.

**Begründung:** Der Hinweis „Du bist noch keiner Organisation zugeordnet.“ stand im Türkis von Bootstrap, das nicht zu den Farben des Tools gehört, und jede Seite gestaltete ihre Hinweise selbst. Mit vier festen Arten sieht man an Farbe und Symbol sofort, ob man nur etwas erfährt, etwas tun muss, etwas schiefging oder etwas geklappt hat. Helles Gelb statt Sonnengelb, weil die Warnung so ruhiger wirkt und sich klar vom Band der Testumgebung abhebt; eine Farbfamilie, damit das Tool nicht noch mehr Farben bekommt.

**Technische Wahl** (KI): Der Baustein ist ein Template-Tag `{% meldung art text=… title=… icon=… live=… %}` in `core/templatetags/layout.py` mit der Vorlage `core/templates/core/_meldung.html`; die Arten heißen im Code wie die Stufen von Djangos Meldungen (`info`, `warning`, `error`, `success`), damit die Login-Seite sie direkt weitergibt. Die Hinweise beim Login tragen deshalb jetzt die passende Stufe: Abbruch und „gerade nicht möglich“ als `error`, „keine Mail“ als `warning` (`accounts/adapter.py`, `accounts/views.py`). Fest stehende Meldungen sind `role="note"`; Meldungen nach einer Handlung (`live=True`) sind `role="alert"` (Warnung, Fehler) oder `role="status"` (Information, Erfolg), wie im Zielbild. Eine unbekannte Stufe erscheint als Information statt als Serverfehler (Befund der unabhängigen Prüfung). Die Klassen `alert` von Bootstrap und die blaue Hinweisfläche (`a-hinweisflaeche`) sind entfernt; ein Test meldet, wenn eine Vorlage wieder `alert` nutzt.

**Umsetzung:** `core/templatetags/layout.py`, `core/templates/core/_meldung.html`, `core/templates/core/_symbole.svg` (Symbole „info“, „erfolg“, „labor“), `core/templates/core/_testband.html`, `core/static/core/app.css`, die Vorlagen von Startseite, „Mein Profil“, Login und Musterseite, `docs/gestaltung.md`, `docs/zielbilder/meldungen.html` mit Eintrag in `docs/zielbilder/README.md`; Tests in `tests/test_meldungen.py` und im Rauchtest (`rauchtests/test_rauchtest.py`).

## 2026-10-26 · Eigene Ports für die Prüfungen (#167)

**Entscheidung** (Sebastian, Klärung von #167 am 26.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/167#issuecomment-6414436246)): Port 8000 und 8081 gehören dem eigenen Tool (README, Schritt 9) und der eigenen Testumgebung im Container (README, Schritt T). Prüfungen belegen sie nie; das Tool und `./pruefen.sh` können gleichzeitig laufen. Ist ein Prüf-Port belegt, nennt die Prüfung den Port und was zu tun ist. Zwei Prüfläufe gleichzeitig gehen weiter nicht, weil sie sich die Testdatenbank teilen.

**Begründung:** Am 25.10.2026 war `./pruefen.sh` zweimal rot, weil Sebastians Tool Port 8000 belegte, und sein Browser zeigte unter Port 8000 die Container-Prüfung einer anderen Session statt seines eigenen Tools.

**Technische Wahl** (KI): Der Rauchtest nutzt Port 8010, die Container-Prüfung 8020 (Tool) und 8091 (Keycloak); die Zahlen stehen nur in `tests/check_ports.py`. Die Ports der Testumgebung sind über `TESTUMGEBUNG_TOOL_PORT` und `TESTUMGEBUNG_KEYCLOAK_PORT` einstellbar, ohne Angabe 8000 und 8081. Das lokale Keycloak (`dev/keycloak/dpv-realm.json`) lässt zusätzlich die Rückkehr zu `localhost:8010` und `localhost:8020` zu; nur dieses erfundene Keycloak, nie das des Verbands. Ob ein Port belegt ist, prüfen zwei Proben (antwortet dort etwas, lässt er sich selbst belegen), weil auf dem Mac ein Port nach der Container-Prüfung noch belegt sein kann, ohne zu antworten.

**Umsetzung:** `tests/check_ports.py`, `rauchtests/conftest.py`, `containertests/conftest.py`, `testumgebung/docker-compose.yml`, `dev/keycloak/dpv-realm.json`, `pruefen.sh`, `README.md` (Schritt 11), Tests in `tests/test_pruefports.py`, `tests/test_testumgebung_aufbau.py`, `rauchtests/test_pruefport.py` und `containertests/test_testumgebung_container.py`.

## 2026-10-26 · Ein Ort je Angabe, Ablauf einer Phase und Steuerungssession (#169)

**Entscheidung** (Sebastian; Klärung von #168 am 26.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/168#issuecomment-6410114588), [Szenarien in #169](https://github.com/sebivtt/dpv-participant-management/issues/169#issuecomment-6410122924)). Ergänzt den Eintrag zu #158 vom 25.10.2026, ändert ihn nicht:

1. **Ein Ort je Angabe:** Jede Angabe steht an genau einem Ort, alle anderen Stellen verweisen darauf. Was gilt: `docs/anforderungen.md` und `docs/rechtematrix.md`; warum: diese Datei; Phasen, Abschlusskriterien, Stunden: `docs/fahrplan.md`; Arbeitsregeln: `CLAUDE.md`; Handgriffe: die Skills; was ein Issue verlangt: sein Text (Kommentare sind nur Protokoll); ob geklärt: das Label `geklärt`; ob erledigt: das geschlossene Issue; Reihenfolge (nur Nummern) und Belege der Abschlusskriterien: das Phasen-Issue; was technisch zuerst da sein muss: die Abhängigkeiten auf GitHub. Eine Reihenfolge ohne technischen Grund steht nur im Phasen-Issue.
2. **Ablauf einer Phase:** Start mit Phasen-Issue, Bestandsaufnahme, Grundlagen zuerst, Reihenfolge und Abhängigkeiten, Prüfung der Planung durch eine zweite KI. Klären läuft voraus (Richtwert die nächsten drei Issues, in fachlich zusammenhängenden Gruppen; die nächste Gruppe spätestens in Klärung, wenn die Umsetzung der laufenden beginnt; grobe Entwürfe für neue Seiten etwa zwei Gruppen vorher). Neues während der Phase bekommt im selben Schritt Platz, Abhängigkeiten und Stunden aus dem Puffer, die Stunden mit Sebastians Zustimmung. Neuer Inhalt zu einem geklärten Issue kommt sofort in seinen Text, `geklärt` kommt ab, ein Kommentar nennt die Änderung. Abschluss: Belege, externes Review, Rückblick mit neuen Erfahrungen in `CLAUDE.md`, dann erst der „Stand“ im `README.md`.
3. **Steuerungssession:** liest, verteilt Aufträge, pflegt das Phasen-Issue und entscheidet nichts Fachliches. Sie gibt keine Zustimmung von Sebastian weiter; seine Freigaben stehen in seinen eigenen Worten im Issue oder Pull Request. Ein Auftrag ist nur der Link zum Issue mit dem Verweis auf `CLAUDE.md`. Sie wechselt bei 40 bis 50 % der Kontextanzeige an einem Punkt zwischen zwei Issues, nie mitten in einer Umsetzung, und schreibt vorher den Stand ins Phasen-Issue; 60 % ist die harte Grenze. Fasst Claude Code das Gespräch vorher automatisch zusammen, schreibt sie sofort den Stand und endet.
4. **Umsetzungs-Sessions:** eine frische Session je Issue, danach kein weiteres. Erreicht sie trotzdem rund 60 %, schreibt sie den Stand als Kommentar ins Issue, und eine neue Session macht mit genau diesem Issue weiter.
5. **Kurzform von `grill-me`:** für Issues mit höchstens einem neuen Punkt oder ohne fachliches Verhalten. Gelesen werden nur Issue, Abhängigkeiten und betroffene Dateien; Fragen, Zusammenfassung, Protokoll, Szenarien (wenn nötig) und Sebastians Okay bleiben. Die KI schlägt sie vor, Sebastian bestätigt; will er die volle Klärung, gilt die volle.
6. **„Szenarien vor Code“ nur noch an einem Ort:** Die Regeln dazu stehen nur noch in `CLAUDE.md` und in der Vorlage für Pull Requests. `grill-me` verweist darauf, statt sie zu wiederholen; sein Abschnitt „Danach“ ist nur noch ein Verweis. Der Satz „Aufträge an andere Sessions nennen den Schritt ausdrücklich“ aus dem Eintrag zu #158 (Punkt 3) entfällt, weil ein Auftrag nach Punkt 3 oben nur noch Link und Verweis enthält; `CLAUDE.md` hält die Umsetzung weiter an, wenn der Kommentar „Szenarien (Datum)“ fehlt, auch wenn der Auftrag den Schritt nicht nennt.

**Begründung:** Bei der Prüfung des Vorgehens in P2 am 26.10.2026 standen Abschlusskriterien, Stand „geklärt“ und Reihenfolge doppelt (in `docs/fahrplan.md`, #106, Labels und Abhängigkeiten) und widersprachen sich teils, etwa bei #99. Neuer Inhalt stand nur als Kommentar, Hinweise zeitweise nur im Auftrag der Steuerungssession, und `grill-me` wiederholte Regeln aus `CLAUDE.md`. Mit einem Ort je Angabe läuft nichts mehr auseinander, und jede Session muss weniger lesen; das spart auch Nutzungslimit. Den früheren Wechsel der Steuerungssession wollte Sebastian, um „immer genug Puffer zu lassen“.

**Technische Wahl** (KI): Der Skill heißt `phase-steuern`, die Vorlage `.github/ISSUE_TEMPLATE/phase.yml`. Der Test `tests/test_szenarien_vor_code.py` heißt jetzt `tests/test_arbeitsregeln.py` und prüft schlank: die Kernregeln in `CLAUDE.md`, dass jeder Skill auf `CLAUDE.md` verweist und keine Folge von zehn oder mehr Wörtern aus `CLAUDE.md` wörtlich übernimmt, und die Felder der Vorlagen. Bis zu neun gleiche Wörter in Folge sind erlaubt, damit kurze Verweise und feste Begriffe nicht stören. Ob sich eine Session an die Regeln hält, prüft kein Test.

**Umsetzung:** `CLAUDE.md` (neu „Ein Ort je Angabe“, „Ablauf einer Phase“, „Steuerungssession und Umsetzungs-Sessions“; „Verbindlich“ gekürzt; „Für Phasen und Vorgemerktes gilt“ aufgegangen in „Ablauf einer Phase“), `.claude/skills/grill-me/SKILL.md` (neu „Kurzform“, „Danach“ als Verweis), `.claude/skills/issue-anlegen/SKILL.md` (neu Abschnitt 5 „Laufende Phase“), `.claude/skills/phase-steuern/SKILL.md` (neu), `.github/ISSUE_TEMPLATE/phase.yml` (neu), `tests/test_arbeitsregeln.py`.

## 2026-10-25 · Abgleich mit Keycloak beim Login als Ausnahme vom „Lesen an der Stelle vorbei“ (#76)

**Entscheidung** (Sebastian; Zustimmung über die Steuerungssession bei der Nachprüfung von PR #166 am 25.10.2026): Die Liste der Stellen, an denen Personen- und Anmeldedaten direkt aus der Datenbank gelesen werden dürfen (Eintrag zu #90, „Lesen an der Stelle vorbei“), bekommt einen vierten Eintrag: `accounts/keycloak_abgleich.py`. Freigegeben ist nur diese Datei, bewusst nicht der ganze Login-Adapter `accounts/adapter.py`.

**Begründung:** Der Abgleich beim Login muss allauths Mail-Liste und den Benutzernamen in der Datenbank lesen und ändern. Er ändert nur das Konto, das sich gerade anmeldet, mit den Angaben aus Keycloak, zeigt nichts an und wird nur aus `accounts/adapter.py` aufgerufen. Das entspricht der bestehenden Ausnahme für die Regeln des Rollenmodells. Eine eigene kleine Datei hält die Ausnahme eng; der übrige Adapter bleibt unter der Aufsicht des Rundumtests.

**Technische Wahl** (KI, Umsetzung von Sebastians Entscheidung in #76 vom 22.10.2026):

- **Mail-Liste:** Bei jedem Login, auch dem ersten, steht in `account_emailaddress` genau ein Eintrag: die Mail aus Keycloak in genau dieser Schreibweise (allauth schriebe sie beim ersten Login sonst klein) und `email_verified` aus Keycloak. Ältere Einträge werden gelöscht. Dabei wird die eigene Kontozeile kurz gesperrt, damit gleichzeitige Logins derselben Person nacheinander laufen.
- **Benutzername:** Bei jedem Login aus Keycloak übernommen, zu lange Namen gekürzt. Vergeben heißt wie bei allauths erstem Login auch in anderer Groß- und Kleinschreibung; dann bleibt der alte Name, der Login gelingt, und ins Log kommt eine Zeile ohne Benutzernamen, Mail und Kontonummer. Das Tool sieht vorher nach, statt nur auf die Datenbank zu bauen, weil deren eigenes Log bei einem abgelehnten Speichern den Namen nennen würde.

**Umsetzung:** `accounts/keycloak_abgleich.py`, `accounts/adapter.py` (Aufrufe in `pre_social_login` und `save_user`), `tests/test_rundumtest.py` (Ausnahmeliste), `docs/rechtematrix.md` (Zeile `account.EmailAddress`), Tests in `tests/test_login_angleichen.py`.

## 2026-10-25 · Zielbild vor Gestaltung, und „Mein Profil“ nach Zielbild (#161)

**Entscheidung** (Sebastian; nach der Abnahme von PR #160 am 25.10.2026; Klärung von #161 am 25.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102089), [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403102282), [Nachklärung Kacheln](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403407168)):

1. **Ablauf „Zielbild vor Gestaltung“:** Entsteht eine Seite zum ersten Mal, baut die KI aus den bisherigen Erkenntnissen, der Musterseite und den anderen Seiten einen groben Entwurf als HTML-Datei mit erfundenen Daten. Sebastian entwickelt daraus mit ChatGPT einen fertigen Entwurf und spielt ihn als Zielbild ein. Erst dann entsteht die Seite. Bei „Mein Profil“ entfiel der grobe Entwurf, weil die Seite schon stand. Wie der Ablauf fest in `CLAUDE.md` und `grill-me` kommt, regelt #162.
2. **Ein Zielbild ist Orientierung, keine Anforderung:** Es gibt niemandem ein Recht und ändert keine Entscheidung. Es gehen vor: Rechtematrix, `docs/anforderungen.md`, diese Datei und `docs/gestaltung.md`. Gebaut wird nur, was das Tool speichert; Teile ohne Daten fehlen ganz. Wo die Seite abweicht, nennen der Pull Request und `docs/zielbilder/README.md` Stelle und Grund.
3. **„Mein Profil“ nach Zielbild:** Kopfzeile mit Profilkreis und Name (ohne Namen der Benutzername); Angaben als graue, gesperrte Felder mit Symbol und Schloss; Hinweis „Name und E-Mail-Adresse stammen aus deinem DPV-Konto …“ in einer blauen Fläche; „Deine Angaben“ nur für Vorleseprogramme. Die Mitgliedschaft steht in einer zart blauen Fläche, die Rollen als weiße Kacheln mit feinem Rand und blauem Streifen oben, weiter von klein nach groß. Jede Kachel zeigt klein die Rolle, groß die Organisation und darunter den Weg nach oben; Verbandsleitung, DPV-Veranstaltungsteam und Admin zeigen statt des Wegs einen festen Satz: Verbandsleitung „Leitung des Verbands“, DPV-Veranstaltungsteam „Veranstaltungen des Verbands“, Admin „Verwaltung des ganzen Tools“ (groß „DPV Anmeldetool“, weil die Rolle an keiner Organisation hängt). Die Texte „E-Mail-Adresse“ und „stammen aus“ ersetzen „Mail“ und „kommen aus“ aus dem Eintrag zu #96.
4. **Rand an den Rollen-Kacheln:** bewusste Ausnahme von „Flächen statt Rahmen“ (`docs/gestaltung.md`), nur für diese Kacheln.
5. **„Austreten“ bleibt auf „Mein Profil“** (#65), obwohl das Zielbild stattdessen „Organisation öffnen“ zeigt.

**Begründung:** „Mein Profil“ entstand ohne Zielbild und blieb schlicht. Mit einem Zielbild sieht Sebastian früh, wie eine Seite aussehen wird, und die KI baut nicht nach eigenem Geschmack. Weil ein Entwurf aus ChatGPT mehr zeigt, als geklärt ist, darf er keine Regel still ändern.

**Technische Wahl** (KI):

- **Ort und Form:** Zielbilder liegen unverändert unter `docs/zielbilder/` (für „Mein Profil“ `mein-profil.html`), daneben `README.md` mit Datum, Herkunft, Prüfsumme und Abweichungen. Unverändert, damit nachvollziehbar bleibt, was Sebastian vorgegeben hat; die Datei öffnet sich mit Doppelklick. Eine neue Fassung ersetzt die Datei, die alte bleibt in der Versionsgeschichte. Ein Test prüft Prüfsumme, erfundene Adressen und dass nichts von fremden Servern geladen wird. Das Tool selbst lädt Zielbilder nie; Skripte daraus werden nicht übernommen.
- **Bausteine:** Profilkreis mit Name, gesperrte Felder, Hinweisfläche, Flächen-Überschrift mit Symbol, Mitgliedschafts-Fläche und Rollen-Kacheln stehen auf der Musterseite und ersetzen die Bausteine „Angaben“ und „Rollen“ aus #96. Die Kacheln sind Listeneinträge, die Mitgliedschaft eine eigene Fläche, beide ohne eigene Überschriften. Die kleine Rollenmarke ist in den Kacheln zart blau hinterlegt (Sebastian, [Nachtrag](https://github.com/sebivtt/dpv-participant-management/issues/161#issuecomment-6403556335)). Was eine Kachel zeigt, stellt `core/views.py` (`_tile()`, feste Sätze in `ROLE_NOTES`) zusammen; Seite und Musterseite nutzen dafür denselben Baustein `core/templates/core/_rollenkachel.html`.

**Umsetzung:** `docs/zielbilder/`, `core/templates/core/profil.html`, `core/views.py` (Mitgliedschaft getrennt von den Rollen, Inhalt der Kacheln; Beispiel der Musterseite), `core/templates/core/muster.html`, `core/templates/core/_rollenkachel.html`, `core/templates/core/_symbole.svg` (Symbole „mail“ und „at“), `core/static/core/app.css`, Tests in `tests/test_mein_profil.py` und `rauchtests/test_rauchtest.py`.

## 2026-10-25 · „Mein Profil“ zum Ansehen, Grundregel des Profils und „Organisation“ statt „Einheit“ (#96)

**Entscheidung** (Sebastian; W1 in der [Bestandsaufnahme zu P2](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6342842432) am 22.10.2026, ergänzt bei der Klärung von #111 und #65; [Klärung von #96](https://github.com/sebivtt/dpv-participant-management/issues/96#issuecomment-6348627990) am 22.10.2026 mit [Nachtrag zu Frage 5](https://github.com/sebivtt/dpv-participant-management/issues/96#issuecomment-6348932400); [Nachklärung P2](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6351698512), Frage 7; [Szenarien vom 25.10.2026](https://github.com/sebivtt/dpv-participant-management/issues/96#issuecomment-6398658886)):

1. **W1, eigene Daten:** In P2 gibt es eine schlichte Seite „Mein Profil“ zum Ansehen: Vorname, Nachname, Benutzername und Mail, dazu die Mitgliedschaft und alle Rollen. Name und Mail kommen aus dem DPV-Konto; der Hinweis dazu steht ohne Link, bis der DPV-Admin sagt, ob die Kontoseite im Keycloak abgeschaltet ist und wer Name und Mail ändert. „Meine Anmeldungen“ und „Profil löschen“ (DSG-09) kommen später.
2. **Ergänzungen zu W1:** Zwei Bedienelemente kommen auf diese Seite, gebaut in eigenen Issues: den Fahrtennamen trägt die Person selbst ein (#111), und neben der Mitgliedschaft steht „Austreten“ (#65; wer austreten darf, regelt die Rechtematrix, EP-06). Sonst lässt sich dort in P2 nichts bearbeiten. Der Kasten „Dein Konto“ auf der Startseite entfällt; der Zugang zur Seite ist der Profilkreis (#13).
3. **Grundregel:** „Mein Profil“ zeigt alles, was das Tool über die Person speichert. Kommt später eine Angabe dazu (z. B. Adresse, Geburtsdatum, Gesundheitsangaben nach FRM-04), erscheint sie dort ebenfalls.
4. **„Organisation“ statt „Einheit“:** Texte für Nutzende sagen „Organisation“, nie „Einheit“ (z. B. „keiner Organisation zugeordnet“), weil „Einheit“ zu militärisch klingt. In Anforderungen, Issues und Code bleibt „Einheit“ der Fachbegriff (im Code `unit`). Ältere Texte für Nutzende werden angepasst, wenn ihre Seite ohnehin geändert wird.

**Begründung:** Personen sollen sehen, was das Tool über sie weiß (PER-01, ORG-05), ohne dass P2 eine eigene Bearbeitung von Stammdaten braucht. Ein fester Ort für die eigenen Daten hält die Startseite frei für das Dashboard (#28). Die Kontoseite des DPV-Keycloak zeigte am 22.10.2026 nur eine Fehlermeldung; ein Link dorthin führte ins Leere.

**Technische Wahl** (KI, mit der Klärung bestätigt):

- **Adresse ohne Kennung** (`/profil/`): Die Seite zeigt immer die angemeldete Person und liest nichts aus der Anfrage, auch keine angehängten Parameter, htmx-Kopfzeilen oder Formularfelder. Ein fremdes Profil ist über diese Seite auf keinem Weg erreichbar (EP-02).
- **Frisch gelesen:** Rollen und Organisationen liest die Seite bei jedem Aufruf über die zentrale Rechteprüfung (`Rights.own_roles()`); eine Änderung erscheint ohne neue Anmeldung. Name und Mail ändern sich erst mit dem nächsten Login.
- **Reihenfolge der Rollen:** Mitgliedschaft, dann Gruppen-, Stammes-, Ring- und Bundesleitung, Verbandsleitung, DPV-Veranstaltungsteam, Admin; dieselbe Rolle mehrmals nach dem Namen der Organisation. Darunter klein der Weg nach oben ohne den Verband (`Unit.names_above()`).
- **Fehlender Name:** derselbe Hinweis wie auf der Startseite, aus derselben Prüfung; an der leeren Stelle steht „nicht angegeben“. Namen nur aus Leerzeichen regelt #77 an dieser einen Stelle für beide Seiten.
- **Code-Name:** „Mein Profil“ heißt im Code `profile` (Adresse `profile`, Vorlage `core/profil.html`).

**Umsetzung:** `core/views.py`, `core/templates/core/profil.html`, `core/templates/core/start.html`, `config/urls.py`, `access/rights.py` (`own_roles()`), `units/models.py` (`names_above()`), `core/static/core/app.css` und `core/templates/core/muster.html` (Bausteine „Angaben“ und „Rollen“), `docs/rechtematrix.md` (EP-01, EP-02, EP-05 gebaut), Tests in `tests/test_mein_profil.py` und `rauchtests/test_rauchtest.py`.

## 2026-10-25 · Umsetzung nur mit vorher bestätigten Szenarien (#158)

**Entscheidung** (Sebastian; Klärung von #158 am 25.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/158#issuecomment-6398277636)):

1. **Szenarien vor dem ersten Test:** Die KI schlägt Szenarien vor, Sebastian entscheidet je Szenario. Vor dem ersten Test stehen sie als Kommentar „Szenarien (Datum)“ im Issue, mit seinen Entscheidungen. Fehlt der Kommentar, hält die KI an und legt ihm Szenarien vor, auch wenn der Auftrag den Schritt nicht nennt; ein Auftrag hebt ihn nie auf.
2. **Gesammelt beim Klären:** `grill-me` sammelt die Szenarien als Schritt vor dem Label `geklärt`. Fehlen sie trotzdem, holt die Umsetzung sie nach.
3. **Ausnahme nur durch die Klärung:** Ohne Szenarien geht nur ein Issue, für das die Klärung mit Sebastian festhält, dass es kein fachliches Verhalten hat (z. B. reine Doku, CI oder Arbeitsregeln). Fehlt diese Angabe, sind Szenarien nötig. Aufträge an andere Sessions nennen den Schritt ausdrücklich; weglassen dürfen sie ihn nur mit dieser Angabe, der Grund steht dann im Auftrag und im Pull Request.
4. **Im Pull Request:** Die Vorlage hat unter „Wie geprüft wurde“ eine Zeile „Szenarien“: Link zum Kommentar und Tests, die darüber hinaus dazugekommen sind, ohne Szenarien der Grund aus der Klärung.
5. **#8:** Die Szenarien zu #8 werden nicht nachgeholt; dafür gibt es kein eigenes Issue.

**Begründung:** Am 25.10.2026 fiel auf, dass bei #90, #64 und #8 keine Szenarien von Sebastian vorlagen. Die Aufträge der Steuerungssession nannten nur „prüfen, Tests, Code“, und nichts hielt die Umsetzung an. Die nachträglich aufgeschriebenen Szenarien zu #90 und #64 brachten acht Lücken zutage (#156). Liegt die Entscheidung über die Ausnahme bei der Klärung, kann sich keine Session selbst davon befreien.

**Technische Wahl** (KI): Ein Test prüft, dass die Regeln in `CLAUDE.md`, in der Vorlage für Pull Requests und in `grill-me` stehen, nach dem Vorbild des Tests zur Regel für den Neustart (#133). Ob sich eine KI daran hält, kann er nicht prüfen.

**Umsetzung:** `CLAUDE.md` („Ablauf je Aufgabe“, Schritt 3; „Für die Umsetzung gilt außerdem“; „Erfahrungen aus dem Vorgänger-Repo“), `.github/pull_request_template.md`, `.claude/skills/grill-me/SKILL.md` (Abschnitte 2, 5, 8 und „Danach“, bisherige Abschnitte 5 bis 7 jetzt 6 bis 8), `tests/test_szenarien_vor_code.py`.

## 2026-10-25 · Sitzung endet spätestens 12 Stunden nach dem Login (#8)

**Entscheidung** (Sebastian, Klärung von #8 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/8#issuecomment-6334870652), Frage 1). Ergänzt die Sitzungsdauer vom 21.10.2026 (Punkt 2), ersetzt sie nicht:

1. **Obergrenze:** Eine Sitzung endet wie bisher nach 2 Stunden ohne Klick und zusätzlich spätestens 12 Stunden nach dem Login, auch wenn die Person die ganze Zeit klickt. Danach führt der nächste Klick zur Login-Seite mit dem bestehenden Hinweis „Sitzung abgelaufen“.
2. **Gesperrte und gelöschte Keycloak-Konten:** Beim neuen Login entscheidet Keycloak. Ist das Konto dort gesperrt oder gelöscht, kommt die Person nicht mehr ins Tool. Eine in Keycloak gesperrte Person arbeitet so höchstens bis 12 Stunden nach ihrem letzten Login weiter.
3. **Nichts wird automatisch entfernt:** Konto, Rollen, Profil und Anmeldungen im Tool bleiben unverändert. Lange nicht genutzte Konten regelt #66.

**Technische Wahl** (KI):

- **Beide Werte an einer Stelle:** `SESSION_IDLE_MINUTES` und neu `SESSION_MAX_HOURS` stehen untereinander in `config/settings.py`.
- **Login-Zeitpunkt in der Sitzung:** Bei jedem Login merkt sich das Tool den Zeitpunkt in der Sitzung. Es nutzt dafür Djangos eigenes Signal zum Login, nicht das von allauth, damit kein Weg zum Login ihn auslässt. Abgelehnt: das Feld „letzter Login“ am Konto. Es gilt für alle Geräte zugleich; ein Login am Handy verlängerte sonst die Sitzung am Laptop.
- **Ein kleiner Baustein vor der Login-Pflicht** (`accounts.session.SessionMaxAgeMiddleware`): Ist der Login 12 Stunden oder länger her, meldet er im Tool ab. Ab da läuft alles wie nach 2 Stunden ohne Klick: dieselbe Weiterleitung zur Login-Seite, auch bei htmx-Anfragen, derselbe Hinweis. Eine Sitzung ohne gemerkten Zeitpunkt (etwa von vor dieser Änderung) gilt als zu alt und endet beim nächsten Klick.
- **Keine Nachfragen bei Keycloak:** Das Tool fragt Keycloak nie während der Sitzung, ob das Konto noch gilt. Abgelehnt: eine Prüfung alle 5 Minuten (mehr Aufwand, Keycloak wird zur Voraussetzung für jeden Klick) und eine Meldung von Keycloak ans Tool beim Sperren (Back-Channel-Logout; ungeprüft, mit der Obergrenze nicht nötig).
- **Login ohne Passwort:** Ob der neue Login das Passwort verlangt, entscheidet Keycloak nach seinen eigenen Einstellungen. In der Grundeinstellung von Keycloak 26.7.5, die auch die Testumgebung nutzt, endet die Anmeldung bei Keycloak nach 30 Minuten ohne Aktivität dort und spätestens nach 10 Stunden. Nach 12 Stunden im Tool fragt Keycloak dann meist wieder nach dem Passwort. Wie der Keycloak des DPV eingestellt ist, ist nicht bekannt.

**Begründung:** Protokoll der Klärung in #8. Bisher lief eine Sitzung ohne Ende, solange jemand klickte; eine in Keycloak gesperrte Person hätte so beliebig lange weiterarbeiten können. Die Obergrenze kostet kaum Aufwand und braucht keine Nachfragen bei Keycloak. Für den Ablauf danach gibt es keinen eigenen Weg, nur den bestehenden nach 2 Stunden ohne Klick; so verhält sich beides gleich, auch bei htmx.

**Umsetzung:** `config/settings.py`, `accounts/session.py`, `accounts/signals.py`, Tests in `tests/test_sitzung_obergrenze.py` (nachgestellter Keycloak, verstellte Uhr) und `tests/test_sitzung_obergrenze_echt.py` (Keycloak-Testumgebung mit erfundenen, frisch registrierten Konten, die der Test sperrt oder löscht).

## 2026-10-25 · „Nicht gefunden“ für fremde Einträge, „kein Zugriff“ für ganze Bereiche, zufällige Kennungen in Adressen (#64)

**Entscheidung** (Sebastian; Klärung von #21 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/21#issuecomment-6334628645), Frage 2; Klärung von #64 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/64#issuecomment-6344116521), und Nachklärung in [#106](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6351698512)). Auslegung von BER-01, gilt für alle späteren Seiten:

1. **Adresse mit Kennung eines Eintrags** (Person, Einheit, Anmeldung, Veranstaltung, auch Unterseiten, htmx-Anfragen und Formulare): Fehlt das Recht, erscheint dieselbe Seite „nicht gefunden“ (404) wie bei einem Eintrag, den es nicht gibt, mit derselben Antwort. Das gilt auch, wenn jemand den Eintrag sieht, aber die gewünschte Aktion nicht darf.
2. **Adresse ohne Kennung, also ein ganzer Bereich** (z. B. „Organisation“, #93, nur für Leitungen): Fehlt das Recht, erscheint „Dafür fehlt dir die Berechtigung.“ (403). Welche Bereiche es gibt, ist kein Geheimnis, der Code ist öffentlich.
3. **Recht verloren:** Wer ein Recht mitten in der Arbeit verliert, bekommt beim nächsten Klick dieselbe Antwort; eine eigene Meldung gibt es nicht (#90).
4. **Zufällige Kennungen:** Einträge stehen in Adressen mit einer zufälligen Kennung, nie mit einer laufenden Nummer, damit sich weder die Anzahl ablesen noch Adressen durchprobieren lassen. Für Nutzende werden Adressen nur länger.
5. **Ausnahme BER-06, ab P3:** Wer über den Anmeldelink zu einer Veranstaltung kommt, aber nicht zum Teilnahmekreis gehört, sieht den Hinweis aus BER-06. In P2 gibt es keine Anmeldelinks; die Ausnahme wird in #122 weitergeführt.

**Technische Wahl** (KI):

- **Kennung:** 20 Zeichen aus Kleinbuchstaben und den Ziffern 2 bis 7 (Alphabet von Base32), gezogen mit `secrets`, also 100 Bit Zufall. Bei einer Million Einträgen und einer Milliarde Versuchen pro Sekunde dauerte es im Mittel rund 40 Millionen Jahre bis zu einem Treffer. Abgelehnt: UUID (36 Zeichen mit Bindestrichen, ohne Vorteil) und `secrets.token_urlsafe` (Groß- und Kleinschreibung, Sonderzeichen).
- **Zusätzliches Feld statt neuer Primärschlüssel:** Konten und Einheiten bekommen ein eigenes, eindeutiges Feld, das beim Anlegen entsteht und das keine Seite und kein Befehl ändert (eine Sperre im Programm gibt es dafür nicht); die interne Nummer bleibt für Verweise zwischen Tabellen und in den Protokollen. Ein Umbau aller Verweise (Rollen, Login-Baustein, Protokolle) wäre viel riskanter und brächte nichts, weil die Nummer nie in einer Seite steht. Die Migration gibt vorhandenen Einträgen (Testumgebung) je eine eigene Kennung. Rollen bekommen eine Kennung erst, wenn eine Seite sie in eine Adresse schreibt.
- **Ein gemeinsamer Weg an der zentralen Stelle** (`access/rights.py`): `request.rights.entry(einträge, kennung, allowed=…)` und `request.rights.person(kennung)` ergeben ohne Recht immer 404; `request.rights.require_section(recht)` ergibt ohne Recht 403. Meldet eine Seite an einer Adresse mit Kennung trotzdem „kein Zugriff“, macht die Middleware „nicht gefunden“ daraus. Kennungen in falscher Form und alte Nummern ergeben „nicht gefunden“.
- **Adressen** schreiben Kennungen als `<key:…>`; Adressen mit Kennung in falscher Form gibt es dann gar nicht. Der Rundumtest wird rot, wenn eine Adresse mit Login etwas anderes nimmt, z. B. `<int:pk>`.
- **Gegenprobe Byte für Byte:** Die Tests vergleichen Statuscode, Inhalt und alle Kopfzeilen. Ausgenommen ist nur der Wert des Formularschutzes (CSRF) auf Seiten mit Formular, weil Django ihn bei jeder Antwort neu verschlüsselt; die Fehlerseiten haben kein Formular. Auch die Zeile im Log ist für fremde und fehlende Einträge gleich.
- **Begriffe im Code** (`CONTRIBUTING.md`, Abschnitt 1): Kennung (in Adressen) heißt `key`, Eintrag `entry`, ein ganzer Bereich des Tools `section` (nicht zu verwechseln mit dem Bereich einer Leitung, `area`).

**Umsetzung:** `access/keys.py`, `access/rights.py`, `accounts/models.py` und `units/models.py` (Feld `key`), Migrationen `accounts/migrations/0002_key.py` und `units/migrations/0003_key.py`, `config/urls.py`, `units/management/common.py` (Hilfsname umbenannt), `docs/rechtematrix.md` (Lesehilfe, Tabellenliste bei den Konten), Tests in `tests/test_nicht_gefunden.py`, `tests/test_rechtepruefung.py`, `tests/test_rundumtest.py`, `tests/test_rechte_ohne_seite.py` und `tests/urls.py`.

## 2026-10-25 · Zentrale Rechteprüfung (#90): Grundstock, Markierung jeder Adresse, Begriffe im Code

**Entscheidung** (Sebastian; Klärung von #90 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/90#issuecomment-6344029090), und Nachklärung am 25.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/90#issuecomment-6394863197)):

1. **Grundstock:** Die zentrale Rechteprüfung (`access/rights.py`) enthält mit #90 die Regeln zu Personen mit Konto, Einheiten und Leitungen. Das sind BER-01, Gründe 1 bis 3, Bereich, Kette nach oben, Leitungspfad, einspringende Leitung und „Leitung der eigenen Einheit einer Person“. Die übrigen Gründe und die einzelnen Aktionen bauen die späteren Issues an derselben Stelle ein, keines baut eine eigene Prüfung.
2. **Hinweis zum Einspringen:** Ob eine Leitung im Tool sieht, wo sie gerade einspringt, wird in #93 geklärt.
3. **Gesperrte Leitung** (Auslegung von ROL-02; Sebastian beim Umsetzen, [Kommentar](https://github.com/sebivtt/dpv-participant-management/issues/90#issuecomment-6395708845)): Eine im Tool gesperrte Leitung zählt nicht als „Leitung mit Konto“; die Leitung darüber springt ein. Sonst hätte in der Einheit niemand Rechte.

**Technische Wahl** (KI, von Sebastian in der Nachklärung bestätigt):

- **Einmal pro Anfrage:** Jede Anfrage bekommt ein eigenes Objekt `request.rights`. Es lädt Rollen, Einheiten und „welche Einheit hat eine Leitung“ beim ersten Bedarf, je mit einer Abfrage, und wird mit der Anfrage verworfen. Einen Zwischenspeicher über Anfragen hinweg gibt es nicht. Ändert sich eine Rolle während derselben Anfrage, wirkt das erst beim nächsten Klick.
- **Leere Werte ergeben „verboten“:** Das gilt ohne Login, für ein gesperrtes oder nicht gespeichertes Konto, ohne Mitgliedschaft, für die Rolle Admin ohne Einheit und am Verband, der nie zu Bereich oder Kette gehört. Eine Kennung, die keine Zahl ist, ergibt „nicht gefunden“.
- **Leitungen nur mit Name und Rolle:** Die Liste der sichtbaren Leitungen gibt nur Kennung, Vor- und Nachname, Rolle und Einheit heraus, nie die Mail (#136, B2). So kann keine Seite versehentlich mehr zeigen.
- **Markierung jeder Adresse** (`access/addresses.py`): `@checks_rights("PK-01", …)` mit Kennungen der Rechtematrix oder `@without_personal_data("Begründung")`. Fehlt sie, ist sie leer oder stehen beide an einer Adresse, wird der Rundumtest rot. Eine Kennung, die es in der Matrix nicht gibt, ebenso.
- **Lesen an der Stelle vorbei:** Ein Test durchsucht jeden Python-Ordner des Tools, auch spätere, nach den üblichen Wegen, Personendaten selbst zu lesen. Das betrifft Konten, Rollen, beide Protokolle, Sitzungen und die Daten des Logins. Gesucht wird nach `Modell.objects`, `.roles`, Abfragen über Rollen oder Konten, auch über mehrere Stufen (`parent__roles__user`, `prefetch_related("roles")`), und nach rohem SQL. Erlaubt ist das nur in der zentralen Stelle, in den Regeln des Rollenmodells und im Befehl für Admins auf dem Server. Der Test erkennt nicht jeden denkbaren Weg, etwa kein umbenanntes Modell (`import User as U`); den Rest prüft die unabhängige Prüfung.
- **Verbote ohne Seite** (EP-09, RO-19, PR-01, PR-03, TD-01): Ein Test ruft jede Adresse lesend, mit htmx und mit einem manipulierten Formular auf. Er tut das als Mitglied, Leitung, Verbandsleitung, Admin, Konto ohne Zuordnung und als Person mit vielen Rollen zugleich. Danach muss die Datenbank unverändert sein, und keine Antwort darf zeigen, was niemand im Tool sieht. Neue Adressen prüft er mit.
- **Begriffe im Code** (`CONTRIBUTING.md`, Abschnitt 1): Bereich heißt `area`, Kette nach oben `chain`, einspringen `covers`, Leitung einer Einheit (selbst oder einspringend) `leads_unit`, Leitungspfad `on_lead_path`, die Rechte einer Anfrage `rights`.
- **Testmuster aus dem alten Repo** (sebivtt/scout-participant-management, Stand 9df4513):
  - Aus `backend/tests/test_zugriffsschutz.py` übernommen: das Muster „nach dem verbotenen Versuch steht in der Datenbank noch dasselbe“. Nicht übernommen ist der Code, weil er an Veranstaltungen und Zusatzfeldern hing, die es hier noch nicht gibt. Ebenfalls nicht übernommen: „403, 404 oder 405“ als erlaubte Antworten, weil hier nach #64 genau „nicht gefunden“ gilt.
  - Aus `backend/tests/test_abfragen.py` übernommen ist schon seit P1 der Wachstumstest (`tests/query_limit.py`). Nicht übernommen: die Toleranz von zwei Abfragen und die Markierung bekannter N+1-Fehler mit Messwert, weil der Wachstumstest streng bleibt (Eintrag vom 24.10.2026) und es keine bekannten Fehler gibt.

**Umsetzung:** `access/rights.py`, `access/addresses.py`, `config/settings.py` (Middleware), Markierungen in `accounts/views.py` und `core/views.py`, `docs/rechtematrix.md` (EP-09, RO-19, PR-01, PR-03, TD-01 gebaut), Tests in `tests/test_rechtepruefung.py`, `tests/test_rechte_ohne_seite.py` und `tests/test_rundumtest.py`.

## 2026-10-25 · Hängende Browser-Installation auf GitHub abfangen; Neustart ohne Rückfrage (#133)

**Entscheidung** (Sebastian; Klärung von #133 am 23.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/133#issuecomment-6366796217)):

1. **Abfangen statt Ursache beseitigen:** Der Schritt „Browser für den Rauchtest installieren“ in der Prüfung auf GitHub hat je Versuch ein Zeitlimit von 10 Minuten und höchstens drei Versuche. Die Browser kommen aus dem Zwischenspeicher von GitHub, solange die Playwright-Fassung aus `uv.lock` gleich ist. Das spart nur das Herunterladen der Browser; die Systempakete, bei denen es hing, kommen weiter bei jedem Lauf vom Ubuntu-Paketserver. Scheitern alle Versuche, ist der Lauf rot und meldet, dass es an der Browser-Installation liegt und ein Neustart meist hilft. Die Prüfungen selbst und das Zeitlimit des ganzen Laufs (35 Minuten) bleiben gleich. Abgelehnt: das fertige Playwright-Abbild von Microsoft (großer Umbau, 2 GB von einem anderen fremden Server) und ein eigener Paketserver.
2. **Neustart ohne Rückfrage** (gilt über #133 hinaus): Ist ein Lauf nur an der Browser-Installation gescheitert, ist kein einziger Test gelaufen und nennt die Meldung klar die Browser-Installation, darf eine KI-Sitzung den Lauf einmal pro Stand ohne Rückfrage neu starten. Scheitert auch der Neustart, fragt sie Sebastian. Der Pull Request nennt den Neustart.

**Technische Wahl** (KI): drei einzelne Schritte statt einer Schleife, damit GitHub jeden Versuch mit eigenem Zeitlimit sichtbar zeigt; Zwischenspeicher mit `actions/cache` von GitHub, wie die anderen fremden Bausteine auf einen Commit festgelegt. Ein Test prüft, dass Zeitlimit, Wiederholung und Zwischenspeicher in `ci.yml` stehen.

**Begründung:** Am 23.10.2026 hing der Schritt in PR #132 und PR #135, weil der Ubuntu-Paketserver langsam war; der Lauf brach jeweils erst nach 35 Minuten ab, der Neustart war grün. Ein Neustart ändert nichts am Code und übernimmt nichts.

**Umsetzung:** `.github/workflows/ci.yml`, `tests/test_pruefung_auf_github.py`, `CLAUDE.md` („Ablauf je Aufgabe“, Schritt 6).

## 2026-10-25 · Folgekorrekturen nach PR #135 (#150): Kette nach oben, Tabelle zu BER-01, „Kreis“

**Entscheidung** (Sebastian; Klärung von #150 am 25.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/150#issuecomment-6394528633)). Die Einträge vom 24.10.2026 bleiben stehen; dieser legt nur fest, was dort mehrdeutig oder noch nicht nachgetragen war.

1. **Kette nach oben** (C3): Sie beginnt bei der Einheit der eigenen Mitgliedschaft und, bei einer Leitung, außerdem bei jeder Einheit, die sie leitet, jeweils bis zum Bund. Beispiel: Berta ist Mitglied des Bundes und Stammesleitung von Walhall; sie sieht Name, Fahrtenname und Rolle der Ringleitung über Walhall und der Bundesleitung (RO-01). Für Mitglieder ohne Leitungsrolle bleibt es bei der Mitgliedschaft (RO-02). Grund: Eine Leitung braucht die Leitung über der Einheit, die sie leitet; als Mitglied sieht sie nicht weniger als andere Mitglieder.
2. **Tabelle unter der Einleitung zu BER-01:** Bei allen Leitungen und der Verbandsleitung steht in der Spalte „Personen fremder Einheiten“ „nein (außer BER-01, Grund 3 und 4)“. Beim DPV-Veranstaltungsteam bleibt „nein“: Eine Ausnahme wäre dort ein neues Recht und widerspräche dem Eintrag vom 23.10.2026 zu #87, Nr. 5, und RO-07. Die Spalte „Veranstaltungen“ nennt in jeder Zeile außer Admin „Veranstaltungen, in deren Teilnahmekreis sie sind (BER-04), und geleitete Veranstaltungen“.
3. **„Kreis“ und Kreise nur mit Zuordnung** (Eintrag vom 24.10.2026, Nr. 4 und 10): „Eigener Kreis“ heißt in den Anforderungen jetzt überall „Kreis“. GRP-01 und der Einleitungssatz zu den Kreisen sagen „Jede Person mit Zuordnung (BER-03)“. Gebaut werden die Kreise weiter mit #141.
4. **ORG-01** bekommt den Vermerk, dass bis zur Seite für Bünde (#107) ein Admin weitere Bünde auf Bitte der Verbandsleitung anlegt (EH-22).
5. **BER-05** bleibt unverändert bis auf das Wort „Kreis“. Die Regel für Mails klärt #151 (P5).

**Ohne neue Entscheidung** (Vorschläge der KI, von Sebastian bestätigt): Glossar-Eintrag „Kette nach oben“; Vermerk „ändert sich ab P3“ bei PK-16 nach ROL-01 und #136, Teil 3, Frage 5; Klarstellung bei EH-02, dass Mitglieder im eigenen Bund weiter alle Einheiten sehen, auch die Gruppen; bei EH-25 schaltet ab #107 die Bundesleitung „hat Ringe“ selbst aus (ROL-03). Zum Eintrag vom 24.10.2026, Nr. 1 kommt kein Zusatz: Nr. 3 gibt der einspringenden Leitung alle Rechte einer Leitung, auch Entfernen und endgültiges Löschen, und PK-21 und VP-09 nennen sie.

**Umsetzung:** `docs/anforderungen.md` (Einleitungssatz „Organisationsstruktur, Personen und Rollen“, ORG-01, ORG-03, Tabelle unter der Einleitung zu BER-01, BER-04, BER-05, Beispiel Vorbereitungstreffen, TEAM-03, Abschnitt „Kreise“ mit GRP-01, Glossar), `docs/rechtematrix.md` (Einleitung, Kette nach oben, RO-01, PK-16, EH-02, EH-25), Tests in `tests/test_rechtematrix.py`. Neues Issue: #151.

## 2026-10-24 · Rechte nach dem externen Review der Rechtematrix (#136): elf Anforderungen geändert, dazu Folgeänderungen

**Entscheidung** (Sebastian; Klärung in #136 am 24.10.2026, Protokolle [Teil 1](https://github.com/sebivtt/dpv-participant-management/issues/136#issuecomment-6383778907), [Teil 2](https://github.com/sebivtt/dpv-participant-management/issues/136#issuecomment-6384078749), [Teil 3](https://github.com/sebivtt/dpv-participant-management/issues/136#issuecomment-6386790510) und [Nachtrag](https://github.com/sebivtt/dpv-participant-management/issues/136#issuecomment-6386910794)). Sie ändert, soweit unten genannt, die Einträge vom 23.10.2026 zu #87 (Nr. 6), #88 (Nr. 2) und #89 (Nr. 3 und 5) sowie die Klärungen in #9, #65, #93, #94, #95, #100, #117 und #118; die alten Einträge bleiben stehen.

1. **Reichweite** (Grundsatz 1): Es gibt keine pauschale Vererbung nach unten; jedes Recht hat seine eigene Reichweite. Leitungen benennen Leitungen in allen Einheiten unter ihrer eigenen (ROL-02). Mitglieder und verwaltete Personen ordnet jede Leitung nur ihrer eigenen Einheit zu und verteilt sie nur eine Ebene tiefer. Personen sehen gilt weiter nach BER-01. Entfernen und endgültig löschen dürfen nur die Leitungen der eigenen Einheit der Person (Teil 3, Frage 1; Teil 2 zu VP-09).
2. **Keine Selbstvergabe** (Grundsatz 2): Niemand gibt sich selbst eine Rolle, auch nicht die Verbandsleitung als Bundesleitung; die eigene Rolle niederlegen darf jede Person (ROL-02, ROL-03).
3. **Einheiten ohne Leitung** (Grundsatz 4): Hat eine Einheit keine Leitung mit Konto, hat die Leitung direkt darüber dort alle Rechte einer Leitung, höchstens bis zur Bundesleitung, nie die Verbandsleitung. Das wird berechnet, nicht als Rolle gespeichert (ROL-02). Eine kommissarische Leitung außerhalb des eigenen Pfads ist vorgemerkt (#138).
4. **Zuordnung** (Grundsatz 5, Teil 3, Frage 8): Alles rund um Veranstaltungen und Kreise braucht eine Zuordnung: Mitglied einer Gruppe, eines Stammes, eines Rings oder eines Bundes, oder Verbandsleitung oder DPV-Veranstaltungsteam (BER-03). In P2 gilt davon nur das Anlegen einer Veranstaltung (#100). **Was ein Konto ohne Zuordnung darf, steht nur in der Rechtematrix**, damit neue Module nicht an zwei Stellen nachgetragen werden müssen; bei BER-01 bleibt die geschlossene Liste, weil es dort um Personendaten geht.
5. **Wer welche Leitungen sieht** (B2, B3): Mitglieder sehen die Leitungen auf ihrer Kette nach oben (eigene Einheit und darüber bis zum Bund). Wer die Ansicht „Leitungen“ sieht, sieht Name, Fahrtenname und Rolle; die Mail nur, wer die Person nach BER-01 ohnehin sieht. Das gilt auch für angezeigte Leitungsrollen verwalteter Personen (BER-01, Grund 3).
6. **Konten finden** (C2, C3, Frage 15): Die Namenssuche der Bundesleitung nach Konten ohne Zuordnung entfällt. Konten findet man über die genaue Mail oder den Benutzernamen, höchstens 20 Suchen je Person und Stunde (#93, P2). Das Protokoll der Kontosuchen ist vorgemerkt (#144, spätestens P6).
7. **Austritt und Entfernen** (F2.4, Teil 3 zu ROL-01, Nachtrag Nr. 4): Austreten geht jederzeit; die Person wählt die Ebene und wird Einzelmitglied der Ebene darüber. Es enden die Leitungsrollen in der verlassenen Einheit und darunter sowie alle, die danach nicht mehr auf dem Leitungspfad liegen. Das Tool zeigt sie vorher und führt erst nach Bestätigung aus. Bestehende Anmeldungen bleiben. Das ändert die Ablehnung „erst die Rollen abgeben“ aus #89; der Code folgt mit #65.
8. **Struktur** (F2.8, Teil 3, Fragen 28 und zu ORG-06): Die Verbandsleitung legt Bünde an und benennt sie um (#107). Die Bundesleitung benennt ihren Bund um und schaltet „hat Ringe“ ein (mit #95, P2). Ausgeschaltet wird „hat Ringe“ in einem Schritt; bis zur Seite für Bünde (#107) tut das ein Admin per Befehl auf Bitte der Bundesleitung (#95). „Ausschalten nur ohne Ringe“ (Eintrag zu #88, Nr. 2) entfällt damit; „Ring ist Pflicht“ bleibt, solange ein Bund Ringe hat. Umbenennen darf jede Leitung ihre Einheit und alle darunter.
9. **Ab P3** (Teil 3, Fragen 2 bis 5): Beitrittsanfragen kommen mit #140. Dafür sieht ein Konto ohne Zuordnung die Namen der Bünde, Ringe und Stämme, ohne Gruppen und ohne Leitungsstatus; für Mitglieder gilt das über die Bundesgrenze hinaus. Ob eine Einheit gerade eine Leitung hat, sehen nur Mitglieder für die Einheiten ihres Bundes. In P2 bleibt das Sehen von Einheiten wie bisher.
10. **Begriff „Kreis“** (Teil 3, Frage 8): „Kreis“ ist der Begriff für die „eigenen Kreise“ aus GRP-01, auch für die „Teams“ aus Sebastians Konzept. „Veranstaltungsteam“ und „DPV-Veranstaltungsteam“ bleiben davon getrennt. Wer einen Kreis verwaltet, heißt „Verwaltende“.
11. **Leitungsrollen enden nur, wenn die Person selbst geht oder ausdrücklich entfernt wird** (Sebastian, 24.10.2026, beim Umsetzen in PR #135). Läge eine Leitungsrolle nach dem Verschieben eines Mitglieds nicht mehr auf seinem Leitungspfad, lehnt das Tool ab wie bisher (#89); die Meldung nennt die Rolle und weist darauf hin, dass sie zuerst beendet werden kann (ROL-02). Das Löschen einer Einheit und das Ausschalten von „hat Ringe“ nach ORG-06 bleiben davon unberührt (Abgrenzung der KI). Grund: Austritt, Wechsel per Anfrage und Entfernen sind bewusste Entscheidungen zu gehen; Verschieben ist ein organisatorischer Schritt, bei dem eine endende Rolle in einer anderen Einheit eine unbeabsichtigte Nebenwirkung wäre (PK-25).
12. **Angezeigte Leitungsrollen verwalteter Personen** (Sebastian, 24.10.2026, beim Umsetzen in PR #135): Wer Leitungen benennen darf (ROL-02), trägt auch angezeigte Leitungsrollen ein. Die Anzeige gibt weiter keine Rechte, und die Einwilligung nach #98 und #99 gilt unabhängig davon, wer einträgt (VP-14). Die Verbandsleitung trägt keine angezeigten Rollen ein, weil sie die verwaltete Person selbst nicht sieht (ROL-03, VP-06); Name, Fahrtenname und Rolle einer angezeigten Bundesleitung sieht sie nach BER-01, Grund 3 (RO-09). Präzisiert von Sebastian nach der Prüfung von PR #135.
13. **Angezeigte Leitungsrollen in BER-01, Grund 3** (Sebastian, 24.10.2026, nach der Prüfung von PR #135): Der Zusatz zu angezeigten Leitungsrollen verwalteter Personen steht am Ende von Grund 3 und gilt für alle Teile, auch für die Verbandsleitung (RO-05, RO-09).
14. **Die Rolle Admin legt man nicht im Tool nieder** (Sebastian, 24.10.2026, nach der Prüfung von PR #135): ROL-02 erlaubt das Niederlegen der eigenen Rolle „außer der Rolle Admin, RO-19“; bis ADM-01 geht das nur per Befehl auf dem Server.
15. **Löschen einer Einheit** (Sebastian, 24.10.2026, nach der Prüfung von PR #135): ORG-07 folgt ORG-06. Personen mit Account und verwaltete Personen kommen zur Ebene darüber; es enden nur die Leitungsrollen in dieser Einheit. „Wahlweise löschen“ entfällt; wer verwaltete Personen löschen will, tut das vorher einzeln (VP-09). „Untereinheiten“ fällt aus der Zusammenfassung weg, weil nur Einheiten ohne Einheiten darunter gelöscht werden.
16. **Veranstaltungsleitung nur mit Zuordnung** (Sebastian, 24.10.2026, nach der Prüfung von PR #135): TEAM-01 folgt BER-03; als weitere Veranstaltungsleitung wird nur hinzugefügt, wer eine Zuordnung hat.

**Geänderte Anforderungen** in `docs/anforderungen.md`, Wortlaut aus Teil 3, von Sebastian bestätigt; ORG-07, TEAM-01 und die Ergänzungen zu ROL-02 und BER-01 nach der Prüfung von PR #135 (Nr. 13 bis 16):

- **ROL-01:** Leitungsrollen nur auf dem Leitungspfad; Austritt jederzeit mit Wahl der Ebene; Entfernen wirkt eine Ebene nach oben; welche Rollen dabei enden; Anmeldungen bleiben.
- **ROL-02:** Benennen in allen Einheiten unter der eigenen, nur auf dem Leitungspfad; keine Selbstvergabe; die eigene Rolle niederlegen darf jede Person, außer der Rolle Admin; Einspringen bis höchstens zur Bundesleitung.
- **ROL-03:** Die Verbandsleitung legt Bünde an und benennt sie um, gibt sich selbst keine Rolle, springt nie ein; Ausnahmen nach BER-01, Grund 3 und 4.
- **ORG-01:** Weitere Bünde legt die Verbandsleitung an; Ringe „nur in Bünden mit Ringen, derzeit DPBM Mosaik“; Einzelmitglieder direkt in Bund, Ring oder Stamm.
- **ORG-06:** Wer welche Einheiten anlegt, löscht und umbenennt; „hat Ringe“ einschalten und in einem Schritt ausschalten.
- **ORG-07:** Beim Löschen einer Einheit kommen alle Personen zur Ebene darüber; kein „wahlweise löschen“.
- **BER-01:** geschlossene Liste von sieben Gründen, Personendaten zu sehen; Spalte „Fremde Einheiten“ heißt jetzt „Personen fremder Einheiten“; angezeigte Leitungsrollen verwalteter Personen gelten für alle Teile von Grund 3.
- **BER-03:** Veranstaltungen nur mit Zuordnung.
- **BER-04:** Man lädt ein, wozu man gehört; Kreise auch für Bundesleitungen, Verbandsleitung und DPV-Veranstaltungsteam nur, wenn sie darin sind.
- **ADM-03:** zusätzlich die Protokolle der Strukturänderungen und der Kontosuchen; was das Protokoll der Kontosuchen nennt.
- **TEAM-01:** Weitere Veranstaltungsleitungen nur mit Zuordnung (BER-03).

**Folgeänderungen ohne neue Entscheidung** (Sebastian, 24.10.2026, vor dem Übernehmen von PR #135): Der Einleitungssatz zu BER-01 nennt die Gründe nach BER-01; die Verbandsleitung sieht als Verbandsleitung Personendaten nur nach BER-01, Grund 3, 4 und 7, Admins nur für Support (Grund 6) und ab P8 die Protokolle (Grund 7). ROL-05: Die Rolle gilt als Zuordnung (BER-03). ROL-05 und das Glossar sagen statt „jeden Teilnahmekreis wählen“ jetzt „bundesübergreifende Einheiten, Rollen und ‚alle‘ wählen; für Kreise gilt BER-04“. Die Zielgruppe nennt Ringe wie ORG-01 „nur in Bünden mit Ringen, derzeit DPBM Mosaik“.

**Begründung** (Sebastian, aus den Protokollen): eine einfache Regel statt Einzelfällen; Schutz vor unbekannten Erwachsenen bei Veranstaltungen mit Kindern (Grundsatz 5); niemand verschafft sich selbst Rechte (Grundsatz 2); Einheiten ohne Leitung bleiben handlungsfähig, ohne dass die Verbandsleitung Personendaten bekommt (Grundsatz 4, ROL-03); Mengenbegrenzung und Protokoll, damit die Suche über Mail und Benutzernamen nicht zum Durchprobieren taugt (Frage 15).

**Umsetzung:** `docs/anforderungen.md` (die elf Anforderungen, die Spaltenüberschrift, der Einleitungssatz zu BER-01, ROL-05, die Zielgruppe und das Glossar), `docs/rechtematrix.md` (PR #135). Code in `roles/` und `units/` folgt mit #65 und #95; der Fahrplan mit #113. Neue Issues: #137 bis #149, die meisten vorgemerkt.

## 2026-10-24 · Rechtematrix nach dem Review korrigiert (#136): Begriffe, Kennungen, technische Vorschläge

**Entscheidung** (Sebastian, Teil 3, Frage 14): Die Korrekturen A1 bis A17 am Text der Matrix kommen alle in PR #135, angepasst an die Entscheidungen oben. A3 entfällt mit der Namenssuche (C2). Was für P3 entschieden ist (EH-03, EH-05, EH-07, Beitrittsanfrage), bekommt nur einen Vermerk „ändert sich ab P3 (#136)“; die Zeilen kommen mit den Daten (Entscheidung vom 23.10.2026, Nr. 2).

**Technische Wahl** (KI):

- **Zwei Begriffe statt „Pfad“** (A1): „Kette nach oben“ für das Sehen von Leitungen, „Leitungspfad (#89)“ dafür, wo jemand Leitung sein darf. Ein Test wird rot, wenn „Pfad“ in der Matrix anders vorkommt.
- **Kennungen bleiben:** Entfällt ein Recht, wird seine Zeile zum Verbot und behält ihre Kennung (RO-12, RO-16, PK-11), weil Issues und Tests sie nennen. Neue Zeilen bekommen die nächste freie Nummer. Ein Test prüft, dass jede Kennung des ersten Entwurfs bleibt, und ein weiterer, dass jeder Verweis auf eine Zeile oder Anforderung auf etwas zeigt, das es gibt.
- **„Gebaut“ heißt: alle Fälle** (A17): Nennt eine Zeile mehrere Rollen, Daten oder Aktionen, prüft je Fall ein eigener Test. Das kostet in #90 mehr Tests.
- **Technische Vorschläge aus Sebastians Konzept** (F4, Teil 3, Frage 12): Die Rechteprüfung bleibt in Django (#90), mit einer Stelle, die für jedes Recht und Objekt gefragt wird; ein Umbau in Datenbankfunktionen kostete geschätzt 20 bis 30 Stunden (Annahme) und gebauten Code. `ltree` erst messen (#104). Absicherung gegen leere Werte und Negativtests je Recht (#90). Verschlüsselung der Gesundheitsangaben in P4 prüfen (#102, #121). Gast-Links mit 256 Bit Zufall (#84). Kein Rechte-Zwischenspeicher über Anfragen hinweg; Rollen und Bereiche werden einmal pro Anfrage geladen (Ergänzung von Sebastian, #90). Für die Zahl der Abfragen bleibt der Wachstumstest (1 gegen 10 Einträge, `tests/query_limit.py`) statt fester Zahlen, weil feste Zahlen bei jeder harmlosen Änderung rot würden.

**Umsetzung:** `docs/rechtematrix.md`, `tests/rechtematrix.py`, `tests/test_rechtematrix.py`.

## 2026-10-23 · Rechtematrix (#87): Form, Regel „neue Daten → sofort Rechte klären“, Login-Tabellen, DPV-Veranstaltungsteam

**Entscheidung** (Sebastian; Klärung von #87 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/87#issuecomment-6343846888); [Fragen bei der Umsetzung](https://github.com/sebivtt/dpv-participant-management/issues/87#issuecomment-6365683098) und [Szenarien](https://github.com/sebivtt/dpv-participant-management/issues/87#issuecomment-6365733029) am 23.10.2026):

1. **Form:** Die Rechtematrix steht als `docs/rechtematrix.md` im Repo und wird dauerhaft fortgeschrieben. Sie hat ein Inhaltsverzeichnis und einen Abschnitt je Art von Daten. Jede Zeile nennt Kennung, wer, welche Daten, welche Aktion, erlaubt oder verboten, die Quelle und den Stand („geplant“ mit dem bauenden Issue oder „gebaut“ mit den Tests für den erlaubten und den verbotenen Fall). Der erste Entwurf für P2 kommt mit #87; mit dem Übernehmen ist er freigegeben, danach beginnt #90.
2. **Neue Daten → sofort Rechte klären:** Wer neue Daten ins Tool bringt, ergänzt im selben Pull Request ihre Zeilen: wer sie sehen, anlegen, bearbeiten und löschen bzw. verwalten darf, erlaubt und verboten. Die Regel steht in `CONTRIBUTING.md` (Abschnitt 4), im Skill `grill-me` und in der Vorlage für Pull Requests. Ein automatischer Test wird rot, wenn eine Tabelle der Datenbank in der Matrix fehlt.
3. **Umfang des ersten Pull Requests** (F1): Matrix und Regel zusammen, ohne Code für die Rechteprüfung. „Nur die Matrix“ im Issue heißt: ohne Rechte-Code.
4. **Tabellen des Logins** (F2): Sitzungen, die Verknüpfung mit dem DPV-Konto samt dem, was Keycloak mitschickt, die Mail-Liste des Login-Bausteins und Djangos technische Listen sieht und ändert niemand im Tool, auch Admins nicht, auch nicht im Support-Zugang. Nur der Login selbst schreibt sie. Was Leitungen von Personen mit Konto sehen, regelt allein der Abschnitt „Personen mit Konto“.
5. **DPV-Veranstaltungsteam** (F3): Es sieht die Namen aller Bünde wie die Verbandsleitung, aber nicht, wer sie leitet. Sebastian wollte zunächst „alles wie die Verbandsleitung“; die KI hat darauf hingewiesen, dass die Namen der Bundesleitungen Personendaten sind und ROL-05 der Rolle keinen weiteren Zugriff darauf gibt. ROL-05 bleibt unverändert.
6. **Rechte ohne Seite in P2** (F4): Mitglieder dürfen die Namen der Einheiten ihres Bundes und die Leitungen auf ihrem Pfad sehen; das Veranstaltungsteam die Namen der Bünde. In P2 baut keine Seite das für sie. Die Zeilen stehen als „erlaubt“ mit Stand „geplant“; die Anzeige ist in #134 vorgemerkt (P3, Soll).

**Technische Wahl** (KI):

- **Kennungen:** zwei Großbuchstaben für den Abschnitt oder einen Teil davon (VA und AN im Abschnitt „Veranstaltungen und Anmeldungen“), ein Bindestrich und eine zweistellige Nummer, z. B. `VP-02`. Eine Kennung kommt nur einmal vor und hat genau diese Form; Tests prüfen beides. Die Tabellenliste darf nur vorhandene Abschnitte nennen.
- **Tests nennen ihre Zeile über eine Markierung** (`@pytest.mark.rechtematrix("PR-02")`), nicht über ihren Namen. So bleiben vorhandene Tests unverändert; die vier Protokolltests je aus `tests/test_rollen_protokoll.py` und `tests/test_einheiten_protokoll.py` bekommen nur diese Markierung, ihre Regeln blieben gleich.
- **Was „erlaubt“ und „verboten“ prüfen:** Eine Zeile „erlaubt“ prüft als verbotenen Fall den nächsten Nachbarn (andere Einheit, Ebene darunter); eine Zeile „verboten“ prüft als erlaubten Fall die Gegenprobe, dass der vorgesehene Weg weiter geht.
- **Automatische Prüfung schon jetzt:** `tests/test_rechtematrix.py` läuft mit `./pruefen.sh` und wird rot bei einer fehlenden Tabelle, einer doppelten oder falsch geschriebenen Kennung, einem unbekannten Abschnitt in der Tabellenliste und bei einer gebauten Zeile, deren Tests fehlen oder die Kennung nicht tragen. #90 baut darauf auf (direkte Adressen, htmx-Anfragen, manipulierte Formulare, Rundumtest).
- **Verbindungstabellen,** die Django selbst zu einer Tabelle anlegt, gehören zu dieser Tabelle und stehen nicht eigens in der Matrix.
- **Aus der Grundregel abgeleitet,** nicht neu entschieden, aber erstmals ausgeschrieben: Verbandsleitung und Veranstaltungsteam ohne weitere Rolle sehen keine Namen von Ringen, Stämmen und Gruppen (EH-05), weil das nirgends erlaubt ist.

**Umsetzung:** `docs/rechtematrix.md`, `tests/rechtematrix.py`, `tests/test_rechtematrix.py`, `pyproject.toml` (Markierung angemeldet), `CONTRIBUTING.md` (Abschnitt 4), `.claude/skills/grill-me/SKILL.md`, `.github/pull_request_template.md`; Markierung an Tests in `tests/test_rollen_protokoll.py` und `tests/test_einheiten_protokoll.py`.

## 2026-10-23 · Protokoll der Strukturänderungen (#131): Anlegen, Umbenennen, Ring, „hat Ringe“; 5 Stunden aus dem Puffer

**Entscheidung** (Sebastian; Klärung von #131 am 23.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/131#issuecomment-6360896544); [Fragen bei der Umsetzung](https://github.com/sebivtt/dpv-participant-management/issues/131#issuecomment-6361709938) am selben Tag). Löst die technische Wahl „Kein Protokoll für Änderungen an Einheiten“ aus der Klärung von #95 vom 22.10.2026 ab.

1. **Was ins Protokoll kommt:** Anlegen einer Organisation, Umbenennen (auch nur in der Schreibweise, „boreas“ → „Boreas“), einen Stamm einem Ring zuordnen oder in einen anderen Ring verschieben und „hat Ringe“ ein- oder ausschalten. Jeder Weg schreibt: die Befehle für Verband und Bünde (#88) mit „Befehl auf dem Server“ als Urheber und später die Seiten aus #95 und #107. Abgelehnte Versuche und Speichern ohne Änderung schreiben nichts; Leerzeichen am Rand entfernt das Tool ohnehin. Das Notfall-Löschen steht im Protokoll der Admin-Zugriffe (#92). Namensänderungen von Personen kommen nicht hinein.
2. **Inhalt eines Eintrags:** Zeitpunkt, wer geändert hat, welche Organisation (Name zum Zeitpunkt der Änderung und Kennung, wie #91), was geändert wurde, bei Änderungen alter und neuer Wert. Kein Feld für einen Grund oder freien Text.
3. **Anlegen nennt den Ort** (F1): Der Eintrag nennt, wo die neue Organisation hängt, etwa den Ring eines neuen Stammes, weil der Ring bestimmt, welche Ringleitung die Personen sieht.
4. **Bund gleich mit Ringen anlegen** (F2) ergibt zwei Einträge mit derselben Uhrzeit: „angelegt“ und „hat Ringe · aus → ein“.
5. **Gruppe in einen anderen Stamm verschieben** (F3): Das Datenmodell erlaubt es, keine Seite bietet es an. Es kommt als „Stamm gewechselt“ ins Protokoll und wird nicht neu verboten; ob es erlaubt bleibt, klärt sich bei #95 bzw. #127. Der Satz an ORG-06 nennt es deshalb nicht eigens.
6. **Sicherheit wie #91:** Änderung und Eintrag gelingen nur zusammen. Niemand ändert oder löscht Einträge über das Tool, auch Admins nicht; der Testdaten-Befehl (#103) darf die Datenbank weiter vollständig leeren. Das Protokoll steht nicht im Fehlerprotokoll. In P2 sieht niemand es im Tool (W4); die Einsicht kommt mit ADM-03 in P8. Die Zeilen in der Rechtematrix kommen mit #87.
7. **Anforderungen und Fahrplan:** ORG-06 bekommt den Satz „Jede Änderung an der Struktur (anlegen, umbenennen, Ring zuordnen oder wechseln, „hat Ringe“) wird protokolliert.“ und bleibt Muss. Die rund 5 Stunden (Annahme) gehen vom Puffer ab, nichts wird verdrängt. Gerechnet gegen den Stand in `main`, ohne #113: Bedarf 606 + 5 = 611 Stunden, Puffer 658 − 611 = 47 Stunden, 47 / 611 ≈ 7,7 %, rund 8 % (`docs/fahrplan.md`, Abschnitt 3 und Abschnitt 6, Nr. 47). Nr. 46 bleibt für #113 frei (F4); #113 schreibt die Zahlen danach fort (619 Stunden, 39 Stunden Puffer, rund 6 %). Zustimmung von Sebastian am 23.10.2026.

**Technische Wahl** (KI):

- **Eine eigene Tabelle `units.UnitChange`** in der App der Einheiten, mit altem und neuem Wert. Kennungen von Urheber, Organisation und den Einheiten darüber stehen als Zahlen darin, nicht als Verweise, damit ein Eintrag nie das Löschen einer Einheit oder eines Kontos verhindert. Beim Ring sind alter und neuer Wert die Namen der Ringe, leer heißt „kein Ring“.
- **Wer ändert, ist Pflicht:** Das Speichern einer Einheit verlangt wie bei den Rollen die Angabe `by` (Konto oder `SERVER_COMMAND`). „Befehl auf dem Server“ und die Prüfung liegen dafür jetzt gemeinsam in `core/actors.py`; für die Rollen ändert sich nichts. Die bestehenden Tests in `tests/test_einheiten.py`, `tests/test_einheiten_befehle.py`, `tests/test_rollen.py`, `tests/test_rollen_befehle.py` und `tests/test_rollen_protokoll.py` geben deshalb an, wer ändert; ihre Regeln blieben gleich.
- **Kurze Sperre beim Speichern:** Die Einheit selbst wird gesperrt, bis gespeichert ist, damit der alte Wert im Eintrag stimmt; zwei gleichzeitige Umbenennungen ergeben „A → B“ und danach „B → C“. Das ist nicht der „Änderungsmodus“ aus #127, der eine Organisation über Minuten festhält; #131 hängt nicht von #127 ab.
- **Nur, was geschrieben wird, zählt:** Die Befehle schreiben nur das geänderte Feld. Ein im Programm veralteter Wert der übrigen Felder ergibt keinen Eintrag.
- **Mehrere Änderungen auf einmal** ergeben je einen Eintrag, alle mit dem Namen von vor dem Speichern und derselben Uhrzeit.
- **Sperre doppelt** wie bei #91: im Programm und per Trigger in der Datenbank gegen jedes `UPDATE` und `DELETE`; offen bleibt nur `TRUNCATE`. Sammeländerungen an den Einheiten selbst (`update()`, `bulk_create()`) umgehen wie schon die Regeln aus #88 auch das Protokoll; das Tool nutzt sie für Einheiten nicht.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Protokoll der Strukturänderungen `unit_change` (`UnitChange`), angelegt `created`, umbenannt `renamed`, Ring zugeordnet `ring_assigned`, Ring gewechselt `ring_changed`, Stamm gewechselt `troop_changed`, „hat Ringe“ umgeschaltet `has_rings`, alter und neuer Wert `old_value` und `new_value`.

**Umsetzung:** `units/models.py` (`UnitChange`, Einträge beim Speichern), `units/migrations/0002_unit_change.py` (Tabelle und Trigger), `units/texts.py`, `units/management/commands/federation.py` und `association.py`, `core/actors.py`, `roles/models.py` und `roles/texts.py` (nutzen `core/actors.py`), `README.md` (Abschnitt „Verband und Bünde anlegen (Admins)“), `docs/anforderungen.md` (ORG-06), `docs/fahrplan.md` (Abschnitt 3, Abschnitt 6 Nr. 47), Tests in `tests/test_einheiten_protokoll.py`; Anpassungen in den oben genannten Tests.

## 2026-10-23 · Protokoll der Rollenänderungen (#91): nur schreiben in P2 (W4), Namen zum Zeitpunkt, Sperre in der Datenbank

**Entscheidung** (Sebastian; Bestandsaufnahme P2 vom 22.10.2026, [W4 in #106](https://github.com/sebivtt/dpv-participant-management/issues/106#issuecomment-6342842432); Klärung von #91 am 22.10.2026; Nachklärung P2 vom 22.10.2026 in #106, Frage 2; [Fragen bei der Umsetzung](https://github.com/sebivtt/dpv-participant-management/issues/91#issuecomment-6360190203) am 23.10.2026):

1. **W4, Einsicht in Protokolle (ROL-03 gegen ADM-03):** In P2 werden das Protokoll der Rollenänderungen (#91) und das Protokoll der Admin-Zugriffe (#92) nur geschrieben und getestet, auch dass sich Einträge nicht ändern oder löschen lassen. Die Einsicht für Admins und Verbandsleitung kommt mit ADM-03 in P8; bis dahin gilt die Ausnahme in ROL-03 noch nicht.
2. **Was ins Protokoll kommt:** jedes tatsächliche Vergeben und Entfernen einer Rolle aus ROL-01, auch der Mitgliedschaft (aufnehmen, beenden, wechseln, automatisch beim Einsetzen als Leitung) und der Admin-Befehle auf dem Server. Ein Wechsel ergibt „entfernt“ und „vergeben“ mit derselben Uhrzeit. Abgelehnte Versuche und Speichern ohne Änderung schreiben nichts. Es gibt kein Feld für einen Grund oder freien Text, weil darin Gesundheitsangaben landen könnten.
3. **Urheber:** Der Eintrag nennt nur die Person, die geändert hat, nicht die Rolle, in der sie gehandelt hat; bei mehreren passenden Rollen wäre unklar, welche gemeint ist. Bei Befehlen auf dem Server steht „Befehl auf dem Server“.
4. **Namen zum Zeitpunkt der Änderung:** Der Eintrag hält die Namen von Person, Urheber und Organisation fest, wie sie damals hießen; eine spätere Umbenennung ändert ihn nicht. Ein Eintrag hindert nie daran, später ein Konto zu löschen. Was dann mit den Einträgen geschieht und wie lange sie bleiben, klärt #66 (DSG-09, OP-2); in P2 wird nichts gelöscht.
5. **Testdaten-Befehl:** Lokal und in der Testumgebung darf der Befehl aus #103 die Datenbank vollständig leeren, auch das Protokoll. Die Sperre im Tool bleibt.
6. **Rechtematrix:** Die Zeilen für das Protokoll kommen mit #87, weil es die Matrix bei #91 noch nicht gab (Hinweis in #87).

**Technische Wahl** (KI):

- **Eine Tabelle `roles.RoleChange`** in der App der Rollen. Kennungen von Urheber, Person und Einheit stehen als Zahlen darin, nicht als Verweise; sonst ließe sich ein Konto, das je eine Rolle hatte, nie löschen, oder die Datenbank müsste den Eintrag beim Löschen ändern.
- **Wer ändert, ist Pflicht:** Speichern und Löschen einer Rolle verlangen die Angabe `by` (Konto oder `SERVER_COMMAND`); ohne sie lehnt das Tool ab. So kann keine spätere Seite (#65, #93, #94, #92, #103) den Urheber still vergessen. Die bestehenden Tests in `tests/test_rollen.py` und `tests/test_rollen_befehle.py` geben deshalb an, wer ändert; ihre Regeln blieben gleich.
- **Beides oder nichts:** Rolle und Eintrag werden in derselben Datenbank-Transaktion geschrieben. Die Uhrzeit ist der Beginn der äußersten laufenden Transaktion, deshalb tragen zusammengehörige Einträge genau dieselbe. Öffnet eine spätere Seite oder ein Befehl vorher selbst eine Transaktion, ist es deren Beginn; das Tool tut das in P2 nicht. Die Reihenfolge der Einträge gibt ihre laufende Nummer an, nicht die Uhrzeit: Bei gleichzeitigen Änderungen kann eine früher begonnene Transaktion später schreiben.
- **Sperre doppelt:** Im Programm lehnt das Tool Ändern und Löschen eines Eintrags ab. Zusätzlich lehnt eine Regel in der Datenbank (Trigger) jedes `UPDATE` und `DELETE` auf der Tabelle ab, auch Sammeländerungen am Programm vorbei. Offen bleibt nur das vollständige Leeren (`TRUNCATE`), das der Testdaten-Befehl (#103) und der Testlauf brauchen; im Tool gibt es dafür keinen Weg. Wer direkt in der Datenbank auf dem Server arbeitet, kann den Trigger entfernen; das gehört ins Betriebshandbuch (P6).
- **Grenze:** Sammeländerungen an den Rollen selbst (`update()`, `bulk_create()`, `QuerySet.delete()`) umgehen wie schon die Regeln aus #89 auch das Protokoll. Das Tool nutzt sie für Rollen nicht.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Protokoll der Rollenänderungen `role_change` (`RoleChange`), Urheber `actor`, vergeben `granted`, entfernt `removed`, Befehl auf dem Server `SERVER_COMMAND`.

**Umsetzung:** `roles/models.py` (`RoleChange`, Einträge beim Speichern und Löschen), `roles/expressions.py`, `roles/migrations/0002_role_change.py` (Tabelle und Trigger), `roles/texts.py`, `roles/management/commands/admin.py`, `README.md` (Abschnitt „Admins ernennen und entfernen“), Tests in `tests/test_rollen_protokoll.py`; Anpassungen in `tests/test_rollen.py` und `tests/test_rollen_befehle.py`.

## 2026-10-23 · Rollen: Mitgliedschaft und Leitungspfad, Rolle Admin, ROL-01 ergänzt

**Entscheidung** (Sebastian; Klärung von #89 am 22.10.2026, [Protokoll](https://github.com/sebivtt/dpv-participant-management/issues/89#issuecomment-6343606180); Nachklärung P2 vom 22.10.2026 in #106, Fragen 4 und 9; Fragen bei der Umsetzung am 23.10.2026 in #89):

1. **Mitgliedschaft und Leitung sind getrennt.** Eine Person mit Account ist Mitglied in höchstens einer Einheit (Gruppe, Stamm, Ring oder Bund), nie im Verband. Leitungsrollen hat sie nur auf ihrem Pfad: im eigenen Stamm (auch in anderen Gruppen dort) und in den Einheiten darüber; ist sie direkt Mitglied eines Rings oder Bundes, auch in allen Einheiten darunter. Sonst lehnt das Tool ab und nennt den Grund.
2. **Automatische Mitgliedschaft:** Wer ohne Mitgliedschaft als Leitung einer Gruppe, eines Stammes, eines Rings oder eines Bundes eingesetzt wird, wird Mitglied der geleiteten Einheit und bleibt es, wenn die Leitung endet. Verbandsleitung und DPV-Veranstaltungsteam brauchen keine Mitgliedschaft und legen keine an.
3. **Wechsel und Ende der Mitgliedschaft** gehen nur, wenn danach alle Leitungsrollen in Einheiten noch auf dem Pfad liegen; ohne Mitgliedschaft heißt das: keine Leitungsrollen in Einheiten. Sonst nennt das Tool die Rollen, die zuerst entfernt werden müssen. Leitungsrollen werden nie automatisch entfernt. Am 23.10.2026 hat Sebastian erwogen, beim Austreten die Leitungsrollen mit enden zu lassen, und ist nach dem Hinweis auf #65 und den Wortlaut von ROL-01 bei der geklärten Regel geblieben (F1 in #89).
4. **Admin** gibt keine Rechte einer Leitung; Personendaten sieht ein Admin nur über den Support-Weg mit Protokoll (#92). Admin wird man bis ADM-01 (P6) nur per Befehl auf dem Server, über den Benutzernamen eines Kontos, das sich schon einmal angemeldet hat; ein zweiter Befehl entfernt das Recht, auch beim letzten Admin. Rechte entstehen nur aus Rollen, nie aus Keycloak und nie daraus, wer etwas angelegt hat.
5. **ROL-01 ergänzt** (#109) um den Satzteil ab „Eine Person mit Account ist Mitglied in höchstens einer Einheit …“ bis „Ohne Leitungsrolle kann sie selbst aus ihrer Einheit austreten.“, im Wortlaut der Nachklärung vom 22.10.2026, dem Sebastian zugestimmt hat.

**Technische Wahl** (KI):

- **Eine Tabelle für alle Rollen** (`roles.Role`: Person, Rolle, Einheit), auch für die Mitgliedschaft. So setzt die Datenbank „höchstens eine Mitgliedschaft“, „dieselbe Rolle je Einheit nur einmal“, „Admin ohne Einheit, alle anderen mit“ selbst durch, und das Protokoll (#91) beobachtet nur eine Stelle. Welche Rolle zu welcher Ebene passt und der Pfad stehen in der Regelprüfung beim Speichern und Löschen.
- **Admin nicht als Djangos „Superuser“:** Der hätte automatisch alle Rechte; ein Admin bekommt dadurch keine.
- **Gleichzeitige Änderungen:** Jede Änderung an den Rollen einer Person sperrt deren Konto kurz; so sehen die Regeln immer den aktuellen Stand, etwa wenn ein Wechsel und eine neue Leitung zugleich kommen.
- **Nur die Einheit einer Mitgliedschaft lässt sich ändern** (Wechsel). Jede andere Rolle wird entfernt und neu gegeben, damit jede Änderung als solche im Protokoll steht (#91).
- **Löschschutz:** Eine Einheit, an der eine Rolle hängt, und ein Konto mit Rollen lassen sich in der Datenbank nicht löschen.
- **Meldungen** nennen Namen in Anführungszeichen ohne Artikel („keine Leitung in „Zugvögel““), weil sich Namen nicht automatisch beugen lassen; Gruppen mit ihrem Stamm in Klammern. Meldungen, die die Einheit der Person nennen (Pfad, zweite Mitgliedschaft, Rollen zuerst entfernen), tragen je einen eigenen Code (`outside_path`, `second_membership`, `remove_roles_first`), damit #65, #93 und #94 bei fremden Personen eine Fassung ohne Einheit zeigen können (BER-01).
- **Befehl:** `python manage.py admin grant|revoke BENUTZERNAME` (Anleitung im `README.md`). Wer schon Admin ist, bekommt beim Ernennen nur einen Hinweis.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Rolle `role`, Mitglied `member`, Gruppenleitung `group_lead`, Stammesleitung `troop_lead`, Ringleitung `ring_lead`, Bundesleitung `association_lead`, Verbandsleitung `federation_lead`, DPV-Veranstaltungsteam `event_team`, Admin `admin`.

**Umsetzung:** `roles/` (Datenmodell, Migration, Regeln, Meldungen, Befehl `admin`), `config/settings.py`, `.dockerignore`, `README.md` (Abschnitt „Admins ernennen und entfernen“), `docs/anforderungen.md` (ROL-01), Tests in `tests/test_rollen.py` und `tests/test_rollen_befehle.py`; `tests/test_testumgebung_aufbau.py` nennt die neue App.

## 2026-10-23 · Einheiten: kein Löschknopf (W5), Ring-Schalter, Personen auf jeder Ebene, eindeutige Namen

**Entscheidung** (Sebastian; Klärung von #88 am 22.10.2026, Nachklärung P2 vom 22.10.2026 in #106, Fragen bei der Umsetzung am 23.10.2026 in #88). Das sind Auslegungen von ORG-01 und ORG-06; der Text der Anforderungen bleibt.

1. **W5, Einheiten löschen:** In P2 gibt es in der Oberfläche keinen Löschknopf, nur Anlegen und Bearbeiten. Die Datenbank verhindert das Löschen einer Einheit, unter der noch Einheiten hängen; den Schutz für Einheiten mit Personen testen die Issues, die Personen an Einheiten hängen (#65, #97). Im Notfall löscht ein Admin eine leere Einheit per Befehl, protokolliert (#92). Löschen mit Zusammenfassung nach ORG-07 kommt später (#108).
2. **Ring-Schalter je Bund** statt Ringen fest nur im „DPBM Mosaik“: Jeder Bund hat den Schalter „hat Ringe“, Standard aus. Nur dort lassen sich Ringe anlegen, und jeder neue Stamm hängt dann in einem Ring. Einschalten geht auch, wenn der Bund schon Stämme hat; sie bleiben ohne Ring, bis sie einem zugeordnet werden (#95). Ausschalten geht nur, solange der Bund keinen Ring hat.
3. **Personen auf jeder Ebene außer dem Verband:** Personen gehören zu einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie direkt zum Verband. Das deckt „Pflegt ein Bund keine Stämme, gehören Personen direkt zum Bund“ (ORG-01) ab. Umgesetzt mit #65 und #97.
4. **Eindeutige Namen:** Kein Name ist leer, keiner ist länger als 100 Zeichen. Eindeutig sind Bünde im Verband, Ringe und Stämme zusammen im Bund (auch über verschiedene Ringe hinweg; ein Ring und ein Stamm im selben Bund heißen also nie gleich) und Gruppen im Stamm. Als gleich gilt, was sich nur in Groß- und Kleinschreibung oder Leerzeichen am Anfang oder Ende unterscheidet; Leerzeichen in der Mitte zählen („Sippe  Falken“ ist ein anderer Name als „Sippe Falken“). Stämme und Gruppen dürfen in verschiedenen Bünden bzw. Stämmen gleich heißen.
5. **Kurznamen** wie „DPV“ oder „DPBM“ kommen nicht mit #88; vorgemerkt in #124.

**Technische Wahl** (KI):

- **Eine Tabelle für alle fünf Ebenen** (`units.Unit`) mit Art, Name und der Einheit darüber, statt fünf Tabellen. Später hängen Personen, Rollen und Teilnahmekreise an Einheiten jeder Ebene; mit einer Tabelle reicht dafür ein Verweis. Nachteil: Welche Art unter welcher hängen darf, prüft das Tool beim Speichern, nicht die Datenbank. Genau ein Verband, eindeutige Namen, nicht leere Namen ohne Leerzeichen am Rand und der Löschschutz stehen zusätzlich als Regeln in der Datenbank.
- **Der Bund steht bei Ringen und Stämmen zusätzlich dabei,** damit die Datenbank selbst doppelte Stämme über Ringe hinweg verhindert, auch bei gleichzeitigen Anfragen. Damit dieser Wert nie veraltet, bleibt die Ebene einer Einheit fest, und ein Ring oder Stamm wechselt nicht den Bund. Innerhalb eines Bundes lässt sich ein Stamm weiter einem Ring zuordnen oder in einen anderen Ring verschieben (#95). Sollte ein Wechsel zwischen Bünden einmal gebraucht werden, wird er dort neu entschieden.
- **„Ring ist Pflicht“ auch beim Verschieben** (aus Frage 4 der Klärung): In einem Bund mit Ringen kommt kein Stamm neu ohne Ring an den Bund, auch nicht, indem man ihn aus seinem Ring herausnimmt. Nur Stämme von vor dem Einschalten bleiben ohne Ring.
- **Gleichzeitige Änderungen:** Beim Anlegen eines Rings oder Stammes und beim Umschalten von „hat Ringe“ sperrt das Tool den Bund kurz, sonst könnten ein neuer Ring und das Ausschalten zugleich durchgehen.
- **Befehle für Admins:** `python manage.py federation create|rename` und `python manage.py association create|rename|rings|list` (Anleitung im `README.md`). Befehlsnamen sind Code und deshalb englisch; die Meldungen sind deutsch. Umbenennen und Umschalten schreiben nur das geänderte Feld, damit zwei gleichzeitige Befehle sich nicht gegenseitig überschreiben.
- **Code-Namen** (CONTRIBUTING.md, Abschnitt 1): Einheit `unit`, Verband `federation`, Bund `association`, Ring `ring`, Stamm `troop`, Gruppe `group`, Schalter „hat Ringe“ `has_rings`.

**Umsetzung:** `units/` (Datenmodell, Migration, Befehle, Meldungen), `config/settings.py`, `README.md` (Abschnitt „Verband und Bünde anlegen (Admins)“), Tests in `tests/test_einheiten.py`, `tests/test_einheiten_befehle.py`, `tests/test_testumgebung_aufbau.py` und `containertests/test_testumgebung_container.py`; `.dockerignore` gibt den Ordner `units/` für das Container-Abbild frei.

## 2026-10-22 · Antworten der Datenschutzperson zu OP-2

**Entscheidung** (Sebastian, 22.10.2026; #81): Die Antworten der Datenschutzperson des DPV werden so übernommen:

- **Verantwortlich** im Sinne der DSGVO ist der Betreiber, also der DPV.
- **Einwilligung:** Die Abfrage genügt, dass die angemeldeten Personen die Kriterien erfüllen bzw. die Einwilligung der Erziehungsberechtigten vorliegt (DSG-01; für die Bestätigung beim Anlegen nach DSG-02 ist das eine Auslegung der KI). Angeregt ist, zusätzlich abzufragen, dass die Personen die Teilnahmekriterien erfüllen; der Wortlaut wird beim Klären von DSG-01 festgelegt. Grundsatz: nach bestem Wissen umsetzen, handhabbar und brauchbar bleiben, Vertrauen statt übermäßiger Kontrolle. Die Idee, dass die Leitung einen Link erzeugt, über den Eltern bzw. Kinder einer Gruppenanmeldung beitreten und selbst bestätigen, kommt als Vorschlag in #44.
- **Gesundheitsangaben im eigenen Profil** (FRM-04): freiwillige Angaben sind in Ordnung, bei regelmäßiger automatischer Löschung (dass die Löschung Bedingung für die Speicherung im Profil ist, ist eine vorsichtige Auslegung der KI). In der Anmeldung speichert ein Knopf „Für künftige Anmeldungen speichern“ die Angaben im eigenen Profil, wo sie bearbeitet werden können. Die Löschfrist ist offen und wird beim Klären festgelegt.
- **Verträge zur Auftragsverarbeitung** (u. a. Microsoft Azure, Google Workspace) liegen vor; Google Workspace soll laut Datenschutzperson DSGVO-konform sein.
- **Impressum und Datenschutzerklärung:** Das Tool bekommt eigene Seiten (#12); verantwortlich ist der DPV.

**Noch offen** (nicht beantwortet oder ausdrücklich offen): ob eine Datenschutz-Folgenabschätzung nötig ist; ab welchem Alter Personen mit Account selbst einwilligen können; ob die Einwilligung nach Volljährigkeit fortgilt (DSG-02, bleibt Annahme); Verzeichnis der Verarbeitungen und Ablauf bei Datenpannen; ob das Fehlerprotokoll einen Bezug zum Konto braucht (#11, bis dahin bleibt es ohne); ob für Entwicklung und Betrieb des Tools ein eigener Vertrag mit dem DPV nötig ist (gefragt war nur nach den Verträgen mit Azure und Google). Der Vorbehalt bei FRM-04 bleibt deshalb: Die Speicherung im Profil wird in P4 zuletzt gebaut und nur mit Freigabe aus OP-2. Fristen und Folgen der OP-Tabelle bleiben unverändert.

**Neue Wünsche,** vorgemerkt ohne Phase: Fahrtkosten- und Auslagenerstattung (#82), Anbindung an Google Sheets für Kostenübersichten (#83), Kennwort für Gäste je Veranstaltung (#84).

**Begründung:** Die Antworten bestätigen die Arbeitsannahme vom 20.10.2026 zur stellvertretenden Bestätigung. Hinweise der KI: Einige Antworten lassen die Frage offen, etwa ob eine Folgenabschätzung entfällt; sie werden deshalb nicht als geklärt eingetragen, sondern bleiben unter OP-2 offen. Gesundheitsdaten von Kindern gehören zu den besonders geschützten Daten; ob dafür eine Folgenabschätzung Pflicht ist, entscheidet die Datenschutzperson, nicht die KI.

**Umsetzung:** `docs/anforderungen.md` (FRM-04, Abschnitt Datenschutz, DSG-01, DSG-02, OP-2) und `docs/fahrplan.md` (OP-Tabelle bei OP-2, Abschnitt 6 Nr. 45), mit Zustimmung von Sebastian am 22.10.2026; Kommentare in #11, #12 und #44; neue vorgemerkte Issues #82, #83 und #84.

---

## 2026-10-22 · Login auf dem Testserver wandert von P1 nach P2

**Entscheidung** (Sebastian, 22.10.2026; #71): Das Abschlusskriterium „Login nur per Keycloak … auf dem Testserver“ gehört jetzt zu P2, zusammen mit #59 (Testumgebung auf dem Server) und #63 (Login dort nachweisen). P1 verlangt nur noch den Login lokal. Die Folgen bei OP-1 (Test-Client) und OP-4 (Testserver) in der OP-Tabelle nennen P2; die Fristen der Anfragen bleiben. Die Empfehlung der KI war das Verschieben; die Alternative war, auf den Admin zu warten.

**Begründung:** Der Code von P1 ist fertig. Der Server-Teil bringt vor allem Einrichtung auf dem Server, eine Anleitung und eine Checkliste von Hand und wartet auf Auskünfte des Admins, der im Urlaub ist. So kann das externe Review zu P1 jetzt auf dem fertigen Stand laufen, und P2 beginnt danach. Das Review zu P2 prüft den Server-Teil mit. Ändert der Server doch Code, etwa für HTTPS hinter einem vorgeschalteten Programm, landet das in P2. An E3 ändert sich nichts: Dort müssen ohnehin alle Abschlusskriterien von P1 bis P6 erfüllt sein. Die Stunden der Phasen bleiben, der Aufwand des Server-Teils ist gering (Annahme). Antwortet der Admin sehr spät, zählt die Wartezeit jetzt gegen P2 und damit gegen E1; die OP-Fristen (31.01. und 28.02.2027) liegen aber vor dem Zieldatum von P2.

**Umsetzung:** `docs/fahrplan.md` (Phasen P1 und P2, OP-Tabelle, kritischer Pfad, Abschnitt 6 Nr. 44); Labels und Texte von #37, #38, #59, #63; #57.

## 2026-10-22 · Kein Stundenlog, E1 misst Termine statt Stunden

**Entscheidung** (Sebastian, 22.10.2026; #68):

1. **Kein Stundenlog.** Sebastian führt keins; er ist dem Zeitplan weit voraus. Damit entfallen das Stundenlog aus dem Eintrag „Neustart, Name, Lizenz, Umfang und Technik“ vom 20.10.2026, die getrennt notierte Lernzeit aus „Entscheidungen nach der Prüfung der Rückmeldungen“ vom 20.10.2026, „Stundenlog führen“ aus „P1 beginnt früher, Restpunkte von P0 laufen parallel“ vom 21.10.2026 und der Eintrag der Review-Zeit aus „Externes KI-Review am Ende jeder Phase“ vom 21.10.2026.
2. **E1 misst Termine statt Stunden:** weiter, wenn P2 mit höchstens 4 Wochen Verzug fertig ist; bei 4 bis 8 Wochen Liste 2 und die Zieldaten der folgenden Phasen um den Verzug neu rechnen; bei mehr Verzug mit dem DPV-Veranstaltungsteam ein späteres Vorbereitungstreffen als Generalprobe festlegen. Die übrigen Bedingungen von E1 bleiben. E2 misst schon so.
3. **Risikotabelle:** „Zu wenig Zeit“ zeigt sich daran, dass eine Phase an ihrem Zieldatum nicht fertig ist; „Schätzung zu niedrig“ daran, dass P2 mehr als 4 Wochen nach ihrem Zieldatum fertig ist.

Die Empfehlung der KI war „Termine statt Stunden“; die anderen Möglichkeiten waren eine grobe Schätzung am Prüfpunkt oder keine Prüfung des Tempos mehr.

**Begründung:** Eine Messgröße, die nicht gepflegt wird, macht die Prüfpunkte wertlos. Termine stehen ohnehin fest. P2 dauert rund 17 Wochen (28.02. bis 30.06.2027); 4 Wochen Verzug entsprechen etwa 125 %, 8 Wochen etwa 150 % der Phasendauer. Das ist etwas großzügiger als die bisherige Schwelle von 125 % der geschätzten Stunden, die bei rund 7,5 Stunden je Woche schon nach rund 2 Wochen Verzug erreicht gewesen wäre. Die Schätzungen in Stunden bleiben als Planungsgrundlage (Annahme) stehen, werden aber nicht mehr nachgemessen. Punkt 1 aus „Offene Punkte aus der Bestandsaufnahme“ vom 20.10.2026 („Die Stundenschwelle an E1 wird nicht weiter geklärt“) ist damit gegenstandslos.

**Nicht geändert:** E4 („Betriebsaufwand pro Woche gemessen“) betrifft den Betrieb ab 2028 und wird vor E4 neu angesehen.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, Machbarkeit, Phasen, E1, Risikotabelle, Abschnitt 6 Nr. 43), `docs/review-leitfaden.md`; in #57 ist „Stundenlog läuft“ als entfallen markiert.

## 2026-10-22 · Test-Realm im Keycloak des DPV: Konten, Passwörter, Nachweis

**Entscheidung** (Sebastian, Klärung von #38 am 22.10.2026; Protokoll in #38):

1. **Selbstregistrierung aus** im Test-Realm `dpv-test`. Konten entstehen nur, wenn Sebastian oder der Admin sie anlegen.
2. **Passwörter nicht im Repo:** Die Importdatei enthält die Konten ohne Passwort. Nach dem Import setzt Sebastian jedem Konto ein eigenes, langes Passwort und bewahrt es in seinem Passwortmanager auf. Lokal bleiben die erfundenen Passwörter im Repo, weil die Keycloak-Testumgebung nur auf dem eigenen Rechner läuft.
3. **Vier erfundene Konten:** `erika.testfrau`, `max.testmann`, `ohne.name`, `ohne.nachname`, Mails auf `@example.org`. Ein Konto ohne Mail gibt es im echten Realm nicht; seine Ablehnung prüft weiter die lokale Testumgebung.
4. **Weitere Personen** (Prüfer, Planungsteam) bekommen je ein eigenes erfundenes Konto ohne echten Namen und echte Mail. Sebastian legt es an und löscht es wieder.
5. **Keine Kennzeichnung** der Login-Seite von Keycloak (Empfehlung der KI war eine Überschrift „DPV Testumgebung – nur erfundene Konten“). Der Realm bekommt keinen Anzeigenamen; Keycloak zeigt deshalb „dpv-test“.
6. **Nachweis** des Logins auf dem Server per Checkliste von Hand (#63).
7. **Abweichende Keycloak-Fassung:** Weicht die Fassung des DPV von 26.7.5 ab, werden die lokale Testumgebung und die Prüfung auf GitHub in einem eigenen Issue angeglichen.

**Technische Wahl** (KI):

- **Importdatei** `testumgebung/keycloak/dpv-test-realm.json`, angelegt über „Realm erstellen“ mit hochgeladener Datei. Kein Passwort und kein Client-Secret darin; das Secret erzeugt Keycloak beim Import. Ein Test schlägt fehl, sobald eines hineinkommt.
- **Kein Mailserver und kein „Passwort vergessen“**, damit Keycloak aus dem Test-Realm nie Mails verschickt.
- **Schutz gegen Passwortraten:** Nach 10 Fehlversuchen (oder sehr schnellen Wiederholungen) sperrt Keycloak das Konto vorübergehend, höchstens 15 Minuten, nie dauerhaft. Die Login-Seite ist offen erreichbar.
- **Name und Mail ändert nur der Admin**, nicht die Person über die Kontoverwaltung von Keycloak. Sonst könnte jemand mit einem Testkonto seine echten Angaben eintragen (DSG-08). Gleiche Begründung wie bei der Selbstregistrierung.
- **Login-Client wie lokal:** vertraulich, Login nur über die Login-Seite von Keycloak mit PKCE, kein Login mit Passwort direkt aus dem Tool, kein Service-Konto, keine Rollen. Rücksprung und Abmelden nur zur Testdomain; bis sie feststeht, steht dort `https://testdomain-eintragen.invalid`. Die Endung `.invalid` gibt es im Internet nicht.
- **HTTPS Pflicht** (`sslRequired: external`), außer bei Aufrufen vom eigenen Rechner.
- **Prüfung gegen echtes Keycloak 26.7.5:** Die Tests importieren die Datei mit dem Admin-Zugang der lokalen Keycloak-Testumgebung (erfundener Wert, auf GitHub `KEYCLOAK_DEV_ADMIN_PASSWORD`), setzen Passwörter und melden sich im Tool an. Das Tool selbst bekommt nie einen Admin-Zugang.

**Begründung:** Zu 1 bis 7: Protokoll in #38. Die Testumgebung ist offen erreichbar (Entscheidung vom 22.10.2026 zu #37); vor E3 dürfen keine echten Daten hinein, und wer das Repo sieht, soll nicht hineinkommen.

**Umsetzung:** `testumgebung/keycloak/dpv-test-realm.json`, `README.md` (Abschnitt „Test-Realm im Keycloak des DPV“), `.github/workflows/ci.yml`, Tests in `tests/test_testrealm_datei.py` und `tests/test_testrealm_echt.py`.

## 2026-10-22 · Testumgebung im Container: Schutz, Kennzeichnung, Datenbank, Mails, Aktualisieren

**Entscheidung** (Sebastian, Klärung von #37 am 22.10.2026; Protokoll in #37):

1. **Schutz:** Die Testumgebung ist offen erreichbar wie später das echte Tool, ohne Vorschaltpasswort. Suchmaschinen werden gebeten, nichts aufzunehmen. Hineinkommen kann nur, wer ein Konto im Test-Realm hat (#38). Die Empfehlung der KI war ein Vorschaltpasswort.
2. **Kennzeichnung:** Auf jeder Seite der Testumgebung steht oben ein Band mit Symbol und dem Text „Testumgebung: Hier gibt es nur erfundene Daten. Bitte gib keine echten Angaben ein.“ Es erscheint nur mit dem Schalter `TEST_ENVIRONMENT=1`, nie im späteren Betrieb.
3. **Datenbank:** Die Testumgebung bringt einen eigenen Datenbank-Container mit PostgreSQL 18 mit, ohne Zugriff auf das PostgreSQL des Servers.
4. **Mails** gehen in der Testumgebung nur als Hinweis ins Log, ohne Empfänger und Inhalt. Der Mailtest aus P5 kommt in #60.
5. **Aktualisieren:** Sebastian selbst, der Admin als Vertretung; bei Bedarf, sicher vor jedem externen Review und vor den Prüfpunkten. Nichts wird automatisch von GitHub auf den Server gespielt.
6. **Aufteilung:** #37 in #58 (Abbild und Testumgebung lokal) und #59 (auf dem Server).

**Technische Wahl** (KI):

- **gunicorn 26.2.0** (MIT, mit der EUPL-1.2 verträglich; Fassung vom 24.08.2026, gepflegt vom Projekt gunicorn.org, keine weiteren Pakete) als Webserver im Container. Djangos eigener Server ist nur für die Entwicklung gedacht. Gewählt statt uvicorn oder waitress, weil das Tool synchron arbeitet (WSGI) und gunicorn dafür der verbreitetste Weg ist. Ohne Zugriffsprotokoll: Es enthielte jede echte Adresse mit Parametern (Entscheidung zu #6); ob der Betrieb eins braucht, klärt #11.
- **Abbild:** `python:3.13-slim` mit uv 0.13.4 wie in der Prüfung auf GitHub, Pakete fest aus `uv.lock` ohne die Pakete zum Prüfen, das Tool läuft nicht als Verwalter. Die Grundabbilder sind über ihre Fassung festgelegt, nicht über eine Prüfsumme; die ließ sich aus der Arbeitsumgebung nicht nachsehen (Docker Hub gesperrt).
- **Mails über `MAILERS`:** Seit Django 6.1 ersetzt `MAILERS` die Einstellung `EMAIL_BACKEND`, die bis Django 2028 wegfällt. Der einzige Mailweg ist `core.mail.LogOnlyEmailBackend`, auch in der Entwicklung, bis P5 den Versand bringt.
- **HTTPS nur mit Schalter** (`DJANGO_BEHIND_HTTPS_PROXY=1`): Dann vertraut das Tool dem Hinweis `X-Forwarded-Proto` des Programms davor, und Sitzungs- und Formular-Cookies gehen nur über HTTPS. Ohne Schalter könnte jede Anfrage den Hinweis selbst mitschicken.
- **Keycloak aus dem Container** (`KEYCLOAK_REALM_URL_INTERN`): Auf dem eigenen Rechner erreicht das Tool im Container die Keycloak-Testumgebung unter `keycloak:8080`, der Browser unter `localhost:8081`. Keycloak nennt dem Browser deshalb immer `localhost:8081` (`--hostname`, `--hostname-backchannel-dynamic`). Auf dem Server ist beides dieselbe Adresse.
- **Prüfung im Container:** `pruefen.sh` baut und startet die Testumgebung unter eigenem Namen (`containertests/`), meldet sich wirklich an und räumt danach ab; eine eigene Testumgebung auf dem Mac bleibt unberührt.
- **Rote Prüfungen auf GitHub lesbar:** `pruefen.sh` schreibt auf GitHub je rote Prüfung einen Fehler-Hinweis und die roten Tests als Warnungen an den Prüflauf. Das volle Protokoll ist aus der Arbeitsumgebung der KI nicht lesbar (Azure-Speicher gesperrt), diese Hinweise schon.

**Begründung:** Zu 1 bis 6: Protokoll in #37. Die Testumgebung läuft so lokal genau so, wie sie später auf dem Server läuft, und lässt sich prüfen, bevor der Admin die Testdomain eingerichtet hat.

**Umsetzung:** `Dockerfile`, `.dockerignore`, `docker/start.sh`, `testumgebung/`, `config/settings.py`, `core/mail.py`, `core/testumgebung.py`, `core/templatetags/layout.py`, `core/templates/` (Band, Symbol, Musterseite), `core/static/core/app.css`, `pyproject.toml`, `uv.lock`, `pruefen.sh`, `.github/workflows/ci.yml`, `ruff.toml`, `README.md`, Tests in `tests/test_testumgebung.py`, `tests/test_testumgebung_aufbau.py` und `containertests/`.

## 2026-10-21 · Antwort des DPV-Admins: Test-Realm, Testumgebung auf dem Produktivserver, eigene Admin-Konten

**Auskünfte** des Admins des DPV vom 21.10.2026, von Sebastian weitergegeben:

- Er kann einen Keycloak-Client anlegen oder Sebastian zum Admin machen, und er kann eine Testdomain anlegen. Der Keycloak des DPV läuft in der aktuellsten Fassung.
- Ob ein Konto gelöscht oder gesperrt ist, merkt das Tool wahrscheinlich daran, dass der Login bei Keycloak scheitert. Eine Meldung dafür kennt er nicht.
- Keycloak erhebt kein Alter.
- Einen Testserver gibt es nicht mehr. Der Produktivserver läuft mit Docker Compose bei Azure und kann beliebige Container betreiben; PostgreSQL läuft dort schon.
- Mails gehen über das SMTP-Relay von Google Workspace; der Produktivserver ist dafür freigeschaltet.
- Er ist die Ansprechperson für den Betrieb (OP-4).

**Entscheidung** (Sebastian, 21.10.2026):

1. **Eigener Test-Realm:** Der Test-Client kommt in einen eigenen Realm des DPV-Keycloak mit erfundenen Konten, nicht in den Realm der Mitglieder. Ein Realm ist ein abgeschlossener Bereich in Keycloak mit eigenen Konten.
2. **Keycloak-Fassung:** Sebastian nimmt an, dass der DPV dieselbe Fassung nutzt wie die Keycloak-Testumgebung (26.7.5), weil er sie aus aktiven Repos des DPV übernommen hat (Annahme). „Die aktuellste“ kann auch neuer sein als 26.7.5. Die genaue Fassung sieht Sebastian mit seinem Admin-Konto nach; dass das Tool mit ihr läuft, zeigt der Login über den Test-Client (#38).
3. **Testumgebung auf dem Produktivserver:** Sie läuft als eigener Container auf dem Produktivserver des DPV, mit eigener Datenbank, eigenem Datenbank-Zugang, der Testdomain und nur erfundenen Daten. Gewählt gegen einen eigenen, kostenpflichtigen Server. Die Einzelheiten klärt #37.
4. **Eigene Admin-Konten für Sebastian:** Sebastian lässt sich vom Admin ein Admin-Konto für Keycloak geben, voraussichtlich auch für Azure und weitere Dienste, um Fragen selbst nachsehen zu können. Mit diesen Konten meldet er sich nie im Tool an.

**Was unverändert gilt** (`CLAUDE.md`, `docs/fahrplan.md`): Das Tool bekommt im Keycloak des DPV keine Admin-Rechte und kein Service-Konto und schreibt nicht in Keycloak; ORG-04 Variante A nur, wenn OP-1 es erlaubt. Die KI ändert nichts am Produktivserver.

**Folge daraus** (Vorschlag der KI, Sebastian stimmt mit dem Übernehmen des Pull Requests zu): Die KI bekommt keinen von Sebastians Admin-Zugängen. Einrichtung und Aktualisierung der Testumgebung auf dem Produktivserver machen Sebastian oder der Admin nach einer Anleitung, die ohne KI funktioniert (#37).

**Begründung:** Zu 1: Im Realm der Mitglieder meldeten sich echte Personen auf dem Testserver an, und ihre echten Namen und Mails kämen ins Tool; vor E3 gibt es keine echten Personendaten (DSG-08, `docs/fahrplan.md`). Zu 3: Der Server ist schon da und kostet nichts; die Testumgebung läuft dort so wie später das Tool. Die eigene Datenbank mit eigenem Zugang hält die erfundenen Testdaten von allen echten Daten auf dem Server getrennt (Empfehlung der KI). Zu 4: Sebastian kann Fragen zu Keycloak und Server selbst nachsehen, statt jedes Mal den Admin zu fragen.

**Hinweise der KI:**

- Mit den Admin-Konten sieht Sebastian echte Daten aller Mitglieder. Auszüge daraus, auch Bildschirmfotos oder Logzeilen, gehören nie in KI-Werkzeuge (DSG-08). Für die Admin-Konten empfiehlt sich eine Anmeldung mit zweitem Faktor.
- Damit vor E3 keine echten Daten in die Testumgebung kommen, gehören drei Punkte in die Klärung von #37 und #38: Im Test-Realm ist die Selbstregistrierung aus, sonst könnten sich echte Personen mit echtem Namen und echter Mail registrieren. Die Testumgebung schickt keine Mails über das echte SMTP-Relay an echte Adressen. Sie ist von den übrigen Containern getrennt: eigenes Netz, eigene Zugangsdaten, keine gemeinsamen Ablagen.
- Gesperrte oder gelöschte Konten: Wer im Tool schon angemeldet ist, bleibt es, bis 2 Stunden lang kein Klick kam oder die Person sich abmeldet (Entscheidung zu #5). Ob das reicht, klärt #8.
- Keycloak kennt kein Alter. Der Satz in `docs/anforderungen.md` (Abgrenzung), die Altersprüfung sei Aufgabe von Keycloak, stimmte damit nicht mehr. Ob und wie das Alter für die Einwilligung von Personen mit Account zählt, ist eine Rechtsfrage für OP-2.

**Noch offen:** die Fragen an die Datenschutzperson (OP-2), die Sebastian später klärt; beim Admin die Fassung von PostgreSQL, die Region bei Azure (sie gehört in die Auftragsverarbeitung, OP-2), Backups, Absenderkonto, Tageslimit des SMTP-Relays, SPF und DKIM.

**Umsetzung:** `docs/fahrplan.md` (OP-Tabelle bei OP-1, OP-2 und OP-4; Abschnitt 6, Nr. 41 und 42) und `docs/anforderungen.md` (Abgrenzung; Offene Punkte OP-1 und OP-4), Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt. Kommentare in #37, #38 und #8.

## 2026-10-21 · Externes KI-Review am Ende jeder Phase

**Entscheidung** (Sebastian, Klärung von #26 am 21.10.2026; Protokoll in #26):

1. **Einordnung:** #26 kommt aus dem Puffer von P1 und verdrängt nichts. Die Zeit für jedes Review steht im Stundenlog.
2. **Zeitpunkt:** Am Ende jeder Phase P1 bis P10, sobald die Abschlusskriterien erfüllt scheinen, prüfen zwei externe KI-Modelle den Stand; P0 bekommt kein Review. Eine Phase gilt erst als abgeschlossen, wenn das Review-Issue eingeordnet ist und alle blockierenden Befunde behoben sind. Erst dann wechselt der „Stand“ im `README.md`.
3. **Umfang:** der ganze Stand zum geprüften Commit, Code, Tests und Doku, mit Schwerpunkt auf dem Neuen der Phase. Jedes Abschlusskriterium wird als erfüllt, nicht erfüllt oder nicht prüfbar bewertet. Widersprüche melden die Modelle, sie lösen sie nie auf.
4. **Modelle:** A mit breitem Blick, B mit Schwerpunkt Sicherheit, Rechte und Datenschutz; B sieht den Bericht von A erst nach der eigenen Prüfung. Pilot nach P1: A = ChatGPT, B = Gemini. Kein Anbieter ist vorgeschrieben. Ein drittes Modell nur bei einem strittigen, möglicherweise blockierenden Befund und immer nach P6 (vor Tor E3).
5. **Zugang:** je Review eine ZIP-Datei genau des geprüften Commits, die Sebastian hochlädt. Kein dauerhafter Zugriff externer Dienste auf das Repo. Externe Modelle bekommen nur den Inhalt des Repos und erfundene Daten (DSG-08).
6. **Zusammenführung:** Eine eigene Claude-Sitzung prüft jeden Befund nach (Beleg oder Annahme), bündelt Doppelte und schlägt die Einordnung vor. Sie schreibt nur ins Review-Issue; Befund-Issues legt sie erst nach Sebastians Entscheidung an.
7. **Stufen:** blockierend, zeitnah, später, Fehlalarm oder Duplikat, akzeptiertes Risiko. Blockierende Befunde sind vor Abschluss der Phase behoben, nicht nur entschieden. Bei Sicherheit und Datenschutz gibt es kein akzeptiertes Risiko; ein Härtungshinweis ohne konkrete Lücke darf auf „später“, ist aber vor E3 erledigt.
8. **Ablage:** ein Review-Issue je Phase. Die Rohberichte stehen unverändert als eingeklappte Kommentare darin, die eingeordneten Befunde im Text. Ins Repo kommen nur Entscheidungen.
9. **Auswertung** nach dem Review zu P2, zusammen mit E1 (#35).
10. **Fahrplan:** Phasenende und Stundenrechnung angepasst (`docs/fahrplan.md`, Abschnitt 6, Nr. 40), mit Sebastians Zustimmung.

**Technische Wahl** (KI):

- **Labels statt Issue-Typ:** GitHub bietet eigene Issue-Typen nur für Organisationen an; `sebivtt` ist ein persönliches Konto, und die Schnittstelle liefert für das Repo keine Typen (geprüft am 21.10.2026). Deshalb die Labels `externes-review` (Review-Issue einer Phase) und `review-befund` (Einzelbefund) mit je einer Vorlage in `.github/ISSUE_TEMPLATE/`.
- **ZIP-Datei mit `git archive`:** Sie enthält nur Dateien aus dem Repo, nie `.env`. `.gitattributes` hält die fremden Bibliotheken Bootstrap und axe-core heraus.
- **PyYAML 6.0.3** (MIT, mit der EUPL-1.2 verträglich; Fassung vom 25.09.2025, gepflegt vom YAML-Projekt pyyaml.org), nur zum Prüfen: Der Test liest damit die Issue-Vorlagen. Eine fehlerhafte Vorlage zeigt GitHub ohne Fehlermeldung nicht an; ein eigener Leser für das YAML-Format wäre fehleranfälliger als das verbreitete, gepflegte Paket.

**Begründung:** Die Prüfung vor jedem Pull Request sieht nur den Diff, die Prüfung vom 20.10.2026 war einmalig. Fehler im Zusammenspiel, nur scheinbar erfüllte Abschlusskriterien und widersprüchliche Anforderungen fallen so leicht durch. Zwei Modelle mit verschiedenem Schwerpunkt sehen mehr als eines; die Nachprüfung verhindert, dass Vermutungen als Fehler gelten (am 20.10.2026 waren mehrere Anmerkungen falsch oder unbelegt, z. B. G4 und G7). Claude prüft nicht als A oder B, weil Claude den Code schreibt. Blockierende Befunde müssen behoben sein, weil die nächste Phase sonst auf einem fehlerhaften Stand aufbaut; bei Sicherheit und Datenschutz wird laut Fahrplan nie gekürzt.

**Umsetzung:** `docs/review-leitfaden.md`, `.github/ISSUE_TEMPLATE/externes-review.yml`, `.github/ISSUE_TEMPLATE/review-befund.yml`, `.gitattributes`, `docs/fahrplan.md` (Machbarkeit, Phasen, Abschnitt 6 Nr. 40), `CLAUDE.md`, `README.md`, `.claude/skills/issue-anlegen/SKILL.md`, `pyproject.toml`, `uv.lock`, Labels auf GitHub, Tests in `tests/test_issue_vorlagen.py`.

## 2026-10-21 · Grundgestaltung: Bootstrap, Farben, Aufbau, Sprache und Prüfung im Browser

**Entscheidung** (Sebastian, Klärung von #7 am 20.10.2026 und drei Nachklärungen am 21.10.2026; Protokolle in #7):

1. **CSS-Grundlage: Bootstrap** (5.3.8). Sebastian hat beide Varianten der Musterseite, Bootstrap und Pico.css, am Handy und am PC verglichen. Pico.css kommt nicht ins Repo.
2. **Farbpalette:** DPV-Blau `#1a4b7e` trägt die Gestaltung, dazu Weiß und kühle Grautöne. Eine Akzentfarbe, Sonnengelb `#f0ad2c`, sparsam eingesetzt (gewählt gegen Terrakotta); Sonnengelb trägt nie Text auf Weiß. Statusfarben sind gedeckt und stehen immer mit Wort und Symbol. Alle Farben stehen in `core/static/core/app.css`; vorerst nur heller Modus, dunkler vorbereitet (#15). Schrift: die Systemschrift des Geräts (gewählt gegen Nunito Sans).
3. **Aufbau:** am PC eine feste Seitenleiste links ohne Kopfzeile über dem Inhalt; am Handy eine schmale Leiste mit „Menü“, Lilie und Profilkreis, „Abmelden“ im Menü mit Symbol und Wort. Login- und Fehlerseite ohne Seitenleiste. Fußbereich als flache Zeile: Impressum und Datenschutz links, Copyright rechts.
4. **Regel für Navigationspunkte:** Die Navigation zeigt nur, was es gibt, und nur Personen, die es nutzen dürfen. Keine leeren Platzhalter und keine Seiten „im Aufbau“. Ausblenden ersetzt nie die Rechteprüfung auf dem Server.
5. **Regel für Menüs:** Menüs öffnen am PC beim Darüberfahren und zusätzlich per Klick, Antippen und Tastatur; sie schließen mit kurzer Verzögerung. Gilt für alle späteren Menüs.
6. **Regel für gendersensible Sprache** (NFA-09): neutrale Wörter („Teilnehmende“, „Leitung“, „Person“); wo es keine gibt, beide Formen ausschreiben oder umformulieren. Kein Sternchen, kein Doppelpunkt. Die Texte duzen.
7. **Unterstützte Browser:** die gängigen der letzten rund zwei Jahre: Safari auf iPhone und Mac, Chrome und Samsung Internet auf Android, Chrome, Firefox und Edge am PC. Ältere nur bei Bedarf (#17).
8. **Logo:** Die Lilie liegt im Repo mit dem Hinweis „Das Logo ist Eigentum des DPV und nicht Teil der EUPL-Lizenz.“ im `README.md` und in `core/templates/core/LOGO-HINWEIS.md`.
9. **Leitlinie:** Sebastians Gestaltungskonzept vom 21.10.2026 steht in `docs/gestaltung.md`, zusammen mit dem, was bei #7 konkret festgelegt wurde. Spätere Seiten bauen danach.

**Technische Wahl** (KI):

- **Gestaltung vom eigenen Server mit WhiteNoise 6.12** (MIT). Ohne ein solches Paket liefert Django CSS und Skripte nur bei eingeschalteter Fehleranzeige für Entwickler aus, und die ist bewusst aus (Entscheidung zu #4). WhiteNoise liest die Dateien direkt aus `core/static/` (`WHITENOISE_USE_FINDERS`), ein Einsammeln mit `collectstatic` ist bis P6 nicht nötig. Gestaltung und Skript sind ohne Login abrufbar, weil die Login-Seite sie braucht; sie enthalten keine Daten.
- **Bootstrap ohne sein Skript:** Nur die CSS-Datei, unverändert aus dem offiziellen Paket (`npm` bootstrap 5.3.8), mit Lizenz in `core/static/core/bootstrap/`. Das Handy-Menü ist ein `dialog`-Element des Browsers mit wenigen Zeilen eigenem Skript (`core/static/core/app.js`); es hält den Fokus im Menü und schließt mit Escape.
- **Symbole:** eigene, einfache Zeichnungen in `core/templates/core/_symbole.svg` (EUPL wie das Tool), kein fremdes Symbolpaket.
- **Fachbegriffe im Code** (CONTRIBUTING.md, Abschnitt 1): Veranstaltung = `event`, Teilnehmende = `participant`. Bisher nur in den Beispieldaten der Musterseite.
- **Rauchtest mit Playwright 1.64** (Apache-2.0) in Python, nur zum Prüfen. Playwright bringt greenlet (MIT und PSF-2.0), pyee (MIT) und typing-extensions (PSF-2.0) mit. Ohne `pytest-playwright`, das zwei weitere Pakete mitbrächte; die wenigen Helfer stehen in `rauchtests/conftest.py`. Der Rauchtest läuft in Chromium, Firefox und WebKit, meldet sich wirklich bei der Keycloak-Testumgebung an und braucht dafür Port 8000. Er läuft in einem eigenen pytest-Lauf in `pruefen.sh`, weil Playwright eine Ereignisschleife betreibt, neben der Django Datenbankzugriffe abbricht; nur dort ist `DJANGO_ALLOW_ASYNC_UNSAFE` gesetzt.
- **axe-core 4.14.0** (MPL-2.0, mit der EUPL verträglich) für die Prüfung auf Barrierefreiheit liegt als Datei in `tests/vendor/axe-core/`, mit Lizenz; Prüfsumme gegen die von axe-core veröffentlichte geprüft. Gewählt statt des Python-Pakets `axe-playwright-python`, für das PyPI keine Lizenz nennt. Geprüft wird nach WCAG 2.2 A und AA.
- **Firefox auf dem Mac:** Firefox von Playwright startet unter macOS 27.0.1 nicht („Could not find profile folder“, auf Sebastians Mac auch im eigenen Terminal belegt). Der Rauchtest überspringt Firefox nur genau dann, sichtbar im Ergebnis; auf GitHub läuft Firefox immer mit.
- **WebKit auf dem Mac:** Ohne die Mac-Einstellung „Tastaturnavigation“ springt WebKit wie Safari mit Tab nur zwischen Eingabefeldern; der Tastatur-Rauchtest nutzt dort Wahltaste und Tab.

**Begründung:** Zu 1 bis 9: Protokolle in #7. Zu Bootstrap: laut Sebastian „sieht wesentlich ordentlicher aus“. Zur Technik: Gestaltung ohne Build-Schritt und vom eigenen Server (Entscheidung vom 20.10.2026, CONTRIBUTING.md, Abschnitt 6); jedes Paket weniger ist ein Paket weniger zu pflegen.

**Umsetzung:** `core/templates/base.html`, `base_app.html`, `base_einfach.html`, `core/templates/core/` (Musterseite, Bausteine, Lilie, Symbole), `core/static/core/`, `core/navigation.py`, `core/templatetags/layout.py`, `core/views.py`, `config/settings.py`, `config/urls.py`, `accounts/templates/accounts/login.html`, `core/templates/500.html`, `docs/gestaltung.md`, `README.md`, `pruefen.sh`, `.github/workflows/ci.yml`, Tests in `tests/test_gestaltung.py`, `tests/test_texte.py` und `rauchtests/`.

## 2026-10-21 · Login über Keycloak: Abmelden, Sitzung, Anrede und Technik

**Entscheidung** (Sebastian, Klärung von #5 am 20.10.2026 und Nachklärung am 21.10.2026):

1. **Vollständiges Abmelden:** „Abmelden“ beendet die Sitzung im Tool und bei Keycloak. Wer danach am selben Gerät „Anmelden“ klickt, muss das Passwort eingeben. Andere Dienste am selben Keycloak sind dann ebenfalls abgemeldet (Annahme).
2. **Sitzungsdauer:** Nach 2 Stunden ohne Aktivität endet die Sitzung im Tool; jeder Klick verlängert sie. Die Dauer steht an einer Stelle (`SESSION_IDLE_MINUTES` in `config/settings.py`).
3. **Anrede:** Alle Texte des Tools duzen, wie das Anforderungsdokument.
4. **Gleiche Mail, neue Kennung:** Meldet sich jemand mit einer neuen Keycloak-Kennung (`sub`), aber derselben Mail wie ein bestehendes Konto an, legt das Tool ein neues, leeres Konto an. Zwei Konten mit derselben Mail sind damit möglich; der Umgang damit gehört zu #8.

**Technische Wahl** (KI):

- **django-allauth 65.20.1** mit der Anbindung für OpenID Connect ist der Login-Baustein. Es läuft mit Keycloak 26.7.5; das belegen Tests, die sich wirklich an der Keycloak-Testumgebung anmelden, registrieren und abmelden. Der Rückfall auf Django 5.2 mit mozilla-django-oidc (20.10.2026) ist nicht nötig.
- **Eigenes Kontenmodell:** App `accounts`, Modell `User` (Djangos Bezeichnung), im Text „Konto“. Verknüpft wird nur über die Keycloak-Kennung, die allauth als `SocialAccount.uid` speichert.
- **Login-Pflicht für jede Adresse** über Djangos `LoginRequiredMiddleware`. Öffentlich sind nur die Login-Seite, Start und Rückkehr des Logins bei Keycloak und das Abmelden; die Liste steht mit Begründung in `tests/test_rundumtest.py`. Das Abmelden ist öffentlich, damit es auch nach abgelaufener Sitzung bei Keycloak gelingt; es geht nur per Formular mit Formularschutz.
- **Keine Anmeldung mit Passwort im Tool:** Die Adressen von allauth sind nicht eingebunden, nur Start und Rückkehr des Logins; dazu `SOCIALACCOUNT_ONLY`. Konten werden nie über die Mail gefunden oder verknüpft.
- **Abmelden ohne Rückfrage bei Keycloak:** Das Tool hebt das Kennungs-Token von Keycloak in der Sitzung auf und schickt es beim Abmelden mit. Ohne das fragt Keycloak „Möchtest du dich wirklich abmelden?“.
- **Hinweis „Sitzung abgelaufen“:** Ein Cookie `dpv_war_angemeldet` mit dem Wert `1`, ohne Bezug zur Person, überdauert die Sitzung bis zu 30 Tage. Ist es da und die Sitzung weg, zeigt die Login-Seite den Hinweis und löscht das Cookie; beim Abmelden wird es ebenfalls gelöscht.
- **Keycloak-Angaben** (`KEYCLOAK_REALM_URL`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`) prüft eine Systemprüfung beim Start (`runserver`, `migrate`, `check`), nicht das Laden der Einstellungen, damit sich diese auch ohne Keycloak laden lassen.
- **Keycloak-Testumgebung:** Keycloak 26.7.5 in `dev/docker-compose.yml` mit eingebauter Entwicklungsdatenbank, Realm, Login-Client und erfundenen Konten aus `dev/keycloak/dpv-realm.json`. Die Reihe 26.7 nutzte der DPV laut altem Repo im Juli 2026. Auf GitHub startet dieselbe Umgebung in einem eigenen Schritt.

**Begründung:** Zu 1 bis 3: Protokoll der Klärung in #5. Vollständiges Abmelden wegen gemeinsam genutzter Geräte und späterer Gesundheitsdaten. Zu 4: Niemand wird ausgesperrt, und ins bestehende Konto kommt die Person trotzdem nie (Frage beim Umsetzen, Protokoll in #5). Zur Technik: Ein eigenes Kontenmodell empfiehlt Django zu Projektbeginn, weil ein späterer Wechsel aufwendig ist; mit #5 entstehen die ersten Konten. Die Login-Pflicht als Grundeinstellung schützt auch Adressen, bei denen jemand den Schutz vergisst. Die Keycloak-Testumgebung entsteht so bei jedem Start gleich, auch bei einer schon bestehenden Datenbank; das 7 KB große Einrichtungsskript des alten Repos entfällt.

**Umsetzung:** `accounts/` (Modell, Anpassungen an allauth, Seiten, Hinweise), `config/settings.py`, `config/urls.py`, `core/views.py`, `core/templates/core/start.html`, `dev/docker-compose.yml`, `dev/keycloak/dpv-realm.json`, `.env.example`, `.github/workflows/ci.yml`, `README.md`, Tests in `tests/test_login.py`, `tests/test_rundumtest.py` und `tests/test_keycloak_echt.py`.

## 2026-10-21 · Projektordner auf dem Mac außerhalb von iCloud

**Entscheidung** (Sebastian, #23): Das Projekt liegt auf dem Mac in `~/Entwicklung/dpv-participant-management`, nicht in „Dokumente“ oder „Schreibtisch“. Das README nennt diesen Ort.

**Begründung:** Am 21.10.2026 waren fünf Kopien wie `pyproject 2.toml` versehentlich in einem Commit zu #6 (vor dem Pull Request entfernt). Belegt ist: Sebastians Ordner „Dokumente“ wird mit iCloud abgeglichen. Annahme: iCloud legt solche Kopien bei Konflikten an, etwa wenn git viele Dateien auf einmal ändert, und kann auch Dateien in `.git` doppeln oder nur in der Cloud behalten. Außerhalb von iCloud entfällt die Ursache. Nichts geht verloren, weil alles auf GitHub liegt.

**Umsetzung:** `README.md` („Projekt starten (Mac)“, Schritte 2 und 3), Test in `tests/test_grundgeruest.py`. Den bestehenden Ordner verschiebt Sebastian selbst (Anleitung im Pull Request). Zusätzlich sperrt auf Sebastians Mac `.git/info/exclude` Dateien nach dem Muster „Name Leerzeichen Zahl“ für git; das gilt nur dort und steht nicht im Repo.

## 2026-10-21 · Fehlerprotokoll ohne Personendaten

**Entscheidung** (Sebastian, Klärung von #6 am 20.10.2026 und Nachklärung am 21.10.2026):

1. **Fehlernummer:** Bei einem unerwarteten Fehler zeigt die Fehlerseite einen kurzen Hinweis in der Du-Form und eine zufällige Fehlernummer (z. B. `7F3K-92QA`). Dieselbe Nummer steht im Log. Wer einen Fehler meldet, nennt die Nummer.
2. **Kein Bezug zum Konto im Log,** auch keine interne Kontonummer. Ob das Log doch einen braucht, klärt Sebastian mit der Datenschutzperson (OP-2, vorgemerkt in #11).
3. **Muster statt echter Adresse:** Im Log steht das Muster der Adresse (z. B. `/anmeldungen/<int:pk>/`), nie die echte Adresse mit Nummern und nie angehängte Parameter. Passt eine Adresse zu keinem Muster, steht dort „unbekannte Adresse“.
4. **Kein Meldungstext im Log:** Von einem Fehler kommen nur seine Art (z. B. `ValueError`) und die Stellen im Code ins Log, nie sein Meldungstext. Das gilt für alle Log-Einträge, auch aus fremden Paketen.
5. **„Nicht gefunden“, „kein Zugriff“ und „ungültige Anfrage“** stehen als kurze Zeile im Log: Zeitpunkt, Art und Muster der Adresse, ohne Fehlernummer, ohne Bezug zum Konto und ohne frei gewählten Text aus der Anfrage. Djangos eigene Zeilen dazu sind abgeschaltet.
6. **Keine Fehlerberichte per Mail.** Djangos eingebaute Funktion dafür ist abgeschaltet.

**Begründung:** DSG-08: Echte Personendaten gelangen nie in KI-Werkzeuge, auch nicht zur Fehlersuche; Logs werden dafür leicht kopiert, sind schlechter geschützt als die Datenbank und werden länger aufbewahrt. Auch eine Kontonummer ist ein Personendatum. Schon eine Adresse wie `/konto/17/` kann sie enthalten, und Meldungstexte enthalten oft genau die eingegebenen Daten (z. B. „Mail … existiert schon“). Die Fehlernummer genügt für den häufigsten Fall, dass sich jemand meldet. Folge: Ein Fehler ist ohne Meldungstext schwerer zu finden; er wird lokal mit erfundenen Daten nachgestellt. Viele „kein Zugriff“ können ab P2 zeigen, dass jemand fremde Daten sucht, deshalb bleiben diese Zeilen. „Ungültige Anfrage“ (Nachtrag vom 21.10.2026 nach der unabhängigen Prüfung) zeigt z. B. einen falsch eingestellten Servernamen, bei dem das Tool jede Anfrage ablehnt. Der Fahrplan nennt Fehlerberichte per Mail mit Anfragedaten als Fehler des alten Tools (Abschnitt 6, Nr. 8).

**Umsetzung:** `core/errors.py`, `config/settings.py` (`LOGGING`, `ADMINS`, `MIDDLEWARE`), `config/urls.py`, `core/templates/500.html`, Tests in `tests/test_fehlerprotokoll.py`. Nicht Teil: freundliche Seiten für „nicht gefunden“ und „kein Zugriff“ (#21), Aufbewahrung der Logs und Zugriffsprotokoll des Webservers im Betrieb (#11).

## 2026-10-21 · Grundgerüst: nur grüne Pull Requests, Werkzeuge und Fassungen

**Entscheidung:**

1. **Nur grüne Pull Requests** (Sebastian, Klärung von #4 am 20.10.2026): Die KI schickt den Link zu einem Pull Request erst, wenn alle Prüfungen auf GitHub für den letzten Stand grün sind, und nennt das Ergebnis in der Beschreibung. Sebastian übernimmt keinen Pull Request mit roter Prüfung. Die Regel ersetzt die Sperre durch GitHub, bis das Repo veröffentlicht ist (#16).
2. **Werkzeuge und Fassungen** (KI, technisch):
   - `uv` verwaltet Python und Pakete. Kurze Paketliste in `pyproject.toml`, feste Fassungen in `uv.lock`.
   - Python genau 3.13, festgelegt in `.python-version` und `pyproject.toml`. Django 6.1 wie entschieden am 20.10.2026.
   - PostgreSQL 18, lokal in Docker (`dev/docker-compose.yml`) und in der Prüfung auf GitHub. Die Tests laufen nur gegen PostgreSQL, nie gegen eine Ersatzdatenbank.
   - Alle Prüfungen stehen in `pruefen.sh`. GitHub ruft dasselbe Skript auf; lokal und auf GitHub wird gleich geprüft.
   - Zugangsdaten kommen aus Umgebungsvariablen; lokal aus `.env`, die `uv run --env-file .env` einliest. Fehlt eine Pflichtangabe, startet das Tool nicht. Die Fehleranzeige für Entwickler ist nur an, wenn sie ausdrücklich eingeschaltet ist.
   - Fremde Bausteine im Prüfablauf auf GitHub sind auf einen festen Commit festgelegt.

**Begründung:** Zu 1: GitHub sperrt das Übernehmen roter Pull Requests bei privaten Repos ohne GitHub Pro nicht (Protokoll zu #4). Zu 2: `uv` installiert auch die passende Python-Fassung und macht die Startprobe einfacher (Protokoll zu #4). Die feste Python-Fassung ist nötig: Auf Sebastians Mac lagen am 21.10.2026 drei Python-Fassungen, und `uv` griff ohne Festlegung zu 3.11 und wich still auf Django 5.2 aus (Befund der KI). 3.13 statt 3.14, weil 3.13 länger erprobt ist und Django 6.1 beide unterstützt; die Fassung auf dem DPV-Server ist noch offen (OP-4). PostgreSQL 18 ist die neueste Hauptfassung; PostgreSQL pflegt jede Hauptfassung fünf Jahre, bei Erscheinen 2025 also bis 2030 (aus dem Wissen der KI, nicht eigens nachgesehen); die Fassung auf dem Server ist ebenfalls offen (OP-4). Ein gemeinsames Prüfskript verhindert, dass lokal etwas anderes geprüft wird als auf GitHub. Feste Commits verhindern, dass eine Änderung an einem fremden Baustein unbemerkt in die Prüfung gelangt. `uv run --env-file` liest die Umgebungsdatei ohne zusätzliches Paket.

**Umsetzung:** `CLAUDE.md` (Ablauf je Aufgabe, Schritte 4 und 6; Erfahrung „Erst alles hochladen“), `CONTRIBUTING.md` (Abschnitte 6 und 8), `.github/pull_request_template.md`, `README.md` („Projekt starten“), Pull Request zu #4.

## 2026-10-21 · P1 beginnt früher, Restpunkte von P0 laufen parallel

**Entscheidung** (Sebastian): Phase P1 „Gerüst“ beginnt am 21.10.2026 statt wie bisher vorgesehen am 30.11.2026. Die Restpunkte von P0 erledigt Sebastian parallel: Anfragen zu OP-1, OP-2 und OP-4 verschicken (bis 15.11.2026), altes Repo archivieren, Stundenlog führen; dazu, mit gleicher Frist wie E0, Liste 1 dem DPV mitteilen (OP-6, bis 29.11.2026). Prüfpunkt E0 bleibt am 29.11.2026; die Zieldaten im Fahrplan bleiben unverändert.

**Abweichung vom Fahrplan:** Das Ziel von P0 lautet „Rahmen steht, bevor Code entsteht“, und E0 sagt für den Fall ohne Antwort des DPV „P1 beginnt trotzdem“; beides setzt voraus, dass P1 erst nach E0 beginnt. Jetzt entsteht Code schon vor E0. Der Fahrplan bleibt unverändert, für den Beginn von P1 gilt dieser Eintrag.

**Begründung:** Die P1-Issues #4 bis #7 sind geklärt und haben keine offenen Fragen. Die beiden Klärungen für P1 werden erst gegen Ende der Phase gebraucht und haben laut OP-Tabelle Übergangslösungen: der Test-Client (OP-1, bis 31.01.2027; sonst ein eigenes Keycloak der Testumgebung) und der Testserver (OP-4, bis 28.02.2027; sonst ein eigener Testserver). OP-2 blockiert erst den Gesundheitsblock in P2 (spätestens 31.05.2027; sonst rückt er an den Anfang von P4) und Tor E3; die Zwischenschritte (Ansprechperson bis 31.12.2026, Entwurf bis 31.01.2027) laufen bei Sebastian neben P1. Ein früherer Beginn verschiebt keinen Termin nach hinten, sondern schafft Reserve (Einschätzung der KI). Die Restpunkte von P0 sind Sebastians eigene Aufgaben und keine Programmierarbeit; der Grundsatz „zwei Phasen parallel geht für eine Person nicht“ (`docs/fahrplan.md`, Kritischer Pfad) betrifft das Bauen und bleibt deshalb unberührt (Einschätzung der KI). Hinweis der KI: Die Stundenrechnung des Fahrplans zählt ab dem 26.10.2026; Stunden ab dem 21.10.2026 kommen trotzdem ins Stundenlog.

**Umsetzung:** `README.md` („Stand“). Vor dem Beginn hat die KI nach `CLAUDE.md` alle offenen Issues mit `vorgemerkt` oder ohne Phasen-Label durchgesehen (#8 bis #17); keines gehört nach P1, kein Label war zu korrigieren.

## 2026-10-20 · Auskünfte zum Keycloak des DPV, Phasen-Labels und vorgemerkte Issues

**Entscheidung** (Sebastian):

1. **Keycloak des DPV** (Auskunft von Sebastian): Die Selbstregistrierung ist erlaubt. Benutzername und Mail sind bei jedem Konto vorhanden, sind die festen Werte und ändern sich nicht; Vor- und Nachname können fehlen oder sich ändern. Unverändert gilt laut Fahrplan (P1): Das Tool verknüpft Konten über die feste Kennung (`sub`).
2. **Phasen-Labels:** Issues tragen das Label der Phase (`P0` bis `P10`), in die sie voraussichtlich gehören; ist sie unklar, keins. Das Label ist nur Orientierung, nie ein Filter.
3. **Vorgemerktes:** Was beim Klären auf später verschoben oder noch ungeklärt für eine spätere Phase angelegt wird, bekommt ein eigenes Issue mit dem Label `vorgemerkt`. Vor Beginn jeder Phase werden alle offenen vorgemerkten Issues und alle ohne Phasen-Label durchgesehen, nicht nur die der Phase.

**Begründung:** Zu 1: Die Auskünfte betreffen OP-1 schon jetzt, nicht erst mit dem Pull Request zu #5. Zu 2 und 3: Verschobene Punkte standen nur unter „Nicht Teil dieser Anforderung“ und wären mit dem Schließen des Issues aus dem Blick geraten (Hinweis der KI). Phasen-Labels geben die Übersicht; weil sich eine Zuordnung als falsch erweisen kann, sieht jede Phase alle vorgemerkten Issues und alle ohne Phasen-Label durch, und ein Fehler fällt spätestens beim nächsten Phasenbeginn auf.

**Umsetzung:** `CLAUDE.md` („Für Phasen und Vorgemerktes gilt“), `.claude/skills/issue-anlegen/SKILL.md` und `.claude/skills/grill-me/SKILL.md`, Labels `vorgemerkt` und `P0` bis `P10` auf GitHub, Issues #8 bis #17. Dazu Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt: OP-1 in `docs/fahrplan.md` (OP-Tabelle, Abschnitt 6 Nr. 39) und in `docs/anforderungen.md` (Offene Punkte) um die Auskunft aus Punkt 1 ergänzt.

## 2026-10-20 · Offene Punkte aus der Bestandsaufnahme

**Entscheidung** (Sebastian):

1. Die Stundenschwelle an E1 wird nicht weiter geklärt. Der Plan rechnet mit rund 7,5 Stunden je Woche, E1 verlangt 8, die Risikotabelle warnt unter 30 Stunden im Monat. Der Unterschied bleibt so stehen. Das Stundenkontingent soll das Projekt nicht weiter belasten. Der Fahrplan bleibt dafür unverändert.
2. Die Go/No-Go-Kriterien und die Betriebsspur aus dem Doc „Fahrplan Neubau“ kommen nicht ins Repo. Sie werden nicht mehr betrachtet.
3. Die fehlenden Diagramme hat Sebastian lokal. Das Diagramm zum Lebenszyklus einer Veranstaltung ergänzt er, wenn ein Issue den Lebenszyklus berührt. Damit das nicht vergessen wird, fragt `grill-me` dann danach.
4. Das Repo bleibt privat, bis das Tool in einen echten Test geht. Dann veröffentlicht Sebastian es. Dafür ändert sich keine Datei.

**Begründung:** Zu 2: Der Weg des Neubaus ist geklärt. Die Prüffragen von E1 stehen im Fahrplan selbst, den Betrieb regeln P6 und das Betriebshandbuch (Einschätzung der KI). Zu 4: Die EUPL wirkt erst, wenn das Repo veröffentlicht oder weitergegeben wird (Hinweis der KI).

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, P2, E1, Abschnitt 6 Nr. 35 bis 38), `.claude/skills/grill-me/SKILL.md` (Abschnitt 1). Dazu Vorschläge der KI, denen Sebastian mit dem Übernehmen des Pull Requests zustimmt: `docs/anforderungen.md`, OP-6 und Risikotabelle bei ROL-04 auf den Stand der Entscheidung vom 20.10.2026 gebracht (Protokoll in P2, Benachrichtigung in P8); Abschnitt 6 Nr. 7 und Nr. 26 im Fahrplan mit je einem erklärenden Hinweis.

## 2026-10-20 · Code aus dem alten Repo darf übernommen werden

**Entscheidung** (Sebastian): Code und Codeschnipsel aus dem alten Repo dürfen übernommen werden, wenn es dafür logische und sinnvolle Anwendungsfälle gibt. Sebastian hat dafür die Erlaubnis; sie wurde mündlich erteilt. Ersetzt im Eintrag „Neustart, Name, Lizenz, Umfang und Technik“ den Satz „Kein Programmcode wird übernommen“; auf dem alten Code wird weiterhin nicht weitergebaut.

**Begründung:** Der Fahrplan nannte die ungeklärte Lizenz als Hürde für jede Codeübernahme (Abschnitt 1, Punkt 5); die Erlaubnis räumt sie aus. Der Neustart bleibt, weil er vor allem am Datenmodell hängt (Punkte 1 bis 4) und laut Abschnitt 2 kein Baustein ohne Umbau passt. Sinnvoll sind deshalb vor allem kleine, in sich geschlossene Teile, etwa die KJP-Generatoren für LIS-03 (Einschätzung der KI).

**Umsetzung:** `CONTRIBUTING.md` (Abschnitt 10), `CLAUDE.md`, `README.md`, `.github/pull_request_template.md`, `docs/fahrplan.md` (Abschnitt 1, „Was ausdrücklich nicht gemacht wird“).

## 2026-10-20 · Klärungen zu OP-1 und OP-4, Arbeitsannahme zu OP-2, Gesundheitsdaten im Anforderungsdokument

**Entscheidung** (Sebastian):

- OP-1: Struktur, Rollen und Kreise verwaltet das Tool selbst (ORG-06). Der Keycloak-Login dient nur dazu, Personen zu verifizieren; mehr aus Keycloak kann später nachgeholt werden. Ein Lesekonto gibt es nicht. Personen mit Account dürfen selbst einwilligen (ab welchem Alter, prüft OP-2). Test-Client und Meldung gelöschter oder gesperrter Konten klärt Sebastian.
- OP-2 (Arbeitsannahme, keine Freigabe): Sebastian schätzt ein, dass die stellvertretende Bestätigung durch die anmeldende Leitung reicht (DSG-01), die Einwilligung nach Volljährigkeit fortgilt (DSG-02) und die Folgenabschätzung die Speicherung im eigenen Profil (FRM-04) mit abdecken soll. Bestätigen oder verwerfen muss das die Datenschutzperson des DPV, vor dem Gesundheitsblock und vor E3. Die übrigen OP-2-Schritte folgen wie im Fahrplan.
- OP-4: Ansprechperson für den Betrieb und Testserver klärt Sebastian. Mails gehen über das Google Workspace des DPV, wenn die Anbindung technisch möglich ist.
- Anforderungsdokument: Die drei Sätze zu Gesundheitsdaten (Einleitung und Verarbeitungen im Abschnitt Datenschutz, Risikotabelle) sind an FRM-04 angepasst (Vorschläge der KI, von Sebastian angenommen). Die Folgeänderungen aus der OP-1- und OP-4-Entscheidung bei ORG-05, ORG-06, OP-1, OP-4 und in der Risikotabelle sind Vorschläge der KI; Sebastian stimmt ihnen mit dem Übernehmen des Pull Requests zu.

**Begründung:** Die Abhängigkeit vom Verbands-Keycloak bleibt so klein wie möglich (ORG-03). Das Google Workspace nutzt der DPV bereits. Hinweise der KI: Ohne Lesekonto findet das Tool nur Personen, die sich schon einmal angemeldet haben. Ein Konto in Google Workspace darf laut Google 2.000 Mails pro Tag senden; bei Überschreitung ist der Versand bis zu 24 Stunden gesperrt, deshalb verteilt der Postausgang den Versand. Ob Jugendliche mit Account selbst einwilligen können, hängt am Alter und wird unter OP-2 mitgeprüft. Google Workspace als Mail-Dienstleister gehört in die Auftragsverarbeitung und das Verzeichnis der Verarbeitungen (OP-2).

**Umsetzung:** `docs/anforderungen.md` (Datenschutz, Risiken; Folgeänderungen bei ORG-05, ORG-06, OP-1 und OP-4), `docs/fahrplan.md` (Abschnitt 1, Planungsgrundlagen, Liste 2, P0, P5, kritischer Pfad, OP-Tabelle, E3, Risiken).

## 2026-10-20 · Kein Hitobito, eigenes Tool

**Entscheidung** (Sebastian): Statt Hitobito einzusetzen, wird das eigene Tool gebaut.

**Begründung:** Sebastian hat sich Hitobito angesehen. Es ist nicht so ansprechend und bedienungsfreundlich, wie er es sich wünscht. Das Anforderungsdokument verlangt ein Tool, das „freundlich in der Bedienung“ ist (Ausgangslage und Motivation). Hinweis der KI: Die Prüffrage von E0 im Fahrplan (deckt Hitobito Gesundheitsdaten pro Anmeldung, Teilnahmekreise und Keycloak-Login ohne eigene Programmierung ab?) ist damit nicht beantwortet. Entschieden hat die Bedienbarkeit.

**Umsetzung:** Dieser Eintrag ist das Ergebnis, das P0 verlangt („Hitobito geprüft und Ergebnis notiert“).

## 2026-10-20 · Entscheidungen nach der Prüfung der Rückmeldungen

**Entscheidung** (Sebastian, jeweils auf Empfehlung der KI):

1. Anforderungen und Fahrplan liegen maßgeblich im Repo (`docs/anforderungen.md`, `docs/fahrplan.md`). Änderungen laufen über Pull Requests. Die Docs in Claude bleiben als Stand vom 20.10.2026.
2. FRM-04: Die freiwillige Speicherung eigener Gesundheitsangaben im Profil bleibt, unter Vorbehalt. Sie wird in P4 als letzter Teil gebaut und entfällt, wenn die Datenschutz-Folgenabschätzung (OP-2) abrät oder bis dahin nicht fertig ist.
3. ROL-04: Das Protokoll der Rollenänderungen kommt in P2. Die Benachrichtigung Entfernter bleibt in P8.
4. Kontrolle: Sebastian prüft über die Rechtematrix in Klartext (ab P2) und eine Startprobe ohne KI an E1, E3 und E6: das Projekt allein nach dem README starten und die Tests laufen lassen. Code lesen lernt er aus eigenem Interesse nach und nach dazu, außerhalb der 8 Stunden pro Woche; die Lernzeit steht getrennt im Stundenlog (Ergänzung der KI).

**Begründung (Zusammenfassung der KI):**

1. Am 20.10.2026 konnte die Arbeitssitzung die beiden Docs zweimal nicht lesen; erst ein Export half. Die KI arbeitet im Repo, also gehören die maßgeblichen Texte dorthin.
2. Das Anforderungsdokument widerspricht sich: FRM-03, FRM-04 und BER-01 erlauben die Speicherung im eigenen Profil, die Datenschutz-Einleitung und die Risikotabelle sagen „nur pro Anmeldung“. Die Einzelregeln sind genauer; die Folgenabschätzung entscheidet, ob es dabei bleibt.
3. Das Anforderungsdokument verlangt selbst „ROL-04 früh einplanen“ (OP-6) und nennt das Risiko „unbemerkter Zugriff auf Daten von Kindern“. Echte Daten kommen ab E3 (Juni 2028), ROL-04 stand erst in P8. Kosten rund 4 Stunden (Annahme).
4. Wer den Code nicht liest, braucht ein Prüfwerkzeug in Klartext. Die Startprobe erfüllt die Gegenmaßnahme „Projekt ohne KI start- und testbar“ aus dem Anforderungsdokument. Lernzeit getrennt, damit das Stundenlog an E1 die tatsächliche Entwicklungszeit zeigt.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, Phasen, Abschnitt 6), `docs/pruefung-2026-10-20.md`.

## 2026-10-20 · Django 6.1 mit django-allauth, Gestaltung ohne Build-Schritt

**Entscheidung** (KI, technisch):

- Start auf Django 6.1 mit django-allauth als Login-Baustein. Umstieg auf 6.2 LTS gleich zu Beginn von P3, auf Django 2029 in P8.
- Rückfall: Läuft allauth in P1 nicht mit dem Keycloak-Testzugang, Start auf Django 5.2 mit mozilla-django-oidc.
- Gestaltung mit einer CSS-Grundlage ohne Build-Schritt (Bootstrap oder Pico.css). Die Wahl fällt in P1 an der Musterseite. Alle Dateien kommen vom eigenen Server, nicht von fremden.

**Begründung:** Django 5.2 bekommt seit dem 03.12.2025 nur noch Sicherheitsupdates, bis April 2028. mozilla-django-oidc, der Login-Baustein des alten Tools, gibt Unterstützung nur bis Django 5.2 an (PyPI, Fassung 5.0.2 vom 19.12.2025). django-allauth gibt 6.0 und 6.1 an (PyPI, Fassung 65.20.0 vom 16.10.2026). Django 6.1 bekommt Sicherheitsupdates bis Dezember 2027, 6.2 LTS bis April 2030 (djangoproject.com, abgerufen am 20.10.2026). Tailwind braucht einen Build-Schritt; den vermeidet der Plan.

**Umsetzung:** `docs/fahrplan.md` (Planungsgrundlagen, P1, P3, Risiken).

## 2026-10-20 · Neustart, Name, Lizenz, Umfang und Technik

**Entscheidung:**

- Neustart statt Weiterbau des alten Tools (`sebivtt/scout-participant-management`). Kein Programmcode wird übernommen, nur Regeln und Werkzeuge aus Sebastians Sitzungen seit dem 14.10.2026 (Sebastian).
- Name „DPV Anmeldetool“, Repo `sebivtt/dpv-participant-management`, Lizenz EUPL-1.2 (Sebastian).
- Liste 1: DSG-03, ORG-07, DSG-09 und der volle Nachweis von NFA-05 kommen fest nach der Generalprobe, jeweils mit Übergang (Sebastian).
- Start am 26.10.2026; 8 Stunden pro Woche im Jahresschnitt, Betrieb eingerechnet; Stundenlog ab P0 (Sebastian).
- Technik (KI): Django mit serverseitig erzeugten Seiten und htmx, Alpine.js für kleine Logik, SortableJS für den Formular-Baukasten, PostgreSQL. Login nur per OIDC über den Keycloak des DPV, ohne Schreibzugriff dort. Mails über einen Postausgang in der Datenbank, kein Celery und kein Redis.
- Arbeitsweise aus dem alten Repo übernommen (dort entschieden am 15. und 16.10.2026): Regeln in `CONTRIBUTING.md`; Fehler und Anforderungen nur als Issue; Issues erst mit `grill-me` klären und nur mit Label `geklärt` umsetzen; ein Issue ergibt einen Pull Request mit eigenem Test; unabhängige Prüfung vor jedem Pull Request.

**Begründung:** Fahrplan, Abschnitt 1 (fünf Punkte, am Code des alten Tools geprüft) und Abschnitt 3 (Machbarkeit bei 8 Stunden pro Woche).

**Umsetzung:** `LICENSE`, `docs/fahrplan.md`, `CONTRIBUTING.md`, `CLAUDE.md`.
