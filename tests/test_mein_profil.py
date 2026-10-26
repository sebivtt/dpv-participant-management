"""Tests für „Mein Profil“ zum Ansehen (#96, PER-01, ORG-05; EP-01, EP-02, EP-05) und seine Gestaltung nach Zielbild (#161).

Die Nummern verweisen auf Sebastians Szenarien vom 25.10.2026: „Szenario n“ auf die in #96,
„Szenario n zu #161“ auf die in #161, ab dem 25.10.2026 mit der „Nachklärung Kacheln“. Wo #161 Aufbau oder Texte geändert hat (Mitgliedschaft
als eigene Fläche, Rollen als Kacheln, „E-Mail-Adresse“), prüfen die Tests aus #96 den neuen
Stand. Was nur ein echter Browser zeigen kann (Handy, Tastatur, axe, Farben), prüft der
Rauchtest in rauchtests/test_rauchtest.py. Alle Namen sind erfunden; die Einheiten stammen aus
`build_org()` in tests/test_rollen.py.
"""

import hashlib
import re
from pathlib import Path

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
    "Name und E-Mail-Adresse stammen aus deinem DPV-Konto und lassen sich hier nicht ändern. "
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


def with_class(root, name: str) -> list:
    return _all(root, lambda e: name in _classes(e))


def details_box(root):
    return _one(_all(root, lambda e: e.name == "dl" and "a-felder" in _classes(e)))


def details(root) -> dict[str, str]:
    """Die Angaben als „Beschriftung → Wert“, so wie sie auf der Seite stehen."""
    box = details_box(root)
    labels = [_visible_text(e) for e in _by_tag(box, "dt")]
    values = [_visible_text(e) for e in _by_tag(box, "dd")]
    assert len(labels) == len(values)
    return dict(zip(labels, values, strict=True))


def display_name(root) -> str:
    """Der große Name in der Kopfzeile der ersten Fläche (#161)."""
    return _visible_text(_one(with_class(root, "a-anzeigename")))


def avatar(root):
    """Der Profilkreis in der Kopfzeile der ersten Fläche (#161)."""
    return _one(with_class(_one(with_class(root, "a-identitaet")), "a-avatar"))


def raw_text(element) -> str:
    """Der ganze Text eines Elements, auch was für Bildschirmleser ausgeblendet ist."""
    if isinstance(element, str):
        return element.strip()
    return "".join(raw_text(child) for child in element.children)


def symbols(element) -> list[str]:
    """Die Namen der Symbole in einem Element, z. B. ["person", "schloss"]."""
    return [(_attr(use, "href") or "").removeprefix("#i-") for use in _by_tag(element, "use")]


def _entry(box) -> tuple[str, str, str]:
    label = with_class(box, "a-rollenmarke")
    way = with_class(box, "a-weg")
    return (
        _visible_text(label[0]) if label else "",
        _visible_text(_one(with_class(box, "a-rollenorg"))),
        _visible_text(way[0]) if way else "",
    )


def membership_boxes(root) -> list:
    return with_class(main(root), "a-mitgliedschaft")


def role_tiles(root) -> list:
    lists = _all(main(root), lambda e: e.name == "ul" and "a-rollenkacheln" in _classes(e))
    return _by_tag(_one(lists), "li") if lists else []


def entries(root) -> list[tuple[str, str, str]]:
    """Was unter „Organisation und Rollen“ steht, als (klein, groß, Weg darunter) (#161).

    Zuerst die Fläche der Mitgliedschaft („Mitgliedschaft“, Organisation, Weg), dann jede
    Kachel (Rolle, Organisation, Weg oder fester Satz).
    """
    return [_entry(box) for box in membership_boxes(root)] + [_entry(tile) for tile in role_tiles(root)]


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
        "E-Mail-Adresse": "erika.testfrau@example.org",
    }
    assert _visible_text(_one(_by_tag(root, "h1"))) == "Mein Profil"


def test_kopfzeile_zeigt_kreis_mit_anfangsbuchstaben_und_namen(org):
    """Szenario 1 zu #161."""
    root = page(org.erika)

    assert display_name(root) == "Erika Testfrau"
    assert raw_text(avatar(root)) == "E"
    assert _attr(avatar(root), "aria-hidden") == "true"  # der Name steht gleich daneben


