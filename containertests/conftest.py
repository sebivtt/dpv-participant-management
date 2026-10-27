"""Startet die Testumgebung im Container für containertests/ (#58).

Gebaut und gestartet wird genau das, was Sebastian nach dem README startet
(testumgebung/docker-compose.yml), mit der Keycloak-Testumgebung für den eigenen Rechner
(Profil „lokal“). Damit eine schon laufende Testumgebung auf dem Mac unberührt bleibt, läuft
die Prüfung unter einem eigenen Namen und mit eigener Ablage, die danach wieder gelöscht wird.
Sie nutzt eigene Ports (tests/check_ports.py), nicht 8000 und 8081 der eigenen Testumgebung
und des eigenen Tools; die laufen dabei weiter (#167). Name und Ports sind fest; eine
Container-Prüfung aus einer anderen Arbeitskopie läuft deshalb erst, wenn diese fertig ist (#184).
"""

import os
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.check_ports import (
    CONTAINER_KEYCLOAK_PORT,
    CONTAINER_LOCK_PORT,
    CONTAINER_TOOL_PORT,
    PORT_RELEASE_SECONDS,
    fail_if_busy,
    tell,
    wait_for_turn,
)

BASE_DIR = Path(__file__).resolve().parent.parent
COMPOSE_FILE = BASE_DIR / "testumgebung" / "docker-compose.yml"
ENV_EXAMPLE = BASE_DIR / "testumgebung" / ".env.example"
PROJECT = "dpv-pruefung"

TOOL = f"http://localhost:{CONTAINER_TOOL_PORT}"
KEYCLOAK = f"http://localhost:{CONTAINER_KEYCLOAK_PORT}"
# Die Ports der Testumgebung sind einstellbar (testumgebung/docker-compose.yml); ohne Angabe 8000 und 8081.
PORTS = {"TESTUMGEBUNG_TOOL_PORT": str(CONTAINER_TOOL_PORT), "TESTUMGEBUNG_KEYCLOAK_PORT": str(CONTAINER_KEYCLOAK_PORT)}


def compose(*arguments: str, env_file: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Ruft docker compose für die Prüf-Testumgebung auf und gibt Ausgabe und Ergebnis zurück."""
    command = [
        "docker",
        "compose",
        "--project-name",
        PROJECT,
        "--file",
        str(COMPOSE_FILE),
        "--profile",
        "lokal",
        # Dieselbe Datei für die Angaben der Datenbank in der Compose-Datei wie für das Tool.
        "--env-file",
        str(env_file),
        *arguments,
    ]
    return subprocess.run(  # noqa: S603 -- fester Befehl, die Angaben stammen aus diesem Repo
        command,
        env={**_path_only(), "TESTUMGEBUNG_ENV_FILE": str(env_file), "TESTUMGEBUNG_TAG": PROJECT, **PORTS},
        capture_output=True,
        text=True,
        check=check,
        timeout=900,
    )


def _path_only() -> dict[str, str]:
    """Nur die Angaben, die docker selbst braucht; nichts aus der Umgebung der Tests."""
    keep = ("PATH", "HOME", "DOCKER_HOST", "DOCKER_CONFIG", "DOCKER_CONTEXT", "XDG_RUNTIME_DIR")
    return {name: os.environ[name] for name in keep if name in os.environ}


def wait_for(url: str, seconds: int = 180) -> None:
    """Wartet, bis die Adresse antwortet; der erste Start von Keycloak dauert."""
    deadline = time.monotonic() + seconds
    while True:
        try:
            with urllib.request.urlopen(url, timeout=5):  # noqa: S310 -- nur localhost
                return
        except OSError:
            if time.monotonic() > deadline:
                raise
            time.sleep(2)


def env_file_content() -> str:
    """Umgebungsdatei aus der Vorlage, dazu absichtlich die eingeschaltete Fehleranzeige (Szenario 4).

    Der Browser erreicht Keycloak hier unter dem Port der Prüfung statt unter 8081 (#167).
    """
    example = ENV_EXAMPLE.read_text()
    own_keycloak = "KEYCLOAK_REALM_URL=http://localhost:8081/realms/dpv\n"
    assert own_keycloak in example, "Vorlage geändert: Adresse von Keycloak in der Prüfung anpassen."
    example = example.replace(own_keycloak, f"KEYCLOAK_REALM_URL={KEYCLOAK}/realms/dpv\n")
    return example + "\n# Nur in der Prüfung: Die Testumgebung muss das ignorieren.\nDJANGO_DEBUG=1\n"


@pytest.fixture(scope="session")
def env_file(tmp_path_factory) -> Path:
    """Schreibt die Umgebungsdatei der Prüfung (env_file_content) in einen eigenen Ordner."""
    path = tmp_path_factory.mktemp("testumgebung") / ".env"
    path.write_text(env_file_content())
    return path


@pytest.fixture(scope="session")
def testumgebung(env_file, request) -> Iterator[Path]:
    """Baut und startet die Testumgebung, wartet, bis sie antwortet, und räumt danach alles ab.

    Erst, wenn keine andere Container-Prüfung mehr läuft: Das Abräumen am Anfang träfe sonst
    deren Container (#184).
    """
    with wait_for_turn(CONTAINER_LOCK_PORT, "Container-Prüfung", say=tell(request.config)):
        compose("down", "--volumes", "--remove-orphans", env_file=env_file, check=False)
        fail_if_busy(CONTAINER_TOOL_PORT, "das Tool in der Prüfung der Testumgebung", seconds=PORT_RELEASE_SECONDS)
        fail_if_busy(CONTAINER_KEYCLOAK_PORT, "Keycloak in der Prüfung der Testumgebung", seconds=PORT_RELEASE_SECONDS)
        started = compose("up", "--detach", "--build", "--wait", env_file=env_file, check=False)
        try:
            assert started.returncode == 0, started.stdout + started.stderr
            wait_for(f"{KEYCLOAK}/realms/dpv/.well-known/openid-configuration")
            wait_for(f"{TOOL}/anmelden/")
            yield env_file
        finally:
            compose("down", "--volumes", "--remove-orphans", env_file=env_file, check=False)
