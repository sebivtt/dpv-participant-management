"""Tests für Organisationen anlegen und bearbeiten durch die Ebene darüber (#95, ORG-06).

Die Kennungen O1 bis O10, OV1 bis OV10 und OG1 bis OG8 verweisen auf die Szenarien vom 28.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/95#issuecomment-6475719227), OG9 auf
die Ergänzung vom 03.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/95#issuecomment-6607300699). Die
Wortlaute stehen im Text von #95. Personen und Einheiten wie in den Tests zu #190
(`tests/test_benennen.py`): Boreas (ohne Ringe) mit Bruno, Wanda, Fiete und Zora; Mosaik (mit
Ringen) mit Mona, Kai (Ringleitung Küste), Lars (Stammesleitung Leuchtturm) und Nele (Ringleitung
Nord); Sturmvogel in Ring Nord hat keine Stammesleitung. Vera ist Verbandsleitung, Tom im
DPV-Veranstaltungsteam. Namen, Fahrtennamen und Mails sind erfunden.

Jede Handlung hat eine eigene Adresse unter der Seite der Organisation; die Organisation darüber
und die Art der neuen Organisation kommen immer aus der Adresse, nie aus dem Formular.
"""

import pytest
from django.core.exceptions import ValidationError
from django.urls import get_resolver

from access.rights import Rights
from roles.models import Role
from tests import test_benennen
from tests.test_benennen import _one_after_the_other, dialog_of, short_notices
from tests.test_einheiten_befehle import refused, run
from tests.test_gestaltung import _all, _attr, _classes, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_rechtepruefung import lead, remove
from tests.test_rollen import BY, give
from units.models import Kind as U
from units.models import Unit, UnitChange

R = Role.Kind
A = UnitChange.Action
pytestmark = pytest.mark.django_db

base_org = test_benennen.base_org
org_189 = test_benennen.org_189
org = test_benennen.org

RINGS_QUESTION = (
    "Ringe für Pfadfinderbund Boreas einführen? Danach muss jeder neue Stamm in einem Ring hängen. Die "
    "bisherigen Stämme bleiben ohne Ring, bis du sie einem Ring zuordnest. Zurücknehmen lässt sich das "
    "vorerst nicht."
)
OG5_MESSAGE = (
    "Kompass (Kai Kueste) ist Ringleitung von Ring Küste. Nach dem Wechsel passt diese Rolle nicht mehr zu "
    "der Mitgliedschaft in Stamm Leuchtturm. Sie kann zuerst beendet werden."
)
NOT_ON_PATH_LARS = "Laterne (Lars Leuchtturm) ist Mitglied in Leuchtturm und kann deshalb keine Leitung bei Ring Küste sein."


def create_address(where) -> str:
    return f"{unit_address(where)}anlegen/"


def rename_address(where) -> str:
    return f"{unit_address(where)}umbenennen/"


def ring_address(where) -> str:
    return f"{unit_address(where)}ring-wechseln/"


def rings_address(where) -> str:
    return f"{unit_address(where)}ringe-einfuehren/"


def create(user, where, name: str, client=None, **more):
    """„Anlegen“ im Dialog bestätigen, wie der blaue Knopf es mit dem Namen abschickt."""
    return (client or client_for(user)).post(create_address(where), {"name": name, **more})


def rename(user, where, name: str, client=None, **more):
    return (client or client_for(user)).post(rename_address(where), {"name": name, **more})


def change_ring(user, troop, ring, client=None, **more):
    return (client or client_for(user)).post(ring_address(troop), {"ring": ring.key, **more})


def introduce_rings(user, bund, client=None):
    return (client or client_for(user)).post(rings_address(bund), {})


def children(where) -> set[tuple[str, str]]:
    return set(Unit.objects.filter(parent=where).values_list("kind", "name"))


def fresh(unit) -> Unit:
    return Unit.objects.select_related("parent").get(pk=unit.pk)


def entries(since: int = 0) -> list[tuple]:
    """Das Protokoll der Strukturänderungen ab `since`: wer, welche Organisation, was, alt, neu."""
    return [(e.actor_id, e.unit_name, e.action, e.old_value, e.new_value)
            for e in UnitChange.objects.filter(pk__gt=since).order_by("pk")]