def test_kopfzeile_kreis_mit_grossem_anfangsbuchstaben_auch_bei_kleinem_vornamen(org):
    """Szenario 1 zu #161, wie der Profilkreis in der Seitenleiste (unabhängige Prüfung zu #161)."""
    org.erika.first_name = "erika"
    org.erika.save()

    root = page(org.erika)

    assert raw_text(avatar(root)) == "E"
    assert display_name(root) == "erika Testfrau"


def test_angaben_als_gesperrte_felder_mit_symbol_und_schloss(org):
    """Szenario 1 zu #161: jedes Feld mit eigenem Symbol und einem Schloss, für Vorleseprogramme stumm."""
    box = details_box(page(org.erika))

    fields = [dd for dd in _by_tag(box, "dd")]
    assert [symbols(dd) for dd in fields] == [
        ["person", "schloss"], ["person", "schloss"], ["at", "schloss"], ["mail", "schloss"],
    ]
    assert all(_attr(svg, "aria-hidden") == "true" for svg in _by_tag(box, "svg"))


def test_hinweis_zum_dpv_konto_ohne_link(org):
    root = page(org.erika)

    assert HINT_ACCOUNT in text(root)
    hint = _one(_all(main(root), lambda e: e.name == "p" and HINT_ACCOUNT in re.sub(r"\s+", " ", _visible_text(e))))
    assert _by_tag(hint, "a") == []
    links = [_attr(a, "href") or "" for a in _by_tag(main(root), "a")]
    assert not [href for href in links if "realms" in href or "account" in href], links


def test_hinweis_zum_dpv_konto_in_blauer_flaeche_mit_schloss(org):
    """Szenario 1 zu #161; seit #165 als Informationsmeldung (zart blau, Schloss)."""
    box = _one(with_class(main(page(org.erika)), "ist-info"))

    assert re.sub(r"\s+", " ", _visible_text(box)) == HINT_ACCOUNT
    assert symbols(box) == ["schloss"]


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
    # Szenario 2 zu #161: Die Kopfzeile zeigt, was da ist.
    assert display_name(root) == "Max"
    assert raw_text(avatar(root)) == "M"


def test_fehlender_vorname_hinweis_und_nicht_angegeben(org):
    org.max.first_name = ""
    org.max.save()

    root = page(org.max)

    assert HINT_NAME in text(root)
    assert details(root)["Vorname"] == NOT_GIVEN
    # Szenario 3 zu #161: Personensymbol im Kreis, daneben der Nachname.
    assert display_name(root) == "Testmann"
    assert raw_text(avatar(root)) == ""
    assert symbols(avatar(root)) == ["person"]


def test_ohne_vor_und_nachname_steht_der_benutzername_in_der_kopfzeile(org):
    """Szenario 4 zu #161."""
    org.max.first_name = ""
    org.max.last_name = ""
    org.max.save()

    root = page(org.max)

    assert display_name(root) == "max.testmann"
    assert symbols(avatar(root)) == ["person"]
    assert details(root)["Vorname"] == details(root)["Nachname"] == NOT_GIVEN
    assert HINT_NAME in text(root)


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

    assert entries(page(org.erika)) == [
        ("Mitgliedschaft", "Sippe Falken", "Pfadfinderbund Boreas › Walhall"),
        ("Gruppenleitung", "Meute Wölfe", "Pfadfinderbund Boreas › Walhall"),
        ("Stammesleitung", "Walhall", "Pfadfinderbund Boreas"),
        ("DPV-Veranstaltungsteam", "DPV", "Veranstaltungen des Verbands"),  # Nachklärung Kacheln, Szenario 5
    ]


