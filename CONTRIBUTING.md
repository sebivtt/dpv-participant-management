# Regeln für die Entwicklung

Diese Regeln gelten für jede Änderung, egal ob von Menschen oder KI. Sie sollen sicherstellen, dass der Code verständlich, getestet und sicher bleibt, auch wenn ihn niemand Zeile für Zeile prüfen kann. Übernommen aus dem Vorgänger-Repo (vereinbart am 15.10.2026), angepasst am 20.10.2026.

Was ein Programm prüfen kann, prüft GitHub bei jeder Änderung automatisch, sobald es Code gibt (ab P1). Die übrigen Regeln sind mit „(Review)“ markiert. Wo eine Regel erst ab einer späteren Phase greift, steht die Phase dabei.

## 1. Sprache

- **Code auf Englisch:** Namen von Variablen, Funktionen, Klassen, Dateien und Feldern.
- **Erklärungen auf Deutsch:** Kommentare, Docstrings, Dokumentation, Commit-Nachrichten, Pull Requests, Meldungen für Nutzende.
- Fachbegriffe folgen dem Glossar am Ende von `docs/anforderungen.md`: im Code `registration`, im Text „Anmeldung“. Das Glossar nennt keine Code-Namen; wer einen Fachbegriff zum ersten Mal im Code verwendet, hält den englischen Namen in `docs/entscheidungen.md` fest, damit alle denselben nehmen. (Review)
- Oberflächentexte und Mailvorlagen sind gendersensibel formuliert (NFA-09) und stehen nicht fest im Code, sondern in übersetzbaren Texten (NFA-02). (Review)

## 2. Verständlichkeit

- **Kommentare erklären das Warum, nicht das Was.** „Neue Anmeldungen enden mit der Änderungsfrist, sonst gäbe es Anmeldungen, die niemand mehr ändern kann“ ist hilfreich. „Prüft das Datum“ ist es nicht. (Review)
- **Jede öffentliche Funktion und Klasse hat einen Docstring:** ein Satz, was sie tut, dazu die Regeln oder Grenzfälle, die nicht offensichtlich sind. (Review)
- **Funktionen bleiben überschaubar:** zyklomatische Komplexität höchstens 12. Grob heißt das: nicht mehr als etwa zehn Verzweigungen. Wird es mehr, wird aufgeteilt. (automatisch ab P1, `ruff` C901)
- **Gestaltung aus Bausteinen: einbinden, nicht kopieren.** Seiten binden die entschiedenen Bausteine aus dem Bausteinkatalog (`/bausteine/`) ein, statt ihr Aussehen nachzubauen; Regeln in `docs/gestaltung.md`. (automatisch ab P2 für Eingabefelder und Vorlagenstücke, `tests/test_bausteinkatalog.py`; sonst Review)
- **Kein auskommentierter Code.** Alte Fassungen stehen in der Git-Historie. (Review)
- **Kein `print()`** im Anwendungscode, stattdessen `logging`. Ausnahme: Verwaltungsbefehle (`manage.py`). (automatisch ab P1, `ruff` T20)
- Fehler werden gezielt abgefangen, nie pauschal (`except:` oder `except Exception: pass`). (automatisch für `except:`, sonst Review)
- `# noqa` nur mit Regelnummer und Begründung nach `--`. Braucht eine Zeile die Ausnahme, weil ihr Fehlen still etwas kaputt machen würde (z. B. ein Import, der etwas anmeldet), bekommt sie einen Test, der das bemerkt. (automatisch ab P1, `ruff` PGH004 und RUF100; Begründung und Test: Review)

## 3. Korrektheit und Tests

