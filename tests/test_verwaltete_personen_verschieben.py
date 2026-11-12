"""Tests für verwaltete Personen verschieben, austragen und löschen (#118, PER-02).

Die Kennungen V1 bis V9, VV1 bis VV7, VG1 bis VG6 und U1 bis U3 verweisen auf die Szenarien vom
11.11.2026 (https://github.com/sebivtt/dpv-participant-management/issues/118#issuecomment-6789855229),
die Wortlaute auf den Text von #118. Verschieben und Austragen gehen wie bei Personen mit Konto (#286,
#287): dieselben Knöpfe, derselbe Dialog, dieselben Sätze; Löschen im Dialog „Bearbeiten“ wie im Zielbild
zu #117, Fassung 1 (Nachklärung N5 dort). Personen und Organisationen wie in den Tests zu #117
(`tests/test_verwaltete_personen.py`): Wanda und Willi leiten Walhall, Fiete die Sippe Falken, Wim die
Meute Wölfe (er ist direkt Mitglied von Walhall), Zora die Zugvögel, Bruno Boreas; verwaltet sind Lena
Probe „Kiwi“ (Sippe Falken), Paul Probe (Stamm Walhall) und Mia Probe (Meute Wölfe). Alle Namen sind
erfunden. Geprüft wird, was beim Browser ankommt, und was danach in der Datenbank steht.

Prüfgrundsatz der Szenarien: Die Organisation kommt immer aus der Adresse, nie aus dem Formular. Jeder
unberechtigte Aufruf wird direkt, aus dem Skript und mit manipuliertem Formular geprüft (`refused()`).
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import DatabaseError, transaction
from django.http import Http404
from django.test import Client

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import AdminAccess, Role, RoleChange
from tests import test_verwaltete_personen
from tests.test_austragen import choice_dialog
from tests.test_benennen import _one_after_the_other, dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person
from tests.test_verschieben import move_dialog
from tests.test_verwaltete_personen import add, edit_address, entries, lena_now, managed, open_edit, save

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures aus tests/test_verwaltete_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_verwaltete_personen.base_org
org_189 = test_verwaltete_personen.org_189
org_190 = test_verwaltete_personen.org_190
org_285 = test_verwaltete_personen.org_285
org = test_verwaltete_personen.org
lena = test_verwaltete_personen.lena

DELETE_BUTTON = "Verwaltete Person löschen"
LENA_QUESTION = "Kiwi (Lena Probe) endgültig löschen?"
CANNOT_UNDO = "Das lässt sich nicht rückgängig machen."
LENA_DELETED = "Kiwi (Lena Probe) wurde gelöscht."


@pytest.fixture
def mia(org):
    """Mia Probe in der Meute Wölfe, ohne Fahrtennamen."""
    return managed("Mia", "Probe", org.woelfe, born=date(2016, 4, 1))


# ---------- Hilfen ----------


def move_address(where, entry) -> str:
    return f"{unit_address(where)}verwaltete-person/{entry.key}/verschieben/"


def expel_address(where, entry) -> str:
    return f"{unit_address(where)}verwaltete-person/{entry.key}/austragen/"


def delete_address(where, entry) -> str:
    return f"{unit_address(where)}verwaltete-person/{entry.key}/loeschen/"


def move(user, where, entry, goal, client=None, **more):
    """„Verschieben“ im Dialog bestätigen, wie der blaue Knopf es mit der gewählten Organisation abschickt."""
    return (client or client_for(user)).post(move_address(where, entry), {"ziel": goal.key, **more})


def expel(user, where, entry, client=None, **more):
    """„Austragen“ im Dialog bestätigen; für verwaltete Personen gibt es nur „gehört danach direkt zu …“."""
    return (client or client_for(user)).post(expel_address(where, entry), {"wahl": "hoch", **more})


def delete(user, where, entry, client=None, **more):
    """„Endgültig löschen“ in der Rückfrage, wie der rote Knopf es abschickt."""
    return (client or client_for(user)).post(delete_address(where, entry), more)


def refused(user, address: str, form: dict) -> None:
    """Die Adresse ist für `user` wie nicht vorhanden: direkt, aus dem Skript und mit manipuliertem Formular."""
    assert_like_missing(user, address)
    script = Client()
    script.force_login(user)
    assert script.post(address, form, headers={"x-requested-with": "fetch"}).status_code == 404, user.username
    assert script.get(address, headers={"x-requested-with": "fetch"}).status_code == 404, user.username
    manipulated = {**form, "unit": "b" * 20, "organisation": "b" * 20, "person": "b" * 20, "wahl": "ganz"}
    assert client_for(user).post(address, manipulated).status_code == 404, user.username


def delete_link(dialog):
    """Der Knopf „Verwaltete Person löschen“ im Dialog „Bearbeiten“, oder None."""
    links = [link for link in _by_tag(dialog, "a") if _visible_text(link) == DELETE_BUTTON]
    return _one(links) if links else None


def confirmation(response) -> dict:
    """Die Rückfrage vor dem Löschen: Titel, Text, „Nicht löschen“ und der rote Knopf mit seinem Formular."""
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    form = _one(_by_tag(dialog, "form", method="post"))
    keep = [link for link in _by_tag(dialog, "a") if _visible_text(link) == "Nicht löschen"]
    return {
        "title": _visible_text(_one(_by_tag(dialog, "h2"))),
        "text": _visible_text(dialog),
        "keep": _attr(_one(keep), "href") if keep else None,
        "button": _one(_by_tag(form, "button", type="submit")),
        "action": _attr(form, "action"),
        "links": [_visible_text(link) for link in _by_tag(dialog, "a")],
    }


def managed_log(before: int) -> list[tuple]:
    """Die Einträge im Protokoll der Rollenänderungen seit `before`, die eine verwaltete Person betreffen."""
    entries = RoleChange.objects.order_by("id")[before:]
    return [(entry.actor_name, entry.person_name, entry.kind, entry.unit_name, entry.action)
            for entry in entries if entry.managed]


def unit_of(entry) -> str:
    entry.refresh_from_db()
    return entry.unit.name


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VP-07", "PR-02")
def test_v1_wanda_verschiebt_paul_in_die_sippe_falken(org):
    shown = entries(page_tree(org.walhall_leitung, unit_address(org.walhall)))
    assert shown["Paul Probe"]["buttons"]["Verschieben"] == move_address(org.walhall, org.paul)
    assert shown["Paul Probe"]["buttons"]["Austragen"] == expel_address(org.walhall, org.paul)
    client = client_for(org.walhall_leitung)
    found = move_dialog(client.get(move_address(org.walhall, org.paul)))
    assert found["title"] == "Verschieben"
    assert found["subtitle"] == "Paul Probe aus Stamm Walhall"
    # Zur Wahl stehen nur die Organisationen direkt darunter.
    assert [label for _name, _value, label, _checked in found["options"]] == ["Meute Wölfe", "Sippe Falken"]
    assert found["action"] == move_address(org.walhall, org.paul)
    before = RoleChange.objects.count()

    response = move(org.walhall_leitung, org.walhall, org.paul, org.falken, client=client)

    assert response.status_code == 302
    assert response.url == unit_address(org.walhall)
    assert short_notices(client.get(response.url)) == ["Paul Probe gehört jetzt zu Sippe Falken."]
    assert unit_of(org.paul) == "Sippe Falken"
    # Beim nächsten Klick gelten die Rechte der neuen Organisation (#90).
    assert "Paul Probe" in entries(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert "Paul Probe" not in entries(page_tree(org.walhall_leitung, unit_address(org.walhall)))
    assert managed_log(before) == [
        ("Wanda Walhall", "Paul Probe", R.MEMBER, "Walhall", "removed"),
        ("Wanda Walhall", "Paul Probe", R.MEMBER, "Sippe Falken (Walhall)", "granted"),
    ]
    assert len(mail.outbox) == 0


@pytest.mark.rechtematrix("VP-18", "PR-02")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_v2_wim_traegt_mia_aus_der_meute_woelfe_aus(org, mia):
    shown = entries(page_tree(org.woelfe_leitung, unit_address(org.woelfe)))
    # Unter einer Gruppe gibt es nichts, wohin man verschieben könnte; Austragen und Bearbeiten schon.
    assert shown["Mia Probe"]["buttons"] == {"Bearbeiten": edit_address(org.woelfe, mia),
                                             "Austragen": expel_address(org.woelfe, mia)}
    client = client_for(org.woelfe_leitung)
    found = choice_dialog(client.get(expel_address(org.woelfe, mia)))
    assert found["title"] == "Mia Probe aus Meute Wölfe austragen?"
    assert [(option["value"], option["label"]) for option in found["options"]] == [
        ("hoch", "Mia Probe gehört danach direkt zu Stamm Walhall")]
    assert found["options"][0]["preview"][0] == (
        "Mia Probe aus Meute Wölfe austragen? Danach gehört Mia Probe direkt zu Stamm Walhall.")
    assert found["button"] == "Austragen"
    assert found["action"] == expel_address(org.woelfe, mia)
    before = RoleChange.objects.count()

    response = expel(org.woelfe_leitung, org.woelfe, mia, client=client)

    assert response.status_code == 302
    assert response.url == unit_address(org.woelfe)
    assert short_notices(client.get(response.url)) == ["Mia Probe ist aus Meute Wölfe ausgetragen."]
    assert unit_of(mia) == "Walhall"
    assert managed_log(before) == [
        ("Wim Wolf", "Mia Probe", R.MEMBER, "Meute Wölfe (Walhall)", "removed"),
        ("Wim Wolf", "Mia Probe", R.MEMBER, "Walhall", "granted"),
    ]
    # Wim sieht Mia danach nicht mehr; Walhall liegt für ihn nur auf der Kette nach oben.
    assert "Mia Probe" not in entries(page_tree(org.woelfe_leitung, unit_address(org.woelfe)))
    assert "Mia" not in client.get(unit_address(org.walhall)).content.decode()
    assert_like_missing(org.woelfe_leitung, edit_address(org.walhall, mia))
    assert "Mia Probe" in entries(page_tree(org.walhall_leitung, unit_address(org.walhall)))


@pytest.mark.rechtematrix("VP-07", "VP-18")
def test_v3_gruppenwechsel_in_zwei_schritten_mia_kommt_in_die_falken(org, mia):
    assert expel(org.woelfe_leitung, org.woelfe, mia).status_code == 302
    before = RoleChange.objects.count()

    response = move(org.walhall_leitung, org.walhall, mia, org.falken)

    assert response.status_code == 302
    assert unit_of(mia) == "Sippe Falken"
    assert "Mia Probe" in entries(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert managed_log(before) == [
        ("Wanda Walhall", "Mia Probe", R.MEMBER, "Walhall", "removed"),
        ("Wanda Walhall", "Mia Probe", R.MEMBER, "Sippe Falken (Walhall)", "granted"),
    ]


@pytest.mark.rechtematrix("VP-07", "VP-08", "EH-18", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/verschieben/")
def test_v4_ohne_stammesleitung_springt_bruno_ein_und_verschiebt_paul(org):
    # Solange Walhall eine Stammesleitung hat, verschiebt Bruno dort niemanden (EH-19).
    refused(org.bundesleitung, move_address(org.walhall, org.paul), {"ziel": org.falken.key})
    assert unit_of(org.paul) == "Walhall"
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove(org.willi, R.TROOP_LEAD, org.walhall)
    shown = entries(page_tree(org.bundesleitung, unit_address(org.walhall)))
    assert shown["Paul Probe"]["buttons"]["Verschieben"] == move_address(org.walhall, org.paul)

    response = move(org.bundesleitung, org.walhall, org.paul, org.falken)

    assert response.status_code == 302
    assert unit_of(org.paul) == "Sippe Falken"


@pytest.mark.rechtematrix("VP-09", "VP-10", "PR-02")
def test_v5_fiete_loescht_lena_im_dialog_bearbeiten(org):
    client = client_for(org.falken_leitung)
    assert add(org.falken_leitung, org.falken, client=client).status_code == 302
    lena = lena_now()
    assert lena.consent_by_id == org.falken_leitung.pk
    found, _version = open_edit(org.falken_leitung, org.falken, lena, client=client)
    link = delete_link(found)
    assert link is not None
    assert _attr(link, "href") == delete_address(org.falken, lena)
    # Zart rot wie „Entfernen“ (Baustein „Knopf „Entfernen““), im Fuß des Dialogs als Erstes, also links unten.
    assert "btn-entfernen" in _classes(link)
    footer = _one(_all(found, lambda e: "a-dialog-fuss" in _classes(e)))
    assert [_visible_text(entry) for entry in _all(footer, lambda e: e.name in ("a", "button"))] == [
        DELETE_BUTTON, "Abbrechen", "Speichern"]

    asked = confirmation(client.get(delete_address(org.falken, lena)))
    assert asked["title"] == LENA_QUESTION
    assert CANNOT_UNDO in asked["text"]
    assert _visible_text(asked["button"]) == "Endgültig löschen"
    assert "btn-gefahr" in _classes(asked["button"])
    assert asked["action"] == delete_address(org.falken, lena)
    assert asked["keep"] == edit_address(org.falken, lena)
    before = RoleChange.objects.count()

    response = delete(org.falken_leitung, org.falken, lena, client=client)

    assert response.status_code == 302
    assert response.url == unit_address(org.falken)
    assert short_notices(client.get(response.url)) == [LENA_DELETED]
    # Gelöscht samt aller Angaben und der Bestätigung der Einwilligung (#98), ohne Papierkorb.
    assert not ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert not ManagedPerson.objects.filter(consent_by=org.falken_leitung).exists()
    assert "Kiwi" not in entries(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert managed_log(before) == [("Fiete Falke", "Lena Probe", R.MEMBER, "Sippe Falken (Walhall)", "removed")]
    assert len(mail.outbox) == 0


@pytest.mark.rechtematrix("VP-09", "EH-18")
def test_v6_ohne_gruppenleitung_loescht_wanda_lena(org, lena):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    client = client_for(org.walhall_leitung)
    found, _version = open_edit(org.walhall_leitung, org.falken, lena, client=client)
    assert _attr(delete_link(found), "href") == delete_address(org.falken, lena)

    response = delete(org.walhall_leitung, org.falken, lena, client=client)

    assert response.status_code == 302
    assert short_notices(client.get(response.url)) == [LENA_DELETED]
    assert not ManagedPerson.objects.filter(pk=lena.pk).exists()


@pytest.mark.rechtematrix("VP-09")
def test_v7_nicht_loeschen_loescht_nichts(org, lena):
    client = client_for(org.falken_leitung)
    asked = confirmation(client.get(delete_address(org.falken, lena)))
    before = RoleChange.objects.count()

    back = client.get(asked["keep"])

    assert back.status_code == 200
    assert _visible_text(_one(_by_tag(dialog_of(_tree(back)), "h2"))) == "Kiwi (Lena Probe) bearbeiten"
    # Das × der Rückfrage führt zur Seite zurück, zum Knopf „Bearbeiten“ von Lena.
    close = _one(_all(dialog_of(_tree(client.get(delete_address(org.falken, lena)))),
                      lambda e: "a-schliessen" in _classes(e)))
    assert _attr(close, "href") == f"{unit_address(org.falken)}#bearbeiten-{lena.key}"
    assert ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PR-02")
def test_v8_anlegen_steht_im_protokoll_als_vergeben(org):
    before = RoleChange.objects.count()

    assert add(org.falken_leitung, org.falken).status_code == 302

    assert managed_log(before) == [("Fiete Falke", "Lena Probe", R.MEMBER, "Sippe Falken (Walhall)", "granted")]
    entry = RoleChange.objects.order_by("id").last()
    assert entry.person_id == lena_now().pk


@pytest.mark.rechtematrix("VP-07", "VP-13", "VP-18")
def test_v9_verschieben_und_austragen_lassen_die_bestaetigung_der_einwilligung_unveraendert(org):
    """#98, Szenario EG3: Konto und Zeitpunkt der Bestätigung bleiben, wie sie beim Anlegen gespeichert wurden."""
    confirmed_at = datetime(2026, 11, 1, 10, 0, tzinfo=ZoneInfo("Europe/Berlin"))
    ManagedPerson.objects.filter(pk=org.paul.pk).update(consent_by=org.willi, consent_at=confirmed_at)

    assert move(org.walhall_leitung, org.walhall, org.paul, org.falken).status_code == 302
    org.paul.refresh_from_db()
    assert (org.paul.consent_by_id, org.paul.consent_at) == (org.willi.pk, confirmed_at)
    assert expel(org.falken_leitung, org.falken, org.paul).status_code == 302
    org.paul.refresh_from_db()
    assert org.paul.unit_id == org.walhall.pk
    assert (org.paul.consent_by_id, org.paul.consent_at) == (org.willi.pk, confirmed_at)


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VP-08")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/verschieben/")
def test_vv1_fiete_verschiebt_lena_nicht(org, lena):
    shown = entries(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert "Verschieben" not in shown["Kiwi"]["buttons"]

    assert_like_missing(org.falken_leitung, move_address(org.falken, lena))
    refused(org.falken_leitung, move_address(org.falken, lena), {"ziel": org.woelfe.key})

    assert unit_of(lena) == "Sippe Falken"


@pytest.mark.rechtematrix("VP-08", "VP-18")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/austragen/")
def test_vv2_wanda_verschiebt_und_traegt_lena_nicht_aus_solange_die_falken_fiete_haben(org, lena):
    shown = entries(page_tree(org.walhall_leitung, unit_address(org.falken)))
    assert shown["Kiwi"]["buttons"] == {"Bearbeiten": edit_address(org.falken, lena)}

    assert_like_missing(org.walhall_leitung, expel_address(org.falken, lena))
    refused(org.walhall_leitung, move_address(org.falken, lena), {"ziel": org.woelfe.key})
    refused(org.walhall_leitung, expel_address(org.falken, lena), {"wahl": "hoch"})
    # Mit Walhall in der Adresse ebenso: Lena gehört nicht direkt zu Walhall.
    refused(org.walhall_leitung, move_address(org.walhall, lena), {"ziel": org.woelfe.key})
    refused(org.walhall_leitung, expel_address(org.walhall, lena), {"wahl": "hoch"})

    assert unit_of(lena) == "Sippe Falken"
    assert not RoleChange.objects.filter(person_id=lena.pk, managed=True).exists()


@pytest.mark.rechtematrix("VP-07", "VP-08")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/verschieben/")
def test_vv3_ein_manipuliertes_ziel_fuer_paul_ist_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)
    before = RoleChange.objects.count()
    for goal in (org.adler, org.zugvoegel, org.walhall, org.boreas, org.moewen):
        assert move(org.walhall_leitung, org.walhall, org.paul, goal, client=client).status_code == 404, goal.name
    assert client.post(move_address(org.walhall, org.paul), {"ziel": "b" * 20}).status_code == 404
    assert client.post(move_address(org.walhall, org.paul), {"ziel": str(org.falken.pk)}).status_code == 404
    assert client.post(move_address(org.walhall, org.paul), {}).status_code == 404
    # Aus dem Skript ebenso.
    assert client.post(move_address(org.walhall, org.paul), {"ziel": org.adler.key},
                       headers={"x-requested-with": "fetch"}).status_code == 404

    assert unit_of(org.paul) == "Walhall"
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("VP-09", "VP-10")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/loeschen/")
def test_vv4_nur_die_leitung_der_falken_loescht_lena(org, lena):
    # Wanda und Bruno bearbeiten Lena, löschen sie aber nicht, solange die Falken Fiete haben.
    for user in (org.walhall_leitung, org.bundesleitung):
        found, _version = open_edit(user, org.falken, lena)
        assert delete_link(found) is None, user.username
        assert "löschen" not in _visible_text(found), user.username
        refused(user, delete_address(org.falken, lena), {})
    for user in (org.zugvoegel_leitung, org.falke, org.ohne, org.verbandsleitung, org.team, org.max):
        refused(user, delete_address(org.falken, lena), {})

    assert ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert not RoleChange.objects.filter(person_id=lena.pk, managed=True).exists()


