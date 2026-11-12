"""Tests für verwaltete Personen: anlegen, sehen und bearbeiten im Abschnitt „Personen“ (#117, PER-02).

Die Kennungen M1 bis M7, MW1 bis MW3, MV1 bis MV7 und MG1 bis MG9 verweisen auf die Szenarien vom
28.10.2026, Fassung nach dem Zielbild
(https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6478724730), MG3 in
der Fassung vom 30.10.2026 (Fahrtenname höchstens 30 Zeichen,
https://github.com/sebivtt/dpv-participant-management/issues/117#issuecomment-6524836769). MG10 (wie
am Handy tippen) prüft der Rauchtest `rauchtests/test_verwaltete_personen.py`. Wortlaute nach dem Text
von #117 und der Nachklärung N1 bis N7. Personen und Organisationen wie in den Tests zu #285
(`tests/test_personen.py`); die verwalteten Personen Lena Probe „Kiwi“ (Sippe Falken), Paul Probe
(Stamm Walhall), Ole Probe (Sippe Adler) und Lotta Probe (Meute Möwen) wie in den Szenarien. Alle
Namen sind erfunden. Geprüft wird, was beim Browser ankommt, und was danach in der Datenbank steht.
"""

import hashlib
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import Role
from tests import test_personen
from tests.test_benennen import _one_after_the_other, dialog_of, notices, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_personen import admit_address, persons_head, persons_section
from tests.test_rechtepruefung import remove
from tests.test_rollen import build_org, give, person, unit
from tests.query_limit import assert_queries_do_not_grow
from units.models import Kind as U

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

# Die Fixtures aus tests/test_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_personen.base_org
org_189 = test_personen.org_189
org_190 = test_personen.org_190
org_285 = test_personen.org

CHANGED_MEANWHILE = (
    "Kiwi (Lena Probe) wurde inzwischen von jemand anderem geändert. Bitte prüfe die Angaben und speichere erneut."
)
LENA = {"first_name": "Lena", "last_name": "Probe", "birth_date": "2015-05-14", "scout_name": "Kiwi"}


def managed(first_name: str, last_name: str, where, scout_name: str = "", born: date = date(2014, 3, 1)):
    """Eine verwaltete Person, wie sie das Tool speichert."""
    return ManagedPerson.objects.create(first_name=first_name, last_name=last_name, scout_name=scout_name,
                                        birth_date=born, unit=where)


@pytest.fixture
def org(org_285):
    """Die Personen aus #285 und die verwalteten Personen der Szenarien außer Lena, die Fiete in M1 erst anlegt."""
    org = org_285
    org.paul = managed("Paul", "Probe", org.walhall, born=date(2012, 9, 3))
    org.ole = managed("Ole", "Probe", org.adler, born=date(2016, 2, 29))
    org.lotta = managed("Lotta", "Probe", org.moewen, born=date(2017, 7, 7))
    return org


@pytest.fixture
def lena(org):
    """Lena Probe „Kiwi“ in der Sippe Falken, wie nach M1."""
    return managed("Lena", "Probe", org.falken, scout_name="Kiwi", born=date(2015, 5, 14))


def add_address(where) -> str:
    return f"{unit_address(where)}verwaltete-person/anlegen/"


def edit_address(where, entry) -> str:
    return f"{unit_address(where)}verwaltete-person/{entry.key}/bearbeiten/"


def back_from_add(where) -> str:
    """Wohin „Verwaltete Person anlegen“ zurückführt: zum Knopf, der den Dialog geöffnet hat."""
    return f"{unit_address(where)}#verwaltete-person-anlegen"


def back_from_edit(where, entry) -> str:
    """Wohin „… bearbeiten“ zurückführt: zum Knopf „Bearbeiten“ dieser Person."""
    return f"{unit_address(where)}#bearbeiten-{entry.key}"


def hidden(root, name: str) -> str:
    """Der Wert eines versteckten Felds im Dialog, etwa die Kennung des Dialogs beim Anlegen."""
    return _attr(_one(_by_tag(dialog_of(root), "input", name=name)), "value")


def open_add(user, where, client=None) -> tuple:
    """Öffnet „Verwaltete Person anlegen“; gibt den Dialog und die Kennung des Dialogs zurück."""
    root = _tree((client or client_for(user)).get(add_address(where)))
    return dialog_of(root), hidden(root, "creation_key")


def add(user, where, client=None, **values):
    """Öffnet den Dialog und schickt ihn ab, wie der Knopf „Anlegen“; `values` ersetzen Lenas Angaben.

    Seit #98 schiebt die Leitung dabei den Regler der Einwilligung auf „an“ (DSG-02).
    """
    client = client or client_for(user)
    _dialog, creation_key = open_add(user, where, client=client)
    return client.post(add_address(where), {**LENA, "consent": "an", "creation_key": creation_key, **values})


def open_edit(user, where, entry, client=None) -> tuple:
    """Öffnet „… bearbeiten“; gibt den Dialog und den Stand beim Öffnen zurück."""
    root = _tree((client or client_for(user)).get(edit_address(where, entry)))
    return dialog_of(root), hidden(root, "version")


def save(user, where, entry, version: str, client=None, **values):
    """Schickt „… bearbeiten“ ab, mit den Angaben von `entry` und den Änderungen in `values`."""
    form = {"first_name": entry.first_name, "last_name": entry.last_name, "birth_date": entry.birth_date.isoformat(),
            "scout_name": entry.scout_name, "version": version, **values}
    return (client or client_for(user)).post(edit_address(where, entry), form)


