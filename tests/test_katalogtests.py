"""Schutz für das Kennzeichen der Katalogtests (#304, Szenario S6).

Ein Test, der den Bausteinkatalog aufruft, ohne das Kennzeichen ``bausteinkatalog`` zu tragen,
liefe im schnellen Lauf nicht immer mit. Die Wache in ``tests/katalogtests.py`` macht ihn rot und
nennt ihn; Tests über jede Adresse tragen stattdessen „alle Adressen“ (S7). Szenarien:
https://github.com/sebivtt/dpv-participant-management/issues/304#issuecomment-6852474128
(„Szenarien (13.11.2026, Fassung nach der Nachklärung)“). Alle Daten sind erfunden.
"""

import os
from pathlib import Path

import pytest
from django.urls import reverse

from tests import katalogtests

BASE_DIR = Path(katalogtests.__file__).resolve().parent.parent

# Ein eigener pytest-Lauf ohne Django und ohne Datenbank: Die Anfrage meldet der Test so, wie
# Django jede Anfrage meldet (Signal request_started), über den Test-Client wie über den Server
# des Rauchtests.
INNER = """
import pytest
from django.core.signals import request_started


def _anfrage(adresse):
    request_started.send(sender=None, environ={"PATH_INFO": adresse})


@pytest.mark.bausteinkatalog
def test_katalog_mit_kennzeichen():
    _anfrage("/bausteine/")


def test_katalog_ohne_kennzeichen_erfunden():
    _anfrage("/bausteine/")


def test_andere_seite_ohne_kennzeichen():
    _anfrage("/profil/")


def test_danach_ohne_anfrage():
    pass
"""


def _inner_run(pytester, monkeypatch):
    pytester.makepyfile(test_innen=INNER)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(BASE_DIR), os.environ.get("PYTHONPATH")])))
    return pytester.runpytest_subprocess("-p", "no:django", "-p", "no:cacheprovider", "-p", "tests.katalogtests", "-rE")


def test_s6_aufruf_des_katalogs_ohne_kennzeichen_ist_rot_und_nennt_den_test(pytester, monkeypatch):
    result = _inner_run(pytester, monkeypatch)

    # Nur der Test ohne Kennzeichen, der den Katalog aufruft, ist rot; die Anfrage zählt nicht für
    # den nächsten Test.
    result.assert_outcomes(passed=4, errors=1)
    output = result.stdout.str()
    assert "ERROR test_innen.py::test_katalog_ohne_kennzeichen_erfunden" in output
    # Die volle Meldung (die Zeile darüber kürzt pytest auf die Breite des Fensters).
    assert "test_innen.py::test_katalog_ohne_kennzeichen_erfunden ruft den Bausteinkatalog" in output
    assert "@pytest.mark.bausteinkatalog" in output
    for name in ["test_katalog_mit_kennzeichen", "test_andere_seite_ohne_kennzeichen", "test_danach_ohne_anfrage"]:
        assert f"ERROR test_innen.py::{name}" not in output, name


INNER_ALLE_ADRESSEN = """
import pytest
from django.core.signals import request_started


@pytest.mark.alle_adressen
@pytest.mark.parametrize("adresse", ["/", "/profil/", "/bausteine/"])
def test_jede_adresse_erfunden(adresse):
    request_started.send(sender=None, environ={"PATH_INFO": adresse})
"""


def test_s7_ein_test_ueber_alle_adressen_mit_eigenem_kennzeichen_ist_nicht_rot(pytester, monkeypatch):
    pytester.makepyfile(test_innen=INNER_ALLE_ADRESSEN)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(filter(None, [str(BASE_DIR), os.environ.get("PYTHONPATH")])))
    result = pytester.runpytest_subprocess("-p", "no:django", "-p", "no:cacheprovider", "-p", "tests.katalogtests", "-rE", "-W", "error::pytest.PytestUnknownMarkWarning")

    result.assert_outcomes(passed=3)


def test_die_wache_kennt_die_adresse_des_katalogs():
    # Zieht der Katalog um, bliebe die Wache sonst still.
    assert reverse("building_blocks") == katalogtests.CATALOG


@pytest.mark.bausteinkatalog
@pytest.mark.django_db
def test_die_wache_erkennt_den_aufruf_ueber_den_test_client(client):
    client.get("/")
    assert not katalogtests.catalog_requested()

    client.get("/bausteine/")
    assert katalogtests.catalog_requested()