@pytest.mark.rechtematrix("VP-07", "VP-09", "VP-18")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/austragen/")
def test_vv5_im_bund_gibt_es_kein_austragen_nur_verschieben_und_loeschen(org):
    berti = managed("Berti", "Probe", org.boreas, born=date(2011, 1, 11))
    shown = entries(page_tree(org.bundesleitung, unit_address(org.boreas)))
    assert set(shown["Berti Probe"]["buttons"]) == {"Bearbeiten", "Verschieben"}

    refused(org.bundesleitung, expel_address(org.boreas, berti), {"wahl": "hoch"})
    assert unit_of(berti) == "Pfadfinderbund Boreas"
    found, _version = open_edit(org.bundesleitung, org.boreas, berti)
    assert _attr(delete_link(found), "href") == delete_address(org.boreas, berti)
    assert move(org.bundesleitung, org.boreas, berti, org.zugvoegel).status_code == 302
    assert unit_of(berti) == "Zugvögel"


@pytest.mark.rechtematrix("VP-10")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/loeschen/")
def test_vv6_mit_finns_kennung_ist_loeschen_verschieben_und_austragen_nicht_gefunden(org):
    for address in (delete_address(org.falken, org.falke), expel_address(org.falken, org.falke)):
        refused(org.falken_leitung, address, {"wahl": "hoch"})
    refused(org.walhall_leitung, move_address(org.walhall, org.walhall_mitglied), {"ziel": org.falken.key})

    assert User.objects.filter(pk=org.falke.pk, is_active=True).exists()
    assert Role.objects.filter(user=org.falke, kind=R.MEMBER, unit=org.falken).exists()
    assert Role.objects.filter(user=org.walhall_mitglied, kind=R.MEMBER, unit=org.walhall).exists()


