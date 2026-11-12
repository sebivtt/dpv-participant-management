"""Tests für angezeigte Leitungsrollen verwalteter Personen (#99, PER-07).

Die Kennungen L1 bis L9, LV1 bis LV6, LG1 bis LG4 und U1 bis U3 verweisen auf die Szenarien vom
11.11.2026 (https://github.com/sebivtt/dpv-participant-management/issues/99#issuecomment-6789880932), die
Wortlaute auf den Text von #99. Personen und Organisationen wie in den Tests zu #117 und #118
(`tests/test_verwaltete_personen.py`): Wanda und Willi leiten Walhall, Fiete die Sippe Falken, Wim die
Meute Wölfe (er ist direkt Mitglied von Walhall), Zora die Zugvögel, Bruno Boreas, Vera ist
Verbandsleitung, Tom im DPV-Veranstaltungsteam, Otto ohne Zuordnung, Max Admin; Finn ist Mitglied der
Sippe Falken. Das Mitglied der Meute heißt in diesen Tests Wiebke (in den Szenarien Moritz). Verwaltet
sind Tim Probe (Meute Wölfe, ohne Fahrtennamen), Paul Probe (Stamm Walhall), Lena Probe „Kiwi“ (Sippe
Falken) und Berta Probe (direkt im Bund Boreas). Alle Namen sind erfunden.

Prüfgrundsatz der Szenarien: Die Organisation kommt immer aus der Adresse, nie aus dem Formular. Jeder
unberechtigte Aufruf wird direkt, aus dem Skript und mit manipuliertem Formular geprüft (`refused()`).
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404
from django.test import Client

from access.rights import Rights
from persons.models import DisplayedLead, ManagedPerson
from roles.models import AdminAccess, Role, RoleChange
from tests import test_verwaltete_personen
from tests.test_benennen import _one_after_the_other, appoint_address, dialog_of, hits, notices, search
from tests.test_benennen import short_notices, suggest
from tests.test_entfernen import buttons, confirmation
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, leads_notice, leads_on_page, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person
from tests.test_verband import bunds
from tests.query_limit import assert_queries_do_not_grow
from tests.test_verschieben import move_dialog
from tests.test_verwaltete_personen import entries, managed
from tests.test_verwaltete_personen_verschieben import delete, move

R = Role.Kind
pytestmark = pytest.mark.django_db

# Die Fixtures aus tests/test_verwaltete_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_verwaltete_personen.base_org
org_189 = test_verwaltete_personen.org_189
org_190 = test_verwaltete_personen.org_190
org_285 = test_verwaltete_personen.org_285
org_117 = test_verwaltete_personen.org

ONLY_DISPLAY = "ohne Konto, nur Anzeige"
TIM_HINT = "Tim Probe hat kein Konto. Die Rolle wird nur angezeigt und gibt keine Rechte."
TIM_APPOINTED = "Tim Probe ist jetzt Gruppenleitung von Meute Wölfe."
TIM_ALREADY = "Tim Probe ist schon Gruppenleitung von Meute Wölfe."
TIM_QUESTION = "Tim Probe als Gruppenleitung von Meute Wölfe entfernen?"
TIM_REMOVED = "Tim Probe ist nicht mehr Gruppenleitung von Meute Wölfe."
TIM_ROLE = "Gruppenleitung Meute Wölfe (nur Anzeige)"
LENA_OFF_PATH = "Kiwi (Lena Probe) gehört zu Sippe Falken und kann deshalb keine Leitung bei Stamm Zugvögel sein."
BERTA_BLOCKED = ("Berta Probe ist Stammesleitung von Stamm Zugvögel. Diese Rolle passt nicht zu Stamm Walhall. "
                 "Sie kann zuerst beendet werden.")


@pytest.fixture
def org(org_117):
    """Die Personen aus #117 mit Paul, dazu Tim, Lena und Berta wie in den Szenarien."""
    org = org_117
    org.tim = managed("Tim", "Probe", org.woelfe, born=date(2016, 6, 6))
    org.lena = managed("Lena", "Probe", org.falken, scout_name="Kiwi", born=date(2015, 5, 14))
    org.berta = managed("Berta", "Probe", org.boreas, born=date(2001, 1, 1))
    return org


