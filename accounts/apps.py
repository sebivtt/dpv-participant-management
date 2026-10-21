"""Konten und Login über den Keycloak des DPV (#5)."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Anmeldung der App „accounts“ bei Django."""

    name = "accounts"

    def ready(self) -> None:
        """Meldet die Prüfung der Keycloak-Einstellungen und die Schritte nach dem Login an.

        Fehlt das, startet das Tool ohne Keycloak-Angaben und merkt sich nach dem Login
        nichts fürs Abmelden; das bemerken die Tests in tests/test_login.py.
        """
        from accounts import checks, signals  # noqa: F401 -- meldet Prüfung und Signale an