@pytest.mark.rechtematrix("VP-08", "VP-10", "VP-18")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/austragen/")
def test_vv7_verband_team_otto_und_max_ohne_zugang_aendern_nichts(org, lena, mia):
    cases = [
        (move_address(org.walhall, org.paul), {"ziel": org.falken.key}),
        (expel_address(org.woelfe, mia), {"wahl": "hoch"}),
        (expel_address(org.falken, lena), {"wahl": "hoch"}),
        (delete_address(org.walhall, org.paul), {}),
        (delete_address(org.falken, lena), {}),
    ]
    for user in (org.verbandsleitung, org.team, org.ohne, org.max, org.falke):
        for address, form in cases:
            refused(user, address, form)

    assert (unit_of(org.paul), unit_of(mia), unit_of(lena)) == ("Walhall", "Meute Wölfe", "Sippe Falken")
    assert not RoleChange.objects.filter(managed=True).exists()


@pytest.mark.rechtematrix("VP-07", "VP-09")
def test_admins_verschieben_und_loeschen_nur_im_support_zugang_mit_eintrag(org, lena):
    """#92: Im Support-Zugang hat Max die Rechte der Leitung, mit „ändern“ im Protokoll der Admin-Zugriffe."""
    from tests.test_support_zugang import start

    client = client_for(org.max)
    refused(org.max, move_address(org.walhall, org.paul), {"ziel": org.falken.key})
    assert start(org.max, org.walhall, client=client).status_code == 302
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert move(org.max, org.walhall, org.paul, org.falken, client=client).status_code == 302
    assert delete(org.max, org.falken, lena, client=client).status_code == 302

    assert unit_of(org.paul) == "Sippe Falken"
    assert not ManagedPerson.objects.filter(pk=lena.pk).exists()
    changes = AdminAccess.objects.filter(actor_id=org.max.pk, action=AdminAccess.Action.CHANGED)
    assert changes.count() == 2


