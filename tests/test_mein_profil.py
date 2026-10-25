"""Tests für „Mein Profil“ zum Ansehen (#96, PER-01, ORG-05; EP-01, EP-02, EP-05).

Die Nummern verweisen auf Sebastians Szenarien vom 25.10.2026 (Kommentar „Szenarien
(25.10.2026)“ in #96). Was nur ein echter Browser zeigen kann (Handy, Tastatur, axe), prüft
der Rauchtest in rauchtests/test_rauchtest.py. Alle Namen sind erfunden; die Einheiten stammen
aus `build_org()` in tests/test_rollen.py.
"""

import re

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from roles.models import Role
from tests.keycloak_fake import login
from tests.query_limit import assert_queries_do_not_grow
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_rechte_ohne_seite import every_attempt, snapshot
from tests.test_rollen import BY, build_org, give, person, unit
from units.models import Unit

pytestmark = pytest.mark.django_db

R = Role.Kind
U = Unit.Kind
User = get_user_model()

ADDRESS = "/profil/"
HINT_ACCOUNT = (
    "Name und Mail kommen aus deinem DPV-Konto und lassen sich hier nicht ändern. "
    "Änderungen dort erscheinen hier nach deiner nächsten Anmeldung."
)
HINT_NAME = "Ergänze deinen Namen in deinem DPV-Konto und melde dich danach neu an."
HINT_NO_ORG_BOLD = "Du bist noch keiner Organisation zugeordnet."
HINT_NO_ORG = (
    f"{HINT_NO_ORG_BOLD} Wende dich an die Leitung deiner Gruppe oder deines Stammes, damit sie dich aufnimmt."
)
NOT_GIVEN = "nicht angegeben"


@pytest.fixture
def org():
    """Die Einheiten aus tests/test_rollen.py; Erika und Max haben Mail und noch keine Rolle."""
    o = build_org()
    for user, mail in ((o.erika, "erika.testfrau@example.org"), (o.max, "max.testmann@example.org")):
        user.email = mail
        user.save()
    return o


def open_profile(user, address: str = ADDRESS, method: str = "get", data=None, htmx: bool = False, client=None):
    if client is None:
        client = Client()
        client.force_login(user)
    headers = {"HX-Request": "true"} if htmx else {}
    return getattr(client, method)(address, data or {}, headers=headers)


def page(user, **kwargs):
    response = open_profile(user, **kwargs)
    assert response.status_code == 200, response.status_code
    return _tree(response)


def main(root):
    return _one(_by_tag(root, "main"))


def details(root) -> dict[str, str]:
    """Die Angaben als „Beschriftung → Wert“, so wie sie auf der Seite stehen."""
    box = _one(_all(root, lambda e: e.name == "dl" and "a-angaben" in _classes(e)))
    labels = [_visible_text(e) for e in _by_tag(box, "dt")]
    values = [_visible_text(e) for e in _by_tag(box, "dd")]
    assert len(labels) == len(values)
    return dict(zip(labels, values, strict=True))


def role_rows(root) -> list[tuple[str, str]]:
    """Jede Zeile unter „Organisation und Rollen“ als (Rolle · Organisation, Weg darunter)."""
    lists = _all(root, lambda e: e.name == "ul" and "a-rollen" in _classes(e))
    if not lists:
        return []
    rows = []
    for item in _by_tag(_one(lists), "li"):
        line = _one(_all(item, lambda e: "a-rolle" in _classes(e)))
        way = _all(item, lambda e: "a-weg" in _classes(e))
        rows.append((_visible_text(line), _visible_text(way[0]) if way else ""))
    return rows


def text(root) -> str:
    return re.sub(r"\s+", " ", _visible_text(main(root)))


# Szenario 1: Erika sieht ihre Angaben


@pytest.mark.rechtematrix("EP-01", "EP-02")
def test_erika_sieht_vorname_nachname_benutzername_und_mail(org):
    root = page(org.erika)

    assert details(root) == {
        "Vorname": "Erika",
        "Nachname": "Testfrau",
        "Benutzername": "erika.testfrau",
        "Mail": "erika.testfrau@example.org",
    }
    assert _visible_text(_one(_by_tag(root, "h1"))) == "Mein Profil"


def test_hinweis_zum_dpv_konto_ohne_link(org):
    root = page(org.erika)

    assert HINT_ACCOUNT in text(root)
    hint = _one(_all(main(root), lambda e: e.name == "p" and HINT_ACCOUNT in re.sub(r"\s+", " ", _visible_text(e))))
    assert _by_tag(hint, "a") == []
    links = [_attr(a, "href") or "" for a in _by_tag(main(root), "a")]
    assert not [href for href in links if "realms" in href or "account" in href], links