def entries(root) -> dict[str, dict]:
    """Jede Person im Abschnitt „Personen“: sichtbarer Text, Name dahinter, Marken, Mail und Knöpfe mit Adresse."""
    found = {}
    for entry in _all(persons_section(root), lambda e: "a-leitung" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        extra = _all(entry, lambda e: "a-anzeigename-zusatz" in _classes(e))
        mails = _all(entry, lambda e: "a-leitung-mail" in _classes(e))
        found[name] = {
            "text": _visible_text(entry),
            "extra": _text(extra[0]) if extra else "",
            "marks": [_visible_text(mark) for mark in _all(entry, lambda e: "a-kennmarke" in _classes(e))],
            "mail": _visible_text(mails[0]) if mails else "",
            "buttons": {_visible_text(button): _attr(button, "href") for button in _all(entry, lambda e: "btn" in _classes(e))},
        }
    return found


def head_buttons(root) -> dict[str, str]:
    """Die Knöpfe im Kopf des Abschnitts „Personen“ in ihrer Reihenfolge, mit ihren Adressen."""
    links = _all(persons_section(root), lambda e: "a-flaeche-aktion" in _classes(e))
    return {_visible_text(link): _attr(link, "href") for link in links}


def field_names(dialog) -> list[str]:
    """Die Eingabefelder des Dialogs, ohne versteckte Felder und Knöpfe."""
    fields = _all(dialog, lambda e: e.name in ("input", "select", "textarea") and _attr(e, "type") not in ("hidden", "submit"))
    return [_attr(field, "name") for field in fields]


def field_error(dialog, name: str) -> str:
    """Der Fehler am Feld `name`, über aria-describedby mit ihm verbunden; leer ohne Fehler."""
    field = _one(_by_tag(dialog, "input", name=name))
    if _attr(field, "aria-invalid") != "true":
        return ""
    described = (_attr(field, "aria-describedby") or "").split()
    errors = [_visible_text(_one(_all(dialog, lambda e, wanted=wanted: _attr(e, "id") == wanted)))
              for wanted in described if wanted.endswith("-fehler")]
    return " ".join(errors)


def value_of(dialog, name: str) -> str:
    return _attr(_one(_by_tag(dialog, "input", name=name)), "value") or ""


def lena_now() -> ManagedPerson:
    return ManagedPerson.objects.get(first_name="Lena")


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VP-01", "GA-05")
def test_m1_fiete_legt_lena_in_den_falken_an(org):
    client = client_for(org.falken_leitung)
    root = page_tree(org.falken_leitung, unit_address(org.falken))
    assert head_buttons(root)["Verwaltete Person anlegen"] == add_address(org.falken)

    found, _creation_key = open_add(org.falken_leitung, org.falken, client=client)
    assert _text(_one(_by_tag(found, "h2"))) == "Verwaltete Person anlegen"
    assert "in Sippe Falken · ohne Konto, verwaltet" in _visible_text(found)
    # Seit #98 steht unter den vier Feldern der Regler der Einwilligung (DSG-02).
    assert field_names(found) == ["first_name", "last_name", "birth_date", "scout_name", "consent"]
    assert [_visible_text(button) for button in _by_tag(found, "button")] == ["Anlegen"]

    response = add(org.falken_leitung, org.falken, client=client)

    assert response.status_code == 302
    assert response.url == back_from_add(org.falken)
    created = lena_now()
    assert (created.first_name, created.last_name, created.scout_name, created.birth_date, created.unit_id) == (
        "Lena", "Probe", "Kiwi", date(2015, 5, 14), org.falken.pk)
    page = client.get(response.url)
    assert short_notices(page) == ["Kiwi (Lena Probe) gehört jetzt zu Sippe Falken."]
    shown = entries(_tree(page))["Kiwi"]
    assert shown["extra"] == "(Lena Probe)"
    assert shown["marks"] == ["verwaltet"]
    assert shown["mail"] == ""
    # Kein Geburtsdatum in der Liste, in keiner Schreibweise.
    assert not re.search(r"2015|14\.0?5\.", shown["text"])


@pytest.mark.rechtematrix("VP-01")
def test_m2_wanda_legt_paul_ohne_fahrtennamen_in_walhall_an(org):
    org.paul.delete()

    response = add(org.walhall_leitung, org.walhall, first_name="Paul", last_name="Probe", birth_date="2012-09-03",
                   scout_name="")

    assert response.status_code == 302
    created = ManagedPerson.objects.get(first_name="Paul")
    assert (created.unit_id, created.scout_name) == (org.walhall.pk, "")
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    assert entries(root)["Paul Probe"]["extra"] == ""


@pytest.mark.rechtematrix("VP-01", "VP-17", "EH-18")
def test_m3_ohne_gruppenleitung_springt_wanda_in_den_woelfen_ein(org):
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)

    root = page_tree(org.walhall_leitung, unit_address(org.woelfe))
    assert "Verwaltete Person anlegen" in head_buttons(root)
    response = add(org.walhall_leitung, org.woelfe, first_name="Wanja", last_name="Probe", scout_name="")

    assert response.status_code == 302
    assert ManagedPerson.objects.get(first_name="Wanja").unit_id == org.woelfe.pk
    page = client_for(org.walhall_leitung).get(unit_address(org.woelfe))
    assert "Wanja Probe" in entries(_tree(page))


