"""Tests für den Login über den Keycloak des DPV (#5, ORG-02, ORG-03).

Keycloak ist hier nachgestellt (tests/keycloak_fake.py), damit jede Regel einzeln prüfbar
ist. Die Nummern verweisen auf die Szenarien im Issue #5 (Kommentare „Vorarbeit zur
Umsetzung“ und „Nachklärung und Szenarien“). Alle Daten sind erfunden.
"""

import subprocess
import sys
import threading
from datetime import timedelta
from pathlib import Path

import pytest
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import connection
from django.test import Client, RequestFactory
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from accounts.adapter import SocialAccountAdapter
from tests.keycloak_fake import ERIKA, MAX, RETURN, keycloak_parameters, login, start_login

pytestmark = pytest.mark.django_db

User = get_user_model()
BASE_DIR = Path(__file__).resolve().parent.parent

GREETING_SENTENCE = "Hier entsteht das DPV Anmeldetool"
HINT_NAME = "Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an."
HINT_CANCELLED = "Die Anmeldung wurde abgebrochen. Du kannst es noch einmal versuchen."
HINT_UNREACHABLE = "Die Anmeldung ist gerade nicht möglich. Versuche es später noch einmal."
HINT_NO_MAIL = "Die Anmeldung ist nicht möglich, weil in deinem DPV-Konto keine Mail eingetragen ist."
HINT_EXPIRED = "Deine Sitzung ist abgelaufen. Bitte melde dich neu an."
HINT_NO_ACCOUNT = "Wenn du noch kein Konto hast, wende dich an anmeldetool@dpvonline.de"
REGISTRATION_LINK = "Noch kein Konto? Registrieren"


def _page(response) -> str:
    return response.content.decode()


def _login_page(client) -> str:
    response = client.get("/anmelden/")
    assert response.status_code == 200
    return _page(response)


def _assert_lands_on_login_page_with(client, response, hint: str) -> None:
    """Prüft: weitergeleitet zur Login-Seite, dort steht der Hinweis, keine Fehlerseite."""
    assert response.status_code == 302, response.status_code
    assert response["Location"].startswith("/anmelden/")
    assert hint in _login_page(client)


# Szenario 1
def test_erika_sieht_nach_dem_login_begruessung_name_mail_und_abmelden(client, keycloak):
    response = login(client)

    assert response.status_code == 302
    assert response["Location"] == "/"
    page = _page(client.get("/"))
    assert "Hallo Erika!" in page
    # Name und Mail stehen seit #96 auf „Mein Profil“ statt im Kasten „Dein Konto“.
    profile = _page(client.get("/profil/"))
    assert "Erika" in profile and "Testfrau" in profile
    assert "erika.testfrau@example.org" in profile
    assert GREETING_SENTENCE in page
    assert 'action="/abmelden/"' in page
    assert "Abmelden" in page
    assert HINT_NAME not in page


def test_konto_ist_ueber_die_feste_keycloak_kennung_verknuepft(client, keycloak):
    login(client)

    account = SocialAccount.objects.get()
    assert account.uid == ERIKA["sub"]
    assert account.user.email == "erika.testfrau@example.org"


