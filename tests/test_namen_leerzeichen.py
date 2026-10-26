"""Tests: Leerzeichen am Rand von Name, Mail und Benutzername aus Keycloak (#77).

Die Nummern verweisen auf den Kommentar „Szenarien (26.10.2026)“ in #77. Keycloak ist
nachgestellt (tests/keycloak_fake.py); alle Daten sind erfunden.
"""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from tests.keycloak_fake import ERIKA, login
from tests.test_gestaltung import _all, _classes, _one, _tree, _visible_text
from tests.test_meldungen import HINT_NAME, HINT_NO_MAIL, assert_is, notice_with
from tests.test_mein_profil import NOT_GIVEN, details, raw_text, symbols

pytestmark = pytest.mark.django_db

User = get_user_model()

NBSP = " "
ZERO_WIDTH_SPACE = "​"


def _erika() -> User:
    return User.objects.get(socialaccount__uid=ERIKA["sub"])


def _start(client):
    return _tree(client.get("/"))


def _circle(root):
    """Der Profilkreis in der Seitenleiste."""
    sidebar = _one(_all(root, lambda e: e.name == "aside"))
    profile = _one(_all(sidebar, lambda e: e.name == "a" and "a-profil" in _classes(e)))
    return _one(_all(profile, lambda e: "a-avatar" in _classes(e)))


def _greeting(root) -> str:
    return _visible_text(_one(_all(root, lambda e: e.name == "h1"))).strip()


def _assert_name_missing(client) -> None:
    """Startseite mit „Hallo!“, Warnmeldung zum Ergänzen und Personensymbol im Profilkreis."""
    root = _start(client)
    assert _greeting(root) == "Hallo!"
    assert_is(notice_with(root, HINT_NAME), "warning")
    assert raw_text(_circle(root)) == ""
    assert symbols(_circle(root)) == ["person"]


# Szenario 1
def test_leerzeichen_am_rand_des_vornamens_werden_entfernt(client, keycloak):
    keycloak.person["given_name"] = "  Erika "

    login(client)

    assert _erika().first_name == "Erika"
    root = _start(client)
    assert _greeting(root) == "Hallo Erika!"
    assert raw_text(_circle(root)) == "E"


# Szenario 2
def test_leerzeichen_am_rand_der_mail_werden_entfernt(client, keycloak):
    keycloak.person["email"] = " erika.testfrau@example.org "

    login(client)

    erika = _erika()
    assert erika.email == "erika.testfrau@example.org"
    assert list(EmailAddress.objects.filter(user=erika).values_list("email", flat=True)) == [
        "erika.testfrau@example.org"
    ]
    assert details(_tree(client.get("/profil/")))["E-Mail-Adresse"] == "erika.testfrau@example.org"


def test_leerzeichen_am_rand_von_nachname_und_benutzername_werden_entfernt(client, keycloak):
    keycloak.person["family_name"] = " Testfrau  "
    keycloak.person["preferred_username"] = " erika.testfrau "

    login(client)

    assert (_erika().last_name, _erika().username) == ("Testfrau", "erika.testfrau")


