"""Nachgestellter Keycloak für die Login-Tests (#5).

Das Tool fragt Keycloak über das Netz: Einstellungen des Realms, Austausch des Codes gegen
Schlüssel und Angaben zur Person. Diese Anfragen beantwortet hier ein erfundener Keycloak,
damit die Regeln des Tools ohne laufenden Keycloak und in jeder Kombination prüfbar sind.
Dass das Tool auch mit dem echten Keycloak zusammenspielt, prüft tests/test_keycloak_echt.py.
"""

import json
import time
from urllib.parse import parse_qs, urlencode, urlparse

import jwt
import pytest
import requests
from django.conf import settings

START = "/anmelden/keycloak/start/"
RETURN = "/anmelden/keycloak/zurueck/"

ERIKA = {
    "sub": "11111111-aaaa-4bbb-8ccc-000000000001",
    "preferred_username": "erika.testfrau",
    "email": "erika.testfrau@example.org",
    # Keycloak meldet die Mail als bestätigt; so würde allauth sie zum Verknüpfen nutzen, wenn man es ließe.
    "email_verified": True,
    "given_name": "Erika",
    "family_name": "Testfrau",
}
MAX = {
    "sub": "22222222-aaaa-4bbb-8ccc-000000000002",
    "preferred_username": "max.testmann",
    "email": "max.testmann@example.org",
    "email_verified": True,
    "given_name": "Max",
    "family_name": "Testmann",
}


class FakeKeycloak:
    """Beantwortet die Anfragen des Tools an Keycloak mit erfundenen Daten.

    `person` sind die Angaben, die Keycloak zur angemeldeten Person liefert. Ist
    `unreachable` gesetzt, scheitert jede Verbindung wie bei einem ausgefallenen Server.
    """

    def __init__(self) -> None:
        self.person = dict(ERIKA)
        self.unreachable = False
        self.realm = settings.KEYCLOAK_REALM_URL
        self.endpoints = {
            "issuer": self.realm,
            "authorization_endpoint": f"{self.realm}/protocol/openid-connect/auth",
            "token_endpoint": f"{self.realm}/protocol/openid-connect/token",
            "userinfo_endpoint": f"{self.realm}/protocol/openid-connect/userinfo",
            "end_session_endpoint": f"{self.realm}/protocol/openid-connect/logout",
            "jwks_uri": f"{self.realm}/protocol/openid-connect/certs",
            "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        }
        self.last_id_token = ""

    def id_token(self) -> str:
        """Erzeugt ein Kennungs-Token, wie Keycloak es beim Austausch des Codes mitschickt."""
        now = int(time.time())
        claims = {
            "iss": self.realm,
            "aud": settings.KEYCLOAK_CLIENT_ID,
            "sub": self.person["sub"],
            "iat": now,
            "exp": now + 300,
        }
        # Die Signatur prüft das Tool hier nicht, weil es das Token direkt von Keycloak
        # bekommt (OpenID Connect Core 1.0, Abschnitt 3.1.3.7); ein erfundener Schlüssel genügt.
        self.last_id_token = jwt.encode(claims, "nur-fuer-tests-nicht-geheim-und-lang-genug", algorithm="HS256")
        return self.last_id_token

    def answer(self, method: str, url: str) -> requests.Response:
        """Gibt die Antwort zurück, die Keycloak auf diese Anfrage schicken würde."""
        if self.unreachable:
            raise requests.ConnectionError("Keycloak nicht erreichbar (nachgestellt)")
        path = url.split("?")[0]
        if path.endswith("/.well-known/openid-configuration"):
            return _json_response(url, self.endpoints)
        if path == self.endpoints["token_endpoint"] and method.upper() == "POST":
            token = {"access_token": "zugang-nur-test", "token_type": "Bearer", "expires_in": 300}
            return _json_response(url, {**token, "id_token": self.id_token()})
        if path == self.endpoints["userinfo_endpoint"]:
            return _json_response(url, self.person)
        return _json_response(url, {"error": "unbekannte Adresse im nachgestellten Keycloak"}, status=404)


def _json_response(url: str, data: dict, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(data).encode()
    return response


@pytest.fixture
def keycloak(monkeypatch) -> FakeKeycloak:
    """Leitet alle Anfragen des Tools an Keycloak auf den nachgestellten Keycloak um."""
    fake = FakeKeycloak()

    def request(session, method, url, *args, **kwargs):
        return fake.answer(method, url)

    monkeypatch.setattr(requests.Session, "request", request)
    return fake


def start_login(client, next_url: str | None = None, auth_params: str | None = None):
    """Klickt auf der Login-Seite auf „Anmelden“; die Antwort leitet zu Keycloak weiter."""
    address = START if auth_params is None else f"{START}?{urlencode({'auth_params': auth_params})}"
    data = {} if next_url is None else {"next": next_url}
    return client.post(address, data)


def keycloak_parameters(response) -> dict[str, str]:
    """Liest die Angaben, mit denen das Tool zu Keycloak weiterleitet (z. B. state, prompt)."""
    assert response.status_code == 302, response.status_code
    return {key: values[0] for key, values in parse_qs(urlparse(response["Location"]).query).items()}


def login(client, next_url: str | None = None):
    """Durchläuft den ganzen Login: Start, Anmeldung bei Keycloak, Rückkehr ins Tool."""
    state = keycloak_parameters(start_login(client, next_url))["state"]
    return client.get(RETURN, {"state": state, "code": "code-nur-test"})
