"""Datenmodell der Kreise (#381, GRP-01, GRP-02): der Kreis, seine Mitglieder und die offenen Einladungen.

Wer einen Kreis sieht und was dort geht, regelt allein die zentrale Rechteprüfung (`access/rights.py`, Abschnitt
„Kreise“, und `docs/rechtematrix.md`, Abschnitt „Kreise“). Hier stehen nur die Regeln, die die Datenbank selbst
durchsetzt: Name und Beschreibung ohne Leerzeichen am Rand und nicht zu lang, eine Person höchstens einmal Mitglied
und höchstens einmal eingeladen je Kreis, und ein Formular legt höchstens einen Kreis an.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Length, Trim
from django.db.models.lookups import LessThanOrEqual
from django.utils import timezone

from access.keys import KEY_LENGTH, key_field, new_key

# Höchstens 60 Zeichen für den Namen und 500 für die Beschreibung, nach dem Entfernen der Leerzeichen am Rand (#141 F11).
NAME_MAX_LENGTH = 60
DESCRIPTION_MAX_LENGTH = 500


class Circle(models.Model):
    """Ein privater Kreis mit Name und freiwilliger Beschreibung (GRP-01, GRP-02).

    Der Name darf mehrfach vorkommen (#141 F11). `creation_key` ist die Kennung des Formulars „Kreis anlegen“:
    Wird dasselbe Formular zweimal abgeschickt, auch gleichzeitig, bleibt es bei einem Kreis (Szenario AG3).
    """

    key = key_field()
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    description = models.TextField(max_length=DESCRIPTION_MAX_LENGTH, blank=True, default="")
    creation_key = models.CharField(max_length=KEY_LENGTH, unique=True, default=new_key, editable=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(name="") & Q(name=Trim("name")), name="circle_name_trimmed_not_empty"),
            models.CheckConstraint(condition=Q(description=Trim("description")), name="circle_description_trimmed"),
            models.CheckConstraint(condition=LessThanOrEqual(Length("name"), NAME_MAX_LENGTH),
                                   name="circle_name_max_length"),
            models.CheckConstraint(condition=LessThanOrEqual(Length("description"), DESCRIPTION_MAX_LENGTH),
                                   name="circle_description_max_length"),
        ]

    def __str__(self) -> str:
        return self.name


class CircleMember(models.Model):
    """Eine Person im Kreis; mit `manages` verwaltet sie ihn (GRP-01).

    Verwaltende sind keine Rolle und keine Zuordnung (BER-03, #136). Mitglied wird man nur beim Anlegen oder mit
    „Annehmen“ einer Einladung (GRP-02). Die Kennung brauchen erst die Handlungen aus Teil B (#382).
    """

    key = key_field()
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_memberships")
    manages = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["circle", "user"], name="circle_member_once"),
        ]


class CircleInvitation(models.Model):
    """Eine offene Einladung in einen Kreis (GRP-02): wer eingeladen ist und wer einlädt.

    Sie läuft nicht ab (#141 F1). Mit „Annehmen“ wird sie zur Mitgliedschaft, mit „Ablehnen“ oder „Zurücknehmen“
    verschwindet sie; danach lässt sich die Person erneut einladen (#141 F12).
    """

    key = key_field()
    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name="invitations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="circle_invitations")
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    invited_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["circle", "user"], name="circle_invitation_once"),
        ]
