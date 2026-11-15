"""Startprüfung: Auf einem Server startet das Tool nicht mit unsicheren Einstellungen (#325).

Die Kennungen (E1, V4, G6 …) verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #325. Diese
Tests prüfen die Regeln der Startprüfung schnell und mit allen Schreibweisen; dass jede Regel den
echten Start des Containers abbricht, prüft containertests/test_startpruefung_container.py (G3).
Testdomain, Schlüssel und Passwörter sind erfunden.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from django.core import checks

from core.server_checks import EXAMPLE_VALUES, SECRET_SETTINGS, is_server, problems, server_settings_safe

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_LOCAL = BASE_DIR / ".env.example"
ENV_SERVER = BASE_DIR / "testumgebung" / ".env.example"
COMPOSE = BASE_DIR / "testumgebung" / "docker-compose.yml"

DOMAIN = "test.anmeldung.example.org"
PREFIX = "Unsichere Einstellung für den Server: "
SUFFIX = "(docs/betrieb.md)."

# E1: Max richtet die Testumgebung auf dem Server mit eigenen Werten ein.
TEST_SERVER = {
    "DJANGO_ALLOWED_HOSTS": DOMAIN,
    "DJANGO_SECRET_KEY": "Zx7-erfundener-langer-Schluessel-nur-fuer-diesen-Test-4f9Qa2",
    "POSTGRES_PASSWORD": "erfundenes-passwort-nur-fuer-diesen-test",
    "KEYCLOAK_CLIENT_SECRET": "erfundenes-geheimnis-nur-fuer-diesen-test",
    "DJANGO_BEHIND_HTTPS_PROXY": "1",
    "KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv-test",
    "TEST_ENVIRONMENT": "1",
}
# E2: dasselbe im Betrieb, ohne Testschalter und mit dem Realm des DPV.
PRODUCTION = {**TEST_SERVER, "KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv"}
del PRODUCTION["TEST_ENVIRONMENT"]


def _example(path: Path) -> dict[str, str]:
    """Einstellungen einer Vorlage; auskommentierte Zeilen zählen mit, als Beispiel für den Server."""
    found = {}
    for line in path.read_text().splitlines():
        match = re.match(r"^#?\s*([A-Z][A-Z0-9_]*)=(.*)$", line)
        if match:
            found[match.group(1)] = match.group(2)
    return found


def _lines(env: dict[str, str]) -> list[str]:
    return [line for _, line in problems(env)]


def _assert_line_format(line: str) -> None:
    assert line.startswith(PREFIX), line
    assert line.endswith(SUFFIX), line
    assert "\n" not in line


# ---------- E: Was weiter startet ----------


def test_e1_testumgebung_auf_dem_server_mit_eigenen_werten_ohne_befund():
    assert is_server(TEST_SERVER)
    assert problems(TEST_SERVER) == []


def test_e2_betrieb_mit_eigenen_werten_ohne_befund():
    assert is_server(PRODUCTION)
    assert problems(PRODUCTION) == []


def test_e3_eigener_rechner_mit_den_beispielwerten_ist_kein_server(monkeypatch):
    local = {**_example(ENV_SERVER), **_example(ENV_LOCAL)}
    assert local["DJANGO_DEBUG"] == "1" and local["LOCAL_ENVIRONMENT"] == "1"
    # Testumgebung auf dem Mac: Vorlage der Testumgebung, Schalter aus der Compose-Datei.
    mac = {**_example(ENV_SERVER), "TEST_ENVIRONMENT": "1", "DJANGO_DEBUG": "1"}

    for env in (local, mac, {}):
        assert not is_server(env)
        assert problems(env) == []

    # Auch die angemeldete Prüfung meldet dann nichts, obwohl die Einstellungen für einen Server
    # unsicher wären (etwa ohne HTTPS).
    for name in list(os.environ):
        monkeypatch.delenv(name)
    for name, value in local.items():
        monkeypatch.setenv(name, value)
    assert server_settings_safe(None) == []


# ---------- V: Was auf dem Server den Start abbricht ----------

# Je Fall: Änderung gegenüber E1 und die Einstellung, die die Zeile im Log nennt.
UNSAFE = {
    "V1 Schlüssel aus .env.example": ({"DJANGO_SECRET_KEY": _example(ENV_LOCAL)["DJANGO_SECRET_KEY"]}, "DJANGO_SECRET_KEY"),
    "V2 Schlüssel zu kurz": ({"DJANGO_SECRET_KEY": "kurz-aber-bunt-Q7x"}, "DJANGO_SECRET_KEY"),
    "V2 Schlüssel zu gleichförmig": ({"DJANGO_SECRET_KEY": "ab" * 40}, "DJANGO_SECRET_KEY"),
    "V2 Schlüssel als unsicher gekennzeichnet": ({"DJANGO_SECRET_KEY": "django-insecure-" + TEST_SERVER["DJANGO_SECRET_KEY"]}, "DJANGO_SECRET_KEY"),
    "V3 ohne HTTPS-Schalter": ({"DJANGO_BEHIND_HTTPS_PROXY": ""}, "DJANGO_BEHIND_HTTPS_PROXY"),
    "V4 Keycloak ohne https": ({"KEYCLOAK_REALM_URL": "http://login.example.org/realms/dpv-test"}, "KEYCLOAK_REALM_URL"),
    "V4 Keycloak auf localhost": ({"KEYCLOAK_REALM_URL": "https://localhost:8443/realms/dpv-test"}, "KEYCLOAK_REALM_URL"),
    "V4 Keycloak auf 127.0.0.1": ({"KEYCLOAK_REALM_URL": "https://127.0.0.1/realms/dpv-test"}, "KEYCLOAK_REALM_URL"),
    "V4 Keycloak im Container": ({"KEYCLOAK_REALM_URL": "https://keycloak:8080/realms/dpv-test"}, "KEYCLOAK_REALM_URL"),
    "V5 interne Adresse": ({"KEYCLOAK_REALM_URL_INTERN": "https://login.example.org/realms/dpv-test"}, "KEYCLOAK_REALM_URL_INTERN"),
    "V6 lokaler Schalter": ({"LOCAL_ENVIRONMENT": "1"}, "LOCAL_ENVIRONMENT"),
    "V7 Testumgebung mit dem Realm des DPV": ({"KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv"}, "KEYCLOAK_REALM_URL"),
    "V9 Fehleranzeige in der Testumgebung": ({"DJANGO_DEBUG": "1"}, "DJANGO_DEBUG"),
    "V10 jeder Name": ({"DJANGO_ALLOWED_HOSTS": f"{DOMAIN},*"}, "DJANGO_ALLOWED_HOSTS"),
}


@pytest.mark.parametrize("change, setting", UNSAFE.values(), ids=UNSAFE.keys())
def test_v1_bis_v10_unsichere_einstellung_ergibt_genau_eine_zeile(change, setting):
    lines = _lines({**TEST_SERVER, **change})

    assert len(lines) == 1, lines
    _assert_line_format(lines[0])
    assert setting in lines[0]


def test_v8_betrieb_mit_dem_test_realm():
    lines = _lines({**PRODUCTION, "KEYCLOAK_REALM_URL": "https://login.example.org/realms/dpv-test"})

    assert len(lines) == 1, lines
    _assert_line_format(lines[0])
    assert "KEYCLOAK_REALM_URL" in lines[0]
    assert "TEST_ENVIRONMENT" in lines[0]


EXAMPLES = sorted(
    {(name, value) for path in (ENV_LOCAL, ENV_SERVER) for name, value in _example(path).items() if name in SECRET_SETTINGS}
)


# V1 mit jedem Beispielwert beider Vorlagen: Jeder ist öffentlich, keiner darf auf einen Server.
@pytest.mark.parametrize("name, value", EXAMPLES, ids=[f"{n}={v}" for n, v in EXAMPLES])
def test_v1_jeder_beispielwert_aus_beiden_vorlagen(name, value):
    lines = _lines({**TEST_SERVER, name: value})

    assert len(lines) == 1, lines
    assert f"{name} ist ein öffentlich bekannter Beispielwert" in lines[0]


# ---------- G: Grenzfälle ----------


def test_g1_alle_probleme_auf_einmal_je_eine_zeile():
    env = {
        **TEST_SERVER,
        "DJANGO_SECRET_KEY": _example(ENV_SERVER)["DJANGO_SECRET_KEY"],
        "DJANGO_BEHIND_HTTPS_PROXY": "",
        "DJANGO_DEBUG": "1",
    }

    lines = _lines(env)

    assert len(lines) == 3, lines
    for line in lines:
        _assert_line_format(line)
    assert (
        "Unsichere Einstellung für den Server: DJANGO_SECRET_KEY ist ein öffentlich bekannter Beispielwert. "
        "Bitte einen eigenen geheimen Wert eintragen (docs/betrieb.md)." in lines
    )
    assert any("DJANGO_BEHIND_HTTPS_PROXY" in line for line in lines)
    assert any("DJANGO_DEBUG" in line for line in lines)
    # Jede Zeile hat ihre eigene Kennung.
    assert len({key for key, _ in problems(env)}) == 3


# Was eine Zeile als Grund nennen darf, auch wenn es im Wert vorkommt.
NAMED_IN_REASON = "https:// localhost 127.0.0.1 keycloak /realms/dpv-test"


def _fragments(value: str) -> set[str]:
    """Jedes Stück aus 8 Zeichen, außer es steht so auch im Grund (NAMED_IN_REASON)."""
    windows = {value[i : i + 8] for i in range(max(len(value) - 7, 1))}
    return {window for window in windows if window not in NAMED_IN_REASON}


# Schalter (V3, V6, V9) verraten nichts; geprüft wird jeder Fall mit einem freien Wert.
WITH_VALUE = {case: (change, setting) for case, (change, setting) in UNSAFE.items() if change[setting] not in {"", "1"}}


@pytest.mark.parametrize("change, setting", WITH_VALUE.values(), ids=WITH_VALUE.keys())
def test_g2_kein_wert_und_kein_teil_davon_im_log(change, setting):
    text = "\n".join(_lines({**TEST_SERVER, **change}))

    assert text, "keine Zeile im Log"
    for fragment in _fragments(change[setting]):
        assert fragment not in text, f"„{fragment}“ aus dem Wert von {setting} steht im Log: {text}"


def test_g5_localhost_zusammen_mit_testdomain_gilt_als_server():
    env = {**TEST_SERVER, "DJANGO_ALLOWED_HOSTS": f"localhost,{DOMAIN}", "DJANGO_DEBUG": "1"}

    assert is_server(env)
    assert len(_lines(env)) == 1
    assert not is_server({"DJANGO_ALLOWED_HOSTS": "localhost, 127.0.0.1"})


def test_g6_vorlagen_enthalten_nur_beispielwerte_die_die_startpruefung_kennt():
    for path in (ENV_LOCAL, ENV_SERVER):
        settings = _example(path)
        # Jede Einstellung, deren Name nach einem Geheimnis klingt, zählt die Startprüfung als geheim.
        secret_like = {name for name in settings if re.search(r"SECRET|PASSWORD|PASSWORT|TOKEN|_KEY$", name)}
        assert secret_like <= set(SECRET_SETTINGS), f"{path.name}: {secret_like - set(SECRET_SETTINGS)} fehlt in SECRET_SETTINGS"
        for name in SECRET_SETTINGS:
            if name in settings:
                assert settings[name] in EXAMPLE_VALUES, (
                    f"{path.name}: Beispielwert für {name} fehlt in EXAMPLE_VALUES (core/server_checks.py)"
                )


def test_g4_nach_dem_abbruch_versucht_der_container_es_neu_mit_derselben_pruefung():
    tool = yaml.safe_load(COMPOSE.read_text())["services"]["tool"]
    start = (BASE_DIR / "docker" / "start.sh").read_text()

    assert tool["restart"] == "unless-stopped"
    # Jeder Start prüft erneut: migrate läuft mit der Systemprüfung, und erst danach der Webserver.
    assert "set -e" in start
    assert start.index("manage.py migrate") < start.index("exec gunicorn")
    assert "--skip-checks" not in start


# ---------- Djangos eigene Prüfung für den Betrieb (check --deploy) ----------


def _server_environment(monkeypatch, env: dict[str, str]) -> None:
    for name in list(os.environ):
        monkeypatch.delenv(name)
    for name, value in env.items():
        monkeypatch.setenv(name, value)


def _messages(errors) -> list[str]:
    assert all(error.level >= checks.ERROR for error in errors), errors
    return [error.msg for error in errors]


def test_djangos_pruefung_fuer_den_betrieb_gehoert_auf_dem_server_dazu(monkeypatch, settings):
    _server_environment(monkeypatch, TEST_SERVER)
    # Eine Einstellung, die nur Djangos Prüfung für den Betrieb kennt: Weiterleitung auf HTTPS aus.
    settings.SECURE_SSL_REDIRECT = False

    messages = _messages(server_settings_safe(None))

    assert any("security.W008" in message for message in messages), messages
    for message in messages:
        _assert_line_format(message)


def test_djangos_pruefung_fuer_den_betrieb_laesst_die_entscheidung_zu_hsts_gelten(monkeypatch, settings):
    # HSTS nur für genau diese Adresse und ohne Vorab-Liste (Klärung von #324): keine Meldung dazu.
    _server_environment(monkeypatch, TEST_SERVER)
    settings.SECURE_HSTS_SECONDS = 365 * 24 * 60 * 60
    settings.SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    settings.SECURE_HSTS_PRELOAD = False

    messages = _messages(server_settings_safe(None))

    assert not any("security.W005" in message or "security.W021" in message for message in messages), messages


def test_djangos_pruefung_fuer_den_betrieb_nicht_auf_dem_eigenen_rechner(monkeypatch, settings):
    _server_environment(monkeypatch, {**_example(ENV_LOCAL), "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1"})
    settings.SECURE_SSL_REDIRECT = False

    assert server_settings_safe(None) == []


def test_startpruefung_ist_bei_django_angemeldet():
    assert server_settings_safe in checks.registry.registry.get_checks()


# ---------- V11: Tests nur gegen das Keycloak auf dem eigenen Rechner ----------

FOREIGN_KEYCLOAK = "https://keycloak.invalid/realms/dpv"
V11_MESSAGE = "Kein Test hat Keycloak angesprochen"


def _pytest_with_foreign_keycloak(*arguments: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "KEYCLOAK_REALM_URL": FOREIGN_KEYCLOAK, "KEYCLOAK_REALM_URL_INTERN": ""}
    return subprocess.run(  # noqa: S603 -- fester Befehl mit Dateien aus diesem Repo
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", *arguments],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.parametrize(
    "test_file",
    ["tests/test_keycloak_echt.py", "tests/test_testrealm_echt.py", "tests/test_sitzung_obergrenze_echt.py"],
)
def test_v11_keycloak_tests_brechen_gegen_fremdes_keycloak_ab_bevor_sie_es_ansprechen(test_file):
    result = _pytest_with_foreign_keycloak(test_file)
    output = result.stdout + result.stderr

    assert result.returncode != 0, output
    assert V11_MESSAGE in output, output
    # Angesprochen hätte ein Test die Adresse nur mit einer Meldung „nicht erreichbar“.
    assert "nicht erreichbar" not in output, output
    # Abgebrochen, bevor der erste Test oder seine Vorbereitung lief.
    assert "ERROR at setup" not in output, output
    assert " passed" not in output, output


def test_v11_rauchtests_brechen_gegen_fremdes_keycloak_ab_bevor_sie_es_ansprechen():
    result = _pytest_with_foreign_keycloak("rauchtests/test_rauchtest.py")
    output = result.stdout + result.stderr

    assert result.returncode != 0, output
    assert V11_MESSAGE in output, output
    assert "nicht erreichbar" not in output, output
    # Abgebrochen, bevor der erste Test oder seine Vorbereitung lief.
    assert "ERROR at setup" not in output, output
    assert " passed" not in output, output
