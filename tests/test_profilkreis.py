"""Tests für den Profilkreis als Zugang zu „Mein Profil“ (#13, PER-01; EP-01, EP-02).

Die Nummern verweisen auf Sebastians Szenarien vom 26.10.2026 in #13. Was nur ein echter
Browser zeigen kann (Tastatur, sichtbarer Fokus), prüft der Rauchtest in
rauchtests/test_rauchtest.py. Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _sidebar, _text, _tree, _visible_text

pytestmark = pytest.mark.django_db

User = get_user_model()

PROFILE = "/profil/"
PAGES_WITH_SIDEBAR = ["/", PROFILE, "/muster/"]


def _client(username="erika.testfrau", first_name="Erika", last_name="Testfrau") -> tuple[Client, User]:
    user = User.objects.create(username=username, first_name=first_name, last_name=last_name,
                               email=f"{username}@example.org")
    client = Client()
    client.force_login(user)
    return client, user


def _circles(root) -> tuple:
    """Der Kreis unten in der Seitenleiste (PC) und der oben in der Leiste (Handy)."""
    sidebar = _one(_all(_sidebar(root), lambda e: e.name == "a" and "a-profil" in _classes(e)))
    bar = _one(_all(root, lambda e: e.name == "header" and "a-topbar" in _classes(e)))
    topbar = _one(_all(bar, lambda e: e.name == "a" and "a-profil" in _classes(e)))
    return sidebar, topbar


# ---------- Szenarien 1 bis 3: der Kreis führt auf jeder Seite zu „Mein Profil“ ----------


@pytest.mark.parametrize("address", PAGES_WITH_SIDEBAR)
def test_kreis_am_pc_und_am_handy_fuehrt_auf_jeder_seite_zu_mein_profil(address):
    client, _ = _client()

    for circle in _circles(_tree(client.get(address))):
        assert _attr(circle, "href") == PROFILE
        assert "Mein Profil" in (_attr(circle, "aria-label") or _text(circle))


def test_klick_auf_den_kreis_zeigt_die_eigenen_angaben():
    client, _ = _client()
    sidebar, _ = _circles(_tree(client.get("/")))

    root = _tree(client.get(_attr(sidebar, "href")))

    assert _visible_text(_one(_by_tag(root, "h1"))) == "Mein Profil"
    assert "erika.testfrau@example.org" in _text(_one(_by_tag(root, "main")))


# ---------- Szenario 4: hervorgehoben, solange „Mein Profil“ offen ist ----------


def test_auf_mein_profil_ist_der_kreis_die_aktuelle_seite():
    client, _ = _client()

    for circle in _circles(_tree(client.get(PROFILE))):
        assert _attr(circle, "aria-current") == "page"


@pytest.mark.parametrize("address", ["/", "/muster/"])
def test_auf_anderen_seiten_ist_der_kreis_nicht_hervorgehoben(address):
    client, _ = _client()

    for circle in _circles(_tree(client.get(address))):
        assert _attr(circle, "aria-current") is None


# ---------- Szenario 6: die Adresse enthält keine Kennung (EP-02) ----------


@pytest.mark.rechtematrix("EP-02")
def test_adresse_hinter_dem_kreis_enthaelt_keine_kennung():
    client, erika = _client()

    for circle in _circles(_tree(client.get("/"))):
        href = _attr(circle, "href")
        assert href == PROFILE
        for identifier in (str(erika.key), str(erika.pk), erika.username):
            assert identifier not in href


@pytest.mark.rechtematrix("EP-02")
def test_fremde_kennung_am_ziel_des_kreises_zeigt_das_eigene_profil():
    _, erika = _client()
    client, _ = _client(username="max.testmann", first_name="Max", last_name="Testmann")

    response = client.get(PROFILE, {"person": erika.key, "id": erika.pk, "username": erika.username})

    main = _text(_one(_by_tag(_tree(response), "main")))
    assert "max.testmann@example.org" in main
    assert "erika.testfrau" not in main


# ---------- Szenario 7: Konto ohne Namen ----------


def test_ohne_namen_zeigt_der_kreis_das_personensymbol_und_fuehrt_zu_mein_profil():
    client, _ = _client(username="ohne.name", first_name="", last_name="")

    for circle in _circles(_tree(client.get("/"))):
        avatar = _one(_all(circle, lambda e: "a-avatar" in _classes(e)))
        assert _all(avatar, lambda e: e.name == "svg"), "Personensymbol fehlt"
        assert _attr(circle, "href") == PROFILE


# ---------- Szenario 8: kein eigener Punkt in der Navigation ----------


@pytest.mark.parametrize("address", ["/", PROFILE])
def test_kein_eigener_punkt_mein_profil_in_der_navigation(address):
    client, _ = _client()
    root = _tree(client.get(address))

    navs = _by_tag(root, "nav", aria_label="Hauptnavigation")
    assert len(navs) == 2, "Navigation in der Seitenleiste und im Menü am Handy erwartet"
    for nav in navs:
        assert "Mein Profil" not in _text(nav)
        assert PROFILE not in [_attr(link, "href") for link in _by_tag(nav, "a")]


# ---------- Szenario 9: Login- und Fehlerseiten ohne Kreis ----------


def test_login_seite_hat_keinen_kreis():
    root = _tree(Client().get("/anmelden/"))

    assert not _all(root, lambda e: "a-profil" in _classes(e))


def test_fehlerseite_hat_keinen_kreis(settings):
    settings.ROOT_URLCONF = "tests.urls"
    erika, _ = _client()
    client = Client(raise_request_exception=False)
    client.cookies = erika.cookies

    root = _tree(client.get("/test/1/"))

    assert not _all(root, lambda e: "a-profil" in _classes(e))
