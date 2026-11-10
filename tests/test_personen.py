"""Tests für den Abschnitt „Personen“ und „Person aufnehmen“ auf der Seite einer Organisation (#285, Teil 1 von #65).

Die Kennungen P1, P2, P12, PV1, PV2, PV6, PV7, PV10, PG4, PG5, PG7, PG8, PG9 und U1 verweisen auf
die Szenarien vom 10.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/285#issuecomment-6766975648), die
Wortlaute auf den Text von #285 und die Nachklärung N1 bis N3. Personen und Einheiten wie in den
Tests zu #190 (`tests/test_benennen.py`); Wim ist wie in den Szenarien direkt Mitglied von Walhall.
Fahrtennamen und Mails sind erfunden. Geprüft wird, was beim Browser ankommt, und was danach in der
Datenbank steht.
"""

import hashlib
import re
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from access.rights import Rights
from accounts.models import AccountSearch
from roles.models import Role, RoleChange
from tests import test_benennen
from tests.test_benennen import _one_after_the_other, dialog_of, hits, notices, roles_of, search, short_notices
from tests.test_benennen import search_address as appoint_search_address
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import BY, build_org, give, person, unit
from tests.query_limit import assert_queries_do_not_grow
from units.models import Kind as U

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

base_org = test_benennen.base_org
org_189 = test_benennen.org_189
org_190 = test_benennen.org

OTHER_ORGANISATION = (
    "Diese Person gehört schon zu einer anderen Organisation. Sie kann dort selbst austreten oder ihre "
    "bisherige Leitung bitten, sie auszutragen."
)
NO_ACCOUNT = "Kein Konto gefunden. Die Person muss sich zuerst einmal im Tool anmelden."
DIALOG_HELP = (
    "Die Person muss sich schon einmal im Tool angemeldet haben. Gefunden wird sie nur über die genaue Mail "
    "oder den genauen Benutzernamen."
)


@pytest.fixture
def org(org_190):
    """Die Personen aus #190; Wim ist wie in den Szenarien direkt Mitglied von Walhall, nicht der Wölfe."""
    membership = Role.objects.get(user=org_190.woelfe_leitung, kind=R.MEMBER)
    membership.unit = org_190.walhall
    membership.save(by=BY)
    return org_190


def admit_address(where) -> str:
    return f"{unit_address(where)}aufnehmen/"


def search_address(where) -> str:
    return f"{admit_address(where)}suchen/"


def find(user, where, text: str, client=None):
    """„Suchen“ im Dialog „Person aufnehmen“; gibt den Dialog der Antwort zurück."""
    response = (client or client_for(user)).post(search_address(where), {"suche": text})
    assert response.status_code == 200
    return dialog_of(_tree(response))


def admit(user, where, target, client=None, **more):
    """„Aufnehmen“ neben einem Treffer, wie der Knopf es abschickt; `more` sind weitere Felder."""
    return (client or client_for(user)).post(admit_address(where), {"person": target.key, **more})


def membership_of(user) -> str | None:
    found = Role.objects.filter(user=user, kind=R.MEMBER).select_related("unit").first()
    return found.unit.name if found else None


def persons_section(root):
    """Der Abschnitt „Personen“, oder None, wenn die Seite ihn nicht hat."""
    found = _by_tag(root, "section", aria_labelledby="h-personen")
    return _one(found) if found else None


