"""Startet die Testumgebung im Container für containertests/ (#58).

Gebaut und gestartet wird genau das, was Sebastian nach dem README startet
(testumgebung/docker-compose.yml), mit der Keycloak-Testumgebung für den eigenen Rechner
(Profil „lokal“). Damit eine schon laufende Testumgebung auf dem Mac unberührt bleibt, läuft
die Prüfung unter einem eigenen Namen und mit eigener Ablage, die danach wieder gelöscht wird.
Sie braucht wie die Testumgebung die Ports 8000 und 8081.
"""

import os
import subprocess
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
COMPOSE_FILE = BASE_DIR / "testumgebung" / "docker-compose.yml"
ENV_EXAMPLE = BASE_DIR / "testumgebung" / ".env.example"
PROJECT = "dpv-pruefung"

TOOL = "http://localhost:8000"
KEYCLOAK = "http://localhost:8081"


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
        env={**_path_only(), "TESTUMGEBUNG_ENV_FILE": str(env_file), "TESTUMGEBUNG_TAG": PROJECT},
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


@pytest.fixture(scope="session")
def env_file(tmp_path_factory) -> Path:
    """Umgebungsdatei aus der Vorlage, dazu absichtlich die eingeschaltete Fehleranzeige (Szenario 4)."""
    path = tmp_path_factory.mktemp("testumgebung") / ".env"
    path.write_text(
        ENV_EXAMPLE.read_text() + "\n# Nur in der Prüfung: Die Testumgebung muss das ignorieren.\nDJANGO_DEBUG=1\n"
    )
    return path


@pytest.fixture(scope="session")
def testumgebung(env_file) -> Iterator[Path]:
    """Baut und startet die Testumgebung, wartet, bis sie antwortet, und räumt danach alles ab."""
    compose("down", "--volumes", "--remove-orphans", env_file=env_file, check=False)
    started = compose("up", "--detach", "--build", "--wait", env_file=env_file, check=False)
    try:
        assert started.returncode == 0, started.stdout + started.stderr
        wait_for(f"{KEYCLOAK}/realms/dpv/.well-known/openid-configuration")
        wait_for(f"{TOOL}/anmelden/")
        yield env_file
    finally:
        compose("down", "--volumes", "--remove-orphans", env_file=env_file, check=False)
