"""Datenmodell der Einheiten des DPV: Verband, Bund, Ring, Stamm und Gruppe (#88, ORG-01).

Alle fünf Ebenen stehen in einer Tabelle, jede Einheit mit ihrer Art und der Einheit direkt
darüber. So reicht später ein einziger Verweis, wenn Personen, Rollen oder Teilnahmekreise an
einer Einheit beliebiger Ebene hängen. Welche Art unter welcher hängen darf, prüft das Tool
beim Speichern; alles, was die Datenbank selbst durchsetzen kann (genau ein Verband, eindeutige
Namen, Löschschutz), steht zusätzlich als Regel in der Datenbank.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q, Value
from django.db.models.functions import Lower, Trim
from django.utils.translation import gettext_lazy

from units import texts


class Kind(models.TextChoices):
    """Die Ebenen in ihrer Reihenfolge von oben nach unten."""

    FEDERATION = "federation", gettext_lazy("Verband")
    ASSOCIATION = "association", gettext_lazy("Bund")
    RING = "ring", gettext_lazy("Ring")
    TROOP = "troop", gettext_lazy("Stamm")
    GROUP = "group", gettext_lazy("Gruppe")


# Unter welcher Art jede Art hängen darf, und die Meldung, wenn nicht.
ALLOWED_PARENTS = {
    Kind.FEDERATION: ((), texts.FEDERATION_HAS_NO_PARENT),
    Kind.ASSOCIATION: ((Kind.FEDERATION,), texts.ASSOCIATION_PARENT),
    Kind.RING: ((Kind.ASSOCIATION,), texts.RING_PARENT),
    Kind.TROOP: ((Kind.RING, Kind.ASSOCIATION), texts.TROOP_PARENT),
    Kind.GROUP: ((Kind.TROOP,), texts.GROUP_PARENT),
}
BELOW_ASSOCIATION = (Kind.RING, Kind.TROOP, Kind.GROUP)


class Unit(models.Model):
    """Eine Einheit des DPV; nach außen heißt sie „Organisation“.

    Regeln (Klärung von #88 am 22. und 23.10.2026):
    - Es gibt genau einen Verband. Ein Bund hängt am Verband, ein Ring an einem Bund, ein Stamm
      an einem Ring oder direkt an einem Bund, eine Gruppe an einem Stamm.
    - Ringe gibt es nur in einem Bund mit eingeschaltetem „hat Ringe“. Dort hängt jeder neue
      Stamm in einem Ring; Stämme von vor dem Einschalten dürfen ohne Ring bleiben.
    - Namen sind nie leer und höchstens 100 Zeichen lang. Eindeutig sind Bünde im Verband, Ringe
      und Stämme zusammen im Bund (auch über Ringe hinweg) und Gruppen im Stamm. Als gleich gilt,
      was sich nur in Groß- und Kleinschreibung oder Leerzeichen am Rand unterscheidet.
    - Eine Einheit, unter der noch etwas hängt, lässt sich nicht löschen (Entscheidung W5).

    Die Regeln gelten bei jedem Speichern, auch für Testdaten und spätere Seiten; `save()`
    lehnt mit `ValidationError` und einer Meldung in Alltagssprache ab.
    """

    Kind = Kind

    kind = models.CharField(max_length=20, choices=Kind)
    name = models.CharField(max_length=100, error_messages={"blank": texts.NAME_EMPTY})
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Der Bund, zu dem ein Ring, Stamm oder eine Gruppe gehört. Steht zusätzlich zur Einheit
    # darüber, damit die Datenbank selbst „kein Stamm heißt im Bund zweimal gleich“ prüfen
    # kann, auch über Ringe hinweg und bei gleichzeitigen Anfragen. Setzt `save()` selbst.
    association = models.ForeignKey(
        "self", null=True, blank=True, editable=False, on_delete=models.PROTECT, related_name="+"
    )
    has_rings = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(name="") & Q(name=Trim("name")), name="unit_name_trimmed_not_empty"),
            models.CheckConstraint(
                condition=Q(kind=Kind.FEDERATION, parent__isnull=True)
                | (~Q(kind=Kind.FEDERATION) & Q(parent__isnull=False)),
                name="unit_parent_except_federation",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=BELOW_ASSOCIATION, association__isnull=False)
                | Q(kind__in=(Kind.FEDERATION, Kind.ASSOCIATION), association__isnull=True),
                name="unit_association_below_association",
            ),
            models.CheckConstraint(
                condition=Q(has_rings=False) | Q(kind=Kind.ASSOCIATION), name="unit_only_association_has_rings"
            ),
            models.UniqueConstraint(fields=["kind"], condition=Q(kind=Kind.FEDERATION), name="unit_one_federation"),
            models.UniqueConstraint(
                Lower("name"), condition=Q(kind=Kind.ASSOCIATION), name="unit_association_name_unique"
            ),
            models.UniqueConstraint(
                Lower("name"),
                "association",
                condition=Q(kind__in=(Kind.RING, Kind.TROOP)),
                name="unit_ring_troop_name_unique_in_association",
            ),
            models.UniqueConstraint(
                Lower("name"), "parent", condition=Q(kind=Kind.GROUP), name="unit_group_name_unique_in_troop"
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        """Prüft die Regeln und speichert; lehnt mit `ValidationError` ab.

        Der betroffene Bund wird dabei gesperrt, bis gespeichert ist. Sonst könnten ein neuer
        Ring und das Ausschalten von „hat Ringe“ gleichzeitig durchgehen, weil keiner den
        anderen sieht. Legen zwei gleichzeitig denselben Namen an, lehnt die Datenbank den
        zweiten ab; er bekommt dieselbe Meldung wie sonst auch.
        """
        self.name = self.name.strip()
        self.association = self._find_association()
        try:
            with transaction.atomic():
                self._lock_association()
                self.full_clean(validate_unique=False, validate_constraints=False)
                super().save(*args, **kwargs)
        except IntegrityError as error:
            clash = self._name_clash()
            if clash:
                raise ValidationError(clash) from error
            raise

    def clean(self) -> None:
        """Prüft Ebene, Ringe und Namen und sammelt alle Gründe für eine Ablehnung."""
        errors = [*self._parent_errors(), *self._ring_errors()]
        clash = self._name_clash()
        if clash:
            errors.append(clash)
        if errors:
            raise ValidationError(errors)

    def _find_association(self) -> "Unit | None":
        """Der Bund über einem Ring, Stamm oder einer Gruppe; bei falscher Ebene keiner."""
        if self.kind not in BELOW_ASSOCIATION or self.parent is None:
            return None
        if self.parent.kind == Kind.ASSOCIATION:
            return self.parent
        return self.parent.association

    def _lock_association(self) -> None:
        """Sperrt den Bund, dessen Schalter „hat Ringe“ für dieses Speichern zählt."""
        if self.kind in (Kind.RING, Kind.TROOP):
            locked = self.association_id
        elif self.kind == Kind.ASSOCIATION:
            locked = self.pk
        else:
            return
        if locked:
            list(Unit.objects.select_for_update().filter(pk=locked).values_list("pk"))

    def _parent_errors(self) -> list:
        """Hängt die Einheit unter der richtigen Ebene? Eine unbekannte Art meldet clean_fields."""
        if self.kind not in ALLOWED_PARENTS:
            return []
        allowed, message = ALLOWED_PARENTS[self.kind]
        if allowed:
            valid = self.parent is not None and self.parent.kind in allowed
        else:
            valid = self.parent is None
        return [] if valid else [message]

    def _ring_errors(self) -> list:
        """Regeln zum Schalter „hat Ringe“. Liest den Schalter frisch aus der Datenbank."""
        if self.has_rings and self.kind != Kind.ASSOCIATION:
            return [texts.ONLY_ASSOCIATION_HAS_RINGS]
        if self.kind == Kind.ASSOCIATION and not self.has_rings and self.pk:
            if Unit.objects.filter(kind=Kind.RING, parent_id=self.pk).exists():
                return [texts.STILL_HAS_RINGS % {"association": self.name}]
            return []
        if self.association_id is None or self.kind not in (Kind.RING, Kind.TROOP):
            return []
        association = Unit.objects.get(pk=self.association_id)
        if self.kind == Kind.RING and not association.has_rings:
            return [texts.RINGS_SWITCHED_OFF % {"association": association.name}]
        new_troop_without_ring = self._state.adding and self.parent_id == association.pk
        if self.kind == Kind.TROOP and association.has_rings and new_troop_without_ring:
            return [texts.NEW_TROOP_NEEDS_RING % {"association": association.name}]
        return []

    def _name_clash(self) -> str | None:
        """Meldung, wenn es den Namen dort schon gibt, wo er eindeutig sein muss; sonst None."""
        if self.kind == Kind.FEDERATION:
            other = Unit.objects.filter(kind=Kind.FEDERATION).exclude(pk=self.pk).first()
            return texts.FEDERATION_EXISTS % {"name": other.name} if other else None
        same_name = Unit.objects.alias(key=Lower("name")).filter(key=Lower(Value(self.name))).exclude(pk=self.pk)
        if self.kind == Kind.ASSOCIATION:
            other = same_name.filter(kind=Kind.ASSOCIATION).first()
            return texts.ASSOCIATION_EXISTS % {"name": other.name} if other else None
        if self.kind in (Kind.RING, Kind.TROOP) and self.association_id:
            other = same_name.filter(kind__in=(Kind.RING, Kind.TROOP), association_id=self.association_id).first()
            if other:
                message = texts.RING_EXISTS if other.kind == Kind.RING else texts.TROOP_EXISTS
                return message % {"association": self.association.name, "name": other.name}
        if self.kind == Kind.GROUP and self.parent_id:
            other = same_name.filter(kind=Kind.GROUP, parent_id=self.parent_id).first()
            if other:
                return texts.GROUP_EXISTS % {"troop": self.parent.name, "name": other.name}
        return None
