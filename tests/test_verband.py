"""Tests für die Verbandsleitung: Seite „Verband“, Benennen und Entfernen ohne Personendaten (#94).

Die Nummern V1 bis V13, VV1 bis VV10 und VG1 bis VG4 verweisen auf Sebastians Szenarien vom
28.10.2026 (https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6475718734).
Personen wie in den Tests zu #189 bis #191 (Vera Verbandsleitung, Tom DPV-Veranstaltungsteam,
Bruno Bundesleitung Boreas, Mona Bundesleitung Mosaik, Otto ohne Zuordnung, Max Admin), dazu
Viktor als zweite Verbandsleitung. Alle Daten sind erfunden. Geprüft wird, was beim Browser
ankommt, und was danach in der Datenbank steht.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.http import Http404

from access.rights import Rights
from accounts.models import AccountSearch
from roles.models import Role, RoleChange
from tests import test_benennen, test_organisation
from tests.test_benennen import _one_after_the_other, dialog_of, hits, notices, roles_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import ADDRESS, NO_ACCESS_TEXT, client_for, header, lock, nav_labels, page_tree, unit_address
from tests.test_rechtepruefung import lead
from tests.test_rollen import BY, build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

base_org = test_organisation.base_org
org_189 = test_organisation.org
org_190 = test_benennen.org

LIMIT_TEXT = "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in {} noch einmal."
ELSEWHERE_TEXT = ("Diese Person gehört schon zu einer anderen Organisation und kann hier keine Leitung werden. Sie kann "
                  "bei ihrer bisherigen Leitung den Wechsel veranlassen.")
NOT_YOURSELF_TEXT = "Dir selbst kannst du keine Rolle geben. Das kann eine andere Verbandsleitung."


@pytest.fixture
def org(org_190):
    """Die Personen aus #190, dazu Viktor als zweite Verbandsleitung, angemeldet wie alle anderen."""
    org_190.viktor = lead("viktor.verband", R.FEDERATION_LEAD, org_190.dpv)
    User.objects.filter(pk=org_190.viktor.pk).update(last_login=org_190.ohne.last_login)
    org_190.viktor.refresh_from_db()
    return org_190


# ---------- Adressen und Helfer ----------

def team_address(org) -> str:
    """Dialog „Teammitglied benennen“; die Adressen im Verband tragen die Kennung des Verbands."""
    return f"/organisation/verband/{org.dpv.key}/team/benennen/"


def federation_lead_address(org) -> str:
    return f"/organisation/verband/{org.dpv.key}/verbandsleitung/benennen/"


def lead_address(bund) -> str:
    return f"/organisation/verband/bund/{bund.key}/benennen/"


def remove_address(role: Role) -> str:
    return f"/organisation/verband/entfernen/{role.key}/"


def role_of(user, kind) -> Role:
    return Role.objects.get(user=user, kind=kind)


def search(user, address: str, text: str, client=None):
    response = (client or client_for(user)).post(f"{address}suchen/", {"suche": text})
    assert response.status_code == 200
    return dialog_of(_tree(response))


def appoint(user, address: str, target, client=None):
    return (client or client_for(user)).post(address, {"person": target.key})


def section_of(root, heading_id: str):
    return _one(_all(root, lambda e: e.name == "section" and _attr(e, "aria-labelledby") == heading_id))


def people(root, heading_id: str) -> list[str]:
    """Die Einträge einer Fläche als sichtbarer Text, ohne die Abschnitte der Bünde darin."""
    return [_visible_text(entry) for entry in _all(section_of(root, heading_id), lambda e: "a-leitung" in _classes(e)
                                                   and e.name == "li")]


def bunds(root) -> dict[str, dict]:
    """Je Bund auf der Seite „Verband“: Link, Marke, Leitungen als Text und der Satz ohne Bundesleitung."""
    found = {}
    for entry in _all(section_of(root, "h-buende"), lambda e: "a-bund" in _classes(e)):
        heading = _one(_by_tag(entry, "h3"))
        links = _by_tag(heading, "a")
        marks = _all(_one(_all(entry, lambda e: "a-flaeche-kopf" in _classes(e))), lambda e: "a-kennmarke" in _classes(e))
        found[_visible_text(heading)] = {
            "href": _attr(links[0], "href") if links else None,
            "mark": _visible_text(marks[0]) if marks else "",
            "leads": [_visible_text(li) for li in _all(entry, lambda e: "a-leitung" in _classes(e) and e.name == "li")],
            "notices": [_visible_text(n) for n in _all(entry, lambda e: "a-meldung" in _classes(e))],
            "text": _visible_text(entry),
        }
    return found


def confirmation(user, role: Role) -> dict:
    response = client_for(user).get(remove_address(role))
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    inner = _one(_all(dialog, lambda e: "a-dialog-inhalt" in _classes(e)))
    return {
        "title": _visible_text(_one(_by_tag(dialog, "h2"))),
        "text": [_visible_text(entry) for entry in _by_tag(inner, "p")],
        "button": _visible_text(_one(_all(dialog, lambda e: "btn-gefahr" in _classes(e)))),
    }


# ---------- V1, V2: Befehl auf dem Server ----------


