# Aufbau des Codes

Wie der Code des Tools aufgebaut ist und wo man was baut (#282). Regeln für jede Änderung stehen in `CONTRIBUTING.md`, für die Gestaltung in `docs/gestaltung.md`, Begründungen in `docs/entscheidungen.md`; diese Seite wiederholt sie nicht. Ob der Code der Richtung unten folgt, prüft `tests/test_aufbau.py`; er liest die Tabelle „Schichten“ aus dieser Datei.

## Die Apps

Django teilt das Tool in Apps, also Ordner mit je einem Fachbereich; `access` und `config` sind Ordner ohne eigene Anmeldung als App bei Django, stehen hier aber mit.

| App | Aufgabe |
| --- | --- |
| `access/` | Rechteprüfung: wer welche Personen, Leitungen und Einheiten sehen und bearbeiten darf (`access/rights.py`), die Kennzeichnung jeder Seite (`access/addresses.py`) und die zufälligen Kennungen in Adressen (`access/keys.py`). |
| `accounts/` | Konten und Login über Keycloak, Abmelden, Dauer der Sitzung, Fahrtenname. |
| `core/` | Grundbausteine ohne eigenen Fachbereich (Urheber einer Änderung, Fehlerprotokoll, Mail, Band der Testumgebung), die gemeinsame Gestaltung (Vorlagen, Bausteinkatalog, Navigation) und alle Seiten außer Login und Abmelden: Startseite, „Mein Profil“, Organisation mit Verband, Leitungen und Personen, auch verwalteten (`core/views.py`). |
| `units/` | Einheiten (Verband, Bund, Ring, Stamm, Gruppe) mit ihrem Protokoll, die Aufbereitung der Seite „Organisation“ (`units/organisation.py`) und die Befehle `federation` und `association`. |
| `roles/` | Rollen (Leitungen, Mitglieder, Teams, Admin) mit ihrem Protokoll und die Befehle `admin` und `federation_lead`. |
| `persons/` | Verwaltete Personen: Profile ohne Konto, die eine Leitung für ihre Organisation anlegt (#117, PER-02). |
| `config/` | Einstellungen (`config/settings.py`) und die Liste aller Adressen (`config/urls.py`). |

Die Apps hängen gegenseitig voneinander ab, weil Grundbausteine in Apps liegen, die auch obere Teile enthalten (etwa `access/keys.py` neben `access/rights.py`). Die Richtung legen deshalb nicht die Apps fest, sondern die Schichten.

## Schichten

Jede Datei des Tools gehört zu genau einer Schicht. Sie bindet nur Dateien aus ihrer eigenen oder einer niedrigeren Schicht ein (`import`), auch innerhalb von Funktionen, nie aus einer höheren. Ein Modell darf also nie die Rechteprüfung oder eine Seite einbinden; eine Seite darf alles darunter nutzen. Ein Ordner mit `/` am Ende steht für alle Dateien darin.

| Nr. | Schicht | Aufgabe | Dateien |
| --- | --- | --- | --- |
| 1 | Grundbausteine | ohne Fachlogik: Texte, Kennungen, Urheber, Protokolle, Mail, Sitzung, Abgleich mit Keycloak | `access/keys.py`, `core/actors.py`, `roles/expressions.py`, `accounts/texts.py`, `roles/texts.py`, `units/texts.py`, `persons/texts.py`, `core/texts.py`, `accounts/keycloak_abgleich.py`, `accounts/session.py`, `accounts/checks.py`, `core/errors.py`, `core/mail.py`, `core/gunicorn_log.py`, `core/testumgebung.py` |
| 2 | Modelle | was in der Datenbank steht, mit den Regeln beim Speichern | `accounts/models.py`, `units/models.py`, `roles/models.py`, `persons/models.py` |
| 3 | Rechteprüfung | wer was darf; Kennzeichnung der Seiten | `access/rights.py`, `access/addresses.py` |
| 4 | Aufbereitung | ordnet Daten für Seiten und Befehle, Formulare, Navigation, Bausteine für Vorlagen | `units/organisation.py`, `units/management/common.py`, `accounts/forms.py`, `core/forms.py`, `core/navigation.py`, `core/templatetags/layout.py` |
| 5 | Seiten, Befehle und Adressen | was von außen aufgerufen wird: Seiten, Befehle auf dem Server, Login über allauth, Start von Django und Webserver | `core/views.py`, `accounts/views.py`, `accounts/adapter.py`, `accounts/signals.py`, `accounts/apps.py`, `core/apps.py`, `roles/apps.py`, `units/apps.py`, `persons/apps.py`, `core/management/commands/`, `roles/management/commands/`, `units/management/commands/`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `manage.py`, `docker/gunicorn.conf.py` |

**Nicht Teil der Schichten:** `tests/`, `rauchtests/`, `containertests/`, `.github/`, `.claude/` und jeder Ordner `migrations`.

Eine Datei `__init__.py` gehört zu keiner Schicht; sie bindet nichts aus dem Tool ein, auch das prüft der Test. Nicht erkennen kann er Verweise ohne `import`, etwa Namen als Text in `config/settings.py`; solche Verweise stehen nur in der Schicht „Seiten, Befehle und Adressen“.

Eine neue Datei bekommt im selben Pull Request ihre Zeile in dieser Tabelle; sonst wird der Test rot. Braucht eine Datei etwas aus einer höheren Schicht, gehört entweder das Gebrauchte nach unten oder die Datei nach oben; das klärt der Pull Request, statt die Tabelle still anzupassen.

## Weg einer Anfrage

Jede Anfrage läuft durch die Bausteine in `MIDDLEWARE` (`config/settings.py`). Für eine Seite des Tools zählen diese Schritte, in dieser Reihenfolge:

1. **Login-Pflicht:** Jede Adresse verlangt einen Login. Ausnahmen sind nur die Login-Seiten in `accounts/views.py`, markiert mit `@login_not_required`; der Rundumtest `tests/test_rundumtest.py` kennt jede Ausnahme. Wessen Login zu lange her ist, gilt vorher schon als abgemeldet (`accounts/session.py`).
2. **Rechte:** Jede Anfrage bekommt ihre eigenen, frisch berechneten Rechte als `request.rights` (`access/rights.py`). Daten anderer Personen holt eine Seite nur darüber (`CONTRIBUTING.md`, Abschnitt 4).
3. **Seite:** `config/urls.py` ordnet die Adresse einer Seite zu. Jede Seite trägt eine Kennzeichnung aus `access/addresses.py`: welche Zeilen der Rechtematrix sie prüft oder warum sie keine Personendaten enthält. Fehlt sie, wird der Rundumtest rot.
4. **Antwort:** Die Seite bereitet ihre Daten mit der Schicht „Aufbereitung“ auf und gibt sie an eine Vorlage. Die Fehlerseiten sind Vorlagen in `core/templates/`; das Fehlerprotokoll und die Seite bei einem Fehler im Tool kommen aus `core/errors.py`.

## Wo was liegt

- **Texte**, die Nutzende sehen, stehen übersetzbar in der Datei `texts.py` ihrer App, etwa `units/texts.py`; Texte, die nur eine Vorlage braucht, stehen übersetzbar in der Vorlage.
- **Vorlagen** liegen in `core/templates/` (gemeinsame Rahmen, Fehlerseiten, alle Seiten von `core`) und `accounts/templates/accounts/` (Login, Abmelden).
- **Bausteine** der Gestaltung sind die Vorlagen mit `_` am Anfang in `core/templates/core/`, dazu die Bausteine in `core/templatetags/layout.py`. Der Bausteinkatalog (`core/templates/core/bausteine.html`, Adresse `/bausteine/`) zeigt jeden; welche es gibt und wie eine Seite sie einbindet, steht in `docs/gestaltung.md`.
- **Gestaltung und Skript** liegen in `core/static/core/` (`app.css`, `app.js`).
- **Navigation:** Ein neuer Punkt der Seitenleiste kommt nach `core/navigation.py`.
- **Datenbank:** Modelle in `models.py` der App, Änderungen daran als Migration im Ordner `migrations` der App.
- **Tests:** `tests/` für alles ohne Browser, `rauchtests/` für Rauchtests im Browser, `containertests/` für die Testumgebung im Container. Wie sie laufen, steht im `README.md`.
