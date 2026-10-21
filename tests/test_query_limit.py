"""Tests für den Abfragegrenzen-Baustein, am Beispiel einer Liste von Konten mit ihren Gruppen."""

import pytest
from django.contrib.auth.models import Group, User

from tests.query_limit import assert_queries_do_not_grow


def _create_account_with_group(number: int) -> None:
    account = User.objects.create(username=f"testkonto{number}")
    account.groups.add(Group.objects.create(name=f"Testgruppe {number}"))


def _list_with_query_per_entry() -> list[list[str]]:
    # Absichtlich falsch: Für jedes Konto wird die Datenbank erneut nach den Gruppen gefragt.
    return [[g.name for g in account.groups.all()] for account in User.objects.all()]


def _list_prefetched() -> list[list[str]]:
    return [[g.name for g in account.groups.all()] for account in User.objects.prefetch_related("groups")]


@pytest.mark.django_db
def test_liste_mit_abfrage_pro_eintrag_wird_gemeldet():
    with pytest.raises(AssertionError, match="1 Eintrag: 2 Abfragen, 10 Einträge: 11 Abfragen"):
        assert_queries_do_not_grow(_create_account_with_group, _list_with_query_per_entry)


@pytest.mark.django_db
def test_vorab_geladene_liste_besteht():
    assert_queries_do_not_grow(_create_account_with_group, _list_prefetched)
