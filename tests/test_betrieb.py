"""Tests zur Prüfliste „vor dem ersten Server“ (#324).

Die Kennungen (E1, V2, G3 …) verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #324. Diese
Tests prüfen die Prüfliste, die Vorlagen der Umgebungsdatei, die Einstellungen für HTTPS und die
Dateien, aus denen Docker die Testumgebung baut. Dass Sitzungen im laufenden Container wirklich
gelöscht werden und das Log des Datenbankservers keine Mail enthält, prüfen containertests/
(E5, G1, V1). Die Testdomain ist erfunden.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from django.test import Client

pytestmark = pytest.mark.django_db

BASE_DIR = Path(__file__).resolve().parent.parent
BETRIEB = BASE_DIR / "docs" / "betrieb.md"
README = BASE_DIR / "README.md"
SETTINGS = BASE_DIR / "config" / "settings.py"
ENV_SERVER = BASE_DIR / "testumgebung" / ".env.example"
ENV_LOCAL = BASE_DIR / ".env.example"
COMPOSE = BASE_DIR / "testumgebung" / "docker-compose.yml"
DOCKERFILE = BASE_DIR / "Dockerfile"

DOMAIN = "test.anmeldung.example.org"
ONE_YEAR = 365 * 24 * 60 * 60

# Pflichtangaben mit erfundenen Werten, damit sich die Einstellungen in einem eigenen Prozess laden lassen.
INVENTED = {
    "DJANGO_SECRET_KEY": "nur-fuer-diesen-test",
    "POSTGRES_DB": "beispiel",
    "POSTGRES_USER": "beispiel",
    "POSTGRES_PASSWORD": "beispiel",
}

# Alles, was der HTTPS-Schalter einstellt (Punkt 2).
HTTPS_SETTINGS = (
    "SECURE_PROXY_SSL_HEADER",
    "SECURE_SSL_REDIRECT",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
)


def _settings_from_start(env: dict[str, str]) -> dict:
    """Lädt die Einstellungen in einem eigenen Prozess mit genau dieser Umgebung.

    Einstellungen aus Umgebungsvariablen werden beim Start einmal gelesen; ein eigener Prozess
    zeigt, was der Start tatsächlich aus dem Schalter macht.
    """
    code = (
        "from django.conf import settings; "
        f"print(repr({{name: getattr(settings, name) for name in {HTTPS_SETTINGS!r}}}))"
    )
    result = subprocess.run(  # noqa: S603 -- fester Befehl mit dem eigenen Python, keine Eingaben von außen
        [sys.executable, "-c", code],
        cwd=BASE_DIR,
        env={"PATH": os.environ.get("PATH", ""), "DJANGO_SETTINGS_MODULE": "config.settings", **INVENTED, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return ast.literal_eval(result.stdout.strip())


@pytest.fixture
def mit_schalter(settings):
    """Das Tool mit genau den Einstellungen, die der Start aus DJANGO_BEHIND_HTTPS_PROXY=1 macht."""
    for name, value in _settings_from_start({"DJANGO_BEHIND_HTTPS_PROXY": "1"}).items():
        setattr(settings, name, value)
    settings.ALLOWED_HOSTS = [DOMAIN]
    return settings


@pytest.fixture
def ohne_schalter(settings):
    """Das Tool mit genau den Einstellungen, die der Start ohne HTTPS-Schalter macht."""
    for name, value in _settings_from_start({}).items():
        setattr(settings, name, value)
    settings.ALLOWED_HOSTS = [DOMAIN, "localhost"]
    return settings


# Wie das Programm vor dem Tool, das HTTPS annimmt und mit diesem Hinweis weiterreicht.
VIA_HTTPS = {"HTTP_X_FORWARDED_PROTO": "https"}


# ---------- E1: Prüfliste ----------


def _rows() -> list[list[str]]:
    """Die Zeilen der Tabellen in docs/betrieb.md, ohne Kopf und Trennlinie, je Zeile die Zellen."""
    rows = []
    for line in BETRIEB.read_text().splitlines():
        if not line.startswith("|") or set(line) <= {"|", "-", " ", ":"}:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[0] == "Absicherung":
            continue
        rows.append(cells)
    return rows


ZEITPUNKTE = ("vor der Testumgebung", "vor dem echten Betrieb", "nicht umsetzen")


def test_e1_jede_zeile_nennt_ort_stand_und_zeitpunkt():
    rows = _rows()

    assert len(rows) >= 20
    for absicherung, ort, stand, zeitpunkt in rows:
        assert absicherung and ort, (absicherung, ort)
        assert stand in ("erledigt", "offen"), (absicherung, stand)
        assert zeitpunkt.startswith(ZEITPUNKTE), (absicherung, zeitpunkt)


def test_e1_nicht_umsetzen_nur_mit_sebastians_grund():
    for absicherung, _ort, _stand, zeitpunkt in _rows():
        if zeitpunkt.startswith("nicht umsetzen"):
            assert "Sebastian" in zeitpunkt and "Grund" in zeitpunkt, absicherung


def test_e1_offen_vor_der_testumgebung_nur_was_59_ohnehin_blockiert():
    open_before_test = [
        (absicherung, ort)
        for absicherung, ort, stand, zeitpunkt in _rows()
        if stand == "offen" and zeitpunkt.startswith("vor der Testumgebung")
    ]

    for absicherung, ort in open_before_test:
        issues = set(re.findall(r"#\d+", ort))
        assert issues and issues <= {"#278", "#325"}, absicherung


def test_e1_alle_absicherungen_aus_dem_issue_stehen_in_der_liste():
    text = BETRIEB.read_text()

    # Die Tabelle in #324 und die Beispiele aus dem Akzeptanzkriterium „Vollständig“.
    for issue in ("#6", "#79", "#278", "#325", "#38", "#11", "#147", "#130", "#334", "#335", "#202", "#66"):
        assert re.search(rf"{issue}\b", text), issue
    for topic in (
        "Fehleranzeige für Entwickler",
        "Band",
        "Mails",
        "eigene Datenbank",
        "eigenes Netz",
        "Umgebungsdatei",
        "Selbstregistrierung",
        "Backups",
        "zweiter Faktor",
        "SECURITY.md",
        "HTTPS",
        "HSTS",
        "Sitzungen",
        "Log des Datenbankservers",
        "Grundabbilder",
        "Bootstrap",
        "migrate",
        "Konten löschen",
    ):
        assert topic in text, topic


def test_e1_readme_nennt_die_pruefliste():
    assert "docs/betrieb.md" in README.read_text()


# ---------- E2: ein Ort je Einstellung ----------


def _variables_in_settings() -> set[str]:
    code = SETTINGS.read_text()
    return set(re.findall(r'(?:os\.environ\.get|required_env)\(\s*"([A-Z_]+)"', code))


def _described(path: Path) -> dict[str, str]:
    """Jede Einstellung der Vorlage (auch auskommentiert) mit dem Kommentar direkt darüber.

    Mehrere Einstellungen direkt untereinander teilen sich denselben Kommentar; eine Leerzeile
    beendet ihn.
    """
    described: dict[str, str] = {}
    comment: list[str] = []
    for line in path.read_text().splitlines():
        setting = re.match(r"#?\s?([A-Z][A-Z0-9_]*)=", line)
        if setting:
            described[setting.group(1)] = " ".join(comment)
        elif line.startswith("#"):
            comment.append(line.lstrip("# "))
        else:
            comment = []
        if not line.strip():
            comment = []
    return described


def test_e2_jede_einstellung_steht_in_einer_vorlage():
    in_templates = set(_described(ENV_SERVER)) | set(_described(ENV_LOCAL))
    # Diese Einstellung trägt die Compose-Datei der Testumgebung fest ein, nicht die Umgebungsdatei.
    fixed_in_compose = {"TEST_ENVIRONMENT"}

    assert _variables_in_settings() - in_templates - fixed_in_compose == set()


def test_e2_gemeinsame_einstellungen_beschreibt_nur_die_vorlage_der_testumgebung():
    server = _described(ENV_SERVER)
    local = _described(ENV_LOCAL)

    shared = set(server) & set(local)
    assert {"DJANGO_SECRET_KEY", "POSTGRES_PASSWORD", "KEYCLOAK_REALM_URL"} <= shared
    for name in shared:
        assert server[name] and "testumgebung/.env.example" not in server[name], name
        # Für den eigenen Rechner nur der Wert und der Verweis, keine eigene Beschreibung.
        assert local[name] == "Beschreibung: testumgebung/.env.example", (name, local[name])


def test_e2_einstellungen_verweisen_auf_vorlagen_und_pruefliste():
    docstring = ast.get_docstring(ast.parse(SETTINGS.read_text()))

    assert "testumgebung/.env.example" in docstring
    assert "docs/betrieb.md" in docstring


# ---------- E3, E4, V2, G2: HTTPS ----------


def test_e3_mit_schalter_dauerhaft_auf_https_mit_pfad_und_parametern(mit_schalter):
    response = Client().get("/veranstaltungen/?seite=2&suche=wald", HTTP_HOST=DOMAIN)

    assert response.status_code == 301
    assert response["Location"] == f"https://{DOMAIN}/veranstaltungen/?seite=2&suche=wald"


def test_e3_auch_die_startseite_ohne_login(mit_schalter):
    response = Client().get("/", HTTP_HOST=DOMAIN)

    assert response.status_code == 301
    assert response["Location"] == f"https://{DOMAIN}/"


@pytest.mark.parametrize("path", ["/anmelden/", "/gibt-es-nicht/", "/static/core/app.css"])
def test_e4_mit_schalter_jede_antwort_ueber_https_bittet_ein_jahr_nur_um_https(mit_schalter, path):
    response = Client(**VIA_HTTPS).get(path, HTTP_HOST=DOMAIN)

    assert response.status_code in (200, 302, 404), response.status_code
    # Nur diese Adresse, ohne Unteradressen und ohne Eintrag in die Vorab-Liste der Browser.
    assert response["Strict-Transport-Security"] == f"max-age={ONE_YEAR}"


def test_e4_schalter_stellt_hsts_genau_so_ein():
    values = _settings_from_start({"DJANGO_BEHIND_HTTPS_PROXY": "1"})

    assert values["SECURE_SSL_REDIRECT"] is True
    assert values["SECURE_HSTS_SECONDS"] == ONE_YEAR
    assert values["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is False
    assert values["SECURE_HSTS_PRELOAD"] is False


def test_v2_ohne_schalter_weder_weiterleitung_noch_hsts(ohne_schalter):
    response = Client().get("/anmelden/", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response


def test_v2_ohne_schalter_hilft_auch_ein_behaupteter_https_hinweis_nicht(ohne_schalter):
    # Ohne Programm davor kann jede Anfrage „das war HTTPS“ behaupten; das Tool glaubt es nicht.
    response = Client(**VIA_HTTPS).get("/anmelden/", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert "Strict-Transport-Security" not in response


def test_v2_ohne_schalter_bleibt_alles_wie_bisher():
    values = _settings_from_start({})

    assert values == {
        "SECURE_PROXY_SSL_HEADER": None,
        "SECURE_SSL_REDIRECT": False,
        "SECURE_HSTS_SECONDS": 0,
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
        "SECURE_HSTS_PRELOAD": False,
        "SESSION_COOKIE_SECURE": False,
        "CSRF_COOKIE_SECURE": False,
    }


def test_g2_kommt_die_anfrage_schon_ueber_https_keine_weitere_weiterleitung(mit_schalter):
    response = Client(**VIA_HTTPS).get("/anmelden/", HTTP_HOST=DOMAIN)

    assert response.status_code == 200


def test_g3_pruefliste_nennt_den_hinweis_des_programms_davor():
    text = BETRIEB.read_text()

    assert "X-Forwarded-Proto" in text
    assert "endlos" in text
    # Befund G2 der unabhängigen Prüfung: Django wertet den Wert ganz links aus, also einen vom
    # Browser mitgeschickten; das Programm davor muss ihn ersetzen, nicht nur anhängen.
    assert "ersetzen" in text


# ---------- E5: Sitzungen aufräumen (Aufbau; im Container: containertests/) ----------


def _services() -> dict:
    return yaml.safe_load(COMPOSE.read_text())["services"]


def test_e5_eigener_dienst_raeumt_sitzungen_beim_start_und_mindestens_taeglich_auf():
    cleanup = _services()["aufraeumen"]
    script = (BASE_DIR / cleanup["command"][-1]).read_text()

    assert cleanup["image"] == _services()["tool"]["image"]
    assert cleanup["depends_on"]["tool"]["condition"] == "service_healthy"
    assert cleanup["restart"] == "unless-stopped"
    # Erst aufräumen, dann warten, in einer Schleife.
    loop = script[script.index("while true") :]
    assert loop.index("manage.py clearsessions") < loop.index("sleep")
    seconds = int(re.search(r"sleep (\d+)", loop).group(1))
    assert 0 < seconds <= 24 * 60 * 60


def test_e5_scheitert_ein_lauf_kommt_der_naechste_bald(tmp_path):
    # Befund M2 der unabhängigen Prüfung: Ist die Datenbank etwa nach einem Neustart des Servers
    # noch nicht bereit, darf der Dienst nicht 24 Stunden bis zum nächsten Versuch warten.
    # Ersatz für python (erster Lauf scheitert) und sleep (merkt sich die Pause, endet nach zwei).
    calls = tmp_path / "aufrufe"
    (tmp_path / "python").write_text(f'#!/bin/sh\necho lauf >> "{calls}"\n[ "$(grep -c lauf "{calls}")" -gt 1 ]\n')
    (tmp_path / "sleep").write_text(
        f'#!/bin/sh\necho "pause $1" >> "{calls}"\n[ "$(grep -c pause "{calls}")" -lt 2 ] || kill -TERM $PPID\n'
    )
    for stub in ("python", "sleep"):
        (tmp_path / stub).chmod(0o755)

    subprocess.run(  # noqa: S603 -- festes Skript aus dem Repo, Ersatzbefehle aus diesem Test
        ["/bin/sh", str(BASE_DIR / "docker" / "aufraeumen.sh")],
        cwd=BASE_DIR,
        env={"PATH": f"{tmp_path}:/usr/bin:/bin"},
        timeout=30,
        check=False,
    )

    pauses = [int(line.split()[1]) for line in calls.read_text().splitlines() if line.startswith("pause")]
    assert pauses[0] <= 5 * 60, pauses
    assert 0 < pauses[1] <= 24 * 60 * 60, pauses


def test_e5_aufraeumen_erreicht_nur_die_datenbank():
    cleanup = _services()["aufraeumen"]

    assert cleanup["networks"] == ["intern"]
    assert "ports" not in cleanup


# ---------- V1: Log des Datenbankservers (Aufbau; im Container: containertests/) ----------


def test_v1_datenbankserver_schreibt_keine_befehle_und_keine_fehlerdetails_ins_log():
    command = " ".join(_services()["datenbank"]["command"])

    # Fehler einzelner Befehle (Stufe ERROR) können Werte enthalten; ins Log kommen erst
    # Meldungen ab LOG, etwa Start, Prüfpunkte und abgewiesene Verbindungen.
    assert "log_min_messages=log" in command
    assert "log_min_error_statement=panic" in command
    assert "log_error_verbosity=terse" in command
    assert "log_statement=none" in command


# ---------- E6: Grundabbilder fest ----------

PINNED = re.compile(r"^[\w./-]+:\d+\.\d+[\w.-]*@sha256:[0-9a-f]{64}$")


def test_e6_grundabbilder_des_tools_mit_fester_fassung_und_pruefsumme():
    images = re.findall(r"^FROM\s+(\S+)", DOCKERFILE.read_text(), re.M)

    assert len(images) == 2
    for image in images:
        assert PINNED.match(image), image


def test_e6_datenbank_der_testumgebung_mit_fester_fassung_und_pruefsumme():
    image = _services()["datenbank"]["image"]

    assert PINNED.match(image), image
    assert image.startswith("postgres:18.")


def test_e6_pruefliste_nennt_das_aktualisieren_per_pull_request():
    text = BETRIEB.read_text()

    assert "Prüfsumme" in text
    assert "Pull Request" in text


# ---------- G4: Bootstrap ----------


def test_g4_pruefliste_nennt_den_hinweis_zu_bootstrap_und_sebastians_entscheidung():
    rows = [row for row in _rows() if "Bootstrap" in row[0]]

    assert len(rows) == 1
    absicherung, _ort, _stand, zeitpunkt = rows[0]
    assert zeitpunkt.startswith("nicht umsetzen")
    assert "Sicherheitshinweise" in BETRIEB.read_text()
