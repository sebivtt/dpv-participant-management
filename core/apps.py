"""Grundbausteine ohne eigenen Fachbereich, gemeinsame Gestaltung und alle Seiten außer Login und Abmelden.

Was wohin gehört, steht in docs/aufbau.md (#282).
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Anmeldung der App „core“ bei Django."""

    name = "core"

    def ready(self) -> None:
        """Schaltet beim Start das Fehlerprotokoll ein und meldet die Startprüfung für Server an.

        Fehlt das, kommt kein Fehler mit Nummer ins Log oder ein Server startet mit unsicheren
        Einstellungen; das bemerken die Tests in tests/test_fehlerprotokoll.py und
        tests/test_startpruefung.py.
        """
        from core import server_checks  # noqa: F401 -- meldet die Startprüfung an (#325)
        from core.errors import connect_error_log

        connect_error_log()
