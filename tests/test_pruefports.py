"""Die Prüfungen laufen auf eigenen Ports, nie auf denen des eigenen Tools (#167).

Port 8000 und 8081 gehören Sebastian: das Tool aus README Schritt 9 und die eigene
Testumgebung im Container (README, Schritt T). Der Rauchtest und die Prüfung der Testumgebung
im Container nutzen feste Ports, die sonst nichts nutzt, damit beides gleichzeitig laufen kann.
Ist ein Prüf-Port trotzdem belegt, nennt die Prüfung den Port und was zu tun ist.
"""

import json
import socket
from pathlib import Path

import pytest

from tests.check_ports import (
    CONTAINER_KEYCLOAK_PORT,
    CONTAINER_TOOL_PORT,
    SMOKE_TEST_PORT,
    busy_port_message,
    fail_if_busy,
    is_busy,
)

BASE_DIR = Path(__file__).resolve().parent.parent
REALM = BASE_DIR / "dev" / "keycloak" / "dpv-realm.json"

# Port 8000 und 8081: eigenes Tool und eigene Testumgebung; 8080 und 5432: Keycloak und
# Datenbank aus dev/docker-compose.yml, die für die Prüfungen laufen.
OWN_PORTS = {8000, 8081, 8080, 5432}


def _client() -> dict:
    realm = json.loads(REALM.read_text())
    return next(c for c in realm["clients"] if c["clientId"] == "dpv-anmeldetool")


def test_pruefungen_belegen_nie_die_ports_des_eigenen_tools_und_der_eigenen_testumgebung():
    check_ports = [SMOKE_TEST_PORT, CONTAINER_TOOL_PORT, CONTAINER_KEYCLOAK_PORT]

    assert not set(check_ports) & OWN_PORTS
    assert len(set(check_ports)) == len(check_ports)


def test_lokales_keycloak_laesst_die_rueckkehr_zu_den_pruefungen_zu():
    # Rauchtest und Container-Prüfung melden sich bei einem Keycloak mit dieser Datei an.
    client = _client()
    logout = client["attributes"]["post.logout.redirect.uris"].split("##")

    for port in (SMOKE_TEST_PORT, CONTAINER_TOOL_PORT):
        assert f"http://localhost:{port}/anmelden/keycloak/zurueck/" in client["redirectUris"], port
        assert f"http://localhost:{port}/anmelden/" in logout, port


def test_lokales_keycloak_laesst_die_rueckkehr_zum_eigenen_tool_weiter_zu():
    # Gegenprobe: Das Tool aus README Schritt 9 muss sich weiter anmelden und abmelden können.
    client = _client()
    logout = client["attributes"]["post.logout.redirect.uris"].split("##")

    for host in ("127.0.0.1:8000", "localhost:8000"):
        assert f"http://{host}/anmelden/keycloak/zurueck/" in client["redirectUris"], host
        assert f"http://{host}/anmelden/" in logout, host


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_belegter_port_wird_erkannt():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        assert is_busy(port)


def test_freier_port_gilt_als_frei():
    assert not is_busy(_free_port())


def test_meldung_nennt_den_port_und_was_zu_tun_ist():
    message = busy_port_message(8010, "den Rauchtest")

    assert "Port 8010 ist belegt" in message
    assert "den Rauchtest" in message
    assert "lsof -i :8010" in message
    # Port 8000 bleibt dem eigenen Tool; das muss niemand beenden.
    assert "8000" not in message


def test_belegter_pruefport_bricht_mit_der_meldung_ab():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]

        with pytest.raises(pytest.fail.Exception, match=f"Port {port} ist belegt; die Prüfung braucht ihn für den Test"):
            fail_if_busy(port, "den Test")


def test_freier_pruefport_laesst_die_pruefung_weiterlaufen():
    fail_if_busy(_free_port(), "den Test")