def mark() -> int:
    last = UnitChange.objects.order_by("pk").last()
    return last.pk if last else 0


def field_errors(response) -> list[str]:
    """Die Fehler am Feld im offenen Dialog."""
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    return [_visible_text(entry) for entry in _all(dialog, lambda e: "invalid-feedback" in _classes(e))]


def dialog_notices(response) -> list[str]:
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    return [_visible_text(entry) for entry in _all(dialog, lambda e: "a-meldung" in _classes(e))]


def links_to(user, where, address: str) -> list:
    """Alle Links auf der Seite der Organisation, die zu `address` führen."""
    root = page_tree(user, unit_address(where))
    return _all(root, lambda e: e.name == "a" and _attr(e, "href") == address)


# ---------- Anlegen: erlaubt ----------


@pytest.mark.rechtematrix("EH-10")
def test_o1_bruno_legt_in_boreas_den_stamm_eichen_an(org):
    start = mark()
    client = client_for(org.bundesleitung)

    response = create(org.bundesleitung, org.boreas, "Eichen", client=client)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.boreas)
    assert (U.TROOP, "Eichen") in children(org.boreas)
    assert short_notices(client.get(response["Location"])) == ["Stamm Eichen ist angelegt."]
    assert entries(start) == [(org.bundesleitung.pk, "Eichen", A.CREATED, "", "Pfadfinderbund Boreas")]


@pytest.mark.rechtematrix("EH-12")
def test_o2_wanda_legt_in_walhall_die_sippe_kraniche_an(org):
    client = client_for(org.walhall_leitung)

    response = create(org.walhall_leitung, org.walhall, "Sippe Kraniche", client=client)

    assert response["Location"] == unit_address(org.walhall)
    assert (U.GROUP, "Sippe Kraniche") in children(org.walhall)
    assert short_notices(client.get(response["Location"])) == ["Sippe Kraniche ist angelegt."]


@pytest.mark.rechtematrix("EH-10")
def test_o3_bruno_legt_in_walhall_eine_gruppe_an_obwohl_walhall_eine_leitung_hat(org):
    assert create(org.bundesleitung, org.walhall, "Rotte Biber").status_code == 302

    assert (U.GROUP, "Rotte Biber") in children(org.walhall)


@pytest.mark.rechtematrix("EH-10", "EH-11")
def test_o4_mona_legt_einen_ring_an_kai_einen_stamm_und_darin_eine_gruppe(org):
    assert create(org.mosaik_leitung, org.mosaik, "Süd").status_code == 302
    assert create(org.kueste_leitung, org.kueste, "Düne").status_code == 302
    duene = Unit.objects.get(name="Düne")
    assert create(org.kueste_leitung, duene, "Sippe Sand").status_code == 302

    assert (U.RING, "Süd") in children(org.mosaik)
    assert (duene.kind, duene.parent_id) == (U.TROOP, org.kueste.pk)
    assert children(duene) == {(U.GROUP, "Sippe Sand")}


@pytest.mark.rechtematrix("EH-11")
def test_kai_legt_auch_in_leuchtturm_eine_gruppe_an(org):
    """EH-11: Gruppen im ganzen eigenen Ring, auch in einem Stamm mit eigener Leitung."""
    assert create(org.kueste_leitung, org.leuchtturm, "Sippe Krebse").status_code == 302

    assert (U.GROUP, "Sippe Krebse") in children(org.leuchtturm)


def test_neuer_name_ohne_leerzeichen_am_rand(org):
    create(org.walhall_leitung, org.walhall, "  Sippe Kraniche ")

    assert (U.GROUP, "Sippe Kraniche") in children(org.walhall)


# ---------- Anlegen: verboten ----------


@pytest.mark.rechtematrix("EH-13")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/anlegen/")
def test_ov1_zora_legt_keine_gruppe_in_walhall_an(org):
    """OV1: auch über die direkte Adresse und als Anfrage aus dem Skript."""
    before = children(org.walhall)
    start = mark()

    assert_like_missing(org.zugvoegel_leitung, create_address(org.walhall))
    response = client_for(org.zugvoegel_leitung).post(create_address(org.walhall), {"name": "Sippe Fremd"},
                                                      HTTP_HX_REQUEST="true")

    assert response.status_code == 404
    assert children(org.walhall) == before
    assert entries(start) == []