- **Jede fachliche Regel hat einen Test**, der sie in Alltagssprache benennt, z. B. `test_nach_anmeldeschluss_keine_neue_anmeldung`. (Review)
- **Erst der Test, dann der Code.** Ein neuer Test muss vor der Änderung fehlschlagen, und zwar aus dem richtigen Grund. Bei neuen Funktionen entsteht dafür zuerst ein leeres Gerüst (Adresse, Funktion), damit der Test an der fachlichen Regel scheitert und nicht daran, dass etwas fehlt. Jeder behobene Fehler bekommt einen Test, der ohne die Behebung fehlschlägt. Ändert ein Pull Request Code, kommen die Tests als eigener Commit vor dem Code (ein leeres Gerüst darf als eigener Commit davor stehen), und die Beschreibung nennt beide Kennungen. So ist der Stand mit den Tests vor dem Code jederzeit auffindbar; ob er aus dem richtigen Grund rot ist, zeigt erst ein Lauf. *Code* heißt dabei jede Datei außer unter `docs/`, `tests/`, `rauchtests/`, `containertests/`, `.github/ISSUE_TEMPLATE/` und außer `*.md`; auch Prüfskripte, CI und `.claude/`-Einstellungen sind Code. Ohne Code entfällt der Test-Commit; das ist unabhängig davon, ob Szenarien nötig sind. (automatisch: Prüfung „PR-Angaben“ prüft, dass der Test-Commit genannt ist, nur Tests ändert und kein Code vor ihm liegt; ob er aus dem richtigen Grund rot ist und ob ein Gerüst nur Gerüst ist: Review)
- **Bestehende Tests werden nur geändert oder gelöscht, wenn sich die zugehörige Anforderung geändert hat.** Der Pull Request nennt das ausdrücklich. Schlägt ein alter Test fehl, wird der Code repariert, nicht der Test. (Review)
- **Eine Prüfbedingung wird nicht gelockert, um einen Lauf grün zu bekommen.** Wird in einem bestehenden Test oder gegenüber einem Szenario oder Akzeptanzkriterium eine Zusicherung, ein Grenzwert oder ein Zeitfenster schwächer oder ein Test übersprungen, geschieht das nur in einem eigenen Issue, nie im selben Pull Request. Hat ein neuer Test eine Anforderung falsch übersetzt, wird er im selben Pull Request korrigiert; die Beschreibung nennt das unveränderte Kriterium, vorher und nachher. Ein roter Lauf allein ist dafür kein Grund. (Review)
- **Rauchtest am PC und am Handy, je einmal nur mit der Tastatur:** Jede neue Seite und jede Seite, die neue Bedienelemente bekommt (Knopf, Feld, Dialog), bekommt ihren Rauchtest im Browser am PC und am Handy, dazu je einen Durchgang nur mit der Tastatur. Ein Durchgang darf mehrere Seiten abdecken. (Review; `docs/entscheidungen.md`, 27.10.2026, #78)
- Bekannte, noch offene Fehler werden als `@pytest.mark.xfail(strict=True, raises=..., reason=...)` festgehalten. `raises` nennt genau die erwartete Fehlerart. Wird einer behoben, meldet der Testlauf das, und die Markierung muss weg. (automatisch ab P1, außer `raises`: Review)
- Bekannte unsichere Muster (abgeschaltete Zertifikatsprüfung, Passwörter im Code, verschluckte Fehler, unsichere Aufrufe) meldet ruff. (automatisch ab P1, `ruff` S)
- Keine ungenutzten Importe oder Variablen. (automatisch ab P1, `ruff` F)

## 4. Rechte und Datenschutz

- **Rechte werden auf dem Server geprüft, nie nur in der Oberfläche. Was nicht ausdrücklich erlaubt ist, ist verboten.** (Review)
- **Jede Adresse verlangt einen Login**, außer sie ist ausdrücklich als öffentlich markiert und begründet. (automatisch ab P1, Rundumtest)
- **Personen- und Anmeldedaten werden nur über die zentrale Rechteprüfung gelesen oder geändert**, nie mit eigenen Abfragen in einer einzelnen Seite. (ab P2 automatisch über den Rundumtest, sonst Review)
- **Schreibende Adressen prüfen das Recht auf das betroffene Objekt**, nicht nur den Login. Die Zugehörigkeit (Veranstaltung, Anmeldung) kommt aus der Adresse, nie aus dem Inhalt der Anfrage, sonst lässt sich ein Eintrag in eine fremde Veranstaltung schieben. (Review; ab P2 Tests aus der Rechtematrix)
- **Keine internen Nummern auf Seiten, jede Adresse mit Kennung hat einen Test „wie nicht vorhanden“:** Keine Seite zeigt die interne Nummer einer Person oder Einheit, weder in Links und Parametern noch in Formularfeldern oder im Text; Einträge stehen dort nur mit ihrer zufälligen Kennung und werden über `request.rights.entry()` geholt. Jede Adresse mit Kennung (`<key:…>`) hat mindestens einen Test, der ihren verbotenen Fall mit `assert_like_missing` als „genau gleich wie nicht vorhanden“ prüft und dafür `@pytest.mark.wie_nicht_vorhanden("<Muster der Adresse>")` trägt. (automatisch ab P2, Rundumtest; ob der Test den richtigen verbotenen Fall wählt: Review)
- **Jede Zeile der Rechtematrix** (ab P2) (`docs/rechtematrix.md`) hat einen Test für den erlaubten und einen für den verbotenen Fall. Die Tests tragen die Kennung ihrer Zeile (`@pytest.mark.rechtematrix("VP-02")`). (automatisch ab P2: Eine gebaute Zeile ohne beide Tests macht `tests/test_rechtematrix.py` rot; sonst Review)
- **Neue Daten → sofort Rechte klären:** Wer neue Daten ins Tool bringt, ergänzt im selben Pull Request die Zeilen der Rechtematrix: wer sie sehen, anlegen, bearbeiten und löschen bzw. verwalten darf, erlaubt und verboten. (automatisch ab P2: Eine Tabelle in der Datenbank, die in der Matrix fehlt, macht `tests/test_rechtematrix.py` rot; sonst Review)
- **Gesundheitsdaten** stehen nie in Logs, Mails, Benachrichtigungen oder Adressen (URLs). (Review; ab P1 Logtest)
- **Eingegebenes HTML** (Einladungstexte, Mailvorlagen) wird beim Speichern mit `nh3` auf die erlaubten Formatierungen bereinigt. Platzhalter in Mails werden escaped. (ab P3, Test mit eingeschleustem Skript)
- **Keine echten Personendaten** in Tests, Testdaten, Logs, Bildschirmfotos oder KI-Werkzeugen, auch nicht zur Fehlersuche (DSG-08). Fehler aus dem Betrieb werden lokal mit erfundenen Daten nachgestellt. (Review)
- **Keine Passwörter oder Schlüssel im Code** (NFA-10). Zugangsdaten stehen in Umgebungsdateien, die `.gitignore` aus dem Repo heraushält; ins Repo kommen nur Vorlagen mit erkennbar erfundenen Werten (`*.example`). (Review; ab P1 zusätzlich `ruff` S)

## 5. Effizienz

- **Listen dürfen nicht pro Eintrag neue Datenbankabfragen auslösen** (N+1-Muster). Zugehörige Daten werden mit `select_related` oder `prefetch_related` vorab geladen. (automatisch ab P1 für die getesteten Seiten)
- Neue Listen bekommen einen Skalierungstest: Die Zahl der Abfragen darf bei 10 Einträgen nicht höher sein als bei einem. (Review)
- Externe Dienste (Keycloak, Mail) werden höchstens einmal pro Anfrage gefragt, nicht pro Listeneintrag. (Review)

## 6. Abhängigkeiten

- **Neue Pakete nur mit Begründung im Pull Request:** Wofür, warum nicht selbst gelöst, wird es gepflegt, welche Lizenz? Die Lizenz muss mit der EUPL-1.2 verträglich sein. (Review)
- Die Pakete stehen in einer kurzen Liste (`pyproject.toml`); daraus erzeugt `uv` die Liste mit festen Fassungen (`uv.lock`), die nie von Hand bearbeitet wird. (automatisch ab P1: `uv lock --check` meldet, wenn beide nicht zusammenpassen)
- Pakete mit bekannten Sicherheitslücken blockieren die Übernahme. (automatisch ab P1, `pip-audit`)
- Gestaltung und Skripte für den Browser kommen vom eigenen Server, nicht von fremden Servern. (Review)

## 7. Datenbank

- Änderungen am Datenmodell kommen mit Migration. (automatisch ab P1)
- Vor dem Übernehmen werden die Migrationen eines Branches zu möglichst einer zusammengefasst. Migrationen, die schon in `main` sind, werden nie geändert oder gelöscht. (Review)
- Was zusammen gelingen oder scheitern muss (z. B. eine Sammelanmeldung), läuft in einer Datenbank-Transaktion. Gleichzeitige Anfragen auf denselben Platz oder dasselbe Objekt bekommen einen Test. (Review)

## 8. Pull Requests

- **Klein und thematisch:** ein Thema pro Pull Request. (Review)
- **Nur grüne Pull Requests werden übernommen.** Alle Prüfungen auf GitHub müssen für den letzten Stand grün sein; die Beschreibung nennt das Ergebnis. Wer einen Pull Request zur Durchsicht schickt, tut das erst, wenn alles grün ist. GitHub sperrt das Übernehmen bei diesem privaten Repo nicht, deshalb gilt die Regel, bis die Sperre mit der Veröffentlichung kommt (#16). (Review, Entscheidung vom 21.10.2026)
- Die Beschreibung beginnt mit dem Abschnitt „Für Sebastian“: höchstens fünf Zeilen und 600 Zeichen, was sich ändert, was er ansehen sollte und was offen ist; Regeländerungen als „vorher / nachher“. (automatisch: Prüfung „PR-Angaben“ prüft Platz und Länge; ob der Kopf verständlich ist: Review)
- Die Beschreibung folgt der Vorlage (`.github/pull_request_template.md`) und erklärt in Alltagssprache:
  1. was sich für Nutzende ändert,
  2. welche Anforderungen, Regeln oder Entscheidungen umgesetzt sind,
  3. wie geprüft wurde: Tests für den erlaubten und den verbotenen Fall, tatsächlich ausgeführte Prüfungen mit Ergebnis,
  4. was nicht geprüft wurde und offen bleibt.
- Ändert ein Pull Request Datenmodell oder Rechte, nennt er die betroffenen Dateien, damit sie sich nachlesen lassen. (Review)
- **Neue Regeln und Entscheidungen** stehen in `docs/entscheidungen.md`, mit Datum. (Review)
- Änderungen an `docs/anforderungen.md` und `docs/fahrplan.md` nur mit Sebastians Zustimmung und mit einem Eintrag in `docs/entscheidungen.md`. (Review)

## 9. Die Pfadfinderregel

> Hinterlasse den Code besser, als du ihn vorgefunden hast.

Wer eine bestehende Funktion ändert, ergänzt dabei ihren Docstring, entfernt toten Code daneben und schreibt einen Test, falls keiner existiert.

## 10. Übernahme aus dem alten Repo

Seit dem 20.10.2026 dürfen Code und Codeschnipsel aus dem alten Repo `sebivtt/scout-participant-management` übernommen werden (`docs/entscheidungen.md`).

- **Nur, wo es sinnvoll ist:** wenn ein Teil ohne grundlegenden Umbau zum neuen Datenmodell passt und Übernehmen einfacher ist als neu schreiben. (Review)
- **Herkunft angeben:** Commit-Nachricht und Pull-Request-Beschreibung nennen Datei und Commit im alten Repo. (Review)
- **Gleiche Regeln:** Übernommener Code erfüllt dieselben Regeln wie neuer, mit Tests, Docstrings und Rechteprüfung. Er bekommt keine Ausnahmen. (automatisch ab P1, sonst Review)
- **Nicht übernommen** werden die Teile, die der Fahrplan (Abschnitte 1, 2 und 6) als fehlerhaft oder unpassend belegt, u. a.: die Rechteprüfung über Keycloak-Gruppen, Schreibzugriffe nach Keycloak, die Personensicht, Ernährung im Personenprofil, Mailvorlagen ohne Kopie je Veranstaltung und ohne Escaping, die harte Dublettensperre, die Kontensuche über den Benutzernamen und die Anmeldung ohne Prüfung des Teilnahmekreises. (Review)
- **Fremde Lizenzen:** Teile, die im alten Repo unter einer eigenen Lizenz stehen (z. B. `backend/notifications/` mit BSD-Lizenz), kommen nur mit ihrem Lizenzhinweis mit. Die Erlaubnis vom 20.10.2026 deckt sie nicht ab. (Review)