# ---------- Grenzfälle ----------


def _outcome(work) -> str:
    try:
        work()
    except Http404:
        return "nicht gefunden"
    return "gelungen"


@pytest.mark.django_db(transaction=True)
def test_vg1_fiete_und_frida_loeschen_lena_gleichzeitig():
    o = build_org()
    fiete = person("fiete.falke", "Fiete", "Falke")
    frida = person("frida.falke", "Frida", "Falke")
    give(fiete, R.GROUP_LEAD, o.falken)
    give(frida, R.GROUP_LEAD, o.falken)
    lena = managed("Lena", "Probe", o.falken, scout_name="Kiwi", born=date(2015, 5, 14))

    results = _one_after_the_other(lambda: _outcome(lambda: Rights(fiete).delete_managed(o.falken, lena.key)),
                                   lambda: _outcome(lambda: Rights(frida).delete_managed(o.falken, lena.key)))

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    assert not ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert RoleChange.objects.filter(person_id=lena.pk, managed=True, action="removed").count() == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("first", ["verschieben", "löschen"])
def test_vg2_wanda_verschiebt_paul_waehrend_willi_ihn_loescht(first):
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    paul = managed("Paul", "Probe", o.walhall)
    works = {
        "verschieben": lambda: _outcome(lambda: Rights(wanda).move_managed(o.walhall, paul.key, o.falken.key)),
        "löschen": lambda: _outcome(lambda: Rights(willi).delete_managed(o.walhall, paul.key)),
    }
    second = "löschen" if first == "verschieben" else "verschieben"

    results = _one_after_the_other(works[first], works[second])

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    if first == "verschieben":
        assert ManagedPerson.objects.get(pk=paul.pk).unit_id == o.falken.pk
        assert list(RoleChange.objects.filter(person_id=paul.pk, managed=True).values_list("action", flat=True)) == [
            "removed", "granted"]
    else:
        assert not ManagedPerson.objects.filter(pk=paul.pk).exists()
        assert list(RoleChange.objects.filter(person_id=paul.pk, managed=True).values_list("action", flat=True)) == [
            "removed"]