@pytest.mark.rechtematrix("EH-13")
def test_ov1_die_kennung_von_walhall_im_formular_aendert_nichts(org):
    """OV1: Die Organisation darüber kommt immer aus der Adresse; Zoras Gruppe entsteht in den Zugvögeln."""
    before = children(org.walhall)

    create(org.zugvoegel_leitung, org.zugvoegel, "Sippe Kiebitze", unit=org.walhall.key, parent=org.walhall.key)

    assert children(org.walhall) == before
    assert Unit.objects.get(name="Sippe Kiebitze").parent_id == org.zugvoegel.pk


@pytest.mark.rechtematrix("EH-13")
def test_ov2_fiete_hat_keinen_knopf_und_legt_nichts_an(org):
    assert links_to(org.falken_leitung, org.falken, create_address(org.falken)) == []
    assert create(org.falken_leitung, org.falken, "Sippe Küken").status_code == 404
    assert create(org.falken_leitung, org.walhall, "Sippe Küken").status_code == 404

    assert not Unit.objects.filter(name="Sippe Küken").exists()


@pytest.mark.rechtematrix("EH-13")
def test_ov3_wanda_legt_keinen_stamm_an_und_unter_einer_gruppe_gibt_es_nichts(org):
    assert create(org.walhall_leitung, org.boreas, "Stamm Neu").status_code == 404
    assert create(org.walhall_leitung, org.falken, "Unter Falken").status_code == 404

    assert not Unit.objects.filter(name__in=["Stamm Neu", "Unter Falken"]).exists()


@pytest.mark.rechtematrix("EH-13")
def test_ov4_mona_legt_keinen_stamm_direkt_im_mosaik_an_und_kai_keinen_ring(org):
    """OV4: Die Art kommt aus der Adresse; ein Feld „kind“ ändert sie nicht."""
    create(org.mosaik_leitung, org.mosaik, "Möwenstein", kind=U.TROOP)

    assert Unit.objects.get(name="Möwenstein").kind == U.RING
    assert not Unit.objects.filter(kind=U.TROOP, parent=org.mosaik).exists()
    assert create(org.kueste_leitung, org.mosaik, "Ring Kai").status_code == 404
    assert not Unit.objects.filter(name="Ring Kai").exists()


@pytest.mark.rechtematrix("EH-13", "EH-19")
def test_mona_legt_in_ring_kueste_mit_ringleitung_keinen_stamm_an(org):
    """EH-13, EH-19: Stämme in einem Ring legt die Bundesleitung nur an, wenn sie für den Ring einspringt."""
    assert create(org.mosaik_leitung, org.kueste, "Stamm Mona").status_code == 404

    assert not Unit.objects.filter(name="Stamm Mona").exists()


@pytest.mark.rechtematrix("EH-13", "EH-15", "EH-27")
def test_ov7_vera_und_tom_legen_nichts_an_und_benennen_nichts_um(org):
    remove(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)
    start = mark()

    for user in (org.verbandsleitung, org.team):
        for where in (org.boreas, org.walhall, org.mosaik, org.kueste, org.dpv):
            assert create(user, where, "Von oben").status_code == 404
            assert rename(user, where, "Von oben").status_code == 404

    assert not Unit.objects.filter(name="Von oben").exists()
    assert entries(start) == []
    assert not Rights(org.verbandsleitung).covers(org.boreas)


# ---------- Namen ----------


@pytest.mark.rechtematrix("EH-14")
def test_og1_eine_zweite_sippe_habichte_lehnt_das_tool_ab(org):
    rename(org.walhall_leitung, org.falken, "Sippe Habichte")
    rename(org.walhall_leitung, org.walhall, "Walhalla")
    start = mark()

    response = create(org.walhall_leitung, org.walhall, " sippe habichte ")

    assert field_errors(response) == ["Die Gruppe ‚Sippe Habichte‘ gibt es in Walhalla schon."]
    assert [name for _kind, name in children(org.walhall)].count("Sippe Habichte") == 1
    assert entries(start) == []


