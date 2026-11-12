"""Tests für die Seite „Organisation“: Gliederung und Seite je Organisation, nur Anzeige (#189, Teil 1 von #93).

Die Nummern A1 bis A23 und AV1 bis AV9 verweisen auf Sebastians Szenarien vom 27.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/189#issuecomment-6441094033).
Personen und Einheiten wie dort, gebaut aus der Fixture in `tests/test_rechtepruefung.py`;
Fahrtennamen und Mails sind erfunden. Geprüft wird die Antwort, wie sie beim Browser ankommt:
was sichtbar ist, was anklickbar ist und was eine Adresse ohne Recht antwortet.
"""

import hashlib
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from roles.models import Role
from tests import test_rechtepruefung
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _sidebar, _text, _tree, _visible_text
from tests.test_nicht_gefunden import MISSING, NO_ACCESS_TEXT, answer, assert_like_missing, with_missing_keys
from tests.test_rechtepruefung import lead, member, remove
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
pytestmark = pytest.mark.django_db
ADDRESS = "/organisation/"

# Fahrtennamen wie im Zielbild; wer hier fehlt, hat keinen.
SCOUT_NAMES = {
    "wanda.walhall": "Wirbelwind",
    "willi.walhall": "Wiesel",
    "bruno.bund": "Brummbär",
    "fiete.falke": "Funke",
    "zora.zugvogel": "Zimt",
    "mona.mosaik": "Möwe",
    "kai.kueste": "Kompass",
    "lars.leuchtturm": "Laterne",
    "mia.moewe": "Muschel",
}


@pytest.fixture
def org(base_org):
    """Die Personen aus tests/test_rechtepruefung.py, dazu Willi, Max (Admin), Fahrtennamen und Mails."""
    org = base_org
    org.willi = lead("willi.walhall", R.TROOP_LEAD, org.walhall)
    org.max = person("max.admin", "Max", "Admin")
    give(org.max, R.ADMIN)
    users = get_user_model().objects.all()
    for user in users:
        user.scout_name = SCOUT_NAMES.get(user.username, "")
        user.email = f"{user.username}@example.org"
        user.save()
    for name in vars(org):
        value = getattr(org, name)
        if isinstance(value, get_user_model()):
            value.refresh_from_db()
    return org


# Die Grundlage der Fixture oben: die Fixture „org“ aus tests/test_rechtepruefung.py unter eigenem Namen.
base_org = test_rechtepruefung.org

def client_for(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def unit_address(entry: Unit) -> str:
    return f"{ADDRESS}{entry.key}/"


def lock(user) -> None:
    """Sperrt ein Konto im Tool (Entscheidung vom 25.10.2026); es kann sich dann nicht mehr anmelden."""
    user.is_active = False
    user.save()


def unlock(user) -> None:
    user.is_active = True
    user.save()


# ---------- Was beim Browser ankommt ----------


def page_tree(user, address: str = ADDRESS):
    return _tree(client_for(user).get(address))


def nav_labels(root) -> list[str]:
    return [_visible_text(link) for link in _all(root, lambda e: "a-navlink" in _classes(e))]


def outline_of(root):
    """Die Gliederung: aside mit der Überschrift „Gliederung“."""
    return _one(_all(root, lambda e: "a-gliederung" in _classes(e)))


def nodes(root) -> dict[str, dict]:
    """Jede Organisation der Gliederung: Adresse (oder None), Marke, Zeile der Leitungen, ob zugeklappt."""
    found = {}
    for node in _all(outline_of(root), lambda e: "a-knoten" in _classes(e)):
        name = _text(_one(_all(node, lambda e: "a-knoten-name" in _classes(e))))
        marks = _all(node, lambda e: "a-kennmarke" in _classes(e))
        leads = _all(node, lambda e: "a-knoten-leitung" in _classes(e))
        found[name] = {
            "href": _attr(node, "href") if node.name == "a" else None,
            "mark": _visible_text(marks[0]) if marks else "",
            "leads": _text(leads[0]) if leads else "",
        }
    for details in _all(outline_of(root), lambda e: e.name == "details"):
        for node in _all(details, lambda e: "a-knoten" in _classes(e)):
            found[_text(_one(_all(node, lambda e: "a-knoten-name" in _classes(e))))]["folded"] = True
    for entry in found.values():
        entry.setdefault("folded", False)
    return found


def folds(root) -> list[str]:
    """Die Beschriftungen der zugeklappten Teile, z. B. „1 weitere ohne Zugriff“."""
    return [_text(_one(_by_tag(details, "summary"))) for details in _all(outline_of(root), lambda e: e.name == "details")]


def unit_page(root):
    return _one(_all(root, lambda e: "a-orga-seite" in _classes(e)))


def header(root) -> dict:
    head = _one(_all(unit_page(root), lambda e: "a-orga-kopf" in _classes(e)))
    marks = _all(head, lambda e: "a-kennmarke" in _classes(e))
    path = _one(_all(head, lambda e: "a-pfad" in _classes(e)))
    return {
        "name": _text(_one(_all(head, lambda e: "a-orga-name" in _classes(e)))),
        "kind": _text(_one(_all(head, lambda e: "a-unterzeile" in _classes(e)))),
        "mark": _visible_text(marks[0]) if marks else "",
        "path": [(_text(link), _attr(link, "href")) for link in _by_tag(path, "a")],
        "path_text": _visible_text(path),
    }


def section(root, heading_id: str):
    found = _by_tag(unit_page(root), "section", aria_labelledby=heading_id)
    return found[0] if found else None


def leads_on_page(root) -> list[dict]:
    """Die Einträge unter „Leitungen“: sichtbarer Text, Mail (oder None) und ob „gesperrt“ dabeisteht."""
    found = []
    for entry in _all(section(root, "h-leitungen"), lambda e: "a-leitung" in _classes(e)):
        mails = _all(entry, lambda e: "a-leitung-mail" in _classes(e))
        marks = [_visible_text(mark) for mark in _all(entry, lambda e: "a-kennmarke" in _classes(e))]
        found.append({
            "text": _visible_text(entry),
            "name": _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e)))),
            "mail": _text(mails[0]) if mails else None,
            "locked": "gesperrt" in marks,
        })
    return found


