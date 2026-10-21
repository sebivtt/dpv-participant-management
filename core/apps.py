"""Grundbausteine des Tools, die zu keinem Fachbereich gehören."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Anmeldung der App „core“ bei Django."""

    name = "core"