@pytest.mark.rechtematrix("VP-02", "VP-03")
def test_m4_wanda_willi_und_bruno_sehen_lena_und_koennen_sie_bearbeiten(org, lena):
    for user in (org.walhall_leitung, org.willi, org.bundesleitung, org.falken_leitung):
        shown = entries(page_tree(user, unit_address(org.falken)))
        # Seit #118 trägt Fiete als Gruppenleitung der Falken Lena auch aus (VP-18); die anderen nicht.
        expected = {"Bearbeiten": edit_address(org.falken, lena)}
        if user == org.falken_leitung:
            expected["Austragen"] = f"{unit_address(org.falken)}verwaltete-person/{lena.key}/austragen/"
        assert shown["Kiwi"]["buttons"] == expected, user.username
        found, version = open_edit(user, org.falken, lena)
        assert _text(_one(_by_tag(found, "h2"))) == "Kiwi (Lena Probe) bearbeiten"
        assert value_of(found, "birth_date") == "2015-05-14"
        response = save(user, org.falken, lena, version, scout_name=f"Kiwi {user.first_name}")
        assert response.status_code == 302, user.username
        lena.refresh_from_db()
        assert lena.scout_name == f"Kiwi {user.first_name}"
        lena.scout_name = "Kiwi"
        lena.save()


@pytest.mark.rechtematrix("VP-02")
def test_m4_in_mosaik_sehen_mona_und_kai_lotta_in_der_meute_moewen(org):
    for user in (org.mosaik_leitung, org.kueste_leitung):
        shown = entries(page_tree(user, unit_address(org.moewen)))
        assert shown["Lotta Probe"]["buttons"] == {"Bearbeiten": edit_address(org.moewen, org.lotta)}, user.username
        _found, version = open_edit(user, org.moewen, org.lotta)
        assert save(user, org.moewen, org.lotta, version, birth_date=f"2017-07-0{version}").status_code == 302
        org.lotta.refresh_from_db()
        assert org.lotta.birth_date == date(2017, 7, int(version)), user.username


@pytest.mark.rechtematrix("VP-02")
def test_m5_fiete_aendert_lenas_geburtsdatum(org, lena):
    client = client_for(org.falken_leitung)
    _found, version = open_edit(org.falken_leitung, org.falken, lena, client=client)

    response = save(org.falken_leitung, org.falken, lena, version, client=client, birth_date="2015-05-15")

    assert response.status_code == 302
    assert response.url == back_from_edit(org.falken, lena)
    assert short_notices(client.get(response.url)) == ["Die Angaben zu Kiwi (Lena Probe) sind gespeichert."]
    lena.refresh_from_db()
    assert lena.birth_date == date(2015, 5, 15)
    found, _version = open_edit(org.falken_leitung, org.falken, lena, client=client)
    assert value_of(found, "birth_date") == "2015-05-15"


def test_m6_mitglieder_und_lena_stehen_gemischt_nach_nachname(org, lena):
    managed("Emil", "Eber", org.falken)

    root = page_tree(org.falken_leitung, unit_address(org.falken))

    assert list(entries(root)) == ["Emil Eber", "Funke", "Flink", "Kiwi"]
    assert persons_head(root) == "4 Personen"
    assert list(head_buttons(root)) == ["Verwaltete Person anlegen", "Person mit Konto aufnehmen"]
    assert head_buttons(root)["Person mit Konto aufnehmen"] == admit_address(org.falken)
    shown = entries(root)
    # Personen mit Konto bleiben, wie sie sind: mit Mail, ohne Marke „verwaltet“.
    assert shown["Flink"]["mail"] == "finn.falke@example.org"
    assert shown["Flink"]["marks"] == []
    dialog = dialog_of(_tree(client_for(org.falken_leitung).get(admit_address(org.falken))))
    assert _text(_one(_by_tag(dialog, "h2"))) == "Person mit Konto aufnehmen"


def test_m7_leere_liste_mit_hinweis_nur_fuer_wer_dort_anlegen_darf(org):
    eulen = unit(U.GROUP, "Sippe Eulen", org.walhall)
    kraniche = unit(U.GROUP, "Sippe Kraniche", org.walhall)
    kira = person("kira.kranich", "Kira", "Kranich")
    give(kira, R.MEMBER, org.walhall)
    give(kira, R.GROUP_LEAD, kraniche)
    first = "Dieser Organisation sind noch keine Personen zugeordnet."
    second = "Du kannst oben eine verwaltete Person anlegen oder eine bereits registrierte Person aufnehmen."

    may_add = [(org.walhall_leitung, eulen), (kira, kraniche)]
    only_sees = [(org.walhall_leitung, kraniche), (org.bundesleitung, eulen)]
    for user, where in may_add:
        text = _visible_text(persons_section(page_tree(user, unit_address(where))))
        assert f"{first} {second}" in text, (user.username, where.name)
    for user, where in only_sees:
        text = _visible_text(persons_section(page_tree(user, unit_address(where))))
        assert first in text and second not in text, (user.username, where.name)
        assert "gehört direkt noch niemand" not in text


