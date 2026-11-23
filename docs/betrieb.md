# Betrieb auf einem Server

Der eine Ort für alle Absicherungen des Serverbetriebs (#324). In P6 wird diese Datei der Anfang des Betriebshandbuchs.

Jede Zeile nennt nur, wo die Absicherung umgesetzt ist oder welches Issue sie bringt, ihren Stand und den Zeitpunkt. Die Regel selbst steht dort, nicht hier. Was jede Einstellung der Umgebungsdatei bedeutet, steht in `testumgebung/.env.example`; was nur für den eigenen Rechner gilt, in `.env.example`.

Zeitpunkte:

- **vor der Testumgebung:** bevor die Testumgebung auf dem Server offen erreichbar ist (#59).
- **vor dem echten Betrieb:** bevor echte Daten ins Tool kommen (P6, Tor E3). In der Testumgebung gibt es nur erfundene Daten, die sich neu erzeugen lassen.
- **nicht umsetzen:** mit Sebastians Grund.

## Prüfliste

| Absicherung | Wo umgesetzt oder welches Issue | Stand | Zeitpunkt |
|---|---|---|---|
| Server-Einstellungen an einem Ort: diese Liste und je Einstellung genau eine Beschreibung | diese Datei, `testumgebung/.env.example`, `.env.example` (#324) | erledigt | vor der Testumgebung |
| Fehleranzeige für Entwickler aus, auch wenn die Umgebungsdatei sie einschaltet; auf einem Server startet das Tool damit gar nicht | `config/settings.py` (`DEBUG`), #58; `core/server_checks.py`, #325 | erledigt | vor der Testumgebung |
| Band „Testumgebung“ auf jeder Seite und Bitte an Suchmaschinen | `testumgebung/docker-compose.yml` (`TEST_ENVIRONMENT`), `core/testumgebung.py`, #58; für den Server: Hinweis unten | erledigt | vor der Testumgebung |
| Mails nur als Hinweis ins Log, nie an einen Mailserver | `config/settings.py` (`MAILERS`), #58; Versand nur an Testadressen: #60 | erledigt | vor der Testumgebung |
| Testumgebung im Container: eigene Datenbank und eigenes Netz; Datenbank ohne Port nach außen, keine gemeinsamen Ablagen | `testumgebung/docker-compose.yml`, #58; auf dem Server eigene Datenbank im gemeinsamen PostgreSQL und gemeinsames Netz (`docs/entscheidungen.md`, 23.11.2026, #59), Hinweis unten | erledigt | vor der Testumgebung |
| Zugangsdaten nur in der Umgebungsdatei auf dem Server, nie im Abbild oder im Repo; auf dem Server aus dem Key Vault in eine eigene Datei des Tools, nicht in die gemeinsame Datei des DPV | `testumgebung/.env.example` (nur erfundene Werte), `.dockerignore`, #58; Server: Repo des DPV-Servers, #59 | erledigt | vor der Testumgebung |
| Tool im Container nicht als Verwalter | `Dockerfile`, #58 | erledigt | vor der Testumgebung |
| HTTPS: Sitzungs- und Formular-Cookies nur verschlüsselt | `config/settings.py` (`DJANGO_BEHIND_HTTPS_PROXY`), #58 | erledigt | vor der Testumgebung |
| HTTPS: Weiterleitung von `http` auf `https` und HSTS | `config/settings.py` (`DJANGO_BEHIND_HTTPS_PROXY`), #324 | erledigt | vor der Testumgebung |
| Adresssuche: nur der Server fragt OpenStreetMap, nur der Suchtext, höchstens eine Anfrage pro Sekunde, Suchtext in keinem Log; der Server braucht dafür Zugang nach außen zu `nominatim.openstreetmap.org` (HTTPS) | `core/address_search.py`, `config/settings.py` (`ADDRESS_SEARCH_…`), #163; Kontaktadresse in `ADRESSSUCHE_KENNUNG`: unten | erledigt | vor der Testumgebung |
| Sicherheitsrichtlinie für Skripte | `config/settings.py` (`SECURE_CSP`), #278 | erledigt | vor der Testumgebung |
| Startprüfung: Tool startet nicht mit unsicheren Einstellungen | `core/server_checks.py` (läuft mit `migrate` in `docker/start.sh`), #325 | erledigt | vor der Testumgebung |
| Abgelaufene Sitzungen löschen, beim Start und danach alle 24 Stunden | `testumgebung/docker-compose.yml` (Dienst `aufraeumen`), `docker/aufraeumen.sh`, #324 | erledigt | vor der Testumgebung |
| Log des Datenbankservers ohne Befehle und ohne Werte aus Fehlern | `testumgebung/docker-compose.yml` (Dienst `datenbank`, `command`), #324; für den Server nur für die Datenbank des Tools: Hinweis unten (#59) | erledigt | vor der Testumgebung |
| Fehlerprotokoll des Tools ohne Personendaten | `core/errors.py`, `config/settings.py` (`LOGGING`), #6 | erledigt | vor der Testumgebung |
| Webserver ohne Zugriffsprotokoll mit echten Adressen | `docker/gunicorn.conf.py`, #58 | erledigt | vor der Testumgebung |
| Auf dem Server: Zugriffsprotokoll des Programms davor (Caddy) ohne Adressen mit Parametern | `Caddyfile` im Repo des DPV-Servers (`import access_log` für die Testdomain); eigenes Issue in Vorbereitung (Befund der unabhängigen Prüfung zu #59) | offen | vor dem echten Betrieb |
| Webserver-Log: auch Fehlerzeilen mit Ablauf ohne Meldungstext | #79 | offen | vor dem echten Betrieb |
| Grundabbilder mit fester Fassung und Prüfsumme | `Dockerfile`, `testumgebung/docker-compose.yml` (Dienst `datenbank`), #324; Aktualisieren: unten | erledigt | vor der Testumgebung |
| Schwachstellenprüfung der Pakete | `pruefen.sh` (`pip-audit`), `CONTRIBUTING.md`, Abschnitt 6 | erledigt | vor der Testumgebung |
| Schwachstellenprüfung für Bootstrap | keine eigene Prüfung; stattdessen der Hinweis unten | erledigt | nicht umsetzen; Grund von Sebastian (#324): Das Tool nutzt nur die Gestaltungsdatei von Bootstrap ohne Skript; bekannte Lücken betrafen bisher das Skript. |
| Selbstregistrierung im Test-Realm aus | Importdatei `testumgebung/keycloak/dpv-test-realm.json` (#62); eingespielt wird sie beim Einrichten (#38) | erledigt | vor der Testumgebung |
| Protokolle „nur anhängbar“ auch gegenüber dem Datenbankkonto | #334 | offen | vor dem echten Betrieb |
| Sicherung vor `migrate` beim Start | #335 | offen | vor dem echten Betrieb |
| Konten löschen | #202, #66 | offen | vor dem echten Betrieb |
| Aufbewahrung der Logs | #11 | offen | vor dem echten Betrieb |
| Aufbewahrung der Protokolle | #147 | offen | vor dem echten Betrieb |
| Protokolle bei Arbeiten direkt in der Datenbank (Betriebshandbuch) | #130 | offen | vor dem echten Betrieb |
| Backups: verschlüsselt, an einem zweiten Ort, Zurückspielen geübt | OP-4, NFA-06 (`docs/anforderungen.md`), P6 | offen | vor dem echten Betrieb |
| zweiter Faktor beim Login für Admins | P6 (`docs/fahrplan.md`, NFA-10) | offen | vor dem echten Betrieb |
| `SECURITY.md` | P6 (`docs/fahrplan.md`, NFA-10) | offen | vor dem echten Betrieb |
| Datenbank-Log und Aufräumen der Sitzungen auch im echten Betrieb, nicht nur in der Testumgebung | P6 (Betriebshandbuch); bisher nur in der Testumgebung, im Container und auf dem Server | offen | vor dem echten Betrieb |

## Beim Einrichten auf dem Server (#59)

- **Hinweis auf HTTPS:** Das Programm vor dem Tool, das die verschlüsselte Verbindung annimmt, muss bei jeder Anfrage die Kopfzeile `X-Forwarded-Proto: https` selbst setzen und einen vom Browser mitgeschickten Wert ersetzen, nicht nur anhängen. Fehlt sie, hält das Tool mit `DJANGO_BEHIND_HTTPS_PROXY=1` jede Anfrage für unverschlüsselt und leitet endlos weiter. Leitet das Programm davor selbst schon auf HTTPS weiter, schadet das nicht. Nach dem Einrichten prüft Sebastian den Login auf dem Server einmal von Hand (#59).
- **Adresssuche:** In der Umgebungsdatei `ADRESSSUCHE_KENNUNG` mit einer Kontaktadresse des Teams setzen (`testumgebung/.env.example`); das wünschen die Nutzungsregeln von OpenStreetMap. Erreicht der Server OpenStreetMap nicht, meldet das Tool „Die Adresssuche ist gerade nicht erreichbar.“, und die Adresse lässt sich von Hand eintragen (#163).
- **Sitzungen:** Der Dienst zum Aufräumen (`aufraeumen`, auf dem Server `anmeldetool-aufraeumen`) startet mit der Testumgebung von selbst. `README.md`, „Testumgebung auf dem Server“, S6, zeigt ihn mit `Up`, solange er läuft; sein Log bleibt leer, außer ein Lauf scheitert (dann neuer Versuch nach einer Minute).
- **Fest in der Compose-Datei, nicht in der Umgebungsdatei:** `TEST_ENVIRONMENT=1` für Band, Bitte an Suchmaschinen und ohne Fehleranzeige für Entwickler, wie in `testumgebung/docker-compose.yml`. Mails gehen ohnehin nur ins Log; einen Mailserver kennt das Tool nicht.
- **Link „Registrieren“:** `REGISTRATION_LINK_ENABLED` nicht auf 0 setzen; der Link bleibt sichtbar (Sebastian, 15.11.2026, #59).
- **Datenbank im gemeinsamen PostgreSQL:** Der Benutzer `anmeldetool` ist Eigentümer nur seiner Datenbank `anmeldetool`, ohne Verwalterrechte und ohne Recht, Datenbanken oder Benutzer anzulegen. PostgreSQL erlaubt jedem Benutzer von sich aus die Verbindung zu jeder Datenbank; damit `anmeldetool` die übrigen nicht erreicht, braucht jede andere Datenbank `REVOKE CONNECT ON DATABASE <Name> FROM PUBLIC;` (ihre Eigentümer und Verwalter verbinden sich weiter; vorher prüfen, ob sonst ein Benutzer sie braucht). Das gilt auch für jede später angelegte Datenbank.
- **Log der Datenbank:** Für die Datenbank des Tools schreibt PostgreSQL keine Befehle und keine Fehler einzelner Befehle ins Log, wie in der Testumgebung im Container (#324, Begründung dort). Eingestellt vom Admin, nur für diese Datenbank, als Verwalter in `psql`; die übrigen Dienste merken davon nichts. Wirksam wird es für jede neue Verbindung. Weil das Tool beim ersten Start sofort in die Datenbank schreibt, am besten gleich beim Anlegen der Datenbank (auf dem Server der Dienst `anmeldetool-db-init`), sonst danach mit einem Neustart des Tools:
  ```sql
  ALTER DATABASE anmeldetool SET log_min_messages = 'log';
  ALTER DATABASE anmeldetool SET log_min_error_statement = 'panic';
  ALTER DATABASE anmeldetool SET log_error_verbosity = 'terse';
  ALTER DATABASE anmeldetool SET log_statement = 'none';
  ALTER DATABASE anmeldetool SET log_min_duration_statement = -1;
  ```
  Die ersten vier stehen in derselben Fassung in `testumgebung/docker-compose.yml` (Dienst `datenbank`); die letzte verhindert, dass langsame Befehle mit ihren Werten ins Log kommen, falls der Server das sonst tut. `tests/test_testumgebung_server.py` hält beide Stellen gleich.

## Aktualisieren

- **Grundabbilder:** Fassung und Prüfsumme ändern sich nur per Pull Request, mit dem vollen Prüflauf auf GitHub. Nach dem Übernehmen baut GitHub das Abbild neu, sobald die Prüfungen für diesen Stand von `main` grün sind (`.github/workflows/abbild-veroeffentlichen.yml`) und legt es unter einer neuen Version in der GitHub Container Registry ab; der Server holt es von dort und baut nicht selbst (#302; `README.md`, „Testumgebung auf dem Server“). Die Datenbank steht in derselben Fassung auch in `.github/workflows/ci.yml`, `.github/workflows/leistungstest.yml` und `dev/docker-compose.yml`; alle Stellen ändern sich zusammen, sonst ist `tests/test_pruefung_auf_github.py` rot (#349).
- **Bootstrap:** Beim Aktualisieren von Bootstrap (`core/static/core/bootstrap/`) dessen Sicherheitshinweise nachsehen und im Pull Request nennen.