def test_auf_der_seite_laesst_sich_nichts_bearbeiten(org):
    content = main(page(org.erika))

    assert _by_tag(content, "form") == []
    assert [e.name for e in _all(content, lambda e: e.name in ("input", "textarea", "select", "button"))] == []


# Szenario 2: Ein Name fehlt


def test_fehlender_nachname_hinweis_wie_auf_der_startseite_und_nicht_angegeben(org):
    org.max.last_name = ""
    org.max.save()

    root = page(org.max)

    assert HINT_NAME in text(root)
    assert details(root)["Nachname"] == NOT_GIVEN
    assert details(root)["Vorname"] == "Max"
    marked = _one(_all(root, lambda e: e.name == "dd" and _visible_text(e) == NOT_GIVEN))
    assert "a-leer" in _classes(marked)


def test_fehlender_vorname_hinweis_und_nicht_angegeben(org):
    org.max.first_name = ""
    org.max.save()

    root = page(org.max)

    assert HINT_NAME in text(root)
    assert details(root)["Vorname"] == NOT_GIVEN


def test_vollstaendiger_name_kein_hinweis_zum_ergaenzen(org):
    root = page(org.erika)

    assert HINT_NAME not in text(root)
    assert NOT_GIVEN not in text(root)


# Szenario 3: Erst die Mitgliedschaft, dann die Rollen, mit dem Weg nach oben ohne den Verband


@pytest.mark.rechtematrix("EP-01", "EP-02")
def test_mitgliedschaft_zuerst_dann_rollen_mit_weg_nach_oben(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.EVENT_TEAM, org.dpv)

    assert role_rows(page(org.erika)) == [
        ("Mitglied · Sippe Falken", "Pfadfinderbund Boreas › Walhall"),
        ("Gruppenleitung · Meute Wölfe", "Pfadfinderbund Boreas › Walhall"),
        ("Stammesleitung · Walhall", "Pfadfinderbund Boreas"),
        ("DPV-Veranstaltungsteam · DPV", ""),
    ]


# Szenario 4: Reihenfolge von klein nach groß, dieselbe Rolle nach dem Alphabet


def test_reihenfolge_der_rollen_von_klein_nach_gross(org):
    # Absichtlich in anderer Reihenfolge vergeben, als die Seite sie zeigt.
    give(org.erika, R.ADMIN)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)
    give(org.erika, R.EVENT_TEAM, org.dpv)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.GROUP_LEAD, org.falken)

    rows = [line for line, _way in role_rows(page(org.erika))]

    assert rows == [
        "Mitglied · Pfadfinderbund Boreas",  # entstanden mit der ersten Leitungsrolle (ROL-01)
        "Gruppenleitung · Meute Wölfe",
        "Gruppenleitung · Sippe Falken",
        "Stammesleitung · Walhall",
        "Bundesleitung · Pfadfinderbund Boreas",
        "Verbandsleitung · DPV",
        "DPV-Veranstaltungsteam · DPV",
        "Admin",
    ]


def test_ringleitung_steht_zwischen_stammes_und_bundesleitung(org):
    lena = person("lena.leuchtturm", "Lena", "Leuchtturm")
    give(lena, R.MEMBER, org.mosaik)
    give(lena, R.ASSOCIATION_LEAD, org.mosaik)
    give(lena, R.RING_LEAD, org.kueste)
    give(lena, R.TROOP_LEAD, org.leuchtturm)

    assert role_rows(page(lena)) == [
        ("Mitglied · DPBM Mosaik", ""),
        ("Stammesleitung · Leuchtturm", "DPBM Mosaik › Küste"),
        ("Ringleitung · Küste", "DPBM Mosaik"),
        ("Bundesleitung · DPBM Mosaik", ""),
    ]


# Szenario 5: Bund mit Ringen


def test_bund_mit_ringen_zeigt_den_ring_im_weg(org):
    lena = person("lena.leuchtturm", "Lena", "Leuchtturm")
    give(lena, R.MEMBER, org.leuchtturm)
    give(lena, R.GROUP_LEAD, org.moewen)

    assert role_rows(page(lena)) == [
        ("Mitglied · Leuchtturm", "DPBM Mosaik › Küste"),
        ("Gruppenleitung · Meute Möwen", "DPBM Mosaik › Küste › Leuchtturm"),
    ]


# Szenario 6: Admin hängt an keiner Organisation


def test_admin_steht_ohne_organisation_und_ohne_weg(org):
    give(org.max, R.ADMIN)

    root = page(org.max)

    assert role_rows(root) == [("Admin", "")]
    assert HINT_NO_ORG_BOLD not in text(root)


# Szenario 7: Ohne Zuordnung


def test_ohne_mitgliedschaft_und_rolle_steht_der_hinweis(org):
    root = page(org.max)

    assert role_rows(root) == []
    assert HINT_NO_ORG in text(root)
    bold = _one(_all(main(root), lambda e: e.name == "strong" and _visible_text(e) == HINT_NO_ORG_BOLD))
    assert bold is not None


