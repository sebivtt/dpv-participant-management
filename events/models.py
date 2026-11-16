"""Datenmodell der Veranstaltungen (#100, TEAM-01) und Anmeldungen (#101, ANM-01, ANM-02), Proben in P2."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Trim
from django.utils import timezone

from access.keys import KEY_LENGTH, key_field, new_key
from accounts.models import SCOUT_NAME_MAX_LENGTH, display_name
from events import texts
from persons.models import ManagedPerson
from roles.models import LEADS_IN_UNITS, Role, RoleKind
from units.models import Unit

# Höchstens 100 Zeichen für den Namen, nach dem Entfernen der Leerzeichen am Rand (#100).
NAME_MAX_LENGTH = 100
# Die Angaben, die „Veranstaltung erstellen“ anlegt und „… bearbeiten“ ändert; mehr gibt es in P2 nicht (#100).
EDITABLE_FIELDS = ("name", "start", "end")
# Kopierte Namen: so lang wie bei Konten (Django: 150), damit jede Kopie passt; verwaltete Personen haben höchstens 50.
PERSON_NAME_MAX_LENGTH = 150


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


class Registration(models.Model):
    """Eine Anmeldung zu genau einer Veranstaltung, abgegeben von genau einer Ansprechperson (ANM-02, ANM-03, #101).

    Sie nennt eine oder mehrere konkrete Personen, je Person einen Eintrag (`RegisteredPerson`); Kontingente gibt
    es nicht. Mit mehreren Personen heißt sie Sammelanmeldung. Dieselbe Person darf mehrfach zur selben
    Veranstaltung angemeldet sein; eine Sperre gibt es nicht (Klärung vom 22.10.2026, Frage 4; Hinweis ANM-07
    später).

    Entstehen kann sie nur über `create()`, zusammen mit ihren Personen in einer Transaktion: Wer angemeldet werden
    darf, prüft das Datenmodell dort selbst (ANM-01, AN-04, AN-05), damit auch das Formular in P4 nicht daran
    vorbeikommt. Ein einzelnes `save()` lehnt es ab, ebenso jede spätere Änderung (in P2 gibt es keine, AN-06).
    Gelesen wird eine Anmeldung nur über die zentrale Rechteprüfung (`access/rights.py`).
    """

    # Zufällige Kennung für Adressen (#64).
    key = key_field()
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="registrations")
    # Die Ansprechperson: wer die Anmeldung abgegeben hat (ANM-03). Ein Konto lässt sich in P2 nicht löschen (EP-09).
    contact = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registrations")
    # Wann sie abgegeben wurde; danach ordnet der Abschnitt „Anmeldungen“, die älteste zuerst (S1).
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def save(self, *args, **kwargs) -> None:
        """Speichert eine neue Anmeldung nur aus `create()`; sonst `ValidationError` (AG1, AN-06)."""
        if not self._state.adding or not getattr(self, "_creating", False):
            raise ValidationError(texts.REGISTRATION_ONLY_WITH_PERSONS, code="only_with_persons")
        super().save(*args, **kwargs)

    @classmethod
    def create(cls, event: Event | None, contact, people: list) -> "Registration":
        """Legt eine Anmeldung von `contact` zu `event` mit den Personen aus `people` an; gibt sie zurück (ANM-01, ANM-02).

        `people` sind Konten und verwaltete Personen, in der Reihenfolge, in der sie in der Anmeldung stehen.
        Erlaubt sind die Ansprechperson selbst und Personen, die sie verwalten darf (`may_register()`);
        ist auch nur eine Person nicht erlaubt, fehlt die Veranstaltung, die Ansprechperson oder jede Person,
        entsteht nichts, auch nicht für die übrigen (AV1, AG1), und das Ergebnis ist `ValidationError`.
        Jede Person bekommt eine Kopie ihrer Angaben, wie sie jetzt in der Datenbank stehen, bei Personen mit Konto
        ohne Geburtsdatum (A5); ein im Speicher geändertes Objekt zählt nicht (Befund B2 der unabhängigen Prüfung).

        Vor der Prüfung sperrt es in der Reihenfolge wie beim Speichern von Rollen und Einheiten (`_lock_structure()`
        in `access/rights.py`): die Konten (Ansprechperson und angemeldete Konten), alle Bünde, dann die verwalteten
        Personen. Ein gleichzeitiges Beenden einer Rolle, Verschieben, Austragen oder ein Ringwechsel ist danach
        entweder schon gespeichert oder wartet, nie halb (AG1, Befund B1).
        """
        if event is None or contact is None or not people:
            raise ValidationError(texts.REGISTRATION_ONLY_WITH_PERSONS, code="only_with_persons")
        with transaction.atomic():
            people = _locked(contact, people)
            not_allowed = [person for person in people if not may_register(contact, person)]
            if not_allowed:
                names = ", ".join(name_of(person) for person in not_allowed)
                raise ValidationError(texts.NOT_REGISTERABLE % {"persons": names}, code="not_allowed")
            registration = cls(event=event, contact=contact)
            registration._creating = True
            registration.save()
            for person in people:
                entry = RegisteredPerson(registration=registration, **copy_of(person))
                entry._creating = True
                entry.save()
        return registration


class RegisteredPerson(models.Model):
    """Eine angemeldete Person in einer Anmeldung, mit einer Kopie ihrer Angaben beim Anmelden (ANM-02, #101).

    Kopiert sind Vorname, Nachname, Geburtsdatum und Fahrtenname, bei Personen mit Konto ohne Geburtsdatum (sie
    haben in P2 keins, #143). Spätere Änderungen am Profil ändern die Kopie nicht (A5). Dazu die Verbindung zum
    Profil: zum Konto oder zur verwalteten Person, nie zu beidem. Wird eine verwaltete Person gelöscht (#118),
    fällt nur diese Verbindung weg; Eintrag und Kopie bleiben (A6). Angaben in einer Anmeldung hängen später je an
    diesem Eintrag (Vorbereitung FRM-09). Entsteht nur zusammen mit ihrer Anmeldung (`Registration.create()`).
    """

    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name="persons")
    first_name = models.CharField(max_length=PERSON_NAME_MAX_LENGTH, blank=True)
    last_name = models.CharField(max_length=PERSON_NAME_MAX_LENGTH, blank=True)
    birth_date = models.DateField(null=True)
    scout_name = models.CharField(max_length=SCOUT_NAME_MAX_LENGTH, blank=True, default="")
    # Ein Konto lässt sich in P2 nicht löschen (EP-09); was dann mit Anmeldungen geschieht, ist noch offen.
    account = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    managed = models.ForeignKey(ManagedPerson, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(account__isnull=True) | Q(managed__isnull=True),
                                   name="registered_person_one_profile"),
            models.CheckConstraint(condition=Q(account__isnull=True) | Q(birth_date__isnull=True),
                                   name="registered_person_account_without_birth_date"),
        ]

    def save(self, *args, **kwargs) -> None:
        """Speichert einen neuen Eintrag nur zusammen mit seiner Anmeldung; sonst `ValidationError` (AV1, AN-06)."""
        if not self._state.adding or not getattr(self, "_creating", False):
            raise ValidationError(texts.REGISTRATION_ONLY_WITH_PERSONS, code="only_with_persons")
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        """Der Name aus der Kopie wie überall im Tool: „Kiwi (Lena Probe)“ (#111)."""
        return display_name(self.first_name, self.last_name, self.scout_name)

    @property
    def shown_name(self) -> str:
        """Der Name auf den Seiten: aus der Kopie; ohne Namen der Benutzername des verbundenen Kontos (#189, A12)."""
        if self.display_name or self.account is None:
            return self.display_name
        return self.account.username


def may_register(contact, person) -> bool:
    """Darf `contact` die Person `person` anmelden, ein Konto oder eine verwaltete Person (ANM-01, AN-04, AN-05)?

    Sich selbst immer, in P2 auch ohne Zuordnung (A4; ab P3 nicht mehr, BER-03). Andere nur als Leitung ihres
    Bereichs, wie beim Sehen und Verwalten (#65, #117, `Rights.area`): Die Organisation der Person, bei einem Konto
    die seiner Mitgliedschaft, ist eine geleitete oder liegt darunter. Die Gruppenleitung meldet also nur ihre
    Gruppe an, die Stammesleitung den ganzen Stamm, Ring- und Bundesleitung alles darunter. Verbandsleitung,
    DPV-Veranstaltungsteam, Mitglieder und Konten ohne Zuordnung leiten keine Organisation und melden nur sich
    selbst an. Es zählen nur die eigenen Rollen, nie ein Support-Zugang: Als Ansprechperson sähe ein Admin die
    Anmeldung sonst dauerhaft (Nachklärung vom 15.11.2026, Frage 2; #92). Ein gesperrtes Konto meldet niemanden an.

    Die Regel steht hier im Datenmodell, nicht in der Rechteprüfung, damit keine Seite und kein Formular daran
    vorbeikommt (Klärung vom 22.10.2026; `docs/aufbau.md`, Schichten). Alles kommt frisch aus der Datenbank.
    """
    users = get_user_model().objects
    if getattr(contact, "pk", None) is None or not users.filter(pk=contact.pk, is_active=True).exists():
        return False
    if isinstance(person, ManagedPerson):
        unit_id = ManagedPerson.objects.filter(pk=person.pk).values_list("unit_id", flat=True).first()
    elif isinstance(person, get_user_model()) and person.pk is not None:
        if person.pk == contact.pk:
            return True
        unit_id = Role.objects.filter(user_id=person.pk, kind=RoleKind.MEMBER).values_list("unit_id", flat=True).first()
    else:
        return False
    led = set(Role.objects.filter(user_id=contact.pk, kind__in=LEADS_IN_UNITS).values_list("unit_id", flat=True))
    while unit_id is not None and led:
        if unit_id in led:
            return True
        unit_id = Unit.objects.filter(pk=unit_id).values_list("parent_id", flat=True).first()
    return False


def _locked(contact, people: list) -> list:
    """Sperrt Konten, Bünde und verwaltete Personen einer Anmeldung bis zum Ende der Transaktion (Befund B1).

    Gibt die Personen in derselben Reihenfolge frisch aus der Datenbank zurück; was es nicht mehr gibt oder weder
    Konto noch verwaltete Person ist, bleibt, wie es war, und `may_register()` lehnt es ab.
    """
    users = get_user_model()
    account_ids = {contact.pk} | {p.pk for p in people if isinstance(p, users) and p.pk is not None}
    accounts = {u.pk: u for u in users.objects.select_for_update().filter(pk__in=account_ids).order_by("pk")}
    list(Unit.objects.select_for_update().filter(kind=Unit.Kind.ASSOCIATION).order_by("pk").values_list("pk"))
    managed_ids = {p.pk for p in people if isinstance(p, ManagedPerson) and p.pk is not None}
    managed = {m.pk: m for m in ManagedPerson.objects.select_for_update().filter(pk__in=managed_ids).order_by("pk")}

    def fresh(person):
        if isinstance(person, ManagedPerson):
            return managed.get(person.pk, person)
        if isinstance(person, users):
            return accounts.get(person.pk, person)
        return person

    return [fresh(person) for person in people]


def copy_of(person) -> dict:
    """Die Angaben einer Person für ihren Eintrag in der Anmeldung, wie sie jetzt sind (A5)."""
    values = {"first_name": person.first_name, "last_name": person.last_name, "scout_name": person.scout_name}
    if isinstance(person, ManagedPerson):
        return {**values, "birth_date": person.birth_date, "managed": person}
    return {**values, "birth_date": None, "account": person}


def name_of(person) -> str:
    """Der Name eines Kontos oder einer verwalteten Person; bei einem Konto ohne Namen der Benutzername (#189, A12)."""
    return person.display_name or getattr(person, "username", "")
