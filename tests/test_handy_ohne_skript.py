"""Am Handy ohne Skript: „Menü“ springt ans Seitenende, dort Navigation, Profilkreis und „Abmelden“ (#281, NFA-01).

Die Kennungen E1 bis G2 verweisen auf den Kommentar „Szenarien (06.11.2026)“ im Issue #281. Hier
steht, was die Seite vom Server mitbringt; was nur ein Browser zeigt (Sprung, Skript lädt nicht oder
spät, Tastatur), prüft rauchtests/test_handy_ohne_skript.py. Alle Personen sind erfunden.
"""

import pytest
from django.test import Client

from roles.models import Role
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_rollen import BY, give, person, unit
from units.models import Unit

pytestmark = pytest.mark.django_db

R = Role.Kind
U = Unit.Kind


@pytest.fixture
def walhall():
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    return unit(U.TROOP, "Walhall", boreas)


def _page(user, address="/"):
    client = Client()
    client.force_login(user)
    return _tree(client.get(address))


def _bottom(root):
    """Die Liste am Seitenende."""
    return _one(_by_tag(root, "section", id="menue-unten"))


def _labels(container) -> list[str]:
    return [_visible_text(link) for link in _by_tag(_one(_by_tag(container, "nav")), "a")]


def _drawer(root):
    return _one(_by_tag(root, "dialog", id="menue"))


# E1, E2: „Menü“ ist ohne Skript ein Sprung ans Seitenende; dort dasselbe wie im Menü
def test_e1_menue_springt_ohne_skript_ans_seitenende_zur_liste():
    erika = person("erika.testfrau", "Erika", "Testfrau")
    root = _page(erika)

    bar = _one(_all(root, lambda e: e.name == "header" and "a-topbar" in _classes(e)))
    jump = _one(_by_tag(bar, "a", href="#menue-unten"))
    assert _visible_text(jump) == "Menü"
    # Der Knopf, der mit Skript das Menü öffnet, wartet versteckt auf das Skript.
    button = _one(_by_tag(bar, "button", id="menue-auf"))
    assert _attr(button, "hidden") is not None
    # Die Liste steht im Inhaltsbereich nach dem Inhalt und vor dem Fußbereich.
    main = _one(_by_tag(root, "main"))
    parts = [child for child in main.children if not isinstance(child, str)]
    names = [_attr(part, "id") or (_classes(part) or [part.name])[0] for part in parts]
    assert names.index("a-main-inhalt") < names.index("menue-unten") < names.index("a-fuss"), names


def test_e1_e2_liste_mit_navigation_profilkreis_und_abmelden_wie_im_menue():
    erika = person("erika.testfrau", "Erika", "Testfrau")
    root = _page(erika)

    bottom = _bottom(root)
    assert _labels(bottom) == _labels(_drawer(root)) == ["Startseite"]
    profile = _one(_all(bottom, lambda e: e.name == "a" and "a-profil" in _classes(e)))
    assert _attr(profile, "href") == "/profil/"
    assert "Erika" in _visible_text(profile)
    form = _one(_by_tag(bottom, "form", action="/abmelden/"))
    assert _attr(form, "method") == "post"
    assert "Abmelden" in _text(_one(_by_tag(form, "button")))


@pytest.mark.rechtematrix("EH-08")
def test_e1_leitung_findet_organisation_auch_in_der_liste(walhall):
    erika = person("erika.testfrau", "Erika", "Testfrau")
    give(erika, R.TROOP_LEAD, walhall)

    root = _page(erika)

    # Seit #100 steht für alle mit Zuordnung auch „Veranstaltungen“ in der Liste.
    assert _labels(_bottom(root)) == _labels(_drawer(root)) == ["Startseite", "Organisation", "Veranstaltungen"]
    link = [a for a in _by_tag(_bottom(root), "a") if _visible_text(a) == "Organisation"]
    assert _attr(_one(link), "href") == "/organisation/"


# V1: ohne Leitungsrolle fehlt „Organisation“ auch am Seitenende; die Adresse bleibt gesperrt
@pytest.mark.rechtematrix("EH-09")
def test_v1_ohne_leitung_fehlt_organisation_auch_in_der_liste(walhall):
    max_ = person("max.mustermann", "Max", "Mustermann")
    give(max_, R.MEMBER, walhall)

    root = _page(max_)

    assert _labels(_bottom(root)) == ["Startseite", "Veranstaltungen"]
    client = Client()
    client.force_login(max_)
    assert client.get("/organisation/").status_code == 403


# G2: Endet die letzte Leitungsrolle, fehlt der Punkt ab dem nächsten Klick
@pytest.mark.rechtematrix("EH-08", "EH-09")
def test_g2_rolle_endet_punkt_fehlt_ab_dem_naechsten_klick(walhall):
    erika = person("erika.testfrau", "Erika", "Testfrau")
    lead = give(erika, R.TROOP_LEAD, walhall)
    client = Client()
    client.force_login(erika)
    assert "Organisation" in _labels(_bottom(_tree(client.get("/"))))

    lead.delete(by=BY)

    # Die Mitgliedschaft bleibt; mit ihr „Veranstaltungen“ (#100).
    assert _labels(_bottom(_tree(client.get("/")))) == ["Startseite", "Veranstaltungen"]


# Unverändert: Login- und Fehlerseiten haben kein Menü und deshalb auch keine Liste
def test_login_und_fehlerseiten_ohne_liste():
    for address in ("/anmelden/", "/gibt-es-nicht/"):
        content = Client().get(address).content.decode()
        assert 'id="menue-unten"' not in content, address
        assert "#menue-unten" not in content, address
