"""Datenmodell der Konten."""

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Konto einer Person im Tool.

    Verknüpft ist es mit genau einem Keycloak-Konto über dessen feste Kennung (`sub`), die
    allauth als SocialAccount.uid speichert, nie über Benutzername oder Mail (#5). Name
    und Mail kommen bei jedem Login neu aus Keycloak. Ein eigenes Modell statt Djangos
    Standard, weil ein späterer Wechsel aufwendig ist; vorerst ohne zusätzliche Felder.
    """