def test_nach_dem_dialog_kehrt_der_fokus_zum_knopf_zurueck(org, lena):
    """Aus dem Zielbild: Nach dem Dialog liegt der Fokus wieder auf dem Knopf, der ihn geöffnet hat.

    × und „Abbrechen“ führen zur Seite mit der Kennung des Knopfs in der Adresse; das Skript gibt ihm
    dort den Fokus. Den Weg im Browser prüft der Rauchtest.
    """
    root = page_tree(org.falken_leitung, unit_address(org.falken))
    add_button = _one([link for link in _all(persons_section(root), lambda e: "a-flaeche-aktion" in _classes(e))
                       if _attr(link, "href") == add_address(org.falken)])
    edit_button = _one(_by_tag(persons_section(root), "a", href=edit_address(org.falken, lena)))
    assert _attr(add_button, "id") == "verwaltete-person-anlegen"
    assert _attr(edit_button, "id") == f"bearbeiten-{lena.key}"

    for found, back in ((open_add(org.falken_leitung, org.falken)[0], back_from_add(org.falken)),
                        (open_edit(org.falken_leitung, org.falken, lena)[0], back_from_edit(org.falken, lena))):
        # Seit #118 steht im Dialog „Bearbeiten“ für Fiete auch „Verwaltete Person löschen“; das schließt nicht.
        closing = [_attr(link, "href") for link in _by_tag(found, "a") if _visible_text(link) != "Verwaltete Person löschen"]
        assert closing == [back, back]


# ---------- Leitungswechsel (Abschlusskriterium von P2) ----------


@pytest.mark.rechtematrix("VP-04", "VP-05")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_mw1_die_entfernte_gruppenleitung_speichert_im_offenen_dialog_nichts(org):
    fiete = client_for(org.falken_leitung)
    assert add(org.falken_leitung, org.falken, client=fiete).status_code == 302
    lena = lena_now()
    _found, version = open_edit(org.falken_leitung, org.falken, lena, client=fiete)

    role = Role.objects.get(user=org.falken_leitung, kind=R.GROUP_LEAD, unit=org.falken)
    removed = client_for(org.walhall_leitung).post(f"{unit_address(org.falken)}entfernen/{role.key}/")
    assert removed.status_code == 302

    response = save(org.falken_leitung, org.falken, lena, version, client=fiete, first_name="Lenchen")
    assert response.status_code == 404
    lena.refresh_from_db()
    assert lena.first_name == "Lena"
    assert fiete.get(edit_address(org.falken, lena)).status_code == 404
    assert fiete.get(unit_address(org.falken)).status_code == 404
    assert_like_missing(org.falken_leitung, edit_address(org.falken, lena))
    # Fiete bleibt Mitglied der Falken.
    assert Role.objects.filter(user=org.falken_leitung, kind=R.MEMBER, unit=org.falken).exists()


@pytest.mark.rechtematrix("VP-04")
def test_mw1_gegenprobe_wanda_bearbeitet_lena_nach_dem_entfernen_weiter(org, lena):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    _found, version = open_edit(org.walhall_leitung, org.falken, lena)

    assert save(org.walhall_leitung, org.falken, lena, version, first_name="Lenchen").status_code == 302
    lena.refresh_from_db()
    assert lena.first_name == "Lenchen"


@pytest.mark.rechtematrix("VP-02", "VP-05")
def test_mw2_frida_sieht_lena_nach_dem_benennen_und_kann_sie_bearbeiten(org, lena):
    frida = person("frida.falke", "Frida", "Falke")
    give(frida, R.MEMBER, org.falken)
    User.objects.filter(pk=frida.pk).update(last_login=timezone.now())
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    assert client_for(frida).get(edit_address(org.falken, lena)).status_code == 404

    appointed = client_for(org.walhall_leitung).post(f"{unit_address(org.falken)}benennen/", {"person": frida.key})
    assert appointed.status_code == 302

    shown = entries(page_tree(frida, unit_address(org.falken)))
    # Seit #118 trägt die Gruppenleitung verwaltete Personen auch aus (VP-18).
    assert shown["Kiwi"]["buttons"] == {"Bearbeiten": edit_address(org.falken, lena),
                                        "Austragen": f"{unit_address(org.falken)}verwaltete-person/{lena.key}/austragen/"}
    _found, version = open_edit(frida, org.falken, lena)
    assert save(frida, org.falken, lena, version, scout_name="Kiwi Frida").status_code == 302


@pytest.mark.rechtematrix("VP-17", "EH-18", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/anlegen/")
def test_mw3_das_einspringen_endet_bei_offenem_dialog_und_niemand_wird_angelegt(org):
    wolke = managed("Wolke", "Probe", org.woelfe)
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)
    wanda = client_for(org.walhall_leitung)
    _found, creation_key = open_add(org.walhall_leitung, org.woelfe, client=wanda)

    give(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)

    response = wanda.post(add_address(org.woelfe), {**LENA, "consent": "an", "creation_key": creation_key})
    assert response.status_code == 404
    assert not ManagedPerson.objects.filter(first_name="Lena").exists()
    assert_like_missing(org.walhall_leitung, add_address(org.woelfe))
    # Sehen und bearbeiten kann Wanda die Personen der Meute weiter (VP-02).
    shown = entries(page_tree(org.walhall_leitung, unit_address(org.woelfe)))
    assert "Bearbeiten" in shown["Wolke Probe"]["buttons"]
    _found, version = open_edit(org.walhall_leitung, org.woelfe, wolke, client=wanda)
    assert save(org.walhall_leitung, org.woelfe, wolke, version, client=wanda, scout_name="Wolke").status_code == 302


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VP-01", "VP-17", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/anlegen/")
def test_mv1_ohne_einspringen_legt_niemand_in_einer_organisation_darunter_an(org):
    forbidden = [(org.walhall_leitung, org.falken), (org.bundesleitung, org.walhall), (org.kueste_leitung, org.leuchtturm)]
    for user, where in forbidden:
        assert "Verwaltete Person anlegen" not in head_buttons(page_tree(user, unit_address(where))), user.username
        assert_like_missing(user, add_address(where))
        response = client_for(user).post(add_address(where), {**LENA, "consent": "an", "creation_key": "b" * 20})
        assert response.status_code == 404

    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