@pytest.mark.parametrize("kind", [R.FEDERATION_LEAD, R.EVENT_TEAM, R.ADMIN])
def test_nur_rolle_im_verband_oder_admin_ohne_mitgliedschaft_kein_hinweis(org, kind):
    give(org.max, kind, None if kind == R.ADMIN else org.dpv)

    root = page(org.max)

    assert HINT_NO_ORG_BOLD not in text(root)
    assert len(role_rows(root)) == 1


def test_mit_mitgliedschaft_kein_hinweis(org):
    give(org.max, R.MEMBER, org.adler)

    root = page(org.max)

    assert HINT_NO_ORG_BOLD not in text(root)
    assert role_rows(root) == [("Mitglied · Sippe Adler", "Pfadfinderbund Boreas › Zugvögel")]


# Szenario 8: Änderungen erscheinen beim nächsten Aufruf, ohne neue Anmeldung


def test_geaenderte_rolle_erscheint_beim_naechsten_aufruf_ohne_neue_anmeldung(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    client = Client()
    client.force_login(org.erika)
    assert len(role_rows(_tree(client.get(ADDRESS)))) == 2

    Role.objects.get(user=org.erika, kind=R.GROUP_LEAD).delete(by=BY)
    membership = Role.objects.get(user=org.erika, kind=R.MEMBER)
    membership.unit = org.woelfe
    membership.save(by=BY)

    assert role_rows(_tree(client.get(ADDRESS))) == [("Mitglied · Meute Wölfe", "Pfadfinderbund Boreas › Walhall")]


def test_umbenannte_organisation_erscheint_beim_naechsten_aufruf(org):
    give(org.erika, R.MEMBER, org.falken)
    client = Client()
    client.force_login(org.erika)
    client.get(ADDRESS)

    org.walhall.name = "Walhall Nord"
    org.walhall.save(by=BY)

    assert role_rows(_tree(client.get(ADDRESS))) == [("Mitglied · Sippe Falken", "Pfadfinderbund Boreas › Walhall Nord")]


# Szenario 9: Wortwahl „Organisation“, nie „Einheit“


def test_ueberschriften_der_seite(org):
    root = page(org.erika)

    assert [_visible_text(h) for h in _by_tag(main(root), "h1")] == ["Mein Profil"]
    assert [_visible_text(h) for h in _by_tag(main(root), "h2")] == ["Deine Angaben", "Organisation und Rollen"]


def test_nirgends_das_wort_einheit(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ADMIN)

    for user in (org.erika, org.max):
        response = open_profile(user)
        assert "einheit" not in response.content.decode().lower()


# Szenario 10: Kein fremdes Profil, auf keinem Weg (EP-02)


@pytest.mark.rechtematrix("EP-02", "EP-01")
@pytest.mark.parametrize("htmx", [False, True])
@pytest.mark.parametrize("method", ["get", "post"])
def test_angehaengte_kennung_zeigt_trotzdem_nur_das_eigene_profil(org, method, htmx):
    leader = person("wanda.walhall", "Wanda", "Walhall")
    give(leader, R.TROOP_LEAD, org.walhall)
    give(org.max, R.MEMBER, org.falken)
    foreign = {
        "person": org.max.key, "key": org.max.key, "user": org.max.pk, "user_id": org.max.pk,
        "id": org.max.pk, "pk": org.max.pk, "username": org.max.username, "email": org.max.email,
    }

    response = open_profile(leader, method=method, data=foreign, htmx=htmx)

    assert response.status_code == 200
    content = response.content.decode()
    assert "wanda.walhall" in content
    for trace in ("Testmann", "max.testmann"):
        assert trace not in content


@pytest.mark.rechtematrix("EP-02")
def test_adresse_mit_kennung_gibt_es_nicht(org):
    leader = person("wanda.walhall", "Wanda", "Walhall")
    give(leader, R.TROOP_LEAD, org.walhall)
    give(org.max, R.MEMBER, org.falken)

    for address in (f"/profil/{org.max.key}/", f"/profil/{org.max.pk}/", f"/profil/{org.max.username}/"):
        for htmx in (False, True):
            response = open_profile(leader, address=address, htmx=htmx)
            assert response.status_code == 404, address
            assert "max.testmann" not in response.content.decode()


@pytest.mark.rechtematrix("EP-02")
def test_admin_sieht_ueber_mein_profil_nur_sich_selbst(org):
    give(org.erika, R.ADMIN)

    content = open_profile(org.erika, data={"person": org.max.pk, "username": org.max.username}).content.decode()

    assert "erika.testfrau@example.org" in content
    assert "max.testmann" not in content


# EP-05: Name, Benutzername und Mail lassen sich im Tool nicht ändern


@pytest.mark.rechtematrix("EP-05")
def test_formular_an_die_seite_aendert_nichts(org):
    give(org.erika, R.TROOP_LEAD, org.walhall)
    before = snapshot(User, "pk", "username", "first_name", "last_name", "email")
    changed = {"first_name": "Gekapert", "last_name": "Gekapert", "username": "gekapert", "email": "g@example.org"}

    for htmx in (False, True):
        for target in (org.erika, org.max):
            open_profile(org.erika, method="post", data={**changed, "user": target.pk}, htmx=htmx)

    assert snapshot(User, "pk", "username", "first_name", "last_name", "email") == before


@pytest.mark.rechtematrix("EP-05")
def test_keine_adresse_aendert_name_benutzername_oder_mail(org):
    """Jede Adresse, als Mitglied, Leitung, Verbandsleitung, Admin, ohne Zuordnung und mit vielen Rollen."""
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)
    give(org.erika, R.ADMIN)
    give(org.max, R.MEMBER, org.falken)
    lead = person("zora.zugvogel", "Zora", "Zugvogel")
    give(lead, R.TROOP_LEAD, org.zugvoegel)
    federation_lead = person("vera.verband", "Vera", "Verband")
    give(federation_lead, R.FEDERATION_LEAD, org.dpv)
    admin = person("ada.admin", "Ada", "Admin")
    give(admin, R.ADMIN)
    without = person("otto.ohne", "Otto", "Ohne")
    org.everyone = [org.max, lead, federation_lead, admin, without, org.erika]
    before = snapshot(User, "pk", "username", "first_name", "last_name", "email")

    list(every_attempt(org))

    assert snapshot(User, "pk", "username", "first_name", "last_name", "email") == before


