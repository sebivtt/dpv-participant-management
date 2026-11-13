"""Tests für „Leitung entfernen“ und „Rolle abgeben“ auf der Seite einer Organisation (#191, Teil 3 von #93).

Die Nummern C1 bis C13 und CV1 bis CV8 verweisen auf Sebastians Szenarien vom 27.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/191), die Antworten bei der
Umsetzung auf seinen Kommentar vom 28.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/191#issuecomment-6476276104).
Personen und Einheiten wie in den Tests zu #190 (`tests/test_benennen.py`); Fahrtennamen und Mails
sind erfunden. Geprüft wird, was beim Browser ankommt, und was danach in der Datenbank steht.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.http import Http404

from access.rights import Rights
from roles.models import Role, RoleChange
from tests import test_benennen, test_organisation
from tests.test_benennen import _one_after_the_other, appoint, dialog_of, roles_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, leads_on_page, lock, nav_labels, page_tree, unit_address, unlock
from tests.test_rechtepruefung import remove as remove_by_command
from tests.test_rollen import build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures aus tests/test_organisation.py und tests/test_benennen.py unter eigenem Namen.
base_org = test_organisation.base_org
org_189 = test_organisation.org
org = test_benennen.org


def role_of(user, kind, where) -> Role:
    return Role.objects.get(user=user, kind=kind, unit=where)


def remove_address(where, role: Role) -> str:
    return f"{unit_address(where)}entfernen/{role.key}/"


def remove(user, where, role: Role, client=None):
    """„Entfernen“ oder „Rolle abgeben“ im Dialog bestätigen, wie der rote Knopf es abschickt."""
    return (client or client_for(user)).post(remove_address(where, role))


def buttons(user, where) -> dict[str, tuple[str, str]]:
    """Je Leitung unter „Leitungen“ die Beschriftung und Adresse ihres Knopfs; ohne Knopf fehlt sie."""
    root = page_tree(user, unit_address(where))
    found = {}
    for entry in _all(root, lambda e: "a-leitung" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        links = _all(entry, lambda e: "a-leitung-knopf" in _classes(e))
        if links:
            found[name] = (_visible_text(_one(links)), _attr(_one(links), "href"))
    return found


def confirmation(user, where, role: Role) -> dict:
    """Der Dialog zur Bestätigung: Titel, Text darunter und der rote Knopf."""
    response = client_for(user).get(remove_address(where, role))
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    inner = _one(_all(dialog, lambda e: "a-dialog-inhalt" in _classes(e)))
    confirm = _one(_all(dialog, lambda e: "btn-gefahr" in _classes(e)))
    form = _one(_by_tag(dialog, "form", method="post"))
    return {
        "title": _visible_text(_one(_by_tag(dialog, "h2"))),
        "text": [_visible_text(entry) for entry in _by_tag(inner, "p")],
        "button": _visible_text(confirm),
        "action": _attr(form, "action"),
        "cancel": _attr(_one(_by_tag(_one(_all(dialog, lambda e: "a-dialog-fuss" in _classes(e))), "a")), "href"),
    }


def frida_for(o):
    """Frida als zweite Gruppenleitung der Falken, Mitglied der Falken (nur wo genannt)."""
    frida = person("frida.falke", "Frida", "Falke")
    frida.scout_name = "Feder"
    frida.save()
    give(frida, R.MEMBER, o.falken)
    give(frida, R.GROUP_LEAD, o.falken)
    return frida


# ---------- Wer welchen Knopf hat ----------


@pytest.mark.rechtematrix("RO-10", "RO-11", "RO-13", "RO-20")
def test_entfernen_bei_jeder_anderen_leitung_rolle_abgeben_nur_beim_eigenen_eintrag(org):
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)
    wanda = role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    willi = role_of(org.willi, R.TROOP_LEAD, org.walhall)

    assert buttons(org.walhall_leitung, org.falken) == {"Funke": ("Entfernen", remove_address(org.falken, fiete))}
    assert buttons(org.walhall_leitung, org.walhall) == {
        "Wirbelwind": ("Rolle abgeben", remove_address(org.walhall, wanda)),
        "Wiesel": ("Entfernen", remove_address(org.walhall, willi)),
    }
    assert buttons(org.bundesleitung, org.walhall) == {
        "Wirbelwind": ("Entfernen", remove_address(org.walhall, wanda)),
        "Wiesel": ("Entfernen", remove_address(org.walhall, willi)),
    }
    assert buttons(org.falken_leitung, org.falken) == {"Funke": ("Rolle abgeben", remove_address(org.falken, fiete))}
    assert buttons(org.kueste_leitung, org.leuchtturm) == {"Laterne": ("Entfernen", remove_address(
        org.leuchtturm, role_of(org.leuchtturm_leitung, R.TROOP_LEAD, org.leuchtturm)))}


@pytest.mark.rechtematrix("RO-13", "EH-28")
def test_cv1_auf_der_leseseite_gibt_es_keine_knoepfe(org):
    assert buttons(org.falken_leitung, org.walhall) == {}
    assert buttons(org.walhall_leitung, org.boreas) == {}
    assert buttons(org.kueste_leitung, org.mosaik) == {}


@pytest.mark.rechtematrix("RO-21")
def test_c11_auch_bei_der_gesperrten_leitung_steht_entfernen(org):
    lock(org.falken_leitung)

    assert list(buttons(org.walhall_leitung, org.falken)) == ["Funke"]
    assert buttons(org.walhall_leitung, org.falken)["Funke"][0] == "Entfernen"


# ---------- Bestätigung ----------


def test_c1_wanda_entfernt_fiete_die_letzte_gruppenleitung(org):
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)

    shown = confirmation(org.walhall_leitung, org.falken, fiete)

    assert shown["title"] == "Funke (Fiete Falke) als Gruppenleitung von Sippe Falken entfernen?"
    assert shown["text"] == ["Danach hat Sippe Falken keine Gruppenleitung mehr. Bis eine neue benannt ist, springt die "
                             "Leitung von Stamm Walhall ein. Trotzdem entfernen?"]
    assert shown["button"] == "Entfernen"
    assert shown["action"] == remove_address(org.falken, fiete)
    assert shown["cancel"] == unit_address(org.falken)


def test_c2_willi_entfernt_wanda_die_nicht_die_letzte_ist(org):
    shown = confirmation(org.willi, org.walhall, role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall))

    assert shown["title"] == "Wirbelwind (Wanda Walhall) als Stammesleitung von Walhall entfernen?"
    assert shown["text"] == []
    assert shown["button"] == "Entfernen"


@pytest.mark.rechtematrix("RO-20")
def test_c3_fiete_gibt_seine_rolle_ab(org):
    shown = confirmation(org.falken_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert shown["title"] == "Deine Rolle als Gruppenleitung von Sippe Falken abgeben?"
    assert shown["text"] == [
        "Du verlierst damit sofort den Zugriff auf die Personen von Sippe Falken.",
        "Danach hat Sippe Falken keine Gruppenleitung mehr. Bis eine neue benannt ist, springt die Leitung von Stamm "
        "Walhall ein. Trotzdem abgeben?",
    ]
    assert shown["button"] == "Rolle abgeben"


@pytest.mark.rechtematrix("RO-20")
def test_c4_bruno_gibt_als_einzige_bundesleitung_ab(org):
    shown = confirmation(org.bundesleitung, org.boreas, role_of(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas))

    assert shown["title"] == "Deine Rolle als Bundesleitung von Pfadfinderbund Boreas abgeben?"
    assert shown["text"] == [
        "Du verlierst damit sofort den Zugriff auf die Personen von Pfadfinderbund Boreas.",
        "Danach hat Pfadfinderbund Boreas keine Bundesleitung mehr, und niemand springt ein. Eine neue Bundesleitung "
        "kann nur die Verbandsleitung benennen. Trotzdem abgeben?",
    ]


def test_c5_bruno_entfernt_zora_die_letzte_stammesleitung(org):
    shown = confirmation(org.bundesleitung, org.zugvoegel, role_of(org.zugvoegel_leitung, R.TROOP_LEAD, org.zugvoegel))

    assert shown["title"] == "Zimt (Zora Zugvogel) als Stammesleitung von Zugvögel entfernen?"
    assert shown["text"] == ["Danach hat Zugvögel keine Stammesleitung mehr. Bis eine neue benannt ist, springt die "
                             "Leitung von Pfadfinderbund Boreas ein. Trotzdem entfernen?"]


def test_c6_kai_entfernt_lars(org):
    shown = confirmation(org.kueste_leitung, org.leuchtturm,
                         role_of(org.leuchtturm_leitung, R.TROOP_LEAD, org.leuchtturm))

    assert shown["text"] == ["Danach hat Leuchtturm keine Stammesleitung mehr. Bis eine neue benannt ist, springt die "
                             "Leitung von Ring Küste ein. Trotzdem entfernen?"]


def test_ohne_leitung_darueber_springt_niemand_ein(org):
    """Sebastians Antwort 2 vom 28.10.2026: kurzer Satz, wenn bis zum Bund niemand Leitung ist."""
    remove_by_command(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)
    remove_by_command(org.willi, R.TROOP_LEAD, org.walhall)

    shown = confirmation(org.walhall_leitung, org.walhall, role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall))

    assert shown["text"] == [
        "Du verlierst damit sofort den Zugriff auf die Personen von Walhall.",
        "Danach hat Walhall keine Stammesleitung mehr, und niemand springt ein. Trotzdem abgeben?",
    ]


def test_c11_die_gesperrte_letzte_leitung_hat_dieselbe_bestaetigung_wie_c1(org):
    lock(org.falken_leitung)

    shown = confirmation(org.walhall_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert shown["title"] == "Funke (Fiete Falke) als Gruppenleitung von Sippe Falken entfernen?"
    assert shown["text"] == ["Danach hat Sippe Falken keine Gruppenleitung mehr. Bis eine neue benannt ist, springt die "
                             "Leitung von Stamm Walhall ein. Trotzdem entfernen?"]


@pytest.mark.rechtematrix("RO-11", "RO-21")
def test_c12_frida_entfernt_den_gesperrten_fiete_ohne_warnung(org):
    frida = frida_for(org)
    lock(org.falken_leitung)

    shown = confirmation(frida, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert shown["title"] == "Funke (Fiete Falke) als Gruppenleitung von Sippe Falken entfernen?"
    assert shown["text"] == []


def test_gesperrte_leitungen_zaehlen_beim_satz_zur_letzten_leitung_nicht_mit(org):
    frida = frida_for(org)
    lock(org.falken_leitung)

    shown = confirmation(org.walhall_leitung, org.falken, role_of(frida, R.GROUP_LEAD, org.falken))

    assert shown["title"] == "Feder (Frida Falke) als Gruppenleitung von Sippe Falken entfernen?"
    assert shown["text"][0].startswith("Danach hat Sippe Falken keine Gruppenleitung mehr.")


def test_c9_abbrechen_aendert_nichts(org):
    before = RoleChange.objects.count()
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)

    shown = confirmation(org.walhall_leitung, org.falken, fiete)
    page = client_for(org.walhall_leitung).get(shown["cancel"])

    assert page.status_code == 200
    assert Role.objects.filter(pk=fiete.pk).exists()
    assert RoleChange.objects.count() == before


def test_der_dialog_steht_ueber_der_seite_der_organisation(org):
    root = _tree(client_for(org.walhall_leitung).get(
        remove_address(org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))))

    assert "Funke" in [lead["name"] for lead in leads_on_page(root)]
    dialog = dialog_of(root)
    assert _attr(dialog, "data-schliessen") == unit_address(org.falken)


# ---------- Danach ----------


@pytest.mark.rechtematrix("RO-10", "RO-14")
def test_c1_nach_dem_bestaetigen_ist_fiete_keine_leitung_mehr_und_bleibt_mitglied(org):
    before = RoleChange.objects.count()

    response = remove(org.walhall_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.falken)
    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken")}
    change = RoleChange.objects.get(kind=R.GROUP_LEAD, person_id=org.falken_leitung.pk, action="removed")
    assert (change.actor_id, change.unit_id, change.action) == (org.walhall_leitung.pk, org.falken.pk, "removed")
    assert RoleChange.objects.count() == before + 1
    assert mail.outbox == []


@pytest.mark.rechtematrix("RO-11")
def test_c2_willi_entfernt_wanda(org):
    response = remove(org.willi, org.walhall, role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall))

    assert response.status_code == 302
    assert roles_of(org.walhall_leitung) == {(R.MEMBER, "Walhall")}
    assert (R.TROOP_LEAD, "Walhall") in roles_of(org.willi)


@pytest.mark.rechtematrix("RO-10")
def test_c5_c6_bruno_und_kai_entfernen_leitungen_unter_sich(org):
    remove(org.bundesleitung, org.zugvoegel, role_of(org.zugvoegel_leitung, R.TROOP_LEAD, org.zugvoegel))
    remove(org.kueste_leitung, org.leuchtturm, role_of(org.leuchtturm_leitung, R.TROOP_LEAD, org.leuchtturm))
    remove(org.bundesleitung, org.adler, role_of(org.adler_leitung, R.GROUP_LEAD, org.adler))

    assert roles_of(org.zugvoegel_leitung) == {(R.MEMBER, "Zugvögel")}
    assert roles_of(org.leuchtturm_leitung) == {(R.MEMBER, "Leuchtturm")}
    assert roles_of(org.adler_leitung) == {(R.MEMBER, "Sippe Adler")}


def test_c13_danach_steht_die_kurze_meldung(org):
    client = client_for(org.walhall_leitung)

    response = remove(org.walhall_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken), client)

    page = client.get(response["Location"])
    assert short_notices(page) == ["Funke (Fiete Falke) ist nicht mehr Gruppenleitung von Sippe Falken."]
    assert "Funke" not in [lead["name"] for lead in leads_on_page(_tree(page))]
    assert short_notices(client.get(response["Location"])) == []


@pytest.mark.rechtematrix("RO-20", "EH-08")
def test_c13_wanda_gibt_ihre_letzte_rolle_ab_und_der_naechste_klick_zeigt_kein_zugriff(org):
    client = client_for(org.walhall_leitung)

    response = remove(org.walhall_leitung, org.walhall, role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall), client)

    assert roles_of(org.walhall_leitung) == {(R.MEMBER, "Walhall")}
    assert response.status_code == 302
    assert response["Location"] == "/profil/"
    profile = client.get(response["Location"])
    assert short_notices(profile) == ["Du bist nicht mehr Stammesleitung von Walhall."]
    assert "Organisation" not in nav_labels(_tree(profile))
    assert client.get("/organisation/").status_code == 403
    change = RoleChange.objects.get(kind=R.TROOP_LEAD, person_id=org.walhall_leitung.pk, action="removed")
    assert (change.actor_id, change.action) == (org.walhall_leitung.pk, "removed")


@pytest.mark.rechtematrix("RO-20")
def test_c3_nach_dem_abgeben_sieht_fiete_die_falken_hoechstens_lesend(org):
    """Fiete bleibt Mitglied der Falken; ohne Leitungsrolle hat er weder Menüpunkt noch Seite (AV9)."""
    client = client_for(org.falken_leitung)

    response = remove(org.falken_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken), client)

    assert response["Location"] == "/profil/"
    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken")}
    assert client.get(unit_address(org.falken)).status_code == 404


@pytest.mark.rechtematrix("RO-20")
def test_c8_fiete_gibt_die_falken_ab_und_behaelt_die_woelfe(org):
    give(org.falken_leitung, R.GROUP_LEAD, org.woelfe)
    client = client_for(org.falken_leitung)

    response = remove(org.falken_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken), client)

    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Meute Wölfe")}
    # Die Falken sieht er über seine Mitgliedschaft nur noch lesend, ohne Knöpfe (EH-28).
    assert response["Location"] == unit_address(org.falken)
    page = client.get(response["Location"])
    assert short_notices(page) == ["Du bist nicht mehr Gruppenleitung von Sippe Falken."]
    assert "Organisation" in nav_labels(_tree(page))
    assert buttons(org.falken_leitung, org.falken) == {}
    assert "Funke" in buttons(org.falken_leitung, org.woelfe)


def test_c7_otto_bleibt_nach_dem_entfernen_mitglied_von_walhall(org):
    appoint(org.walhall_leitung, org.walhall, org.ohne)
    assert roles_of(org.ohne) == {(R.MEMBER, "Walhall"), (R.TROOP_LEAD, "Walhall")}

    remove(org.walhall_leitung, org.walhall, role_of(org.ohne, R.TROOP_LEAD, org.walhall))

    assert roles_of(org.ohne) == {(R.MEMBER, "Walhall")}


def test_c10_fietes_offene_seite_zeigt_beim_naechsten_klick_nicht_gefunden(org):
    fiete = client_for(org.falken_leitung)
    assert fiete.get(unit_address(org.falken)).status_code == 200

    remove(org.walhall_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert fiete.get(unit_address(org.falken)).status_code == 404
    assert fiete.get("/organisation/").status_code == 403
    assert "Organisation" not in nav_labels(_tree(fiete.get("/profil/")))


@pytest.mark.rechtematrix("RO-21")
def test_c11_die_entfernte_rolle_kommt_nach_der_sperre_nicht_zurueck(org):
    lock(org.falken_leitung)

    response = remove(org.walhall_leitung, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))
    unlock(org.falken_leitung)

    assert response.status_code == 302
    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken")}
    assert client_for(org.falken_leitung).get("/organisation/").status_code == 403


def test_c12_frida_entfernt_den_gesperrten_fiete(org):
    frida = frida_for(org)
    lock(org.falken_leitung)

    remove(frida, org.falken, role_of(org.falken_leitung, R.GROUP_LEAD, org.falken))

    assert roles_of(org.falken_leitung) == {(R.MEMBER, "Sippe Falken")}
    assert (R.GROUP_LEAD, "Sippe Falken") in roles_of(frida)


# ---------- Verboten und manipuliert ----------


@pytest.mark.rechtematrix("RO-13")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/entfernen/<key:role>/")
def test_cv1_fiete_entfernt_wanda_nicht(org):
    wanda = role_of(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    assert_like_missing(org.falken_leitung, remove_address(org.walhall, wanda))

    assert Role.objects.filter(pk=wanda.pk).exists()


@pytest.mark.rechtematrix("RO-10", "RO-13")
def test_cv2_fiete_entfernt_wim_nicht_und_zora_entfernt_fiete_nicht(org):
    wim = role_of(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert_like_missing(org.falken_leitung, remove_address(org.woelfe, wim))
    assert_like_missing(org.zugvoegel_leitung, remove_address(org.falken, fiete))

    assert Role.objects.filter(pk__in=[wim.pk, fiete.pk]).count() == 2


@pytest.mark.rechtematrix("RO-13", "RO-18", "RO-19")
def test_cv3_fremde_kennungen_an_der_adresse_von_walhall_sind_nicht_gefunden(org):
    before = set(Role.objects.values_list("pk", flat=True))
    foreign = [
        role_of(org.zugvoegel_leitung, R.TROOP_LEAD, org.zugvoegel),
        role_of(org.walhall_mitglied, R.MEMBER, org.walhall),
        role_of(org.walhall_leitung, R.MEMBER, org.walhall),
        role_of(org.verbandsleitung, R.FEDERATION_LEAD, org.dpv),
        role_of(org.team, R.EVENT_TEAM, org.dpv),
        Role.objects.get(user=org.max, kind=R.ADMIN),
        # Eine Rolle, die Wanda entfernen darf, aber an der Adresse einer anderen Organisation.
        role_of(org.falken_leitung, R.GROUP_LEAD, org.falken),
    ]

    for role in foreign:
        assert_like_missing(org.walhall_leitung, remove_address(org.walhall, role))
    # Auch Bruno, der die Zugvögel entfernen dürfte, nicht an der Adresse von Walhall.
    assert_like_missing(org.bundesleitung, remove_address(org.walhall, foreign[0]))

    assert set(Role.objects.values_list("pk", flat=True)) == before


@pytest.mark.rechtematrix("RO-20")
def test_cv8_die_eigene_mitgliedschaft_laesst_sich_nicht_abgeben(org):
    """CV8: Mit diesem Knopf endet nie eine Mitgliedschaft, auch nicht die eigene."""
    own = role_of(org.walhall_leitung, R.MEMBER, org.walhall)

    response = remove(org.walhall_leitung, org.walhall, own)

    assert response.status_code == 404
    assert Role.objects.filter(pk=own.pk).exists()


@pytest.mark.rechtematrix("RO-14", "RO-17")
def test_cv4_ohne_leitungsrolle_entfernt_niemand_eine_rolle(org):
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)

    for user in (org.falke, org.ohne, org.team, org.max, org.verbandsleitung):
        assert_like_missing(user, remove_address(org.falken, fiete))

    assert Role.objects.filter(pk=fiete.pk).exists()


@pytest.mark.rechtematrix("RO-22")
def test_cv7_finn_sieht_den_gesperrten_fiete_nicht_und_entfernt_ihn_nicht(org):
    lock(org.falken_leitung)
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert_like_missing(org.falke, remove_address(org.falken, fiete))
    assert_like_missing(org.zugvoegel_leitung, remove_address(org.falken, fiete))

    assert Role.objects.filter(pk=fiete.pk).exists()


def test_andere_anfragen_als_lesen_und_bestaetigen_zeigen_nicht_gefunden(org):
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)
    client = client_for(org.walhall_leitung)

    for method in (client.put, client.delete, client.patch):
        assert method(remove_address(org.falken, fiete)).status_code == 404

    assert Role.objects.filter(pk=fiete.pk).exists()


def test_cv6_ein_zweites_entfernen_derselben_rolle_ist_nicht_gefunden(org):
    fiete = role_of(org.falken_leitung, R.GROUP_LEAD, org.falken)
    remove(org.walhall_leitung, org.falken, fiete)

    assert remove(org.bundesleitung, org.falken, fiete).status_code == 404
    assert RoleChange.objects.filter(kind=R.GROUP_LEAD, person_id=org.falken_leitung.pk, action="removed").count() == 1


def test_jede_rolle_hat_eine_eigene_kennung(org):
    keys = list(Role.objects.values_list("key", flat=True))

    assert len(keys) == len(set(keys))
    assert all(len(key) == 20 for key in keys)


def test_entfernen_kommt_aus_dem_baustein_rolle_abgeben_nicht(org):
    """Neues Kriterium vom 28.10.2026: „Entfernen“ ist der gemeinsame Baustein mit zarter roter Fläche (wie „Austragen“ in #65)."""
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    found = {_visible_text(link): _classes(link) for link in _all(root, lambda e: "a-leitung-knopf" in _classes(e))}

    assert "btn-entfernen" in found["Entfernen"]
    assert "btn-entfernen" not in found["Rolle abgeben"]


def test_die_seite_zeigt_keine_laufenden_nummern_der_rollen(org):
    """Die Knöpfe nennen die Rolle nur über ihre Kennung (#156)."""
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    hrefs = [_attr(link, "href") for link in _all(root, lambda e: "a-leitung-knopf" in _classes(e))]

    assert len(hrefs) == 2
    for role in Role.objects.filter(unit=org.walhall, kind=R.TROOP_LEAD):
        assert remove_address(org.walhall, role) in hrefs
        assert f"/entfernen/{role.pk}/" not in "".join(hrefs)


# ---------- Gleichzeitig ----------


def _or_missing(work):
    """Das Ergebnis oder „nicht gefunden“, damit der Test beides vergleichen kann."""
    def run():
        try:
            return work()
        except Http404:
            return "nicht gefunden"
    return run


def _walhall_with_wanda_and_willi():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    return o, wanda, willi


@pytest.mark.django_db(transaction=True)
def test_cv5_wanda_und_willi_entfernen_sich_gleichzeitig_gegenseitig():
    o, wanda, willi = _walhall_with_wanda_and_willi()
    wanda_role = role_of(wanda, R.TROOP_LEAD, o.walhall)
    willi_role = role_of(willi, R.TROOP_LEAD, o.walhall)

    results = _one_after_the_other(_or_missing(lambda: Rights(wanda).remove(o.walhall, willi_role.key)),
                                   _or_missing(lambda: Rights(willi).remove(o.walhall, wanda_role.key)))

    assert sorted(results) == ["Willi Walhall ist nicht mehr Stammesleitung von Walhall.", "nicht gefunden"]
    assert list(Role.objects.filter(kind=R.TROOP_LEAD).values_list("user__username", flat=True)) == ["wanda.walhall"]


@pytest.mark.django_db(transaction=True)
def test_cv6_wanda_und_bruno_entfernen_fiete_gleichzeitig():
    o, wanda, _willi = _walhall_with_wanda_and_willi()
    bruno = person("bruno.bund", "Bruno", "Bund")
    give(bruno, R.ASSOCIATION_LEAD, o.boreas)
    fiete = person("fiete.falke", "Fiete", "Falke")
    give(fiete, R.GROUP_LEAD, o.falken)
    role = role_of(fiete, R.GROUP_LEAD, o.falken)
    before = RoleChange.objects.count()

    results = _one_after_the_other(_or_missing(lambda: Rights(wanda).remove(o.falken, role.key)),
                                   _or_missing(lambda: Rights(bruno).remove(o.falken, role.key)))

    assert sorted(results) == ["Fiete Falke ist nicht mehr Gruppenleitung von Sippe Falken.", "nicht gefunden"]
    assert RoleChange.objects.count() == before + 1
    assert roles_of(fiete) == {(R.MEMBER, "Sippe Falken")}


@pytest.mark.django_db(transaction=True)
def test_wer_gerade_entfernt_wird_benennt_danach_niemanden_mehr():
    """Hinweis aus der Prüfung von #190: Die Benennung prüft das Recht unter der Sperre noch einmal."""
    o, wanda, willi = _walhall_with_wanda_and_willi()
    finn = person("finn.falke", "Finn", "Falke")
    give(finn, R.MEMBER, o.falken)
    wanda_role = role_of(wanda, R.TROOP_LEAD, o.walhall)

    results = _one_after_the_other(_or_missing(lambda: Rights(willi).remove(o.walhall, wanda_role.key)),
                                   _or_missing(lambda: Rights(wanda).appoint(o.falken, finn.key)))

    assert sorted(results) == ["Wanda Walhall ist nicht mehr Stammesleitung von Walhall.", "nicht gefunden"]
    assert roles_of(finn) == {(R.MEMBER, "Sippe Falken")}


@pytest.mark.django_db(transaction=True)
def test_wer_gerade_entfernt_wird_entfernt_danach_niemanden_mehr():
    o, wanda, willi = _walhall_with_wanda_and_willi()
    fiete = person("fiete.falke", "Fiete", "Falke")
    give(fiete, R.GROUP_LEAD, o.falken)
    wanda_role = role_of(wanda, R.TROOP_LEAD, o.walhall)
    fiete_role = role_of(fiete, R.GROUP_LEAD, o.falken)

    results = _one_after_the_other(_or_missing(lambda: Rights(willi).remove(o.walhall, wanda_role.key)),
                                   _or_missing(lambda: Rights(wanda).remove(o.falken, fiete_role.key)))

    assert sorted(results) == ["Wanda Walhall ist nicht mehr Stammesleitung von Walhall.", "nicht gefunden"]
    assert Role.objects.filter(pk=fiete_role.pk).exists()


# ---------- Bausteinkatalog ----------


@pytest.mark.bausteinkatalog
def test_der_katalog_zeigt_die_knoepfe_bei_den_leitungen_und_im_dialog(settings, org):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(client_for(org.walhall_leitung).get("/bausteine/"))

    lead_block = _one(_by_tag(root, "section", aria_labelledby="h-leitung"))
    labels = [_visible_text(link) for link in _all(lead_block, lambda e: "a-leitung-knopf" in _classes(e))]
    assert labels == ["Rolle abgeben", "Entfernen", "Entfernen"]
    remove_block = _one(_by_tag(root, "section", aria_labelledby="h-knopfentfernen"))
    assert [_visible_text(link) for link in _all(remove_block, lambda e: "btn-entfernen" in _classes(e))] == ["Entfernen"]
    dialog_block = _one(_by_tag(root, "section", aria_labelledby="h-dialog"))
    # Seit #118 zeigt der Katalog dazu die Rückfrage vor dem Löschen einer verwalteten Person mit „Endgültig löschen“.
    assert [_visible_text(button) for button in _all(dialog_block, lambda e: "btn-gefahr" in _classes(e))] == [
        "Entfernen", "Endgültig löschen"]
