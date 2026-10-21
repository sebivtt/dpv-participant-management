"""Die Testumgebung startet im Container und tut, was #58 verlangt.

Die Nummern verweisen auf die Szenarien im Kommentar „Szenarien für die Umsetzung“ in #58.
Angemeldet wird wirklich bei der Keycloak-Testumgebung, mit einem erfundenen Konto aus
dev/keycloak/dpv-realm.json. Die Tests laufen in der Reihenfolge der Datei: Szenario 10
prüft, dass das Konto aus Szenario 1 nach dem Aktualisieren noch da ist.
"""

import html
import re

import requests

from containertests.conftest import TOOL, compose, wait_for

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


def _login(session: requests.Session, user: tuple[str, str]) -> requests.Response:
    """Meldet sich an wie eine Person im Browser: Login-Seite, Keycloak, zurück ins Tool."""
    login_page = session.get(f"{TOOL}/anmelden/", timeout=30)
    action, fields = _form(login_page.text, "Mit DPV-Konto anmelden")
    keycloak_page = session.post(f"{TOOL}{action}", data=fields, timeout=30)
    assert "localhost:8081" in keycloak_page.url, keycloak_page.url
    action, fields = _form(keycloak_page.text, 'name="username"')
    return session.post(action, data={**fields, "username": user[0], "password": user[1]}, timeout=60)


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


# Szenario 1
def test_erika_meldet_sich_in_der_testumgebung_an(testumgebung):
    session = requests.Session()

    start_page = _login(session, ERIKA)

    assert start_page.url == f"{TOOL}/"
    page = html.unescape(start_page.text)
    assert "Hallo Erika!" in page
    assert BAND in page


# Szenario 4
def test_fehleranzeige_bleibt_aus_obwohl_die_umgebungsdatei_sie_einschaltet(testumgebung):
    # Ein fremder Servername löst einen Fehler aus; die Fehleranzeige für Entwickler zeigte ihn samt Einstellungen.
    response = requests.get(f"{TOOL}/anmelden/", headers={"Host": "fremd.example"}, timeout=30)

    assert response.status_code == 400
    assert "DisallowedHost" not in response.text
    assert "ALLOWED_HOSTS" not in response.text


# Szenario 6
def test_datenbank_hat_keinen_zugang_von_aussen(testumgebung):
    result = compose("port", "datenbank", "5432", env_file=testumgebung, check=False)

    assert result.returncode != 0 or not result.stdout.strip()


# Szenario 10
def test_daten_bleiben_nach_dem_aktualisieren_erhalten(testumgebung):
    before = _number_of_accounts(testumgebung)
    assert before >= 1

    # So wie beim Aktualisieren nach dem README: anhalten und neu bauen, ohne die Ablage zu löschen.
    compose("down", env_file=testumgebung)
    compose("up", "--detach", "--build", "--wait", env_file=testumgebung)
    wait_for(f"{TOOL}/anmelden/")

    assert _number_of_accounts(testumgebung) == before


# Szenario 5
def test_ohne_pflichtangabe_startet_die_testumgebung_nicht(testumgebung):
    result = compose(
        "run", "--rm", "--no-deps", "--env", "DJANGO_SECRET_KEY=", "tool", env_file=testumgebung, check=False
    )

    assert result.returncode != 0
    assert "Die Umgebungsvariable DJANGO_SECRET_KEY fehlt" in result.stdout + result.stderr