@pytest.mark.rechtematrix("VP-02", "VP-03")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_mv2_zora_wim_und_ada_sehen_und_bearbeiten_lena_nicht(org, lena):
    for user in (org.zugvoegel_leitung, org.woelfe_leitung, org.adler_leitung):
        assert client_for(user).get(unit_address(org.falken)).status_code == 404, user.username
        assert_like_missing(user, edit_address(org.falken, lena))
        assert_like_missing(user, add_address(org.falken))
        own = client_for(user).get(unit_address(Role.objects.filter(user=user, kind__in=(R.GROUP_LEAD, R.TROOP_LEAD))
                                                 .get().unit)).content.decode()
        assert "Kiwi" not in own and "Lena" not in own

    lena.refresh_from_db()
    assert (lena.first_name, lena.scout_name) == ("Lena", "Kiwi")


@pytest.mark.rechtematrix("VP-03")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_fiete_bearbeitet_und_legt_auf_der_leseseite_von_walhall_nichts_an(org):
    """Von unten nach oben: Walhall liegt nur auf Fietes Kette, nicht in seinem Bereich (unabhängige Prüfung, Befund 5)."""
    assert client_for(org.falken_leitung).get(unit_address(org.walhall)).status_code == 200
    assert "Paul" not in client_for(org.falken_leitung).get(unit_address(org.walhall)).content.decode()
    assert_like_missing(org.falken_leitung, edit_address(org.walhall, org.paul))
    assert_like_missing(org.falken_leitung, add_address(org.walhall))
    response = client_for(org.falken_leitung).post(edit_address(org.walhall, org.paul),
                                                    {**LENA, "first_name": "Gekapert", "version": "1"})
    assert response.status_code == 404
    org.paul.refresh_from_db()
    assert org.paul.first_name == "Paul"


def test_die_dialoge_pruefen_im_tool_nicht_im_browser(org, lena):
    """Die Meldungen am Feld kommen vom Tool, nicht als Blase des Browsers (MG1, MG4; unabhängige Prüfung, Befund 1)."""
    for found in (open_add(org.falken_leitung, org.falken)[0], open_edit(org.falken_leitung, org.falken, lena)[0]):
        form = _one(_by_tag(found, "form", id="f-dialog"))
        assert _attr(form, "novalidate") is not None


def test_der_dialog_anlegen_kommt_nicht_aus_dem_zwischenspeicher(org):
    """Nach „Zurück“ im Browser kommt der Dialog neu vom Server, mit neuer Kennung; sonst legte die zweite Person
    stillschweigend niemanden an (MG7; unabhängige Prüfung, Befund 2)."""
    response = client_for(org.falken_leitung).get(add_address(org.falken))

    assert "no-store" in response["Cache-Control"]


@pytest.mark.rechtematrix("VP-06")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_mv3_finn_otto_vera_tom_und_max_sehen_keine_verwalteten_personen(org, lena):
    for user in (org.falke, org.ohne, org.verbandsleitung, org.team, org.max):
        assert_like_missing(user, edit_address(org.falken, lena))
        assert_like_missing(user, add_address(org.falken))
        # Admins öffnen die Seite seit #92 nur mit dem Kopf (S1); alle anderen gar nicht.
        expected = 200 if user == org.max else 404
        assert client_for(user).get(unit_address(org.falken)).status_code == expected, user.username
        for address in ("/", "/profil/", "/organisation/"):
            content = client_for(user).get(address).content.decode()
            assert "Kiwi" not in content and "Probe" not in content, (user.username, address)

    assert ManagedPerson.objects.count() == 4


@pytest.mark.rechtematrix("VP-06")
def test_verbandsleitung_sieht_keine_verwalteten_personen_auch_nicht_ueber_den_bund(org, lena):
    """Test aus #94 (Nachklärung vom 22.10.2026): auch über die Seite „Verband“ und direkte Adressen nicht."""
    vera = client_for(org.verbandsleitung)
    for where, entry in ((org.falken, lena), (org.walhall, org.paul), (org.moewen, org.lotta)):
        assert vera.get(edit_address(where, entry)).status_code == 404
        assert vera.post(edit_address(where, entry), {"first_name": "Gekapert", "version": "1"}).status_code == 404
        assert vera.get(unit_address(where)).status_code == 404
    assert vera.post(add_address(org.boreas), {**LENA, "consent": "an", "creation_key": "c" * 20}).status_code == 404
    page = vera.get("/organisation/").content.decode()
    assert "Probe" not in page
    assert ManagedPerson.objects.filter(first_name="Lena", unit=org.boreas).count() == 0


@pytest.mark.rechtematrix("VP-06")
def test_mv3_gegenprobe_finn_als_gruppenleitung_sieht_lena(org, lena):
    """Die Rolle gibt das Recht, nicht das Konto: Finn sieht Lena, sobald er die Falken leitet."""
    give(org.falke, R.GROUP_LEAD, org.falken)

    assert "Kiwi" in entries(page_tree(org.falke, unit_address(org.falken)))


@pytest.mark.rechtematrix("VP-01")
def test_mv4_eine_fremde_organisation_im_formular_aendert_nichts(org):
    response = add(org.falken_leitung, org.falken, unit=org.adler.key, organisation=org.adler.key,
                   organisation_unit=org.adler.key)

    assert response.status_code == 302
    assert lena_now().unit_id == org.falken.pk
    assert not ManagedPerson.objects.filter(unit=org.adler, first_name="Lena").exists()


