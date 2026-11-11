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

from access.keys import key_field
from core import actors
from core.actors import check_actor
from roles.expressions import TransactionStart
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
# Ebenen, bei denen der Bund zusätzlich gespeichert wird (siehe Feld `association`).
WITH_ASSOCIATION = (Kind.RING, Kind.TROOP)


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

    - Die Ebene einer Einheit bleibt, ein Ring oder Stamm wechselt nicht den Bund und eine Gruppe
      nicht den Stamm (#95, Frage 13; #127 kann das gezielt öffnen).
    - Ein Stamm wechselt den Ring nur, wenn danach jede Leitungsrolle noch auf dem Pfad der
      Mitgliedschaft ihrer Person liegt (#89, #95). Dafür sperrt `save()` den Bund, wie das
      Speichern einer Rolle (`roles.models.Role.save()`), damit gleichzeitige Änderungen den
      Stand der anderen sehen.

    Die Regeln gelten bei jedem Speichern, auch für Testdaten und spätere Seiten; `save()`
    lehnt mit `ValidationError` und einer Meldung in Alltagssprache ab. Jedes Anlegen und jede
    tatsächliche Änderung an Name, Einheit darüber und „hat Ringe“ schreibt `save()` in
    derselben Transaktion ins Protokoll der Strukturänderungen (`UnitChange`, #131). Wer an
    `save()` vorbei schreibt (`update()`, `bulk_create()`), umgeht die Regeln, die nur das Tool
    prüft, und das Protokoll.
    """

    Kind = Kind

    kind = models.CharField(max_length=20, choices=Kind)
    name = models.CharField(max_length=100, error_messages={"blank": texts.NAME_EMPTY})
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Der Bund, zu dem ein Ring oder Stamm gehört. Steht zusätzlich zur Einheit darüber, damit
    # die Datenbank selbst „kein Stamm heißt im Bund zweimal gleich“ prüfen kann, auch über
    # Ringe hinweg und bei gleichzeitigen Anfragen. Setzt `save()` selbst. Gruppen brauchen ihn
    # nicht (eindeutig im Stamm), und ein Ring oder Stamm wechselt nie den Bund; so kann der
    # Wert bei keiner Einheit veralten.
    association = models.ForeignKey(
        "self", null=True, blank=True, editable=False, on_delete=models.PROTECT, related_name="+"
    )
    has_rings = models.BooleanField(default=False)
    # Zufällige Kennung für Adressen (#64); sie ändert sich nie und kommt nicht ins Protokoll.
    key = key_field()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(name="") & Q(name=Trim("name")), name="unit_name_trimmed_not_empty"),
            models.CheckConstraint(
                condition=Q(kind=Kind.FEDERATION, parent__isnull=True)
                | (~Q(kind=Kind.FEDERATION) & Q(parent__isnull=False)),
                name="unit_parent_except_federation",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=WITH_ASSOCIATION, association__isnull=False)
                | (~Q(kind__in=WITH_ASSOCIATION) & Q(association__isnull=True)),
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

    def names_above(self) -> list[str]:
        """Die Namen der Einheiten darüber, von oben nach unten, ohne den Verband (#96, ORG-05).

        Für eine Gruppe in Walhall im Bund Boreas also ["Pfadfinderbund Boreas", "Walhall"]; für
        einen Bund und den Verband selbst eine leere Liste. Ohne vorab geladene Einheiten darüber
        (`select_related`) fragt jede Stufe die Datenbank einzeln.
        """
        names = []
        unit = self.parent
        while unit is not None and unit.kind != Kind.FEDERATION:
            names.append(unit.name)
            unit = unit.parent
        return names[::-1]

    def save(self, *args, by, **kwargs) -> None:
        """Prüft die Regeln, speichert und schreibt ins Protokoll; lehnt mit `ValidationError` ab.

        `by` ist das Konto, das ändert, oder `SERVER_COMMAND`. Ohne diese Angabe lehnt das Tool
        jede Änderung ab, damit keine Seite den Urheber still vergisst (#131, wie #91).

        Der betroffene Bund wird dabei gesperrt, bis gespeichert ist. Sonst könnten ein neuer
        Ring und das Ausschalten von „hat Ringe“ gleichzeitig durchgehen, weil keiner den
        anderen sieht. Ebenso die Einheit selbst, damit das Protokoll den tatsächlich alten Wert
        festhält. Legen zwei gleichzeitig denselben Namen an, lehnt die Datenbank den zweiten
        ab; er bekommt dieselbe Meldung wie sonst auch.
        """
        check_actor(by)
        if kwargs.get("update_fields") is not None:
            # Django liest die Felder einmal; das Protokoll braucht sie danach noch einmal.
            kwargs["update_fields"] = frozenset(kwargs["update_fields"])
        self.name = self.name.strip()
        self.association = self._find_association()
        try:
            with transaction.atomic():
                self._lock_association()
                stored = self._lock_stored()
                self.full_clean(validate_unique=False, validate_constraints=False)
                self._check_leads_on_path(stored)
                super().save(*args, **kwargs)
                if self.parent_id:
                    # Die Einheit darüber frisch lesen: Im Programm kann ihr Name veraltet sein,
                    # ins Protokoll gehört der gespeicherte.
                    self.parent = Unit.objects.get(pk=self.parent_id)
                if stored is None:
                    self._record_created(by)
                else:
                    self._record_changes(by, stored, kwargs.get("update_fields"))
        except IntegrityError as error:
            clash = self._name_clash()
            if clash:
                raise ValidationError(clash) from error
            raise

    def _check_leads_on_path(self, stored: "Unit | None") -> None:
        """Lehnt einen Ringwechsel ab, nach dem eine Leitungsrolle nicht mehr auf dem Pfad läge (#89, #95).

        Läuft unter der Sperre des Bundes, die auch das Speichern einer Rolle nimmt; so sieht die
        Prüfung eine gleichzeitig benannte Leitung (OG9).
        """
        if stored is None or self.kind != Kind.TROOP or stored.parent_id == self.parent_id:
            return
        # Rollen liegen eine Schicht gleich hoch und binden dieses Modul ein; deshalb erst hier.
        from roles.models import describe, leads_off_path

        blocking = [lead for _membership, leads in leads_off_path(self, self.parent) for lead in leads]
        if blocking:
            roles = ", ".join(f"{lead.get_kind_display()} {describe(lead.unit)}" for lead in blocking)
            raise ValidationError(texts.LEADS_OFF_PATH % {"roles": roles}, code="leads_off_path")

    def clean(self) -> None:
        """Prüft Ebene, Ringe und Namen und sammelt alle Gründe für eine Ablehnung."""
        stored = Unit.objects.filter(pk=self.pk).values("kind", "parent_id", "association_id").first()
        errors = [*self._change_errors(stored), *self._parent_errors(), *self._ring_errors(stored)]
        clash = self._name_clash()
        if clash:
            errors.append(clash)
        if errors:
            raise ValidationError(errors)

    def _find_association(self) -> "Unit | None":
        """Der Bund über einem Ring oder Stamm; bei anderer oder falscher Ebene keiner."""
        if self.kind not in WITH_ASSOCIATION or self.parent is None:
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

    def _lock_stored(self) -> "Unit | None":
        """Sperrt die gespeicherte Einheit bis zum Ende des Speicherns und gibt ihren Stand zurück.

        Ohne die Sperre sähen zwei gleichzeitige Umbenennungen beide den Namen von vorher, und
        im Protokoll stünde zweimal „A → …“ statt „A → B“ und danach „B → C“.
        """
        if self.pk is None:
            return None
        list(Unit.objects.select_for_update().filter(pk=self.pk).values_list("pk"))
        return Unit.objects.select_related("parent").filter(pk=self.pk).first()

    def _record_created(self, by) -> None:
        """Schreibt das Anlegen ins Protokoll, mit der Einheit darüber (F1 in #131).

        Ist „hat Ringe“ gleich eingeschaltet, kommt das als eigener Eintrag dazu (F2), damit
        jedes Einschalten gleich im Protokoll steht.
        """
        name = logged_name(self)
        where = logged_name(self.parent) if self.parent else ""
        UnitChange.record(by, self, name, UnitChange.Action.CREATED, new=where, new_parent_id=self.parent_id)
        if self.has_rings:
            UnitChange.record(by, self, name, UnitChange.Action.HAS_RINGS, old=texts.SWITCH_OFF, new=texts.SWITCH_ON)

    def _record_changes(self, by, stored: "Unit", update_fields) -> None:
        """Schreibt jede tatsächliche Änderung ins Protokoll, mit dem Namen von vor dem Speichern.

        Zählt nur, was dieses Speichern tatsächlich schreibt. Die Befehle schreiben nur ein Feld;
        ein im Programm veralteter Wert der übrigen Felder ist keine Änderung.
        """
        if update_fields is None:
            written = {"name", "parent", "has_rings"}
        else:
            written = {self._meta.get_field(field).name for field in update_fields}
        name = logged_name(stored)
        if "name" in written and stored.name != self.name:
            UnitChange.record(by, self, name, UnitChange.Action.RENAMED, old=stored.name, new=self.name)
        if "parent" in written and stored.parent_id != self.parent_id:
            UnitChange.record(
                by,
                self,
                name,
                self._move_action(stored.parent),
                old=self._place_name(stored.parent),
                new=self._place_name(self.parent),
                old_parent_id=stored.parent_id,
                new_parent_id=self.parent_id,
            )
        if "has_rings" in written and stored.has_rings != self.has_rings:
            switch = (texts.SWITCH_OFF, texts.SWITCH_ON) if self.has_rings else (texts.SWITCH_ON, texts.SWITCH_OFF)
            UnitChange.record(by, self, name, UnitChange.Action.HAS_RINGS, old=switch[0], new=switch[1])

    def _move_action(self, old_parent: "Unit") -> str:
        """Was das Verschieben heißt. Nur Stämme wechseln die Einheit darüber, seit #95 keine Gruppen mehr.

        Ein Stamm kommt nie neu ohne Ring an den Bund (#88); deshalb gibt es kein „aus dem
        Ring genommen“.
        """
        if old_parent.kind == Kind.ASSOCIATION:
            return UnitChange.Action.RING_ASSIGNED
        return UnitChange.Action.RING_CHANGED

    def _place_name(self, parent: "Unit") -> str:
        """Alter oder neuer Wert beim Verschieben: der Stamm einer Gruppe, der Ring eines Stammes."""
        if self.kind == Kind.TROOP and parent.kind != Kind.RING:
            return ""
        return parent.name

    def _change_errors(self, stored: dict | None) -> list:
        """Was sich an einer gespeicherten Einheit nicht ändern darf."""
        if stored is None:
            return []
        if stored["kind"] != self.kind:
            return [texts.KIND_FIXED]
        if self.kind in WITH_ASSOCIATION and stored["association_id"] != self.association_id:
            return [texts.STAYS_IN_ASSOCIATION]
        if self.kind == Kind.GROUP and stored["parent_id"] != self.parent_id:
            return [texts.GROUP_STAYS_IN_TROOP]
        return []

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

    def _ring_errors(self, stored: dict | None) -> list:
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
        # Stämme von vor dem Einschalten dürfen ohne Ring bleiben; neu ohne Ring an den Bund
        # kommt keiner, auch nicht durch Verschieben aus einem Ring.
        placed_without_ring = self.parent_id == association.pk and (
            stored is None or stored["parent_id"] != self.parent_id
        )
        if self.kind == Kind.TROOP and association.has_rings and placed_without_ring:
            return [texts.NEW_TROOP_NEEDS_RING % {"association": association.name}]
        return []

    def clashing(self) -> "Unit | None":
        """Die andere Einheit mit demselben Namen dort, wo er eindeutig sein muss; sonst None.

        Gleich ist, was sich nur in Groß- und Kleinschreibung unterscheidet; Leerzeichen am Rand
        entfernt `save()` vorher. Seiten nennen damit den Grund einer Ablehnung (#95, OG1).
        """
        if self.kind == Kind.FEDERATION:
            return Unit.objects.filter(kind=Kind.FEDERATION).exclude(pk=self.pk).first()
        same_name = (
            Unit.objects.alias(lowered_name=Lower("name"))
            .filter(lowered_name=Lower(Value(self.name.strip())))
            .exclude(pk=self.pk)
        )
        if self.kind == Kind.ASSOCIATION:
            return same_name.filter(kind=Kind.ASSOCIATION).first()
        association_id = self.association_id or getattr(self._find_association(), "pk", None)
        if self.kind in (Kind.RING, Kind.TROOP) and association_id:
            return same_name.filter(kind__in=(Kind.RING, Kind.TROOP), association_id=association_id).first()
        if self.kind == Kind.GROUP and self.parent_id:
            return same_name.filter(kind=Kind.GROUP, parent_id=self.parent_id).first()
        return None

    def _name_clash(self) -> str | None:
        """Meldung, wenn es den Namen dort schon gibt, wo er eindeutig sein muss; sonst None."""
        other = self.clashing()
        if other is None:
            return None
        if self.kind == Kind.FEDERATION:
            return texts.FEDERATION_EXISTS % {"name": other.name}
        if self.kind == Kind.ASSOCIATION:
            return texts.ASSOCIATION_EXISTS % {"name": other.name}
        if self.kind == Kind.GROUP:
            return texts.GROUP_EXISTS % {"troop": self.parent.name, "name": other.name}
        message = texts.RING_EXISTS if other.kind == Kind.RING else texts.TROOP_EXISTS
        return message % {"association": other.association.name, "name": other.name}


def logged_name(unit: Unit) -> str:
    """Wie eine Einheit im Protokoll heißt: ohne Anführungszeichen, Gruppen mit ihrem Stamm."""
    if unit.kind == Kind.GROUP:
        return texts.LOGGED_GROUP_IN_TROOP % {"unit": unit.name, "troop": unit.parent.name}
    return unit.name


class UnitChange(models.Model):
    """Ein Eintrag im Protokoll der Strukturänderungen (#131, ORG-06).

    Regeln (Klärung von #131 am 23.10.2026, Fragen bei der Umsetzung am selben Tag):
    - Ins Protokoll kommen Anlegen, Umbenennen, einen Stamm einem Ring zuordnen oder in einen
      anderen Ring verschieben und „hat Ringe“ ein- oder ausschalten; jede Änderung ein Eintrag.
      „Stamm gewechselt“ bleibt als Art für #127; seit #95 wechselt eine Gruppe nicht den Stamm. Nur tatsächliche Änderungen zählen,
      eine andere Schreibweise des Namens ist eine. Das Notfall-Löschen steht im Protokoll
      der Admin-Zugriffe (#92), nicht hier.
    - Ein Eintrag nennt Zeitpunkt, wer geändert hat, welche Organisation, was geändert wurde
      und bei Änderungen den alten und den neuen Wert; beim Anlegen als neuen Wert, wo die
      Organisation hängt. Ein Feld für einen Grund oder anderen freien Text gibt es nicht.
    - Beim Zuordnen und Wechseln eines Rings sind alter und neuer Wert die Namen der Ringe;
      leer heißt „kein Ring“. Dazu stehen die Kennungen der Einheiten darüber dabei.
    - Namen stehen so im Eintrag, wie sie vor der Änderung hießen, Gruppen mit ihrem Stamm.
      Kennungen sind wie bei #91 bewusst keine Verweise; ein Eintrag hindert nie daran, später
      eine Einheit zu löschen.
    - Bei Befehlen auf dem Server steht „Befehl auf dem Server“ als Urheber, ohne Kennung.
    - Uhrzeit und Reihenfolge wie bei `roles.RoleChange`: Beginn der äußersten Transaktion,
      Reihenfolge nach der Kennung `id`.
    - Einträge lassen sich nicht ändern oder löschen: hier im Programm und zusätzlich per Regel
      in der Datenbank (Migration 0002). Das vollständige Leeren der Datenbank bleibt möglich
      (#103); im Tool gibt es dafür keinen Weg.
    - In P2 sieht niemand das Protokoll im Tool (Entscheidung W4); die Einsicht kommt mit ADM-03.
    """

    class Action(models.TextChoices):
        CREATED = "created", gettext_lazy("angelegt")
        RENAMED = "renamed", gettext_lazy("umbenannt")
        RING_ASSIGNED = "ring_assigned", gettext_lazy("Ring zugeordnet")
        RING_CHANGED = "ring_changed", gettext_lazy("Ring gewechselt")
        TROOP_CHANGED = "troop_changed", gettext_lazy("Stamm gewechselt")
        HAS_RINGS = "has_rings", gettext_lazy("hat Ringe")

    changed_at = models.DateTimeField(db_default=TransactionStart())
    actor_id = models.BigIntegerField(null=True)
    actor_name = models.TextField()
    unit_id = models.BigIntegerField()
    unit_kind = models.CharField(max_length=20, choices=Kind)
    unit_name = models.TextField()
    action = models.CharField(max_length=20, choices=Action)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    old_parent_id = models.BigIntegerField(null=True)
    new_parent_id = models.BigIntegerField(null=True)

    @classmethod
    def record(cls, by, unit: Unit, unit_name: str, action: str, old="", new="", **parent_ids) -> "UnitChange":
        """Schreibt einen Eintrag; nur innerhalb der Transaktion der Änderung aufrufen."""
        entry = cls(
            actor_id=actors.actor_id(by),
            actor_name=actors.actor_name(by),
            unit_id=unit.pk,
            unit_kind=unit.kind,
            unit_name=unit_name,
            action=action,
            old_value=str(old),
            new_value=str(new),
            **parent_ids,
        )
        entry.save()
        return entry

    def save(self, *args, **kwargs) -> None:
        """Schreibt einen neuen Eintrag; einen bestehenden zu ändern lehnt das Tool ab."""
        if not self._state.adding:
            raise ValidationError(texts.LOG_LOCKED)
        # Nie als Änderung eines vorhandenen Eintrags speichern, auch nicht mit gesetzter Kennung.
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Einträge lassen sich nicht löschen."""
        raise ValidationError(texts.LOG_LOCKED)
