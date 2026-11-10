"""Tests zur Obergrenze der Sitzung: spätestens 12 Stunden nach dem Login (#8).

Eine im Keycloak des DPV gesperrte oder gelöschte Person soll höchstens bis 12 Stunden nach
ihrem letzten Login weiterarbeiten, auch wenn sie ständig klickt. Danach muss sie sich neu
anmelden; dabei merkt Keycloak die Sperre. Keycloak ist hier nachgestellt
(tests/keycloak_fake.py); das Zusammenspiel mit dem echten Keycloak prüft
tests/test_sitzung_obergrenze_echt.py. Die Zeit läuft nie echt ab: Die Tests setzen den
Login-Zeitpunkt oder verstellen die Uhr. Alle Daten sind erfunden.
"""

from datetime import timedelta

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from accounts.session import LOGIN_TIME_SESSION_KEY
from roles.models import SERVER_COMMAND, Role, RoleKind
from tests.keycloak_fake import login

pytestmark = pytest.mark.django_db

User = get_user_model()

HINT_EXPIRED = "Deine Sitzung ist abgelaufen. Bitte melde dich neu an."
TWELVE_HOURS = timedelta(hours=12)


def _set_login_time(client, ago: timedelta) -> None:
    """Tut so, als läge der Login so lange zurück."""
    session = client.session
    session[LOGIN_TIME_SESSION_KEY] = (timezone.now() - ago).timestamp()
    session.save()


def _assert_still_logged_in(client) -> None:
    response = client.get("/")
    assert response.status_code == 200, response.status_code
    assert "Hallo Erika!" in response.content.decode()


def _assert_next_click_leads_to_login_with_hint(client) -> None:
    response = client.get("/", follow=True)
    assert response.redirect_chain, "keine Weiterleitung, die Sitzung läuft noch"
    assert response.redirect_chain[-1][0].startswith("/anmelden/")
    assert response.status_code == 200
    page = response.content.decode()
    assert HINT_EXPIRED in page
    assert "Hallo Erika!" not in page


def test_beide_werte_stehen_an_einer_stelle_in_den_einstellungen(settings):
    assert settings.SESSION_IDLE_MINUTES == 120
    assert settings.SESSION_MAX_HOURS == 12


def test_knapp_vor_zwoelf_stunden_bleibt_die_person_angemeldet(client, keycloak):
    login(client)
    _set_login_time(client, TWELVE_HOURS - timedelta(seconds=5))

    _assert_still_logged_in(client)


def test_knapp_nach_zwoelf_stunden_fuehrt_der_naechste_klick_zum_login_mit_hinweis(client, keycloak):
    login(client)
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))

    _assert_next_click_leads_to_login_with_hint(client)


def test_genau_nach_zwoelf_stunden_ist_die_sitzung_zu_ende(client, keycloak, monkeypatch):
    """Die Uhr steht still; so liegt der Login genau 12 Stunden zurück, der letzte Klick aber nicht."""
    login(client)
    now = timezone.now()
    monkeypatch.setattr(timezone, "now", lambda: now)
    _set_login_time(client, TWELVE_HOURS)

    _assert_next_click_leads_to_login_with_hint(client)


def test_auch_wer_staendig_klickt_ist_nach_zwoelf_stunden_abgemeldet(client, keycloak, monkeypatch):
    """Erika klickt den ganzen Tag alle 1 Stunde 50 Minuten; die 2 Stunden ohne Klick greifen nie."""
    start = timezone.now()
    clock = {"now": start}
    monkeypatch.setattr(timezone, "now", lambda: clock["now"])
    login(client)

    step = timedelta(hours=1, minutes=50)
    while clock["now"] + step < start + TWELVE_HOURS:
        clock["now"] += step
        _assert_still_logged_in(client)

    clock["now"] += step
    _assert_next_click_leads_to_login_with_hint(client)


def test_nach_zwoelf_stunden_wie_nach_zwei_stunden_ohne_klick(client, keycloak):
    login(client)
    Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))
    after_idle = client.get("/")

    login(client)
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))
    after_max = client.get("/")

    assert after_idle.status_code == 302
    assert (after_max.status_code, after_max["Location"]) == (after_idle.status_code, after_idle["Location"])
    assert HINT_EXPIRED in client.get(after_max["Location"]).content.decode()


def test_rollen_profil_und_konto_bleiben_unveraendert(client, keycloak):
    login(client)
    erika = User.objects.get()
    Role(user=erika, kind=RoleKind.ADMIN).save(by=SERVER_COMMAND)
    before = (
        list(User.objects.values()),
        list(SocialAccount.objects.values("user_id", "uid")),
        list(Role.objects.values("user_id", "kind", "unit_id")),
    )
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))

    _assert_next_click_leads_to_login_with_hint(client)

    after = (
        list(User.objects.values()),
        list(SocialAccount.objects.values("user_id", "uid")),
        list(Role.objects.values("user_id", "kind", "unit_id")),
    )
    assert after == before


def test_das_tool_fragt_dafuer_nicht_bei_keycloak_nach(client, keycloak):
    """Ist Keycloak weg, geht die Arbeit bis zur Obergrenze weiter, und die Sitzung endet trotzdem."""
    login(client)
    keycloak.unreachable = True

    _set_login_time(client, TWELVE_HOURS - timedelta(minutes=1))
    _assert_still_logged_in(client)
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))
    _assert_next_click_leads_to_login_with_hint(client)


def test_neuer_login_nach_ablauf_gibt_wieder_zwoelf_stunden(client, keycloak):
    login(client)
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))
    _assert_next_click_leads_to_login_with_hint(client)

    login(client)

    _assert_still_logged_in(client)
    remaining = client.session[LOGIN_TIME_SESSION_KEY] + TWELVE_HOURS.total_seconds() - timezone.now().timestamp()
    assert TWELVE_HOURS.total_seconds() - 60 < remaining <= TWELVE_HOURS.total_seconds()


def test_sitzung_ohne_login_zeitpunkt_endet_beim_naechsten_klick(client, keycloak):
    """Etwa eine Sitzung von vor dieser Änderung: Ohne Zeitpunkt gilt sie als zu alt."""
    login(client)
    session = client.session
    session.pop(LOGIN_TIME_SESSION_KEY, None)
    session.save()

    _assert_next_click_leads_to_login_with_hint(client)


def test_login_an_einem_anderen_geraet_verlaengert_die_sitzung_hier_nicht(keycloak):
    """Die 12 Stunden zählen je Sitzung, nicht ab dem letzten Login der Person irgendwo."""
    laptop, handy = Client(), Client()
    login(laptop)
    _set_login_time(laptop, TWELVE_HOURS + timedelta(seconds=1))

    login(handy)

    _assert_next_click_leads_to_login_with_hint(laptop)
    _assert_still_logged_in(handy)


def test_abmelden_nach_ablauf_fuehrt_weiter_zu_keycloak(client, keycloak, settings):
    login(client)
    _set_login_time(client, TWELVE_HOURS + timedelta(seconds=1))

    response = client.post("/abmelden/")

    # Seit #280 per Formular an Keycloak statt über eine Weiterleitung.
    assert response.status_code == 200
    assert f'action="{settings.KEYCLOAK_REALM_URL}/protocol/openid-connect/logout"' in response.content.decode()
