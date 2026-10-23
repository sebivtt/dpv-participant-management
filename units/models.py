"""Datenmodell der Einheiten (#88, ORG-01). Gerüst."""

from django.db import models


class Unit(models.Model):
    """Gerüst."""

    class Kind(models.TextChoices):
        FEDERATION = "federation", "Verband"
        ASSOCIATION = "association", "Bund"
        RING = "ring", "Ring"
        TROOP = "troop", "Stamm"
        GROUP = "group", "Gruppe"

    kind = models.CharField(max_length=20, choices=Kind)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    has_rings = models.BooleanField(default=False)
