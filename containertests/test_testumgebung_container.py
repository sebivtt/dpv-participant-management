"""Die Testumgebung startet im Container und tut, was #58 verlangt.

Die Nummern verweisen auf die Szenarien im Kommentar „Szenarien für die Umsetzung“ in #58.
Angemeldet wird wirklich bei der Keycloak-Testumgebung, mit einem erfundenen Konto aus
dev/keycloak/dpv-realm.json. Jeder Test steht für sich; Szenario 10
meldet sich dafür selbst an und prüft, dass das Konto nach dem Aktualisieren noch da ist.
"""

import html
import json
import re
import socket

import pytest
import requests

from containertests.conftest import KEYCLOAK, TOOL, compose, wait_for
from tests.check_ports import CONTAINER_KEYCLOAK_PORT, CONTAINER_LOCK_PORT, CONTAINER_TOOL_PORT
from tests.localhost_browser import BrowserOnLocalhost

BAND = "Testumgebung: Hier gibt es nur erfundene Daten. Bitte gib keine echten Angaben ein."
ERIKA = ("erika.testfrau", "testpasswort-erika")


def _form(page: str, marker: str) -> tuple[str, dict[str, str]]:
    """Liest Ziel und versteckte Felder des Formulars, in dem `marker` vorkommt."""
    forms = re.findall(r"<form\b[^>]*>.*?</form>", page, re.S)
    form = next(f for f in forms if marker in f)
    action = html.unescape(re.search(r'action="([^"]*)"', form).group(1))
    hidden = {
        html.unescape(name): html.unescape(value)
        for name, value in re.findall(r'<input[^>]*type="hidden"[^>]*name="([^"]*)"[^>]*value="([^"]*)"', form)
    }
    return action, hidden


def _login(user: tuple[str, str]) -> requests.Response:
    """Meldet sich an wie eine Person im Browser: Login-Seite, Keycloak, zurück ins Tool."""
    session = BrowserOnLocalhost()
    login_page = session.get(f"{TOOL}/anmelden/", timeout=30)
    action, fields = _form(login_page.text, "Mit DPV-Konto anmelden")
    keycloak_page = session.post(f"{TOOL}{action}", data=fields, timeout=30)
    assert f"localhost:{CONTAINER_KEYCLOAK_PORT}" in keycloak_page.url, keycloak_page.url
    action, fields = _form(keycloak_page.text, 'name="username"')
    start_page = session.post(action, data={**fields, "username": user[0], "password": user[1]}, timeout=60)
    assert start_page.url == f"{TOOL}/", f"Login bei Keycloak gescheitert ({start_page.status_code})"
    return start_page


def _number_of_accounts(env_file) -> int:
    result = compose(
        "exec",
        "-T",
        "tool",
        "python",
        "manage.py",
        "shell",
        "-c",
        "from django.contrib.auth import get_user_model; print(get_user_model().objects.count())",
        env_file=env_file,
    )
    return int(result.stdout.strip().splitlines()[-1])


# Szenarien 1 und 8
def test_login_seite_mit_band_und_hinweis_an_suchmaschinen(testumgebung):
    response = requests.get(f"{TOOL}/anmelden/", timeout=30)

    assert response.status_code == 200
    assert BAND in html.unescape(response.text)
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    # Gestaltung kommt auch im Container vom eigenen Server.
    assert requests.get(f"{TOOL}/static/core/app.css", timeout=30).status_code == 200


# #167: Port 8000 und 8081 bleiben dem eigenen Tool und der eigenen Testumgebung.
def test_pruefung_belegt_nur_ihre_eigenen_ports(testumgebung):
    def published(service: str) -> set[int]:
        listing = compose("ps", "--format", "json", service, env_file=testumgebung).stdout
        return {p["PublishedPort"] for line in listing.splitlines() for p in json.loads(line)["Publishers"] or []}

    assert published("tool") - {0} == {CONTAINER_TOOL_PORT}
    assert published("keycloak") - {0} == {CONTAINER_KEYCLOAK_PORT}


# Szenario 1
def test_pruefung_haelt_die_wartesperre_solange_die_testumgebung_laeuft(testumgebung):
    # Eine Container-Prüfung aus einer anderen Arbeitskopie wartet so, bis diese fertig ist (#184).
    with socket.socket() as other_run:
        with pytest.raises(OSError):
            other_run.bind(("127.0.0.1", CONTAINER_LOCK_PORT))


def test_erika_meldet_sich_in_der_testumgebung_an(testumgebung):
    start_page = _login(ERIKA)

    page = html.unescape(start_page.text)
    assert "Hallo Erika!" in page
    assert BAND in page


