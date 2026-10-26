"""Tests für den Aufbau der Testumgebung im Container (#58, Teil 1 von #37).

Geprüft werden die Dateien, aus denen Docker die Testumgebung baut und startet: Compose-Datei,
Bauvorlage des Abbilds (Dockerfile) und Startskript. Die Regeln dahinter: eigene Datenbank,
die von außen nicht erreichbar ist (Szenario 6 in #58), keine gemeinsamen Ablagen, keine
Zugangsdaten im Abbild und kein Zugriffsprotokoll mit echten Adressen (Entscheidung zu #6).
Dass der Container wirklich startet, prüfen containertests/ (eigener Lauf in pruefen.sh).
"""

import json
import os
import re
import subprocess
from pathlib import Path

import yaml

from tests.check_ports import CONTAINER_KEYCLOAK_PORT, CONTAINER_TOOL_PORT

BASE_DIR = Path(__file__).resolve().parent.parent
COMPOSE = BASE_DIR / "testumgebung" / "docker-compose.yml"
DOCKERFILE = BASE_DIR / "Dockerfile"
DOCKERIGNORE = BASE_DIR / ".dockerignore"
START = BASE_DIR / "docker" / "start.sh"
ENV_EXAMPLE = BASE_DIR / "testumgebung" / ".env.example"
GUNICORN = BASE_DIR / "docker" / "gunicorn.conf.py"


def _gunicorn_settings() -> dict:
    """Liest die Einstellungsdatei von gunicorn so, wie gunicorn sie liest: als Python-Datei."""
    namespace: dict = {}
    exec(compile(GUNICORN.read_text(), str(GUNICORN), "exec"), namespace)  # noqa: S102 -- eigene Datei aus dem Repo
    return namespace


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text())


def _services() -> dict:
    return _compose()["services"]


def _networks(service: dict) -> set[str]:
    networks = service.get("networks", [])
    return set(networks) if isinstance(networks, list) else set(networks.keys())


def _environment(service: dict) -> dict[str, str]:
    environment = service.get("environment", {})
    if isinstance(environment, list):
        return dict(item.split("=", 1) for item in environment)
    return {key: str(value) for key, value in environment.items()}


def _volume_sources(service: dict) -> list[str]:
    return [(v.split(":", 1)[0] if isinstance(v, str) else v["source"]) for v in service.get("volumes", [])]


# ---------- Szenario 6: Datenbank nur für das Tool ----------


def test_datenbank_ist_von_aussen_nicht_erreichbar():
    database = _services()["datenbank"]

    assert "ports" not in database
    assert _networks(database) == {"intern"}
    assert _compose()["networks"]["intern"]["internal"] is True


def test_datenbank_ist_postgresql_18_wie_lokal_und_auf_github():
    assert _services()["datenbank"]["image"] == "postgres:18"


def test_tool_erreicht_die_datenbank_und_ist_selbst_nur_vom_eigenen_rechner_aus_erreichbar():
    tool = _services()["tool"]

    assert {"intern", "aussen"} <= _networks(tool)
    for port in tool.get("ports", []):
        assert str(port).startswith("127.0.0.1:"), port


def test_keine_gemeinsamen_ablagen_und_keine_ordner_vom_rechner():
    services = _services()
    named_volumes = set((_compose().get("volumes") or {}).keys())
    users_per_volume: dict[str, list[str]] = {}
    for name, service in services.items():
        for source in _volume_sources(service):
            # Eigene, benannte Ablagen sind erlaubt; Ordner vom Rechner nur lesend für die
            # erfundenen Konten der Keycloak-Testumgebung, die es auf dem Server nicht gibt.
            if source not in named_volumes:
                assert name == "keycloak" and source.startswith("../dev/keycloak/"), (name, source)
                continue
            users_per_volume.setdefault(source, []).append(name)

    assert all(len(users) == 1 for users in users_per_volume.values()), users_per_volume


def test_daten_der_testumgebung_liegen_in_einer_eigenen_ablage():
    # Szenario 10: Nur so überstehen sie Aktualisieren und Neustart.
    database = _services()["datenbank"]

    assert any(source in (_compose().get("volumes") or {}) for source in _volume_sources(database))


def test_datenbank_bekommt_nur_ihre_eigenen_zugangsdaten():
    # Die Datenbank braucht nur Name, Benutzer und Passwort, nicht die Schlüssel des Tools
    # oder den Zugang zu Keycloak (unabhängige Prüfung zu #58).
    database = _services()["datenbank"]

    assert "env_file" not in database
    assert set(_environment(database)) == {"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"}


# ---------- Szenarien 1 und 4: Testumgebung eingeschaltet, Fehleranzeige nicht durchgereicht ----------


