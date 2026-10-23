"""Befehl auf dem Server: eine Person zum Admin ernennen oder das Admin-Recht entfernen (#89). Gerüst."""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Ernennt Admins (grant) oder entfernt das Admin-Recht (revoke)."""

    help = "Admin ernennen (grant BENUTZERNAME) oder entfernen (revoke BENUTZERNAME)."

    def add_arguments(self, parser):
        actions = parser.add_subparsers(dest="action", required=True)
        actions.add_parser("grant", help="Admin ernennen").add_argument("username")
        actions.add_parser("revoke", help="Admin-Recht entfernen").add_argument("username")

    def handle(self, *args, action: str, username: str, **options):
        pass