# Szenario 2
def test_geaenderter_name_steht_nach_dem_naechsten_login_da(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person["family_name"] = "Probe"

    login(client)

    page = _page(client.get("/profil/"))  # seit #96 statt der Startseite
    assert "Probe" in page
    assert "Testfrau" not in page
    assert User.objects.get().last_name == "Probe"


def test_mail_kommt_bei_jedem_login_aus_keycloak(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person["email"] = "erika.neu@example.org"

    login(client)

    assert User.objects.get().email == "erika.neu@example.org"


# Szenario 3
def test_ohne_namen_klappt_der_login_mit_hallo_und_hinweis(client, keycloak):
    del keycloak.person["given_name"]
    del keycloak.person["family_name"]

    login(client)

    page = _page(client.get("/"))
    assert "Hallo!" in page
    assert HINT_NAME in page
    assert "erika.testfrau@example.org" in _page(client.get("/profil/"))  # seit #96 statt der Startseite


# Szenario 21
def test_ohne_nachnamen_hallo_mit_vornamen_und_hinweis(client, keycloak):
    del keycloak.person["family_name"]
    keycloak.person["name"] = "Erika"

    login(client)

    page = _page(client.get("/"))
    assert "Hallo Erika!" in page
    assert HINT_NAME in page


def test_ohne_vornamen_wird_der_nachname_nicht_zum_vornamen(client, keycloak):
    # Keycloak schickt zusätzlich den ganzen Namen („name“). Fehlt der Vorname, darf das
    # Tool den Nachnamen daraus nicht als Vornamen nehmen.
    del keycloak.person["given_name"]
    keycloak.person["name"] = "Testfrau"

    login(client)

    page = _page(client.get("/"))
    assert "Hallo!" in page
    assert "Hallo Testfrau!" not in page
    assert HINT_NAME in page


# Szenario 4
def test_ohne_mail_wird_der_login_abgelehnt_und_kurz_im_log_vermerkt(client, keycloak, log_output):
    del keycloak.person["email"]

    response = login(client)

    _assert_lands_on_login_page_with(client, response, HINT_NO_MAIL)
    assert not User.objects.exists()
    assert client.get("/").status_code == 302
    log = log_output()
    assert "Login abgelehnt: Keycloak liefert keine Mail" in log
    for value in [ERIKA["sub"], "erika", "Testfrau"]:
        assert value.lower() not in log.lower(), f"„{value}“ steht im Log:\n{log}"


def test_ohne_mail_wird_auch_ein_bestehendes_konto_nicht_angemeldet(client, keycloak):
    login(client)
    client.post("/abmelden/")
    del keycloak.person["email"]

    response = login(client)

    _assert_lands_on_login_page_with(client, response, HINT_NO_MAIL)
    assert client.get("/").status_code == 302


# Szenario 5
def test_gleiche_mail_andere_kennung_kommt_nie_ins_bestehende_konto(client, keycloak):
    login(client)
    erika = User.objects.get()
    client.post("/abmelden/")
    keycloak.person["sub"] = "33333333-aaaa-4bbb-8ccc-000000000003"

    login(client)

    assert int(client.session["_auth_user_id"]) != erika.pk
    assert User.objects.count() == 2
    assert SocialAccount.objects.get(user=erika).uid == ERIKA["sub"]


# Szenario 6
def test_abgebrochener_login_fuehrt_zur_login_seite_mit_hinweis(client, keycloak):
    state = keycloak_parameters(start_login(client))["state"]

    response = client.get(RETURN, {"state": state, "error": "access_denied"})

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    assert client.get("/").status_code == 302


# Szenario 7
def test_abmelden_beendet_die_sitzung_und_meldet_bei_keycloak_ab(client, keycloak):
    login(client)
    id_token = keycloak.last_id_token

    response = client.post("/abmelden/")

    # Seit #280 per Formular statt über eine Adresse; den Aufbau prüft tests/test_abmelden.py.
    # Mit dem Kennungs-Token fragt Keycloak nicht nach, ob man sich wirklich abmelden will.
    assert response.status_code == 200
    page = response.content.decode()
    assert f'action="{keycloak.endpoints["end_session_endpoint"]}"' in page
    assert f'name="id_token_hint" value="{id_token}"' in page
    assert 'name="post_logout_redirect_uri" value="http://testserver/anmelden/"' in page
    assert not Session.objects.exists()
    assert client.get("/").status_code == 302
    assert HINT_EXPIRED not in _login_page(client)


# Szenario 8
def test_sitzung_endet_nach_zwei_stunden_ohne_aktivitaet(settings):
    assert settings.SESSION_IDLE_MINUTES == 120
    assert settings.SESSION_COOKIE_AGE == 120 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True


def test_jeder_klick_verlaengert_die_sitzung_um_zwei_stunden(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() + timedelta(minutes=5))

    client.get("/")

    remaining = Session.objects.get().expire_date - timezone.now()
    assert timedelta(minutes=119) < remaining <= timedelta(minutes=120)


def test_nach_abgelaufener_sitzung_fuehrt_der_naechste_klick_zum_login_mit_hinweis(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))

    response = client.get("/", follow=True)

    assert response.redirect_chain[-1][0].startswith("/anmelden/")
    assert response.status_code == 200
    assert HINT_EXPIRED in _page(response)


# Szenario 9
def test_registrierungslink_fuehrt_zur_registrierung_von_keycloak(client, keycloak):
    page = _login_page(client)
    assert REGISTRATION_LINK in page
    assert "auth_params=prompt%3Dcreate" in page

    parameters = keycloak_parameters(start_login(client, auth_params="prompt=create"))
    assert parameters["prompt"] == "create"

    response = client.get(RETURN, {"state": parameters["state"], "code": "code-nur-test"})
    assert response["Location"] == "/"
    assert "Hallo Erika!" in _page(client.get("/"))


# Szenario 10
def test_ausgeblendeter_registrierungslink_zeigt_stattdessen_die_adresse(client, settings):
    settings.REGISTRATION_LINK_ENABLED = False

    page = _login_page(client)

    assert REGISTRATION_LINK not in page
    assert "prompt%3Dcreate" not in page
    assert HINT_NO_ACCOUNT in page


def test_adresse_fuer_ein_konto_ist_einstellbar(client, settings):
    settings.REGISTRATION_LINK_ENABLED = False
    settings.ACCOUNT_HELP_EMAIL = "konto@example.org"

    assert "wende dich an konto@example.org" in _login_page(client)


def test_mit_registrierungslink_kein_hinweis_auf_die_adresse(client):
    assert HINT_NO_ACCOUNT not in _login_page(client)


# Szenario 12
def test_kein_passwortfeld_und_keine_eigene_registrierung(client, keycloak):
    assert 'type="password"' not in _login_page(client)
    for name in [
        "account_signup",
        "account_change_password",
        "account_set_password",
        "account_reset_password",
        "account_email",
        "socialaccount_signup",
        "socialaccount_connections",
    ]:
        with pytest.raises(NoReverseMatch):
            reverse(name)
    for address in ["/accounts/login/", "/accounts/signup/", "/accounts/password/reset/"]:
        assert client.get(address).status_code == 404

    login(client)
    assert not User.objects.get().has_usable_password()


# Szenario 13
def test_nach_dem_abmelden_sieht_die_naechste_person_nur_ihre_eigenen_daten(client, keycloak):
    login(client)
    client.post("/abmelden/")
    keycloak.person = dict(MAX)

    login(client)

    page = _page(client.get("/"))
    assert "Hallo Max!" in page
    assert "Erika" not in page
    profile = _page(client.get("/profil/"))  # Name und Mail seit #96 auf „Mein Profil“
    assert "max.testmann@example.org" in profile
    assert "Erika" not in profile
    assert "erika.testfrau@example.org" not in profile


def test_login_seite_zeigt_nach_dem_abmelden_nichts_von_der_vorigen_person(client, keycloak):
    # allauth meldet sonst „Erfolgreich angemeldet als erika.testfrau“, und diese Meldung
    # erschiene erst auf der Login-Seite der nächsten Person am selben Gerät.
    login(client)
    client.get("/")
    client.post("/abmelden/")

    page = _login_page(client)

    assert "erika" not in page.lower()


# Szenario 14
def test_wer_angemeldet_ist_kommt_von_der_login_seite_zur_startseite(client, keycloak):
    login(client)

    response = client.get("/anmelden/")

    assert response.status_code == 302
    assert response["Location"] == "/"


# Szenario 15
def test_gefaelschte_rueckmeldung_ohne_login_bei_keycloak_meldet_niemanden_an(client, keycloak):
    response = client.get(RETURN, {"state": "gefaelscht", "code": "code-nur-test"})

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    assert client.get("/").status_code == 302
    assert not User.objects.exists()


def test_rueckmeldung_mit_fremdem_state_meldet_niemanden_an(client, keycloak):
    start_login(client)

    response = client.get(RETURN, {"state": "von-einem-anderen-geraet", "code": "code-nur-test"})

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    assert not User.objects.exists()


def test_angemeldete_person_kann_kein_zweites_keycloak_konto_verknuepfen(client, keycloak):
    # allauth kennt neben dem Login auch das Verknüpfen weiterer Konten. Das Tool verknüpft
    # genau ein Keycloak-Konto; ein untergeschobenes „connect“ darf nichts verknüpfen.
    login(client)
    erika = User.objects.get()
    keycloak.person = dict(MAX)
    state = keycloak_parameters(client.post("/anmelden/keycloak/start/", {"process": "connect"}))["state"]

    response = client.get(RETURN, {"state": state, "code": "code-nur-test"})

    # Erika bleibt angemeldet; die Login-Seite führt sie deshalb gleich zur Startseite.
    assert response.status_code == 302
    assert response["Location"].startswith("/anmelden/")
    assert list(SocialAccount.objects.filter(user=erika).values_list("uid", flat=True)) == [ERIKA["sub"]]
    assert not SocialAccount.objects.filter(uid=MAX["sub"]).exists()


# Szenario 16
def test_nach_dem_login_nie_weiter_zu_einer_fremden_seite(client, keycloak):
    response = login(client, next_url="https://fremde-seite.example/")

    assert response.status_code == 302
    assert response["Location"] == "/"


# Szenario 17
def test_abmelden_geht_nicht_ueber_einen_blossen_link(client, keycloak):
    login(client)

    response = client.get("/abmelden/")

    assert response.status_code == 405
    assert client.get("/").status_code == 200


def test_fremde_seite_kann_niemanden_heimlich_abmelden(client, keycloak):
    login(client)
    # Ein Browser mit derselben Anmeldung, der wie im Betrieb den Formularschutz (CSRF) prüft.
    browser = Client(enforce_csrf_checks=True)
    browser.cookies = client.cookies

    response = browser.post("/abmelden/")

    assert response.status_code == 403
    assert browser.get("/").status_code == 200


@pytest.mark.parametrize("query", ["", "?process=connect"])
def test_login_startet_nur_mit_formular_nicht_ueber_einen_blossen_link(client, keycloak, query):
    # Ein bloßer Link zeigte sonst eine ungestaltete Bestätigungsseite von allauth.
    response = client.get(f"/anmelden/keycloak/start/{query}")

    assert response.status_code == 302
    assert response["Location"] == "/anmelden/"


# Szenario 18
def test_normaler_login_schreibt_nichts_ueber_die_person_ins_log(client, keycloak, log_output):
    login(client)
    client.get("/")
    client.post("/abmelden/")

    log = log_output()
    for value in [ERIKA["sub"], "erika", "Testfrau", "zugang-nur-test", keycloak.last_id_token]:
        assert value.lower() not in log.lower(), f"„{value}“ steht im Log:\n{log}"


# Szenario 19
def test_wer_nie_angemeldet_war_sieht_keinen_hinweis_auf_eine_abgelaufene_sitzung(client):
    response = client.get("/", follow=True)

    assert response.redirect_chain[-1][0].startswith("/anmelden/")
    assert HINT_EXPIRED not in _page(response)


# Szenario 20
def test_keycloak_nicht_erreichbar_beim_start_zeigt_login_seite_mit_hinweis(client, keycloak, log_output):
    keycloak.unreachable = True

    response = start_login(client)

    _assert_lands_on_login_page_with(client, response, HINT_UNREACHABLE)
    assert "Keycloak nicht erreichbar" in log_output()


def test_keycloak_nicht_erreichbar_bei_der_rueckkehr_zeigt_login_seite_mit_hinweis(client, keycloak):
    state = keycloak_parameters(start_login(client))["state"]
    keycloak.unreachable = True

    response = client.get(RETURN, {"state": state, "code": "code-nur-test"})

    _assert_lands_on_login_page_with(client, response, HINT_UNREACHABLE)
    assert client.get("/").status_code == 302


# Wer darf das nicht? Neue Konten bekommen keinerlei Rechte (Hinweis für P2, #9).
def test_neues_konto_hat_keine_besonderen_rechte(client, keycloak):
    login(client)

    erika = User.objects.get()
    assert not erika.is_staff
    assert not erika.is_superuser
    assert not erika.user_permissions.exists()
    assert not erika.groups.exists()


# Einstellungen
def test_ohne_keycloak_angaben_startet_das_tool_nicht():
    env = {
        "PATH": "/usr/bin:/bin",
        "DJANGO_SETTINGS_MODULE": "config.settings",
        "DJANGO_SECRET_KEY": "nur-fuer-diesen-test",
        "POSTGRES_DB": "beispiel",
        "POSTGRES_USER": "beispiel",
        "POSTGRES_PASSWORD": "beispiel",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check"], cwd=BASE_DIR, env=env, capture_output=True, text=True, check=False
    )

    assert result.returncode != 0
    for name in ["KEYCLOAK_REALM_URL", "KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_SECRET"]:
        assert name in result.stderr


# Befunde der unabhängigen Prüfung
@pytest.mark.django_db(transaction=True)
def test_zwei_gleichzeitige_erste_logins_ohne_fehlerseite_und_ohne_verwaistes_konto(client, keycloak, monkeypatch):
    # Doppelklick oder zwei Tabs: Während die Rückkehr von A läuft, ist die von B schon fertig.
    # B läuft wie im Betrieb über eine eigene Datenbankverbindung (eigener Thread).
    other = Client()
    state_a = keycloak_parameters(start_login(client))["state"]
    state_b = keycloak_parameters(start_login(other))["state"]
    original = SocialAccountAdapter.pre_social_login
    calls = []

    def b_finishes_first(self, request, sociallogin):
        calls.append(1)
        if len(calls) == 1:
            thread = threading.Thread(target=_return_in_own_connection, args=(other, state_b))
            thread.start()
            thread.join()
        return original(self, request, sociallogin)

    monkeypatch.setattr(SocialAccountAdapter, "pre_social_login", b_finishes_first)

    response = client.get(RETURN, {"state": state_a, "code": "code-nur-test"})

    assert response.status_code == 302
    assert User.objects.count() == 1
    assert SocialAccount.objects.count() == 1


def _return_in_own_connection(browser, state: str) -> None:
    try:
        browser.get(RETURN, {"state": state, "code": "code-nur-test"})
    finally:
        connection.close()


def test_sehr_langer_name_aus_keycloak_fuehrt_nicht_zur_fehlerseite(client, keycloak):
    keycloak.person["given_name"] = "E" * 255
    keycloak.person["family_name"] = "T" * 255
    keycloak.person["preferred_username"] = "u" * 255

    response = login(client)

    assert response["Location"] == "/"
    erika = User.objects.get()
    assert erika.first_name == "E" * 150
    assert erika.last_name == "T" * 150


def test_sehr_lange_mail_aus_keycloak_fuehrt_nicht_zur_fehlerseite(client, keycloak):
    keycloak.person["email"] = "e" * 250 + "@example.org"

    response = login(client)

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    assert not User.objects.exists()


def test_im_tool_gesperrtes_konto_fuehrt_nicht_zur_fehlerseite(client, keycloak):
    login(client)
    client.post("/abmelden/")
    User.objects.update(is_active=False)

    response = login(client)

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    assert client.get("/").status_code == 302


@pytest.mark.parametrize(
    "auth_params",
    ["redirect_uri=http://localhost:8000/x", "state=fremd", "prompt=none", "prompt=create&login_hint=erika"],
)
def test_nur_die_registrierung_darf_zusaetzliche_angaben_an_keycloak_schicken(client, keycloak, auth_params):
    response = start_login(client, auth_params=auth_params)

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)


