"""ABSICHTLICHE VERSTÖSSE für den Nachweis in #4. Wird im nächsten Commit wieder entfernt."""

import pytest
from django.contrib.auth.models import Group, User

from tests.query_limit import assert_queries_do_not_grow


def test_absichtlich_rot():
    assert 1 + 1 == 3


@pytest.mark.xfail(reason="bekannter Fehler, inzwischen behoben")
def test_absichtlich_unerwartet_bestanden():
    assert True


@pytest.mark.django_db
def test_absichtlich_liste_mit_abfrage_pro_eintrag():
    def create(number: int) -> None:
        User.objects.create(username=f"verstoss{number}").groups.add(Group.objects.create(name=f"G{number}"))

    def load() -> None:
        [list(account.groups.all()) for account in User.objects.all()]

    assert_queries_do_not_grow(create, load)
