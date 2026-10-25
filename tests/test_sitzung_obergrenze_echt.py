"""Obergrenze der Sitzung mit der echten Keycloak-Testumgebung aus dev/docker-compose.yml (#8).

Nach 12 Stunden endet die Sitzung im Tool. Was danach geschieht, entscheidet Keycloak:
Ist die Person dort noch angemeldet und ihr Konto gültig, geht der Login ohne Passwort
weiter. Ist ihr Konto gesperrt oder gelöscht, kommt sie nicht mehr ins Tool.

Für jedes Konto, das gesperrt oder gelöscht wird, registriert der Test ein neues, erfundenes
Konto. Sperren und Löschen erledigt er mit dem Admin-Zugang der lokalen Keycloak-Testumgebung,
wie der Admin des DPV es in der Verwaltung von Keycloak tut. Das Tool selbst bekommt nie einen
Admin-Zugang. Keycloak muss laufen (README.md, „Projekt starten“); sonst schlagen die Tests fehl.
"""

import secrets
from datetime import timedelta
from urllib.parse import urljoin, urlparse

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.session import LOGIN_TIME_SESSION_KEY
from tests.test_keycloak_echt import (
    TOOL_HOST,
    _back_to_tool,
    _form_action,
    _open_keycloak,
    _sign_in,
    browser,  # noqa: F401 (Fixture)
    client,  # noqa: F401 (Fixture)
)
from tests.test_testrealm_echt import KeycloakAdmin

pytestmark = pytest.mark.django_db

User = get_user_model()

REALM = "dpv"
HINT_EXPIRED = "Deine Sitzung ist abgelaufen. Bitte melde dich neu an."
PASSWORD = "testpasswort-neu"  # noqa: S105 (erfundenes Passwort der Testumgebung)


@pytest.fixture
def admin():
    return KeycloakAdmin()


@pytest.fixture
def new_account(client, browser, admin):  # noqa: F811 (Fixtures)
    """Registriert ein neues, erfundenes Konto bei Keycloak, meldet es im Tool an und entfernt es danach."""
    name = f"sperre.{secrets.token_hex(4)}"
    page = _open_keycloak(client, browser, auth_params="prompt=create")
    assert page.status_code == 200
    answer = browser.post(
        urljoin(page.url, _form_action(page.text)),
        data={
            "username": name,
            "email": f"{name}@example.org",
            "firstName": "Gesa",
            "lastName": "Gesperrt",
            "password": PASSWORD,
            "password-confirm": PASSWORD,
        },
        allow_redirects=False,
    )
    assert _back_to_tool(client, answer)["Location"] == "/"
    found = admin.request("GET", f"/{REALM}/users", params={"username": name, "exact": "true"}).json()
    assert len(found) == 1, found
    yield {"name": name, "id": found[0]["id"]}
    admin.request("DELETE", f"/{REALM}/users/{found[0]['id']}")


def _twelve_hours_pass(tool) -> None:
    """Tut so, als läge der Login im Tool 12 Stunden und eine Sekunde zurück."""
    session = tool.session
    session[LOGIN_TIME_SESSION_KEY] = (timezone.now() - timedelta(hours=12, seconds=1)).timestamp()
    session.save()


def _next_click_leads_to_login_with_hint(tool) -> None:
    response = tool.get("/", follow=True)
    assert response.redirect_chain and response.redirect_chain[-1][0].startswith("/anmelden/")
    assert HINT_EXPIRED in response.content.decode()


def _logged_in(tool) -> bool:
    return tool.get("/").status_code == 200


def _login_refused(tool, keycloak_browser, name: str) -> None:
    """Anmelden im Tool: Keycloak verlangt das Passwort, lehnt es ab und schickt nicht zurück ins Tool."""
    page = _open_keycloak(tool, keycloak_browser)
    assert page.status_code == 200, "Keycloak lässt ohne Passwort durch"
    assert 'name="password"' in page.text
    answer = keycloak_browser.post(
        _form_action(page.text), data={"username": name, "password": PASSWORD}, allow_redirects=False
    )
    location = answer.headers.get("Location", "")
    assert urlparse(location).netloc != TOOL_HOST, f"Keycloak schickt zurück ins Tool: {location}"
    assert not _logged_in(tool)
    # Wer danach das Tool aufruft, landet auf der Login-Seite, nicht auf einer Fehlerseite.
    response = tool.get("/", follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1][0].startswith("/anmelden/")


def test_nach_zwoelf_stunden_geht_der_login_ohne_passwort_weiter(client, browser):  # noqa: F811 (Fixtures)
    _sign_in(client, browser, "erika.testfrau", "testpasswort-erika")
    _twelve_hours_pass(client)

    _next_click_leads_to_login_with_hint(client)

    # Erika ist bei Keycloak noch angemeldet: Keycloak schickt sofort zurück, ohne Formular.
    answer = _open_keycloak(client, browser)
    assert answer.status_code == 302, "Keycloak verlangt das Passwort"
    assert _back_to_tool(client, answer)["Location"] == "/"
    assert "Hallo Erika!" in client.get("/").content.decode()


def test_gesperrtes_konto_kommt_nach_zwoelf_stunden_nicht_mehr_ins_tool(client, browser, admin, new_account):  # noqa: F811 (Fixtures)
    answer = admin.request("PUT", f"/{REALM}/users/{new_account['id']}", json={"enabled": False})
    assert answer.status_code == 204, answer.text[:500]
    # Bis zur Obergrenze arbeitet das Konto weiter; das Tool fragt nicht bei Keycloak nach.
    assert _logged_in(client)

    _twelve_hours_pass(client)
    _next_click_leads_to_login_with_hint(client)

    _login_refused(client, browser, new_account["name"])
    gesa = User.objects.get(email=f"{new_account['name']}@example.org")
    assert gesa.is_active, "Das Konto im Tool bleibt unverändert"


def test_geloeschtes_konto_kommt_nach_zwoelf_stunden_nicht_mehr_ins_tool(client, browser, admin, new_account):  # noqa: F811 (Fixtures)
    answer = admin.request("DELETE", f"/{REALM}/users/{new_account['id']}")
    assert answer.status_code == 204, answer.text[:500]
    assert _logged_in(client)

    _twelve_hours_pass(client)
    _next_click_leads_to_login_with_hint(client)

    _login_refused(client, browser, new_account["name"])
    gesa = User.objects.get(email=f"{new_account['name']}@example.org")
    assert gesa.is_active, "Das Konto im Tool bleibt unverändert"