def leads_notice(root) -> str:
    notices = _all(section(root, "h-leitungen"), lambda e: "a-meldung" in _classes(e))
    return _visible_text(_one(notices)) if notices else ""


def children_on_page(root) -> dict[str, str | None]:
    """Die Organisationen darunter: Name und Adresse (oder None, wenn nicht anklickbar)."""
    below = section(root, "h-darunter")
    found = {}
    for tile in _all(below, lambda e: "a-orgakachel" in _classes(e)):
        name = _one(_all(tile, lambda e: "a-rollenorg" in _classes(e)))
        found[_text(name)] = _attr(name, "href") if name.name == "a" else None
        assert ("ist-ohne-zugriff" in _classes(tile)) == (name.name != "a")
    return found


def below_text(root) -> str:
    return _visible_text(section(root, "h-darunter"))


def leads_text(root) -> str:
    return _visible_text(section(root, "h-leitungen"))


# ---------- A1, AV1: wer den Menüpunkt sieht ----------


@pytest.mark.rechtematrix("EH-08", "EH-09")
def test_a1_jede_leitung_von_gruppe_bis_bund_sieht_den_menuepunkt_und_die_gliederung(org):
    leads = [
        org.falken_leitung, org.woelfe_leitung, org.walhall_leitung, org.willi, org.zugvoegel_leitung,
        org.adler_leitung, org.bundesleitung, org.moewen_leitung, org.leuchtturm_leitung, org.kueste_leitung,
        org.nord_leitung, org.mosaik_leitung,
    ]
    for user in leads:
        start = page_tree(user, "/")
        assert "Organisation" in nav_labels(start), user.username
        response = client_for(user).get(ADDRESS)
        assert response.status_code == 200, user.username
        assert outline_of(_tree(response))


def test_a1_der_menuepunkt_fuehrt_zur_gliederung_und_ist_dort_hervorgehoben(org):
    root = _sidebar(page_tree(org.walhall_leitung, ADDRESS))
    link = _one([e for e in _all(root, lambda e: "a-navlink" in _classes(e)) if "Organisation" in _visible_text(e)])

    assert _attr(link, "href") == ADDRESS
    assert _attr(link, "aria-current") == "page"
    on_unit_page = _sidebar(page_tree(org.walhall_leitung, unit_address(org.falken)))
    link = [e for e in _all(on_unit_page, lambda e: "a-navlink" in _classes(e)) if "Organisation" in _visible_text(e)]
    assert _attr(_one(link), "aria-current") == "page"


@pytest.mark.rechtematrix("EH-09", "EH-07", "EH-08")
def test_av1_mitglieder_konten_ohne_zuordnung_und_team_sehen_keinen_menuepunkt(org):
    """Die Verbandsleitung hat den Menüpunkt seit #94 (EH-08, Seite „Verband“); geprüft in tests/test_verband.py.

    Admins haben ihn seit #92, um einen Support-Zugang zu starten (EH-06, EH-08); geprüft in
    tests/test_support_zugang.py.
    """
    others = [
        org.falke, org.walhall_mitglied, org.boreas_mitglied, org.moewe, org.sturmvogel_mitglied,
        org.ohne, org.team,
    ]
    for user in others:
        assert "Organisation" not in nav_labels(page_tree(user, "/")), user.username
        for method in ("get", "post"):
            response = getattr(client_for(user), method)(ADDRESS)
            assert response.status_code == 403, (user.username, method)
            assert NO_ACCESS_TEXT in response.content.decode()


@pytest.mark.rechtematrix("EH-09", "EH-07")
def test_av1_ohne_menuepunkt_auch_keine_seite_einer_organisation(org):
    """Mitglieder haben eine Kette nach oben, sehen die Seiten darauf aber noch nicht (#134)."""
    assert_like_missing(org.falke, unit_address(org.falken))
    assert_like_missing(org.boreas_mitglied, unit_address(org.boreas))
    assert_like_missing(org.ohne, unit_address(org.boreas))
    assert_like_missing(org.verbandsleitung, unit_address(org.boreas))
    assert_like_missing(org.team, unit_address(org.walhall))
    # Admins öffnen die Seite seit #92, aber nur mit dem Kopf (S1); geprüft in tests/test_support_zugang.py.


# ---------- A2 bis A7: Gliederung ----------


