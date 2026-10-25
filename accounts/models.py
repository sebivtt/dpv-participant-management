"""Datenmodell der Konten."""

from django.contrib.auth.models import AbstractUser

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
