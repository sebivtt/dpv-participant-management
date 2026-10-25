"""Tests: Mail-Liste und Benutzername kommen bei jedem Login aus Keycloak (#76, ORG-03).

Die Nummern verweisen auf den Kommentar „Szenarien (25.10.2026)“ in #76. Die Mail-Liste ist
allauths Tabelle `account_emailaddress`. Keycloak ist nachgestellt (tests/keycloak_fake.py);
alle Daten sind erfunden.
"""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

from tests.keycloak_fake import ERIKA, MAX, login

pytestmark = pytest.mark.django_db

User = get_user_model()


def _mail_list(user) -> list[tuple[str, bool]]:
    """Die Einträge der Mail-Liste eines Kontos: Mail und Kennzeichen „bestätigt“."""
    return list(EmailAddress.objects.filter(user=user).values_list("email", "verified"))


def _login_again(client) -> None:
    client.post("/abmelden/")
    login(client)


def _erika() -> User:
    return User.objects.get(socialaccount__uid=ERIKA["sub"])


# Szenario 1
@pytest.mark.parametrize("verified", [True, False])
def test_erstes_login_ergibt_genau_einen_eintrag_mit_bestaetigt_aus_keycloak(client, keycloak, verified):
    keycloak.person["email_verified"] = verified

    login(client)

    assert _mail_list(_erika()) == [("erika.testfrau@example.org", verified)]


def test_erstes_login_uebernimmt_die_schreibweise_der_mail_aus_keycloak(client, keycloak):
    # allauth schreibt die Mail beim ersten Login sonst klein, das Konto aber nicht.
    keycloak.person["email"] = "Erika.Testfrau@Example.org"

    login(client)

    erika = _erika()
    assert erika.email == "Erika.Testfrau@Example.org"
    assert _mail_list(erika) == [("Erika.Testfrau@Example.org", True)]


# Szenario 2
def test_nach_mailwechsel_steht_nur_noch_die_neue_mail_in_der_liste(client, keycloak):
    login(client)
    keycloak.person["email"] = "erika.neu@example.org"

    _login_again(client)

    erika = _erika()
    assert erika.email == "erika.neu@example.org"
    assert _mail_list(erika) == [("erika.neu@example.org", True)]


def test_geaenderte_schreibweise_der_mail_wird_genau_so_uebernommen(client, keycloak):
    login(client)
    keycloak.person["email"] = "Erika.Testfrau@Example.org"

    _login_again(client)

    erika = _erika()
    assert erika.email == "Erika.Testfrau@Example.org"
    assert _mail_list(erika) == [("Erika.Testfrau@Example.org", True)]


# Szenario 3
@pytest.mark.parametrize("before, after", [(True, False), (False, True)])
def test_kennzeichen_bestaetigt_folgt_keycloak_auch_wenn_es_sich_aendert(client, keycloak, before, after):
    keycloak.person["email_verified"] = before
    login(client)
    keycloak.person["email_verified"] = after

    _login_again(client)

    assert _mail_list(_erika()) == [("erika.testfrau@example.org", after)]


# Szenario 4
def test_mehrere_logins_ohne_aenderung_ergeben_keine_doppelten_eintraege(client, keycloak):
    login(client)
    _login_again(client)
    _login_again(client)

    assert _mail_list(_erika()) == [("erika.testfrau@example.org", True)]


def test_mail_liste_anderer_konten_bleibt_unberuehrt(client, keycloak):
    keycloak.person = dict(MAX)
    login(client)
    client.post("/abmelden/")
    keycloak.person = dict(ERIKA)
    login(client)
    keycloak.person["email"] = "erika.neu@example.org"

    _login_again(client)

    max_ = User.objects.get(socialaccount__uid=MAX["sub"])
    assert _mail_list(max_) == [("max.testmann@example.org", True)]


# Szenario 5
def test_geaenderter_benutzername_steht_nach_dem_naechsten_login_im_konto(client, keycloak):
    login(client)
    keycloak.person["preferred_username"] = "erika.neu"

    _login_again(client)

    assert _erika().username == "erika.neu"


# Szenario 6
def test_vergebener_benutzername_login_gelingt_alter_name_bleibt_log_ohne_personendaten(client, keycloak, log_output):
    keycloak.person = dict(MAX)
    login(client)
    client.post("/abmelden/")
    keycloak.person = dict(ERIKA)
    login(client)
    keycloak.person["preferred_username"] = "max.testmann"
    keycloak.person["family_name"] = "Probe"

    client.post("/abmelden/")
    response = login(client)

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert client.get("/").status_code == 200
    erika = _erika()
    assert erika.username == "erika.testfrau"
    assert erika.last_name == "Probe", "Die übrigen Angaben kommen trotzdem aus Keycloak."
    max_ = User.objects.get(socialaccount__uid=MAX["sub"])
    assert (max_.username, max_.email) == ("max.testmann", "max.testmann@example.org")
    log = log_output()
    assert "Benutzername aus Keycloak im Tool schon vergeben, alter bleibt" in log
    for value in ["erika", "max", "testfrau", "testmann", "example.org", ERIKA["sub"], MAX["sub"], str(erika.pk)]:
        assert value.lower() not in log.lower(), f"„{value}“ steht im Log:\n{log}"


def test_vergebener_benutzername_wird_uebernommen_sobald_er_frei_ist(client, keycloak):
    keycloak.person = dict(MAX)
    login(client)
    client.post("/abmelden/")
    keycloak.person = dict(ERIKA)
    login(client)
    keycloak.person["preferred_username"] = "max.testmann"
    _login_again(client)
    assert _erika().username == "erika.testfrau"
    User.objects.filter(socialaccount__uid=MAX["sub"]).update(username="max.anders")

    _login_again(client)

    assert _erika().username == "max.testmann"


# Szenario 7
def test_sehr_langer_benutzername_wird_bei_jedem_login_gekuerzt_uebernommen(client, keycloak):
    login(client)
    keycloak.person["preferred_username"] = "u" * 255

    _login_again(client)

    assert _erika().username == "u" * 150


def test_gekuerzter_benutzername_schon_vergeben_alter_name_bleibt(client, keycloak, log_output):
    User.objects.create(username="u" * 150)
    login(client)
    keycloak.person["preferred_username"] = "u" * 255

    _login_again(client)

    assert client.get("/").status_code == 200
    assert _erika().username == "erika.testfrau"
    assert "Benutzername aus Keycloak im Tool schon vergeben, alter bleibt" in log_output()


# Szenario 8
def test_ohne_benutzernamen_aus_keycloak_bleibt_der_bisherige_und_login_gelingt(client, keycloak):
    login(client)
    del keycloak.person["preferred_username"]

    client.post("/abmelden/")
    response = login(client)

    assert response["Location"] == "/"
    assert client.get("/").status_code == 200
    assert _erika().username == "erika.testfrau"


# Szenario 9
def test_abgelehnter_login_gleicht_nichts_an(client, keycloak):
    login(client)
    User.objects.update(is_active=False)
    keycloak.person["email"] = "erika.neu@example.org"
    keycloak.person["email_verified"] = False
    keycloak.person["preferred_username"] = "erika.neu"

    _login_again(client)

    assert client.get("/").status_code == 302
    erika = _erika()
    assert (erika.username, erika.email) == ("erika.testfrau", "erika.testfrau@example.org")
    assert _mail_list(erika) == [("erika.testfrau@example.org", True)]