@pytest.mark.rechtematrix("EH-01", "EH-03", "RO-01", "RO-03", "RO-04")
def test_a2_wanda_sieht_ganz_boreas_mit_leitungen_auf_ihrer_kette_und_in_ihrem_bereich(org):
    shown = nodes(page_tree(org.walhall_leitung))

    assert set(shown) == {"Pfadfinderbund Boreas", "Walhall", "Sippe Falken", "Meute Wölfe", "Zugvögel", "Sippe Adler"}
    assert shown["Pfadfinderbund Boreas"] == {
        "href": unit_address(org.boreas), "mark": "nur lesen", "leads": "Bundesleitung: Brummbär", "folded": False}
    assert shown["Walhall"] == {
        "href": unit_address(org.walhall), "mark": "",
        "leads": "Stammesleitung: Wirbelwind, Wiesel", "folded": False}
    assert shown["Sippe Falken"] == {
        "href": unit_address(org.falken), "mark": "", "leads": "Gruppenleitung: Funke", "folded": False}
    assert shown["Meute Wölfe"]["href"] == unit_address(org.woelfe)
    assert shown["Meute Wölfe"]["leads"] == "Gruppenleitung: Wim Wolf"
    for name in ("Zugvögel", "Sippe Adler"):
        assert shown[name] == {"href": None, "mark": "", "leads": "", "folded": True}


@pytest.mark.rechtematrix("RO-04", "RO-03")
def test_a2_bei_den_zugvoegeln_steht_nur_der_name_ohne_leitungen(org):
    """Verbotener Nachbar zu RO-01 und RO-03: Zora und Ada erscheinen nirgends."""
    root = page_tree(org.walhall_leitung)

    text = _text(outline_of(root))
    for name in ("Zimt", "Zora", "Ada"):
        assert name not in text


@pytest.mark.rechtematrix("EH-01", "RO-01")
def test_a3_fiete_sieht_dieselbe_gliederung_mit_den_leitungen_ueber_sich(org):
    root = page_tree(org.falken_leitung)
    shown = nodes(root)

    assert set(shown) == {"Pfadfinderbund Boreas", "Walhall", "Sippe Falken", "Meute Wölfe", "Zugvögel", "Sippe Adler"}
    assert shown["Sippe Falken"] == {
        "href": unit_address(org.falken), "mark": "", "leads": "Gruppenleitung: Funke",
        "folded": False}
    assert shown["Walhall"] == {
        "href": unit_address(org.walhall), "mark": "nur lesen", "leads": "Stammesleitung: Wirbelwind, Wiesel",
        "folded": False}
    assert shown["Pfadfinderbund Boreas"]["href"] == unit_address(org.boreas)
    assert shown["Pfadfinderbund Boreas"]["mark"] == "nur lesen"
    for name in ("Meute Wölfe", "Zugvögel", "Sippe Adler"):
        assert shown[name] == {"href": None, "mark": "", "leads": "", "folded": True}


@pytest.mark.rechtematrix("RO-04", "RO-01")
def test_a3_fiete_sieht_die_leitung_der_woelfe_nicht(org):
    """Verbotener Nachbar zu RO-01: die andere Gruppe im selben Stamm."""
    assert "Wim" not in _text(outline_of(page_tree(org.falken_leitung)))


def test_a4_bruno_sieht_ganz_boreas_mit_allen_leitungen_alles_anklickbar(org):
    shown = nodes(page_tree(org.bundesleitung))

    assert set(shown) == {"Pfadfinderbund Boreas", "Walhall", "Sippe Falken", "Meute Wölfe", "Zugvögel", "Sippe Adler"}
    assert all(entry["href"] and entry["leads"] and not entry["folded"] for entry in shown.values())
    assert shown["Pfadfinderbund Boreas"]["mark"] == ""
    assert shown["Zugvögel"]["leads"] == "Stammesleitung: Zimt"
    assert folds(page_tree(org.bundesleitung)) == []


def test_a5_kai_sieht_mosaik_mit_ringen(org):
    root = page_tree(org.kueste_leitung)
    shown = nodes(root)

    assert set(shown) == {"DPBM Mosaik", "Küste", "Leuchtturm", "Meute Möwen", "Nord", "Sturmvogel"}
    assert shown["DPBM Mosaik"] == {
        "href": unit_address(org.mosaik), "mark": "nur lesen", "leads": "Bundesleitung: Möwe", "folded": False}
    assert shown["Küste"]["mark"] == ""
    assert shown["Küste"]["href"] == unit_address(org.kueste)
    assert shown["Leuchtturm"]["leads"] == "Stammesleitung: Laterne"
    assert shown["Meute Möwen"]["href"] == unit_address(org.moewen)
    for name in ("Nord", "Sturmvogel"):
        assert shown[name] == {"href": None, "mark": "", "leads": "", "folded": True}
    assert "Nele" not in _text(root)


def test_a6_zwei_rollen_zaehlen_zusammen_und_enden_einzeln(org):
    give(org.falken_leitung, R.GROUP_LEAD, org.woelfe)
    client = client_for(org.falken_leitung)

    shown = nodes(_tree(client.get(ADDRESS)))
    for name in ("Sippe Falken", "Meute Wölfe"):
        assert shown[name]["href"] == unit_address(getattr(org, "falken" if name == "Sippe Falken" else "woelfe"))
        assert shown[name]["leads"].startswith("Gruppenleitung: ")
    remove(org.falken_leitung, R.GROUP_LEAD, org.woelfe)

    shown = nodes(_tree(client.get(ADDRESS)))
    assert shown["Meute Wölfe"] == {"href": None, "mark": "", "leads": "", "folded": True}
    assert shown["Sippe Falken"]["href"] == unit_address(org.falken)