@pytest.mark.rechtematrix("EP-05")
def test_geaenderter_name_und_mail_erscheinen_nach_der_naechsten_anmeldung(client, keycloak):
    """Gegenprobe zu EP-05: Der vorgesehene Weg ist das DPV-Konto, übernommen beim Login."""
    login(client)
    client.post("/abmelden/")
    keycloak.person["family_name"] = "Probe"
    keycloak.person["email"] = "erika.neu@example.org"

    login(client)

    shown = details(_tree(client.get(ADDRESS)))
    assert shown["Nachname"] == "Probe"
    assert shown["Mail"] == "erika.neu@example.org"


# Szenario 11: Ohne Login zur Anmeldung


def test_ohne_login_geht_es_zur_anmeldung():
    for htmx in (False, True):
        headers = {"HX-Request": "true"} if htmx else {}
        response = Client().get(ADDRESS, headers=headers)
        assert response.status_code == 302
        assert response["Location"].startswith("/anmelden/")


# Szenario 12: Startseite ohne den Kasten „Dein Konto“


def test_startseite_ohne_kasten_dein_konto(org):
    client = Client()
    client.force_login(org.erika)

    content = client.get("/").content.decode()

    assert "Dein Konto" not in content
    assert "erika.testfrau@example.org" not in content
    assert "Hallo Erika!" in content


def test_startseite_behaelt_den_hinweis_zum_namen(org):
    org.max.last_name = ""
    org.max.save()
    client = Client()
    client.force_login(org.max)

    assert HINT_NAME in client.get("/").content.decode()


# Szenario 14 und ORG-05: Aufbau der Seite; Abfragen wachsen nicht mit der Zahl der Rollen


def test_seite_traegt_ihren_namen_im_titel(org):
    assert "<title>Mein Profil · DPV Anmeldetool</title>" in open_profile(org.erika).content.decode()


def test_abfragen_wachsen_nicht_mit_der_zahl_der_rollen(org):
    """CONTRIBUTING.md, Abschnitt 5: Jede Rolle zeigt ihren Weg nach oben, ohne eigene Abfragen."""
    give(org.erika, R.MEMBER, org.mosaik)
    client = Client()
    client.force_login(org.erika)

    def create_role(number: int) -> None:
        troop = unit(U.TROOP, f"Stamm {number}", org.kueste)
        group = unit(U.GROUP, f"Gruppe {number}", troop)
        give(org.erika, R.GROUP_LEAD, group)

    assert_queries_do_not_grow(create_role, lambda: open_profile(org.erika, client=client))


def test_bausteine_angaben_und_rollen_stehen_auf_der_musterseite(org):
    """docs/gestaltung.md: Neue Bausteine kommen zuerst auf die Musterseite."""
    client = Client()
    client.force_login(org.erika)
    root = _tree(client.get("/muster/"))

    assert _all(root, lambda e: e.name == "dl" and "a-angaben" in _classes(e))
    assert _all(root, lambda e: e.name == "ul" and "a-rollen" in _classes(e))
    assert _all(root, lambda e: "a-leer" in _classes(e) and _visible_text(e) == NOT_GIVEN)