def test_mitgliedschaft_in_eigener_flaeche_rollen_als_kacheln(org):
    """Szenario 5 zu #161: die Mitgliedschaft in einer eigenen Fläche, jede Rolle als Kachel in einer Liste."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.EVENT_TEAM, org.dpv)

    root = page(org.erika)

    assert len(membership_boxes(root)) == 1
    assert len(role_tiles(root)) == 3
    assert not _all(_one(membership_boxes(root)), lambda e: e.name == "li")


# Szenario 4: Reihenfolge von klein nach groß, dieselbe Rolle nach dem Alphabet


def test_reihenfolge_der_rollen_von_klein_nach_gross(org):
    # Absichtlich in anderer Reihenfolge vergeben, als die Seite sie zeigt.
    give(org.erika, R.ADMIN)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)
    give(org.erika, R.EVENT_TEAM, org.dpv)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)

    rows = [(label, name) for label, name, _way in entries(page(org.erika))]

    assert rows == [
        ("Mitgliedschaft", "Pfadfinderbund Boreas"),  # entstanden mit der ersten Leitungsrolle (ROL-01)
        ("Gruppenleitung", "Meute Wölfe"),
        ("Gruppenleitung", "Sippe Falken"),
        ("Stammesleitung", "Walhall"),
        ("Bundesleitung", "Pfadfinderbund Boreas"),
        ("Verbandsleitung", "DPV"),
        ("DPV-Veranstaltungsteam", "DPV"),
        ("Admin", "DPV Anmeldetool"),
    ]


def test_ringleitung_steht_zwischen_stammes_und_bundesleitung(org):
    lena = person("lena.leuchtturm", "Lena", "Leuchtturm")
    give(lena, R.MEMBER, org.mosaik)
    give(lena, R.ASSOCIATION_LEAD, org.mosaik)
    give(lena, R.RING_LEAD, org.kueste)
    give(lena, R.TROOP_LEAD, org.leuchtturm)

    assert entries(page(lena)) == [
        ("Mitgliedschaft", "DPBM Mosaik", ""),
        ("Stammesleitung", "Leuchtturm", "DPBM Mosaik › Küste"),
        ("Ringleitung", "Küste", "DPBM Mosaik"),
        ("Bundesleitung", "DPBM Mosaik", ""),
    ]


def test_umlaut_am_anfang_steht_im_alphabet_beim_grundbuchstaben(org):
    """Szenario 4: „im Alphabet“ heißt Ä bei A, nicht hinter Z (unabhängige Prüfung zu #96)."""
    give(org.erika, R.MEMBER, org.walhall)
    for name in ("Meute Zander", "Meute Ährenfeld", "Meute Biber"):
        give(org.erika, R.GROUP_LEAD, unit(U.GROUP, name, org.walhall))

    rows = [name for _label, name, _way in entries(page(org.erika))]

    assert rows[1:] == ["Meute Ährenfeld", "Meute Biber", "Meute Zander"]


# Szenario 5: Bund mit Ringen


def test_bund_mit_ringen_zeigt_den_ring_im_weg(org):
    lena = person("lena.leuchtturm", "Lena", "Leuchtturm")
    give(lena, R.MEMBER, org.leuchtturm)
    give(lena, R.GROUP_LEAD, org.moewen)

    assert entries(page(lena)) == [
        ("Mitgliedschaft", "Leuchtturm", "DPBM Mosaik › Küste"),
        ("Gruppenleitung", "Meute Möwen", "DPBM Mosaik › Küste › Leuchtturm"),
    ]


# Szenario 6: Admin hängt an keiner Organisation


def test_admin_steht_ohne_organisation_und_ohne_weg(org):
    give(org.max, R.ADMIN)

    root = page(org.max)

    # Szenario 8 zu #161, Nachklärung Kacheln: wie die anderen Kacheln, mit festen Texten
    assert entries(root) == [("Admin", "DPV Anmeldetool", "Verwaltung des ganzen Tools")]
    assert membership_boxes(root) == []
    assert HINT_NO_ORG_BOLD not in text(root)


def test_verbandsleitung_mit_festem_satz(org):
    """Szenario 8a zu #161, Nachklärung Kacheln."""
    give(org.max, R.FEDERATION_LEAD, org.dpv)

    assert entries(page(org.max)) == [("Verbandsleitung", "DPV", "Leitung des Verbands")]


# Szenario 7: Ohne Zuordnung


def test_ohne_mitgliedschaft_und_rolle_steht_der_hinweis(org):
    root = page(org.max)

    assert entries(root) == []
    assert role_tiles(root) == [] and membership_boxes(root) == []
    assert HINT_NO_ORG in text(root)
    bold = _one(_all(main(root), lambda e: e.name == "strong" and _visible_text(e) == HINT_NO_ORG_BOLD))
    assert bold is not None


@pytest.mark.parametrize(
    ("kind", "tile"),
    [
        (R.FEDERATION_LEAD, ("Verbandsleitung", "DPV", "Leitung des Verbands")),
        (R.EVENT_TEAM, ("DPV-Veranstaltungsteam", "DPV", "Veranstaltungen des Verbands")),
        (R.ADMIN, ("Admin", "DPV Anmeldetool", "Verwaltung des ganzen Tools")),
    ],
)
def test_nur_rolle_im_verband_oder_admin_ohne_mitgliedschaft_kein_hinweis(org, kind, tile):
    give(org.max, kind, None if kind == R.ADMIN else org.dpv)

    root = page(org.max)

    assert HINT_NO_ORG_BOLD not in text(root)
    # Szenario 9 zu #161 (Nachklärung Kacheln): nur die Kachel mit festem Satz, keine Fläche für die Mitgliedschaft
    assert entries(root) == [tile]
    assert membership_boxes(root) == []


def test_mit_mitgliedschaft_kein_hinweis(org):
    give(org.max, R.MEMBER, org.adler)

    root = page(org.max)

    assert HINT_NO_ORG_BOLD not in text(root)
    assert entries(root) == [("Mitgliedschaft", "Sippe Adler", "Pfadfinderbund Boreas › Zugvögel")]
    assert role_tiles(root) == []


# Szenario 8: Änderungen erscheinen beim nächsten Aufruf, ohne neue Anmeldung


def test_geaenderte_rolle_erscheint_beim_naechsten_aufruf_ohne_neue_anmeldung(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    client = Client()
    client.force_login(org.erika)
    assert len(entries(_tree(client.get(ADDRESS)))) == 2

    Role.objects.get(user=org.erika, kind=R.GROUP_LEAD).delete(by=BY)
    membership = Role.objects.get(user=org.erika, kind=R.MEMBER)
    membership.unit = org.woelfe
    membership.save(by=BY)

    assert entries(_tree(client.get(ADDRESS))) == [("Mitgliedschaft", "Meute Wölfe", "Pfadfinderbund Boreas › Walhall")]


def test_umbenannte_organisation_erscheint_beim_naechsten_aufruf(org):
    give(org.erika, R.MEMBER, org.falken)
    client = Client()
    client.force_login(org.erika)
    client.get(ADDRESS)

    org.walhall.name = "Walhall Nord"
    org.walhall.save(by=BY)

    assert entries(_tree(client.get(ADDRESS))) == [("Mitgliedschaft", "Sippe Falken", "Pfadfinderbund Boreas › Walhall Nord")]


# Szenario 9: Wortwahl „Organisation“, nie „Einheit“; Szenarien 1 und 12 zu #161: „Deine Angaben“ nur für Vorleseprogramme


def test_ueberschriften_der_seite(org):
    root = page(org.erika)

    assert [_visible_text(h) for h in _by_tag(main(root), "h1")] == ["Mein Profil"]
    assert [raw_text(h) for h in _by_tag(main(root), "h2")] == ["Deine Angaben", "Organisation und Rollen"]
    assert [_visible_text(h) for h in _by_tag(main(root), "h2")] == ["", "Organisation und Rollen"]


def test_organisation_und_rollen_mit_symbol_in_der_ueberschrift(org):
    """Szenario 12 zu #161: Die sichtbare Überschrift der zweiten Fläche trägt ein Symbol, wie im Zielbild."""
    heading = _one(_by_tag(main(page(org.erika)), "h2", id="h-rollen"))
    head = _one(_all(main(page(org.erika)), lambda e: "a-flaeche-kopf" in _classes(e) and _by_tag(e, "h2", id="h-rollen")))

    assert _visible_text(heading) == "Organisation und Rollen"
    assert symbols(head) == ["organisation"]


def test_nirgends_das_wort_einheit(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ADMIN)

    for user in (org.erika, org.max):
        response = open_profile(user)
        assert "einheit" not in response.content.decode().lower()


# Szenario 13 zu #161: Teile des Zielbilds ohne Daten fehlen ganz, ohne leere Platzhalter. Den
# Fahrtennamen hat das Tool seit #111; seine Tests stehen in tests/test_fahrtenname.py.

ONLY_IN_TARGET_IMAGE = (
    "Profil freigeben", "Freigabe", "Geburtsdatum", "Wohnadresse", "Gesundheit", "Allergien",
    "Unverträglichkeiten", "Medikamente", "Organisation öffnen", "Austritt", "Austreten", "Profilfoto",
    "Verantwortung auf Verbandsebene", "Verbandsweite Funktion",  # Nachklärung Kacheln, Szenario 13
)


@pytest.mark.parametrize("roles", [False, True])
def test_keine_teile_des_zielbilds_ohne_daten(org, roles):
    if roles:
        give(org.erika, R.MEMBER, org.falken)
        give(org.erika, R.TROOP_LEAD, org.walhall)
        give(org.erika, R.ADMIN)

    root = page(org.erika)
    content = raw_text(main(root)) + " ".join(_attr(e, "aria-label") or "" for e in _all(main(root), lambda e: True))

    assert [word for word in ONLY_IN_TARGET_IMAGE if word.lower() in content.lower()] == []
    shown = [*_by_tag(details_box(root), "dd"), *_all(main(root), lambda e: "a-rollenorg" in _classes(e))]
    assert all(_visible_text(e) for e in shown), "leerer Platzhalter"


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

    root = _tree(client.get(ADDRESS))
    shown = details(root)
    assert shown["Nachname"] == "Probe"
    assert shown["E-Mail-Adresse"] == "erika.neu@example.org"
    assert display_name(root) == "Erika Probe"  # Szenario 15 zu #161: auch in der Kopfzeile


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
    """docs/gestaltung.md: Neue Bausteine kommen zuerst auf die Musterseite (Szenario 18 zu #161)."""
    client = Client()
    client.force_login(org.erika)
    root = _tree(client.get("/muster/"))

    for name in ("a-identitaet", "a-anzeigename", "a-meldung", "a-flaeche-kopf", "a-mitgliedschaft"):
        assert with_class(root, name), name
    assert _all(root, lambda e: e.name == "dl" and "a-felder" in _classes(e))
    assert _all(root, lambda e: e.name == "ul" and "a-rollenkacheln" in _classes(e))
    assert _all(root, lambda e: "a-leer" in _classes(e) and _visible_text(e) == NOT_GIVEN)
    # Auch eine Kachel mit festem Satz statt Weg steht dort als Beispiel (Nachklärung Kacheln).
    tiles = [_entry(tile) for tile in _by_tag(_one(_all(root, lambda e: "a-rollenkacheln" in _classes(e))), "li")]
    assert ("Admin", "DPV Anmeldetool", "Verwaltung des ganzen Tools") in tiles


# Szenario 18 zu #161: Sebastians Zielbild liegt unverändert im Repo

TARGET_IMAGES = Path(__file__).resolve().parent.parent / "docs" / "zielbilder"


def test_zielbild_liegt_unveraendert_mit_liste_im_repo():
    image = TARGET_IMAGES / "mein-profil.html"
    readme = (TARGET_IMAGES / "README.md").read_text()

    checksum = hashlib.sha256(image.read_bytes()).hexdigest()
    assert checksum in readme, "Das Zielbild ist nicht mehr die Fassung, die die Liste nennt."
    section = readme.split("## Mein Profil", 1)[1]
    for must in ("25.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#161"):
        assert must in section, must


def test_zielbild_laedt_nichts_von_fremden_servern_und_nennt_nur_erfundene_adressen():
    content = (TARGET_IMAGES / "mein-profil.html").read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    mails = set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
    assert mails and all(mail.endswith("@example.org") for mail in mails), mails