@pytest.mark.rechtematrix("VP-03")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_mv4_eine_fremde_kennung_beim_bearbeiten_ist_nicht_gefunden(org, lena):
    _found, version = open_edit(org.falken_leitung, org.falken, lena)
    cases = [
        (org.falken_leitung, org.falken, org.ole),
        (org.falken_leitung, org.falken, org.paul),
        (org.walhall_leitung, org.falken, org.ole),
        # Lena gehört direkt zu den Falken, nicht zu Walhall: Die Organisation der Adresse muss stimmen.
        (org.walhall_leitung, org.walhall, lena),
    ]
    for user, where, entry in cases:
        assert_like_missing(user, edit_address(where, entry))
        response = client_for(user).post(edit_address(where, entry), {**LENA, "first_name": "Gekapert", "version": version})
        assert response.status_code == 404

    assert not ManagedPerson.objects.filter(first_name="Gekapert").exists()


@pytest.mark.rechtematrix("VP-03")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verwaltete-person/<key:person>/bearbeiten/")
def test_mv5_finns_kennung_ergibt_beim_bearbeiten_nicht_gefunden(org, lena):
    assert_like_missing(org.falken_leitung, edit_address(org.falken, org.falke))
    response = client_for(org.falken_leitung).post(edit_address(org.falken, org.falke),
                                                    {**LENA, "first_name": "Gekapert", "version": "1"})

    assert response.status_code == 404
    org.falke.refresh_from_db()
    assert org.falke.first_name == "Finn"
    shown = entries(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert "Bearbeiten" not in shown["Flink"]["buttons"]
    assert "Bearbeiten" not in shown["Funke"]["buttons"]


@pytest.mark.rechtematrix("GA-05")
def test_mv6_gesundheitsangaben_werden_nicht_gespeichert(org):
    response = add(org.falken_leitung, org.falken, allergien="Nüsse", gesundheit="Asthma", medikamente="Spray",
                   health="Asthma")

    assert response.status_code == 302
    created = lena_now()
    stored = {field.name for field in ManagedPerson._meta.concrete_fields}
    # Seit #98 dazu, wer wann die Einwilligung bestätigt hat (DSG-02); Gesundheitsangaben weiter nicht.
    assert stored == {"id", "key", "first_name", "last_name", "birth_date", "scout_name", "unit", "version",
                      "creation_key", "consent_by", "consent_at"}
    assert all("Asthma" not in str(getattr(created, name)) for name in stored)
    found, _creation_key = open_add(org.falken_leitung, org.falken)
    assert field_names(found) == ["first_name", "last_name", "birth_date", "scout_name", "consent"]


def test_mv7_im_dialog_bearbeiten_gibt_es_keinen_loeschknopf(org, lena):
    """MV7 ist seit #118 abgelöst (Szenario U2 dort): Den Löschknopf hat jetzt die Leitung der eigenen Organisation
    der Person, hier Fiete (`tests/test_verwaltete_personen_verschieben.py`). Wer nur bearbeiten darf, wie Wanda,
    hat ihn weiter nicht."""
    for user in (org.walhall_leitung,):
        found, _version = open_edit(user, org.falken, lena)
        assert [_visible_text(button) for button in _by_tag(found, "button")] == ["Speichern"]
        assert "Löschen" not in _visible_text(found)
        assert "löschen" not in _visible_text(found)


# ---------- Grenzfälle ----------


def test_mg1_leere_pflichtfelder_zeigen_den_fehler_am_feld_und_der_rest_bleibt(org):
    response = add(org.falken_leitung, org.falken, first_name="   ", last_name="", birth_date="")

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert field_error(found, "first_name") == "Bitte gib den Vornamen ein."
    assert field_error(found, "last_name") == "Bitte gib den Nachnamen ein."
    assert field_error(found, "birth_date") == "Bitte gib das Geburtsdatum ein."
    assert field_error(found, "scout_name") == ""
    assert value_of(found, "scout_name") == "Kiwi"
    assert not ManagedPerson.objects.filter(scout_name="Kiwi").exists()


def test_mg1_auch_beim_bearbeiten_bleibt_die_eingabe_stehen(org, lena):
    _found, version = open_edit(org.falken_leitung, org.falken, lena)

    response = save(org.falken_leitung, org.falken, lena, version, first_name="", scout_name="Kiwi Neu")

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert field_error(found, "first_name") == "Bitte gib den Vornamen ein."
    assert value_of(found, "scout_name") == "Kiwi Neu"
    lena.refresh_from_db()
    assert (lena.first_name, lena.scout_name) == ("Lena", "Kiwi")


def test_mg2_leerzeichen_am_rand_werden_entfernt(org):
    response = add(org.falken_leitung, org.falken, first_name=" Lena ", last_name=" Probe\t", scout_name="  Kiwi ")

    assert response.status_code == 302
    created = lena_now()
    assert (created.first_name, created.last_name, created.scout_name) == ("Lena", "Probe", "Kiwi")


def test_mg3_hoechstlaengen_von_namen_und_fahrtenname(org):
    response = add(org.falken_leitung, org.falken, first_name="L" * 101, last_name="P" * 101, scout_name="K" * 31)
    found = dialog_of(_tree(response))
    assert field_error(found, "first_name") == "Der Vorname darf höchstens 100 Zeichen lang sein."
    assert field_error(found, "last_name") == "Der Nachname darf höchstens 100 Zeichen lang sein."
    assert field_error(found, "scout_name") == "Der Fahrtenname darf höchstens 30 Zeichen lang sein."
    # Nichts wird abgeschnitten: Die zu lange Eingabe bleibt stehen.
    assert value_of(found, "first_name") == "L" * 101
    assert not ManagedPerson.objects.filter(unit=org.falken).exists()

    response = add(org.falken_leitung, org.falken, first_name="L" * 100, last_name="P" * 100, scout_name="K" * 30)

    assert response.status_code == 302
    assert ManagedPerson.objects.get(unit=org.falken).scout_name == "K" * 30


def test_mg2_mg3_auch_beim_bearbeiten_fahrtenname_gekuerzt_und_hoechstens_30_zeichen(org, lena):
    """Unabhängige Prüfung zu #98, Befund 1: Das Bearbeiten prüft den Fahrtennamen wie das Anlegen, statt mit
    einem Fehler der Datenbank abzubrechen."""
    _found, version = open_edit(org.falken_leitung, org.falken, lena)
    response = save(org.falken_leitung, org.falken, lena, version, scout_name="  Kiwi Neu ")
    assert response.status_code == 302
    assert lena_now().scout_name == "Kiwi Neu"

    _found, version = open_edit(org.falken_leitung, org.falken, lena)
    response = save(org.falken_leitung, org.falken, lena, version, scout_name="K" * 31)
    assert response.status_code == 200
    assert field_error(dialog_of(_tree(response)), "scout_name") == "Der Fahrtenname darf höchstens 30 Zeichen lang sein."
    assert lena_now().scout_name == "Kiwi Neu"


def test_mg4_geburtsdatum_heute_geht_morgen_nicht(org):
    today = timezone.localdate()

    tomorrow = add(org.falken_leitung, org.falken, birth_date=(today + timedelta(days=1)).isoformat())
    assert field_error(dialog_of(_tree(tomorrow)), "birth_date") == "Das Geburtsdatum liegt in der Zukunft."
    assert add(org.falken_leitung, org.falken, birth_date=today.isoformat()).status_code == 302
    assert lena_now().birth_date == today


def test_mg4_am_28_10_2026_geht_der_28_10_1906_der_27_10_1906_nicht(org, monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2026, 10, 28))

    too_old = add(org.falken_leitung, org.falken, birth_date="1906-10-27")
    assert field_error(dialog_of(_tree(too_old)), "birth_date") == "Das Geburtsdatum liegt mehr als 120 Jahre zurück."
    assert add(org.falken_leitung, org.falken, birth_date="1906-10-28").status_code == 302
    assert lena_now().birth_date == date(1906, 10, 28)


