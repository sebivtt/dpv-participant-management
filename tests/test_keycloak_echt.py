"""Login gegen die echte Keycloak-Testumgebung aus dev/docker-compose.yml (#5).

Belegt, dass das Tool mit Keycloak tatsächlich zusammenspielt (sonst Rückfall laut
docs/entscheidungen.md, 20.10.2026). Ein Programm spielt dafür den Browser: Es füllt die
Formulare von Keycloak aus wie eine Person. Die erfundenen Konten stehen in
dev/keycloak/dpv-realm.json. Keycloak muss laufen (README.md, „Projekt starten“); läuft er
nicht, schlagen diese Tests fehl, statt still übersprungen zu werden.
"""

import html
import re
import secrets
from urllib.parse import urljoin, urlparse

import pytest
import requests
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.contrib.auth import get_user_model

from tests.keycloak_fake import RETURN, start_login

pytestmark = pytest.mark.django_db

User = get_user_model()

# Keycloak lässt nur Rückkehradressen des eigenen Rechners zu (dev/keycloak/dpv-realm.json).
TOOL_HOST = "localhost:8000"


@pytest.fixture
def client(client, settings):
    """Testbrowser des Tools, der sich als http://localhost:8000 ausgibt."""
    settings.ALLOWED_HOSTS = ["localhost"]
    client.defaults["HTTP_HOST"] = TOOL_HOST
    return client


class BrowserOnLocalhost(requests.Session):
    """Schickt Keycloak seine Cookies zurück, wie ein Browser es bei localhost tut.

    Keycloak markiert seine Cookies als „nur über HTTPS“. Browser schicken sie bei localhost
    trotzdem mit, requests nicht; ohne das meldet Keycloak „cookie_not_found“.
    """

    def prepare_request(self, request):
        for cookie in self.cookies:
            cookie.secure = False
        return super().prepare_request(request)


@pytest.fixture
def browser():
    """Der Teil des Browsers, der mit Keycloak spricht; merkt sich die Anmeldung bei Keycloak."""
    session = BrowserOnLocalhost()
    try:
        session.get(f"{settings.KEYCLOAK_REALM_URL}/.well-known/openid-configuration", timeout=5).raise_for_status()
    except requests.RequestException as error:
        pytest.fail(
            f"Keycloak unter {settings.KEYCLOAK_REALM_URL} nicht erreichbar ({type(error).__name__}). "
            "Starten: docker compose -f dev/docker-compose.yml up -d --wait"
        )
    return session


def _form_action(page: str) -> str:
    match = re.search(r'<form[^>]*action="([^"]+)"', page)
    assert match, f"Kein Formular auf der Seite von Keycloak:\n{page[:2000]}"
    return html.unescape(match.group(1))


def _back_to_tool(client, keycloak_response):
    """Folgt der Weiterleitung von Keycloak zurück ins Tool."""
    assert keycloak_response.status_code == 302, keycloak_response.text[:2000]
    target = urlparse(keycloak_response.headers["Location"])
    assert target.netloc == TOOL_HOST and target.path == RETURN, keycloak_response.headers["Location"]
    return client.get(f"{target.path}?{target.query}")


def _open_keycloak(client, browser, auth_params: str | None = None):
    response = start_login(client, auth_params=auth_params)
    assert response.status_code == 302
    return browser.get(response["Location"], allow_redirects=False)


def _sign_in(client, browser, username: str, password: str):
    page = _open_keycloak(client, browser)
    assert page.status_code == 200, "Keycloak zeigt kein Login-Formular"
    answer = browser.post(
        _form_action(page.text), data={"username": username, "password": password}, allow_redirects=False
    )
    return _back_to_tool(client, answer)


def test_erika_meldet_sich_wirklich_ueber_keycloak_an(client, browser):
    response = _sign_in(client, browser, "erika.testfrau", "testpasswort-erika")

    assert response["Location"] == "/"
    page = client.get("/").content.decode()
    assert "Hallo Erika!" in page
    assert "erika.testfrau@example.org" in page
    assert SocialAccount.objects.get().uid != "erika.testfrau"


def test_konto_ohne_mail_wird_wirklich_abgelehnt(client, browser):
    response = _sign_in(client, browser, "ohne.mail", "testpasswort-ohne-mail")

    assert response["Location"].startswith("/anmelden/")
    assert not User.objects.exists()


def test_nach_dem_abmelden_fragt_keycloak_wieder_nach_dem_passwort(client, browser):
    _sign_in(client, browser, "erika.testfrau", "testpasswort-erika")
    # Gegenprobe: Ohne Abmelden bei Keycloak käme Erika jetzt ohne Passwort durch, denn
    # Keycloak leitet sofort zurück, statt das Formular zu zeigen.
    assert _open_keycloak(client, browser).status_code == 302

    response = client.post("/abmelden/")
    keycloak_logout = browser.get(response["Location"], allow_redirects=False)

    # Keycloak meldet ohne Rückfrage ab und schickt zurück zur Login-Seite des Tools.
    assert keycloak_logout.status_code == 302, keycloak_logout.text[:2000]
    assert keycloak_logout.headers["Location"] == f"http://{TOOL_HOST}/anmelden/"
    page = _open_keycloak(client, browser)
    assert page.status_code == 200
    assert 'name="password"' in page.text


def test_registrierung_bei_keycloak_und_danach_sofort_angemeldet(client, browser):
    name = f"neu.{secrets.token_hex(4)}"
    page = _open_keycloak(client, browser, auth_params="prompt=create")
    assert page.status_code == 200
    assert 'name="password-confirm"' in page.text, "Keycloak zeigt keine Registrierung"

    answer = browser.post(
        urljoin(page.url, _form_action(page.text)),
        data={
            "username": name,
            "email": f"{name}@example.org",
            "firstName": "Nora",
            "lastName": "Neu",
            "password": "testpasswort-neu",
            "password-confirm": "testpasswort-neu",
        },
        allow_redirects=False,
    )
    response = _back_to_tool(client, answer)

    assert response["Location"] == "/"
    assert "Hallo Nora!" in client.get("/").content.decode()