@pytest.mark.django_db(transaction=True)
def test_og1_zwei_gleichzeitig_mit_demselben_namen_ergeben_genau_eine_gruppe(transactional_db, org):
    results = _one_after_the_other(lambda: Rights(org.walhall_leitung).create(org.walhall, "Sippe Kraniche"),
                                   lambda: Rights(org.bundesleitung).create(org.walhall, "sippe kraniche"))

    assert [done for done, _text in results] == [True, False]
    assert results[1][1] == "Die Gruppe ‚Sippe Kraniche‘ gibt es in Walhall schon."
    assert Unit.objects.filter(parent=org.walhall, name__iexact="sippe kraniche").count() == 1


def test_og2_gleicher_gruppenname_in_einem_anderen_stamm_geht(org):
    assert create(org.zugvoegel_leitung, org.zugvoegel, "Sippe Falken").status_code == 302

    assert (U.GROUP, "Sippe Falken") in children(org.zugvoegel)


def test_og2_ring_und_stamm_mit_gleichem_namen_im_selben_bund_lehnt_das_tool_ab(org):
    response = create(org.mosaik_leitung, org.mosaik, "leuchtturm")

    assert field_errors(response) == ["Den Stamm ‚Leuchtturm‘ gibt es in DPBM Mosaik schon."]
    assert not Unit.objects.filter(kind=U.RING, name__iexact="leuchtturm").exists()


@pytest.mark.parametrize("name", ["", "   "])
def test_og3_leerer_name_wird_abgelehnt(org, name):
    start = mark()

    response = create(org.walhall_leitung, org.walhall, name)

    assert field_errors(response) == ["Der Name darf nicht leer sein."]
    assert len(children(org.walhall)) == 2
    assert rename(org.walhall_leitung, org.falken, name).status_code == 200
    assert fresh(org.falken).name == "Sippe Falken"
    assert entries(start) == []


def test_zu_langer_name_wird_abgelehnt_und_nicht_abgeschnitten(org):
    response = create(org.walhall_leitung, org.walhall, "S" * 101)

    assert field_errors(response) == ["Der Name darf höchstens 100 Zeichen haben."]
    assert len(children(org.walhall)) == 2


# ---------- Umbenennen ----------


@pytest.mark.rechtematrix("EH-14")
def test_o5_wanda_benennt_die_falken_und_ihren_stamm_um_fiete_seine_gruppe(org):
    start = mark()
    client = client_for(org.walhall_leitung)

    response = rename(org.walhall_leitung, org.falken, "Sippe Habichte", client=client)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.falken)
    assert short_notices(client.get(response["Location"])) == ["Sippe Falken heißt jetzt Sippe Habichte."]
    assert rename(org.walhall_leitung, org.walhall, "Walhalla").status_code == 302
    assert rename(org.falken_leitung, org.falken, "Sippe Bussarde").status_code == 302
    assert [fresh(unit).name for unit in (org.falken, org.walhall)] == ["Sippe Bussarde", "Walhalla"]
    assert entries(start) == [
        (org.walhall_leitung.pk, "Sippe Falken (Walhall)", A.RENAMED, "Sippe Falken", "Sippe Habichte"),
        (org.walhall_leitung.pk, "Walhall", A.RENAMED, "Walhall", "Walhalla"),
        (org.falken_leitung.pk, "Sippe Habichte (Walhalla)", A.RENAMED, "Sippe Habichte", "Sippe Bussarde"),
    ]


@pytest.mark.rechtematrix("EH-14", "EH-20")
def test_o6_bruno_benennt_boreas_um(org):
    client = client_for(org.bundesleitung)

    response = rename(org.bundesleitung, org.boreas, "Bund Boreas", client=client)

    assert fresh(org.boreas).name == "Bund Boreas"
    assert short_notices(client.get(response["Location"])) == ["Pfadfinderbund Boreas heißt jetzt Bund Boreas."]


def test_umbenennen_nur_in_der_schreibweise_geht(org):
    assert rename(org.walhall_leitung, org.falken, "sippe falken").status_code == 302

    assert fresh(org.falken).name == "sippe falken"