def test_a7_ohne_gruppenleitung_springt_die_stammesleitung_ein_nicht_der_bund(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    for user in (org.walhall_leitung, org.willi):
        assert nodes(page_tree(user))["Sippe Falken"]["mark"] == "Du springst ein"
    assert nodes(page_tree(org.bundesleitung))["Sippe Falken"]["mark"] == ""


def test_a7_ohne_stammesleitung_springt_die_bundesleitung_fuer_beide_ein(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove(org.willi, R.TROOP_LEAD, org.walhall)

    shown = nodes(page_tree(org.bundesleitung))

    assert shown["Sippe Falken"]["mark"] == "Du springst ein"
    assert shown["Walhall"]["mark"] == "Du springst ein"
    assert shown["Meute Wölfe"]["mark"] == ""


# ---------- A8 bis A12: Seite einer Organisation im eigenen Bereich ----------


@pytest.mark.rechtematrix("RO-03")
def test_a8_wanda_sieht_auf_walhall_leitungen_mit_mail_und_die_gruppen_darunter(org):
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    assert header(root)["name"] == "Walhall"
    assert header(root)["kind"] == "Stamm in Pfadfinderbund Boreas"
    assert header(root)["mark"] == ""
    assert children_on_page(root) == {"Meute Wölfe": unit_address(org.woelfe), "Sippe Falken": unit_address(org.falken)}
    shown = leads_on_page(root)
    assert [(entry["name"], entry["mail"]) for entry in shown] == [
        ("Wirbelwind", "wanda.walhall@example.org"),
        ("Wiesel", "willi.walhall@example.org"),
    ]
    assert "Wanda Walhall" in shown[0]["text"] and "Stammesleitung" in shown[0]["text"]
    assert "Willi Walhall" in shown[1]["text"] and "Stammesleitung" in shown[1]["text"]


@pytest.mark.rechtematrix("RO-03")
def test_a8_mail_als_link_zum_schreiben(org):
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    links = _all(section(root, "h-leitungen"), lambda e: "a-leitung-mail" in _classes(e))
    assert [_attr(link, "href") for link in links] == ["mailto:wanda.walhall@example.org", "mailto:willi.walhall@example.org"]


@pytest.mark.rechtematrix("RO-03")
def test_a9_wanda_sieht_bea_als_stammesleitung_ohne_mail(org):
    """Bea ist Mitglied direkt im Bund, also nicht in Wandas Bereich (PK-04)."""
    give(org.boreas_mitglied, R.TROOP_LEAD, org.walhall)

    shown = {entry["name"]: entry for entry in leads_on_page(page_tree(org.walhall_leitung, unit_address(org.walhall)))}

    assert "Bea Boreas" in shown
    assert shown["Bea Boreas"]["mail"] is None
    assert "Stammesleitung" in shown["Bea Boreas"]["text"]
    assert "bea.boreas@example.org" not in _text(page_tree(org.walhall_leitung, unit_address(org.walhall)))
    assert shown["Wiesel"]["mail"] == "willi.walhall@example.org"


def test_a10_ohne_gruppenleitung_nennt_die_seite_wer_einspringt(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    assert leads_notice(root) == (
        "Die Gruppe Sippe Falken hat keine Gruppenleitung. Bis eine benannt ist, springt die Stammesleitung von "
        "Walhall ein."
    )
    assert leads_on_page(root) == []
    assert header(root)["mark"] == "Du springst ein"


def test_a10_ohne_stammesleitung_springt_die_bundesleitung_ein(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove(org.willi, R.TROOP_LEAD, org.walhall)

    root = page_tree(org.bundesleitung, unit_address(org.falken))

    assert leads_notice(root) == (
        "Die Gruppe Sippe Falken hat keine Gruppenleitung. Bis eine benannt ist, springt die Bundesleitung von "
        "Pfadfinderbund Boreas ein."
    )


def test_a10_im_bund_mit_ringen_springt_die_ringleitung_ein(org):
    remove(org.leuchtturm_leitung, R.TROOP_LEAD, org.leuchtturm)

    root = page_tree(org.kueste_leitung, unit_address(org.leuchtturm))

    assert leads_notice(root) == (
        "Der Stamm Leuchtturm hat keine Stammesleitung. Bis eine benannt ist, springt die Ringleitung von Küste ein."
    )


def test_a10_mit_leitung_steht_kein_satz_dazu(org):
    """Gegenprobe; auch einen Hinweiskasten oben gibt es nicht (Frage 4, A23)."""
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    assert leads_notice(root) == ""
    assert _all(unit_page(root), lambda e: "a-meldung" in _classes(e)) == []
    assert _all(root, lambda e: "a-meldung" in _classes(e)) == []


def test_a11_eine_gruppe_hat_keinen_abschnitt_organisationen_darunter(org):
    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    assert section(root, "h-darunter") is None
    assert "Organisationen darunter" not in _text(unit_page(root))


def test_a11_ein_stamm_ohne_gruppen_sagt_das(org):
    neu = unit(U.TROOP, "Wolkenburg", org.boreas)

    root = page_tree(org.bundesleitung, unit_address(neu))

    # Seit #95 steht in der Überschrift der Knopf „Gruppe anlegen“; Bruno darf dort Gruppen anlegen (EH-10).
    assert below_text(root) == "Organisationen darunter Gruppe anlegen Wolkenburg hat noch keine Gruppen."
    assert children_on_page(root) == {}


def test_a11_ein_ring_ohne_staemme_sagt_das(org):
    neu = unit(U.RING, "Süd", org.mosaik)

    root = page_tree(org.mosaik_leitung, unit_address(neu))

    # Seit #95 steht dort „Stamm anlegen“: Süd hat keine Ringleitung, Mona springt ein (EH-18).
    assert below_text(root) == "Organisationen darunter Stamm anlegen Süd hat noch keine Stämme."


def test_a12_ohne_vor_und_nachnamen_steht_der_benutzername(org):
    org.willi.first_name = ""
    org.willi.last_name = ""
    org.willi.scout_name = ""
    org.willi.save()

    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    assert [entry["name"] for entry in leads_on_page(root)] == ["Wirbelwind", "willi.walhall"]
    assert nodes(root)["Walhall"]["leads"] == "Stammesleitung: Wirbelwind, willi.walhall"


def test_a12_ohne_fahrtenname_steht_der_name(org):
    root = page_tree(org.walhall_leitung, unit_address(org.woelfe))

    shown = leads_on_page(root)
    assert [entry["name"] for entry in shown] == ["Wim Wolf"]
    assert "()" not in shown[0]["text"]


# ---------- A13 bis A15: Seite über einem, nur lesen ----------


@pytest.mark.rechtematrix("RO-01", "EH-28")
def test_a13_fiete_sieht_walhall_nur_lesend(org):
    root = page_tree(org.falken_leitung, unit_address(org.walhall))

    assert header(root)["mark"] == "nur lesen"
    shown = leads_on_page(root)
    assert [entry["name"] for entry in shown] == ["Wirbelwind", "Wiesel"]
    assert all(entry["mail"] is None for entry in shown)
    assert "Wanda Walhall" in shown[0]["text"] and "Stammesleitung" in shown[0]["text"]
    assert children_on_page(root) == {"Meute Wölfe": None, "Sippe Falken": unit_address(org.falken)}


@pytest.mark.rechtematrix("EH-28")
def test_a13_die_leseseite_hat_keine_mails_knoepfe_oder_formulare(org):
    root = page_tree(org.falken_leitung, unit_address(org.walhall))

    page = unit_page(root)
    assert "@example.org" not in _text(page)
    assert _by_tag(page, "form") == []
    assert _by_tag(page, "button") == []
    assert "Personen" not in _text(page)


@pytest.mark.rechtematrix("RO-04", "RO-01")
def test_a13_fiete_sieht_auf_walhall_die_leitung_der_woelfe_nicht(org):
    """Verbotener Nachbar zu RO-01: Die Wölfe stehen nur mit Namen unter „Organisationen darunter“."""
    root = page_tree(org.falken_leitung, unit_address(org.walhall))

    assert "Wim" not in _text(unit_page(root))
    assert "Wolke" not in _text(unit_page(root))


@pytest.mark.rechtematrix("EH-28")
def test_a14_wanda_sieht_boreas_nur_lesend(org):
    root = page_tree(org.walhall_leitung, unit_address(org.boreas))

    assert header(root)["name"] == "Pfadfinderbund Boreas"
    assert header(root)["kind"] == "Bund"
    assert header(root)["mark"] == "nur lesen"
    shown = leads_on_page(root)
    assert [(entry["name"], entry["mail"]) for entry in shown] == [("Brummbär", None)]
    assert children_on_page(root) == {"Walhall": unit_address(org.walhall), "Zugvögel": None}


def test_a14_bund_ohne_bundesleitung_ohne_satz_zum_einspringen(org):
    remove(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)

    root = page_tree(org.walhall_leitung, unit_address(org.boreas))

    assert leads_notice(root) == "Der Bund Pfadfinderbund Boreas hat keine Bundesleitung."


@pytest.mark.rechtematrix("EH-28")
def test_a15_bea_oeffnet_boreas_lesend_ueber_ihre_mitgliedschaft(org):
    give(org.boreas_mitglied, R.TROOP_LEAD, org.walhall)

    root = page_tree(org.boreas_mitglied, unit_address(org.boreas))

    assert header(root)["mark"] == "nur lesen"
    assert [entry["name"] for entry in leads_on_page(root)] == ["Brummbär"]


# ---------- A16 bis A19: gesperrte Leitungen ----------


@pytest.fixture
def fritz(org):
    """Mitglied der Falken und Gruppenleitung der Wölfe: Er sieht die Falken nur lesend."""
    return lead_member("fritz.falke", org.falken, R.GROUP_LEAD, org.woelfe)


def lead_member(username: str, membership: Unit, kind: str, where: Unit):
    user = member(username, membership)
    give(user, kind, where)
    user.email = f"{username}@example.org"
    user.save()
    return user


@pytest.mark.rechtematrix("RO-21", "RO-22")
def test_a16_wer_dort_entfernen_darf_sieht_die_gesperrte_leitung(org):
    lock(org.falken_leitung)

    for user in (org.walhall_leitung, org.willi, org.bundesleitung):
        root = page_tree(user, unit_address(org.falken))
        shown = leads_on_page(root)
        assert [(entry["name"], entry["locked"]) for entry in shown] == [("Funke", True)], user.username
        assert nodes(root)["Sippe Falken"]["leads"] == "Gruppenleitung: Funke (gesperrt)"
        assert leads_notice(root) == (
            "Die Gruppe Sippe Falken hat keine Gruppenleitung. Bis eine benannt ist, springt die Stammesleitung "
            "von Walhall ein."
        )
    for user in (org.walhall_leitung, org.willi):
        assert header(page_tree(user, unit_address(org.falken)))["mark"] == "Du springst ein"
    assert header(page_tree(org.bundesleitung, unit_address(org.falken)))["mark"] == ""


@pytest.mark.rechtematrix("RO-22", "RO-21")
def test_a16_wer_die_falken_nur_lesend_sieht_erfaehrt_nichts_von_der_sperre(org, fritz):
    lock(org.falken_leitung)

    root = page_tree(fritz, unit_address(org.falken))

    assert header(root)["mark"] == "nur lesen"
    assert leads_on_page(root) == []
    for text in (_text(unit_page(root)), _text(outline_of(root))):
        assert "Funke" not in text and "Fiete" not in text and "gesperrt" not in text
    assert nodes(root)["Sippe Falken"]["leads"] == "keine Gruppenleitung"


@pytest.mark.rechtematrix("RO-22")
def test_a16_gesperrt_nicht_in_der_liste_der_leitungen_fuer_andere(org, fritz):
    """Die Liste der zentralen Rechteprüfung kennzeichnet gesperrte Leitungen nur für Verwaltende."""
    from access.rights import Rights

    lock(org.falken_leitung)

    for_fritz = {(entry["first_name"], entry["unit_name"]) for entry in Rights(fritz).leads()}
    for_wanda = {(entry["first_name"], entry["unit_name"], entry["locked"]) for entry in Rights(org.walhall_leitung).leads()}
    assert ("Fiete", "Sippe Falken") not in for_fritz
    assert ("Fiete", "Sippe Falken", True) in for_wanda
    assert ("Wanda", "Walhall", False) in for_wanda


@pytest.mark.rechtematrix("RO-21", "RO-22")
def test_a17_zweite_gruppenleitung_frida_sieht_die_sperre_niemand_springt_ein(org, fritz):
    frida = lead_member("frida.falke", org.falken, R.GROUP_LEAD, org.falken)
    lock(org.falken_leitung)

    for user in (frida, org.walhall_leitung, org.willi, org.bundesleitung):
        shown = [(entry["name"], entry["locked"]) for entry in leads_on_page(page_tree(user, unit_address(org.falken)))]
        assert shown == [("Funke", True), ("Frida Falke", False)], user.username
    assert nodes(page_tree(org.walhall_leitung))["Sippe Falken"]["mark"] == ""
    assert leads_notice(page_tree(org.walhall_leitung, unit_address(org.falken))) == ""
    assert [entry["name"] for entry in leads_on_page(page_tree(fritz, unit_address(org.falken)))] == ["Frida Falke"]


@pytest.mark.rechtematrix("RO-22", "EH-28")
def test_a17_frida_sieht_auf_der_leseseite_von_walhall_keine_sperre_in_den_kacheln(org):
    """Unabhängige Prüfung: Die Leseseite zeigt nie gesperrte Leitungen, auch nicht in „Organisationen darunter“."""
    frida = lead_member("frida.falke", org.falken, R.GROUP_LEAD, org.falken)
    lock(org.falken_leitung)

    root = page_tree(frida, unit_address(org.walhall))

    assert header(root)["mark"] == "nur lesen"
    assert "gesperrt" not in below_text(root) and "Funke" not in below_text(root)
    assert "Frida Falke" in below_text(root)
    assert "Funke (gesperrt)" in nodes(page_tree(frida, unit_address(org.falken)))["Sippe Falken"]["leads"]


@pytest.mark.rechtematrix("RO-22", "EH-03")
def test_verbandsleitung_mit_gruppenleitung_sieht_nur_ihren_bund_ohne_gesperrte_bundesleitung(org):
    """Unabhängige Prüfung: Die Liste der Verbandsleitung enthält gesperrte Bundesleitungen aller Bünde; die Seite zeigt sie nicht."""
    give(org.verbandsleitung, R.MEMBER, org.falken)
    give(org.verbandsleitung, R.GROUP_LEAD, org.falken)
    lock(org.bundesleitung)
    lock(org.mosaik_leitung)

    overview = page_tree(org.verbandsleitung)
    boreas = page_tree(org.verbandsleitung, unit_address(org.boreas))
    falken = page_tree(org.verbandsleitung, unit_address(org.falken))

    # Seit #94 öffnet „Organisation“ für die Verbandsleitung die Seite „Verband“ mit allen Bünden und
    # den gesperrten Bundesleitungen (tests/test_verband.py); Gliederung und Seiten des Bundes bleiben ohne sie.
    for root in (boreas, falken):
        text = _text(root)
        for hidden in ("Brummbär", "gesperrt", "DPBM Mosaik", "Möwe", "Mona"):
            assert hidden not in text, hidden
    assert "Organisation" in nav_labels(overview)
    assert "@example.org" not in _text(unit_page(boreas))
    assert "fiete.falke@example.org" in _text(unit_page(falken))
    assert_like_missing(org.verbandsleitung, unit_address(org.mosaik))


def test_a18_alle_darunter_gesperrt_bruno_springt_fuer_falken_und_walhall_ein(org):
    for user in (org.falken_leitung, org.walhall_leitung, org.willi):
        lock(user)

    shown = nodes(page_tree(org.bundesleitung))

    assert shown["Sippe Falken"]["mark"] == "Du springst ein"
    assert shown["Walhall"]["mark"] == "Du springst ein"
    assert shown["Meute Wölfe"]["mark"] == ""
    assert shown["Walhall"]["leads"] == "Stammesleitung: Wirbelwind (gesperrt), Wiesel (gesperrt)"


def test_a19_nach_der_sperre_ist_fiete_wieder_gruppenleitung(org):
    lock(org.falken_leitung)
    client = client_for(org.walhall_leitung)
    assert nodes(_tree(client.get(ADDRESS)))["Sippe Falken"]["mark"] == "Du springst ein"

    unlock(org.falken_leitung)

    shown = nodes(_tree(client.get(ADDRESS)))
    assert shown["Sippe Falken"] == {
        "href": unit_address(org.falken), "mark": "", "leads": "Gruppenleitung: Funke", "folded": False}


def test_a19_entfernte_rolle_bleibt_nach_der_sperre_entfernt(org):
    lock(org.falken_leitung)
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    unlock(org.falken_leitung)

    assert nodes(page_tree(org.walhall_leitung))["Sippe Falken"]["mark"] == "Du springst ein"
    assert "Funke" not in _text(outline_of(page_tree(org.walhall_leitung)))


# ---------- A20 bis A23 ----------


def test_a20_der_naechste_klick_zeigt_den_neuen_stand(org):
    client = client_for(org.walhall_leitung)
    assert nodes(_tree(client.get(unit_address(org.walhall))))["Meute Wölfe"]["mark"] == ""

    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    root = _tree(client.get(unit_address(org.woelfe)))
    assert header(root)["mark"] == "Du springst ein"
    assert leads_on_page(root) == []

    give(org.wolf, R.GROUP_LEAD, org.woelfe)
    root = _tree(client.get(unit_address(org.woelfe)))
    assert header(root)["mark"] == ""
    assert [entry["name"] for entry in leads_on_page(root)] == ["Wiebke Wolf"]


def test_a21_in_der_gliederung_nur_fahrtenname_ohne_ihn_der_name(org):
    root = page_tree(org.bundesleitung)
    shown = nodes(root)

    assert shown["Walhall"]["leads"] == "Stammesleitung: Wirbelwind, Wiesel"
    assert shown["Meute Wölfe"]["leads"] == "Gruppenleitung: Wim Wolf"
    assert "Wanda" not in _text(outline_of(root))


def test_a22_organisationen_ohne_zugriff_immer_zugeklappt_auch_eine_einzelne(org):
    root = page_tree(org.walhall_leitung)

    assert folds(root) == ["1 weitere ohne Zugriff"]
    details = _one(_all(outline_of(root), lambda e: e.name == "details"))
    assert _attr(details, "open") is None
    assert _by_tag(details, "a") == []
    assert folds(page_tree(org.falken_leitung)) == ["1 weitere ohne Zugriff", "1 weitere ohne Zugriff"]


def test_a22_mehrere_ohne_zugriff_stehen_zusammen(org):
    unit(U.TROOP, "Eulenhorst", org.boreas)

    assert folds(page_tree(org.walhall_leitung)) == ["2 weitere ohne Zugriff"]


def test_a23_die_eigene_rolle_steht_nur_bei_den_leitungen_mit_das_bist_du(org):
    """Sebastian am Vorschlag (28.10.2026): keine Marke „Deine Rolle“ in Gliederung und Kopf."""
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    assert "Deine Rolle" not in _text(root)
    shown = leads_on_page(root)
    assert "das bist du" in shown[0]["text"] and shown[0]["name"] == "Wirbelwind"
    assert "das bist du" not in shown[1]["text"]


def test_a23_im_eigenen_bereich_ohne_rolle_und_ohne_einspringen_keine_marke(org):
    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    assert header(root)["mark"] == ""
    assert header(root)["path"] == [
        ("Pfadfinderbund Boreas", unit_address(org.boreas)), ("Walhall", unit_address(org.walhall))]
    assert header(root)["kind"] == "Gruppe in Walhall"


def test_a23_die_aktuelle_organisation_ist_in_der_gliederung_hervorgehoben(org):
    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    current = [node for node in _all(outline_of(root), lambda e: "a-knoten" in _classes(e)) if _attr(node, "aria-current")]
    assert [_text(_one(_all(node, lambda e: "a-knoten-name" in _classes(e)))) for node in current] == ["Sippe Falken"]


def test_a23_die_uebersicht_zeigt_am_pc_die_eigene_organisation(org):
    """Wie im Zielbild: Neben der Gliederung steht die Seite der Organisation, die man leitet."""
    root = page_tree(org.walhall_leitung)

    assert header(root)["name"] == "Walhall"
    page = unit_page(root)
    assert "a-orga-start" in _classes(page)


def test_handy_seite_einer_organisation_hat_den_knopf_zurueck_zur_gliederung(org):
    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    back = _one(_all(root, lambda e: "a-orga-zurueck" in _classes(e)))
    assert _attr(back, "href") == ADDRESS
    assert "Gliederung" in _visible_text(back)
    assert _all(page_tree(org.walhall_leitung), lambda e: "a-orga-zurueck" in _classes(e)) == []


# ---------- AV2 bis AV9 ----------


@pytest.mark.rechtematrix("RO-04")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/")
def test_av2_fiete_erreicht_woelfe_zugvoegel_und_adler_nicht(org):
    for entry in (org.woelfe, org.zugvoegel, org.adler):
        assert_like_missing(org.falken_leitung, unit_address(entry))


@pytest.mark.rechtematrix("RO-04")
def test_av3_zora_erreicht_walhall_und_falken_nicht_aber_boreas_lesend(org):
    for entry in (org.walhall, org.falken):
        assert_like_missing(org.zugvoegel_leitung, unit_address(entry))
    assert header(page_tree(org.zugvoegel_leitung, unit_address(org.boreas)))["mark"] == "nur lesen"


@pytest.mark.rechtematrix("EH-03", "EH-01")
def test_av4_bruno_sieht_mosaik_nicht_und_erreicht_leuchtturm_nicht(org):
    root = page_tree(org.bundesleitung)

    text = _text(root)
    for name in ("DPBM Mosaik", "Küste", "Leuchtturm", "Nord", "Sturmvogel"):
        assert name not in text
    assert_like_missing(org.bundesleitung, unit_address(org.leuchtturm))
    assert_like_missing(org.bundesleitung, unit_address(org.mosaik))


@pytest.mark.rechtematrix("EH-03")
def test_av4_der_verband_erscheint_nicht(org):
    """N7: Für Leitungen endet die Kette beim Bund; der Verband hat keine Seite."""
    root = page_tree(org.bundesleitung)

    assert "DPV" not in [_text(name) for name in _all(outline_of(root), lambda e: "a-knoten-name" in _classes(e))]
    assert_like_missing(org.bundesleitung, unit_address(org.dpv))


@pytest.mark.rechtematrix("EH-28")
def test_av5_anfragen_an_die_leseseite_aendern_nichts_und_zeigen_nicht_gefunden(org):
    roles_before = set(Role.objects.values_list("user__username", "kind", "unit__name"))
    form = {"user": org.falke.key, "person": org.falke.key, "kind": R.TROOP_LEAD, "unit": org.walhall.key,
            "role": "x", "action": "benennen", "q": "Wan"}
    address = unit_address(org.walhall)

    for suffix in ("", "?vorschlaege=Wan"):
        shown = answer(client_for(org.falken_leitung).post(address + suffix, form))
        missing = answer(client_for(org.falken_leitung).post(with_missing_keys(address) + suffix, form))
        assert shown == missing
        assert shown[0] == 404
    assert set(Role.objects.values_list("user__username", "kind", "unit__name")) == roles_before


def test_av6_erfundene_verstuemmelte_oder_fremde_kennung_zeigt_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)

    for address in (f"{ADDRESS}{MISSING}/", f"{ADDRESS}{org.walhall.key[:-1]}/", f"{ADDRESS}{org.walhall.pk}/",
                    f"{ADDRESS}{org.walhall.key.upper()}/", unit_address(org.leuchtturm)):
        response = client.get(address)
        assert response.status_code == 404, address


def test_av7_mitglieder_ohne_leitungsrolle_stehen_nie_unter_leitungen(org):
    """Seit #285 steht Wilma im Abschnitt „Personen“; unter „Leitungen“ steht sie weiter nie."""
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))

    assert "Wilma" not in _text(_one(_by_tag(unit_page(root), "section", aria_labelledby="h-leitungen")))


def test_av8_die_gliederung_zeigt_nie_mails(org):
    for user in (org.bundesleitung, org.walhall_leitung, org.falken_leitung):
        for address in (ADDRESS, unit_address(org.walhall)):
            assert "@" not in _text(outline_of(page_tree(user, address)))


@pytest.mark.rechtematrix("EH-09", "EH-08")
def test_av9_wanda_verliert_ihre_rolle_beim_naechsten_klick(org):
    client = client_for(org.walhall_leitung)
    assert client.get(ADDRESS).status_code == 200

    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    assert "Organisation" not in nav_labels(_tree(client.get("/")))
    assert client.get(ADDRESS).status_code == 403
    assert_like_missing(org.walhall_leitung, unit_address(org.walhall))


# ---------- Technik ----------


def test_keine_internen_nummern_auf_den_seiten(org):
    """#156: Die Seiten nennen Organisationen nur mit ihrer Kennung."""
    for address in (ADDRESS, unit_address(org.walhall), unit_address(org.boreas)):
        content = client_for(org.walhall_leitung).get(address).content.decode()
        for entry in Unit.objects.all():
            assert f"/{entry.pk}/" not in content
            assert f'"{entry.pk}"' not in content


def test_die_liste_der_leitungen_gibt_keine_internen_nummern_heraus(org):
    from access.rights import Rights

    for entry in Rights(org.walhall_leitung).leads():
        assert not {"user_id", "unit_id", "id", "pk", "user", "unit"} & set(entry)


def test_abfragen_wachsen_nicht_mit_der_zahl_der_organisationen(org):
    """CONTRIBUTING.md, Abschnitt 5: Gliederung und Seite brauchen gleich viele Abfragen bei 1 und bei 10 Gruppen."""
    from tests.query_limit import assert_queries_do_not_grow

    for round_, address in enumerate((ADDRESS, unit_address(org.walhall))):

        def add(number: int, round_=round_) -> None:
            group = unit(U.GROUP, f"Gruppe {round_}-{number}", org.walhall)
            if number % 2:
                lead(f"gl{round_}{number}.walhall", R.GROUP_LEAD, group)

        assert_queries_do_not_grow(add, lambda address=address: client_for(org.bundesleitung).get(address))


# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "organisation.html"
CHECKSUM = "6588b56761e8906246d416edec3c60a15bd4aa2fc9f69e2b90f23c6d13ad5d2d"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Organisation", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "27.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#189"):
        assert must in section[1], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert all(mail.endswith("@example.org") for mail in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
