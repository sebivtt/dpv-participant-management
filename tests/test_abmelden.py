"""Abmelden per Formular an Keycloak, ohne Kennungs-Token in einer Adresse (#280).

Die Kennungen E1 bis G3 verweisen auf den Kommentar „Szenarien (06.11.2026)“ im Issue #280.
Keycloak ist nachgestellt (tests/keycloak_fake.py); dass der echte Keycloak das Formular annimmt,
zeigen tests/test_keycloak_echt.py und die Rauchtests. Alle Daten sind erfunden.
"""

import re
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone

from tests.keycloak_fake import ERIKA, login

pytestmark = pytest.mark.django_db

APP_JS = Path(__file__).resolve().parent.parent / "core/static/core/app.js"

HINT_LOGGED_OUT = "Du bist abgemeldet."
HINT_EXPIRED = "Deine Sitzung ist abgelaufen. Bitte melde dich neu an."


class _Page(HTMLParser):
    """Liest Formulare, versteckte Felder, Knöpfe und Skripte aus der kurzen Seite."""

    def __init__(self, html: str):
        super().__init__()
        self.forms: list[dict] = []
        self.scripts: list[dict] = []
        self._in_script = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append({**attrs, "fields": {}, "buttons": 0})
        elif tag == "input" and self.forms:
            self.forms[-1]["fields"][attrs.get("name")] = attrs.get("value")
        elif tag == "button" and self.forms:
            self.forms[-1]["buttons"] += 1
        elif tag == "script":
            self.scripts.append({**attrs, "body": ""})
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts[-1]["body"] += data


def _keycloak_form(response) -> dict:
    """Das eine Formular der kurzen Seite, das an Keycloak geht."""
    forms = [form for form in _Page(response.content.decode()).forms if "openid-connect" in form.get("action", "")]
    assert len(forms) == 1, response.content.decode()[:2000]
    return forms[0]


def _login_page(client) -> str:
    response = client.get("/anmelden/")
    assert response.status_code == 200
    return response.content.decode()


# E1, E2: Abmelden zeigt die kurze Seite, deren Formular alles Nötige per POST an Keycloak schickt.
def test_abmelden_schickt_token_client_und_ruecksprung_per_formular_an_keycloak(client, keycloak):
    login(client)
    id_token = keycloak.last_id_token

    response = client.post("/abmelden/")

    assert response.status_code == 200, response.status_code
    form = _keycloak_form(response)
    assert form["method"].lower() == "post"
    assert form["action"] == keycloak.endpoints["end_session_endpoint"]
    assert form["fields"] == {
        "id_token_hint": id_token,
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": "http://testserver/anmelden/",
    }
    # E2: Ohne Skript steht ein Knopf da, der dasselbe tut.
    assert form["buttons"] == 1
    # Die Sitzung im Tool ist beendet, bevor die Seite kommt.
    assert not Session.objects.exists()
    assert client.get("/").status_code == 302


# E1: Das Skript schickt das Formular sofort ab, und zwar aus app.js, nicht eingebettet (#278).
def test_kurze_seite_schickt_sich_mit_dem_skript_aus_app_js_selbst_ab(client, keycloak):
    login(client)

    response = client.post("/abmelden/")

    form = _keycloak_form(response)
    assert "data-sofort-absenden" in form
    scripts = _Page(response.content.decode()).scripts
    assert [script["src"] for script in scripts] == ["/static/core/app.js"]
    assert all(not script["body"].strip() for script in scripts)
    assert "onload" not in response.content.decode().lower()
    assert re.search(r"form\[data-sofort-absenden\]", APP_JS.read_text(encoding="utf-8")), "app.js schickt das Formular nicht ab"


# E1: Keine Adresse, die das Tool beim Abmelden aufruft oder weiterleitet, enthält das Token.
def test_keine_adresse_beim_abmelden_enthaelt_das_kennungs_token(client, keycloak):
    login(client)
    id_token = keycloak.last_id_token

    response = client.post("/abmelden/")

    assert not response.has_header("Location")
    for name, value in response.items():
        assert id_token not in value, f"Token im Kopf „{name}“"
    assert "?" not in _keycloak_form(response)["action"]


# G3: Die kurze Seite speichert der Browser nicht, und sie zeigt nichts zur Person außer dem Token.
def test_kurze_seite_wird_nicht_gespeichert_und_zeigt_nichts_zur_person(client, keycloak):
    login(client)
    id_token = keycloak.last_id_token

    response = client.post("/abmelden/")

    assert "no-store" in response["Cache-Control"]
    page = response.content.decode().replace(id_token, "")
    for value in [ERIKA["sub"], "erika", "Testfrau", ERIKA["email"]]:
        assert value.lower() not in page.lower(), f"„{value}“ steht auf der kurzen Seite"


# G1: Nach abgelaufener Sitzung geht Abmelden weiter, ohne Token; Keycloak fragt dann einmal nach.
def test_abmelden_nach_abgelaufener_sitzung_geht_ohne_token_weiter(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    response = client.post("/abmelden/")

    assert response.status_code == 200
    assert _keycloak_form(response)["fields"] == {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": "http://testserver/anmelden/",
    }


# E1 und E3: Zurück auf der Login-Seite steht einmal „Du bist abgemeldet.“, beim nächsten Laden nicht mehr.
def test_login_seite_zeigt_einmal_den_hinweis_abgemeldet(client, keycloak):
    login(client)
    client.post("/abmelden/")

    first = _login_page(client)
    again = _login_page(client)

    assert HINT_LOGGED_OUT in first
    assert HINT_EXPIRED not in first
    assert HINT_LOGGED_OUT not in again


# G1: Der Hinweis kommt auch nach abgelaufener Sitzung, und dann nicht zusätzlich „Sitzung abgelaufen“.
def test_hinweis_abgemeldet_auch_nach_abgelaufener_sitzung(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    client.post("/abmelden/")
    page = _login_page(client)

    assert HINT_LOGGED_OUT in page
    assert HINT_EXPIRED not in page


def test_ohne_abmelden_kein_hinweis_abgemeldet(client, keycloak):
    assert HINT_LOGGED_OUT not in _login_page(client)
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    page = _login_page(client)

    assert HINT_EXPIRED in page
    assert HINT_LOGGED_OUT not in page


# G2: Sendet der Browser das Formular nach „Zurück“ erneut, bleibt die Person abgemeldet.
def test_erneut_gesendetes_abmelden_meldet_nicht_wieder_an(client, keycloak):
    login(client)
    client.post("/abmelden/")

    response = client.post("/abmelden/")

    assert response.status_code == 200
    assert "id_token_hint" not in _keycloak_form(response)["fields"]
    assert "no-store" in response["Cache-Control"]
    assert client.get("/").status_code == 302


# Was bleibt unverändert: Das Cookie „war angemeldet“ wird beim Abmelden gelöscht.
def test_abmelden_loescht_das_cookie_war_angemeldet(client, keycloak):
    login(client)

    response = client.post("/abmelden/")

    cookie = response.cookies["dpv_war_angemeldet"]
    assert cookie.value == ""
    assert cookie["max-age"] == 0
