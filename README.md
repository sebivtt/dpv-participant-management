# DPV Anmeldetool

Anmelde- und Veranstaltungstool für den DPV e.V.: Veranstaltungen planen, Anmeldungen einzeln und gesammelt annehmen, Teilnehmendenlisten führen. Login über den Keycloak des DPV. Ehrenamtlich entwickelt, gepflegt und betrieben.

**Stand:** Laufende Phase P1 „Gerüst“, seit dem 21.10.2026 (Zieldatum 28.02.2027, `docs/fahrplan.md`). Das Grundgerüst mit automatischen Prüfungen steht (#4); Fachfunktionen gibt es noch nicht. Parallel laufen die Restpunkte von P0 „Klären und festlegen“ bis zum Prüfpunkt E0 am 29.11.2026 (`docs/entscheidungen.md`, 21.10.2026).

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
   Danach: `Starting WSGI development server at http://127.0.0.1:8000/`, darunter eine englische Warnung, dass dies nur ein Server für die Entwicklung ist; das ist so gewollt. Im Browser http://127.0.0.1:8000/ öffnen: Es erscheint die Login-Seite mit „Mit DPV-Konto anmelden“. Anmelden mit einem der erfundenen Konten aus der Tabelle unten; danach steht dort „Hallo Erika!“. Die Musterseite mit allen Bausteinen der Gestaltung liegt unter http://127.0.0.1:8000/muster/. Beenden mit `ctrl` + `C` im Terminal.

   Erfundene Konten der Keycloak-Testumgebung (`dev/keycloak/dpv-realm.json`):

   | Benutzername | Passwort | Wofür |
   | --- | --- | --- |
   | `erika.testfrau` | `testpasswort-erika` | normales Konto mit Name und Mail |
   | `max.testmann` | `testpasswort-max` | zweites Konto, z. B. zum Wechseln am selben Gerät |
   | `ohne.name` | `testpasswort-ohne-name` | ohne Vor- und Nachnamen |
   | `ohne.nachname` | `testpasswort-ohne-nachname` | nur mit Vornamen |
   | `ohne.mail` | `testpasswort-ohne-mail` | ohne Mail; der Login wird abgelehnt |

   Über „Noch kein Konto? Registrieren“ lassen sich weitere Konten anlegen. Die Verwaltung von Keycloak liegt unter http://localhost:8080/admin/ (Benutzername `admin`, Passwort `nur-lokal-nicht-geheim`).

**Prüfungen laufen lassen** (zuerst Schritt 3, 6 und 7; einige Tests melden sich wirklich bei der Keycloak-Testumgebung an)

10. Nur einmal und nach einer neuen Fassung von Playwright: die drei Browser für den Rauchtest installieren (Chromium, Firefox und WebKit, die Technik hinter Safari). Sie liegen getrennt von deinen eigenen Browsern und brauchen zusammen rund 500 MB.
    ```bash
    uv run playwright install chromium firefox webkit
    ```
    Danach: je Browser eine Zeile `... downloaded to ...`; ist ein Browser schon da, erscheint für ihn nichts.
11. Alle automatischen Prüfungen starten, dieselben wie auf GitHub. Vorher das Tool beenden, falls es aus Schritt 9 noch läuft, und eine laufende Testumgebung im Container anhalten (Schritt T5): Der Rauchtest und die Prüfung der Testumgebung brauchen dieselben Adressen (Ports 8000 und 8081). Die Prüfung baut die Testumgebung selbst und räumt sie danach wieder ab; deine eigene Testumgebung und ihre Daten berührt sie nicht.
    ```bash
    ./pruefen.sh
    ```
    Danach: Für jede Prüfung eine Zeile `--> grün: ...`, ganz unten `Alle Prüfungen grün.` Ist etwas rot, steht unten `Nicht bestanden:` mit der Liste. Auf einem Mac mit macOS 27 steht beim Rauchtest zusätzlich `SKIPPED ... Firefox startet unter macOS 27 nicht`: Firefox von Playwright startet dort nicht; auf GitHub läuft Firefox mit.

**Aufhören**

12. Datenbank und Keycloak anhalten. Die Daten der Datenbank bleiben erhalten. Keycloak beginnt beim nächsten Start wieder mit den Konten aus der Tabelle; selbst registrierte Konten sind dann weg.
    ```bash
    docker compose -f dev/docker-compose.yml down
    ```
    Danach: `Container dpv-dev-postgres-1 Removed` und `Container dpv-dev-keycloak-1 Removed`.

## Testumgebung im Container (Mac)

So läuft das Tool auf deinem Mac genauso wie später in der Testumgebung auf dem Server des DPV (#58): als **Container**, also als abgeschlossenes Paket aus dem Tool und allem, was es braucht, mit einem Webserver für den Betrieb und einer eigenen Datenbank. Auf jeder Seite steht oben ein gelbes Band „Testumgebung“. Mails gehen nicht raus, nur ein Hinweis darauf steht im Log. Diese Anleitung funktioniert ohne KI; je Schritt genau ein Befehl. Voraussetzungen: Schritte 1 bis 3 und die App „Docker“ läuft (Schritt 6). Das Tool aus Schritt 9 vorher beenden, es braucht dieselbe Adresse.

**Einmalig einrichten**

T1. Die Umgebungsdatei der Testumgebung aus der Vorlage anlegen. Sie enthält nur erfundene Werte und kommt nie ins Repo.
   ```bash
   cp testumgebung/.env.example testumgebung/.env
   ```
   Danach: keine Ausgabe.

**Starten und Aktualisieren** (zuerst Schritt 3)

T2. Die Testumgebung bauen und starten. Derselbe Befehl bringt sie nach einer Änderung auf den neuesten Stand; vorher die Änderungen mit `git pull` holen.
   ```bash
   docker compose -f testumgebung/docker-compose.yml --profile lokal up -d --build --wait
   ```
   Danach: am Ende `Container dpv-test-datenbank-1 Healthy`, `Container dpv-test-tool-1 Healthy` und `Container dpv-test-keycloak-1 Healthy`. Beim ersten Mal lädt Docker vorher einiges herunter und baut das Tool; das dauert einige Minuten. Die Datenbank bringt sich beim Start selbst auf den neuesten Stand. Steht dort `failed to connect to the docker API`, läuft Docker nicht: zurück zu Schritt 6. Steht dort `port is already allocated`, läuft auf dem Mac schon etwas auf Port 8000 oder 8081, etwa das Tool aus Schritt 9.
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

## Technik (geplant)

Django mit serverseitig erzeugten Seiten und htmx, PostgreSQL, Login per OIDC über den Keycloak des DPV. Begründung im Fahrplan, Abschnitte 1 und 3.

## Vorgänger

Das Tool ist ein Neustart. Das frühere Repo [sebivtt/scout-participant-management](https://github.com/sebivtt/scout-participant-management) bleibt Nachschlagewerk. Übernommen sind Regeln und Werkzeuge, die seit dem 14.10.2026 dort entstanden sind. Einzelne Teile des alten Programmcodes dürfen mit Erlaubnis übernommen werden, wo sie zum neuen Datenmodell passen (`CONTRIBUTING.md`, Abschnitt 10).

## Lizenz

[EUPL-1.2](LICENSE)

Das Logo ist Eigentum des DPV und nicht Teil der EUPL-Lizenz. Gemeint ist die Lilie in `core/templates/core/lilie.svg` (Hinweis daneben in `LOGO-HINWEIS.md`). Fremde Dateien mit eigener Lizenz liegen mit ihrem Lizenztext im Repo: Bootstrap (MIT) in `core/static/core/bootstrap/`, axe-core (MPL-2.0) für die Prüfung auf Barrierefreiheit in `tests/vendor/axe-core/`.