# ---------- Hilfen ----------


def appoint_managed(user, where, target, client=None, **more):
    """„Benennen“ neben einer verwalteten Person im Dialog, wie der Knopf es abschickt; `more` sind weitere Felder."""
    form = {"person": target.key, "verwaltet": "ja", **more}
    return (client or client_for(user)).post(appoint_address(where), form)


def remove_address(where, entry: DisplayedLead) -> str:
    return f"{unit_address(where)}entfernen-anzeige/{entry.key}/"


def displayed(person: ManagedPerson) -> set[tuple[str, str]]:
    return set(DisplayedLead.objects.filter(person=person).values_list("kind", "unit__name"))


def displayed_of(person: ManagedPerson, kind: str, where) -> DisplayedLead:
    return DisplayedLead.objects.get(person=person, kind=kind, unit=where)


def show(person: ManagedPerson, kind: str, where) -> DisplayedLead:
    """Eine angezeigte Leitungsrolle, wie sie nach dem Eintragen gespeichert ist."""
    return DisplayedLead.objects.create(person=person, kind=kind, unit=where)


def managed_hits(root) -> dict[str, dict]:
    """Vorschläge im Dialog: wie `hits()`, dazu die Marken und ob der Knopf eine verwaltete Person schickt."""
    found = {}
    for entry in _all(root, lambda e: "a-treffer" in _classes(e) and e.name == "li"):
        name = _visible_text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        fields = _by_tag(entry, "input", name="verwaltet")
        found[name] = {
            "text": " ".join(_visible_text(entry).split()),
            "marks": [_visible_text(mark) for mark in _all(entry, lambda e: "a-kennmarke" in _classes(e))],
            "managed": bool(fields) and _attr(fields[0], "value") == "ja",
        }
    return found


def lead_texts(user, where) -> dict[str, str]:
    """Je Eintrag unter „Leitungen“ der sichtbare Text, ohne doppelte Leerzeichen."""
    return {entry["name"]: " ".join(entry["text"].split()) for entry in leads_on_page(page_tree(user, unit_address(where)))}


def refused(user, address: str, form: dict) -> None:
    """Die Adresse ist für `user` wie nicht vorhanden: direkt, aus dem Skript und mit manipuliertem Formular."""
    assert_like_missing(user, address)
    script = Client()
    script.force_login(user)
    assert script.post(address, form, headers={"x-requested-with": "fetch"}).status_code == 404, user.username
    manipulated = {**form, "unit": "b" * 20, "organisation": "b" * 20}
    assert client_for(user).post(address, manipulated).status_code == 404, user.username


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VP-14", "RO-09")
def test_l1_wanda_traegt_tim_als_angezeigte_gruppenleitung_der_woelfe_ein(org):
    client = client_for(org.walhall_leitung)
    found = managed_hits(suggest(org.walhall_leitung, org.woelfe, "Tim"))
    assert found["Tim Probe"]["marks"] == ["verwaltet"]
    assert TIM_HINT in found["Tim Probe"]["text"]
    assert found["Tim Probe"]["managed"] is True
    before = RoleChange.objects.count()

    response = appoint_managed(org.walhall_leitung, org.woelfe, org.tim, client=client)

    assert response.status_code == 302
    assert response.url == unit_address(org.woelfe)
    assert short_notices(client.get(response.url)) == [TIM_APPOINTED]
    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}
    assert f"Tim Probe · {ONLY_DISPLAY}" in lead_texts(org.walhall_leitung, org.woelfe)["Tim Probe"]
    assert TIM_ROLE in entries(page_tree(org.walhall_leitung, unit_address(org.woelfe)))["Tim Probe"]["text"]
    # Eine Rolle mit Konto ist es nicht, und ins Protokoll der Rollenänderungen kommt nichts (L9).
    assert not Role.objects.filter(unit=org.woelfe, kind=R.GROUP_LEAD).exclude(user=org.woelfe_leitung).exists()
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("VP-14")
def test_l2_wim_traegt_tim_als_weitere_angezeigte_gruppenleitung_ein(org):
    response = appoint_managed(org.woelfe_leitung, org.woelfe, org.tim)

    assert response.status_code == 302
    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}
    shown = lead_texts(org.woelfe_leitung, org.woelfe)
    assert set(shown) == {"Wim Wolf", "Tim Probe"}


