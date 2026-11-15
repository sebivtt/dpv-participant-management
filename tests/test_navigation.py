"""Tests für die Hervorhebung des aktuellen Navigationspunkts (#266, Projektprüfung BF-020).

Die Kennungen S1 bis S5, G1, G2, V1, GF1 und GF2 verweisen auf Sebastians Szenarien vom 14.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/266#issuecomment-6876369080). Personen
und Organisationen wie in `tests/test_organisation.py`, dazu die verwaltete Person Paul Probe; alle
Namen sind erfunden.

Hervorgehoben wird nach dem Anfang der Adresse (technische Wahl in der Klärung vom 14.11.2026): Jede
Adresse unter `/organisation/` hebt „Organisation“ hervor, unter `/veranstaltungen/` „Veranstaltungen“,
unter `/profil/` den Profilkreis. GF1 geht dafür jede Adresse des Tools durch, auch solche, die später
dazukommen; die Tests mit echten Seiten zeigen, dass die Seiten es so beim Browser ankommen lassen.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from django.test import RequestFactory
from django.urls import resolve, reverse

from core.navigation import navigation
from persons.models import DisplayedLead
from roles.models import Role
from tests import test_organisation
from tests.test_gestaltung import _all, _attr, _classes, _tree, _visible_text
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_rundumtest import ALL, _example_address
from tests.test_veranstaltungen import event_of
from tests.test_verwaltete_personen import managed

R = Role.Kind

ORGANISATION = "Organisation"
EVENTS = "Veranstaltungen"
START = "Startseite"
# Der Profilkreis ist kein Punkt der Navigation; hier steht er unter dem Namen der Seite, die er öffnet.
PROFILE = "Mein Profil"

# Die Bereiche: Anfang der Adresse und was dort hervorgehoben ist (Text von #266, „Erwartetes Verhalten“).
AREAS = {"/organisation/": ORGANISATION, "/veranstaltungen/": EVENTS, "/profil/": PROFILE}


def highlighted(root) -> set[str]:
    """Was die Seite als aktuell kennzeichnet: Navigationspunkte nach Beschriftung, der Profilkreis als „Mein Profil“.

    Navigation und Profilkreis stehen mehrfach auf der Seite (Seitenleiste, Menü am Handy, Liste am
    Seitenende, #281); jede Stelle muss an allen ihren Orten gleich gekennzeichnet sein.
    """
    places: dict[str, set[bool]] = {}
    for link in _all(root, lambda e: "a-navlink" in _classes(e)):
        places.setdefault(_visible_text(link), set()).add(_attr(link, "aria-current") == "page")
    for circle in _all(root, lambda e: e.name == "a" and "a-profil" in _classes(e)):
        places.setdefault(PROFILE, set()).add(_attr(circle, "aria-current") == "page")
    assert all(len(marks) == 1 for marks in places.values()), places
    return {place for place, marks in places.items() if True in marks}


def get(user, address: str) -> set[str]:
    response = client_for(user).get(address)
    assert response.status_code == 200, address
    return highlighted(_tree(response))


# Die Fixtures aus tests/test_organisation.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_organisation.base_org
org_266 = test_organisation.org


@pytest.fixture
def org(org_266):
    """Die Personen aus tests/test_organisation.py, dazu Paul Probe in Walhall mit angezeigter Stammesleitung."""
    org = org_266
    org.paul = managed("Paul", "Probe", org.walhall, born=date(2012, 9, 3))
    org.paul_lead = DisplayedLead.objects.create(person=org.paul, kind=R.TROOP_LEAD, unit=org.walhall)
    return org


# ---------- S1: „… benennen“ mit Suche ----------


@pytest.mark.django_db
@pytest.mark.rechtematrix("EH-08")
def test_s1_wanda_benennt_und_sucht_und_organisation_bleibt_hervorgehoben(org):
    address = f"{unit_address(org.walhall)}benennen/"
    assert get(org.walhall_leitung, address) == {ORGANISATION}

    response = client_for(org.walhall_leitung).post(f"{address}suchen/", {"suche": "wilma.walhall"})

    assert response.status_code == 200
    assert highlighted(_tree(response)) == {ORGANISATION}


# ---------- S2: jeder andere Dialog einer Organisation ----------


def walhall_dialogs(org) -> dict[str, str]:
    """Die Dialoge von Stamm Walhall, die Wanda öffnen darf, je mit ihrer Adresse."""
    walhall = unit_address(org.walhall)
    willi = Role.objects.get(user=org.willi, kind=R.TROOP_LEAD, unit=org.walhall)
    paul = f"{walhall}verwaltete-person/{org.paul.key}/"
    return {
        "entfernen": f"{walhall}entfernen/{willi.key}/",
        "angezeigte Rolle entfernen": f"{walhall}entfernen-anzeige/{org.paul_lead.key}/",
        "Person aufnehmen": f"{walhall}person-aufnehmen/",
        "aufnehmen": f"{walhall}aufnehmen/",
        "austragen": f"{walhall}austragen/{org.walhall_mitglied.key}/",
        "verschieben": f"{walhall}verschieben/{org.walhall_mitglied.key}/",
        "anlegen": f"{walhall}anlegen/",
        "bearbeiten": f"{walhall}bearbeiten/",
        "verwaltete Person anlegen": f"{walhall}verwaltete-person/anlegen/",
        "verwaltete Person bearbeiten": f"{paul}bearbeiten/",
        "verwaltete Person verschieben": f"{paul}verschieben/",
        "verwaltete Person austragen": f"{paul}austragen/",
        "verwaltete Person löschen": f"{paul}loeschen/",
    }


@pytest.mark.django_db
@pytest.mark.rechtematrix("EH-08")
def test_s2_wanda_oeffnet_jeden_dialog_von_walhall_und_organisation_ist_hervorgehoben(org):
    for name, address in walhall_dialogs(org).items():
        assert get(org.walhall_leitung, address) == {ORGANISATION}, name

    # Die Suche in „aufnehmen“ zeigt den Dialog mit Treffern unter der Adresse der Suche.
    response = client_for(org.walhall_leitung).post(
        f"{unit_address(org.walhall)}aufnehmen/suchen/", {"suche": "otto.ohne"}
    )
    assert response.status_code == 200
    assert highlighted(_tree(response)) == {ORGANISATION}
    # Den Support-Zugang startet nur ein Admin (#92); Max öffnet ihn an Walhall.
    assert get(org.max, f"{unit_address(org.walhall)}support-zugang/") == {ORGANISATION}


# ---------- S3: die Dialoge des Verbands, wie heute ----------


@pytest.mark.django_db
@pytest.mark.rechtematrix("EH-08")
def test_s3_vera_oeffnet_die_dialoge_des_verbands_und_organisation_ist_hervorgehoben(org):
    federation = f"/organisation/verband/{org.dpv.key}/"
    tom = Role.objects.get(user=org.team, kind=R.EVENT_TEAM, unit=org.dpv)
    for address in (
        f"{federation}verbandsleitung/benennen/",
        f"{federation}team/benennen/",
        f"/organisation/verband/bund/{org.boreas.key}/benennen/",
        f"/organisation/verband/entfernen/{tom.key}/",
    ):
        assert get(org.verbandsleitung, address) == {ORGANISATION}, address


# ---------- S4: „Austreten“ und „Rolle abgeben“ auf „Mein Profil“ ----------


@pytest.mark.django_db
@pytest.mark.rechtematrix("EP-06", "RO-20")
def test_s4_austreten_und_rolle_abgeben_heben_den_profilkreis_hervor(org):
    assert get(org.falke, "/profil/austreten/") == {PROFILE}
    assert get(org.team, "/profil/team-abgeben/") == {PROFILE}


# ---------- S5: „bearbeiten“ einer Veranstaltung, wie heute ----------


@pytest.mark.django_db
@pytest.mark.rechtematrix("VA-02")
def test_s5_finn_bearbeitet_seine_veranstaltung_und_veranstaltungen_ist_hervorgehoben(org):
    probelager = event_of(org.falke)

    assert get(org.falke, f"/veranstaltungen/{probelager.key}/bearbeiten/") == {EVENTS}


# ---------- G1, G2: höchstens eine Stelle ----------


@pytest.mark.django_db
def test_g1_hoechstens_eine_stelle_ist_hervorgehoben(org):
    assert get(org.walhall_leitung, "/") == {START}
    assert get(org.walhall_leitung, "/profil/") == {PROFILE}
    assert get(org.walhall_leitung, "/organisation/") == {ORGANISATION}
    assert get(org.walhall_leitung, unit_address(org.walhall)) == {ORGANISATION}


@pytest.mark.django_db
@pytest.mark.bausteinkatalog
def test_g2_im_bausteinkatalog_ist_nichts_hervorgehoben(org):
    assert get(org.walhall_leitung, "/bausteine/") == set()


# ---------- V1: wer „Organisation“ nicht sieht, sieht es auch auf „Austreten“ nicht ----------


@pytest.mark.django_db
@pytest.mark.rechtematrix("EH-09")
def test_v1_finn_sieht_organisation_auch_auf_austreten_nicht(org):
    root = page_tree(org.falke, "/profil/austreten/")
    labels = [_visible_text(link) for link in _all(root, lambda e: "a-navlink" in _classes(e))]

    assert ORGANISATION not in labels
    for address in (f"{unit_address(org.walhall)}benennen/", f"{unit_address(org.falken)}anlegen/"):
        assert client_for(org.falke).get(address).status_code in (403, 404), address


# ---------- GF2: die Fehlerseiten bleiben ohne Navigation ----------


@pytest.mark.django_db
def test_gf2_nicht_gefunden_und_kein_zugriff_unter_organisation_zeigen_keine_navigation(org):
    missing = client_for(org.walhall_leitung).get(f"/organisation/{'a' * 20}/benennen/")
    no_access = client_for(org.falke).get("/organisation/")

    for response in (missing, no_access):
        assert response.status_code in (403, 404)
        content = response.content.decode()
        assert "a-navlink" not in content and "a-profil" not in content


# ---------- GF1: jede Adresse des Tools, auch spätere ----------


def expected(address: str) -> set[str]:
    """Was auf einer Adresse hervorgehoben sein muss: der Punkt ihres Bereichs, auf der Startseite „Startseite“."""
    if address == reverse("start"):
        return {START}
    return {place for start, place in AREAS.items() if address.startswith(start)}


def marked_for(address: str) -> set[str]:
    """Was die Navigation auf `address` hervorhebt, für eine Person, die jeden Navigationspunkt sieht."""
    request = RequestFactory().get(address)
    request.user = SimpleNamespace(is_authenticated=True)
    request.rights = SimpleNamespace(sees_menu=lambda: True, sees_events=lambda: True)
    request.resolver_match = resolve(address)
    context = navigation(request)
    labels = {str(item["label"]) for item in context["nav_items"] if item["active"]}
    return labels | ({PROFILE} if context["profile_active"] else set())


def test_gf1_es_gibt_adressen_in_jedem_bereich():
    addresses = [_example_address(pattern) for pattern, _entry in ALL]

    for start in AREAS:
        assert len([address for address in addresses if address.startswith(start)]) >= 2, start


@pytest.mark.parametrize(("pattern", "entry"), ALL, ids=[pattern or "/" for pattern, _entry in ALL])
def test_gf1_jede_adresse_hebt_genau_ihren_bereich_hervor(pattern, entry):
    address = _example_address(pattern)

    assert marked_for(address) == expected(address), address