@pytest.mark.rechtematrix("RO-14")
def test_v1_max_benennt_vera_per_befehl_und_entfernt_sie_wieder(org, capsys):
    Role.objects.filter(user=org.verbandsleitung).delete()  # am Tool vorbei, nur für die Ausgangslage
    before = RoleChange.objects.count()

    call_command("federation_lead", "grant", "vera.verband")
    assert "vera.verband ist jetzt Verbandsleitung." in capsys.readouterr().out
    assert roles_of(org.verbandsleitung) == {(R.FEDERATION_LEAD, "DPV")}
    call_command("federation_lead", "revoke", "vera.verband")

    assert "vera.verband ist jetzt keine Verbandsleitung mehr." in capsys.readouterr().out
    assert roles_of(org.verbandsleitung) == set()
    log = list(RoleChange.objects.filter(pk__gt=0).order_by("id").values_list("actor_name", "kind", "action"))[before:]
    assert log == [("Befehl auf dem Server", R.FEDERATION_LEAD, "granted"), ("Befehl auf dem Server", R.FEDERATION_LEAD, "removed")]


def test_v1_der_befehl_geht_auch_wenn_es_schon_verbandsleitungen_gibt(org):
    call_command("federation_lead", "grant", "otto.ohne")

    assert (R.FEDERATION_LEAD, "DPV") in roles_of(org.ohne)
    assert Role.objects.filter(kind=R.FEDERATION_LEAD).count() == 3
    assert not Role.objects.filter(user=org.ohne, kind=R.MEMBER).exists()


def test_v2_unbekannter_benutzername(org):
    with pytest.raises(CommandError) as error:
        call_command("federation_lead", "grant", "niemand.da")

    assert str(error.value) == "Kein Konto mit diesem Benutzernamen. Die Person muss sich zuerst einmal im Tool anmelden."


# ---------- V3: Seite „Verband“ ----------


@pytest.mark.rechtematrix("EH-08", "EH-04", "RO-05", "RO-06")
def test_v3_vera_sieht_die_seite_verband(org):
    root = page_tree(org.verbandsleitung)

    assert "Organisation" in nav_labels(root)
    assert _visible_text(_one(_by_tag(root, "h1"))) == "Verband"
    vl = people(root, "h-verbandsleitung")
    assert len(vl) == 2 and any("Vera Verband" in e and "das bist du" in e for e in vl) and any("Viktor" in e for e in vl)
    assert [e for e in people(root, "h-team") if "Tom Team" in e and "DPV-Veranstaltungsteam" in e]
    shown = bunds(root)
    assert list(shown) == ["DPBM Mosaik", "Pfadfinderbund Boreas"]
    assert any("Brummbär" in e and "Bruno Bund" in e and "Bundesleitung" in e for e in shown["Pfadfinderbund Boreas"]["leads"])
    assert any("Mona Mosaik" in e for e in shown["DPBM Mosaik"]["leads"])
    assert all(entry["href"] is None and entry["mark"] == "" for entry in shown.values())


@pytest.mark.rechtematrix("EH-05", "RO-05", "RO-06", "PK-07")
def test_v3_keine_mail_keine_ringe_staemme_gruppen_keine_personen(org):
    content = client_for(org.verbandsleitung).get(ADDRESS).content.decode()

    assert "@example.org" not in content
    for hidden in ("Walhall", "Zugvögel", "Falken", "Küste", "Nord", "Leuchtturm", "Möwen", "Wanda", "Wilma",
                   "Fiete", "Finn", "Personen", "Gliederung"):
        assert hidden not in content, hidden


@pytest.mark.rechtematrix("EH-08")
def test_der_menuepunkt_ist_auf_der_seite_verband_hervorgehoben(org):
    for address in (team_address(org), federation_lead_address(org), lead_address(org.boreas)):
        links = [e for e in _all(page_tree(org.verbandsleitung, address), lambda e: "a-navlink" in _classes(e))
                 if "Organisation" in _visible_text(e)]
        assert links and all(_attr(link, "aria-current") == "page" for link in links), address


# ---------- V4 bis V6: Benennen ----------


