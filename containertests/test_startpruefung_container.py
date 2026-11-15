"""Startprüfung am echten Start des Containers (#325, Szenario G3).

Die Kennungen verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #325. Jeder Test startet
das Tool mit `docker/start.sh`, so wie der Container auf dem Server startet, nur mit geänderten
Einstellungen gegenüber der Umgebungsdatei der Prüfung. Alle Schreibweisen der Regeln prüft
tests/test_startpruefung.py ohne Container. Testdomain, Schlüssel und Passwörter sind erfunden.
"""

import secrets

import pytest

from containertests.conftest import compose
from tests.test_startpruefung import DOMAIN, PREFIX, SUFFIX

# Die Datenbank der Prüfung kennt nur das Passwort aus der Vorlage (testumgebung/.env.example);
# die Tests, die bis zum Webserver starten, geben ihr dafür kurz ein eigenes (_own_password).
OWN_PASSWORD = f"eigenes-passwort-{secrets.token_urlsafe(16)}"

# E1: Testumgebung auf dem Server mit eigenen Werten. TEST_ENVIRONMENT=1 setzt die Compose-Datei.
TEST_SERVER = {
    "DJANGO_ALLOWED_HOSTS": DOMAIN,
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
    "POSTGRES_PASSWORD": OWN_PASSWORD,
    "KEYCLOAK_CLIENT_SECRET": secrets.token_urlsafe(24),
    "DJANGO_BEHIND_HTTPS_PROXY": "1",
    "KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv-test",
    # Die Umgebungsdatei der Prüfung setzt beides für den eigenen Rechner; auf dem Server fehlen sie.
    "KEYCLOAK_REALM_URL_INTERN": "",
    "DJANGO_DEBUG": "",
}

# Startet den echten Start im Hintergrund und wartet, bis der Webserver Verbindungen annimmt.
STARTS_WEB_SERVER = (
    "sh docker/start.sh & "
    "for i in $(seq 60); do "
    "python -c \"import socket; socket.create_connection(('127.0.0.1', 8000), 1)\" 2>/dev/null && exit 0; "
    "sleep 1; done; exit 1"
)


def _start(env_file, change: dict[str, str], *command: str, deps: bool = False):
    arguments = ["run", "--rm"]
    if not deps:
        arguments.append("--no-deps")
    for name, value in {**TEST_SERVER, **change}.items():
        arguments += ["--env", f"{name}={value}"]
    return compose(*arguments, "tool", *command, env_file=env_file, check=False)


def _assert_does_not_start(result) -> str:
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    # gunicorn meldet seinen Start im Log; er darf nie gestartet sein.
    assert "Starting gunicorn" not in output, output
    assert "Listening at" not in output, output
    return output


def _log_lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if PREFIX in line]


@pytest.fixture
def _own_password(testumgebung):
    """Gibt dem Konto der Datenbank für einen Test ein eigenes Passwort und danach das alte zurück."""

    def set_password(value: str) -> None:
        compose(
            "exec",
            "-T",
            "datenbank",
            "sh",
            "-c",
            f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER USER \\"$POSTGRES_USER\\" PASSWORD \'{value}\'"',
            env_file=testumgebung,
        )

    set_password(OWN_PASSWORD)
    try:
        yield
    finally:
        compose(
            "exec",
            "-T",
            "datenbank",
            "sh",
            "-c",
            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "ALTER USER \\"$POSTGRES_USER\\" PASSWORD \'$POSTGRES_PASSWORD\'"',
            env_file=testumgebung,
        )


# ---------- E: Mit richtigen Werten startet das Tool ----------


def test_e1_testumgebung_auf_dem_server_startet_mit_eigenen_werten(testumgebung, _own_password):
    result = _start(testumgebung, {}, "sh", "-c", STARTS_WEB_SERVER, deps=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert PREFIX not in result.stdout + result.stderr


def test_e2_betrieb_startet_mit_eigenen_werten(testumgebung, _own_password):
    change = {"TEST_ENVIRONMENT": "", "KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv"}

    result = _start(testumgebung, change, "sh", "-c", STARTS_WEB_SERVER, deps=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert PREFIX not in result.stdout + result.stderr


# ---------- V: Jede Regel bricht den echten Start ab (G3) ----------

# Je Bedingung 1 bis 8 aus #325 ein Fall: Änderung gegenüber E1 und die Einstellung im Log.
UNSAFE = {
    "V1 Beispielwert": ({"KEYCLOAK_CLIENT_SECRET": "nur-lokal-nicht-geheim"}, "KEYCLOAK_CLIENT_SECRET"),
    "V2 schwacher Schlüssel": ({"DJANGO_SECRET_KEY": "kurz-aber-bunt-Q7x"}, "DJANGO_SECRET_KEY"),
    "V3 ohne HTTPS": ({"DJANGO_BEHIND_HTTPS_PROXY": ""}, "DJANGO_BEHIND_HTTPS_PROXY"),
    "V4 Keycloak lokal": ({"KEYCLOAK_REALM_URL": "http://localhost:8081/realms/dpv-test"}, "KEYCLOAK_REALM_URL"),
    "V5 interne Adresse": ({"KEYCLOAK_REALM_URL_INTERN": "http://keycloak:8080/realms/dpv"}, "KEYCLOAK_REALM_URL_INTERN"),
    "V6 lokaler Schalter": ({"LOCAL_ENVIRONMENT": "1"}, "LOCAL_ENVIRONMENT"),
    "V7 Testumgebung mit falschem Realm": ({"KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv"}, "KEYCLOAK_REALM_URL"),
    "V8 Betrieb mit Test-Realm": ({"TEST_ENVIRONMENT": ""}, "KEYCLOAK_REALM_URL"),
    "V9 Fehleranzeige": ({"DJANGO_DEBUG": "1"}, "DJANGO_DEBUG"),
    "V10 jeder Name": ({"DJANGO_ALLOWED_HOSTS": "*"}, "DJANGO_ALLOWED_HOSTS"),
    "G5 localhost und Testdomain": ({"DJANGO_ALLOWED_HOSTS": f"localhost,{DOMAIN}", "DJANGO_DEBUG": "1"}, "DJANGO_DEBUG"),
}


@pytest.mark.parametrize("change, setting", UNSAFE.values(), ids=UNSAFE.keys())
def test_v1_bis_v10_unsichere_einstellung_bricht_den_echten_start_ab(testumgebung, change, setting):
    output = _assert_does_not_start(_start(testumgebung, change))

    lines = _log_lines(output)
    assert len(lines) == 1, output
    assert setting in lines[0]
    assert lines[0].rstrip().endswith(SUFFIX)


def test_g1_g2_alle_probleme_auf_einmal_und_kein_wert_im_log(testumgebung):
    change = {
        "POSTGRES_PASSWORD": "testumgebung-lokal-nicht-geheim",
        "DJANGO_BEHIND_HTTPS_PROXY": "",
        "KEYCLOAK_REALM_URL": "http://localhost:8081/realms/dpv-test",
    }

    output = _assert_does_not_start(_start(testumgebung, change))

    lines = _log_lines(output)
    assert len(lines) == 3, output
    for setting in ("POSTGRES_PASSWORD", "DJANGO_BEHIND_HTTPS_PROXY", "KEYCLOAK_REALM_URL"):
        assert any(setting in line for line in lines), output
    for value in (*change.values(), TEST_SERVER["DJANGO_SECRET_KEY"], TEST_SERVER["KEYCLOAK_CLIENT_SECRET"], "8081"):
        if value:
            assert value not in output, f"Wert im Log: {value}"
