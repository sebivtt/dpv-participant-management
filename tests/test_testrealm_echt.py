"""Die Importdatei des Test-Realms in einem echten Keycloak 26.7.5 (#62).

Importiert testumgebung/keycloak/dpv-test-realm.json in die Keycloak-Testumgebung aus
dev/docker-compose.yml, genauso wie der Admin des DPV es in der Verwaltung von Keycloak tut
(„Realm erstellen“, Datei hochladen). Nur der Platzhalter der Testdomain wird durch die
Adresse des eigenen Rechners ersetzt. Danach setzt der Test Passwörter, wie Sebastian es
nach dem Import tut, und meldet sich damit im Tool an.

Für Import und Passwörter nutzt der Test den Admin-Zugang der lokalen Keycloak-Testumgebung
(erfundener Wert aus dev/docker-compose.yml). Das Tool selbst bekommt nie einen Admin-Zugang.
Keycloak muss laufen (README.md, „Projekt starten“); sonst schlagen die Tests fehl.
"""

import copy
import os
import secrets
from urllib.parse import urlparse

import pytest
import requests
from allauth.socialaccount.models import SocialAccount
from django.conf import settings as django_settings

from tests.keycloak_fake import RETURN, start_login
from tests.localhost_browser import BrowserOnLocalhost
from tests.test_keycloak_echt import TOOL_HOST, _back_to_tool, _form_action, _open_keycloak
from tests.test_testrealm_datei import PLACEHOLDER, TEST_REALM_FILE

pytestmark = pytest.mark.django_db

REALM = "dpv-test"
TOOL = f"http://{TOOL_HOST}"
# Admin der lokalen Keycloak-Testumgebung (dev/docker-compose.yml); auf GitHub eigener Wert (ci.yml).
ADMIN_PASSWORD = os.environ.get("KEYCLOAK_DEV_ADMIN_PASSWORD", "nur-lokal-nicht-geheim")


def _keycloak_base() -> str:
    """Adresse von Keycloak ohne Realm, z. B. http://localhost:8080."""
    return django_settings.KEYCLOAK_REALM_URL.rsplit("/realms/", 1)[0]


class KeycloakAdmin:
    """Erledigt mit dem Admin-Zugang der Testumgebung, was Admin und Sebastian von Hand tun.

    Meldet sich vor jeder Anfrage neu an: Der Zugang von Keycloak gilt nur 60 Sekunden, und
    der Testlauf mit vielen Logins kann länger dauern, gerade auf GitHub.
    """

    def __init__(self) -> None:
        self.base = _keycloak_base()
        # Der Test löscht den Realm dpv-test. So heißt auch der echte Test-Realm beim DPV;
        # deshalb nur gegen die Keycloak-Testumgebung auf dem eigenen Rechner.
        assert urlparse(self.base).hostname in {"localhost", "127.0.0.1"}, (
            f"Die Tests des Test-Realms laufen nur gegen die lokale Keycloak-Testumgebung, nicht gegen {self.base}"
        )

    def _token(self) -> str:
        try:
            answer = requests.post(
                f"{self.base}/realms/master/protocol/openid-connect/token",
                data={"grant_type": "password", "client_id": "admin-cli", "username": "admin", "password": ADMIN_PASSWORD},
                timeout=10,
            )
        except requests.RequestException as error:
            pytest.fail(
                f"Keycloak unter {self.base} nicht erreichbar ({type(error).__name__}). "
                "Starten: docker compose -f dev/docker-compose.yml up -d --wait"
            )
        assert answer.status_code == 200, (
            "Admin-Login bei der Keycloak-Testumgebung gescheitert. Das Passwort steht in "
            f"dev/docker-compose.yml bzw. in KEYCLOAK_DEV_ADMIN_PASSWORD. Antwort: {answer.text[:500]}"
        )
        return answer.json()["access_token"]

    def request(self, method: str, path: str, **arguments) -> requests.Response:
        """Schickt eine Anfrage an die Admin-Schnittstelle, mit frischem Zugang."""
        headers = {"Authorization": f"Bearer {self._token()}", **arguments.pop("headers", {})}
        return requests.request(method, f"{self.base}/admin/realms{path}", headers=headers, timeout=30, **arguments)

    def delete_realm(self) -> None:
        answer = self.request("DELETE", f"/{REALM}")
        assert answer.status_code in (204, 404), answer.text[:500]

    def import_realm(self, content: str) -> requests.Response:
        """Legt den Realm aus der Datei an, wie „Realm erstellen“ mit hochgeladener Datei."""
        return self.request("POST", "", data=content.encode(), headers={"Content-Type": "application/json"})

    def _get(self, path: str, **params) -> list | dict:
        answer = self.request("GET", path, params=params)
        assert answer.status_code == 200, f"{path}: {answer.status_code} {answer.text[:500]}"
        return answer.json()

    def users(self) -> list[dict]:
        return self._get(f"/{REALM}/users", max=100)

    def user_id(self, username: str) -> str:
        return self._get(f"/{REALM}/users", username=username, exact="true")[0]["id"]

    def credentials(self, username: str) -> list[dict]:
        """Zugangsdaten eines Kontos, wie unter „Credentials“ in der Verwaltung."""
        return self._get(f"/{REALM}/users/{self.user_id(username)}/credentials")

    def set_password(self, username: str, password: str) -> None:
        """Setzt ein dauerhaftes Passwort, wie Sebastian unter „Credentials“ nach dem Import."""
        answer = self.request(
            "PUT",
            f"/{REALM}/users/{self.user_id(username)}/reset-password",
            json={"type": "password", "value": password, "temporary": False},
        )
        assert answer.status_code == 204, answer.text[:500]

    def user_profile(self) -> dict:
        return self._get(f"/{REALM}/users/profile")

    def client_secret(self) -> str:
        """Liest das Client-Secret, das Keycloak beim Import selbst erzeugt hat."""
        clients = self._get(f"/{REALM}/clients", clientId="dpv-anmeldetool")
        assert len(clients) == 1, clients
        return self._get(f"/{REALM}/clients/{clients[0]['id']}/client-secret")["value"]