# #278, Szenario E5: Die Richtlinie kommt mit, und Formulare dürfen an die Keycloak-Adresse der
# Testumgebung, nicht an die vom eigenen Rechner. Login und Abmelden im Browser prüfen die Rauchtests.
def test_testumgebung_schickt_die_richtlinie_mit_ihrer_keycloak_adresse(testumgebung):
    response = requests.get(f"{TOOL}/anmelden/", timeout=30)

    policy = response.headers["Content-Security-Policy"]
    form_action = next(part.split()[1:] for part in policy.split(";") if part.split()[0] == "form-action")
    assert form_action == ["'self'", f"{KEYCLOAK}/realms/dpv/"]
    assert "script-src 'self'" in policy
    assert "Content-Security-Policy-Report-Only" not in response.headers


# Szenario 4
def test_fehleranzeige_bleibt_aus_obwohl_die_umgebungsdatei_sie_einschaltet(testumgebung):
    # Ein fremder Servername löst einen Fehler aus; die Fehleranzeige für Entwickler zeigte ihn samt Einstellungen.
    response = requests.get(f"{TOOL}/anmelden/", headers={"Host": "fremd.example"}, timeout=30)

    assert response.status_code == 400
    assert "DisallowedHost" not in response.text
    assert "ALLOWED_HOSTS" not in response.text


# Szenario 6
def test_datenbank_hat_keinen_zugang_von_aussen(testumgebung):
    # Kein Port zum Mac: Docker meldet für die Datenbank keine veröffentlichte Adresse.
    listing = compose("ps", "--format", "json", "datenbank", env_file=testumgebung).stdout
    published = [p for line in listing.splitlines() for p in json.loads(line)["Publishers"] or []]
    assert all(p["PublishedPort"] == 0 for p in published), published

    # Ein Container außerhalb ihres Netzes (hier Keycloak) erreicht sie nicht, das Tool schon.
    outside = compose(
        "exec", "-T", "keycloak", "bash", "-c", "exec 3<>/dev/tcp/datenbank/5432", env_file=testumgebung, check=False
    )
    assert outside.returncode != 0
    inside = compose(
        "exec",
        "-T",
        "tool",
        "python",
        "-c",
        "import socket; socket.create_connection(('datenbank', 5432), 3)",
        env_file=testumgebung,
        check=False,
    )
    assert inside.returncode == 0, inside.stderr


# #88: Die Befehle für Verband und Bünde laufen auch in der Testumgebung, so wie im README.
def test_verband_und_buende_per_befehl_in_der_testumgebung(testumgebung):
    def manage(*arguments: str):
        return compose("exec", "-T", "tool", "python", "manage.py", *arguments, env_file=testumgebung, check=False)

    created = [
        manage("federation", "create", "DPV"),
        manage("association", "create", "Pfadfinderbund Boreas"),
        manage("association", "create", "DPBM Mosaik", "--rings"),
    ]
    assert all(result.returncode == 0 for result in created), [r.stdout + r.stderr for r in created]

    twice = manage("association", "create", " pfadfinderbund boreas ")
    assert twice.returncode != 0
    assert "Den Bund „Pfadfinderbund Boreas“ gibt es schon." in twice.stderr

    listing = manage("association", "list")
    assert listing.stdout.splitlines() == [
        "Verband: DPV",
        "Bünde:",
        "  DPBM Mosaik (hat Ringe)",
        "  Pfadfinderbund Boreas (ohne Ringe)",
    ], listing.stderr


# Szenario 10
def test_daten_bleiben_nach_dem_aktualisieren_erhalten(testumgebung):
    # Eigenes Konto anlegen, damit der Test nicht vom Login-Test davor abhängt.
    _login(ERIKA)
    before = _number_of_accounts(testumgebung)
    assert before >= 1

    # So wie beim Aktualisieren nach dem README: anhalten und neu bauen, ohne die Ablage zu löschen.
    compose("down", env_file=testumgebung)
    compose("up", "--detach", "--build", "--wait", env_file=testumgebung)
    wait_for(f"{TOOL}/anmelden/")

    assert _number_of_accounts(testumgebung) == before

    # #199, Szenario S2: Keycloak hat neu gestartet; mit der festen Kennung landet Erika wieder
    # in ihrem Konto, statt dass das Tool ein neues anlegt.
    _login(ERIKA)
    assert _number_of_accounts(testumgebung) == before


# Szenario 5
def test_ohne_pflichtangabe_startet_die_testumgebung_nicht(testumgebung):
    result = compose(
        "run", "--rm", "--no-deps", "--env", "DJANGO_SECRET_KEY=", "tool", env_file=testumgebung, check=False
    )

    assert result.returncode != 0
    assert "Die Umgebungsvariable DJANGO_SECRET_KEY fehlt" in result.stdout + result.stderr
