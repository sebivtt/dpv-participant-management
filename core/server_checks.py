"""Startprüfung: Auf einem Server startet das Tool nicht mit unsicheren Einstellungen (#325).

Gerüst; die Regeln folgen.
"""

from collections.abc import Mapping

from django.core.checks import Error, register

# Einstellungen mit geheimem Wert.
SECRET_SETTINGS = ("DJANGO_SECRET_KEY", "POSTGRES_PASSWORD", "KEYCLOAK_CLIENT_SECRET")

# Öffentlich bekannte Beispielwerte aus .env.example und testumgebung/.env.example.
EXAMPLE_VALUES: frozenset[str] = frozenset()


def is_server(env: Mapping[str, str]) -> bool:
    """Läuft das Tool auf einem Server?"""
    return False


def problems(env: Mapping[str, str]) -> list[tuple[str, str]]:
    """Unsichere Einstellungen als Paare aus Kennung und Zeile fürs Log."""
    return []


@register()
def server_settings_safe(app_configs, **kwargs) -> list[Error]:
    """Meldet jede unsichere Einstellung auf einem Server als Fehler, der den Start verhindert."""
    return []