def test_vg3_ein_doppelklick_auf_endgueltig_loeschen_loescht_einmal(org, lena):
    client = client_for(org.falken_leitung)
    before = RoleChange.objects.count()

    first = delete(org.falken_leitung, org.falken, lena, client=client)
    second = delete(org.falken_leitung, org.falken, lena, client=client)

    assert first.status_code == 302
    assert second.status_code == 404
    assert not ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert len(managed_log(before)) == 1


@pytest.mark.parametrize("action", ["anlegen", "verschieben", "austragen", "löschen"])
def test_vg4_ohne_eintrag_im_protokoll_aendert_sich_nichts(org, lena, mia, monkeypatch, action):
    def broken(*args, **kwargs):
        raise DatabaseError("Das Protokoll lässt sich gerade nicht schreiben.")

    monkeypatch.setattr(RoleChange, "save", broken)
    values = {"first_name": "Ole", "last_name": "Neu", "birth_date": date(2016, 1, 1), "scout_name": "",
              "consent": True}
    works = {
        "anlegen": lambda: Rights(org.falken_leitung).add_managed(org.falken, values, "e" * 20),
        "verschieben": lambda: Rights(org.walhall_leitung).move_managed(org.walhall, org.paul.key, org.falken.key),
        "austragen": lambda: Rights(org.woelfe_leitung).expel_managed(org.woelfe, mia.key, "hoch"),
        "löschen": lambda: Rights(org.falken_leitung).delete_managed(org.falken, lena.key),
    }

    with pytest.raises(DatabaseError):
        works[action]()

    assert not ManagedPerson.objects.filter(last_name="Neu").exists()
    assert (unit_of(org.paul), unit_of(mia), unit_of(lena)) == ("Walhall", "Meute Wölfe", "Sippe Falken")