@pytest.mark.rechtematrix("RO-15", "PK-12", "PK-13", "PK-24")
def test_v4_vera_findet_otto_und_benennt_ihn_als_bundesleitung_von_boreas(org):
    dialog = search(org.verbandsleitung, lead_address(org.boreas), "otto.ohne@example.org")
    found = hits(dialog)
    assert list(found) == ["Otto Ohne"] and found["Otto Ohne"]["button"]
    assert "Mit dem Benennen wird die Person Mitglied von Pfadfinderbund Boreas." in found["Otto Ohne"]["text"]

    response = appoint(org.verbandsleitung, lead_address(org.boreas), org.ohne)

    assert response.status_code == 302 and response.url == ADDRESS
    assert short_notices(client_for(org.verbandsleitung).get(ADDRESS)) == []  # schon gelesen beim ersten Aufruf
    assert roles_of(org.ohne) == {(R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"), (R.MEMBER, "Pfadfinderbund Boreas")}
    entry = RoleChange.objects.filter(person_id=org.ohne.pk, kind=R.ASSOCIATION_LEAD).get()
    assert entry.actor_id == org.verbandsleitung.pk and entry.action == "granted"


def test_v4_meldung_nach_dem_benennen(org):
    client = client_for(org.verbandsleitung)
    response = client.post(lead_address(org.boreas), {"person": org.ohne.key}, follow=True)

    assert short_notices(response) == ["Otto Ohne ist jetzt Bundesleitung von Pfadfinderbund Boreas."]


@pytest.mark.rechtematrix("RO-15", "PK-16")
def test_v5_wilma_schon_woanders_mitglied_ohne_organisation_und_doch_benennbar(org):
    dialog = search(org.verbandsleitung, lead_address(org.boreas), "wilma.walhall@example.org")
    entry = hits(dialog)["Wilma Walhall"]

    assert "schon woanders Mitglied" in entry["text"] and "Walhall" not in entry["text"].replace("Wilma Walhall", "")
    assert entry["button"]
    appoint(org.verbandsleitung, lead_address(org.boreas), org.walhall_mitglied)
    assert roles_of(org.walhall_mitglied) == {(R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"), (R.MEMBER, "Walhall")}


@pytest.mark.rechtematrix("RO-15", "RO-18")
def test_v6_weitere_verbandsleitung_und_teammitglied_ohne_mitgliedschaft(org):
    response = client_for(org.verbandsleitung).post(federation_lead_address(org), {"person": org.ohne.key}, follow=True)
    assert short_notices(response) == ["Otto Ohne ist jetzt Verbandsleitung."]
    response = client_for(org.verbandsleitung).post(team_address(org), {"person": org.adler_kind.key}, follow=True)
    assert short_notices(response) == ["Anton Adler ist jetzt im DPV-Veranstaltungsteam."]

    assert roles_of(org.ohne) == {(R.FEDERATION_LEAD, "DPV")}
    assert roles_of(org.adler_kind) == {(R.MEMBER, "Sippe Adler"), (R.EVENT_TEAM, "DPV")}


def test_v6_die_dialoge_heissen_wie_ihr_knopf_und_haben_nur_mail_oder_benutzername(org):
    for address, title in ((federation_lead_address(org), "Verbandsleitung benennen"), (team_address(org), "Teammitglied benennen"),
                           (lead_address(org.boreas), "Bundesleitung benennen")):
        dialog = dialog_of(page_tree(org.verbandsleitung, address))
        assert _visible_text(_one(_by_tag(dialog, "h2"))) == title
        label = _one(_by_tag(dialog, "label"))
        assert _visible_text(label).startswith("Mail oder Benutzername")
        assert not _all(dialog, lambda e: _attr(e, "data-vorschlaege") is not None)


def test_schon_in_der_rolle(org):
    response = appoint(org.verbandsleitung, team_address(org), org.team)

    assert "Tom Team ist schon im DPV-Veranstaltungsteam." in notices(dialog_of(_tree(response)))


# ---------- V7 bis V10: Entfernen und Abgeben ----------


@pytest.mark.rechtematrix("RO-15")
def test_v7_vera_entfernt_bruno_als_letzte_bundesleitung_von_boreas(org):
    role = role_of(org.bundesleitung, R.ASSOCIATION_LEAD)
    shown = confirmation(org.verbandsleitung, role)

    assert shown["title"] == "Brummbär (Bruno Bund) als Bundesleitung von Pfadfinderbund Boreas entfernen?"
    assert shown["text"] == ["Danach hat Pfadfinderbund Boreas keine Bundesleitung mehr, und niemand springt ein. Eine neue "
                             "Bundesleitung kann nur die Verbandsleitung benennen. Trotzdem entfernen?"]
    response = client_for(org.verbandsleitung).post(remove_address(role), follow=True)
    assert short_notices(response) == ["Brummbär (Bruno Bund) ist nicht mehr Bundesleitung von Pfadfinderbund Boreas."]
    assert roles_of(org.bundesleitung) == {(R.MEMBER, "Pfadfinderbund Boreas")}
    assert RoleChange.objects.filter(person_id=org.bundesleitung.pk, action="removed", actor_id=org.verbandsleitung.pk).exists()


@pytest.mark.rechtematrix("RO-15")
def test_v8_vera_entfernt_viktor(org):
    role = role_of(org.viktor, R.FEDERATION_LEAD)
    assert confirmation(org.verbandsleitung, role) == {"title": "Viktor Verband als Verbandsleitung entfernen?", "text": [],
                                                       "button": "Entfernen"}

    response = client_for(org.verbandsleitung).post(remove_address(role), follow=True)

    assert short_notices(response) == ["Viktor Verband ist nicht mehr Verbandsleitung."]
    assert roles_of(org.viktor) == set()


@pytest.mark.rechtematrix("RO-20")
def test_v9_vera_gibt_als_letzte_verbandsleitung_ab(org):
    Role.objects.get(user=org.viktor).delete(by=org.max)
    role = role_of(org.verbandsleitung, R.FEDERATION_LEAD)
    shown = confirmation(org.verbandsleitung, role)

    assert shown == {"title": "Deine Rolle als Verbandsleitung abgeben?",
                     "text": ["Danach gibt es keine Verbandsleitung mehr. Eine neue kann nur ein Admin benennen. Trotzdem abgeben?"],
                     "button": "Rolle abgeben"}
    response = client_for(org.verbandsleitung).post(remove_address(role))
    assert response.url == "/profil/"
    assert not Role.objects.filter(kind=R.FEDERATION_LEAD).exists()
    assert client_for(org.verbandsleitung).get(ADDRESS).status_code == 403


def test_v9_beim_eigenen_eintrag_steht_rolle_abgeben_sonst_entfernen(org):
    root = page_tree(org.verbandsleitung)
    buttons = {_visible_text(e): _attr(e, "href") for e in _all(section_of(root, "h-verbandsleitung"),
                                                                 lambda e: "a-leitung-knopf" in _classes(e))}

    assert buttons == {"Rolle abgeben": remove_address(role_of(org.verbandsleitung, R.FEDERATION_LEAD)),
                       "Entfernen": remove_address(role_of(org.viktor, R.FEDERATION_LEAD))}


@pytest.mark.rechtematrix("RO-20")
def test_v10_tom_gibt_seine_rolle_auf_mein_profil_ab(org):
    profile = page_tree(org.team, "/profil/")
    link = _one([e for e in _by_tag(profile, "a") if _visible_text(e).startswith("Rolle abgeben")])
    assert _attr(link, "href") == "/profil/team-abgeben/"

    dialog = dialog_of(page_tree(org.team, "/profil/team-abgeben/"))
    assert _visible_text(_one(_by_tag(dialog, "h2"))) == "Deine Rolle im DPV-Veranstaltungsteam abgeben?"
    response = client_for(org.team).post("/profil/team-abgeben/", follow=True)

    assert short_notices(response) == ["Du bist nicht mehr im DPV-Veranstaltungsteam."]
    assert roles_of(org.team) == set()
    assert RoleChange.objects.filter(person_id=org.team.pk, action="removed", actor_id=org.team.pk).exists()


@pytest.mark.rechtematrix("RO-20")
def test_v10_ohne_rolle_im_team_gibt_es_weder_knopf_noch_rueckfrage(org):
    assert not [e for e in _by_tag(page_tree(org.bundesleitung, "/profil/"), "a") if "Rolle abgeben" in _visible_text(e)]
    for method in ("get", "post"):
        assert getattr(client_for(org.bundesleitung), method)("/profil/team-abgeben/").status_code == 404
    assert (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas") in roles_of(org.bundesleitung)


# ---------- V11, V12, VG2: zugleich Bundesleitung ----------


@pytest.mark.rechtematrix("RO-16", "RO-12", "EH-08")
def test_v11_viktor_benennt_vera_als_bundesleitung_des_mosaik(org):
    appoint(org.viktor, lead_address(org.mosaik), org.verbandsleitung)

    assert roles_of(org.verbandsleitung) >= {(R.ASSOCIATION_LEAD, "DPBM Mosaik"), (R.MEMBER, "DPBM Mosaik")}
    shown = bunds(page_tree(org.verbandsleitung))
    assert shown["DPBM Mosaik"]["href"] == unit_address(org.mosaik)
    assert shown["DPBM Mosaik"]["mark"] == ""  # seit #218 ohne Marke (Nachklärung M1 vom 30.10.2026)
    assert shown["Pfadfinderbund Boreas"]["href"] is None and shown["Pfadfinderbund Boreas"]["mark"] == ""
    page = client_for(org.verbandsleitung).get(unit_address(org.mosaik))
    assert page.status_code == 200 and "a-gliederung" in page.content.decode()
    entry = RoleChange.objects.get(person_id=org.verbandsleitung.pk, kind=R.ASSOCIATION_LEAD)
    assert entry.actor_id == org.viktor.pk


@pytest.mark.rechtematrix("RO-16")
def test_v12_als_bundesleitung_sieht_vera_die_personen_des_mosaik_nicht_die_von_boreas(org):
    appoint(org.viktor, lead_address(org.mosaik), org.verbandsleitung)
    seen = set(Rights(org.verbandsleitung).persons().values_list("username", flat=True))

    assert {"moritz.moewe", "svea.sturm"} <= seen
    assert not seen & {"finn.falke", "wilma.walhall", "bea.boreas", "bruno.bund"}
    assert_like_missing(org.verbandsleitung, unit_address(org.walhall))


def test_vg2_viktor_entfernt_vera_als_bundesleitung_und_das_mosaik_ist_nicht_mehr_anklickbar(org):
    appoint(org.viktor, lead_address(org.mosaik), org.verbandsleitung)
    client_for(org.viktor).post(remove_address(role_of(org.verbandsleitung, R.ASSOCIATION_LEAD)))

    shown = bunds(page_tree(org.verbandsleitung))
    assert shown["DPBM Mosaik"]["href"] is None and shown["DPBM Mosaik"]["mark"] == ""
    assert client_for(org.verbandsleitung).get(ADDRESS).status_code == 200


# ---------- V13: Suchlimit ----------


@pytest.mark.rechtematrix("PK-24")
def test_v13_zwanzig_suchen_gehen_die_einundzwanzigste_nicht(org):
    client = client_for(org.verbandsleitung)
    for number in range(20):
        dialog = search(org.verbandsleitung, team_address(org), f"niemand{number}@example.org", client=client)
        assert notices(dialog) == ["Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."], number

    dialog = search(org.verbandsleitung, lead_address(org.boreas), "otto.ohne@example.org", client=client)

    assert notices(dialog) == [LIMIT_TEXT.format("60 Minuten")]
    assert hits(dialog) == {}
    assert AccountSearch.objects.filter(user=org.verbandsleitung).count() == 20


# ---------- VV1 bis VV10: Verboten ----------


@pytest.mark.rechtematrix("RO-12", "RO-16")
def test_vv1_vera_findet_sich_selbst_ohne_knopf(org):
    entry = hits(search(org.verbandsleitung, lead_address(org.mosaik), "vera.verband"))["Vera Verband"]

    assert not entry["button"]
    assert NOT_YOURSELF_TEXT in entry["text"]


@pytest.mark.rechtematrix("RO-12", "RO-16")
def test_vv1_manipuliertes_formular_macht_vera_nicht_zur_bundesleitung(org):
    before = RoleChange.objects.count()
    for address in (lead_address(org.mosaik), federation_lead_address(org), team_address(org)):
        response = appoint(org.verbandsleitung, address, org.verbandsleitung)
        assert NOT_YOURSELF_TEXT in notices(dialog_of(_tree(response)))

    assert roles_of(org.verbandsleitung) == {(R.FEDERATION_LEAD, "DPV")}
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PK-12", "PK-13", "PK-15")
def test_vv2_namen_und_teile_einer_mail_finden_nichts(org):
    for text in ("Wanda", "Wirbelwind", "wanda.walhall@example", "walhall", "%", "*"):
        dialog = search(org.verbandsleitung, team_address(org), text)
        assert hits(dialog) == {}, text
    assert Rights(org.verbandsleitung).suggestions("Wanda") == []
    assert client_for(org.verbandsleitung).post(f"{unit_address(org.walhall)}benennen/vorschlaege/",
                                                {"suche": "Wanda"}).status_code == 404


@pytest.mark.rechtematrix("PK-16", "RO-15")
def test_vv3_fiete_wird_nicht_bundesleitung_des_mosaik_und_die_falken_bleiben_ungenannt(org):
    entry = hits(search(org.verbandsleitung, lead_address(org.mosaik), "fiete.falke@example.org"))["Funke"]
    assert "Falken" not in entry["text"] and "schon woanders Mitglied" in entry["text"]

    response = appoint(org.verbandsleitung, lead_address(org.mosaik), org.falken_leitung)

    content = response.content.decode()
    assert ELSEWHERE_TEXT in notices(dialog_of(_tree(response)))
    assert "Falken" not in content and "Boreas" in content  # Boreas steht als Bund in der Liste, nicht in der Meldung
    assert (R.ASSOCIATION_LEAD, "DPBM Mosaik") not in roles_of(org.falken_leitung)


@pytest.mark.rechtematrix("EH-05")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/")
def test_vv4_vera_oeffnet_keinen_bund_und_keine_einheit_darunter(org):
    for where in (org.walhall, org.falken, org.boreas, org.mosaik, org.dpv):
        assert_like_missing(org.verbandsleitung, unit_address(where))


@pytest.mark.rechtematrix("RO-17")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/entfernen/<key:role>/")
def test_vv5_keine_stammes_oder_gruppenleitung_benennen_oder_entfernen(org):
    before = RoleChange.objects.count()
    for role in (role_of(org.walhall_leitung, R.TROOP_LEAD), role_of(org.falken_leitung, R.GROUP_LEAD)):
        assert_like_missing(org.verbandsleitung, remove_address(role))
    for where in (org.walhall, org.falken):
        assert_like_missing(org.verbandsleitung, f"{unit_address(where)}benennen/")
        assert_like_missing(org.verbandsleitung, lead_address(where))

    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("EH-27")
def test_vv6_ohne_bundesleitung_springt_vera_nicht_ein(org):
    Role.objects.get(user=org.bundesleitung, kind=R.ASSOCIATION_LEAD).delete(by=org.max)
    rights = Rights(org.verbandsleitung)

    assert not any(rights.covers(where) or rights.opens_unit(where) for where in (org.boreas, org.walhall, org.falken))
    shown = bunds(page_tree(org.verbandsleitung))["Pfadfinderbund Boreas"]
    assert shown["href"] is None
    assert "Walhall" not in shown["text"] and "Stammesleitung" not in shown["text"]


@pytest.mark.rechtematrix("EH-27")
def test_vv6_gegenprobe_fuer_einen_stamm_ohne_leitung_springt_die_bundesleitung_ein(org):
    for user in (org.walhall_leitung, org.willi):
        Role.objects.get(user=user, kind=R.TROOP_LEAD).delete(by=org.max)

    assert Rights(org.bundesleitung).covers(org.walhall)
    assert not Rights(org.verbandsleitung).covers(org.walhall)


@pytest.mark.rechtematrix("RO-18", "RO-14")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/bund/<key:unit>/benennen/")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/bund/<key:unit>/benennen/suchen/")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/<key:unit>/team/benennen/")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/<key:unit>/team/benennen/suchen/")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/<key:unit>/verbandsleitung/benennen/")
@pytest.mark.wie_nicht_vorhanden("organisation/verband/<key:unit>/verbandsleitung/benennen/suchen/")
def test_vv7_bruno_tom_und_max_benennen_und_entfernen_niemanden_im_verband(org):
    before = RoleChange.objects.count()
    for user in (org.bundesleitung, org.team, org.max, org.falke, org.ohne):
        for address in (federation_lead_address(org), team_address(org), f"{team_address(org)}suchen/"):
            for method in ("get", "post"):
                response = getattr(client_for(user), method)(address, {"person": org.ohne.key, "suche": "otto.ohne"})
                assert response.status_code == 404, (user.username, address, method)
        assert_like_missing(user, lead_address(org.boreas))
        assert_like_missing(user, f"{lead_address(org.boreas)}suchen/")
        for address in (team_address(org), federation_lead_address(org)):
            assert_like_missing(user, address)
            assert_like_missing(user, f"{address}suchen/")
        assert_like_missing(user, remove_address(role_of(org.viktor, R.FEDERATION_LEAD)))
        assert_like_missing(user, remove_address(role_of(org.team, R.EVENT_TEAM)))

    assert RoleChange.objects.count() == before
    assert roles_of(org.ohne) == set()


def test_vv7_unbekannte_rolle_in_der_adresse(org):
    for address in (f"/organisation/verband/{org.dpv.key}/admin/benennen/",
                    f"/organisation/verband/{org.dpv.key}/mitglied/benennen/suchen/"):
        assert client_for(org.verbandsleitung).post(address, {"person": org.ohne.key}).status_code == 404
    assert roles_of(org.ohne) == set()


@pytest.mark.rechtematrix("EH-09", "PK-14", "EH-04", "PK-07", "RO-07")
def test_vv8_tom_sieht_keinen_menuepunkt_keine_personen_und_benennt_niemanden(org):
    assert "Organisation" not in nav_labels(page_tree(org.team, "/"))
    response = client_for(org.team).get(ADDRESS)
    assert response.status_code == 403 and NO_ACCESS_TEXT in response.content.decode()
    assert set(Rights(org.team).persons().values_list("username", flat=True)) == {"tom.team"}
    assert Rights(org.team).find_accounts("otto.ohne") == []
    assert list(Rights(org.team).leads()) == []


@pytest.mark.rechtematrix("RO-19")
def test_vv9_admin_und_mitgliedschaft_sind_beim_entfernen_nicht_gefunden(org):
    before = RoleChange.objects.count()
    for role in (role_of(org.max, R.ADMIN), role_of(org.falke, R.MEMBER), role_of(org.bundesleitung, R.MEMBER)):
        assert_like_missing(org.verbandsleitung, remove_address(role))

    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PK-23")
def test_vv10_die_seite_verband_hat_keinen_abschnitt_personen_und_kein_aufnehmen(org):
    content = client_for(org.verbandsleitung).get(ADDRESS).content.decode()

    for missing in ("Personen", "Aufnehmen", "Austragen", "Verschieben"):
        assert missing not in content


# ---------- VG1, VG3, VG4: Grenzfälle ----------


@pytest.mark.django_db(transaction=True)
def test_vg1_vera_und_viktor_entfernen_sich_gleichzeitig_gegenseitig():
    o = build_org()
    vera = lead("vera.verband", R.FEDERATION_LEAD, o.dpv)
    viktor = lead("viktor.verband", R.FEDERATION_LEAD, o.dpv)
    vera_role, viktor_role = role_of(vera, R.FEDERATION_LEAD), role_of(viktor, R.FEDERATION_LEAD)

    def remove(user, role):
        def work():
            try:
                return Rights(user).remove_in_federation(role.key)[1]["person"]
            except Http404:
                return "nicht gefunden"
        return work

    results = _one_after_the_other(remove(vera, viktor_role), remove(viktor, vera_role))

    assert sorted(results) == ["Viktor Verband", "nicht gefunden"]
    assert list(Role.objects.filter(kind=R.FEDERATION_LEAD).values_list("user__username", flat=True)) == ["vera.verband"]


def test_vg3_bund_ohne_bundesleitung_steht_mit_satz_in_der_liste(org):
    Role.objects.get(user=org.bundesleitung, kind=R.ASSOCIATION_LEAD).delete(by=org.max)

    shown = bunds(page_tree(org.verbandsleitung))["Pfadfinderbund Boreas"]

    assert shown["notices"] == ["Information: Pfadfinderbund Boreas hat keine Bundesleitung."] or \
        shown["notices"][0].endswith("Pfadfinderbund Boreas hat keine Bundesleitung.")
    assert shown["leads"] == []


def test_vg3_gesperrte_bundesleitung_steht_mit_marke_und_der_bund_gilt_als_ohne_bundesleitung(org):
    lock(org.bundesleitung)

    shown = bunds(page_tree(org.verbandsleitung))["Pfadfinderbund Boreas"]

    assert any("Brummbär" in entry and "gesperrt" in entry for entry in shown["leads"])
    assert shown["notices"][0].endswith("Pfadfinderbund Boreas hat keine Bundesleitung.")


@pytest.mark.rechtematrix("EH-08")
def test_vg4_ohne_rolle_zeigt_der_naechste_klick_kein_zugriff(org):
    client = client_for(org.verbandsleitung)
    assert client.get(ADDRESS).status_code == 200
    Role.objects.get(user=org.verbandsleitung).delete(by=org.max)

    response = client.get(ADDRESS)

    assert response.status_code == 403 and NO_ACCESS_TEXT in response.content.decode()
    assert "Organisation" not in nav_labels(_tree(client.get("/")))


# ---------- Keine Personendaten, Gegenprobe ----------


@pytest.mark.rechtematrix("EH-05", "PK-07")
def test_verbandsleitung_sieht_keine_personen_mit_konto_auf_keinem_weg(org):
    """Personen mit Konto; verwaltete Personen prüft `tests/test_verwaltete_personen.py` (#117), Anmeldungen kommen mit #101 (Nachklärung vom 22.10.2026)."""
    assert set(Rights(org.verbandsleitung).persons().values_list("username", flat=True)) == {"vera.verband"}
    for where in (org.boreas, org.walhall, org.falken, org.mosaik):
        assert_like_missing(org.verbandsleitung, unit_address(where))
        assert_like_missing(org.verbandsleitung, f"{unit_address(where)}benennen/")
    for address in (ADDRESS, team_address(org), federation_lead_address(org), lead_address(org.boreas)):
        content = client_for(org.verbandsleitung).get(address).content.decode()
        assert "@example.org" not in content and "Wilma" not in content and "Finn" not in content


@pytest.mark.rechtematrix("EH-28", "EH-05", "PK-07")
def test_gegenprobe_mit_leitungsrolle_sieht_vera_deren_personen(org):
    give(org.verbandsleitung, R.MEMBER, org.falken)
    give(org.verbandsleitung, R.GROUP_LEAD, org.falken)

    assert "finn.falke" in set(Rights(org.verbandsleitung).persons().values_list("username", flat=True))
    assert "finn.falke@example.org" not in client_for(org.verbandsleitung).get(ADDRESS).content.decode()
    shown = bunds(page_tree(org.verbandsleitung))
    assert shown["Pfadfinderbund Boreas"]["href"] == unit_address(org.boreas)  # F2 vom 30.10.2026: lesend, ohne Marke
    assert shown["Pfadfinderbund Boreas"]["mark"] == ""
    assert client_for(org.verbandsleitung).get(unit_address(org.falken)).status_code == 200


def test_auch_ohne_verband_gibt_es_den_befehl_nicht(db):
    give_user = person("vera.verband", "Vera", "Verband")
    with pytest.raises(CommandError) as error:
        call_command("federation_lead", "grant", give_user.username)
    assert "Verband" in str(error.value)


# ---------- Aus der unabhängigen Prüfung (30.10.2026) ----------


def test_gesperrte_und_nie_angemeldete_konten_lassen_sich_auch_mit_manipuliertem_formular_nicht_benennen(org):
    lock(org.ohne)
    never = person("nie.da", "Nie", "Da")
    before = RoleChange.objects.count()

    for target in (org.ohne, never):
        for address in (team_address(org), federation_lead_address(org), lead_address(org.boreas)):
            assert appoint(org.verbandsleitung, address, target).status_code == 404, (target.username, address)

    assert RoleChange.objects.count() == before
    assert roles_of(org.ohne) == set() and roles_of(never) == set()


def test_auch_die_suche_im_dialog_verbandsleitung_ist_fuer_andere_nicht_gefunden(org):
    for user in (org.bundesleitung, org.team, org.max):
        response = client_for(user).post(f"{federation_lead_address(org)}suchen/", {"suche": "otto.ohne"})
        assert response.status_code == 404, user.username


@pytest.mark.django_db(transaction=True)
def test_vera_und_viktor_benennen_otto_gleichzeitig_ins_team():
    o = build_org()
    vera = lead("vera.verband", R.FEDERATION_LEAD, o.dpv)
    viktor = lead("viktor.verband", R.FEDERATION_LEAD, o.dpv)
    otto = person("otto.ohne", "Otto", "Ohne")
    User.objects.filter(pk=otto.pk).update(last_login="2026-10-30T08:00:00Z")

    def appoint_by(user):
        return lambda: Rights(user).appoint_in_federation(R.EVENT_TEAM, o.dpv, otto.key)[1]

    results = _one_after_the_other(appoint_by(vera), appoint_by(viktor))

    assert sorted(results) == ["Otto Ohne ist jetzt im DPV-Veranstaltungsteam.", "Otto Ohne ist schon im DPV-Veranstaltungsteam."]
    assert Role.objects.filter(user=otto, kind=R.EVENT_TEAM).count() == 1


def test_der_bausteinkatalog_zeigt_die_rollenkachel_mit_rolle_abgeben(org):
    root = page_tree(org.verbandsleitung, "/bausteine/")
    block = section_of(root, "h-rollenkachel")

    assert [_visible_text(e) for e in _all(block, lambda e: "a-kachel-knopf" in _classes(e))] == ["Rolle abgeben"]


# ---------- Anmerkungen von Sebastian nach dem lokalen Test (30.10.2026) ----------


def test_kopf_ohne_namen_des_verbands_und_abschnitt_heisst_dpv_verbandsleitung(org):
    """https://github.com/sebivtt/dpv-participant-management/issues/94#issuecomment-6520805547, Punkte 1 und 2."""
    root = page_tree(org.verbandsleitung)
    head = _one(_all(root, lambda e: "a-kopf" in _classes(e)))

    assert _visible_text(head) == "Verband"
    assert _visible_text(_one(_by_tag(root, "h2", id="h-verbandsleitung"))) == "DPV-Verbandsleitung"
    assert _visible_text(_one(_by_tag(root, "h2", id="h-team"))) == "DPV-Veranstaltungsteam"


# ---------- #218: zurück zur Seite „Verband“ ----------
# Die Nummern 1 bis 8 verweisen auf Sebastians Szenarien vom 30.10.2026
# (https://github.com/sebivtt/dpv-participant-management/issues/218#issuecomment-6521671528). Vera
# ist dort zugleich Bundesleitung von Boreas, Vroni Verbandsleitung und Stammesleitung von Walhall.


def _vera_leads_boreas(org) -> None:
    """Viktor benennt Vera zur Bundesleitung von Boreas, wie auf der Seite „Verband“ (keine Selbstvergabe, RO-12)."""
    appoint(org.viktor, lead_address(org.boreas), org.verbandsleitung)
    assert (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas") in roles_of(org.verbandsleitung)


def _vroni(org):
    vroni = lead("vroni.verband", R.FEDERATION_LEAD, org.dpv)
    give(vroni, R.MEMBER, org.walhall)
    give(vroni, R.TROOP_LEAD, org.walhall)
    return vroni


def _back(root) -> tuple[str, str]:
    """Der Knopf oben am Handy: sichtbarer Text und Ziel."""
    back = _one(_all(root, lambda e: "a-orga-zurueck" in _classes(e)))
    return _visible_text(back), _attr(back, "href")


@pytest.mark.rechtematrix("EH-08")
def test_218_1_auf_boreas_steht_dpv_im_pfad_und_fuehrt_zur_seite_verband(org):
    _vera_leads_boreas(org)
    shown = bunds(page_tree(org.verbandsleitung))
    root = page_tree(org.verbandsleitung, shown["Pfadfinderbund Boreas"]["href"])

    assert header(root)["path"] == [("DPV", ADDRESS)]
    assert _visible_text(_one(_by_tag(page_tree(org.verbandsleitung, ADDRESS), "h1"))) == "Verband"


@pytest.mark.rechtematrix("EH-08", "RO-03")
def test_218_2_auf_walhall_stehen_dpv_und_boreas_im_pfad(org):
    _vera_leads_boreas(org)
    root = page_tree(org.verbandsleitung, unit_address(org.walhall))

    assert header(root)["path"] == [("DPV", ADDRESS), ("Pfadfinderbund Boreas", unit_address(org.boreas))]


@pytest.mark.rechtematrix("EH-08", "RO-01")
def test_218_3_vroni_liest_boreas_und_kommt_von_dort_zur_seite_verband(org):
    vroni = _vroni(org)
    on_walhall = page_tree(vroni, unit_address(org.walhall))
    on_boreas = page_tree(vroni, unit_address(org.boreas))

    assert header(on_walhall)["path"] == [("DPV", ADDRESS), ("Pfadfinderbund Boreas", unit_address(org.boreas))]
    assert header(on_boreas)["mark"] == "nur lesen"
    assert header(on_boreas)["path"] == [("DPV", ADDRESS)]
    assert _visible_text(_one(_by_tag(page_tree(vroni, ADDRESS), "h1"))) == "Verband"


def test_218_4_am_handy_heisst_der_knopf_verband_und_fuehrt_zur_seite_verband(org):
    _vera_leads_boreas(org)

    for address in (unit_address(org.boreas), unit_address(org.walhall)):
        assert _back(page_tree(org.verbandsleitung, address)) == ("Verband", ADDRESS), address


@pytest.mark.rechtematrix("EH-03")
def test_218_5_bruno_sieht_keinen_verband_im_pfad_und_den_knopf_gliederung(org):
    root = page_tree(org.bundesleitung, unit_address(org.walhall))

    assert header(root)["path"] == [("Pfadfinderbund Boreas", unit_address(org.boreas))]
    assert "DPV" not in header(root)["path_text"]
    assert _back(root) == ("Gliederung", ADDRESS)


@pytest.mark.rechtematrix("EH-03", "EH-08")
def test_218_6_bruno_sieht_unter_organisation_seinen_bund_nicht_die_seite_verband(org):
    root = page_tree(org.bundesleitung)

    assert header(root)["name"] == "Pfadfinderbund Boreas"
    assert header(root)["path"] == []
    assert "DPV" not in header(root)["path_text"]
    assert _all(root, lambda e: _attr(e, "aria-labelledby") == "h-buende") == []


def test_218_7_nach_dem_abgeben_der_verbandsleitung_fehlt_dpv_wieder(org):
    _vera_leads_boreas(org)
    client_for(org.verbandsleitung).post(remove_address(role_of(org.verbandsleitung, R.FEDERATION_LEAD)))

    root = page_tree(org.verbandsleitung, unit_address(org.boreas))
    assert header(root)["path"] == []
    assert "DPV" not in header(root)["path_text"]
    assert _back(root) == ("Gliederung", ADDRESS)


def test_218_8_nach_dem_umbenennen_steht_der_neue_name_im_pfad(org):
    _vera_leads_boreas(org)
    org.dpv.name = "Deutscher Pfadfinderverband"
    org.dpv.save(by=BY)

    root = page_tree(org.verbandsleitung, unit_address(org.walhall))
    assert header(root)["path"] == [("Deutscher Pfadfinderverband", ADDRESS), ("Pfadfinderbund Boreas", unit_address(org.boreas))]


def test_218_auch_mit_offenem_dialog_steht_dpv_im_pfad(org):
    """Die Dialoge „… benennen“ und „Entfernen“ zeigen dieselbe Seite darunter."""
    _vera_leads_boreas(org)
    bruno = role_of(org.bundesleitung, R.ASSOCIATION_LEAD)

    for address in (f"{unit_address(org.boreas)}benennen/", f"{unit_address(org.boreas)}entfernen/{bruno.key}/"):
        root = page_tree(org.verbandsleitung, address)
        assert header(root)["path"] == [("DPV", ADDRESS)], address
        assert _back(root) == ("Verband", ADDRESS), address


def test_218_der_bausteinkatalog_zeigt_den_kopf_auch_mit_verband_im_pfad(org):
    block = section_of(page_tree(org.verbandsleitung, "/bausteine/"), "h-orgakopf")
    heads = _all(block, lambda e: "a-orga-kopf" in _classes(e))

    paths = [[_text(link) for link in _by_tag(_one(_all(head, lambda e: "a-pfad" in _classes(e))), "a")] for head in heads]
    assert paths == [["Pfadfinderbund Boreas"], ["DPV", "Pfadfinderbund Boreas"]]


# Nachtrag vom 30.10.2026: keine Marke „Deine Rolle: Bundesleitung“ mehr (Szenarien M1, M2,
# https://github.com/sebivtt/dpv-participant-management/issues/218#issuecomment-6523317158).


def test_218_m1_der_eigene_bund_ist_anklickbar_aber_ohne_marke(org):
    _vera_leads_boreas(org)
    root = page_tree(org.verbandsleitung)
    shown = bunds(root)

    assert shown["Pfadfinderbund Boreas"]["href"] == unit_address(org.boreas)
    assert shown["DPBM Mosaik"]["href"] is None
    assert all(entry["mark"] == "" for entry in shown.values())
    assert "Deine Rolle: Bundesleitung" not in _visible_text(root)
    assert _all(page_tree(org.verbandsleitung, unit_address(org.boreas)), lambda e: "a-gliederung" in _classes(e))


def test_218_m2_der_bausteinkatalog_zeigt_die_marke_nicht_mehr_der_titel_bleibt_ein_link(org):
    root = page_tree(org.verbandsleitung, "/bausteine/")

    assert "Deine Rolle: Bundesleitung" not in _visible_text(root)
    heads = _all(section_of(root, "h-flaechenkopf"), lambda e: "a-flaeche-kopf" in _classes(e))
    assert [_text(link) for head in heads for link in _by_tag(_one(_by_tag(head, "h3")), "a")] == ["Pfadfinderbund Boreas"]