@pytest.mark.rechtematrix("VP-14")
def test_l3_bruno_traegt_paul_als_angezeigte_stammesleitung_von_walhall_ein(org):
    client = client_for(org.bundesleitung)
    assert "Paul Probe" in managed_hits(suggest(org.bundesleitung, org.walhall, "Paul"))

    response = appoint_managed(org.bundesleitung, org.walhall, org.paul, client=client)

    assert response.status_code == 302
    assert short_notices(client.get(response.url)) == ["Paul Probe ist jetzt Stammesleitung von Walhall."]
    assert displayed(org.paul) == {(R.TROOP_LEAD, "Walhall")}


@pytest.mark.rechtematrix("RO-09")
def test_l4_mitglieder_sehen_die_angezeigten_rollen_ihrer_kette_nur_mit_name_und_rolle(org):
    show(org.tim, R.GROUP_LEAD, org.woelfe)
    show(org.paul, R.TROOP_LEAD, org.walhall)

    for_wiebke = Rights(org.wolf).displayed_leads()
    for_finn = Rights(org.falke).displayed_leads()

    assert {(entry["first_name"], entry["kind"], entry["unit_name"]) for entry in for_wiebke} == {
        ("Tim", R.GROUP_LEAD, "Meute Wölfe"), ("Paul", R.TROOP_LEAD, "Walhall")}
    # Finn sieht Paul über Walhall; die Meute liegt nicht auf seiner Kette (RO-04).
    assert {(entry["first_name"], entry["kind"]) for entry in for_finn} == {("Paul", R.TROOP_LEAD)}
    allowed = {"kind", "first_name", "last_name", "scout_name", "unit_name", "unit_key", "role_key"}
    for entry in [*for_wiebke, *for_finn]:
        assert set(entry) <= allowed
        assert "birth_date" not in entry


@pytest.mark.rechtematrix("RO-09")
def test_l4_fiete_sieht_paul_auf_der_leseseite_von_walhall_ohne_knopf(org):
    show(org.paul, R.TROOP_LEAD, org.walhall)

    shown = lead_texts(org.falken_leitung, org.walhall)

    assert f"Paul Probe · {ONLY_DISPLAY}" in shown["Paul Probe"]
    assert "Stammesleitung" in shown["Paul Probe"]
    assert "Paul Probe" not in buttons(org.falken_leitung, org.walhall)
    # Den Abschnitt „Personen“ gibt es auf der Leseseite nicht; Pauls Geburtsdatum steht nirgends.
    page = client_for(org.falken_leitung).get(unit_address(org.walhall)).content.decode()
    assert "2012" not in page