def persons_on_page(root) -> dict[str, dict]:
    """Jede Person im Abschnitt „Personen“: sichtbarer Text, Rollen, Mail und die Knöpfe im Eintrag."""
    found = {}
    for entry in _all(persons_section(root), lambda e: "a-leitung" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        mails = _all(entry, lambda e: "a-leitung-mail" in _classes(e))
        found[name] = {
            "text": _visible_text(entry),
            "roles": [_visible_text(mark) for mark in _all(entry, lambda e: "a-rollenmarke" in _classes(e))],
            "mail": _visible_text(mails[0]) if mails else "",
            "buttons": [_visible_text(button) for button in _all(entry, lambda e: "btn" in _classes(e))],
        }
    return found


def persons_head(root) -> str:
    """Die Zahl im Kopf des Abschnitts, etwa „4 Personen“."""
    return _visible_text(_one(_all(persons_section(root), lambda e: "a-flaeche-zahl" in _classes(e))))


def admit_button(user, where) -> str | None:
    """Die Beschriftung des Knopfs „Person aufnehmen“ im Abschnitt „Personen“, oder None."""
    section = persons_section(page_tree(user, unit_address(where)))
    links = _all(section, lambda e: "a-flaeche-aktion" in _classes(e))
    if not links:
        return None
    assert _attr(_one(links), "href") == admit_address(where)
    return _visible_text(_one(links))


# ---------- Abschnitt „Personen“ ----------


@pytest.mark.rechtematrix("PK-01")
def test_p2_auf_walhall_stehen_nur_die_direkten_mitglieder_mit_name_fahrtenname_mail_und_rollen(org):
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    shown = persons_on_page(root)

    assert set(shown) == {"Wirbelwind", "Wiesel", "Wilma Walhall", "Wim Wolf"}
    assert persons_head(root) == "4 Personen"
    assert "Wanda Walhall" in shown["Wirbelwind"]["text"]
    assert shown["Wirbelwind"]["mail"] == "wanda.walhall@example.org"
    assert shown["Wilma Walhall"]["mail"] == "wilma.walhall@example.org"
    # Unter dem Namen die Leitungsrollen (#65 N1); ein Mitglied ohne Leitung hat keine Marke.
    assert shown["Wirbelwind"]["roles"] == ["Stammesleitung Stamm Walhall"]
    assert shown["Wim Wolf"]["roles"] == ["Gruppenleitung Meute Wölfe"]
    assert shown["Wilma Walhall"]["roles"] == []
    assert "das bist du" in shown["Wirbelwind"]["text"]
    assert "das bist du" not in shown["Wiesel"]["text"]


def test_p2_auf_den_falken_sieht_wanda_fiete_und_finn_ohne_verschieben_und_austragen(org):
    root = page_tree(org.walhall_leitung, unit_address(org.falken))
    shown = persons_on_page(root)

    assert set(shown) == {"Funke", "Flink"}
    assert persons_head(root) == "2 Personen"
    assert shown["Funke"]["roles"] == ["Gruppenleitung Sippe Falken"]
    for entry in shown.values():
        assert entry["buttons"] == []
        assert "Verschieben" not in entry["text"]
        assert "Austragen" not in entry["text"]


def test_eine_person_heisst_im_kopf_eine_person(org):
    root = page_tree(org.walhall_leitung, unit_address(org.woelfe))

    assert set(persons_on_page(root)) == {"Wiebke Wolf"}
    assert persons_head(root) == "1 Person"


def test_ohne_direkte_mitglieder_steht_der_satz(org):
    """#65 N2: „Zu Sippe Falken gehört direkt noch niemand.“"""
    Role.objects.get(user=org.falke, kind=R.MEMBER).delete(by=BY)
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    Role.objects.get(user=org.falken_leitung, kind=R.MEMBER).delete(by=BY)

    root = page_tree(org.walhall_leitung, unit_address(org.falken))

    assert persons_on_page(root) == {}
    assert persons_head(root) == "0 Personen"
    assert "Zu Sippe Falken gehört direkt noch niemand." in _visible_text(persons_section(root))
    zugvoegel = page_tree(org.bundesleitung, unit_address(org.zugvoegel))
    assert set(persons_on_page(zugvoegel)) == {"Zimt"}


def test_u1_die_leseseite_hat_keinen_abschnitt_personen(org):
    root = page_tree(org.walhall_leitung, unit_address(org.boreas))

    assert persons_section(root) is None
    assert admit_button(org.walhall_leitung, org.walhall) == "Person aufnehmen"


def test_u1_leitungen_und_organisationen_darunter_bleiben(org):
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    shown = {"h-leitungen", "h-darunter", "h-personen"}
    sections = [_attr(section, "aria-labelledby") for section in _by_tag(root, "section")]

    assert [section for section in sections if section in shown] == ["h-leitungen", "h-darunter", "h-personen"]


# ---------- Wer den Knopf „Person aufnehmen“ hat ----------


@pytest.mark.rechtematrix("PK-17")
def test_den_knopf_hat_die_leitung_der_eigenen_organisation(org):
    allowed = [
        (org.walhall_leitung, org.walhall),
        (org.willi, org.walhall),
        (org.falken_leitung, org.falken),
        (org.woelfe_leitung, org.woelfe),
        (org.bundesleitung, org.boreas),
        (org.kueste_leitung, org.kueste),
    ]
    for user, where in allowed:
        assert admit_button(user, where) == "Person aufnehmen", (user.username, where.name)


@pytest.mark.rechtematrix("PK-26")
def test_pv2_in_organisationen_darunter_gibt_es_keinen_knopf(org):
    forbidden = [
        (org.walhall_leitung, org.falken),
        (org.walhall_leitung, org.woelfe),
        (org.bundesleitung, org.walhall),
        (org.bundesleitung, org.adler),
        (org.kueste_leitung, org.leuchtturm),
    ]
    for user, where in forbidden:
        assert admit_button(user, where) is None, (user.username, where.name)


# ---------- Dialog „Person aufnehmen“ ----------


def test_der_dialog_hat_feld_knopf_und_hinweis_ohne_vorschlaege(org):
    root = _tree(client_for(org.falken_leitung).get(admit_address(org.falken)))
    found = dialog_of(root)
    text = _visible_text(found)

    assert _text(_one(_by_tag(found, "h2"))) == "Person aufnehmen"
    assert "in Sippe Falken" in text
    assert "Mail oder Benutzername" in text
    assert DIALOG_HELP in text
    form = _one(_by_tag(found, "form"))
    assert _attr(form, "action") == search_address(org.falken)
    assert _attr(form, "data-vorschlaege") is None
    assert [_visible_text(button) for button in _by_tag(form, "button")] == ["Suchen"]
    # Die Seite unter dem Dialog ist die Seite der Falken.
    assert persons_section(root) is not None


@pytest.mark.rechtematrix("PK-17")
def test_p1_fiete_findet_otto_und_nimmt_ihn_ohne_zustimmung_in_die_falken_auf(org):
    found = hits(find(org.falken_leitung, org.falken, "otto.ohne@example.org"))

    assert list(found) == ["Otto Ohne"]
    assert found["Otto Ohne"]["button"]
    assert "Aufnehmen" in found["Otto Ohne"]["text"]
    assert found["Otto Ohne"]["key"] == org.ohne.key

    client = client_for(org.falken_leitung)
    response = admit(org.falken_leitung, org.falken, org.ohne, client=client)

    assert response.status_code == 302
    assert response.url == unit_address(org.falken)
    assert membership_of(org.ohne) == "Sippe Falken"
    assert roles_of(org.ohne) == {(R.MEMBER, "Sippe Falken")}
    page = client.get(response.url)
    assert short_notices(page) == ["Otto Ohne gehört jetzt zu Sippe Falken."]
    assert "Otto Ohne" in persons_on_page(_tree(page))


def test_p1_die_aufnahme_steht_im_protokoll(org):
    admit(org.falken_leitung, org.falken, org.ohne)

    entry = RoleChange.objects.filter(person_id=org.ohne.pk).get()
    assert (entry.kind, entry.action, entry.actor_id, entry.unit_id) == (
        R.MEMBER, RoleChange.Action.GRANTED, org.falken_leitung.pk, org.falken.pk)


def test_ohne_treffer_sagt_der_dialog_kein_konto_gefunden(org):
    found = find(org.falken_leitung, org.falken, "niemand@example.org")

    assert hits(found) == {}
    assert NO_ACCOUNT in notices(found)[-1]


@pytest.mark.rechtematrix("PK-17")
def test_den_benutzernamen_findet_der_dialog_auch(org):
    assert list(hits(find(org.falken_leitung, org.falken, "OTTO.OHNE"))) == ["Otto Ohne"]


@pytest.mark.rechtematrix("EH-18", "PK-17", "PK-26")
def test_p12_ohne_gruppenleitung_nimmt_wanda_otto_in_die_falken_auf(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert admit_button(org.walhall_leitung, org.falken) == "Person aufnehmen"
    assert list(hits(find(org.walhall_leitung, org.falken, "otto.ohne@example.org"))) == ["Otto Ohne"]
    assert admit(org.walhall_leitung, org.falken, org.ohne).status_code == 302
    assert membership_of(org.ohne) == "Sippe Falken"


@pytest.mark.rechtematrix("EH-18", "EH-19")
def test_pg9_mit_neuer_gruppenleitung_endet_das_einspringen_beim_naechsten_klick(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    client = client_for(org.walhall_leitung)
    assert client.get(admit_address(org.falken)).status_code == 200

    give(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert admit_button(org.walhall_leitung, org.falken) is None
    assert client.get(admit_address(org.falken)).status_code == 404
    assert admit(org.walhall_leitung, org.falken, org.ohne, client=client).status_code == 404
    assert membership_of(org.ohne) is None


@pytest.mark.rechtematrix("PK-18", "PK-16")
def test_pv1_zora_findet_wilma_und_liest_den_satz_ohne_walhall(org):
    response = client_for(org.zugvoegel_leitung).post(search_address(org.zugvoegel), {"suche": "wilma.walhall@example.org"})
    found = dialog_of(_tree(response))

    assert hits(found) == {}
    assert OTHER_ORGANISATION in notices(found)[-1]
    # Walhall steht für Zora nur als Name in der Gliederung ihres Bundes (EH-01), nie im Dialog,
    # auch nicht unsichtbar: genauso oft wie auf der Seite ohne Dialog.
    assert "Walhall" not in _visible_text(found)
    without_dialog = client_for(org.zugvoegel_leitung).get(unit_address(org.zugvoegel)).content.decode()
    assert response.content.decode().count("Walhall") == without_dialog.count("Walhall")


@pytest.mark.rechtematrix("PK-18", "PK-16")
def test_pv1_auch_ein_manipuliertes_formular_nimmt_wilma_nicht_auf_und_nennt_walhall_nicht(org):
    response = admit(org.zugvoegel_leitung, org.zugvoegel, org.walhall_mitglied)

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert OTHER_ORGANISATION in notices(found)[-1]
    assert "Walhall" not in _visible_text(found)
    assert roles_of(org.walhall_mitglied) == {(R.MEMBER, "Walhall")}


@pytest.mark.rechtematrix("PK-18")
def test_gegenprobe_wer_nirgends_mitglied_ist_nimmt_zora_auf(org):
    assert admit(org.zugvoegel_leitung, org.zugvoegel, org.ohne).status_code == 302
    assert membership_of(org.ohne) == "Zugvögel"


@pytest.mark.rechtematrix("PK-16")
def test_pg5_wanda_sucht_finn_und_liest_schon_mitglied_in_sippe_falken(org):
    found = find(org.walhall_leitung, org.walhall, "finn.falke@example.org")

    assert hits(found) == {}
    assert "Flink (Finn Falke) ist schon Mitglied in Sippe Falken." in notices(found)[-1]
    assert admit(org.walhall_leitung, org.walhall, org.falke).status_code == 200
    assert membership_of(org.falke) == "Sippe Falken"


def test_schon_mitglied_im_stamm_nennt_die_art(org):
    found = find(org.walhall_leitung, org.walhall, "wilma.walhall@example.org")

    assert "Wilma Walhall ist schon Mitglied in Stamm Walhall." in notices(found)[-1]


@pytest.mark.rechtematrix("PK-16", "PK-18")
def test_fiete_sieht_wilma_auf_seiner_kette_nur_als_andere_organisation(org):
    """Walhall liegt auf Fietes Kette nach oben, nicht in seinem Bereich: kein „Stamm Walhall“ (unabhängige Prüfung)."""
    found = find(org.falken_leitung, org.falken, "wilma.walhall@example.org")

    assert hits(found) == {}
    assert OTHER_ORGANISATION in notices(found)[-1]
    assert "Walhall" not in _visible_text(found)


@pytest.mark.rechtematrix("EP-08")
def test_wer_sich_selbst_sucht_ist_schon_mitglied(org):
    found = find(org.walhall_leitung, org.walhall, "wanda.walhall@example.org")

    assert hits(found) == {}
    assert "Wirbelwind (Wanda Walhall) ist schon Mitglied in Stamm Walhall." in notices(found)[-1]
    assert admit(org.walhall_leitung, org.walhall, org.walhall_leitung).status_code == 200
    assert roles_of(org.walhall_leitung) == {(R.MEMBER, "Walhall"), (R.TROOP_LEAD, "Walhall")}


# ---------- Verboten ----------


@pytest.mark.rechtematrix("PK-26", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/aufnehmen/")
def test_pv2_wanda_nimmt_otto_nicht_direkt_in_die_falken_auf(org):
    assert_like_missing(org.walhall_leitung, admit_address(org.falken))

    response = admit(org.walhall_leitung, org.falken, org.ohne)

    assert response.status_code == 404
    assert membership_of(org.ohne) is None


@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/aufnehmen/suchen/")
def test_pv2_wanda_sucht_nicht_ueber_die_falken(org):
    assert_like_missing(org.walhall_leitung, search_address(org.falken))

    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("PK-23")
def test_pv6_ohne_leitungsrolle_nimmt_niemand_jemanden_auf(org):
    for user in (org.verbandsleitung, org.team, org.max, org.walhall_mitglied, org.ohne):
        for where in (org.walhall, org.falken, org.boreas):
            assert_like_missing(user, admit_address(where))
            assert_like_missing(user, search_address(where))
            assert admit(user, where, org.ohne).status_code == 404

    assert membership_of(org.ohne) is None
    assert not AccountSearch.objects.exists()


@pytest.mark.rechtematrix("EP-08")
def test_pv7_otto_ordnet_sich_ueber_eine_manipulierte_adresse_nicht_selbst_walhall_zu(org):
    for where in (org.walhall, org.falken, org.boreas):
        assert admit(org.ohne, where, org.ohne).status_code == 404

    assert roles_of(org.ohne) == set()
    assert not RoleChange.objects.filter(person_id=org.ohne.pk).exists()


def test_die_organisation_kommt_aus_der_adresse_nicht_aus_dem_formular(org):
    admit(org.walhall_leitung, org.walhall, org.ohne, unit=org.zugvoegel.key, organisation=org.adler.key)

    assert membership_of(org.ohne) == "Walhall"


@pytest.mark.rechtematrix("PK-17")
def test_leitungen_ausserhalb_nehmen_nicht_in_fremde_oder_hoehere_organisationen_auf(org):
    """Direkte Adressen außerhalb des eigenen Bereichs und auf der Kette nach oben (Fiete bei Walhall, Zora bei Walhall)."""
    for user, where in ((org.falken_leitung, org.walhall), (org.zugvoegel_leitung, org.walhall),
                        (org.zugvoegel_leitung, org.falken), (org.walhall_leitung, org.boreas),
                        (org.kueste_leitung, org.walhall)):
        assert_like_missing(user, admit_address(where))
        assert admit(user, where, org.ohne).status_code == 404, (user.username, where.name)

    assert membership_of(org.ohne) is None


def test_gesperrtes_oder_nie_angemeldetes_konto_laesst_sich_nicht_aufnehmen(org):
    never = person("nie.angemeldet", "Nie", "Angemeldet")
    locked = person("gesperrt.konto", "Gesperrt", "Konto")
    User.objects.filter(pk=locked.pk).update(is_active=False, last_login=org.ohne.last_login)

    for target in (never, locked):
        assert admit(org.walhall_leitung, org.walhall, target).status_code == 404
        assert roles_of(target) == set()


def test_falsche_oder_fehlende_kennung_einer_person_ist_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)
    for data in ({}, {"person": ""}, {"person": "a" * 20}, {"person": str(org.ohne.pk)}, {"person": org.walhall.key}):
        assert client.post(admit_address(org.walhall), data).status_code == 404, data

    assert membership_of(org.ohne) is None


def test_pv10_eine_organisation_mit_mitglied_laesst_sich_nicht_loeschen(org):
    with pytest.raises(ProtectedError):
        org.adler.delete()
    # Auch an Django vorbei, direkt in der Datenbank; die Prüfung der Verweise sofort statt am Ende.
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("DELETE FROM units_unit WHERE id = %s", [org.adler.pk])

    assert membership_of(org.adler_kind) == "Sippe Adler"


# ---------- Grenzfälle ----------


@pytest.mark.django_db(transaction=True)
def test_pg4_wanda_und_zora_nehmen_otto_gleichzeitig_auf():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    zora = person("zora.zugvogel", "Zora", "Zugvogel")
    otto = person("otto.ohne", "Otto", "Ohne")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(zora, R.TROOP_LEAD, o.zugvoegel)
    User.objects.filter(pk=otto.pk).update(last_login=timezone.now())

    results = _one_after_the_other(lambda: Rights(wanda).admit(o.walhall, otto.key),
                                   lambda: Rights(zora).admit(o.zugvoegel, otto.key))

    assert sorted(results) == [(False, OTHER_ORGANISATION), (True, "Otto Ohne gehört jetzt zu Stamm Walhall.")]
    assert Role.objects.filter(user=otto, kind=R.MEMBER).count() == 1
    assert RoleChange.objects.filter(person_id=otto.pk).count() == 1


def test_pg7_aufnehmen_und_benennen_teilen_sich_das_suchlimit(org):
    client = client_for(org.walhall_leitung)
    for number in range(10):
        client.post(appoint_search_address(org.walhall), {"suche": f"niemand{number}@example.org"})
        client.post(search_address(org.walhall), {"suche": f"niemand{number}@example.org"})
    assert AccountSearch.objects.filter(user=org.walhall_leitung).count() == 20

    refused = find(org.walhall_leitung, org.walhall, "otto.ohne@example.org", client=client)

    assert hits(refused) == {}
    assert "Du hast in kurzer Zeit sehr oft gesucht. Bitte versuche es in 60 Minuten noch einmal." in notices(refused)[-1]
    refused_appoint = search(org.walhall_leitung, org.walhall, "otto.ohne@example.org", client=client)
    assert "Du hast in kurzer Zeit sehr oft gesucht." in notices(refused_appoint)[-1]
    assert AccountSearch.objects.filter(user=org.walhall_leitung).count() == 20


def test_leere_suche_zeigt_nichts_und_zaehlt_nicht(org):
    for text in ("", "   ", "*", "%"):
        assert hits(find(org.walhall_leitung, org.walhall, text)) == {}

    assert not AccountSearch.objects.exists()


def test_pg8_die_liste_personen_waechst_nicht_mit_den_abfragen(org):
    client = client_for(org.walhall_leitung)

    def create_entry(number: int) -> None:
        group = unit(U.GROUP, f"Gruppe {number}", org.walhall)
        member = person(f"mitglied.nummer{number}", "Mitglied", f"Nummer{number}")
        give(member, R.MEMBER, org.walhall)
        give(member, R.GROUP_LEAD, group)

    def load_list() -> None:
        response = client.get(unit_address(org.walhall))
        assert response.status_code == 200

    assert_queries_do_not_grow(create_entry, load_list)
    assert len(persons_on_page(page_tree(org.walhall_leitung, unit_address(org.walhall)))) == 14


# ---------- Zielbild ----------

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "personen.html"
CHECKSUM = "93e97f1d2ec233ebe02c029e7da3f1c61aa5da9e0cc617b9b8aa726c50f9c79a"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Personen", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "28.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#285"):
        assert must in section[1], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert all(mail.endswith("@example.org") for mail in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