@pytest.mark.rechtematrix("EH-15")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/umbenennen/")
def test_ov5_fiete_benennt_walhall_nicht_um_und_wanda_boreas_nicht(org):
    start = mark()

    assert_like_missing(org.falken_leitung, rename_address(org.walhall))
    assert_like_missing(org.walhall_leitung, rename_address(org.boreas))
    assert_like_missing(org.walhall_leitung, rename_address(org.zugvoegel))

    assert fresh(org.walhall).name == "Walhall"
    assert fresh(org.boreas).name == "Pfadfinderbund Boreas"
    assert entries(start) == []


@pytest.mark.rechtematrix("EH-20")
def test_niemand_legt_im_tool_einen_bund_an_oder_benennt_einen_fremden_um(org):
    """EH-20: Verband und Bünde legen Admins per Befehl an; einen fremden Bund benennt niemand um."""
    start = mark()

    for user in (org.verbandsleitung, org.bundesleitung, org.mosaik_leitung, org.max):
        assert create(user, org.dpv, "Neuer Bund").status_code == 404
        assert rename(user, org.dpv, "Neuer Verband").status_code == 404
    assert rename(org.mosaik_leitung, org.boreas, "Gekapert").status_code == 404

    assert not Unit.objects.filter(name__in=["Neuer Bund", "Neuer Verband", "Gekapert"]).exists()
    assert entries(start) == []


@pytest.mark.django_db(transaction=True)
def test_og4_umbenennen_und_gleichzeitig_ring_zuordnen_beides_bleibt(transactional_db, org):
    """OG4: Die Seiten speichern nur das geänderte Feld; ein veralteter Stand überschreibt nichts."""
    org.boreas.has_rings = True
    org.boreas.save(by=BY)
    nord = Unit(kind=U.RING, name="Ring Nord", parent=org.boreas)
    nord.save(by=BY)
    stale = Unit.objects.get(pk=org.walhall.pk)

    results = _one_after_the_other(lambda: Rights(org.bundesleitung).change_ring(org.walhall, nord.key),
                                   lambda: Rights(org.walhall_leitung).rename(stale, "Walhalla"))

    assert [done for done, _text in results] == [True, True]
    assert (fresh(org.walhall).name, fresh(org.walhall).parent_id) == ("Walhalla", nord.pk)


# ---------- Ringe ----------


@pytest.mark.rechtematrix("EH-16")
def test_o7_mona_verschiebt_leuchtturm_nach_ring_nord(org):
    start = mark()
    client = client_for(org.mosaik_leitung)
    assert client_for(org.kueste_leitung).get(unit_address(org.leuchtturm)).status_code == 200

    response = change_ring(org.mosaik_leitung, org.leuchtturm, org.nord, client=client)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.leuchtturm)
    assert short_notices(client.get(response["Location"])) == ["Stamm Leuchtturm gehört jetzt zu Ring Nord."]
    assert fresh(org.leuchtturm).parent_id == org.nord.pk
    assert fresh(org.moewen).parent_id == org.leuchtturm.pk
    assert Role.objects.get(user=org.moewe, kind=R.MEMBER).unit_id == org.moewen.pk
    assert client_for(org.kueste_leitung).get(unit_address(org.leuchtturm)).status_code == 404
    assert client_for(org.nord_leitung).get(unit_address(org.moewen)).status_code == 200
    assert entries(start) == [(org.mosaik_leitung.pk, "Leuchtturm", A.RING_CHANGED, "Küste", "Nord")]


