"""Die Prüfungen laufen auf eigenen Ports, nie auf denen des eigenen Tools (#167).

Port 8000 und 8081 gehören Sebastian: das Tool aus README Schritt 9 und die eigene
Testumgebung im Container (README, Schritt T). Der Rauchtest und die Prüfung der Testumgebung
im Container nutzen feste Ports, die sonst nichts nutzt, damit beides gleichzeitig laufen kann.
Ist ein Prüf-Port trotzdem belegt, nennt die Prüfung den Port und was zu tun ist.
"""

import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from tests.check_ports import (
    CONTAINER_KEYCLOAK_PORT,
    CONTAINER_LOCK_PORT,
    CONTAINER_TOOL_PORT,
    SMOKE_TEST_LOCK_PORT,
    SMOKE_TEST_PORT,
    WAIT_FOR_OTHER_CHECK_SECONDS,
    busy_port_message,
    fail_if_busy,
    is_busy,
    wait_for_turn,
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
    check_ports = [SMOKE_TEST_PORT, CONTAINER_TOOL_PORT, CONTAINER_KEYCLOAK_PORT, SMOKE_TEST_LOCK_PORT, CONTAINER_LOCK_PORT]

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


def test_pruefport_der_eben_frei_wird_laesst_die_pruefung_weiterlaufen():
    # Nach dem vorigen Prüflauf ist ein Port auf dem Mac noch kurz belegt (#167); das darf den
    # nächsten Lauf, der auf ihn gewartet hat, nicht abbrechen (#184).
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    threading.Timer(0.5, listener.close).start()

    fail_if_busy(port, "den Test", seconds=10)

    assert not is_busy(port)


# Wartesperre für Rauchtest und Container-Prüfung (#184). Die Tests nutzen freie Ports statt
# 8019 und 8029, damit sie einen gleichzeitigen echten Prüflauf nicht stören.

ZWEITER_LAUF = """
import sys
from tests.check_ports import wait_for_turn
with wait_for_turn(int(sys.argv[1]), "den Test", say=lambda text: print(text, flush=True), seconds=60, pause=0.1):
    print("weiter", flush=True)
"""

ABSTURZ = """
import sys, time
from tests.check_ports import wait_for_turn
with wait_for_turn(int(sys.argv[1]), "den Test", say=print, seconds=5):
    print("dran", flush=True)
    time.sleep(60)
"""


def _nichts(text: str) -> None:
    pass


def _python(code: str, port: int) -> subprocess.Popen:
    return subprocess.Popen(  # noqa: S603 -- fester Code aus diesem Test
        [sys.executable, "-c", code, str(port)], cwd=BASE_DIR, stdout=subprocess.PIPE, text=True
    )


def test_zweiter_lauf_wartet_auf_den_ersten_und_laeuft_danach_weiter():
    port = _free_port()
    with wait_for_turn(port, "den Test", say=_nichts):
        zweiter = _python(ZWEITER_LAUF, port)
        try:
            assert zweiter.stdout.readline().strip() == "Warte auf eine andere Prüfung (den Test) …"
            time.sleep(1)
            # Er wartet, statt abzubrechen.
            assert zweiter.poll() is None
        except BaseException:
            zweiter.kill()
            raise

    rest, _ = zweiter.communicate(timeout=30)
    assert rest.strip() == "weiter"
    assert zweiter.returncode == 0


def test_wer_gleich_dran_ist_wartet_nicht_und_meldet_nichts():
    gesagt = []

    with wait_for_turn(_free_port(), "den Test", seconds=0, say=gesagt.append):
        pass

    assert gesagt == []


def test_nach_der_wartezeit_bricht_der_wartende_lauf_mit_meldung_ab():
    port = _free_port()
    with wait_for_turn(port, "den Test", say=_nichts):
        with pytest.raises(pytest.fail.Exception) as abbruch:
            with wait_for_turn(port, "den Test", seconds=0.3, pause=0.1, say=_nichts):
                pass

    meldung = str(abbruch.value)
    assert "den Test" in meldung
    assert "./pruefen.sh" in meldung
    assert f"lsof -i :{port}" in meldung


def test_gewartet_wird_hoechstens_30_minuten():
    assert WAIT_FOR_OTHER_CHECK_SECONDS == 30 * 60


def test_abgestuerzter_lauf_gibt_die_sperre_von_selbst_frei():
    port = _free_port()
    erster = _python(ABSTURZ, port)
    try:
        assert erster.stdout.readline().strip() == "dran"
    finally:
        erster.kill()
        erster.wait()

    gesagt = []
    with wait_for_turn(port, "den Test", seconds=0, say=gesagt.append):
        pass

    assert gesagt == []
