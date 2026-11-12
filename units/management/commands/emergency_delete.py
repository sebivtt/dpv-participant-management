"""Befehl auf dem Server: eine falsch angelegte, leere Organisation im Notfall löschen (#92, Entscheidung W5); Gerüst.

Beispiel:
    python manage.py emergency_delete KENNUNG
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Löscht eine leere Organisation über ihre Kennung; Gerüst."""

    help = "Leere Organisation im Notfall löschen (KENNUNG aus der Adresse ihrer Seite)."

    def add_arguments(self, parser):
        parser.add_argument("key")

    def handle(self, *args, key: str, **options):
        raise CommandError("Noch nicht gebaut (#92).")