@pytest.mark.rechtematrix("VP-14", "RO-09")
def test_l5_bruno_traegt_berta_als_bundesleitung_ein_und_vera_sieht_sie_auf_der_seite_verband(org):
    response = appoint_managed(org.bundesleitung, org.boreas, org.berta)

    assert response.status_code == 302
    assert displayed(org.berta) == {(R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas")}
    shown = bunds(page_tree(org.verbandsleitung, "/organisation/"))["Pfadfinderbund Boreas"]
    berta = [" ".join(text.split()) for text in shown["leads"] if "Berta Probe" in text]
    assert len(berta) == 1
    assert f"Berta Probe · {ONLY_DISPLAY}" in berta[0]
    assert "Entfernen" not in berta[0]


@pytest.mark.rechtematrix("VP-14")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/entfernen-anzeige/<key:role>/")
def test_l6_wanda_entfernt_tims_angezeigte_rolle_und_tim_bleibt_in_der_meute(org):
    entry = show(org.tim, R.GROUP_LEAD, org.woelfe)
    assert buttons(org.walhall_leitung, org.woelfe)["Tim Probe"] == ("Entfernen", remove_address(org.woelfe, entry))
    client = client_for(org.walhall_leitung)
    response = client.get(remove_address(org.woelfe, entry))
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    assert _visible_text(_one(_by_tag(dialog, "h2"))) == TIM_QUESTION
    before = RoleChange.objects.count()

    response = client.post(remove_address(org.woelfe, entry))

    assert response.status_code == 302
    assert response.url == unit_address(org.woelfe)
    assert short_notices(client.get(response.url)) == [TIM_REMOVED]
    assert displayed(org.tim) == set()
    assert ManagedPerson.objects.get(pk=org.tim.pk).unit_id == org.woelfe.pk
    assert RoleChange.objects.count() == before
    # Ein zweites Abschicken findet die Rolle nicht mehr, wie bei einer, die es nie gab.
    assert client.post(remove_address(org.woelfe, entry)).status_code == 404
    assert_like_missing(org.walhall_leitung, remove_address(org.woelfe, entry))


@pytest.mark.rechtematrix("VP-16")
def test_l7_ist_tim_die_einzige_leitung_springt_wanda_ein(org):
    show(org.tim, R.GROUP_LEAD, org.woelfe)
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)

    root = page_tree(org.walhall_leitung, unit_address(org.woelfe))

    assert [entry["name"] for entry in leads_on_page(root)] == ["Tim Probe"]
    assert "springt die Stammesleitung von Walhall ein" in leads_notice(root)
    wanda = Rights(org.walhall_leitung)
    assert wanda.covers(org.woelfe)
    assert not wanda.has_lead(org.woelfe)
    assert wanda.may_admit(org.woelfe) and wanda.may_add_managed(org.woelfe) and wanda.may_delete_managed(org.woelfe)


def test_l8_wird_tim_geloescht_verschwindet_seine_angezeigte_rolle(org):
    show(org.tim, R.GROUP_LEAD, org.woelfe)

    response = delete(org.woelfe_leitung, org.woelfe, org.tim)

    assert response.status_code == 302
    assert not ManagedPerson.objects.filter(pk=org.tim.pk).exists()
    assert not DisplayedLead.objects.exists()
    assert "Tim Probe" not in lead_texts(org.walhall_leitung, org.woelfe)


def test_l9_eintragen_und_entfernen_kommen_nicht_ins_protokoll_der_rollenaenderungen(org):
    before = RoleChange.objects.count()

    assert appoint_managed(org.walhall_leitung, org.woelfe, org.tim).status_code == 302
    entry = displayed_of(org.tim, R.GROUP_LEAD, org.woelfe)
    assert client_for(org.walhall_leitung).post(remove_address(org.woelfe, entry)).status_code == 302

    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("VP-14")
def test_im_support_zugang_traegt_max_ein_und_es_steht_im_protokoll_der_admin_zugriffe(org):
    Rights(org.max).start_support(org.walhall, "lead_request")

    response = appoint_managed(org.max, org.woelfe, org.tim)

    assert response.status_code == 302
    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}
    assert AdminAccess.objects.filter(actor_id=org.max.pk, action=AdminAccess.Action.CHANGED).count() == 1


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VP-14", "VP-15")
def test_lv1_lena_steht_bei_den_zugvoegeln_nicht_zur_wahl_und_ein_manipuliertes_formular_lehnt_ab(org):
    assert "Kiwi" not in managed_hits(suggest(org.bundesleitung, org.zugvoegel, "Kiwi"))
    assert "Kiwi" not in managed_hits(suggest(org.bundesleitung, org.zugvoegel, "Lena"))
    # Gegenprobe: bei den Falken schlägt das Tool sie Bruno vor.
    assert "Kiwi" in managed_hits(suggest(org.bundesleitung, org.falken, "Kiwi"))

    response = appoint_managed(org.bundesleitung, org.zugvoegel, org.lena)

    assert response.status_code == 200
    assert LENA_OFF_PATH in notices(dialog_of(_tree(response)))
    assert displayed(org.lena) == set()