@pytest.mark.parametrize("value", ["2015-02-31", "2015-13-01", "14.05.2015", "morgen"])
def test_mg4_ein_unmoegliches_datum_ist_ungueltig(org, value):
    response = add(org.falken_leitung, org.falken, birth_date=value)

    assert field_error(dialog_of(_tree(response)), "birth_date") == "Bitte gib ein gültiges Geburtsdatum ein."
    assert not ManagedPerson.objects.filter(unit=org.falken).exists()


def test_mg4_das_datumsfeld_ist_das_feld_des_browsers_ohne_tage_in_der_zukunft(org):
    found, _creation_key = open_add(org.falken_leitung, org.falken)
    field = _one(_by_tag(found, "input", name="birth_date"))

    assert _attr(field, "type") == "date"
    assert _attr(field, "max") == timezone.localdate().isoformat()
    assert any("a-datumsfeld" in _classes(block) for block in _all(found, lambda e: e.name == "div"))


def test_mg5_eine_zweite_lena_mit_gleichem_geburtsdatum_wird_ohne_hinweis_angelegt(org, lena):
    client = client_for(org.falken_leitung)
    response = add(org.falken_leitung, org.falken, client=client)

    assert response.status_code == 302
    assert ManagedPerson.objects.filter(first_name="Lena", last_name="Probe", birth_date=date(2015, 5, 14)).count() == 2
    page = client.get(response.url)
    assert short_notices(page) == ["Kiwi (Lena Probe) gehört jetzt zu Sippe Falken."]


def test_mg6_wanda_speichert_zuerst_und_fiete_ueberschreibt_nichts(org, lena):
    _found, fiete_version = open_edit(org.falken_leitung, org.falken, lena)
    _found, wanda_version = open_edit(org.walhall_leitung, org.falken, lena)
    assert save(org.walhall_leitung, org.falken, lena, wanda_version, birth_date="2015-05-15").status_code == 302

    response = save(org.falken_leitung, org.falken, lena, fiete_version, first_name="Lenchen")

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert CHANGED_MEANWHILE in notices(found)
    # Der Dialog zeigt Wandas Stand, nicht Fietes Eingabe.
    assert value_of(found, "birth_date") == "2015-05-15"
    assert value_of(found, "first_name") == "Lena"
    lena.refresh_from_db()
    assert (lena.first_name, lena.birth_date) == ("Lena", date(2015, 5, 15))
    # Mit dem neuen Stand speichert Fiete danach.
    assert save(org.falken_leitung, org.falken, lena, hidden(_tree(response), "version"),
                first_name="Lenchen").status_code == 302
    lena.refresh_from_db()
    assert (lena.first_name, lena.birth_date) == ("Lenchen", date(2015, 5, 15))