@pytest.fixture(scope="module")
def admin():
    """Importiert den Test-Realm frisch und entfernt ihn nach den Tests wieder."""
    keycloak = KeycloakAdmin()
    keycloak.delete_realm()
    content = TEST_REALM_FILE.read_text(encoding="utf-8").replace(PLACEHOLDER, TOOL)
    answer = keycloak.import_realm(content)
    assert answer.status_code == 201, f"Import gescheitert: {answer.status_code} {answer.text[:1000]}"
    yield keycloak
    keycloak.delete_realm()


@pytest.fixture
def client(client, settings, admin):
    """Testbrowser des Tools als http://localhost:8000, angebunden an den Test-Realm statt an „dpv“."""
    realm_url = f"{_keycloak_base()}/realms/{REALM}"
    secret = admin.client_secret()
    settings.ALLOWED_HOSTS = ["localhost"]
    settings.KEYCLOAK_REALM_URL = realm_url
    settings.KEYCLOAK_REALM_URL_INTERN = realm_url
    settings.KEYCLOAK_CLIENT_SECRET = secret
    providers = copy.deepcopy(settings.SOCIALACCOUNT_PROVIDERS)
    app = providers["openid_connect"]["APPS"][0]
    app["secret"] = secret
    app["settings"]["server_url"] = realm_url
    settings.SOCIALACCOUNT_PROVIDERS = providers
    client.defaults["HTTP_HOST"] = TOOL_HOST
    return client


@pytest.fixture
def browser():
    """Der Teil des Browsers, der mit Keycloak spricht."""
    return BrowserOnLocalhost()


def _try_sign_in(client, browser, username: str, password: str) -> requests.Response:
    """Füllt das Login-Formular von Keycloak aus und gibt die Antwort von Keycloak zurück."""
    page = _open_keycloak(client, browser)
    assert page.status_code == 200, "Keycloak zeigt kein Login-Formular"
    return browser.post(
        _form_action(page.text), data={"username": username, "password": password}, allow_redirects=False
    )


def _sign_in(client, browser, username: str, password: str):
    return _back_to_tool(client, _try_sign_in(client, browser, username, password))