@pytest.mark.rechtematrix("VP-15")
def test_lv2_fiete_hat_auf_walhall_keinen_knopf_und_traegt_nichts_ein(org):
    root = _one(_by_tag(page_tree(org.falken_leitung, unit_address(org.walhall)), "section", aria_labelledby="h-leitungen"))
    assert not _all(root, lambda e: "a-flaeche-aktion" in _classes(e))

    refused(org.falken_leitung, appoint_address(org.walhall), {"person": org.paul.key, "verwaltet": "ja"})

    assert displayed(org.paul) == set()


@pytest.mark.rechtematrix("VP-15")
def test_lv3_zora_sieht_tim_nicht_und_traegt_bei_ihm_nichts_ein(org):
    entry = show(org.tim, R.GROUP_LEAD, org.woelfe)

    refused(org.zugvoegel_leitung, appoint_address(org.woelfe), {"person": org.tim.key, "verwaltet": "ja"})
    refused(org.zugvoegel_leitung, remove_address(org.woelfe, entry), {})
    # Auch bei den eigenen Zugvögeln: Tim ist für Zora „nicht gefunden“.
    assert appoint_managed(org.zugvoegel_leitung, org.zugvoegel, org.tim).status_code == 404
    assert "Tim Probe" not in managed_hits(suggest(org.zugvoegel_leitung, org.zugvoegel, "Tim"))

    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}


@pytest.mark.rechtematrix("VP-15")
def test_lv4_vera_tom_otto_und_max_ohne_support_zugang_tragen_nichts_ein(org):
    entry = show(org.tim, R.GROUP_LEAD, org.woelfe)

    for user in (org.verbandsleitung, org.team, org.ohne, org.max):
        refused(user, appoint_address(org.woelfe), {"person": org.tim.key, "verwaltet": "ja"})
        refused(user, remove_address(org.woelfe, entry), {})
    # Die Verbandsleitung findet verwaltete Personen weder über Vorschläge noch über den Dialog „Bundesleitung benennen“.
    assert Rights(org.verbandsleitung).suggestions("Berta") == []
    vera = client_for(org.verbandsleitung)
    assert vera.post(f"/organisation/verband/bund/{org.boreas.key}/benennen/",
                     {"person": org.berta.key, "verwaltet": "ja"}).status_code == 404

    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}
    assert displayed(org.berta) == set()


@pytest.mark.rechtematrix("VP-16")
def test_lv5_eine_angezeigte_rolle_gibt_in_der_rechtepruefung_keine_rechte(org):
    show(org.tim, R.GROUP_LEAD, org.woelfe)
    show(org.paul, R.TROOP_LEAD, org.walhall)
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove(org.willi, R.TROOP_LEAD, org.walhall)

    rights = Rights(org.bundesleitung)

    # Walhall und die Meute gelten als ohne Leitung; für beide springt Bruno ein.
    assert not rights.has_lead(org.walhall) and not rights.has_lead(org.woelfe)
    assert rights.covers(org.walhall) and rights.covers(org.woelfe)
    assert rights.covering_unit(org.woelfe) == org.boreas.pk


@pytest.mark.rechtematrix("VP-16")
def test_lv5_wird_wim_als_letzte_leitung_mit_konto_entfernt_kommt_der_hinweis_trotz_tim(org):
    show(org.tim, R.GROUP_LEAD, org.woelfe)
    wim = Role.objects.get(user=org.woelfe_leitung, kind=R.GROUP_LEAD, unit=org.woelfe)

    found = confirmation(org.walhall_leitung, org.woelfe, wim)

    assert any("Danach hat" in line and "keine Gruppenleitung mehr" in line for line in found["text"])