def test_tool_laeuft_als_testumgebung():
    assert _environment(_services()["tool"])["TEST_ENVIRONMENT"] == "1"


def test_compose_datei_schaltet_die_fehleranzeige_nicht_ein():
    assert "DJANGO_DEBUG" not in _environment(_services()["tool"])


def test_pruefung_ueberschreibt_das_abbild_der_eigenen_testumgebung_nicht(monkeypatch, tmp_path):
    from containertests import conftest

    calls = []
    monkeypatch.setattr(conftest.subprocess, "run", lambda command, **kwargs: calls.append(kwargs["env"]))

    conftest.compose("config", env_file=tmp_path / ".env")

    assert _services()["tool"]["image"] == "dpv-anmeldetool:${TESTUMGEBUNG_TAG:-test}"
    assert calls[0]["TESTUMGEBUNG_TAG"] not in ("", "test")


def test_keycloak_der_testumgebung_startet_nur_auf_dem_eigenen_rechner():
    keycloak = _services()["keycloak"]

    assert keycloak["profiles"] == ["lokal"]
    assert "intern" not in _networks(keycloak)


def test_vorlage_der_umgebungsdatei_hat_nur_erfundene_werte():
    values = dict(
        line.split("=", 1) for line in ENV_EXAMPLE.read_text().splitlines() if line and not line.startswith("#")
    )

    for name in ("DJANGO_SECRET_KEY", "POSTGRES_PASSWORD", "KEYCLOAK_CLIENT_SECRET"):
        assert "nicht-geheim" in values[name], name
    assert "DJANGO_DEBUG" not in values


# ---------- Abbild ----------


def _dockerignore() -> list[str]:
    return [line.strip() for line in DOCKERIGNORE.read_text().splitlines() if line.strip() and not line.startswith("#")]


def test_ins_abbild_kommt_nur_was_ausdruecklich_erlaubt_ist():
    # Das Abbild entsteht aus dem Arbeitsordner, nicht aus dem Stand auf GitHub. Dort können
    # Dateien liegen, die .gitignore bewusst fernhält (Zugangsdaten, Exporte, lokale Datenbanken).
    # Deshalb erst alles ausschließen und nur das Nötige freigeben (unabhängige Prüfung zu #58).
    lines = _dockerignore()
    allowed = {line[1:] for line in lines if line.startswith("!")}

    assert lines[0] == "*"
    assert allowed == {
        "access",
        "accounts",
        "config",
        "core",
        "docker",
        "units",
        "roles",
        "manage.py",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "README.md",
        "LICENSE",
    }


def test_auch_in_freigegebenen_ordnern_keine_zugangsdaten_und_keine_daten():
    lines = _dockerignore()
    last_allowed = max(i for i, line in enumerate(lines) if line.startswith("!"))
    excluded_afterwards = set(lines[last_allowed + 1 :])

    for pattern in ("**/.env", "**/.env.*", "**/*.env", "**/*.pem", "**/*.key", "**/*.csv", "**/*.xlsx"):
        assert pattern in excluded_afterwards, pattern
    for pattern in ("**/*.dump", "**/*.sql.gz", "**/*.sqlite3", "**/*.log", "**/__pycache__"):
        assert pattern in excluded_afterwards, pattern
    assert ".env" not in DOCKERFILE.read_text().replace(".env.example", "")


def test_jede_eigene_app_kommt_ins_abbild():
    # Fehlt eine neue App in .dockerignore, startet das Tool im Container nicht, obwohl alle
    # übrigen Tests grün sind (passiert bei #88 mit „units“; erst der Container-Test bemerkte es).
    from django.conf import settings

    allowed = {line[1:] for line in _dockerignore() if line.startswith("!")}
    own_apps = {app.split(".")[0] for app in settings.INSTALLED_APPS if (BASE_DIR / app.split(".")[0]).is_dir()}

    assert own_apps
    assert own_apps <= allowed, own_apps - allowed


def test_jeder_eigene_python_ordner_kommt_ins_abbild():
    # Wie oben, auch für Ordner, die keine eingetragene App sind (passiert bei #90 mit „access“,
    # das nur als Middleware eingetragen ist; erst der Container-Test bemerkte es).
    allowed = {line[1:] for line in _dockerignore() if line.startswith("!")}
    only_for_tests = {"tests", "rauchtests", "containertests"}
    packages = {
        path.parent.name for path in BASE_DIR.glob("*/__init__.py") if path.parent.name not in only_for_tests
    }

    assert "access" in packages
    assert packages <= allowed, packages - allowed