def test_benutzername_mit_leerzeichen_am_rand_auch_beim_naechsten_login(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person["preferred_username"] = " erika.neu "

    login(client)

    assert _erika().username == "erika.neu"


# Szenario 3
@pytest.mark.parametrize("space", [NBSP, ZERO_WIDTH_SPACE, "⁠", "﻿", "\t"])
def test_geschuetzte_und_unsichtbare_leerzeichen_am_rand_werden_entfernt(client, keycloak, space):
    keycloak.person["given_name"] = f"{space}Erika{space}"

    login(client)

    assert _erika().first_name == "Erika"
    assert _greeting(_start(client)) == "Hallo Erika!"


# Szenario 4
def test_leerzeichen_innen_bleiben_genau_so(client, keycloak):
    keycloak.person["given_name"] = "Anna  Lena"
    keycloak.person["family_name"] = f"von{NBSP}Testfrau"

    login(client)

    assert (_erika().first_name, _erika().last_name) == ("Anna  Lena", f"von{NBSP}Testfrau")


# Szenario 5
@pytest.mark.parametrize("value", [" ", "   ", NBSP, f" {ZERO_WIDTH_SPACE} "])
def test_vorname_nur_aus_leerzeichen_gilt_als_fehlend(client, keycloak, value):
    keycloak.person["given_name"] = value

    login(client)

    assert _erika().first_name == ""
    _assert_name_missing(client)


# Szenario 6 und 7
def test_nachname_nur_aus_leerzeichen_gilt_als_fehlend_auch_auf_mein_profil(client, keycloak):
    keycloak.person["family_name"] = " "

    login(client)

    assert _erika().last_name == ""
    start = _start(client)
    assert _greeting(start) == "Hallo Erika!"
    assert_is(notice_with(start, HINT_NAME), "warning")
    profile = _tree(client.get("/profil/"))
    assert_is(notice_with(profile, HINT_NAME), "warning")
    assert details(profile)["Nachname"] == NOT_GIVEN
    assert details(profile)["Vorname"] == "Erika"


# Szenario 7
def test_vorname_nur_aus_leerzeichen_auf_mein_profil_nicht_angegeben(client, keycloak):
    keycloak.person["given_name"] = " "

    login(client)

    profile = _tree(client.get("/profil/"))
    assert_is(notice_with(profile, HINT_NAME), "warning")
    assert details(profile)["Vorname"] == NOT_GIVEN


# Szenario 8
@pytest.mark.parametrize("value", [" ", f"{NBSP} "])
def test_mail_nur_aus_leerzeichen_kein_login_und_kurz_im_log(client, keycloak, log_output, value):
    keycloak.person["email"] = value

    response = login(client)

    assert response.status_code == 302
    assert response["Location"].startswith("/anmelden/")
    assert_is(notice_with(_tree(client.get("/anmelden/")), HINT_NO_MAIL), "warning")
    assert not User.objects.exists()
    assert client.get("/").status_code == 302
    log = log_output()
    assert "Login abgelehnt: Keycloak liefert keine Mail" in log
    for personal in [ERIKA["sub"], "erika", "Testfrau"]:
        assert personal.lower() not in log.lower(), f"„{personal}“ steht im Log:\n{log}"


def test_mail_nur_aus_leerzeichen_auch_bestehendes_konto_nicht_angemeldet(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person["email"] = " "

    response = login(client)

    assert response["Location"].startswith("/anmelden/")
    assert client.get("/").status_code == 302
    assert _erika().email == "erika.testfrau@example.org"


# Szenario 9
def test_bestehendes_konto_mit_vorname_nur_aus_leerzeichen_wird_beim_login_bereinigt(client, keycloak):
    keycloak.person["given_name"] = " "
    login(client)
    client.post("/abmelden/")
    # Der Stand vor der Behebung: Der Vorname aus Leerzeichen steht schon im Konto.
    User.objects.filter(pk=_erika().pk).update(first_name=" ", email=" erika.testfrau@example.org ")

    login(client)

    assert (_erika().first_name, _erika().email) == ("", "erika.testfrau@example.org")
    _assert_name_missing(client)


# Szenario 10
def test_korrigierter_vorname_nach_dem_naechsten_login_ohne_warnmeldung(client, keycloak):
    keycloak.person["given_name"] = " "
    login(client)
    client.post("/abmelden/")
    keycloak.person["given_name"] = "Erika"

    login(client)

    root = _start(client)
    assert _greeting(root) == "Hallo Erika!"
    assert HINT_NAME not in _visible_text(root)


# Aus der unabhängigen Prüfung (B1): Das Kürzen überlanger Angaben darf das Leerzeichen
# nicht wieder an den Rand setzen.
@pytest.mark.parametrize("field", ["given_name", "family_name", "preferred_username"])
def test_gekuerzte_angabe_endet_nicht_mit_einem_leerzeichen(client, keycloak, field):
    limit = User._meta.get_field({"preferred_username": "username"}.get(field, "first_name")).max_length
    keycloak.person[field] = "A" * (limit - 1) + " Erika"

    login(client)

    erika = User.objects.get()
    assert getattr(erika, {"given_name": "first_name", "family_name": "last_name"}.get(field, "username")) == (
        "A" * (limit - 1)
    )


# Aus der unabhängigen Prüfung (B3): Eine Mail-Liste aus der Zeit vor der Behebung.
def test_mail_liste_mit_leerzeichen_wird_beim_naechsten_login_bereinigt(client, keycloak):
    login(client)
    client.post("/abmelden/")
    erika = _erika()
    EmailAddress.objects.filter(user=erika).delete()
    EmailAddress.objects.create(user=erika, email=" erika.testfrau@example.org ", verified=True, primary=True)

    login(client)

    assert list(EmailAddress.objects.filter(user=erika).values_list("email", flat=True)) == [
        "erika.testfrau@example.org"
    ]


# Aus der unabhängigen Prüfung (B3): Begrüßung und Profilkreis holen den Namen an einer
# Stelle, damit #111 dort den Fahrtennamen vorschalten kann (Entscheidung vom 22.10.2026).
def test_begruessung_und_profilkreis_holen_den_namen_an_einer_stelle(client, keycloak, monkeypatch):
    login(client)
    monkeypatch.setattr(User, "short_name", property(lambda self: "Falkenflug"))

    root = _start(client)

    assert _greeting(root) == "Hallo Falkenflug!"
    assert raw_text(_circle(root)) == "F"
