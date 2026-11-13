"""Tests für die Bestätigung der Einwilligung beim Anlegen einer verwalteten Person (#98, DSG-02).

Die Kennungen E1, E2, EV1 bis EV4 und EG1 bis EG6 verweisen auf die Szenarien vom 30.10.2026
(https://github.com/sebivtt/dpv-participant-management/issues/98#issuecomment-6522708412). EG3
(Verschieben und Löschen) prüft #118 in `tests/test_verwaltete_personen_verschieben.py` (V5, V9). Die Tastatur und das Antippen am Handy aus EG5 prüft der
Rauchtest `rauchtests/test_verwaltete_personen.py`; hier steht, was beim Browser ankommt und was
danach in der Datenbank steht. Der Regler ist der Baustein „Schalter“ aus #95, erweitert um die
Ansage als Ankreuzfeld und den Fehler am Feld (Sebastian, 12.11.2026: „Schalter erweitern“,
https://github.com/sebivtt/dpv-participant-management/issues/98#issuecomment-6819322761).
Personen und Organisationen wie in `tests/test_verwaltete_personen.py`; alle Namen sind erfunden.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.utils import timezone

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import Role
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_organisation import client_for, unit_address
from tests.test_rechtepruefung import remove
from tests import test_verwaltete_personen
from tests.test_verwaltete_personen import (
    LENA,
    add,
    add_address,
    edit_address,
    field_error,
    field_names,
    lena_now,
    open_add,
    open_edit,
    save,
    value_of,
)

# Die Fixtures aus tests/test_verwaltete_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_verwaltete_personen.base_org
org_189 = test_verwaltete_personen.org_189
org_190 = test_verwaltete_personen.org_190
org_285 = test_verwaltete_personen.org_285
org = test_verwaltete_personen.org
lena = test_verwaltete_personen.lena

R = Role.Kind
pytestmark = pytest.mark.django_db

SENTENCE = "Die Person bzw. bei Minderjährigen die Erziehungsberechtigten haben der Speicherung der Daten zugestimmt."
MISSING = "Bitte bestätige die Einwilligung. Ohne sie wird die Person nicht gespeichert."
ROOT = Path(__file__).resolve().parent.parent


def switch_of(dialog):
    """Der Regler im Dialog: das Ankreuzfeld „consent“."""
    return _one(_by_tag(dialog, "input", name="consent"))


def switch_row(dialog):
    """Die Zeile des Bausteins „Schalter“, in der der Regler steht."""
    return _one(_all(dialog, lambda e: "a-schalter-zeile" in _classes(e)))


def by_id(root, wanted: str):
    return _one(_all(root, lambda e: _attr(e, "id") == wanted))


def post_add(client, where, creation_key: str, **values):
    """Schickt „Verwaltete Person anlegen“ ab, ohne die Bestätigung von selbst mitzuschicken."""
    return client.post(add_address(where), {**LENA, "creation_key": creation_key, **values})


def confirmation(entry: ManagedPerson) -> tuple:
    entry.refresh_from_db()
    return entry.consent_by_id, entry.consent_at


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VP-11", "VP-12", "VP-13")
def test_e1_fiete_bestaetigt_beim_anlegen_und_sein_konto_und_die_zeit_werden_gespeichert(org):
    """Zugleich Gegenprobe zu VP-12 und VP-13: Gespeichert wird die Bestätigung, beim Anlegen im eigenen Namen."""
    client = client_for(org.falken_leitung)
    found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    # Unter den Feldern der Regler mit genau dem Satz aus DSG-02, ohne Hilfesatz und ohne „i“, auf „aus“.
    assert field_names(found) == ["first_name", "last_name", "birth_date", "scout_name", "consent"]
    switch = switch_of(found)
    assert _attr(switch, "checked") is None
    assert _attr(switch, "form") == "f-dialog"
    assert _visible_text(switch_row(found)) == SENTENCE
    assert _text(by_id(found, _attr(switch, "aria-labelledby"))) == SENTENCE

    before = timezone.now()
    response = post_add(client, org.falken, creation_key, consent="an")
    after = timezone.now()

    assert response.status_code == 302
    assert short_notices(client.get(response.url)) == ["Kiwi (Lena Probe) gehört jetzt zu Sippe Falken."]
    by, at = confirmation(lena_now())
    assert by == org.falken_leitung.pk
    assert before <= at <= after


def test_e1_der_regler_steht_beim_oeffnen_immer_auf_aus(org, lena):
    """N2: Eine Einwilligung ist nie vorbelegt, auch nicht beim nächsten Anlegen nach einer bestätigten Person."""
    client = client_for(org.falken_leitung)
    add(org.falken_leitung, org.falken, client=client, first_name="Mia", scout_name="")

    found, _creation_key = open_add(org.falken_leitung, org.falken, client=client)

    assert _attr(switch_of(found), "checked") is None


@pytest.mark.rechtematrix("VP-11")
def test_e2_wanda_springt_in_den_woelfen_ein_und_die_bestaetigung_traegt_ihr_konto(org):
    remove(org.woelfe_leitung, R.GROUP_LEAD, org.woelfe)

    response = add(org.walhall_leitung, org.woelfe, first_name="Wanja", scout_name="")

    assert response.status_code == 302
    assert confirmation(ManagedPerson.objects.get(first_name="Wanja"))[0] == org.walhall_leitung.pk


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VP-11")
def test_ev1_ohne_bestaetigung_steht_der_fehler_rot_unter_dem_regler_und_die_eingaben_bleiben(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    response = post_add(client, org.falken, creation_key)

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert field_error(found, "consent") == MISSING
    error = by_id(found, f"{_attr(switch_of(found), 'id')}-fehler")
    assert "invalid-feedback" in _classes(error)
    # Rot unter dem Regler: der Fehler folgt auf die Zeile mit dem Regler.
    order = [e for e in _all(found, lambda e: e is error or e is switch_row(found))]
    assert order == [switch_row(found), error]
    assert (value_of(found, "first_name"), value_of(found, "last_name"), value_of(found, "scout_name")) == (
        "Lena", "Probe", "Kiwi")
    assert value_of(found, "birth_date") == "2015-05-14"
    assert field_error(found, "first_name") == ""
    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


def test_ev1_nach_einem_anderen_fehler_bleibt_der_regler_wie_gewaehlt(org):
    """Die Eingaben bleiben stehen; dazu gehört auch der Regler, wenn ein anderes Feld fehlt."""
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    found = dialog_of(_tree(post_add(client, org.falken, creation_key, first_name="", consent="an")))

    assert field_error(found, "first_name") == "Bitte gib den Vornamen ein."
    assert field_error(found, "consent") == ""
    assert _attr(switch_of(found), "checked") is not None


@pytest.mark.rechtematrix("VP-13")
@pytest.mark.parametrize("value", ["", "false"])
def test_ev2_ein_manipuliertes_formular_ohne_bestaetigung_legt_niemanden_an(org, value):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    response = post_add(client, org.falken, creation_key, consent=value)

    assert response.status_code == 200
    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


@pytest.mark.rechtematrix("VP-13")
def test_ev2_eine_anfrage_aus_dem_skript_ohne_bestaetigung_legt_niemanden_an(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    # Die Anfrage aus dem Skript in EV2 ist seit #264 (Nr. 4) eine gewöhnliche Anfrage, ohne eigene Kopfzeile.
    client.post(add_address(org.falken), {**LENA, "creation_key": creation_key})
    with pytest.raises(ValidationError):
        Rights(org.falken_leitung).add_managed(
            org.falken, {"first_name": "Lena", "last_name": "Probe", "birth_date": date(2015, 5, 14), "scout_name": ""},
            "e" * 20)

    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


@pytest.mark.rechtematrix("VP-11", "VP-13")
def test_ev2_ein_mitgeschicktes_konto_und_eine_eigene_uhrzeit_werden_ignoriert(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)
    other = org.walhall_leitung

    before = timezone.now()
    post_add(client, org.falken, creation_key, consent="an", consent_by=other.pk, consent_by_id=other.pk,
             consent_at="2020-01-01T12:00", user=other.key)

    by, at = confirmation(lena_now())
    assert by == org.falken_leitung.pk
    assert at >= before


@pytest.mark.rechtematrix("VP-12")
def test_ev3_niemand_sieht_die_bestaetigung_im_tool(org):
    add(org.falken_leitung, org.falken, consent="an")
    entry = lena_now()
    at = timezone.localtime(confirmation(entry)[1])
    hidden_words = ("zugestimmt", "Einwilligung", at.strftime("%H:%M"), at.strftime("%d.%m.%Y"))

    for user in (org.falken_leitung, org.walhall_leitung, org.falke, org.max):
        client = client_for(user)
        addresses = ["/", "/profil/", "/organisation/", unit_address(org.falken), edit_address(org.falken, entry)]
        for address in addresses:
            response = client.get(address)
            content = _visible_text(_tree(response)) if response.status_code == 200 else ""
            source = response.content.decode()
            for word in hidden_words:
                assert word not in content and word not in source, (user.username, address, word)


@pytest.mark.rechtematrix("VP-13")
def test_ev4_beim_bearbeiten_gibt_es_keinen_regler_und_die_bestaetigung_bleibt(org):
    add(org.falken_leitung, org.falken, consent="an")
    entry = lena_now()
    kept = confirmation(entry)

    found, version = open_edit(org.walhall_leitung, org.falken, entry)
    assert field_names(found) == ["first_name", "last_name", "birth_date", "scout_name"]
    assert not _all(found, lambda e: "a-schalter-zeile" in _classes(e))
    response = save(org.walhall_leitung, org.falken, entry, version, consent="an",
                    consent_by=org.walhall_leitung.pk, consent_at="2020-01-01T12:00")

    assert response.status_code == 302
    assert confirmation(entry) == kept


# ---------- Grenzfälle ----------


def test_eg1_scheitert_die_bestaetigung_wird_auch_lena_nicht_angelegt(org, monkeypatch):
    """Person und Bestätigung werden nur zusammen gespeichert: Scheitert das Schreiben mit Bestätigung, fehlt beides."""
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)
    original = ManagedPerson.save

    def broken(self, *args, **kwargs):
        if getattr(self, "consent_at", None) is not None:
            raise DatabaseError("Bestätigung nicht gespeichert")
        original(self, *args, **kwargs)

    monkeypatch.setattr(ManagedPerson, "save", broken)
    with pytest.raises(DatabaseError):
        post_add(client, org.falken, creation_key, consent="an")

    assert not ManagedPerson.objects.filter(first_name="Lena").exists()


def test_eg2_wanda_aendert_das_geburtsdatum_und_die_bestaetigung_bleibt_fietes(org):
    add(org.falken_leitung, org.falken, consent="an")
    entry = lena_now()
    kept = confirmation(entry)

    _found, version = open_edit(org.walhall_leitung, org.falken, entry)
    save(org.walhall_leitung, org.falken, entry, version, birth_date="2015-05-15")

    assert lena_now().birth_date == date(2015, 5, 15)
    assert confirmation(entry) == kept
    assert kept[0] == org.falken_leitung.pk


def test_eg4_wird_fietes_konto_geloescht_bleiben_lena_und_der_zeitpunkt(org):
    add(org.falken_leitung, org.falken, consent="an")
    entry = lena_now()
    _by, at = confirmation(entry)

    Role.objects.filter(user=org.falken_leitung).delete()
    org.falken_leitung.delete()

    assert confirmation(entry) == (None, at)


def test_eg5_der_regler_ist_fuer_vorleseprogramme_ein_ankreuzfeld_mit_dem_satz(org):
    found, _creation_key = open_add(org.falken_leitung, org.falken)
    switch = switch_of(found)

    assert _attr(switch, "type") == "checkbox"
    # Ohne die Rolle „switch“ sagen Vorleseprogramme ihn als Ankreuzfeld an (N4).
    assert _attr(switch, "role") is None
    assert _text(by_id(found, _attr(switch, "aria-labelledby"))) == SENTENCE


def test_eg6_ein_doppelklick_legt_lena_einmal_an_mit_genau_einer_bestaetigung(org):
    client = client_for(org.falken_leitung)
    _found, creation_key = open_add(org.falken_leitung, org.falken, client=client)

    post_add(client, org.falken, creation_key, consent="an")
    first = confirmation(lena_now())
    later = timezone.now() + timedelta(minutes=5)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("access.rights.timezone.now", lambda: later)
        post_add(client, org.falken, creation_key, consent="an")

    assert ManagedPerson.objects.filter(first_name="Lena").count() == 1
    assert confirmation(lena_now()) == first


# ---------- Baustein und Zielbild ----------


@pytest.mark.bausteinkatalog
def test_der_schalter_fuer_hat_ringe_bleibt_ein_schalter(org, settings):
    """Gegenprobe zur Erweiterung: Ohne Ansage als Ankreuzfeld bleibt der Baustein wie in #95, im Katalog wie bisher."""
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = _tree(client_for(org.ohne).get("/bausteine/"))
    section = _one(_by_tag(root, "section", aria_labelledby="h-schalter"))

    roles = [_attr(field, "role") for field in _by_tag(section, "input", type="checkbox")]
    assert "switch" in roles
    # Der Katalog zeigt auch die Erweiterung aus #98 als Ankreuzfeld. Den Fehler am Feld zeigt er dort nicht,
    # weil der Katalog nur ein Feld mit Fehler hat (tests/test_gestaltung.py, Szenario 9); ihn prüft EV1 am Dialog.
    assert None in roles
    assert MISSING not in _visible_text(section)
    assert "#98" in _visible_text(section)


def test_der_eintrag_mein_profil_nennt_den_regler_als_vorbild_fuer_98():
    readme = (ROOT / "docs" / "zielbilder" / "README.md").read_text()
    section = readme.split("## Mein Profil", 1)[1].split("\n## ", 1)[0]

    assert "#98" in section
