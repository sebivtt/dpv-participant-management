"""Grundbausteine des Tools, die zu keinem Fachbereich gehören."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Anmeldung der App „core“ bei Django."""

    name = "core"

    def ready(self) -> None:
        """Schaltet beim Start das Fehlerprotokoll ein.

        Fehlt das, kommt kein Fehler mit Nummer ins Log; das bemerken die Tests in
        tests/test_fehlerprotokoll.py.
        """
        from core.errors import connect_error_log

        connect_error_log()