@pytest.mark.rechtematrix("EH-23", "EH-16")
def test_o8_bruno_fuehrt_ringe_ein_legt_einen_ring_an_und_ordnet_walhall_zu(org):
    start = mark()
    client = client_for(org.bundesleitung)
    assert RINGS_QUESTION in _visible_text(dialog_of(_tree(client.get(rings_address(org.boreas)))))

    response = introduce_rings(org.bundesleitung, org.boreas, client=client)

    assert response["Location"] == unit_address(org.boreas)
    assert short_notices(client.get(response["Location"])) == ["Pfadfinderbund Boreas hat jetzt Ringe."]
    assert fresh(org.boreas).has_rings is True
    assert create(org.bundesleitung, org.boreas, "Ring West").status_code == 302
    west = Unit.objects.get(name="Ring West")
    assert west.kind == U.RING
    assert change_ring(org.bundesleitung, org.walhall, west).status_code == 302
    assert fresh(org.walhall).parent_id == west.pk
    assert fresh(org.zugvoegel).parent_id == org.boreas.pk
    assert entries(start) == [
        (org.bundesleitung.pk, "Pfadfinderbund Boreas", A.HAS_RINGS, "aus", "ein"),
        (org.bundesleitung.pk, "Ring West", A.CREATED, "", "Pfadfinderbund Boreas"),
        (org.bundesleitung.pk, "Walhall", A.RING_ASSIGNED, "", "Ring West"),
    ]


@pytest.mark.rechtematrix("EH-24")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/ringe-einfuehren/")
def test_ov8_mona_schaltet_fuer_boreas_keine_ringe_ein(org):
    start = mark()

    assert_like_missing(org.mosaik_leitung, rings_address(org.boreas))
    for user in (org.walhall_leitung, org.verbandsleitung, org.team):
        assert introduce_rings(user, org.boreas).status_code == 404
    assert introduce_rings(org.walhall_leitung, org.walhall).status_code == 404

    assert fresh(org.boreas).has_rings is False
    assert entries(start) == []


def test_og8_mit_ringen_gibt_es_ringe_einfuehren_nicht(org):
    assert links_to(org.mosaik_leitung, org.mosaik, rings_address(org.mosaik)) == []
    assert client_for(org.mosaik_leitung).get(rings_address(org.mosaik)).status_code == 404
    assert introduce_rings(org.mosaik_leitung, org.mosaik).status_code == 404


@pytest.mark.rechtematrix("EH-17")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/ring-wechseln/")
def test_ov6_kai_und_lars_verschieben_leuchtturm_nicht(org):
    start = mark()

    assert_like_missing(org.kueste_leitung, ring_address(org.leuchtturm))
    assert_like_missing(org.leuchtturm_leitung, ring_address(org.leuchtturm))
    assert change_ring(org.nord_leitung, org.sturmvogel, org.kueste).status_code == 404
    assert change_ring(org.bundesleitung, org.leuchtturm, org.nord).status_code == 404

    assert fresh(org.leuchtturm).parent_id == org.kueste.pk
    assert fresh(org.sturmvogel).parent_id == org.nord.pk
    assert entries(start) == []


@pytest.mark.rechtematrix("EH-26")
def test_ov9_niemand_nimmt_einen_stamm_aus_seinem_ring(org):
    """OV9: Als Ziel gelten nur Ringe desselben Bundes; der Bund, ein Stamm oder ein fremder Ring sind „nicht gefunden“."""
    start = mark()

    for target in (org.mosaik, org.sturmvogel, org.boreas):
        assert change_ring(org.mosaik_leitung, org.leuchtturm, target).status_code == 404

    assert fresh(org.leuchtturm).parent_id == org.kueste.pk
    assert entries(start) == []


@pytest.mark.rechtematrix("EH-25")
def test_ov9_hat_ringe_ausschalten_gibt_es_nicht_als_befehl(org):
    """OV9, Frage 16 vom 28.10.2026: Der Befehl schaltet nur noch ein (#204 baut das Ausschalten)."""
    run("association", "create", "Bund Ohne")

    assert "invalid choice: 'off'" in refused("association", "rings", "Bund Ohne", "off")
    assert Unit.objects.get(name="Bund Ohne").has_rings is False
    run("association", "rings", "Bund Ohne", "on")
    assert Unit.objects.get(name="Bund Ohne").has_rings is True
    assert "invalid choice: 'off'" in refused("association", "rings", "Bund Ohne", "off")
    assert Unit.objects.get(name="Bund Ohne").has_rings is True


@pytest.mark.rechtematrix("EH-25")
def test_ov9_keine_adresse_schaltet_hat_ringe_aus(org):
    """OV9: Auch ein manipuliertes Formular an „Ringe einführen“ oder „Umbenennen“ schaltet nichts aus."""
    client = client_for(org.mosaik_leitung)

    client.post(rename_address(org.mosaik), {"name": "DPBM Mosaik", "has_rings": "", "ringe": "aus"})
    client.post(rings_address(org.mosaik), {"has_rings": "", "ringe": "aus"})

    assert fresh(org.mosaik).has_rings is True
    assert not [route for route in _routes() if "ausschalten" in route or "loeschen" in route]


