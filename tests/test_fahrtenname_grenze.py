"""Tests für die Grenze von 30 Zeichen beim Fahrtennamen (#214; EP-03, EP-04).

Die Nummern verweisen auf Sebastians Szenarien vom 30.10.2026 in #214 („Szenarien (30.10.2026)“).
Umbruch in Seitenleiste und Menü (Szenarien 5, 6 und 8) zeigt nur ein echter Browser; das prüft
rauchtests/test_fahrtenname_umbruch.py. Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import DataError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from accounts.models import SCOUT_NAME_MAX_LENGTH
from tests import test_fahrtenname
from tests.test_fahrtenname import (
    NOT_GIVEN,
    SAVED,
    TOO_LONG,
    client_for,
    field,
    greeting,
    notices,
    profile,
    save,
    set_stored,
    stored,
)
from tests.test_gestaltung import _attr, _by_tag, _one, _tree, _visible_text
from tests.test_mein_profil import text

pytestmark = pytest.mark.django_db

User = get_user_model()

WANDERFALKE = "Wanderfalke vom Hohen Meißner"
STURMVOGEL = "Sturmvogelwanderfalkenflugkind"


@pytest.fixture
def org():
    """Dieselben Personen wie in tests/test_fahrtenname.py."""
    return test_fahrtenname.org.__wrapped__()


def test_die_grenze_ist_dreissig_und_steht_an_einer_stelle():
    assert SCOUT_NAME_MAX_LENGTH == 30
    assert User._meta.get_field("scout_name").max_length == SCOUT_NAME_MAX_LENGTH
    assert TOO_LONG == "Dein Fahrtenname darf höchstens 30 Zeichen lang sein."


# Szenario 1: 29 Zeichen


def test_erika_speichert_wanderfalke_vom_hohen_meissner(org):
    assert len(WANDERFALKE) == 29
    client = client_for(org.erika)

    response = save(org.erika, WANDERFALKE, client=client)

    assert response.status_code == 302
    assert stored(org.erika) == WANDERFALKE
    assert notices(profile(org.erika, client=client), "ist-erfolg") == [SAVED]


# Szenario 2: genau 30 Zeichen


@pytest.mark.parametrize("value", [STURMVOGEL, "Ä" * 30, "🥝" * 30])
def test_genau_dreissig_zeichen_werden_gespeichert(org, value):
    assert len(value) == 30

    save(org.erika, f" {value} ")

    assert stored(org.erika) == value


# Szenario 3: am Browser vorbei, 40 Zeichen


def test_vierzig_zeichen_am_browser_vorbei_nichts_wird_gespeichert_auch_nicht_gekuerzt(org):
    set_stored(org.erika, "Kiwi")

    response = save(org.erika, "K" * 40, htmx=True)

    assert response.status_code == 200
    assert stored(org.erika) == "Kiwi"
    assert not User.objects.filter(scout_name__startswith="KKK").exists()


# Szenario 4: 31 Zeichen


@pytest.mark.parametrize("value", ["K" * 31, "🥝" * 31, STURMVOGEL + "s"])
def test_einunddreissig_zeichen_fehler_am_feld_und_die_eingabe_bleibt(org, value):
    set_stored(org.erika, "Kiwi")

    response = save(org.erika, value)

    assert response.status_code == 200
    root = _tree(response)
    assert stored(org.erika) == "Kiwi"
    input_ = field(root)
    assert _attr(input_, "value") == value
    assert _attr(input_, "aria-invalid") == "true"
    error = _one(_by_tag(root, "div", id=_attr(input_, "aria-describedby").split()[0]))
    assert _visible_text(error) == TOO_LONG


# Zusätzlich zur Prüfung beim Speichern: die Grenze in der Datenbank (Klärung, Frage 6)


@pytest.mark.django_db(transaction=True)
def test_die_datenbank_nimmt_keine_einunddreissig_zeichen_an(org):
    with pytest.raises(DataError), transaction.atomic():
        User.objects.filter(pk=org.erika.pk).update(scout_name="K" * 31)
    assert stored(org.erika) == ""


# Szenario 7: Umstellen der Datenbank

BEFORE = [("accounts", "0004_account_search")]


@pytest.mark.django_db(transaction=True)
def test_umstellung_leert_zu_lange_fahrtennamen_und_laesst_die_anderen(org):
    executor = MigrationExecutor(connection)
    executor.migrate(BEFORE)
    old_user = executor.loader.project_state(BEFORE).apps.get_model("accounts", "User")
    long_name = "Kleiner Bär vom Hohen Meißner am Edersee 1" + "abc"
    assert len(long_name) == 45
    old_user.objects.filter(pk=org.erika.pk).update(scout_name=long_name)
    old_user.objects.filter(pk=org.lead.pk).update(scout_name=STURMVOGEL)
    old_user.objects.filter(pk=org.max.pk).update(scout_name="Kiwi")

    executor = MigrationExecutor(connection)
    # Alle Apps wieder auf den neuesten Stand, nicht nur `accounts` (unabhängige Prüfung).
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert stored(org.erika) == ""
    assert stored(org.lead) == STURMVOGEL
    assert stored(org.max) == "Kiwi"
    root = profile(org.erika)
    assert NOT_GIVEN in text(root)
    assert greeting(org.erika) == "Hallo Erika!"
