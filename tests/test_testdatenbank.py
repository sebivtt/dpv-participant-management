"""Jede Arbeitskopie hat ihre eigene Test-Datenbank (#184).

Vorher hieß sie in allen Arbeitskopien test_dpv. Liefen zwei Prüfläufe gleichzeitig, brach
einer mit „database already exists“ ab, oder der zweite löschte die Datenbank des ersten.
"""

import os
from pathlib import Path

import pytest
from django.conf import settings
from django.db import connection

from config.settings import BASE_DIR, own_test_database


def test_zwei_arbeitskopien_bekommen_verschiedene_test_datenbanken():
    erste = own_test_database("dpv", Path("/Users/beispiel/dpv-participant-management"))
    zweite = own_test_database("dpv", Path("/Users/beispiel/dpv-participant-management/.claude/worktrees/beispiel"))

    assert erste != zweite


def test_dieselbe_arbeitskopie_bekommt_immer_denselben_namen():
    # So bleibt je Arbeitskopie höchstens eine Test-Datenbank übrig.
    ordner = Path("/Users/beispiel/dpv-participant-management")

    assert own_test_database("dpv", ordner) == own_test_database("dpv", ordner)


def test_name_ist_als_test_datenbank_erkennbar_und_nicht_zu_lang():
    name = own_test_database("dpv", Path("/Users/beispiel/" + "sehr-langer-ordner/" * 20))

    # Am Anfang test_dpv_, damit die Anleitung zum Aufräumen sie findet (README.md, „Übrige Test-Datenbanken entfernen“).
    assert name.startswith("test_dpv_")
    # PostgreSQL kürzt Namen über 63 Zeichen still; dann könnten zwei Arbeitskopien wieder zusammenfallen.
    assert len(name) <= 63
    assert name != "test_dpv"


@pytest.mark.django_db
def test_die_tests_laufen_in_der_test_datenbank_dieser_arbeitskopie():
    eigene = own_test_database(os.environ["POSTGRES_DB"], BASE_DIR)

    assert settings.DATABASES["default"]["TEST"]["NAME"] == eigene
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        assert cursor.fetchone()[0] == eigene
