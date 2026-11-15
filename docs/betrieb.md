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
| Band „Testumgebung“ auf jeder Seite und Bitte an Suchmaschinen | `testumgebung/docker-compose.yml` (`TEST_ENVIRONMENT`), `core/testumgebung.py`, #58 | erledigt | vor der Testumgebung |
| Mails nur als Hinweis ins Log, nie an einen Mailserver | `config/settings.py` (`MAILERS`), #58; Versand nur an Testadressen: #60 | erledigt | vor der Testumgebung |
| Testumgebung hat eine eigene Datenbank und ein eigenes Netz; Datenbank ohne Port nach außen, keine gemeinsamen Ablagen | `testumgebung/docker-compose.yml`, #58 | erledigt | vor der Testumgebung |
| Zugangsdaten nur in der Umgebungsdatei auf dem Server, nie im Abbild oder im Repo | `testumgebung/.env.example` (nur erfundene Werte), `.dockerignore`, #58 | erledigt | vor der Testumgebung |
| Tool im Container nicht als Verwalter | `Dockerfile`, #58 | erledigt | vor der Testumgebung |
| HTTPS: Sitzungs- und Formular-Cookies nur verschlüsselt | `config/settings.py` (`DJANGO_BEHIND_HTTPS_PROXY`), #58 | erledigt | vor der Testumgebung |
| HTTPS: Weiterleitung von `http` auf `https` und HSTS | `config/settings.py` (`DJANGO_BEHIND_HTTPS_PROXY`), #324 | erledigt | vor der Testumgebung |
| Sicherheitsrichtlinie für Skripte | `config/settings.py` (`SECURE_CSP`), #278 | erledigt | vor der Testumgebung |
| Startprüfung: Tool startet nicht mit unsicheren Einstellungen | `core/server_checks.py` (läuft mit `migrate` in `docker/start.sh`), #325 | erledigt | vor der Testumgebung |
| Abgelaufene Sitzungen löschen, beim Start und danach alle 24 Stunden | `testumgebung/docker-compose.yml` (Dienst `aufraeumen`), `docker/aufraeumen.sh`, #324 | erledigt | vor der Testumgebung |
| Log des Datenbankservers ohne Befehle und ohne Werte aus Fehlern | `testumgebung/docker-compose.yml` (Dienst `datenbank`, `command`), #324 | erledigt | vor der Testumgebung |
| Fehlerprotokoll des Tools ohne Personendaten | `core/errors.py`, `config/settings.py` (`LOGGING`), #6 | erledigt | vor der Testumgebung |
| Webserver ohne Zugriffsprotokoll mit echten Adressen | `docker/gunicorn.conf.py`, #58 | erledigt | vor der Testumgebung |
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
| Datenbank-Log und Aufräumen der Sitzungen auch im echten Betrieb, nicht nur in der Testumgebung | P6 (Betriebshandbuch); bisher nur `testumgebung/docker-compose.yml` | offen | vor dem echten Betrieb |

## Beim Einrichten auf dem Server (#59)

- **Hinweis auf HTTPS:** Das Programm vor dem Tool, das die verschlüsselte Verbindung annimmt, muss bei jeder Anfrage die Kopfzeile `X-Forwarded-Proto: https` selbst setzen und einen vom Browser mitgeschickten Wert ersetzen, nicht nur anhängen. Fehlt sie, hält das Tool mit `DJANGO_BEHIND_HTTPS_PROXY=1` jede Anfrage für unverschlüsselt und leitet endlos weiter. Leitet das Programm davor selbst schon auf HTTPS weiter, schadet das nicht. Nach dem Einrichten prüft Sebastian den Login auf dem Server einmal von Hand (#59).
- **Sitzungen:** Der Dienst `aufraeumen` startet mit der Testumgebung von selbst. `docker compose -f testumgebung/docker-compose.yml ps aufraeumen` zeigt ihn mit `Up`, solange er läuft; sein Log bleibt leer, außer ein Lauf scheitert (dann neuer Versuch nach einer Minute).

## Aktualisieren

- **Grundabbilder:** Fassung und Prüfsumme ändern sich nur per Pull Request, mit dem vollen Prüflauf auf GitHub. Danach baut der Server das Abbild beim Aktualisieren neu (#59).
- **Bootstrap:** Beim Aktualisieren von Bootstrap (`core/static/core/bootstrap/`) dessen Sicherheitshinweise nachsehen und im Pull Request nennen.
