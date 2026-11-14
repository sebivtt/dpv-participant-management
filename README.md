# DPV Anmeldetool

Anmelde- und Veranstaltungstool für den DPV e.V.: Veranstaltungen planen, Anmeldungen einzeln und gesammelt annehmen, Teilnehmendenlisten führen. Login über den Keycloak des DPV. Ehrenamtlich entwickelt, gepflegt und betrieben.

**Stand:** Laufende Phase P2 „Durchstich“ (`docs/fahrplan.md`). Was in dieser Phase fertig ist und was als Nächstes kommt, steht im Phasen-Issue [#106](https://github.com/sebivtt/dpv-participant-management/issues/106). Welche Rechte schon gebaut sind, zeigt die Spalte „Stand“ in `docs/rechtematrix.md`.

## Wo was steht

| Datei | Inhalt |
| --- | --- |
| [`docs/anforderungen.md`](docs/anforderungen.md) | Anforderungsdokument: was das Tool können muss (Muss, Soll, Kann) |
| [`docs/fahrplan.md`](docs/fahrplan.md) | Fahrplan: Phasen, Termine, Entscheidungspunkte, Risiken |
| [`docs/entscheidungen.md`](docs/entscheidungen.md) | Entscheidungen mit Datum und Begründung |
| [`docs/pruefung-2026-10-20.md`](docs/pruefung-2026-10-20.md) | Prüfung der Rückmeldungen von ChatGPT und Gemini zum Fahrplan |
| [`docs/review-leitfaden.md`](docs/review-leitfaden.md) | Leitfaden für das externe KI-Review am Ende jeder Phase |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Regeln für jede Änderung, egal ob von Menschen oder KI |
| [`CLAUDE.md`](CLAUDE.md) | zusätzliche Hinweise für KI-Assistenten |
| [`docs/rechtematrix.md`](docs/rechtematrix.md) | wer was darf, mit dem Stand je Zeile |
| [`docs/gestaltung.md`](docs/gestaltung.md) | Leitlinie für die Gestaltung jeder Seite |
| [`docs/zielbilder/`](docs/zielbilder/) | Sebastians Entwürfe für einzelne Seiten |
| [`docs/aufbau.md`](docs/aufbau.md) | Aufbau des Codes: Apps, Schichten und ihre Richtung, wo man was baut |
| [`docs/leistungstest.md`](docs/leistungstest.md) | Ergebnisse des Leistungstests am Ende jeder Phase |

Anforderungen und Fahrplan sind hier im Repo maßgeblich (Entscheidung vom 20.10.2026). Änderungen daran laufen wie alles andere über Pull Requests.

## Projekt starten (Mac)

Diese Anleitung funktioniert ohne KI. Je Schritt genau ein Befehl im Programm „Terminal“, dazu, was danach zu sehen sein sollte. Voraussetzungen: [Homebrew](https://brew.sh) und die App „Docker“ (Docker Desktop) sind installiert.

**Einmalig einrichten**

1. Das Werkzeug `uv` installieren. Es holt später selbst die passende Python-Fassung und alle Pakete.
   ```bash
   brew install uv
   ```
   Danach: Am Ende steht eine Zeile mit `uv` und einer Fassungsnummer, ohne `Error`.
2. Das Repo holen. Wer es schon unter `~/Entwicklung/dpv-participant-management` hat, überspringt diesen Schritt; liegt es woanders, zuerst den ganzen Ordner dorthin verschieben. Der Ordner `Entwicklung` liegt bewusst nicht in „Dokumente“ oder „Schreibtisch“: Diese beiden gleicht iCloud oft ab, und iCloud kann dann Kopien wie `pyproject 2.toml` anlegen, die git durcheinanderbringen.
   ```bash
   git clone https://github.com/sebivtt/dpv-participant-management.git ~/Entwicklung/dpv-participant-management
   ```
   Danach: `Cloning into ...` und keine Fehlermeldung. Fehlt der Ordner `Entwicklung`, legt git ihn selbst an.
3. In den Ordner des Projekts wechseln. Das ist auch bei jedem späteren Start der erste Schritt.
   ```bash
   cd ~/Entwicklung/dpv-participant-management
   ```
   Danach: keine Ausgabe.
4. Die Umgebungsdatei aus der Vorlage anlegen. Sie enthält nur erfundene Werte für den eigenen Rechner und kommt nie ins Repo.
   ```bash
   cp .env.example .env
   ```
   Danach: keine Ausgabe. Wer schon eine `.env` hat und nach einer Änderung an `.env.example` eine Meldung wie `Die Umgebungsvariable KEYCLOAK_REALM_URL fehlt` sieht, wiederholt diesen Schritt; die Datei enthält nur erfundene Werte.
5. Python und Pakete installieren.
   ```bash
   uv sync
   ```
   Danach: Beim ersten Mal `Downloaded cpython-3.13...`, am Ende `Installed ... packages`.

**Bei jedem Start** (zuerst Schritt 3)

6. Die App „Docker“ öffnen und warten, bis unten links „Engine running“ steht.
7. Die Datenbank und Keycloak starten. Keycloak ist hier eine eigene Testumgebung mit erfundenen Konten, nicht der Keycloak des DPV.
   ```bash
   docker compose -f dev/docker-compose.yml up -d --wait
   ```
   Danach: `Container dpv-dev-postgres-1 Healthy` und `Container dpv-dev-keycloak-1 Healthy`. Beim ersten Mal lädt Docker vorher Keycloak herunter, und der Start dauert bis zu zwei Minuten. Steht dort `failed to connect to the docker API`, läuft Docker nicht: zurück zu Schritt 6.
8. Die Datenbank auf den neuesten Stand bringen.
   ```bash
   uv run --env-file .env python manage.py migrate
   ```
   Danach: mehrere Zeilen `Applying ... OK` oder `No migrations to apply.` Steht dort `Connection refused`, läuft die Datenbank nicht: zurück zu Schritt 6.
9. Das Tool starten.
   ```bash
   uv run --env-file .env python manage.py runserver
   ```
   Danach: `Starting WSGI development server at http://127.0.0.1:8000/`, darunter eine englische Warnung, dass dies nur ein Server für die Entwicklung ist; das ist so gewollt. Im Browser http://127.0.0.1:8000/ öffnen: Es erscheint die Login-Seite mit „Mit DPV-Konto anmelden“. Anmelden mit einem der erfundenen Konten aus der Tabelle unten; danach steht dort „Hallo Erika!“. Der Bausteinkatalog mit allen entschiedenen Bausteinen der Gestaltung liegt unter http://127.0.0.1:8000/bausteine/. Beenden mit `ctrl` + `C` im Terminal.

   Erfundene Konten der Keycloak-Testumgebung (`dev/keycloak/dpv-realm.json`):

   | Benutzername | Passwort | Wofür |
   | --- | --- | --- |
   | `erika.testfrau` | `testpasswort-erika` | normales Konto mit Name und Mail |
   | `max.testmann` | `testpasswort-max` | zweites Konto, z. B. zum Wechseln am selben Gerät |
   | `ohne.name` | `testpasswort-ohne-name` | ohne Vor- und Nachnamen |
   | `ohne.nachname` | `testpasswort-ohne-nachname` | nur mit Vornamen |
   | `ohne.mail` | `testpasswort-ohne-mail` | ohne Mail; der Login wird abgelehnt |
   | `verbandsleitung` | `testpasswort-vera` | Testdaten (#103) |
   | `veranstaltungsteam` | `testpasswort-tom` | Testdaten (#103) |
   | `mitglied.walhall` | `testpasswort-wilma` | Testdaten (#103) |
   | `gruppenleitung.falken` | `testpasswort-fiete` | Testdaten (#103) |
   | `mitglied.falken` | `testpasswort-finn` | Testdaten (#103) |
   | `gruppenleitung.woelfe` | `testpasswort-wim` | Testdaten (#103) |
   | `gruppenleitung.kraniche` | `testpasswort-kira` | Testdaten (#103) |
   | `bundesleitung.nordstern` | `testpasswort-nils` | Testdaten (#103) |
   | `ringleitung.kueste` | `testpasswort-kai` | Testdaten (#103) |
   | `stammesleitung.leuchtturm` | `testpasswort-lars` | Testdaten (#103) |
   | `gruppenleitung.moewen` | `testpasswort-mia` | Testdaten (#103) |
   | `admin` | `testpasswort-adam` | Testdaten (#103) |

   Die Konten ab `verbandsleitung` heißen nach ihrer Rolle in den Testdaten; mehr dazu unter „Testdaten anlegen“.

   Über „Noch kein Konto? Registrieren“ lassen sich weitere Konten anlegen. Die Verwaltung von Keycloak liegt unter http://localhost:8080/admin/ (Benutzername `admin`, Passwort `nur-lokal-nicht-geheim`).

**Prüfungen laufen lassen** (zuerst Schritt 3, 6 und 7; einige Tests melden sich wirklich bei der Keycloak-Testumgebung an)

10. Nur einmal und nach einer neuen Fassung von Playwright: die drei Browser für den Rauchtest installieren (Chromium, Firefox und WebKit, die Technik hinter Safari). Sie liegen getrennt von deinen eigenen Browsern und brauchen zusammen rund 500 MB.
    ```bash
    uv run playwright install chromium firefox webkit
    ```
    Danach: je Browser eine Zeile `... downloaded to ...`; ist ein Browser schon da, erscheint für ihn nichts.
11. Alle automatischen Prüfungen starten, dieselben wie auf GitHub (dort in sechs Teilen gleichzeitig, `docs/entscheidungen.md`, 13.11.2026, #307). Das Tool aus Schritt 9 und deine eigene Testumgebung im Container dürfen dabei weiterlaufen: Die Prüfungen nutzen eigene Ports (`tests/check_ports.py`), nie 8000 und 8081. Die Prüfung baut eine eigene Testumgebung und räumt sie danach wieder ab; deine eigene Testumgebung und ihre Daten berührt sie nicht. Zwei Prüfläufe aus verschiedenen Arbeitskopien (etwa deine und die einer Session) dürfen gleichzeitig laufen: Jede Arbeitskopie hat ihre eigene Test-Datenbank. Nur Rauchtest und Container-Prüfung laufen nacheinander; ist dort gerade ein anderer Lauf, steht `Warte auf eine andere Prüfung (...) …`, und es geht von selbst weiter, sobald er fertig ist (höchstens 30 Minuten, dann bricht der Lauf mit einer Meldung ab, was zu tun ist). Zwei Läufe in derselben Arbeitskopie gehen weiter nicht gleichzeitig: Sie teilen sich deren Test-Datenbank.
    ```bash
    ./pruefen.sh
    ```
    Danach: Für jede Prüfung eine Zeile `--> grün: ... (Dauer)`, ganz unten `Alle Prüfungen grün.`, wenn kein Test übersprungen wurde. Wurden Tests übersprungen, steht stattdessen `Alle gelaufenen Prüfungen grün, N Tests übersprungen (Gründe oben unter SKIPPED).`; „grün“ heißt dann nicht „alles gelaufen“, und die Gründe stehen oben bei der jeweiligen Prüfung hinter `SKIPPED`. Ist etwas rot, steht unten `ROT. Nicht bestanden:` mit der Liste und kein grüner Satz. Auf einem Mac mit macOS 27 steht beim Rauchtest zusätzlich `SKIPPED ... Firefox startet unter macOS 27 nicht`: Firefox von Playwright startet dort nicht; auf GitHub läuft Firefox mit.

    Schneller Lauf (der Regelfall bei der Arbeit, `CLAUDE.md`, Ablauf je Aufgabe Nr. 4): dieselben vier Prüfungen ohne Tests (Paketliste, ruff, Django-Systemprüfung, Migrationen), dazu die Testdateien, die du hinter `schnell` nennst, und immer die Tests zum Bausteinkatalog aus `tests/` (Kennzeichen `bausteinkatalog`, `docs/entscheidungen.md`, 13.11.2026, #304). Dateien aus `tests/` laufen in einem Lauf, Dateien aus `rauchtests/` in einem eigenen, wie im vollen Lauf; nennst du eine Datei aus `rauchtests/`, laufen dort auch die Katalog-Rauchtests mit. Jeder Test läuft nur einmal. Container-Prüfung und pip-audit laufen nie. Beispiel:
    ```bash
    ./pruefen.sh schnell tests/test_arbeitsregeln.py
    ```
    Danach: dieselben Zeilen `--> grün: ... (Dauer)` für die gelaufenen Prüfungen, ganz unten `Schneller Lauf grün. Immer mitgelaufen: die Katalogtests aus tests/. Nicht ausgewählt: übrige Tests, alle Rauchtests, Testumgebung im Container, pip-audit.` Übersprungene Tests stehen davor: `Schneller Lauf grün, N Tests übersprungen (Gründe oben unter SKIPPED). Immer mitgelaufen: ...` Ohne Dateien (`./pruefen.sh schnell`) laufen die vier Prüfungen ohne Tests und die Katalogtests aus `tests/`. Eine Datei, die es nicht gibt oder die nicht in `tests/` oder `rauchtests/` liegt, und jede Option hinter `schnell` (etwa `-x`) bricht sofort mit einer Meldung ab (`pruefen.sh: ...`), ohne dass eine Prüfung läuft. Der schnelle Lauf ersetzt den vollen nicht: Den macht die Prüfung auf GitHub.

**Übrige Test-Datenbanken entfernen** (nur bei Bedarf, etwa nachdem alte Arbeitskopien gelöscht wurden)

Jede Arbeitskopie hat ihre eigene Test-Datenbank, Name `test_dpv_` und zwölf Zeichen. Nach einem normalen Lauf ist sie wieder gelöscht; nach einem abgebrochenen bleibt sie liegen, je Arbeitskopie höchstens eine. Eine Datenbank `test_dpv` ohne Zeichen dahinter stammt aus der Zeit vor #184 und kann genauso weg. Die Datenbank `dpv` deines Tools ist davon nicht betroffen. Voraussetzung: Die Datenbank läuft (Schritt 7), und gerade läuft kein `./pruefen.sh`.

1. Übrige Test-Datenbanken anzeigen.
   ```bash
   docker compose -f dev/docker-compose.yml exec postgres psql -U dpv -d dpv -c '\l test_dpv*'
   ```
   Danach: eine Tabelle; in der Spalte `Name` je übrige Test-Datenbank eine Zeile, etwa `test_dpv_0a1b2c3d4e5f`. Steht dort `(0 rows)`, ist nichts zu tun.
2. Eine davon entfernen; den Namen aus Schritt 1 statt `test_dpv_0a1b2c3d4e5f` einsetzen. Für jede weitere wiederholen. Das schadet nichts: Der nächste Prüflauf legt seine Test-Datenbank von selbst neu an.
   ```bash
   docker compose -f dev/docker-compose.yml exec postgres dropdb -U dpv test_dpv_0a1b2c3d4e5f
   ```
   Danach: keine Ausgabe. Schritt 1 zeigt die Datenbank nicht mehr.

**Lokale Datenbank neu anlegen** (nur bei Bedarf, etwa wenn es ein erfundenes Konto mehrfach gibt, mit einer Zahl im Benutzernamen wie `erika3`)

Bis #199 bekamen die erfundenen Konten bei jedem Start von Keycloak eine neue Kennung, und das Tool legte beim nächsten Login jedes Mal ein neues Konto an. Seitdem haben sie feste Kennungen. Ein Keycloak, der schon lief, kennt sie aber erst, nachdem er einmal mit Schritt 12 angehalten und wieder gestartet wurde; die alten Doppelkonten bleiben, bis die Datenbank einmal neu angelegt ist. Beides erledigen die beiden Schritte hier. Das löscht alle Daten der normalen Entwicklung, also Konten, Rollen, Verband und Bünde (danach bei Bedarf wieder anlegen wie unter „Testdaten anlegen“ oder „Verband und Bünde anlegen“), dazu übrige Test-Datenbanken. Die Testumgebung im Container ist davon nicht betroffen; für sie gibt es Schritt T6. Voraussetzung: Docker läuft (Schritt 6), und gerade läuft kein `./pruefen.sh`.

1. Datenbank und Keycloak anhalten und die Datenbank löschen.
   ```bash
   docker compose -f dev/docker-compose.yml down --volumes
   ```
   Danach: `Container dpv-dev-postgres-1 Removed`, `Container dpv-dev-keycloak-1 Removed`, `Network dpv-dev_default Removed` und `Volume dpv-dev_pgdata Removed`.
2. Weiter mit Schritt 7 und 8: Sie legen eine leere Datenbank an und bringen sie auf den neuesten Stand. Beim nächsten Login legt das Tool je erfundenem Konto genau ein Konto an, mit dem Benutzernamen wie beim Login und ohne Zahl.

**Aufhören**

12. Datenbank und Keycloak anhalten. Die Daten der Datenbank bleiben erhalten. Keycloak beginnt beim nächsten Start wieder mit den Konten aus der Tabelle; sie behalten ihre feste Kennung, man landet also wieder im selben Konto (#199). Selbst registrierte Konten sind dann weg.
    ```bash
    docker compose -f dev/docker-compose.yml down
    ```
    Danach: `Container dpv-dev-postgres-1 Removed` und `Container dpv-dev-keycloak-1 Removed`.

## Pull Request lokal ausprobieren

Setzt eine eingerichtete Umgebung voraus (Schritte 1 bis 5 unter „Projekt starten (Mac)“). Das brauchst du nur, wenn du eine Änderung selbst bedienen willst; die HTML-Datei der Vorschau (`CLAUDE.md`, „Vorschau“) öffnest du ohne all das einfach im Browser.

1. In den Ordner des Projekts wechseln.
   ```bash
   cd ~/Entwicklung/dpv-participant-management
   ```
   Danach: keine Ausgabe.
2. Den neuesten Stand von GitHub holen.
   ```bash
   git fetch origin
   ```
   Danach: keine Ausgabe oder Zeilen mit `From https://github.com/...` und `new branch`.
3. Den Stand der Änderung ansehen; statt `<zweig>` den Namen des Zweigs einsetzen, vor dem Pull Request statt `origin/<zweig>` die Kennung, die die Sitzung nennt.
   ```bash
   git switch --detach origin/<zweig>
   ```
   Danach: `HEAD is now at ...` und ein Hinweis auf den „detached HEAD“; der ist hier gewollt. `--detach` holt nur den Stand, ohne den Zweig zu belegen. Ein einfaches `git switch <zweig>` scheitert mit `is already used by worktree`, solange die Sitzung in ihrer Arbeitskopie daran arbeitet.
4. Die Pakete auf den Stand der Änderung bringen.
   ```bash
   uv sync
   ```
   Danach: `Installed ... packages` oder `Audited ... packages`.
5. Docker öffnen (Schritt 6 oben) und die Testumgebung starten (Schritt 7 oben).
   ```bash
   docker compose -f dev/docker-compose.yml up -d --wait
   ```
   Danach: `Container dpv-dev-postgres-1 Healthy` und `Container dpv-dev-keycloak-1 Healthy`.
6. Prüfen, ob der Stand eine Migration mitbringt, also eine Änderung an der Datenbank.
   ```bash
   git diff --name-only origin/main...HEAD -- '*/migrations/*'
   ```
   Danach: Steht dort nichts, bringt der Stand keine Migration mit. Steht dort etwas, nennt die Sitzung vorher den Befehl zum Zurückstellen und sagt, ob er alles wiederherstellt.
7. Die Datenbank auf den Stand der Änderung bringen.
   ```bash
   uv run --env-file .env python manage.py migrate
   ```
   Danach: `Applying ... OK` oder `No migrations to apply.`
8. Das Tool starten (Schritt 9 oben) und anmelden. Welche Rollen und Einheiten du zum Ausprobieren brauchst, nennt die Sitzung; die erfundene Grundausstattung legt der Befehl unter „Testdaten anlegen“ an.
   ```bash
   uv run --env-file .env python manage.py runserver
   ```
   Danach: `Starting WSGI development server at http://127.0.0.1:8000/`; im Browser http://127.0.0.1:8000/ öffnen.
9. Das Tool beenden mit `ctrl` + `C` im Terminal.
   Danach: Die Eingabezeile ist wieder frei.
10. Nur wenn Schritt 6 etwas zeigte und der Stand noch nicht in `main` ist: den Befehl zum Zurückstellen ausführen, den die Sitzung genannt hat, solange der Stand noch ausgecheckt ist, denn auf `main` fehlen die Dateien dazu.
    Danach: so, wie die Sitzung es beschrieben hat.
11. Zurück auf den Hauptzweig wechseln.
    ```bash
    git switch main
    ```
    Danach: `Switched to branch 'main'`.

Spätere Verweise auf einen Schritt mit Zahl in dieser Datei meinen die Liste unter „Projekt starten (Mac)“, nicht diese hier.

## Testumgebung im Container (Mac)

So läuft das Tool auf deinem Mac genauso wie später in der Testumgebung auf dem Server des DPV (#58): als **Container**, also als abgeschlossenes Paket aus dem Tool und allem, was es braucht, mit einem Webserver für den Betrieb und einer eigenen Datenbank. Auf jeder Seite steht oben ein gelbes Band „Testumgebung“. Mails gehen nicht raus, nur ein Hinweis darauf steht im Log. Diese Anleitung funktioniert ohne KI; je Schritt genau ein Befehl. Voraussetzungen: Schritte 1 bis 3 und die App „Docker“ läuft (Schritt 6). Das Tool aus Schritt 9 vorher beenden, es braucht dieselbe Adresse.

**Einmalig einrichten**

T1. Die Umgebungsdatei der Testumgebung aus der Vorlage anlegen. Sie enthält nur erfundene Werte und kommt nie ins Repo.
   ```bash
   cp testumgebung/.env.example testumgebung/.env
   ```
   Danach: keine Ausgabe.

**Starten und Aktualisieren** (zuerst Schritt 3 unter „Projekt starten (Mac)“)

T2. Die Testumgebung bauen und starten. Derselbe Befehl bringt sie nach einer Änderung auf den neuesten Stand; vorher die Änderungen mit `git pull` holen.
   ```bash
   docker compose -f testumgebung/docker-compose.yml --profile lokal up -d --build --wait
   ```
   Danach: am Ende `Container dpv-test-datenbank-1 Healthy`, `Container dpv-test-tool-1 Healthy` und `Container dpv-test-keycloak-1 Healthy`. Beim ersten Mal lädt Docker vorher einiges herunter und baut das Tool; das dauert einige Minuten. Die Datenbank bringt sich beim Start selbst auf den neuesten Stand. Steht dort `failed to connect to the docker API`, läuft Docker nicht: zurück zu Schritt 6. Steht dort `port is already allocated`, läuft auf dem Mac schon etwas auf Port 8000 oder 8081, etwa das Tool aus Schritt 9. Steht dort `is unhealthy`, ist das Tool nicht gestartet: Schritt T4 zeigt, warum, etwa `Die Umgebungsvariable DJANGO_SECRET_KEY fehlt`.
T3. Im Browser http://localhost:8000/ öffnen. Es erscheint die Login-Seite mit dem gelben Band „Testumgebung: Hier gibt es nur erfundene Daten. Bitte gib keine echten Angaben ein.“ Anmelden mit einem erfundenen Konto aus der Tabelle oben, z. B. `erika.testfrau`; danach steht dort „Hallo Erika!“, ebenfalls mit Band. Keycloak läuft hier unter http://localhost:8081/.
T4. Nur bei Bedarf: das Log des Tools ansehen. Auch wenn hier nur erfundene Daten stehen: Auszüge aus Logs gehören nicht in KI-Werkzeuge.
   ```bash
   docker compose -f testumgebung/docker-compose.yml logs tool
   ```
   Danach: die Zeilen des Tools, u. a. `Applying ... OK` oder `No migrations to apply.` und `Booting worker`.

**Anhalten**

T5. Die Testumgebung anhalten. Ihre Daten bleiben erhalten, auch über das Aktualisieren hinweg. Selbst registrierte Konten in Keycloak sind beim nächsten Start weg, wie bei Schritt 12.
   ```bash
   docker compose -f testumgebung/docker-compose.yml --profile lokal down
   ```
   Danach: je Container eine Zeile `Removed`.
T6. Nur bei Bedarf: neu anfangen. Das löscht alle Daten der Testumgebung, nicht die der normalen Entwicklung.
   ```bash
   docker compose -f testumgebung/docker-compose.yml --profile lokal down --volumes
   ```
   Danach: je Container eine Zeile `Removed`, dazu `Volume dpv-test_daten Removed`.

## Testdaten anlegen

Ein Befehl legt erfundene Testdaten an, mit denen sich die Szenarien Walhall, Zugvögel und Boreas aus #103 nachspielen lassen: den Verband „DPV“, den Pfadfinderbund Boreas ohne Ringe mit den Stämmen Walhall (Sippe Falken, Meute Wölfe) und Zugvögel (Sippe Kraniche), den Bund Nordstern mit dem Ring „Küste“, dem Stamm Leuchtturm und der Sippe Möwen, je Organisation eine Leitung, zwei Mitglieder mit Konto, die Verbandsleitung, das DPV-Veranstaltungsteam, ein Konto ohne Organisation und Rolle, einen Admin und 18 verwaltete Personen. Wer welche Rolle bekommt, steht in der Besetzung im [Kommentar „Szenarien (12.11.2026)“](https://github.com/sebivtt/dpv-participant-management/issues/103#issuecomment-6826598949) in #103.

**Achtung:** Jeder Lauf löscht vorher alles außer den Konten, auch Verband, Bünde, Rollen, verwaltete Personen und alle Protokolle, und legt dieselben Daten neu an. Wer vor dem Lauf Admin ist, ist es danach wieder. Der Befehl läuft nur, wenn die Einstellungen ausdrücklich „lokal“ (`LOCAL_ENVIRONMENT=1`) oder „Testumgebung“ sagen; sonst bricht er ab, ohne etwas zu löschen.

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“):

D1. Nur einmal, wenn deine `.env` älter ist als #103: die Umgebungsdatei neu aus der Vorlage anlegen (wie Schritt 4; sie enthält nur erfundene Werte).
   ```bash
   cp .env.example .env
   ```
   Danach: keine Ausgabe. In der Datei steht jetzt die Zeile `LOCAL_ENVIRONMENT=1`.

D2. Nur einmal, damit Keycloak die neuen Konten aus der Tabelle unter Schritt 9 kennt: Datenbank und Keycloak anhalten. Die Daten der Datenbank bleiben erhalten.
   ```bash
   docker compose -f dev/docker-compose.yml down
   ```
   Danach: `Container dpv-dev-postgres-1 Removed` und `Container dpv-dev-keycloak-1 Removed`.

D3. Nur einmal: beide wieder starten. Keycloak liest dabei die Konten neu ein.
   ```bash
   docker compose -f dev/docker-compose.yml up -d --wait
   ```
   Danach: `Container dpv-dev-postgres-1 Healthy` und `Container dpv-dev-keycloak-1 Healthy`.

D4. Die Testdaten anlegen.
   ```bash
   uv run --env-file .env python manage.py testdata
   ```
   Danach: `Testdaten angelegt: 11 Organisationen, 25 Rollen und 18 verwaltete Personen. Alle Daten außer den Konten wurden vorher gelöscht, auch die Protokolle.` Ab dem zweiten Lauf folgt `Wieder Admin wie vor dem Lauf: admin` und alle, die vorher sonst noch Admin waren. Steht dort `CommandError: Der Befehl läuft nur lokal oder in der Testumgebung. …`, fehlt die Zeile aus D1. Danach anmelden, etwa als `erika.testfrau` (Stammesleitung Walhall) oder `gruppenleitung.falken`; jedes Konto landet beim ersten Login im Konto aus dem Befehl.

In der Testumgebung im Container (zuerst Schritt T2) und auf dem Server legt der Befehl keine Konten an. Rollen bekommen dort nur die vier Konten des Test-Realms, mit derselben Rolle wie lokal, und nur, wenn sie sich schon einmal angemeldet haben. Verwaltete Personen entstehen nur, wo eine dieser Leitungen sie anlegen darf; die Sippe Möwen bleibt dort leer (Entscheidung von Sebastian, [Kommentar in #103](https://github.com/sebivtt/dpv-participant-management/issues/103#issuecomment-6861587463)).

D5. Die Testdaten in der Testumgebung im Container anlegen.
   ```bash
   docker compose -f testumgebung/docker-compose.yml exec tool python manage.py testdata
   ```
   Danach: `Testdaten angelegt: 11 Organisationen, …` mit weniger Rollen und verwalteten Personen als lokal, darunter `Ohne verwaltete Personen, weil dort niemand mit Konto sie anlegen darf: Sippe Möwen.` (und weitere Organisationen, solange dort keine Leitung angemeldet war). Fehlt ein Konto, steht dort zum Beispiel `Ohne Rolle, weil noch nie im Tool angemeldet: max.testmann. Diese Konten müssen sich zuerst einmal anmelden; danach den Befehl erneut ausführen.`

## Leistungstest (am Ende einer Phase)

Am Ende jeder Phase prüft der Leistungstest, ob jede Seite mit Personen auch bei 5.000 erfundenen Personen in unter 2 Sekunden vom Server kommt (#104). Er legt dafür mit dem Zusatz `--mass-data` am Befehl `testdata` zusätzlich 40 Probestämme mit je 5 Gruppen und 5.000 erfundene Personen im Pfadfinderbund Boreas an. Die normalen Prüfungen machen das nicht. Warum so, steht in `docs/entscheidungen.md` (13.11.2026, #104).

Am Phasenende misst er relativ zur vorigen Phase (#145): In einem Lauf auf GitHub misst er abwechselnd den Stand vom Ende der vorigen Phase und den neuen Stand, mit denselben erzeugten Daten. Den alten Stand findet er über die feste Markierung `phasenende-p<n>` im Repo (etwa `phasenende-p2`). Rot ist der Lauf, wenn eine Seite eine der Grenzen aus `docs/entscheidungen.md` (14.11.2026, #145, Nr. 3) reißt oder ein Durchgang, alt oder neu, rot war; die Zeile der Seite sagt, was davon. Er meldet auch Seiten mit Personen, die noch keine Messung haben. Wann wer was tut, steht im Skill `phase-steuern`, Abschnitt 5; die Ergebnisse stehen in `docs/leistungstest.md`.

L1. Auf GitHub starten: Im Repo oben auf „Actions“, links „Leistungstest“, rechts „Run workflow“. Unter „Use workflow from“ den Zweig wählen, der gemessen werden soll. Bei „Phase“ die Phase eintragen, die endet (etwa `P3`), bei „Markierung der vorigen Phase“ deren Markierung (etwa `phasenende-p2`); nur am Ende von P2 bleibt sie leer. Dann noch einmal „Run workflow“.
   Danach: Nach einigen Minuten ist der Lauf grün oder rot. Auf der Seite des Laufs steht der fertige Abschnitt für `docs/leistungstest.md`: je Seite Zeit, Wert der vorigen Phase, Abweichung und Ergebnis, darunter die Seiten mit Personen ohne Messung. Passen Phase und Markierung nicht zusammen, bricht er gleich mit `Falsche Eingabe: …` ab.

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“; die Daten entstehen dabei nur in einer eigenen Test-Datenbank):

L2. Den Leistungstest starten.
   ```bash
   uv run --env-file .env pytest tests/leistungstest.py -rsfE
   ```
   Danach: eine Tabelle „Leistungstest (#104), Grenze 2 s je Seite“ mit der Zeit je Seite, darunter `Seiten mit Personen ohne Messung (#145): …` und am Ende `10 passed`. Einen Vergleich mit der vorigen Phase gibt es nur auf GitHub (L1).

Die Massendaten zum Ausprobieren im eigenen Tool legt `uv run --env-file .env python manage.py testdata --mass-data` an. Dann steht nach der Zeile aus D4 noch `Dazu Massendaten für den Leistungstest im Pfadfinderbund Boreas: 240 Probe-Organisationen, 2000 erfundene Konten ohne Login und 3000 verwaltete Personen.` Anmelden kann sich mit diesen Konten niemand. Ein Lauf ohne Zusatz entfernt die Massendaten wieder bis auf die Konten, die dann ohne Rolle bleiben.

Nur einmal, am Ende von P2: Messung von Hand in der Testumgebung auf dem Server (#145), sobald sie läuft (#59). Wie die Befehle dort genau heißen, legt #59 fest; bis dahin gelten sie nur für die Testumgebung im Container auf dem Mac (D5) und werden mit #59 nachgeprüft.

L3. In der Testumgebung im Browser einmal als `ohne.nachname` anmelden, damit Boreas dort eine Bundesleitung hat, mit dem Konto aus dem Test-Realm dort (Abschnitt „Test-Realm im Keycloak des DPV“).
   Danach: „Hallo“ mit dem gelben Band der Testumgebung.
L4. Die Testdaten mit den Massendaten anlegen (wie D5, mit Zusatz).
   ```bash
   docker compose -f testumgebung/docker-compose.yml exec tool python manage.py testdata --mass-data
   ```
   Danach: wie in D5, dazu die Zeile `Dazu Massendaten für den Leistungstest im Pfadfinderbund Boreas: …`.
L5. In Safari zuerst unter „Safari“ → „Einstellungen“ → „Erweitert“ die Funktionen für Webentwickler einschalten. Dann als `ohne.nachname` anmelden, im Menü „Entwickler“ „Webinformationen einblenden“ wählen und dort „Netzwerk“. Nacheinander „Organisation“, die Seite „Probestamm 01“ und auf der Seite „Pfadfinderbund Boreas“ den Dialog „Person mit Konto aufnehmen“ mit einer Suche nach einer Mail öffnen.
   Danach: Je Seite steht in der Liste in der Zeile der Seite selbst unter „Zeit“ die Zeit bis zur Antwort des Servers, und unten die Zeit, bis der Browser die Seite fertig geladen hat. Beide Zahlen je Seite notieren und der KI für `docs/leistungstest.md`, Abschnitt P2, geben. Heißen die Spalten in Safari anders, das der KI sagen.

## Verband und Bünde anlegen (Admins)

In P2 legen Admins den Verband und die Bünde per Befehl an, nicht über eine Seite im Tool (#88; eine Seite ist für später vorgemerkt, #107). Dieselben Befehle benennen um und schalten „hat Ringe“ ein; ausschalten lässt es sich bis #204 nicht. Ringe, Stämme und Gruppen legen die Leitungen im Tool an und benennen sie um, die Bundesleitung auch ihren Bund (#95). Löschen gibt es nicht (Entscheidung W5 in `docs/entscheidungen.md`). Die Befehle prüfen dieselben Regeln wie das Tool: genau ein Verband, keine leeren oder doppelten Namen, höchstens 100 Zeichen; „Boreas“ und „ boreas “ gelten als gleich. Jedes Anlegen, Umbenennen und Umschalten schreibt einen Eintrag ins Protokoll der Strukturänderungen, mit „Befehl auf dem Server“ als Urheber (#131); ein Befehl ohne Änderung schreibt keinen.

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“):

V1. Den Verband anlegen. Ihn gibt es nur einmal.
   ```bash
   uv run --env-file .env python manage.py federation create "DPV"
   ```
   Danach: `Den Verband „DPV“ gibt es jetzt.` Gibt es schon einen, steht dort `CommandError: Es gibt schon einen Verband: „DPV“.`
V2. Einen Bund anlegen. Hat der Bund Ringe, am Ende ` --rings` anfügen.
   ```bash
   uv run --env-file .env python manage.py association create "Pfadfinderbund Boreas"
   ```
   Danach: `Den Bund „Pfadfinderbund Boreas“ gibt es jetzt.` Gibt es ihn schon, steht dort `CommandError: Den Bund „Pfadfinderbund Boreas“ gibt es schon.`
V3. Nachsehen, was angelegt ist.
   ```bash
   uv run --env-file .env python manage.py association list
   ```
   Danach: `Verband: DPV`, darunter `Bünde:` und je Bund eine Zeile, z. B. `  Pfadfinderbund Boreas (ohne Ringe)`.
V4. Nur bei Bedarf: einen Bund umbenennen, erst der alte, dann der neue Name.
   ```bash
   uv run --env-file .env python manage.py association rename "Pfadfinderbund Boreas" "Bund Boreas"
   ```
   Danach: `Der Bund „Pfadfinderbund Boreas“ heißt jetzt „Bund Boreas“.` Den Verband benennt `federation rename "Neuer Name"` um.
V5. Nur bei Bedarf: „hat Ringe“ einschalten (`on`). Das kann seit #95 auch die Bundesleitung selbst im Tool (Stift oben rechts auf der Seite des Bundes, Schalter „Hat Ringe“). Ausschalten geht nicht, weder hier noch im Tool, bis #204 es baut.
   ```bash
   uv run --env-file .env python manage.py association rings "Bund Boreas" on
   ```
   Danach: `Im Bund „Bund Boreas“ ist „hat Ringe“ jetzt eingeschaltet.`

In der Testumgebung im Container (zuerst Schritt T2) steht statt `uv run --env-file .env python manage.py` jeweils `docker compose -f testumgebung/docker-compose.yml exec tool python manage.py`, z. B.:
   ```bash
   docker compose -f testumgebung/docker-compose.yml exec tool python manage.py association list
   ```
   Danach: dieselbe Ausgabe wie in V3, mit den Daten der Testumgebung.

## Admins ernennen und entfernen

Admin wird man bis ADM-01 (P6) nur per Befehl auf dem Server, nie über das Tool, über Keycloak oder als erstes angemeldetes Konto (#89). Die Rolle Admin gibt keine Rechte einer Leitung; Personendaten sieht ein Admin nur im Support-Zugang, den er auf der Seite einer Organisation startet und der ins Protokoll der Admin-Zugriffe kommt (#92). Gebraucht wird der Benutzername aus Keycloak eines Kontos, das sich schon einmal im Tool angemeldet hat. Den letzten Admin zu entfernen geht, weil sich mit Zugang zum Server jederzeit ein neuer ernennen lässt. Beide Befehle schreiben einen Eintrag ins Protokoll der Rollenänderungen, mit „Befehl auf dem Server“ als Urheber (#91).

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“):

A1. Eine Person zum Admin ernennen, hier das erfundene Konto `erika.testfrau`.
   ```bash
   uv run --env-file .env python manage.py admin grant erika.testfrau
   ```
   Danach: `erika.testfrau ist jetzt Admin.` Hat sich das Konto noch nie angemeldet, steht dort `CommandError: Kein Konto mit diesem Benutzernamen. Die Person muss sich zuerst einmal im Tool anmelden.`
A2. Das Admin-Recht wieder entfernen.
   ```bash
   uv run --env-file .env python manage.py admin revoke erika.testfrau
   ```
   Danach: `erika.testfrau ist jetzt kein Admin mehr.` Ist die Person kein Admin, steht dort `CommandError: erika.testfrau ist kein Admin.`

In der Testumgebung im Container steht statt `uv run --env-file .env python manage.py` wieder `docker compose -f testumgebung/docker-compose.yml exec tool python manage.py`.

## Leere Organisation im Notfall löschen (Admins)

Im Tool lässt sich keine Organisation löschen (Entscheidung W5 in `docs/entscheidungen.md`; im Tool erst mit #108). Ist eine Organisation versehentlich angelegt und noch leer, löscht ein Admin sie per Befehl auf dem Server (#92). Der Befehl lehnt den Verband ab und jede Organisation, unter der noch Organisationen hängen oder in der es Rollen, Mitglieder oder verwaltete Personen gibt. Er schreibt einen Eintrag ins Protokoll der Admin-Zugriffe, mit „Befehl auf dem Server“ als Urheber. Gebraucht wird die Kennung der Organisation: Sie steht in der Adresse ihrer Seite, etwa `/organisation/KENNUNG/`; als Admin öffnet sich jede Seite einer Organisation, dort steht nur der Kopf.

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“):

N1. Die Organisation mit dieser Kennung löschen; `KENNUNG` durch die Kennung aus der Adresse ersetzen.
   ```bash
   uv run --env-file .env python manage.py emergency_delete KENNUNG
   ```
   Danach: `„Sippe Irrtum“ ist gelöscht. Der Eintrag steht im Protokoll der Admin-Zugriffe.` Ist sie nicht leer, steht dort `CommandError: „Walhall“ ist nicht leer: …`; gibt es die Kennung nicht, `CommandError: Keine Organisation mit dieser Kennung. …`

In der Testumgebung im Container steht statt `uv run --env-file .env python manage.py` wieder `docker compose -f testumgebung/docker-compose.yml exec tool python manage.py`.

## Verbandsleitung benennen und entfernen

Die erste Verbandsleitung benennt ein Admin per Befehl auf dem Server; weitere benennt die Verbandsleitung selbst im Tool (#94). Der Befehl geht jederzeit, auch wenn es schon Verbandsleitungen gibt. Er braucht den Verband (Schritt V1) und den Benutzernamen aus Keycloak eines Kontos, das sich schon einmal im Tool angemeldet hat. Die letzte Verbandsleitung zu entfernen geht, weil sich mit Zugang zum Server jederzeit eine neue benennen lässt. Beide Befehle schreiben einen Eintrag ins Protokoll der Rollenänderungen, mit „Befehl auf dem Server“ als Urheber (#91).

Lokal (zuerst Schritte 3, 6, 7 und 8 unter „Projekt starten (Mac)“):

L1. Eine Person als Verbandsleitung benennen, hier das erfundene Konto `erika.testfrau`.
   ```bash
   uv run --env-file .env python manage.py federation_lead grant erika.testfrau
   ```
   Danach: `erika.testfrau ist jetzt Verbandsleitung.` Ist sie es schon, steht dort `erika.testfrau ist schon Verbandsleitung.` Hat sich das Konto noch nie angemeldet, steht dort `CommandError: Kein Konto mit diesem Benutzernamen. Die Person muss sich zuerst einmal im Tool anmelden.` Gibt es noch keinen Verband, steht dort `CommandError: Es gibt noch keinen Verband. Lege ihn zuerst mit „federation create“ an.`
L2. Die Verbandsleitung wieder entfernen.
   ```bash
   uv run --env-file .env python manage.py federation_lead revoke erika.testfrau
   ```
   Danach: `erika.testfrau ist jetzt keine Verbandsleitung mehr.` Ist die Person keine Verbandsleitung, steht dort `CommandError: erika.testfrau ist keine Verbandsleitung.`

In der Testumgebung im Container steht statt `uv run --env-file .env python manage.py` wieder `docker compose -f testumgebung/docker-compose.yml exec tool python manage.py`.

## Test-Realm im Keycloak des DPV

Auf dem Server meldet sich die Testumgebung nicht bei der Keycloak-Testumgebung aus `dev/` an, sondern bei einem eigenen **Test-Realm** im Keycloak des DPV (#38). Ein Realm ist ein abgeschlossener Bereich in Keycloak mit eigenen Konten; der Test-Realm `dpv-test` ist vom Realm der Mitglieder getrennt. Er hat vier erfundene Konten, und niemand kann sich dort selbst registrieren oder ein Passwort per Mail zurücksetzen. Die Importdatei liegt in `testumgebung/keycloak/dpv-test-realm.json`. Sie enthält kein Passwort und kein Client-Secret, damit niemand, der das Repo sieht, in die Testumgebung kommt.

Diese Anleitung funktioniert ohne KI und ohne Terminal. Alles geschieht in der Verwaltung von Keycloak, die auf Englisch beschriftet ist; die Beschriftungen stehen hier so, wie sie in Keycloak 26.7.5 heißen. Passwörter und das Client-Secret gehören nie in Chats, Issues oder KI-Werkzeuge.

**Einmalig: Test-Realm anlegen** (der Admin des DPV oder Sebastian mit seinem Admin-Konto)

K1. Sebastian oder der Admin öffnet die Datei `dpv-test-realm.json` auf GitHub (Ordner `testumgebung/keycloak/`) und lädt sie mit „Download raw file“ herunter; sobald das Repo öffentlich ist (#310), ist dafür kein Konto bei GitHub nötig.
K2. In der Verwaltung von Keycloak links „Manage realms“ öffnen, dann „Create realm“.
K3. Unter „Resource file“ auf „Browse...“ klicken, die Datei aus K1 auswählen und „Create“ klicken.
   Danach: Unter „Manage realms“ steht `dpv-test`. Darin stehen unter „Users“ genau vier Konten: `erika.testfrau`, `max.testmann`, `ohne.name` und `ohne.nachname`.

**Einmalig, sobald die Testdomain feststeht** (#59)

K4. Im Realm `dpv-test` links „Clients“ öffnen, dann `dpv-anmeldetool`. Im Reiter „Settings“ steht bei „Valid redirect URIs“ und „Valid post logout redirect URIs“ der Platzhalter `https://testdomain-eintragen.invalid`. In beiden Feldern nur diesen Teil durch die Testdomain ersetzen, z. B. `https://anmeldetool-test.example.org`; der Rest (`/anmelden/keycloak/zurueck/` bzw. `/anmelden/`) bleibt. Dann unten „Save“.
K5. Im selben Client den Reiter „Credentials“ öffnen. Neben „Client Secret“ auf „Copy to clipboard“ klicken und den Wert direkt in die Umgebungsdatei der Testumgebung auf dem Server eintragen (`KEYCLOAK_CLIENT_SECRET`, Anleitung in #59), nirgendwo sonst. Dort gehören außerdem `KEYCLOAK_CLIENT_ID=dpv-anmeldetool` und `KEYCLOAK_REALM_URL` mit der Adresse des Keycloak des DPV und `/realms/dpv-test` am Ende hinein. Die Zeile `KEYCLOAK_REALM_URL_INTERN` aus der Vorlage wird dort gelöscht; sie gilt nur für die Keycloak-Testumgebung auf dem eigenen Rechner, und mit ihr scheitert der Login auf dem Server.

**Einmalig: Passwörter setzen** (Sebastian)

K6. Links „Users“ öffnen und ein Konto anklicken, z. B. `erika.testfrau`. Im Reiter „Credentials“ auf „Set password“ klicken.
K7. Ein langes, neues Passwort aus dem Passwortmanager in beide Felder eintragen. Den Schalter „Temporary“ auf „Off“ stellen; sonst verlangt Keycloak beim ersten Login ein neues Passwort. Dann „Save“; fragt Keycloak noch einmal nach, bestätigen.
K8. K6 und K7 für die übrigen drei Konten wiederholen, jedes mit eigenem Passwort. Die Passwörter stehen nur im Passwortmanager.

**Bei Bedarf: Zugang für eine weitere Person** (Sebastian)

K9. Links „Users“, dann „Add user“. Bei „Username“ einen erfundenen Namen eintragen, z. B. `pruefer.test`, bei „Email“ `pruefer.test@example.org`, bei „First name“ z. B. `Paula`. Nie den echten Namen oder die echte Mail der Person. „Email verified“ auf „On“ stellen und „Create“ klicken. Dann wie in K6 und K7 ein Passwort setzen und es der Person persönlich weitergeben, nicht per Mail oder Chat.
K10. Wird der Zugang nicht mehr gebraucht: das Konto unter „Users“ öffnen, oben rechts „Action“ und „Delete“ wählen und bestätigen.

Wer sich nach zehn falschen Passwörtern nicht mehr anmelden kann, wartet einige Minuten, höchstens 15; Keycloak sperrt das Konto nur vorübergehend. Name und Mail eines Kontos ändert nur der Admin, nicht die Person selbst, damit dort keine echten Angaben landen.

## Technik

Django mit serverseitig erzeugten Seiten und einem eigenen kleinen Skript, PostgreSQL, Login per OIDC über den Keycloak des DPV. Begründung im Fahrplan, Abschnitte 1 und 3. Wie der Code aufgebaut ist und wo man was baut, steht in `docs/aufbau.md`; `tests/test_aufbau.py` prüft, dass er dieser Beschreibung folgt.

## Vorgänger

Das Tool ist ein Neustart. Das frühere Repo [sebivtt/scout-participant-management](https://github.com/sebivtt/scout-participant-management) bleibt Nachschlagewerk. Übernommen sind Regeln und Werkzeuge, die seit dem 14.10.2026 dort entstanden sind. Einzelne Teile des alten Programmcodes dürfen mit Erlaubnis übernommen werden, wo sie zum neuen Datenmodell passen (`CONTRIBUTING.md`, Abschnitt 10).

## Lizenz

[EUPL-1.2](LICENSE)

Das Logo ist Eigentum des DPV und nicht Teil der EUPL-Lizenz. Gemeint ist die Lilie in `core/templates/core/lilie.svg` (Hinweis daneben in `LOGO-HINWEIS.md`). Fremde Dateien mit eigener Lizenz liegen mit ihrem Lizenztext im Repo: Bootstrap (MIT) in `core/static/core/bootstrap/`, axe-core (MPL-2.0) für die Prüfung auf Barrierefreiheit in `tests/vendor/axe-core/`.