def test_umfang_der_angaben_von_keycloak_laesst_sich_nicht_aendern(client, keycloak):
    response = client.post("/anmelden/keycloak/start/?scope=openid+offline_access")

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)


def test_falsche_keycloak_adresse_ohne_fehlerseite(client, keycloak):
    # Antwortet unter der eingestellten Adresse etwas anderes als Keycloak, fehlen die Angaben.
    keycloak.endpoints = {"issuer": keycloak.realm}

    response = start_login(client)

    _assert_lands_on_login_page_with(client, response, HINT_UNREACHABLE)


# #75 (Befund K3 aus #73): Beim abgebrochenen Login kommen nur die drei bekannten Werte von
# allauth ins Log, jeder andere als „anderer Wert“. Erfundene Mail als frei gewählter Text.
FREE_TEXT = "geheim.erika@example.org"


def test_frei_gewaehlter_fehler_in_der_adresse_kommt_nicht_ins_log(client, keycloak, log_output):
    # Wache: allauth 65.20.1 macht daraus schon selbst „unknown“. Besteht deshalb auch ohne die
    # Prüfung im Tool und meldet, falls eine künftige Fassung von allauth den Text weitergibt.
    state = keycloak_parameters(start_login(client))["state"]

    response = client.get(RETURN, {"state": state, "error": FREE_TEXT})

    _assert_lands_on_login_page_with(client, response, HINT_CANCELLED)
    log = log_output()
    assert "Login nicht abgeschlossen: unknown" in log
    assert "erika" not in log


def _authentication_error(error: str) -> None:

    request = RequestFactory().get(RETURN)
    request.session = {}
    request._messages = FallbackStorage(request)
    with pytest.raises(ImmediateHttpResponse):
        SocialAccountAdapter(request).on_authentication_error(request, provider=None, error=error)


def test_frei_gewaehlter_fehlerwert_steht_als_anderer_wert_im_log(log_output):
    _authentication_error(FREE_TEXT)

    log = log_output()
    assert "Login nicht abgeschlossen: anderer Wert" in log
    assert "erika" not in log


# Szenario 8 aus #75: Gegenprobe
@pytest.mark.parametrize("error", ["cancelled", "unknown", "denied"])
def test_bekannte_fehlerwerte_von_allauth_stehen_weiter_im_log(log_output, error):
    _authentication_error(error)

    assert f"Login nicht abgeschlossen: {error}\n" in log_output()


def test_echter_abbruch_steht_weiter_als_cancelled_im_log(client, keycloak, log_output):
    state = keycloak_parameters(start_login(client))["state"]

    client.get(RETURN, {"state": state, "error": "access_denied"})

    assert "Login nicht abgeschlossen: cancelled" in log_output()
