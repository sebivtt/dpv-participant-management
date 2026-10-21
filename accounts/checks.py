"""Systemprüfung: Ohne Keycloak-Angaben startet das Tool nicht (#5).

Django führt die Prüfung bei runserver, migrate und manage.py check aus. Sie steht hier
statt als Pflichtangabe in config/settings.py, damit sich die Einstellungen für andere
Zwecke (z. B. Tests der Einstellungen) auch ohne Keycloak laden lassen.
"""

from django.conf import settings
from django.core.checks import Error, register

REQUIRED = ["KEYCLOAK_REALM_URL", "KEYCLOAK_CLIENT_ID", "KEYCLOAK_CLIENT_SECRET"]


@register()
def keycloak_settings_present(app_configs, **kwargs) -> list[Error]:
    """Meldet jede fehlende Keycloak-Angabe als Fehler, der den Start verhindert."""
    return [
        Error(
            f"Die Umgebungsvariable {name} fehlt. Lokal: Werte aus .env.example in .env übernehmen (README.md).",
            id="accounts.E001",
        )
        for name in REQUIRED
        if not getattr(settings, name)
    ]
