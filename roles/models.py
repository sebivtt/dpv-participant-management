"""Datenmodell der Rollen (#89, ROL-01). Gerüst; die Regeln folgen."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy


class RoleKind(models.TextChoices):
    """Die Rollen aus ROL-01."""

    MEMBER = "member", gettext_lazy("Mitglied")
    GROUP_LEAD = "group_lead", gettext_lazy("Gruppenleitung")
    TROOP_LEAD = "troop_lead", gettext_lazy("Stammesleitung")
    RING_LEAD = "ring_lead", gettext_lazy("Ringleitung")
    ASSOCIATION_LEAD = "association_lead", gettext_lazy("Bundesleitung")
    FEDERATION_LEAD = "federation_lead", gettext_lazy("Verbandsleitung")
    EVENT_TEAM = "event_team", gettext_lazy("DPV-Veranstaltungsteam")
    ADMIN = "admin", gettext_lazy("Admin")


class Role(models.Model):
    """Eine Rolle einer Person mit Account in einer Einheit."""

    Kind = RoleKind

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="roles")
    kind = models.CharField(max_length=20, choices=RoleKind)
    unit = models.ForeignKey("units.Unit", null=True, blank=True, on_delete=models.PROTECT, related_name="roles")