def test_ov9_eine_gruppe_wechselt_nicht_den_stamm(org):
    """OV9, Frage 13 vom 28.10.2026: Das Datenmodell lehnt den Wechsel des Stammes einer Gruppe ab."""
    start = mark()
    falken = Unit.objects.get(pk=org.falken.pk)
    falken.parent = org.zugvoegel

    with pytest.raises(ValidationError) as error:
        falken.save(by=BY)

    assert "Eine Gruppe bleibt in ihrem Stamm." in error.value.messages
    assert fresh(org.falken).parent_id == org.walhall.pk
    assert entries(start) == []


def test_og5_ringwechsel_mit_leitungsrolle_ausserhalb_des_pfads_wird_abgelehnt(org):
    """OG5, #89, PK-25: Kai ist Ringleitung von Küste und Mitglied von Leuchtturm."""
    membership = Role.objects.get(user=org.kueste_leitung, kind=R.MEMBER)
    membership.unit = org.leuchtturm
    membership.save(by=BY)
    start = mark()

    response = change_ring(org.mosaik_leitung, org.leuchtturm, org.nord)

    assert dialog_notices(response) == [OG5_MESSAGE]
    assert fresh(org.leuchtturm).parent_id == org.kueste.pk
    assert entries(start) == []


def test_og5_auch_das_datenmodell_lehnt_den_ringwechsel_ab(org):
    """Weitere Stelle: Auch Befehle und spätere Seiten kommen nicht an der Regel vorbei (#89)."""
    give(org.leuchtturm_leitung, R.RING_LEAD, org.kueste)
    leuchtturm = Unit.objects.get(pk=org.leuchtturm.pk)
    leuchtturm.parent = org.nord

    with pytest.raises(ValidationError):
        leuchtturm.save(by=BY)

    assert fresh(org.leuchtturm).parent_id == org.kueste.pk


def test_ringwechsel_mit_leitung_aus_dem_alten_ring_wird_abgelehnt(org):
    """Risikovariante: Wer direkt Mitglied von Küste ist, darf Leuchtturm leiten, nach dem Wechsel nicht mehr (#89)."""
    rita = lead("rita.ring", R.RING_LEAD, org.kueste)
    give(rita, R.TROOP_LEAD, org.leuchtturm)

    response = change_ring(org.mosaik_leitung, org.leuchtturm, org.nord)

    assert "Stammesleitung von Stamm Leuchtturm" in dialog_notices(response)[0]
    assert fresh(org.leuchtturm).parent_id == org.kueste.pk


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("moving_first", [True, False])
def test_og9_mona_benennt_lars_und_verschiebt_leuchtturm_gleichzeitig(transactional_db, org, moving_first):
    """OG9: Genau eins von beidem wird gespeichert; das andere mit derselben Meldung wie nacheinander."""
    first, second = (
        (lambda: Rights(org.mosaik_leitung).change_ring(org.leuchtturm, org.nord.key),
         lambda: Rights(org.mosaik_leitung).appoint(org.kueste, org.leuchtturm_leitung.key))
    )
    if not moving_first:
        first, second = second, first

    results = _one_after_the_other(first, second)

    _assert_exactly_one(org, results, moving_first)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("moving_first", [True, False])
def test_og9_auch_wenn_kai_benennt_und_mona_verschiebt(transactional_db, org, moving_first):
    """Risikovariante zu OG9: Zwei verschiedene Konten sperren sich nicht gegenseitig; es zählt die gemeinsame Sperre."""
    first, second = (
        (lambda: Rights(org.mosaik_leitung).change_ring(org.leuchtturm, org.nord.key),
         lambda: Rights(org.kueste_leitung).appoint(org.kueste, org.leuchtturm_leitung.key))
    )
    if not moving_first:
        first, second = second, first

    results = _one_after_the_other(first, second)

    _assert_exactly_one(org, results, moving_first)