@pytest.mark.rechtematrix("VP-14", "VP-15")
def test_lv6_eine_organisation_im_formular_wird_nicht_beachtet(org):
    response = appoint_managed(org.walhall_leitung, org.woelfe, org.tim, unit=org.falken.key,
                               organisation=org.falken.key, kind=R.TROOP_LEAD)

    assert response.status_code == 302
    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}
    entry = displayed_of(org.tim, R.GROUP_LEAD, org.woelfe)
    # Entfernen unter der Adresse einer anderen Organisation findet die Rolle nicht, auch mit ihr im Formular.
    wanda = client_for(org.walhall_leitung)
    assert wanda.post(remove_address(org.falken, entry), {"unit": org.woelfe.key}).status_code == 404
    assert displayed(org.tim) == {(R.GROUP_LEAD, "Meute Wölfe")}


# ---------- Grenzfälle ----------


@pytest.mark.rechtematrix("VP-14")
def test_lg1_dieselbe_rolle_ein_zweites_mal(org):
    assert appoint_managed(org.walhall_leitung, org.woelfe, org.tim).status_code == 302

    response = appoint_managed(org.walhall_leitung, org.woelfe, org.tim)

    assert response.status_code == 200
    assert TIM_ALREADY in notices(dialog_of(_tree(response)))
    assert DisplayedLead.objects.filter(person=org.tim).count() == 1