@pytest.mark.rechtematrix("VP-10")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/loeschen/")
def test_vg5_fiete_wird_entfernt_waehrend_die_rueckfrage_offen_ist(org, lena):
    fiete = client_for(org.falken_leitung)
    confirmation(fiete.get(delete_address(org.falken, lena)))
    role = Role.objects.get(user=org.falken_leitung, kind=R.GROUP_LEAD, unit=org.falken)
    assert client_for(org.walhall_leitung).post(f"{unit_address(org.falken)}entfernen/{role.key}/").status_code == 302

    response = delete(org.falken_leitung, org.falken, lena, client=fiete)

    assert response.status_code == 404
    assert ManagedPerson.objects.filter(pk=lena.pk).exists()
    assert_like_missing(org.falken_leitung, delete_address(org.falken, lena))


def test_vg6_namen_geburtsdatum_und_fahrtenname_kommen_nicht_ins_protokoll(org, lena):
    before = RoleChange.objects.count()
    _found, version = open_edit(org.falken_leitung, org.falken, lena)

    response = save(org.falken_leitung, org.falken, lena, version, first_name="Lenchen", last_name="Prober",
                    birth_date="2015-05-15", scout_name="Kiwi Zwei")

    assert response.status_code == 302
    assert RoleChange.objects.count() == before


