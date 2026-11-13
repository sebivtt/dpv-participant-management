"""Datenmodell der verwalteten Personen (#117, PER-02)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Trim

from access.keys import KEY_LENGTH, key_field, new_key
from accounts.models import SCOUT_NAME_MAX_LENGTH, display_name
from persons import texts
from roles.models import LEADS_IN_UNITS, UNIT_KINDS, RoleKind, on_path
from units import texts as unit_texts
from units.models import Unit

# Höchstens 100 Zeichen für Vor- und Nachname, nach dem Entfernen der Leerzeichen am Rand (#117).
NAME_MAX_LENGTH = 100
# Die Angaben, die der Dialog anlegt und ändert; mehr gibt es in P2 nicht (#117), Gesundheitsangaben nie (FRM-04).
EDITABLE_FIELDS = ("first_name", "last_name", "birth_date", "scout_name")


class ManagedPerson(models.Model):
    """Ein Profil ohne Konto, etwa ein Kind, das eine Leitung für ihre Organisation anlegt (PER-02).

    Angaben in P2: Vorname, Nachname, Geburtsdatum (Pflicht) und Fahrtenname (freiwillig). Weitere
    Angaben gibt es nicht, Gesundheitsangaben nie (FRM-04). Die Person gehört genau einer
    Organisation: einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie dem Verband (#88).
    Eine Organisation mit verwalteter Person lässt sich nicht löschen (#88, MG8). Rechte an ihr
    entstehen nur aus den Leitungsrollen dieser Organisation und der Ebenen darüber, nie daraus,
    wer sie angelegt hat (#89, VP-05); gelesen und geändert wird sie nur über die zentrale
    Rechteprüfung (`access/rights.py`).
    """

    # Zufällige Kennung für Adressen (#64).
    key = key_field()
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH)
    birth_date = models.DateField()
    scout_name = models.CharField(max_length=SCOUT_NAME_MAX_LENGTH, blank=True, default="")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="managed_persons")
    # Stand der Angaben: Jedes Speichern zählt ihn hoch. Der Dialog „… bearbeiten“ schickt den Stand
    # beim Öffnen mit; passt er nicht mehr, hat inzwischen jemand anderes gespeichert (MG6).
    version = models.PositiveIntegerField(default=1, editable=False)
    # Kennung des Dialogs, aus dem die Person angelegt wurde: Ein zweites Abschicken desselben
    # Dialogs, etwa ein Doppelklick, legt niemanden ein zweites Mal an (MG7).
    creation_key = models.CharField(max_length=KEY_LENGTH, unique=True, default=new_key, editable=False)
    # Bestätigung der Einwilligung (DSG-02, #98): welches Konto wann beim Anlegen bestätigt hat. Beides setzt
    # nur `Rights.add_managed()` aus der Anmeldung und der Uhr des Servers, nie ein Formular; danach ändert es
    # niemand mehr (VP-11, VP-13), und im Tool zeigt es keine Seite (VP-12). Wird das Konto gelöscht, bleiben
    # Person und Zeitpunkt; nur der Verweis auf das Konto wird leer (EG4). Leer sind beide nur bei Personen,
    # die vor #98 angelegt wurden.
    consent_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="+", editable=False)
    consent_at = models.DateTimeField(null=True, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(first_name="") & Q(first_name=Trim("first_name")),
                name="managed_person_first_name_trimmed_not_empty",
            ),
            models.CheckConstraint(
                condition=~Q(last_name="") & Q(last_name=Trim("last_name")),
                name="managed_person_last_name_trimmed_not_empty",
            ),
            models.CheckConstraint(condition=Q(scout_name=Trim("scout_name")), name="managed_person_scout_name_trimmed"),
        ]

    def __str__(self) -> str:
        return self.display_name

    def save(self, *args, **kwargs) -> None:
        """Speichert die Person; im Verband lehnt es mit `ValidationError` ab (#88).

        Ebenso, wenn sie in eine Organisation wechselt, zu der eine ihrer angezeigten Leitungsrollen nicht
        mehr passt (#99, LG2, wie PK-25); die Meldung nennt die Rollen, die zuerst beendet werden können.
        Die Datenbank kann beides nicht selbst prüfen, deshalb stehen die Regeln hier und gelten so auch
        für Befehle und Testdaten.
        """
        if Unit.objects.filter(pk=self.unit_id, kind=Unit.Kind.FEDERATION).exists():
            raise ValidationError(texts.NOT_IN_FEDERATION, code="federation")
        stored = ManagedPerson.objects.filter(pk=self.pk).values_list("unit_id", flat=True).first() if self.pk else None
        if stored is not None and stored != self.unit_id:
            # Nur bei einem Wechsel der Organisation; sonst bliebe nach einer Lücke anderswo selbst das Bearbeiten
            # der Angaben gesperrt (unabhängige Prüfung, Befund B1).
            target = Unit.objects.select_related("parent__parent__parent__parent").get(pk=self.unit_id)
            blocking = self.leads_outside(target)
            if blocking:
                raise ValidationError(roles_blocking(self, blocking, target), code="remove_roles_first")
        super().save(*args, **kwargs)

    def leads_outside(self, target: Unit) -> list["DisplayedLead"]:
        """Die angezeigten Leitungsrollen, die nicht mehr auf dem Pfad lägen, gehörte die Person zu `target` (#99, LG2).

        Wie `Role.leads_outside()` bei Personen mit Konto (PK-25). Ändert nichts.
        """
        leads = DisplayedLead.objects.filter(person_id=self.pk).select_related("unit__parent__parent__parent__parent")
        return [lead for lead in leads.order_by(lead_order(), "unit__name") if not on_path(target, lead.unit)]

    @property
    def display_name(self) -> str:
        """Der Name wie überall im Tool: „Kiwi (Lena Probe)“, ohne Fahrtenname „Lena Probe“ (#111)."""
        return display_name(self.first_name, self.last_name, self.scout_name)


class DisplayedLead(models.Model):
    """Eine angezeigte Leitungsrolle einer verwalteten Person: „nur Anzeige“, ohne Rechte (#99, PER-07).

    Regeln (Klärungen von #99 am 22.10.2026 und 11.11.2026):
    - Gruppen-, Stammes-, Ring- oder Bundesleitung an einer Organisation der passenden Ebene, dieselbe
      Rolle dort höchstens einmal (LG1, LG3; die Datenbank setzt das selbst durch).
    - Die Rolle liegt auf dem Leitungspfad der Person, wie bei Personen mit Konto (ROL-01, #89; Klärung
      vom 11.11.2026, Frage 1). Wechselt die Person die Organisation, prüft `ManagedPerson.save()` das
      erneut (LG2).
    - Die Rolle gibt keine Rechte und zählt nie als Leitung (VP-16): Sie steht bewusst in einer eigenen
      Tabelle, nicht bei den Rollen (`roles.Role`), die die Rechteprüfung liest. Ins Protokoll der
      Rollenänderungen kommt sie nicht (#91, L9).
    - Wird die Person gelöscht, verschwindet die Rolle mit (L8). Eine Organisation mit angezeigter Rolle
      lässt sich nicht löschen, wie eine mit Rollen (`PROTECT`).

    Eingetragen und entfernt wird nur über die zentrale Rechteprüfung (`Rights.appoint_displayed()`,
    `Rights.remove_displayed()`), die auch die gleichzeitigen Änderungen ordnet.
    """

    # Zufällige Kennung für Adressen, etwa zum Entfernen (#64); nie die laufende Nummer.
    key = key_field()
    person = models.ForeignKey(ManagedPerson, on_delete=models.CASCADE, related_name="displayed_leads")
    kind = models.CharField(max_length=20, choices=RoleKind)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="displayed_leads")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["person", "kind", "unit"], name="displayed_lead_once_per_unit"),
        ]

    def save(self, *args, **kwargs) -> None:
        """Speichert eine neue Rolle; lehnt mit `ValidationError` ab, wenn Ebene oder Leitungspfad nicht passen.

        Eine gespeicherte Rolle ändert sich nie; wer sie anders will, entfernt sie und trägt neu ein.
        """
        if not self._state.adding:
            raise ValidationError(texts.DISPLAYED_FIXED)
        unit = Unit.objects.select_related("parent__parent__parent__parent").get(pk=self.unit_id)
        if self.kind not in LEADS_IN_UNITS or unit.kind not in UNIT_KINDS[self.kind]:
            raise ValidationError(texts.DISPLAYED_WRONG_LEVEL, code="wrong_level")
        # Die Person kommt über den Verweis, nicht über eine eigene Abfrage: Personendaten liest nur die
        # zentrale Rechteprüfung (CONTRIBUTING.md, Abschnitt 4); ihre Organisation dagegen frisch.
        person = self.person
        member_unit = Unit.objects.select_related("parent__parent__parent__parent").get(pk=person.unit_id)
        if not on_path(member_unit, unit):
            values = {"person": person.display_name, "unit": unit_label(member_unit), "target": kind_and_name(unit)}
            raise ValidationError(texts.DISPLAYED_OFF_PATH % values, code="outside_path")
        super().save(*args, **kwargs)


def lead_order() -> models.Case:
    """Leitungsrollen in der Reihenfolge für Meldungen: Gruppe, Stamm, Ring, Bund."""
    return models.Case(*(models.When(kind=kind, then=i) for i, kind in enumerate(LEADS_IN_UNITS)))


def unit_label(unit: Unit) -> str:
    """Eine Organisation wie im Abschnitt „Personen“: „Stamm Walhall“, Gruppen nur mit Namen („Sippe Falken“)."""
    return str(unit_texts.MEMBER_UNIT_NAME[unit.kind] % {"unit": unit.name})


def kind_and_name(unit: Unit) -> str:
    """Eine Organisation mit ihrer Art davor, wie beim Benennen: „Stamm Zugvögel“ (#190)."""
    return str(unit_texts.KIND_AND_NAME[unit.kind] % {"unit": unit.name})


def roles_blocking(person: ManagedPerson, blocking: list[DisplayedLead], target: Unit) -> str:
    """Der Satz wie bei Personen mit Konto (PK-25): „… ist Stammesleitung von Stamm Zugvögel. Diese Rolle passt …“."""
    roles = [str(unit_texts.ROLE_OF % {"role": lead.get_kind_display(), "unit": unit_label(lead.unit)})
             for lead in blocking]
    listed = roles[0] if len(roles) == 1 else f"{', '.join(roles[:-1])} {unit_texts.AND} {roles[-1]}"
    text = unit_texts.MOVE_ROLE_DOES_NOT_FIT if len(roles) == 1 else unit_texts.MOVE_ROLES_DO_NOT_FIT
    return str(text % {"person": person.display_name, "roles": listed, "target": unit_label(target)})


def displayed_off_path(troop: Unit, new_parent: Unit) -> list[tuple[ManagedPerson, list[DisplayedLead]]]:
    """Wessen angezeigte Leitungsrollen nach einem Ringwechsel von `troop` nicht mehr auf dem Pfad lägen (#99, LG5).

    Wie `roles.models.leads_off_path()` für Personen mit Konto (OG5): Betroffen sind Rollen im Stamm und in seinen
    Gruppen und alle Rollen von Personen, die zum Stamm oder einer seiner Gruppen gehören. Gezählt werden nur
    Rollen, die heute auf dem Pfad liegen und es danach nicht mehr täten. Gibt je betroffener Person
    sie und diese Rollen zurück, nach Namen geordnet. Ändert nichts; nur innerhalb der Transaktion mit gesperrtem
    Bund verlässlich.
    """
    bund = troop.association_id
    rows = Unit.objects.filter(Q(pk=bund) | Q(association_id=bund) | Q(parent__association_id=bund)).values_list(
        "pk", "parent_id", "kind")
    before = {pk: (parent, kind) for pk, parent, kind in rows}
    after = {**before, troop.pk: (new_parent.pk, before[troop.pk][1])}
    below = {troop.pk} | {pk for pk, (parent, _kind) in before.items() if parent == troop.pk}
    found: dict[int, tuple[ManagedPerson, list[DisplayedLead]]] = {}
    # Rollen im Stamm und darunter, und alle Rollen von Personen, die zum Stamm oder einer seiner Gruppen gehören,
    # etwa als angezeigte Ringleitung darüber (unabhängige Prüfung, Befund B1).
    involved = Q(unit_id__in=below) | Q(person__unit_id__in=below)
    leads = DisplayedLead.objects.filter(involved).select_related("person", "unit__parent").order_by(
        lead_order(), "unit__name")
    for lead in leads:
        on_before = _lies_on(before, lead.person.unit_id, lead.unit_id)
        on_after = _lies_on(after, lead.person.unit_id, lead.unit_id)
        if on_before and not on_after:
            found.setdefault(lead.person_id, (lead.person, []))[1].append(lead)
    return sorted(found.values(), key=lambda pair: (pair[0].last_name, pair[0].first_name, pair[0].pk))


def _lies_on(tree: dict[int, tuple[int | None, str]], member_unit: int, target: int) -> bool:
    """Wie `on_path()`, über einen Baum aus Nummern (Einheit → Einheit darüber und Ebene), etwa nach einem Wechsel."""

    def upwards(unit):
        found = set()
        while unit is not None and unit in tree:
            found.add(unit)
            unit = tree[unit][0]
        return found

    parent, kind = tree.get(member_unit, (None, None))
    anchor = parent if kind == Unit.Kind.GROUP else member_unit
    return anchor is not None and (anchor in upwards(target) or target in upwards(anchor))
