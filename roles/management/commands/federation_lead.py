"""Befehl auf dem Server: eine Person als Verbandsleitung benennen oder entfernen (#94, ROL-03).

So benennt ein Admin die erste Verbandsleitung; weitere benennt die Verbandsleitung selbst auf der
Seite „Verband“. Der Befehl geht jederzeit, auch wenn es schon Verbandsleitungen gibt, als
Notnagel (Klärung von #94 vom 22.10.2026, Frage 1). Ins Protokoll der Rollenänderungen kommt
„Befehl auf dem Server“ als Urheber (#91).

Beispiele:
    python manage.py federation_lead grant vera.verband
    python manage.py federation_lead revoke vera.verband
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from roles import texts
from roles.models import SERVER_COMMAND, Role
from units import texts as unit_texts
from units.management.common import federation, refuse_with_reason


class Command(BaseCommand):
    """Benennt eine Verbandsleitung (grant) oder entfernt sie (revoke), über den Benutzernamen.

    Ein Konto gibt es nur, wenn sich die Person schon einmal angemeldet hat. Die letzte
    Verbandsleitung zu entfernen wird nicht abgelehnt: Mit Zugang zum Server lässt sich jederzeit
    eine neue benennen.
    """

    help = "Verbandsleitung benennen (grant BENUTZERNAME) oder entfernen (revoke BENUTZERNAME)."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        actions.add_parser("grant", help="Verbandsleitung benennen").add_argument("username")
        actions.add_parser("revoke", help="Verbandsleitung entfernen").add_argument("username")

    def handle(self, *args, action: str, username: str, **options):
        user = get_user_model().objects.filter(username=username.strip()).first()
        if user is None:
            raise CommandError(texts.UNKNOWN_USERNAME)
        unit = federation()
        if unit is None:
            raise CommandError(unit_texts.CREATE_FEDERATION_FIRST)
        names = {"username": user.username}
        role = Role.objects.filter(user=user, kind=Role.Kind.FEDERATION_LEAD).first()
        with refuse_with_reason():
            if action == "grant":
                if role:
                    self.stdout.write(texts.FEDERATION_LEAD_ALREADY % names)
                    return
                Role(user=user, kind=Role.Kind.FEDERATION_LEAD, unit=unit).save(by=SERVER_COMMAND)
                self.stdout.write(texts.FEDERATION_LEAD_GRANTED % names)
                return
            if role is None:
                raise CommandError(texts.NOT_FEDERATION_LEAD % names)
            role.delete(by=SERVER_COMMAND)
            self.stdout.write(texts.FEDERATION_LEAD_REVOKED % names)