# ---------- Was bleibt unverändert ----------


def test_u2_der_loeschknopf_steht_nur_im_dialog_bearbeiten_nicht_beim_anlegen(org):
    """U2: Anlegen bleibt wie in #117; neu ist nur der Löschknopf im Dialog „Bearbeiten“ (löst MV7 aus #117 ab)."""
    from tests.test_verwaltete_personen import open_add

    found, _creation_key = open_add(org.falken_leitung, org.falken)

    assert delete_link(found) is None
    assert "löschen" not in _visible_text(found)


@pytest.mark.rechtematrix("PR-02")
def test_u3_eintraege_zu_verwalteten_personen_lassen_sich_nicht_aendern_oder_loeschen(org):
    from django.core.exceptions import ValidationError

    add(org.falken_leitung, org.falken)
    entry = RoleChange.objects.get(managed=True)

    entry.person_name = "Gekapert"
    with pytest.raises(ValidationError):
        entry.save()
    with pytest.raises(ValidationError):
        entry.delete()
    with pytest.raises(DatabaseError), transaction.atomic():
        RoleChange.objects.filter(pk=entry.pk).update(managed=False)
    with pytest.raises(DatabaseError), transaction.atomic():
        RoleChange.objects.filter(pk=entry.pk).delete()
    assert RoleChange.objects.get(pk=entry.pk).person_name == "Lena Probe"


