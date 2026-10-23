"""Befehl für Admins: den Verband anlegen oder umbenennen (#88).

Beispiele:
    python manage.py federation create "DPV"
    python manage.py federation rename "Deutscher Pfadfinderverband"
"""

from django.core.management.base import BaseCommand, CommandError

from core.actors import SERVER_COMMAND
from units import texts
from units.management.common import federation, refuse_with_reason
from units.models import Kind, Unit


class Command(BaseCommand):
    """Legt den einen Verband an oder benennt ihn um; eine Seite dafür gibt es in P2 nicht."""

    help = "Legt den Verband an (create NAME) oder benennt ihn um (rename NEUER_NAME)."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        actions.add_parser("create", help="Verband anlegen").add_argument("name")
        actions.add_parser("rename", help="Verband umbenennen").add_argument("name")

    def handle(self, *args, action: str, name: str, **options):
        with refuse_with_reason():
            if action == "create":
                unit = Unit(kind=Kind.FEDERATION, name=name)
                unit.save(by=SERVER_COMMAND)
                self.stdout.write(texts.FEDERATION_CREATED % {"name": unit.name})
                return
            unit = federation()
            if unit is None:
                raise CommandError(texts.CREATE_FEDERATION_FIRST)
            unit.name = name
            unit.save(update_fields=["name"], by=SERVER_COMMAND)
            self.stdout.write(texts.FEDERATION_RENAMED % {"name": unit.name})