@pytest.mark.rechtematrix("VP-14")
def test_lg2_berta_mit_angezeigter_rolle_bei_den_zugvoegeln_laesst_sich_nicht_nach_walhall_verschieben(org):
    assert appoint_managed(org.bundesleitung, org.boreas, org.berta).status_code == 302
    assert appoint_managed(org.bundesleitung, org.zugvoegel, org.berta).status_code == 302
    before = RoleChange.objects.count()

    response = move(org.bundesleitung, org.boreas, org.berta, org.walhall)

    found = move_dialog(response)
    assert BERTA_BLOCKED in found["notices"]
    # Das abgelehnte Ziel bleibt gewählt, wie bei Personen mit Konto (PK-25).
    assert [value for _name, value, _label, checked in found["options"] if checked] == [org.walhall.key]
    assert ManagedPerson.objects.get(pk=org.berta.pk).unit_id == org.boreas.pk
    assert RoleChange.objects.count() == before

    response = move(org.bundesleitung, org.boreas, org.berta, org.zugvoegel)

    assert response.status_code == 302
    assert ManagedPerson.objects.get(pk=org.berta.pk).unit_id == org.zugvoegel.pk
    assert displayed(org.berta) == {(R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"), (R.TROOP_LEAD, "Zugvögel")}


def test_lg2_auch_am_modell_vorbei_laesst_sich_berta_nicht_vom_pfad_verschieben(org):
    show(org.berta, R.TROOP_LEAD, org.zugvoegel)
    org.berta.unit = org.walhall

    with pytest.raises(ValidationError, match="Stamm Zugvögel"):
        org.berta.save()

    assert ManagedPerson.objects.get(pk=org.berta.pk).unit_id == org.boreas.pk


def test_lg2_auch_am_modell_vorbei_gibt_es_keine_rolle_neben_dem_pfad(org):
    with pytest.raises(ValidationError, match="Stamm Zugvögel"):
        show(org.lena, R.TROOP_LEAD, org.zugvoegel)

    assert displayed(org.lena) == set()


@pytest.mark.django_db(transaction=True)
def test_lg3_wanda_und_willi_tragen_tim_gleichzeitig_ein():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    tim = managed("Tim", "Probe", o.woelfe)

    results = _one_after_the_other(lambda: Rights(wanda).appoint_displayed(o.woelfe, tim.key),
                                   lambda: Rights(willi).appoint_displayed(o.woelfe, tim.key))

    assert sorted(results) == [(False, TIM_ALREADY), (True, TIM_APPOINTED)]
    assert DisplayedLead.objects.filter(person=tim).count() == 1


@pytest.mark.django_db(transaction=True)
def test_lg4_wird_tim_bei_offenem_dialog_geloescht_ist_er_nicht_gefunden():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    wim = person("wim.wolf", "Wim", "Wolf")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(wim, R.GROUP_LEAD, o.woelfe)
    tim = managed("Tim", "Probe", o.woelfe)

    def appointing():
        try:
            return Rights(wanda).appoint_displayed(o.woelfe, tim.key)
        except Http404:
            return "nicht gefunden"

    results = _one_after_the_other(lambda: Rights(wim).delete_managed(o.woelfe, tim.key), appointing)

    assert "nicht gefunden" in results
    assert not ManagedPerson.objects.filter(pk=tim.pk).exists()
    assert not DisplayedLead.objects.exists()


def test_lg4_nach_dem_loeschen_ergibt_das_eintragen_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)
    assert client.get(appoint_address(org.woelfe)).status_code == 200
    tim_key = org.tim.key
    assert delete(org.woelfe_leitung, org.woelfe, org.tim).status_code == 302

    assert client.post(appoint_address(org.woelfe), {"person": tim_key, "verwaltet": "ja"}).status_code == 404
    assert not DisplayedLead.objects.exists()


# ---------- Was bleibt unverändert? ----------


def test_u1_die_suche_ueber_mail_oder_benutzernamen_findet_weiter_nur_konten(org):
    for text in ("Tim Probe", "tim", "Tim"):
        found = search(org.walhall_leitung, org.woelfe, text)
        assert "Tim Probe" not in hits(found)
        assert Rights(org.walhall_leitung).find_accounts(text) == []
    # Benennen mit Konto bleibt, wie es war: Finn wird Gruppenleitung der Falken, mit Eintrag im Protokoll.
    before = RoleChange.objects.count()
    response = client_for(org.walhall_leitung).post(appoint_address(org.falken), {"person": org.falke.key})
    assert response.status_code == 302
    assert Role.objects.filter(user=org.falke, kind=R.GROUP_LEAD, unit=org.falken).exists()
    assert RoleChange.objects.count() == before + 1
    assert not DisplayedLead.objects.exists()


def test_u1_die_kennung_einer_verwalteten_person_benennt_ohne_feld_verwaltet_niemanden(org):
    response = client_for(org.walhall_leitung).post(appoint_address(org.woelfe), {"person": org.tim.key})

    assert response.status_code == 404
    assert not DisplayedLead.objects.exists()


def test_u1_die_kennung_eines_kontos_traegt_keine_angezeigte_rolle_ein(org):
    response = client_for(org.walhall_leitung).post(appoint_address(org.woelfe), {"person": org.wolf.key,
                                                                                    "verwaltet": "ja"})

    assert response.status_code == 404
    assert not DisplayedLead.objects.exists()
    assert not Role.objects.filter(user=org.wolf, kind=R.GROUP_LEAD).exists()


def test_u2_u3_eine_angezeigte_rolle_aendert_weder_einspringen_noch_rechte_noch_protokoll(org):
    before = RoleChange.objects.count()
    wanda_before = Rights(org.walhall_leitung)
    covered_before = {unit.name for unit in (org.woelfe, org.falken) if wanda_before.covers(unit)}

    show(org.tim, R.GROUP_LEAD, org.woelfe)
    show(org.lena, R.GROUP_LEAD, org.falken)

    wanda = Rights(org.walhall_leitung)
    assert {unit.name for unit in (org.woelfe, org.falken) if wanda.covers(unit)} == covered_before
    assert wanda.leads_unit(org.woelfe) == wanda_before.leads_unit(org.woelfe)
    assert RoleChange.objects.count() == before


def test_die_liste_der_leitungen_fragt_die_datenbank_nicht_je_angezeigter_rolle(org):
    def add(number: int):
        entry = managed(f"Tom{number}", "Probe", org.woelfe)
        show(entry, R.GROUP_LEAD, org.woelfe)

    assert_queries_do_not_grow(add, lambda: client_for(org.walhall_leitung).get(unit_address(org.woelfe)))