@pytest.mark.rechtematrix("EH-18", "VP-08", "VP-10")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("action", ["verschieben", "austragen", "löschen"])
def test_kai_aendert_nichts_in_leuchtturm_waehrend_mona_ihn_nach_nord_verschiebt(action):
    """Befund B1 der unabhängigen Prüfung: Das Recht gilt für den Stand nach der Sperre des Bundes, nicht davor.

    Kai leitet den Ring Küste und springt für Leuchtturm ein, der keine Stammesleitung hat. Wechselt Mona Leuchtturm
    gleichzeitig nach Nord, springt Kai dort nicht mehr ein: „nicht gefunden“, und die Person bleibt, wie sie ist.
    """
    o = build_org()
    mona = person("mona.mosaik", "Mona", "Mosaik")
    kai = person("kai.kueste", "Kai", "Kueste")
    give(mona, R.ASSOCIATION_LEAD, o.mosaik)
    give(kai, R.RING_LEAD, o.kueste)
    nele = person("nele.nord", "Nele", "Nord")
    give(nele, R.RING_LEAD, o.nord)
    lotta = managed("Lotta", "Probe", o.leuchtturm)
    works = {
        "verschieben": lambda: Rights(kai).move_managed(o.leuchtturm, lotta.key, o.moewen.key),
        "austragen": lambda: Rights(kai).expel_managed(o.leuchtturm, lotta.key, "hoch"),
        "löschen": lambda: Rights(kai).delete_managed(o.leuchtturm, lotta.key),
    }

    results = _one_after_the_other(lambda: Rights(mona).change_ring(o.leuchtturm, o.nord.key),
                                   lambda: _outcome(works[action]))

    assert "nicht gefunden" in results
    assert ManagedPerson.objects.get(pk=lotta.pk).unit_id == o.leuchtturm.pk
    assert not RoleChange.objects.filter(person_id=lotta.pk, managed=True).exists()