@pytest.mark.django_db(transaction=True)
def test_mg6_gleichzeitig_gespeichert_gelingt_genau_eine_aenderung():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    fiete = person("fiete.falke", "Fiete", "Falke")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(fiete, R.GROUP_LEAD, o.falken)
    lena = managed("Lena", "Probe", o.falken, scout_name="Kiwi", born=date(2015, 5, 14))
    values = {"first_name": "Lena", "last_name": "Probe", "birth_date": date(2015, 5, 14), "scout_name": "Kiwi"}

    results = _one_after_the_other(
        lambda: Rights(wanda).edit_managed(o.falken, lena.key, {**values, "birth_date": date(2015, 5, 15)}, "1"),
        lambda: Rights(fiete).edit_managed(o.falken, lena.key, {**values, "first_name": "Lenchen"}, "1"))

    assert sorted(done for done, _entry, _text in results) == [False, True]
    lena.refresh_from_db()
    assert (lena.first_name, lena.birth_date, lena.version) == ("Lena", date(2015, 5, 15), 2)


def test_mg7_doppelklick_auf_anlegen_legt_lena_nur_einmal_an(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)
    form = {**LENA, "consent": "an", "creation_key": creation_key}

    first = client.post(add_address(org.falken), form)
    second = client.post(add_address(org.falken), form)

    assert (first.status_code, second.status_code) == (302, 302)
    assert second.url == back_from_add(org.falken)
    assert ManagedPerson.objects.filter(first_name="Lena").count() == 1
    assert short_notices(client.get(second.url)) == ["Kiwi (Lena Probe) gehört jetzt zu Sippe Falken."]


@pytest.mark.django_db(transaction=True)
def test_mg7_gleichzeitig_abgeschickt_entsteht_lena_nur_einmal():
    o = build_org()
    fiete = person("fiete.falke", "Fiete", "Falke")
    give(fiete, R.GROUP_LEAD, o.falken)
    values = {"first_name": "Lena", "last_name": "Probe", "birth_date": date(2015, 5, 14), "scout_name": "Kiwi",
              "consent": True}
    creation_key = "d" * 20

    _one_after_the_other(lambda: Rights(fiete).add_managed(o.falken, values, creation_key),
                         lambda: Rights(fiete).add_managed(o.falken, values, creation_key))

    assert ManagedPerson.objects.filter(first_name="Lena").count() == 1


def test_mg8_die_falken_lassen_sich_mit_lena_nicht_loeschen(org, lena):
    with pytest.raises(ProtectedError):
        org.falken.delete()
    # Auch an Django vorbei, direkt in der Datenbank; die Prüfung der Verweise sofort statt am Ende.
    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("DELETE FROM units_unit WHERE id = %s", [org.falken.pk])

    assert lena_now().unit_id == org.falken.pk


def test_mg9_der_abschnitt_waechst_nicht_mit_den_abfragen(org):
    client = client_for(org.walhall_leitung)

    def create_entry(number: int) -> None:
        managed("Kind", f"Nummer{number}", org.walhall, scout_name=f"Kind {number}")

    def load_list() -> None:
        response = client.get(unit_address(org.walhall))
        assert response.status_code == 200

    assert_queries_do_not_grow(create_entry, load_list)
    assert len(entries(page_tree(org.walhall_leitung, unit_address(org.walhall)))) == 4 + 1 + 10


# ---------- Datenmodell ----------


def test_eine_verwaltete_person_gehoert_nie_zum_verband(org):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="nie zum Verband"):
        managed("Vera", "Probe", org.dpv)
    for where in (org.boreas, org.kueste, org.walhall, org.falken):
        assert managed("Vera", "Probe", where).unit_id == where.pk


def test_jedes_speichern_zaehlt_den_stand_hoch(org, lena):
    _found, version = open_edit(org.falken_leitung, org.falken, lena)
    assert version == "1"

    save(org.falken_leitung, org.falken, lena, version, scout_name="Kiwi 2")

    lena.refresh_from_db()
    assert lena.version == 2


# ---------- Bausteinkatalog und Zielbild ----------


def test_der_bausteinkatalog_zeigt_das_datumsfeld_und_die_marke_verwaltet(org, settings):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(client_for(org.ohne).get("/bausteine/"))

    section = _one(_by_tag(root, "section", aria_labelledby="h-datumsfeld"))
    assert _text(_one(_by_tag(section, "h2"))) == "Datumsfeld"
    assert _attr(_one(_by_tag(section, "input", type="date")), "max")
    marks = _one(_by_tag(root, "section", aria_labelledby="h-kennmarke"))
    assert "verwaltet" in _visible_text(marks)


ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "docs" / "zielbilder" / "verwaltete-personen.html"
CHECKSUM = "be89525874bdcbb10c4c2bc5a37170c98d59eb868013040278ced48a590b005b"


def test_zielbild_liegt_unveraendert_mit_eintrag_im_repo():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()

    assert hashlib.sha256(TARGET.read_bytes()).hexdigest() == CHECKSUM
    section = readme.split("## Verwaltete Personen", 1)
    assert len(section) == 2
    for must in (CHECKSUM, "28.10.2026", "Orientierung, keine Anforderung", "Abweichungen", "#117"):
        assert must in section[1], must


def test_zielbild_laedt_nichts_von_fremden_servern():
    content = TARGET.read_text()

    assert not re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert not re.findall(r"""(?:url\(|@import)\s*["']?(?:https?:)?//""", content, flags=re.I)
    assert all(mail.endswith("@example.org") for mail in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", content))
