"""Tests: Nach dem Login steht in `SocialAccount.extra_data` nur, was das Tool nutzt (#252, BF-126).

Die Nummern (E1 bis G1) verweisen auf den Kommentar „Szenarien (04.11.2026)“ in #252. Genutzt
werden Mail, „Mail bestätigt“, Benutzername, Vor- und Nachname. Keycloak ist nachgestellt
(tests/keycloak_fake.py) und schickt zusätzlich ein erfundenes Geburtsdatum mit. Alle Daten
sind erfunden.
"""

import json
from types import SimpleNamespace

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

from accounts.keycloak_abgleich import keep_only_used_data
from tests.keycloak_fake import ERIKA, MAX, login

pytestmark = pytest.mark.django_db

User = get_user_model()

BIRTHDATE = "1990-01-02"
USED = {"email", "email_verified", "preferred_username", "given_name", "family_name"}


@pytest.fixture(autouse=True)
def _keycloak_schickt_geburtsdatum(keycloak):
    keycloak.person["birthdate"] = BIRTHDATE


def _leaves(data, path=()) -> dict[str, object]:
    """Alle Einzelangaben aus verschachtelten Daten, nach ihrem letzten Namen."""
    if isinstance(data, dict):
        found = {}
        for key, value in data.items():
            found.update(_leaves(value, (*path, key)))
        return found
    return {path[-1] if path else "": data}


def _stored(sub: str) -> dict:
    """Die gespeicherten Angaben des Kontos mit dieser Keycloak-Kennung."""
    return SocialAccount.objects.get(uid=sub).extra_data


def _assert_only_used(extra_data: dict, person: dict) -> None:
    """Das Geburtsdatum steht nirgends, und nichts außer den fünf genutzten Angaben."""
    assert BIRTHDATE not in json.dumps(extra_data), f"Geburtsdatum gespeichert: {extra_data}"
    leaves = _leaves(extra_data)
    assert set(leaves) <= USED, f"Mehr als nötig gespeichert: {sorted(set(leaves) - USED)}"
    for key in USED & set(person):
        assert leaves.get(key) == person[key], f"„{key}“ fehlt oder weicht ab: {leaves}"


# E1
def test_erster_login_speichert_nur_die_genutzten_angaben(client, keycloak):
    login(client)

    _assert_only_used(_stored(ERIKA["sub"]), ERIKA)


# E2
def test_weiterer_login_speichert_nur_die_genutzten_angaben_im_selben_konto(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person["given_name"] = "Erika-Maria"

    login(client)

    assert User.objects.count() == 1
    assert SocialAccount.objects.count() == 1
    _assert_only_used(_stored(ERIKA["sub"]), keycloak.person)
    assert User.objects.get().first_name == "Erika-Maria"


# E3
def test_alte_vollstaendige_angaben_werden_beim_login_gekuerzt(client, keycloak):
    keycloak.person = dict(MAX)
    login(client)
    client.post("/abmelden/")
    SocialAccount.objects.filter(uid=MAX["sub"]).update(
        extra_data={"userinfo": {**MAX, "birthdate": BIRTHDATE}, "id_token": {"sub": MAX["sub"], "birthdate": BIRTHDATE}}
    )
    keycloak.person = {**MAX, "birthdate": BIRTHDATE}

    login(client)

    _assert_only_used(_stored(MAX["sub"]), MAX)


# V1
def test_gesperrtes_konto_wird_abgelehnt_und_das_geburtsdatum_nicht_gespeichert(client, keycloak):
    del keycloak.person["birthdate"]
    login(client)
    client.post("/abmelden/")
    User.objects.update(is_active=False)
    keycloak.person["birthdate"] = BIRTHDATE

    response = login(client)

    assert response.status_code == 302
    assert client.get("/").status_code == 302
    _assert_only_used(_stored(ERIKA["sub"]), ERIKA)


# V2
def test_ohne_mail_wird_abgelehnt_und_das_geburtsdatum_nicht_gespeichert(client, keycloak):
    del keycloak.person["birthdate"]
    login(client)
    client.post("/abmelden/")
    del keycloak.person["email"]
    keycloak.person["birthdate"] = BIRTHDATE

    response = login(client)

    assert response.status_code == 302
    assert client.get("/").status_code == 302
    # Gespeichert ist, was dieser Login mitbrachte, ohne die Mail, die fehlte.
    _assert_only_used(_stored(ERIKA["sub"]), keycloak.person)


# G1
def test_fehlt_eine_angabe_wird_nur_gespeichert_was_da_ist(client, keycloak):
    del keycloak.person["family_name"]

    response = login(client)

    assert User.objects.count() == 1
    assert client.get("/").status_code == 200, response.status_code
    stored = _stored(ERIKA["sub"])
    _assert_only_used(stored, keycloak.person)
    assert "family_name" not in _leaves(stored)


# Kein Szenario: Fehlermechanismus „andere Quelle als allauth“. Liefert Keycloak die Angaben nur im
# Kennungs-Token, liest allauth sie dort; die Kürzung muss dieselbe Quelle nehmen, sonst geht die Mail verloren.
def test_stehen_die_angaben_nur_im_kennungs_token_bleiben_die_genutzten_erhalten(client, keycloak):
    login(client)
    account = SocialAccount.objects.get(uid=ERIKA["sub"])
    account.extra_data = {"userinfo": {}, "id_token": {**ERIKA, "birthdate": BIRTHDATE}}

    keep_only_used_data(SimpleNamespace(account=account))

    _assert_only_used(_stored(ERIKA["sub"]), ERIKA)
