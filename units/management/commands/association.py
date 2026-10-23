"""Befehl für Admins: Bünde anlegen, umbenennen, „hat Ringe“ setzen und auflisten (#88).

Beispiele:
    python manage.py association create "Pfadfinderbund Boreas"
    python manage.py association create "DPBM Mosaik" --rings
    python manage.py association rename "Pfadfinderbund Boreas" "Bund Boreas"
    python manage.py association rings "DPBM Mosaik" on
    python manage.py association list
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models.functions import Lower

from core.actors import SERVER_COMMAND
from units import texts
from units.management.common import association, federation, refuse_with_reason
from units.models import Kind, Unit


class Command(BaseCommand):
    """Pflegt die Bünde unter dem Verband; eine Seite dafür gibt es in P2 nicht (#107)."""

    help = "Bünde anlegen (create), umbenennen (rename), „hat Ringe“ setzen (rings) und auflisten (list)."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        create = actions.add_parser("create", help="Bund anlegen")
        create.add_argument("name")
        create.add_argument("--rings", action="store_true", help="„hat Ringe“ gleich einschalten")
        rename = actions.add_parser("rename", help="Bund umbenennen")
        rename.add_argument("name")
        rename.add_argument("new_name")
        rings = actions.add_parser("rings", help="„hat Ringe“ ein- oder ausschalten")
        rings.add_argument("name")
        rings.add_argument("switch", choices=["on", "off"])
        actions.add_parser("list", help="Verband und Bünde anzeigen")

    def handle(self, *args, action: str, **options):
        with refuse_with_reason():
            getattr(self, f"_{action}")(**options)

    def _create(self, name: str, rings: bool, **options):
        parent = federation()
        if parent is None:
            raise CommandError(texts.CREATE_FEDERATION_FIRST)
        unit = Unit(kind=Kind.ASSOCIATION, name=name, parent=parent, has_rings=rings)
        unit.save(by=SERVER_COMMAND)
        self.stdout.write(texts.ASSOCIATION_CREATED % {"name": unit.name})
        if rings:
            self.stdout.write(texts.RINGS_ON_AT_CREATION)

    def _rename(self, name: str, new_name: str, **options):
        unit = association(name)
        old = unit.name
        unit.name = new_name
        # Nur den Namen schreiben, damit ein gleichzeitiges Umschalten nicht verloren geht.
        unit.save(update_fields=["name"], by=SERVER_COMMAND)
        self.stdout.write(texts.ASSOCIATION_RENAMED % {"old": old, "new": unit.name})

    def _rings(self, name: str, switch: str, **options):
        unit = association(name)
        unit.has_rings = switch == "on"
        unit.save(update_fields=["has_rings"], by=SERVER_COMMAND)
        self.stdout.write((texts.RINGS_NOW_ON if unit.has_rings else texts.RINGS_NOW_OFF) % {"name": unit.name})

    def _list(self, **options):
        parent = federation()
        if parent is None:
            self.stdout.write(texts.NO_FEDERATION)
            return
        self.stdout.write(texts.LIST_FEDERATION % {"name": parent.name})
        associations = Unit.objects.filter(kind=Kind.ASSOCIATION).order_by(Lower("name"))
        if not associations:
            self.stdout.write(texts.LIST_NO_ASSOCIATIONS)
            return
        self.stdout.write(texts.LIST_ASSOCIATIONS)
        for unit in associations:
            line = texts.LIST_WITH_RINGS if unit.has_rings else texts.LIST_WITHOUT_RINGS
            self.stdout.write(line % {"name": unit.name})
