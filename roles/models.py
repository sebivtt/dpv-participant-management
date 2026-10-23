"""Datenmodell der Rollen von Personen in Einheiten, Mitgliedschaft eingeschlossen (#89, ROL-01).

Jede Rolle ist eine Zeile: Person mit Account, Rolle, Einheit. Auch die Mitgliedschaft ist eine
solche Zeile, damit das Protokoll der Rollenänderungen (#91) nur eine Stelle beobachten muss und
die Datenbank „höchstens eine Mitgliedschaft“ selbst durchsetzt. Admin ist eine Zeile ohne
Einheit und bewusst nicht Djangos „Superuser“, weil der automatisch alle Rechte hätte.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy

from roles import texts
from units.models import Kind as UnitKind
from units.models import Unit


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


# An welcher Ebene jede Rolle hängt; Admin an keiner.
UNIT_KINDS = {
    RoleKind.MEMBER: (UnitKind.GROUP, UnitKind.TROOP, UnitKind.RING, UnitKind.ASSOCIATION),
    RoleKind.GROUP_LEAD: (UnitKind.GROUP,),
    RoleKind.TROOP_LEAD: (UnitKind.TROOP,),
    RoleKind.RING_LEAD: (UnitKind.RING,),
    RoleKind.ASSOCIATION_LEAD: (UnitKind.ASSOCIATION,),
    RoleKind.FEDERATION_LEAD: (UnitKind.FEDERATION,),
    RoleKind.EVENT_TEAM: (UnitKind.FEDERATION,),
    RoleKind.ADMIN: (),
}
# Leitungsrollen, die auf dem Pfad der Mitgliedschaft liegen müssen, in der Reihenfolge für Meldungen.
# Verbandsleitung und DPV-Veranstaltungsteam gehören nicht dazu: Am Verband ist niemand Mitglied.
LEADS_IN_UNITS = (RoleKind.GROUP_LEAD, RoleKind.TROOP_LEAD, RoleKind.RING_LEAD, RoleKind.ASSOCIATION_LEAD)


class Role(models.Model):
    """Eine Rolle einer Person mit Account, an einer Einheit oder (nur Admin) ohne.

    Regeln (Klärung von #89 am 22.10.2026, Fragen bei der Umsetzung am 23.10.2026):
    - Jede Rolle außer Admin hängt an genau einer Einheit der passenden Ebene. Dieselbe Rolle
      hat eine Person in derselben Einheit höchstens einmal, Admin höchstens einmal.
    - Mitglied ist eine Person in höchstens einer Einheit, nie im Verband.
    - Leitungsrollen in Einheiten liegen auf dem Pfad der Mitgliedschaft: im eigenen Stamm (auch
      in anderen Gruppen dort) und in den Einheiten darüber; wer direkt Mitglied eines Rings oder
      Bundes ist, auch in allen Einheiten darunter.
    - Wer ohne Mitgliedschaft eine Leitungsrolle in einer Einheit bekommt, wird zugleich Mitglied
      der geleiteten Einheit und bleibt es, wenn die Leitung endet.
    - Eine Mitgliedschaft wechselt oder endet nur, wenn danach alle Leitungsrollen in Einheiten
      noch auf dem Pfad liegen; ohne Mitgliedschaft heißt das: keine solchen Leitungsrollen.
    - Nur die Einheit einer Mitgliedschaft lässt sich ändern; jede andere Rolle wird entfernt und
      neu gegeben, damit jede Änderung als solche im Protokoll steht (#91).

    `save()` und `delete()` sperren die Person, bis die Änderung gespeichert ist; so laufen
    gleichzeitige Änderungen an den Rollen derselben Person nacheinander. Sie lehnen mit
    `ValidationError` und einer Meldung in Alltagssprache ab. Wer an ihnen vorbei schreibt
    (`update()`, `bulk_create()`, `QuerySet.delete()`), umgeht die Regeln, die nur das Tool prüft.
    """

    Kind = RoleKind

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="roles")
    kind = models.CharField(max_length=20, choices=RoleKind)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name="roles")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind=RoleKind.ADMIN, unit__isnull=True) | (~Q(kind=RoleKind.ADMIN) & Q(unit__isnull=False)),
                name="role_unit_except_admin",
            ),
            models.UniqueConstraint(fields=["user"], condition=Q(kind=RoleKind.MEMBER), name="role_one_membership"),
            models.UniqueConstraint(fields=["user"], condition=Q(kind=RoleKind.ADMIN), name="role_one_admin"),
            models.UniqueConstraint(
                fields=["user", "kind", "unit"], condition=Q(unit__isnull=False), name="role_once_per_unit"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.unit or '-'}"

    def save(self, *args, **kwargs) -> None:
        """Prüft die Regeln, speichert und legt bei Bedarf die Mitgliedschaft an."""
        with transaction.atomic():
            self._lock_person()
            stored = Role.objects.filter(pk=self.pk).values("user_id", "kind", "unit_id").first() if self.pk else None
            errors = self._errors(stored)
            if errors:
                raise ValidationError(errors)
            try:
                with transaction.atomic():
                    super().save(*args, **kwargs)
            except IntegrityError as error:
                # Nur am Tool vorbei möglich, weil die Sperre gleichzeitige Änderungen nacheinander reiht.
                duplicate = self._duplicate_error()
                if duplicate:
                    raise ValidationError(duplicate) from error
                raise
            if self.kind in LEADS_IN_UNITS and self._membership() is None:
                Role(user=self.user, kind=RoleKind.MEMBER, unit=self.unit).save()

    def delete(self, *args, **kwargs):
        """Entfernt die Rolle; eine Mitgliedschaft nur, wenn keine Leitungsrolle in einer Einheit mehr besteht."""
        with transaction.atomic():
            self._lock_person()
            if self.kind == RoleKind.MEMBER:
                blocking = list(self._leads())
                if blocking:
                    raise ValidationError(self._remove_first(blocking))
            return super().delete(*args, **kwargs)

    def _lock_person(self) -> None:
        """Sperrt das Konto, damit die Regeln den Stand sehen, den die Änderung tatsächlich trifft."""
        list(get_user_model().objects.select_for_update().filter(pk=self.user_id).values_list("pk"))

    def _errors(self, stored: dict | None) -> list:
        """Alle Gründe, aus denen diese Rolle so nicht gespeichert werden darf."""
        if stored and (
            stored["user_id"] != self.user_id
            or stored["kind"] != self.kind
            or (self.kind != RoleKind.MEMBER and stored["unit_id"] != self.unit_id)
        ):
            return [texts.ROLE_FIXED]
        if self.kind not in UNIT_KINDS:
            self.clean_fields(exclude=["user", "unit"])  # meldet die unbekannte Rolle
        allowed = UNIT_KINDS[self.kind]
        if (self.unit is None) != (not allowed) or (self.unit is not None and self.unit.kind not in allowed):
            return [texts.WRONG_LEVEL[self.kind]]
        duplicate = self._duplicate_error()
        if duplicate:
            return [duplicate]
        if self.kind in LEADS_IN_UNITS:
            membership = self._membership()
            if membership and not on_path(membership.unit, self.unit):
                return [ValidationError(self._outside_path(membership.unit), code="outside_path")]
        if self.kind == RoleKind.MEMBER and stored and stored["unit_id"] != self.unit_id:
            blocking = [lead for lead in self._leads() if not on_path(self.unit, lead.unit)]
            if blocking:
                return [self._remove_first(blocking)]
        return []

    def _duplicate_error(self) -> str | None:
        """Meldung, wenn die Person diese Rolle dort schon hat; sonst None."""
        others = Role.objects.filter(user_id=self.user_id).exclude(pk=self.pk).select_related("unit__parent")
        name = person_name(self.user)
        if self.kind == RoleKind.ADMIN:
            return texts.ALREADY_ADMIN % {"person": name} if others.filter(kind=RoleKind.ADMIN).exists() else None
        if self.kind == RoleKind.MEMBER:
            other = others.filter(kind=RoleKind.MEMBER).first()
            return texts.SECOND_MEMBERSHIP % {"person": name, "unit": describe(other.unit)} if other else None
        if others.filter(kind=self.kind, unit_id=self.unit_id).exists():
            return texts.ALREADY_HAS_ROLE % {"person": name, "role": self.get_kind_display(), "unit": describe(self.unit)}
        return None

    def _membership(self) -> "Role | None":
        """Die Mitgliedschaft der Person, frisch aus der Datenbank, ohne diese Rolle selbst."""
        return (
            Role.objects.filter(user_id=self.user_id, kind=RoleKind.MEMBER)
            .exclude(pk=self.pk)
            .select_related("unit__parent")
            .first()
        )

    def _leads(self) -> models.QuerySet:
        """Die Leitungsrollen der Person in Einheiten, in der Reihenfolge für Meldungen."""
        order = models.Case(*(models.When(kind=kind, then=i) for i, kind in enumerate(LEADS_IN_UNITS)))
        return (
            Role.objects.filter(user_id=self.user_id, kind__in=LEADS_IN_UNITS)
            .select_related("unit__parent")
            .order_by(order, "unit__name")
        )

    def _outside_path(self, member_unit: Unit) -> str:
        return texts.OUTSIDE_PATH % {
            "person": person_name(self.user),
            "unit": describe(member_unit),
            "target": describe(self.unit),
        }

    def _remove_first(self, blocking: list["Role"]) -> str:
        """Meldung, welche Leitungsrollen zuerst entfernt werden müssen."""
        parts = [str(texts.ROLE_IN_UNIT % {"role": r.get_kind_display(), "unit": describe(r.unit)}) for r in blocking]
        listed = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} {texts.AND} {parts[-1]}"
        message = texts.REMOVE_ROLE_FIRST if len(parts) == 1 else texts.REMOVE_ROLES_FIRST
        return message % {"person": person_name(self.user), "roles": listed}


def on_path(member_unit: Unit, target: Unit) -> bool:
    """Liegt `target` auf dem Pfad einer Person, die Mitglied in `member_unit` ist?

    Ausgangspunkt ist der eigene Stamm, bei direkten Mitgliedern eines Stammes, Rings oder
    Bundes diese Einheit selbst. Auf dem Pfad liegt alles darüber und alles darunter; damit
    zählen auch die anderen Gruppen im eigenen Stamm.
    """
    anchor = member_unit.parent if member_unit.kind == UnitKind.GROUP else member_unit
    return anchor.pk in _upwards(target) or target.pk in _upwards(anchor)


def _upwards(unit: Unit) -> list[int]:
    """Die Kennungen der Einheit und aller Einheiten darüber, höchstens fünf Ebenen."""
    found = []
    while unit is not None:
        found.append(unit.pk)
        unit = unit.parent
    return found


def person_name(user) -> str:
    """Der Name für Meldungen; ohne Namen in Keycloak der Benutzername."""
    return user.get_full_name() or user.username


def describe(unit: Unit) -> str:
    """Wie eine Einheit in Meldungen heißt."""
    if unit.kind == UnitKind.GROUP:
        return texts.GROUP_IN_TROOP % {"unit": unit.name, "troop": unit.parent.name}
    return texts.UNIT % {"unit": unit.name}
