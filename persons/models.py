"""Datenmodell der verwalteten Personen (#117, PER-02)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Trim

from access.keys import KEY_LENGTH, key_field, new_key
from accounts.models import SCOUT_NAME_MAX_LENGTH, display_name
from persons import texts
from roles.models import RoleKind
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

        Die Datenbank kann die Ebene der Organisation nicht selbst prüfen, deshalb steht die Regel hier
        und gilt so auch für Befehle und Testdaten.
        """
        if Unit.objects.filter(pk=self.unit_id, kind=Unit.Kind.FEDERATION).exists():
            raise ValidationError(texts.NOT_IN_FEDERATION, code="federation")
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        """Der Name wie überall im Tool: „Kiwi (Lena Probe)“, ohne Fahrtenname „Lena Probe“ (#111)."""
        return display_name(self.first_name, self.last_name, self.scout_name)


class DisplayedLead(models.Model):
    """Eine angezeigte Leitungsrolle einer verwalteten Person: „nur Anzeige“, ohne Rechte (#99, PER-07).

    Gerüst; Regeln und Prüfungen kommen mit der Umsetzung von #99.
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
