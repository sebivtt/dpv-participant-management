"""Datenmodell der Konten."""

from django.contrib.auth.models import AbstractUser
from django.db import models

from access.keys import key_field


class User(AbstractUser):
    """Konto einer Person im Tool.

    Verknüpft ist es mit genau einem Keycloak-Konto über dessen feste Kennung (`sub`), die
    allauth als SocialAccount.uid speichert, nie über Benutzername oder Mail (#5). Name
    und Mail kommen bei jedem Login neu aus Keycloak. Ein eigenes Modell statt Djangos
    Standard, weil ein späterer Wechsel aufwendig ist. Zusätzlich hat es nur die zufällige
    Kennung für Adressen (#64); sie entsteht beim ersten Login mit dem Konto.
    """

    key = key_field()
    scout_name = models.CharField(max_length=50, blank=True, default="")

    @property
    def short_name(self) -> str:
        """Der Name in Begrüßung und Profilkreis, leer, wenn er fehlt (#77).

        Beide fragen nur hier, damit #111 an dieser einen Stelle den Fahrtennamen
        vorschalten kann. Bis dahin ist es der Vorname; Leerzeichen am Rand entfernt schon
        der Login (`accounts/adapter.py`), ein Name nur aus Leerzeichen ist hier also leer.
        """
        return self.first_name


def display_name(first_name: str, last_name: str, scout_name: str) -> str:
    return ""
