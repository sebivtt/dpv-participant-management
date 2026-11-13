"""Befehl für den eigenen Rechner und die Testumgebung: erfundene Testdaten anlegen (#103).

Gerüst; der Inhalt folgt nach den Tests.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Leert die Datenbank bis auf die Konten und legt die erfundenen Testdaten neu an."""

    help = "Erfundene Testdaten anlegen; nur lokal und in der Testumgebung."

    def handle(self, *args, **options):
        """Gerüst: tut noch nichts."""
