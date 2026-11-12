"""Befehl auf dem Server: eine falsch angelegte, leere Organisation im Notfall löschen (#92, Entscheidung W5).

Im Tool lässt sich keine Organisation löschen (EH-21); das kommt mit ORG-07 (#108). Bis dahin
löscht ein Admin mit Zugang zum Server so eine Organisation, die versehentlich angelegt wurde.
Gefunden wird sie über ihre Kennung, die in der Adresse ihrer Seite steht: Admins öffnen jede
Seite einer Organisation, dort steht nur der Kopf (#92, S1). Ins Protokoll der Admin-Zugriffe
kommt „Befehl auf dem Server“ als Urheber; wer den Befehl eingetippt hat, weiß das Tool nicht.

Beispiel:
    python manage.py emergency_delete KENNUNG
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError

from access.keys import is_key
from core.actors import SERVER_COMMAND
from roles.models import AdminAccess
from units import texts
from units.models import Kind, Unit


class Command(BaseCommand):
    """Löscht eine leere Organisation über ihre Kennung und schreibt einen Eintrag ins Protokoll der Admin-Zugriffe.

    Abgelehnt wird der Verband und jede Organisation mit Organisationen darunter, mit Rollen oder
    Mitgliedschaften oder mit verwalteten Personen (SG4). Das prüft der Löschschutz der Datenbank
    selbst (`PROTECT`, #88): Hängt noch etwas an der Organisation, scheitert das Löschen, und der
    Befehl liest dafür keine Personendaten. Gesperrt sind die Organisation und der Bund, damit
    niemand gleichzeitig etwas darunter anlegt oder jemanden aufnimmt; Löschen und Eintrag gelingen
    nur zusammen.
    """

    help = "Leere Organisation im Notfall löschen (KENNUNG aus der Adresse ihrer Seite)."

    def add_arguments(self, parser):
        parser.add_argument("key")

    def handle(self, *args, key: str, **options):
        key = key.strip()
        if not is_key(key) or not Unit.objects.filter(key=key).exists():
            raise CommandError(texts.EMERGENCY_UNKNOWN)
        with transaction.atomic():
            unit = Unit.objects.select_related("parent").get(key=key)
            bund = unit.association_id or (unit.parent.association_id if unit.kind == Kind.GROUP else None)
            locked = [entry for entry in (bund, unit.pk) if entry is not None]
            list(Unit.objects.select_for_update().filter(pk__in=locked).order_by("pk").values_list("pk"))
            if unit.kind == Kind.FEDERATION:
                raise CommandError(texts.EMERGENCY_FEDERATION)
            AdminAccess.record(SERVER_COMMAND, AdminAccess.Action.DELETED, unit)
            try:
                with transaction.atomic():
                    unit.delete()
            except ProtectedError as error:
                # Der Eintrag oben fällt mit der äußeren Transaktion weg.
                raise CommandError(texts.EMERGENCY_NOT_EMPTY % {"unit": unit.name}) from error
        self.stdout.write(texts.EMERGENCY_DELETED % {"unit": unit.name})
