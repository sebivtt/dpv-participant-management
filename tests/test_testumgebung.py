"""Tests für die Einstellungen der Testumgebung (#58, Teil 1 von #37).

Die Nummern verweisen auf die Szenarien im Kommentar „Szenarien für die Umsetzung“ in #58.
Diese Tests prüfen das Tool selbst, ohne Container. Dass die Testumgebung als Container
tatsächlich startet, prüfen containertests/ (eigener Lauf in pruefen.sh). Alle Daten sind
erfunden.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core import mail
from django.test import Client

from core.mail import LogOnlyEmailBackend
from tests.keycloak_fake import keycloak_parameters, login, start_login

pytestmark = pytest.mark.django_db

BASE_DIR = Path(__file__).resolve().parent.parent

BAND = "Testumgebung: Hier gibt es nur erfundene Daten. Bitte gib keine echten Angaben ein."

# Pflichtangaben mit erfundenen Werten, damit sich die Einstellungen in einem eigenen Prozess laden lassen.
INVENTED = {
    "DJANGO_SECRET_KEY": "nur-fuer-diesen-test",
    "POSTGRES_DB": "beispiel",
    "POSTGRES_USER": "beispiel",
    "POSTGRES_PASSWORD": "beispiel",
}


def _setting(name: str, env: dict[str, str]) -> str:
    """Lädt die Einstellungen in einem eigenen Prozess mit genau dieser Umgebung und gibt einen Wert aus.

    Einstellungen aus Umgebungsvariablen werden beim Start einmal gelesen; ein eigener Prozess
    zeigt, was der Start tatsächlich daraus macht.
    """
    code = f"from django.conf import settings; print(repr(eval({name!r}, {{'settings': settings}})))"
    result = subprocess.run(  # noqa: S603 -- fester Befehl mit dem eigenen Python, keine Eingaben von außen
        [sys.executable, "-c", code],
        cwd=BASE_DIR,
        env={"PATH": os.environ.get("PATH", ""), "DJANGO_SETTINGS_MODULE": "config.settings", **INVENTED, **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def testumgebung(settings):
    """Schaltet die Testumgebung ein, so wie es die Umgebungsdatei der Testumgebung tut."""
    settings.TEST_ENVIRONMENT = True
    return settings


# ---------- Szenarien 1, 2 und 3: Band ----------


def test_band_steht_auf_der_login_seite(testumgebung):
    response = Client().get("/anmelden/")

    assert response.status_code == 200
    assert BAND in response.content.decode()


def test_band_steht_nach_dem_login_auf_der_startseite(testumgebung, client, keycloak):
    login(client)

    page = client.get("/").content.decode()

    assert "Hallo Erika!" in page
    assert BAND in page


def test_band_steht_auch_auf_der_fehlerseite(testumgebung):
    testumgebung.ROOT_URLCONF = "tests.urls"
    client = Client(raise_request_exception=False)

    response = client.get("/test/1/")

    assert response.status_code == 500
    assert BAND in response.content.decode()


# Jede Anfrage kommt von einer angemeldeten Person (client nach login).
def _not_found(client):
    return client.get("/gibt-es-nicht/")


def _entry_not_found(client):
    # Die Adresse gibt es, den Eintrag nicht (Http404 in der Seite selbst).
    return client.get("/test/1/nicht-da/")


def _forbidden(client):
    return client.get("/test/1/verboten/")


def _form_expired(client):
    # Ohne gültigen Formularschutz (CSRF), etwa weil das Formular zu lange offen war.
    client.handler.enforce_csrf_checks = True
    return client.post("/abmelden/")


def _bad_request(client):
    # Unbekannter Servername: Das Tool lehnt die Anfrage ab.
    return client.get("/anmelden/", HTTP_HOST="fremd.example")


# Djangos eingebaute Fehlerseiten; die eigenen zeigen stattdessen einen kurzen Hinweis auf Deutsch.
DJANGO_ERROR_TEXTS = ("Not Found", "Forbidden", "Bad Request", "CSRF verification failed")
ERROR_PAGES = [
    pytest.param(_not_found, 404, id="nicht-gefunden"),
    pytest.param(_entry_not_found, 404, id="eintrag-nicht-gefunden"),
    pytest.param(_forbidden, 403, id="kein-zugriff"),
    pytest.param(_form_expired, 403, id="formular-abgelaufen"),
    pytest.param(_bad_request, 400, id="ungueltige-anfrage"),
]


# Entscheidung von Sebastian am 22.10.2026 in #58: das Band auf jeder Fehlerseite.
@pytest.mark.parametrize(("request_page", "status"), ERROR_PAGES)
def test_band_steht_auf_jeder_fehlerseite(testumgebung, client, keycloak, request_page, status):
    testumgebung.ROOT_URLCONF = "tests.urls"
    login(client)

    response = request_page(client)

    assert response.status_code == status
    page = response.content.decode()
    assert BAND in page
    assert not any(text in page for text in DJANGO_ERROR_TEXTS), page


def test_fehlerseite_zeigt_die_adresse_nicht(testumgebung):
    # Schon die Adresse kann Personendaten enthalten (Entscheidung zu #6).
    response = Client().get("/erika-mustermann/")

    assert response.status_code == 404
    assert "erika" not in response.content.decode().lower()


@pytest.mark.parametrize(("request_page", "status"), ERROR_PAGES)
def test_ohne_schalter_eigene_fehlerseite_ohne_band(settings, client, keycloak, request_page, status):
    settings.TEST_ENVIRONMENT = False
    settings.ROOT_URLCONF = "tests.urls"
    login(client)

    response = request_page(client)

    assert response.status_code == status
    page = response.content.decode()
    assert BAND not in page
    assert "DPV Anmeldetool" in page


def test_band_hat_ein_symbol_und_ist_fuer_bildschirmleser_ein_hinweis(testumgebung):
    page = Client().get("/anmelden/").content.decode()

    start = page.index('class="a-testband"')
    band = page[page.rindex("<", 0, start) : page.index("</div>", start)]
    assert 'role="note"' in band
    assert '<use href="#i-' in band


def test_ohne_schalter_kein_band(settings, client, keycloak):
    settings.TEST_ENVIRONMENT = False
    login(client)

    assert BAND not in Client().get("/anmelden/").content.decode()
    assert BAND not in client.get("/").content.decode()


def test_katalog_zeigt_das_band_als_baustein_auch_ohne_schalter(settings, client, keycloak):
    # Entschiedene Bausteine stehen im Bausteinkatalog (#176); dort prüft auch der Rauchtest
    # die Barrierefreiheit, z. B. den Kontrast des Bands.
    settings.TEST_ENVIRONMENT = False
    login(client)

    assert BAND in client.get("/bausteine/").content.decode()


def test_testumgebung_ist_nur_mit_ausdruecklichem_schalter_an():
    assert _setting("settings.TEST_ENVIRONMENT", {}) == "False"
    assert _setting("settings.TEST_ENVIRONMENT", {"TEST_ENVIRONMENT": "ja"}) == "False"
    assert _setting("settings.TEST_ENVIRONMENT", {"TEST_ENVIRONMENT": "1"}) == "True"


# ---------- Szenario 4: Fehleranzeige für Entwickler bleibt aus ----------


def test_in_der_testumgebung_bleibt_die_fehleranzeige_aus_auch_wenn_eingeschaltet():
    assert _setting("settings.DEBUG", {"TEST_ENVIRONMENT": "1", "DJANGO_DEBUG": "1"}) == "False"


def test_auf_dem_eigenen_rechner_laesst_sich_die_fehleranzeige_weiter_einschalten():
    # Gegenprobe: Die Sperre gilt nur in der Testumgebung, nicht für die Entwicklung (README.md).
    assert _setting("settings.DEBUG", {"DJANGO_DEBUG": "1"}) == "True"


# ---------- Szenario 7: Mails nur ins Log ----------


def test_eingestellter_mailweg_schreibt_nur_ins_log():
    backend = "settings.MAILERS['default']['BACKEND']"

    assert _setting(backend, {"TEST_ENVIRONMENT": "1"}) == "'core.mail.LogOnlyEmailBackend'"
    # Nur ein Mailweg: Es gibt keinen zweiten, über den eine Mail doch an einen Mailserver ginge.
    assert _setting("list(settings.MAILERS)", {"TEST_ENVIRONMENT": "1"}) == "['default']"


def test_mail_geht_nur_als_hinweis_ins_log_ohne_empfaenger_und_inhalt(log_output):
    message = mail.EmailMessage(
        subject="Betreff mit Allergie Erdnuss",
        body="Inhalt mit Allergie Erdnuss",
        from_email="absender@example.org",
        to=["erika.testfrau@example.org"],
        cc=["max.testmann@example.org"],
    )

    sent = LogOnlyEmailBackend().send_messages([message])

    log = log_output()
    assert "Mail nicht verschickt (nur Log)" in log
    for detail in ("Erdnuss", "erika.testfrau", "max.testmann", "absender@example.org", "Betreff"):
        assert detail not in log
    # Nicht verschickt heißt auch: Für das Tool gilt die Mail nicht als zugestellt.
    assert sent == 0


def test_mailweg_baut_keine_verbindung_zu_einem_mailserver_auf(monkeypatch, log_output):
    def no_network(*args, **kwargs):
        raise AssertionError("Verbindung zu einem Mailserver versucht")

    monkeypatch.setattr("smtplib.SMTP.connect", no_network)
    message = mail.EmailMessage("Betreff", "Inhalt", "absender@example.org", ["erika.testfrau@example.org"])

    LogOnlyEmailBackend().send_messages([message])

    assert "Mail nicht verschickt (nur Log)" in log_output()


# ---------- Szenario 8: Suchmaschinen ----------


def test_testumgebung_bittet_suchmaschinen_keine_seite_aufzunehmen(testumgebung, client, keycloak):
    assert Client().get("/anmelden/")["X-Robots-Tag"] == "noindex, nofollow"
    assert Client().get("/static/core/app.css")["X-Robots-Tag"] == "noindex, nofollow"
    login(client)
    assert client.get("/")["X-Robots-Tag"] == "noindex, nofollow"


def test_hinweis_an_suchmaschinen_auch_auf_der_fehlerseite(testumgebung):
    testumgebung.ROOT_URLCONF = "tests.urls"

    response = Client(raise_request_exception=False).get("/test/1/")

    assert response.status_code == 500
    assert response["X-Robots-Tag"] == "noindex, nofollow"


def test_ohne_testumgebung_kein_hinweis_an_suchmaschinen(settings):
    settings.TEST_ENVIRONMENT = False

    assert "X-Robots-Tag" not in Client().get("/anmelden/")


# ---------- Szenario 9: HTTPS ----------


HTTPS_PROXY = {"HTTP_X_FORWARDED_PROTO": "https"}


@pytest.fixture
def hinter_https(settings):
    """So wie das Tool hinter einem Programm läuft, das HTTPS annimmt und weiterreicht."""
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    return settings


def test_hinter_https_schalter_setzt_die_einstellungen():
    env = {"DJANGO_BEHIND_HTTPS_PROXY": "1"}
    assert _setting("settings.SECURE_PROXY_SSL_HEADER", env) == "('HTTP_X_FORWARDED_PROTO', 'https')"
    assert _setting("settings.SESSION_COOKIE_SECURE", env) == "True"
    assert _setting("settings.CSRF_COOKIE_SECURE", env) == "True"


def test_ohne_https_schalter_traut_das_tool_keinem_weitergereichten_hinweis():
    # Ohne Programm davor könnte jede Anfrage selbst „das war HTTPS“ behaupten.
    assert _setting("settings.SECURE_PROXY_SSL_HEADER", {}) == "None"
    assert _setting("settings.SESSION_COOKIE_SECURE", {}) == "False"


def test_hinter_https_gehen_alle_cookies_des_logins_nur_verschluesselt(hinter_https, keycloak):
    client = Client(**HTTPS_PROXY)

    login(client)

    cookies = client.cookies
    assert cookies["sessionid"]["secure"] is True
    assert cookies["dpv_war_angemeldet"]["secure"] is True
    client.get("/anmelden/")
    assert client.cookies["csrftoken"]["secure"] is True


def test_hinter_https_kehrt_keycloak_an_eine_https_adresse_zurueck(hinter_https, keycloak):
    client = Client(**HTTPS_PROXY)

    parameters = keycloak_parameters(start_login(client))

    assert parameters["redirect_uri"].startswith("https://")


def test_ohne_https_klappt_der_login_wie_bisher(client, keycloak):
    # Mit den Einstellungen ohne Schalter, wie auf dem Mac: Cookies auch ohne HTTPS.
    login(client)

    assert client.cookies["sessionid"]["secure"] == ""
    assert "Hallo Erika!" in client.get("/").content.decode()


# ---------- Keycloak aus dem Container ----------


def test_interne_keycloak_adresse_nur_fuer_anfragen_des_tools():
    # Im Container erreicht das Tool Keycloak unter einer anderen Adresse als der Browser.
    env = {
        "KEYCLOAK_REALM_URL": "http://localhost:8081/realms/dpv",
        "KEYCLOAK_REALM_URL_INTERN": "http://keycloak:8080/realms/dpv",
    }
    server_url = "settings.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['settings']['server_url']"

    assert _setting(server_url, env) == "'http://keycloak:8080/realms/dpv'"
    assert _setting("settings.KEYCLOAK_REALM_URL", env) == "'http://localhost:8081/realms/dpv'"


def test_ohne_interne_adresse_gilt_die_normale_fuer_beides():
    env = {"KEYCLOAK_REALM_URL": "http://localhost:8080/realms/dpv/"}
    server_url = "settings.SOCIALACCOUNT_PROVIDERS['openid_connect']['APPS'][0]['settings']['server_url']"

    assert _setting(server_url, env) == "'http://localhost:8080/realms/dpv'"
