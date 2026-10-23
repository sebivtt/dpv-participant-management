"""Befehl auf dem Server: eine Person zum Admin ernennen oder das Admin-Recht entfernen (#89).

Bis ADM-01 (P6) wird jeder Admin so ernannt, nie über das Tool, über Keycloak oder als erstes
angemeldetes Konto. Ins Protokoll der Rollenänderungen kommt „Befehl auf dem Server“ als
Urheber (#91); wer den Befehl eingetippt hat, weiß das Tool nicht.

Beispiele:
    python manage.py admin grant erika.testfrau
    python manage.py admin revoke erika.testfrau
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from roles import texts
from roles.models import SERVER_COMMAND, Role
from units.management.common import refuse_with_reason


class Command(BaseCommand):
    """Ernennt Admins (grant) oder entfernt das Admin-Recht (revoke).

    Gefunden wird das Konto über den Benutzernamen aus Keycloak. Konten entstehen nur beim
    ersten Login; ein Konto gibt es also nur, wenn sich die Person schon einmal angemeldet hat.
    Den letzten Admin zu entfernen wird nicht abgelehnt: Mit Zugang zum Server lässt sich
    jederzeit ein neuer ernennen.
    """

    help = "Admin ernennen (grant BENUTZERNAME) oder entfernen (revoke BENUTZERNAME)."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        actions.add_parser("grant", help="Admin ernennen").add_argument("username")
        actions.add_parser("revoke", help="Admin-Recht entfernen").add_argument("username")

    def handle(self, *args, action: str, username: str, **options):
        user = get_user_model().objects.filter(username=username.strip()).first()
        if user is None:
            raise CommandError(texts.UNKNOWN_USERNAME)
        names = {"username": user.username}
        admin = Role.objects.filter(user=user, kind=Role.Kind.ADMIN).first()
        with refuse_with_reason():
            if action == "grant":
                if admin:
                    self.stdout.write(texts.ADMIN_ALREADY % names)
                    return
                Role(user=user, kind=Role.Kind.ADMIN).save(by=SERVER_COMMAND)
                self.stdout.write(texts.ADMIN_GRANTED % names)
                return
            if admin is None:
                raise CommandError(texts.NOT_ADMIN % names)
            admin.delete(by=SERVER_COMMAND)
            self.stdout.write(texts.ADMIN_REVOKED % names)