def _assert_exactly_one(org, results, moving_first: bool) -> None:
    move_result, appoint_result = results if moving_first else results[::-1]
    lars_leads_kueste = Role.objects.filter(user=org.leuchtturm_leitung, kind=R.RING_LEAD, unit=org.kueste).exists()
    in_nord = fresh(org.leuchtturm).parent_id == org.nord.pk
    if moving_first:
        assert move_result[0] is True
        assert appoint_result == (False, NOT_ON_PATH_LARS)
        assert (in_nord, lars_leads_kueste) == (True, False)
    else:
        assert appoint_result[0] is True
        assert move_result[0] is False
        assert "Laterne (Lars Leuchtturm) ist Ringleitung von Ring Küste." in move_result[1]
        assert (in_nord, lars_leads_kueste) == (False, True)


# ---------- Einspringen ----------


@pytest.mark.rechtematrix("EH-18", "EH-11", "EH-14")
def test_o9_nele_legt_in_sturmvogel_eine_gruppe_an_und_benennt_sie_um(org):
    assert create(org.nord_leitung, org.sturmvogel, "Sippe Sturm").status_code == 302
    sturm = Unit.objects.get(name="Sippe Sturm")
    assert rename(org.nord_leitung, sturm, "Sippe Orkan").status_code == 302

    assert fresh(sturm).name == "Sippe Orkan"


@pytest.mark.rechtematrix("EH-18")
def test_o9_ohne_ringleitung_legt_mona_in_ring_nord_einen_stamm_an(org):
    remove(org.nord_leitung, R.RING_LEAD, org.nord)

    assert create(org.mosaik_leitung, org.nord, "Brandung").status_code == 302

    assert (U.TROOP, "Brandung") in children(org.nord)


@pytest.mark.rechtematrix("EH-19")
def test_mit_neuer_ringleitung_endet_das_einspringen_beim_naechsten_klick(org):
    remove(org.nord_leitung, R.RING_LEAD, org.nord)
    client = client_for(org.mosaik_leitung)
    assert create(org.mosaik_leitung, org.nord, "Brandung", client=client).status_code == 302

    give(org.nord_leitung, R.RING_LEAD, org.nord)

    assert create(org.mosaik_leitung, org.nord, "Klippe", client=client).status_code == 404
    assert not Unit.objects.filter(name="Klippe").exists()


@pytest.mark.rechtematrix("EH-18")
def test_o10_im_gemischten_uebergang_springt_bruno_fuer_die_zugvoegel_ein(org):
    introduce_rings(org.bundesleitung, org.boreas)
    remove(org.zugvoegel_leitung, R.TROOP_LEAD, org.zugvoegel)
    rights = Rights(org.bundesleitung)

    assert rights.covers(org.zugvoegel)
    assert rights.may_admit(org.zugvoegel)
    assert create(org.bundesleitung, org.zugvoegel, "Sippe Möwen").status_code == 302
    assert fresh(org.zugvoegel).parent_id == org.boreas.pk


# ---------- Allgemein ----------


def _routes() -> list[str]:
    return [str(pattern.pattern) for pattern in get_resolver().url_patterns]


@pytest.mark.rechtematrix("EH-21")
def test_ov10_es_gibt_keinen_loeschknopf_und_keine_adresse_zum_loeschen(org):
    root = page_tree(org.bundesleitung, unit_address(org.walhall))

    assert "Löschen" not in _visible_text(root)
    assert not [route for route in _routes() if "loesch" in route or "lösch" in route]
    assert create(org.bundesleitung, org.walhall, "Rotte Biber").status_code == 302


def test_abgelehnte_versuche_schreiben_nichts_ins_protokoll(org):
    """OG6: über alle vier Handlungen hinweg, auch bei Ablehnung mit Meldung."""
    start = mark()

    create(org.walhall_leitung, org.walhall, "Sippe Falken")
    rename(org.walhall_leitung, org.falken, "Meute Wölfe")
    rename(org.falken_leitung, org.walhall, "Fremd")
    change_ring(org.kueste_leitung, org.leuchtturm, org.nord)
    introduce_rings(org.walhall_leitung, org.boreas)

    assert entries(start) == []