def test_import_legt_genau_die_vier_erfundenen_konten_und_den_login_client_an(admin):
    users = {user["username"]: user for user in admin.users()}

    assert set(users) == {"erika.testfrau", "max.testmann", "ohne.name", "ohne.nachname"}
    assert all(user["email"] == f"{name}@example.org" for name, user in users.items())
    assert admin.client_secret(), "Keycloak hat beim Import kein Client-Secret erzeugt"


def test_keycloak_laesst_name_und_mail_nur_vom_admin_aendern(admin):
    for attribute in admin.user_profile()["attributes"]:
        assert attribute["permissions"]["edit"] == ["admin"], attribute["name"]


def test_ohne_gesetztes_passwort_kommt_niemand_hinein(client, browser, admin):
    assert admin.credentials("ohne.nachname") == []

    # Auch nicht mit dem Passwort, das das Konto in der lokalen Testumgebung hat.
    answer = _try_sign_in(client, browser, "ohne.nachname", "testpasswort-ohne-nachname")

    # Keycloak zeigt das Formular wieder mit Fehlermeldung, statt zurück ins Tool zu leiten.
    assert answer.status_code == 200
    assert 'name="password"' in answer.text


def test_nach_dem_setzen_des_passworts_meldet_sich_erika_im_tool_an(client, browser, admin):
    password = f"testpasswort-{secrets.token_hex(8)}"
    admin.set_password("erika.testfrau", password)

    response = _sign_in(client, browser, "erika.testfrau", password)

    assert response["Location"] == "/"
    assert "Hallo Erika!" in client.get("/").content.decode()
    # Verknüpft über die feste Keycloak-Kennung, nie über Benutzername oder Mail.
    assert SocialAccount.objects.get().uid == admin.user_id("erika.testfrau")


def test_konto_ohne_namen_sieht_hallo_ohne_namen(client, browser, admin):
    password = f"testpasswort-{secrets.token_hex(8)}"
    admin.set_password("ohne.name", password)

    _sign_in(client, browser, "ohne.name", password)

    assert "Hallo!" in client.get("/").content.decode()


def test_login_seite_bietet_weder_registrieren_noch_passwort_vergessen(client, browser, admin):
    page = _open_keycloak(client, browser)

    assert page.status_code == 200
    assert "login-actions/registration" not in page.text
    assert "login-actions/reset-credentials" not in page.text


def test_direkt_aufgerufene_registrierung_zeigt_kein_formular(client, browser, admin):
    page = _open_keycloak(client, browser, auth_params="prompt=create")

    assert 'name="password-confirm"' not in page.text


def test_nach_vielen_falschen_passwoertern_sperrt_keycloak_vorlaeufig(client, browser, admin):
    # Schnell aufeinander folgende Fehlversuche sperren schon früher; dass es nach 10 auch
    # langsamen Versuchen geschieht, sichert tests/test_testrealm_datei.py über failureFactor.
    password = f"testpasswort-{secrets.token_hex(8)}"
    admin.set_password("max.testmann", password)

    for _attempt in range(10):
        _try_sign_in(client, browser, "max.testmann", "falsch")
    answer = _try_sign_in(client, browser, "max.testmann", password)

    # Auch mit richtigem Passwort geht es vorerst nicht weiter ins Tool.
    assert answer.status_code == 200
    assert 'name="password"' in answer.text


def test_fremde_ruecksprungadresse_lehnt_keycloak_ab(client, browser, admin):
    location = start_login(client)["Location"]
    fremd = location.replace(
        requests.utils.quote(f"{TOOL}{RETURN}", safe=""), requests.utils.quote("https://boese.example/", safe="")
    )
    assert fremd != location, "Rücksprungadresse nicht in der Weiterleitung gefunden"

    answer = browser.get(fremd, allow_redirects=False)

    assert answer.status_code == 400
    assert "boese.example" not in answer.headers.get("Location", "")


def test_abmelden_fuehrt_zurueck_zur_login_seite_des_tools(client, browser, admin):
    password = f"testpasswort-{secrets.token_hex(8)}"
    admin.set_password("ohne.nachname", password)
    _sign_in(client, browser, "ohne.nachname", password)

    response = client.post("/abmelden/")
    keycloak_logout = browser.get(response["Location"], allow_redirects=False)

    assert keycloak_logout.status_code == 302, keycloak_logout.text[:2000]
    assert keycloak_logout.headers["Location"] == f"{TOOL}/anmelden/"