def test_abbild_enthaelt_nur_die_pakete_fuer_den_betrieb():
    dockerfile = DOCKERFILE.read_text()

    assert re.search(r"uv sync [^\n]*--locked", dockerfile)
    assert re.search(r"uv sync [^\n]*--no-dev", dockerfile)


def test_tool_laeuft_im_abbild_nicht_als_verwalter():
    users = re.findall(r"^USER\s+(\S+)", DOCKERFILE.read_text(), re.M)

    assert users and users[-1] not in ("root", "0")


def test_start_bringt_erst_die_datenbank_auf_stand_dann_den_webserver():
    script = START.read_text()

    assert script.index("manage.py migrate") < script.index("exec gunicorn")
    assert "set -e" in script


def test_webserver_startet_mit_der_einstellungsdatei():
    assert "-c docker/gunicorn.conf.py" in START.read_text()


def test_webserver_schreibt_kein_zugriffsprotokoll_mit_echten_adressen():
    # Entscheidung zu #6: Im Log steht nie die echte Adresse mit Nummern und Parametern.
    # Ein Zugriffsprotokoll des Webservers enthielte genau das; ob es eins braucht, klärt #11.
    # Das übrige Log von gunicorn prüft tests/test_webserver_log.py.
    settings = _gunicorn_settings()

    assert settings.get("accesslog") is None
    assert "--access-log" not in START.read_text()
    assert settings["logger_class"] == "core.gunicorn_log.SafeLogger"


def test_webserver_hat_keinen_steuerzugang():
    # gunicorn legt sonst einen Steuerzugang im Benutzerordner an, über den sich der laufende
    # Webserver bedienen lässt. Gebraucht wird er nicht, und der Benutzer im Abbild hat
    # absichtlich keinen eigenen Ordner.
    assert _gunicorn_settings()["control_socket_disable"] is True


# ---------- Eigene Ports für die Prüfung (#167) ----------


def _compose_config(**ports: str) -> dict:
    """Die Testumgebung, wie Docker Compose sie mit diesen Angaben startet (ohne zu starten)."""
    env = {name: os.environ[name] for name in ("PATH", "HOME", "DOCKER_CONFIG") if name in os.environ}
    command = ["docker", "compose", "--file", str(COMPOSE), "--profile", "lokal"]
    command += ["--env-file", str(ENV_EXAMPLE), "config", "--format", "json"]
    result = subprocess.run(  # noqa: S603 -- fester Befehl, die Angaben stammen aus diesem Repo
        command,
        env={**env, "TESTUMGEBUNG_ENV_FILE": str(ENV_EXAMPLE), **ports},
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout)["services"]


def _published(service: dict) -> list[tuple[str, str, int]]:
    return [(p["host_ip"], p["published"], p["target"]) for p in service["ports"]]


def test_eigene_testumgebung_bleibt_ohne_angabe_auf_8000_und_8081():
    services = _compose_config()

    assert _published(services["tool"]) == [("127.0.0.1", "8000", 8000)]
    assert _published(services["keycloak"]) == [("127.0.0.1", "8081", 8080)]
    assert "--hostname=http://localhost:8081" in services["keycloak"]["command"]


def test_pruefung_startet_die_testumgebung_auf_eigenen_ports(monkeypatch, tmp_path):
    from containertests import conftest

    calls = []
    monkeypatch.setattr(conftest.subprocess, "run", lambda command, **kwargs: calls.append(kwargs["env"]))
    conftest.compose("config", env_file=tmp_path / ".env")
    monkeypatch.undo()
    ports = {name: value for name, value in calls[0].items() if name.endswith("_PORT")}

    services = _compose_config(**ports)

    assert _published(services["tool"]) == [("127.0.0.1", str(CONTAINER_TOOL_PORT), 8000)]
    assert _published(services["keycloak"]) == [("127.0.0.1", str(CONTAINER_KEYCLOAK_PORT), 8080)]
    # Keycloak nennt dem Browser die Adresse, unter der er es wirklich erreicht.
    assert f"--hostname=http://localhost:{CONTAINER_KEYCLOAK_PORT}" in services["keycloak"]["command"]


def test_tool_der_pruefung_schickt_den_browser_zum_keycloak_der_pruefung():
    from containertests.conftest import env_file_content

    values = dict(line.split("=", 1) for line in env_file_content().splitlines() if line and not line.startswith("#"))

    assert values["KEYCLOAK_REALM_URL"] == f"http://localhost:{CONTAINER_KEYCLOAK_PORT}/realms/dpv"
    assert values["KEYCLOAK_REALM_URL_INTERN"] == "http://keycloak:8080/realms/dpv"
    # Szenario 4 aus #58 bleibt: Die Prüfung schaltet die Fehleranzeige absichtlich ein.
    assert values["DJANGO_DEBUG"] == "1"
