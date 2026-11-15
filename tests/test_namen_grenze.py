"""Tests für die Grenze von 50 Zeichen bei Vor- und Nachname verwalteter Personen (#330; PER-02, VP-01, VP-02).

Die Nummern verweisen auf Sebastians Szenarien vom 14.11.2026 in #330
(https://github.com/sebivtt/dpv-participant-management/issues/330#issuecomment-6876861670). Die Zahl
beim Tippen und die rote Meldung vor dem Speichern (Szenarien 5 und 6) schreibt erst das Skript; das
prüft rauchtests/test_namen_grenze.py. Personen wie in tests/test_verwaltete_personen.py: Wanda leitet
Walhall, Fiete die Sippe Falken mit Lena Probe „Kiwi“. Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import DataError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from core.management import mass_data
from core.management.commands.testdata import MANAGED
from persons import texts
from persons.models import NAME_MAX_LENGTH, ManagedPerson
from tests import test_verwaltete_personen
from tests.keycloak_fake import ERIKA, login
from tests.test_benennen import dialog_of
from tests.test_gestaltung import _attr, _by_tag, _one, _tree
from tests.test_verwaltete_personen import add, field_error, open_add, open_edit, save, value_of

pytestmark = pytest.mark.django_db

User = get_user_model()

# Die Fixtures aus tests/test_verwaltete_personen.py unter eigenem Namen, mit allem, worauf sie aufbauen.
base_org = test_verwaltete_personen.base_org
org_189 = test_verwaltete_personen.org_189
org_190 = test_verwaltete_personen.org_190
org_285 = test_verwaltete_personen.org_285
org = test_verwaltete_personen.org
lena = test_verwaltete_personen.lena

FIRST_TOO_LONG = "Der Vorname darf höchstens 50 Zeichen lang sein."
LAST_TOO_LONG = "Der Nachname darf höchstens 50 Zeichen lang sein."
TOO_LONG = {"first_name": FIRST_TOO_LONG, "last_name": LAST_TOO_LONG}

MAXIMILIANE = ("Maximiliane-Charlotte", "Müller-Lüdenscheidt von Hohenstein")
# Genau 50 Zeichen, ein langer Doppelname wie aus dem Alltag.
FIFTY = "Müller-Lüdenscheidt von Hohenstein zu Waldeck-Brau"


def test_die_grenze_ist_fuenfzig_und_steht_an_einer_stelle():
    assert len(FIFTY) == 50
    assert NAME_MAX_LENGTH == 50
    assert ManagedPerson._meta.get_field("first_name").max_length == NAME_MAX_LENGTH
    assert ManagedPerson._meta.get_field("last_name").max_length == NAME_MAX_LENGTH
    assert (texts.FIRST_NAME_TOO_LONG, texts.LAST_NAME_TOO_LONG) == (FIRST_TOO_LONG, LAST_TOO_LONG)


# ---------- Erlaubt ----------


# Szenario 1
@pytest.mark.rechtematrix("VP-01")
def test_s1_wanda_legt_maximiliane_charlotte_mueller_luedenscheidt_von_hohenstein_in_walhall_an(org):
    first, last = MAXIMILIANE

    response = add(org.walhall_leitung, org.walhall, first_name=first, last_name=last, scout_name="")

    assert response.status_code == 302
    created = ManagedPerson.objects.get(first_name=first)
    assert (created.last_name, created.unit) == (last, org.walhall)


# Szenario 2
@pytest.mark.rechtematrix("VP-01")
@pytest.mark.parametrize("value", ["V" * 50, "Ä" * 50, "🥝" * 50])
def test_s2_ein_vorname_mit_genau_fuenfzig_zeichen_wird_gespeichert(org, value):
    assert len(value) == 50

    response = add(org.falken_leitung, org.falken, first_name=value)

    assert response.status_code == 302
    assert ManagedPerson.objects.get(unit=org.falken).first_name == value


# Szenario 3
@pytest.mark.rechtematrix("VP-02")
def test_s3_fiete_bearbeitet_lena_nachname_mit_genau_fuenfzig_zeichen(org, lena):
    _found, version = open_edit(org.falken_leitung, org.falken, lena)

    response = save(org.falken_leitung, org.falken, lena, version, last_name=FIFTY)

    assert response.status_code == 302
    lena.refresh_from_db()
    assert lena.last_name == FIFTY


# ---------- Verboten ----------


# Szenario 4: am Browser vorbei, beim Anlegen und beim Bearbeiten
@pytest.mark.rechtematrix("VP-01")
@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_s4_einundfuenfzig_zeichen_am_browser_vorbei_beim_anlegen_nichts_wird_gespeichert(org, name):
    response = add(org.falken_leitung, org.falken, **{name: "X" * 51})

    assert response.status_code == 200
    assert not ManagedPerson.objects.filter(unit=org.falken).exists()


@pytest.mark.rechtematrix("VP-02")
@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_s4_einundfuenfzig_zeichen_am_browser_vorbei_beim_bearbeiten_nichts_wird_gespeichert(org, lena, name):
    _found, version = open_edit(org.falken_leitung, org.falken, lena)

    response = save(org.falken_leitung, org.falken, lena, version, **{name: "X" * 51})

    assert response.status_code == 200
    lena.refresh_from_db()
    # Auch nicht gekürzt: Lena heißt weiter Lena Probe, und der Stand ist unverändert.
    assert (lena.first_name, lena.last_name, lena.version) == ("Lena", "Probe", 1)


# Zusätzlich zur Prüfung beim Speichern: die Grenze in der Datenbank (Text von #330)
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_die_datenbank_nimmt_keine_einundfuenfzig_zeichen_an(org, lena, name):
    with pytest.raises(DataError), transaction.atomic():
        ManagedPerson.objects.filter(pk=lena.pk).update(**{name: "X" * 51})
    lena.refresh_from_db()
    assert (lena.first_name, lena.last_name) == ("Lena", "Probe")


# ---------- Grenzfälle ----------


def _field(dialog, name: str):
    return _one(_by_tag(dialog, "input", name=name))


# Szenarien 5 und 6: was der Server ausliefert, beim Anlegen
@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_s5_s6_das_feld_nennt_grenze_und_meldung_fuer_die_zahl_beim_tippen(org, lena, name):
    created, _key = open_add(org.falken_leitung, org.falken)
    edited, _version = open_edit(org.falken_leitung, org.falken, lena)

    for dialog in (created, edited):
        field = _field(dialog, name)
        assert _attr(field, "data-hoechstens") == "50"
        assert _attr(field, "data-zu-lang") == TOO_LONG[name]


@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_s5_s6_beim_anlegen_meldung_am_feld_und_die_eingabe_bleibt(org, name):
    value = "Y" * 51

    response = add(org.falken_leitung, org.falken, **{name: value})

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert field_error(found, name) == TOO_LONG[name]
    assert value_of(found, name) == value
    assert not ManagedPerson.objects.filter(unit=org.falken).exists()


@pytest.mark.parametrize("name", ["first_name", "last_name"])
def test_s5_s6_beim_bearbeiten_meldung_am_feld_und_die_eingabe_bleibt(org, lena, name):
    value = "Y" * 51
    _found, version = open_edit(org.falken_leitung, org.falken, lena)

    response = save(org.falken_leitung, org.falken, lena, version, **{name: value})

    assert response.status_code == 200
    found = dialog_of(_tree(response))
    assert field_error(found, name) == TOO_LONG[name]
    assert value_of(found, name) == value
    lena.refresh_from_db()
    assert (lena.first_name, lena.last_name) == ("Lena", "Probe")


# Szenario 7
@pytest.mark.parametrize("edge", [" ", "\t", " ", "​"])
def test_s7_fuenfzig_zeichen_mit_leerzeichen_am_rand_werden_ohne_sie_gespeichert(org, edge):
    response = add(org.falken_leitung, org.falken, first_name=f"{edge}{'V' * 50}{edge}",
                   last_name=f"{edge}{FIFTY}{edge}")

    assert response.status_code == 302
    created = ManagedPerson.objects.get(unit=org.falken)
    assert (created.first_name, created.last_name) == ("V" * 50, FIFTY)


# Szenario 8: Umstellen der Datenbank

BEFORE = [("persons", "0003_displayed_lead")]
# 80 Zeichen; das 50. ist ein Leerzeichen, das nach dem Kürzen am Ende stünde.
EIGHTY = "Maximiliane Charlotte Friederike Wilhelmine Luise Auguste Sophie Henriette Amely"


@pytest.mark.django_db(transaction=True)
def test_s8_umstellung_kuerzt_zu_lange_namen_auf_fuenfzig_und_laesst_die_anderen(org, lena):
    assert len(EIGHTY) == 80 and EIGHTY[49] == " "
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    old = executor.loader.project_state(BEFORE).apps.get_model("persons", "ManagedPerson")
    old.objects.filter(pk=lena.pk).update(first_name=EIGHTY, last_name="N" * 80)
    old.objects.filter(pk=org.paul.pk).update(last_name=FIFTY)

    executor = MigrationExecutor(connection)
    # Alle Apps wieder auf den neuesten Stand, nicht nur `persons` (wie im Test zu #214).
    executor.migrate(executor.loader.graph.leaf_nodes())

    lena.refresh_from_db()
    org.paul.refresh_from_db()
    org.ole.refresh_from_db()
    assert lena.first_name == EIGHTY[:49] == "Maximiliane Charlotte Friederike Wilhelmine Luise"
    assert lena.last_name == "N" * 50
    assert (org.paul.first_name, org.paul.last_name) == ("Paul", FIFTY)
    assert (org.ole.first_name, org.ole.last_name) == ("Ole", "Probe")


# Szenario 9: Namen aus Keycloak
def test_s9_personen_mit_konto_behalten_namen_aus_keycloak_wie_sie_sind(client, keycloak):
    keycloak.person["given_name"] = EIGHTY
    keycloak.person["family_name"] = "N" * 80

    login(client)

    erika = User.objects.get(socialaccount__uid=ERIKA["sub"])
    assert (erika.first_name, erika.last_name) == (EIGHTY, "N" * 80)


# Szenario 10: Die erfundenen Testdaten (#103) und die Massendaten des Leistungstests (#104) passen unter die
# Grenze; dass beide Befehle ohne Fehler laufen, prüfen tests/test_testdaten.py und tests/test_massendaten.py.
def test_s10_die_erfundenen_namen_passen_unter_die_grenze():
    names = [name for persons in MANAGED.values() for first, last, _born, _scout in persons for name in (first, last)]
    names += [*mass_data.FIRST_NAMES, *mass_data.LAST_NAMES]
    assert names
    assert max(len(name) for name in names) <= NAME_MAX_LENGTH
