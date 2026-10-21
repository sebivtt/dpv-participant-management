"""ABSICHTLICHER VERSTOSS für den Nachweis in #4: Modell ohne Migration. Wird wieder entfernt."""

from django.db import models


class Example(models.Model):
    """Beispielmodell ohne Migration."""

    name = models.CharField(max_length=10)
