"""Datenmodell der Veranstaltungen (#100, TEAM-01, Probe in P2)."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Trim

from access.keys import KEY_LENGTH, key_field, new_key

# Höchstens 100 Zeichen für den Namen, nach dem Entfernen der Leerzeichen am Rand (#100).
NAME_MAX_LENGTH = 100
# Die Angaben, die „Veranstaltung erstellen“ anlegt und „… bearbeiten“ ändert; mehr gibt es in P2 nicht (#100).
EDITABLE_FIELDS = ("name", "start", "end")


class Event(models.Model):
    """Eine Veranstaltung mit Name, Beginn und Ende und ihrer Veranstaltungsleitung (TEAM-01).

    Wer sie anlegt, ist ihre Veranstaltungsleitung; die Leitung kommt immer aus der Anmeldung, nie aus
    einem Formular (#100, VV3). In P2 hat jede Veranstaltung genau eine Leitung; weitere kommen mit
    TEAM-01 in P3, deshalb kann die Datenbank schon mehrere halten. Beginn und Ende sind Tage ohne
    Uhrzeit, das Ende liegt nicht vor dem Beginn; beides prüft auch die Datenbank. Gelesen und
    geändert wird eine Veranstaltung nur über die zentrale Rechteprüfung (`access/rights.py`).
    """

    # Zufällige Kennung für Adressen (#64).
    key = key_field()
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    start = models.DateField()
    end = models.DateField()
    # Die Veranstaltungsleitung (TEAM-01). Setzt nur `Rights.create_event()` aus der Anmeldung.
    leads = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="led_events", editable=False)
    # Kennung des Formulars „Veranstaltung erstellen“: Ein zweites Abschicken desselben Formulars, etwa
    # ein Doppelklick, legt die Veranstaltung nicht ein zweites Mal an (VG8, wie MG7 aus #117).
    creation_key = models.CharField(max_length=KEY_LENGTH, unique=True, default=new_key, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(name="") & Q(name=Trim("name")), name="event_name_trimmed_not_empty"),
            models.CheckConstraint(condition=Q(end__gte=F("start")), name="event_end_not_before_start"),
        ]

    def __str__(self) -> str:
        return self.name
