"""Baustein für den Abfragegrenzen-Test (CONTRIBUTING.md, Abschnitt 5)."""

from collections.abc import Callable

from django.db import connection
from django.test.utils import CaptureQueriesContext


def assert_queries_do_not_grow(create_entry: Callable[[int], object], load_list: Callable[[], object]) -> None:
    """Prüft, dass eine Liste bei 10 Einträgen nicht mehr Datenbankabfragen auslöst als bei einem.

    create_entry legt einen Eintrag an und bekommt eine laufende Nummer, damit Namen eindeutig
    bleiben. load_list muss die Liste vollständig laden, z. B. eine Seite aufrufen oder eine
    Abfrage in eine Liste umwandeln; eine nur vorbereitete Abfrage fragt die Datenbank nie.
    """
    create_entry(1)
    # Ein Aufruf vorab, ohne zu zählen: Einmalige Abfragen beim allerersten Aufruf (z. B. ein
    # Zwischenspeicher wird gefüllt) würden sonst ein Wachstum der Liste verdecken.
    load_list()
    with CaptureQueriesContext(connection) as with_one:
        load_list()

    for number in range(2, 11):
        create_entry(number)
    with CaptureQueriesContext(connection) as with_ten:
        load_list()

    if len(with_ten) > len(with_one):
        raise AssertionError(
            "Die Liste fragt die Datenbank pro Eintrag neu (N+1-Muster): "
            f"1 Eintrag: {len(with_one)} Abfragen, 10 Einträge: {len(with_ten)} Abfragen. "
            "Zugehörige Daten mit select_related oder prefetch_related vorab laden."
        )
