"""Datenmodell der Veranstaltungen (#100, TEAM-01; Uhrzeiten und Ort seit #379, Adresse des Orts seit #163, Zustand und
„Veröffentlicht“ seit #359, Einladungstext seit #358, Fristen seit #360) und Anmeldungen (#101, ANM-01, ANM-02)."""

from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Trim
from django.utils import timezone

from access.keys import KEY_LENGTH, key_field, new_key
from accounts.models import SCOUT_NAME_MAX_LENGTH, display_name
from core.models import ADDRESS_FIELDS, PostalAddress, address_constraints
from events import texts
from persons.models import ManagedPerson
from roles.models import LEADS_IN_UNITS, Role, RoleKind
from units.models import Unit

# Höchstens 100 Zeichen für den Namen, nach dem Entfernen der Leerzeichen am Rand (#100).
NAME_MAX_LENGTH = 100
# Höchstens 100 Zeichen für den Ort, ebenso ohne die Leerzeichen am Rand (#379, VER-04).
LOCATION_MAX_LENGTH = 100
# Höchstens 10.000 Zeichen sichtbarer Text im Einladungstext, ohne Formatierung gezählt (#358, Frage 5).
INVITATION_MAX_LENGTH = 10_000
# Die Angaben, die „Veranstaltung erstellen“ anlegt und der Stift der Kachel „Grunddaten“ ändert (#100, #379), seit #163
# mit der Adresse des Orts.
EDITABLE_FIELDS = ("name", "start", "start_time", "end", "end_time", "location", *ADDRESS_FIELDS)
# Die Fristen der Anmeldung (#360, VER-09), in dieser Reihenfolge; sie setzt der Stift der Kachel „Anmeldung“ und
# Schritt 3 beim Anlegen, nie ein Formular der Grunddaten.
DEADLINE_FIELDS = ("registration_opens", "registration_closes", "changes_close")
# Kopierte Namen: so lang wie bei Konten (Django: 150), damit jede Kopie passt; verwaltete Personen haben höchstens 50.
PERSON_NAME_MAX_LENGTH = 150


class Event(PostalAddress):
    """Eine Veranstaltung mit Name, Beginn und Ende, Ort und ihrer Veranstaltungsleitung (TEAM-01).

    Wer sie anlegt, ist ihre Veranstaltungsleitung; die Leitung kommt immer aus der Anmeldung, nie aus
    einem Formular (#100, VV3). In P2 hat jede Veranstaltung genau eine Leitung; weitere kommen mit
    TEAM-01 in P3, deshalb kann die Datenbank schon mehrere halten. Beginn und Ende sind Tage, je mit
    freiwilliger Uhrzeit; ohne Uhrzeit gilt der ganze Tag (#379, VER-02). Das Ende liegt nicht vor dem
    Beginn, am selben Tag auch nicht mit früherer Uhrzeit; das prüft auch die Datenbank. Der Ort ist eine
    freiwillige Bezeichnung (VER-04), dazu die freiwillige Adresse des Orts aus dem Baustein „Adressfeld“ (#163,
    `core.models.PostalAddress`). Gelesen und geändert wird eine
    Veranstaltung nur über die zentrale Rechteprüfung (`access/rights.py`).
    """

    # Zufällige Kennung für Adressen (#64).
    key = key_field()
    name = models.CharField(max_length=NAME_MAX_LENGTH)
    start = models.DateField()
    end = models.DateField()
    # Freiwillige Uhrzeiten (#379, VER-02); Veranstaltungen aus P2 haben keine.
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    # Bezeichnung des Orts, etwa „Burg Ludwigstein“; leer heißt ohne Ort (#379, VER-04).
    location = models.CharField(max_length=LOCATION_MAX_LENGTH, blank=True, default="")
    # Stand für gleichzeitiges Speichern: Ein älteres Fenster überschreibt nichts (#379, AG7, wie bei #117).
    version = models.PositiveIntegerField(default=1, editable=False)
    # Die Veranstaltungsleitung (TEAM-01). Setzt nur `Rights.create_event()` aus der Anmeldung.
    leads = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="led_events", editable=False)
    # Kennung des Formulars „Veranstaltung erstellen“: Ein zweites Abschicken desselben Formulars, etwa
    # ein Doppelklick, legt die Veranstaltung nicht ein zweites Mal an (VG8, wie MG7 aus #117).
    creation_key = models.CharField(max_length=KEY_LENGTH, unique=True, default=new_key, editable=False)
    # Wer die Veranstaltung gerade in Schritten anlegt (#380); leer, sobald das Anlegen mit „Veranstaltung
    # speichern“ oder „Entwurf speichern“ beendet ist, und bei Veranstaltungen von vor #380. Nur solange es gesetzt
    # ist, gibt es den Ablauf und „Entwurf löschen“, und nur für diese Person (VA-06). Ein Konto lässt sich nicht
    # löschen (EP-09), deshalb PROTECT wie bei der Ansprechperson einer Anmeldung.
    creating_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    editable=False, related_name="+")
    # Schalter „Veröffentlicht“ (#359, VER-07, VER-08; im Tool „Veröffentlicht“ statt „sichtbar“, #356 E2). Jede
    # Veranstaltung ist ein Entwurf, bis ihre Leitung sie veröffentlicht, auch alle aus P2 (ZG1). Setzt nur
    # `Rights.set_published()`, nie ein Formular der Grunddaten.
    published = models.BooleanField(default=False, editable=False)
    # Einladungstext (#358, VER-05): freiwillig, leer heißt „Noch kein Einladungstext.“, auch bei Veranstaltungen von
    # vor #358 (G6). Gespeichert wird nur, was `events.invitation.clean()` übrig lässt; das setzt nur
    # `Rights.edit_invitation()`, nie ein Formular der Grunddaten.
    invitation_text = models.TextField(blank=True, default="", editable=False)
    # Eigener Stand für gleichzeitiges Speichern des Einladungstexts (#358, G2), getrennt vom Stand der Grunddaten:
    # Wer in einem zweiten Fenster die Grunddaten ändert, ändert den Einladungstext nicht.
    invitation_version = models.PositiveIntegerField(default=1, editable=False)
    # Fristen der Anmeldung (#360, VER-09): je ein Tag, freiwillig, jede einzeln; leer heißt, die Anmeldung öffnet mit
    # dem Veröffentlichen, läuft bis zum Beginn, Nachmelden und Ändern gehen bis zum Beginn. Veranstaltungen von vor
    # #360 haben keine (FG8). Setzt nur `Rights.edit_deadlines()`, nie ein Formular der Grunddaten.
    registration_opens = models.DateField(null=True, blank=True, editable=False)
    registration_closes = models.DateField(null=True, blank=True, editable=False)
    changes_close = models.DateField(null=True, blank=True, editable=False)
    # Eigener Stand für gleichzeitiges Speichern der Fristen (#360, FG7), getrennt von Grunddaten und Einladungstext.
    deadlines_version = models.PositiveIntegerField(default=1, editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(name="") & Q(name=Trim("name")), name="event_name_trimmed_not_empty"),
            models.CheckConstraint(condition=Q(end__gte=F("start")), name="event_end_not_before_start"),
            # Am selben Tag liegt eine Uhrzeit des Endes nicht vor der des Beginns (#379, AG3).
            models.CheckConstraint(
                condition=Q(end__gt=F("start")) | Q(start_time__isnull=True) | Q(end_time__isnull=True)
                | Q(end_time__gte=F("start_time")),
                name="event_end_time_not_before_start_time"),
            models.CheckConstraint(condition=Q(location=Trim("location")), name="event_location_trimmed"),
            # Fristen (#360, VER-09): Anmeldestart ≤ Anmeldeschluss ≤ Änderungsschluss, ein Änderungsschluss nur mit
            # Anmeldeschluss, jede spätestens am Tag des Beginns (Frage 4); gleicher Tag ist erlaubt.
            models.CheckConstraint(
                condition=Q(registration_opens__isnull=True) | Q(registration_closes__isnull=True)
                | Q(registration_closes__gte=F("registration_opens")),
                name="event_registration_closes_not_before_opens"),
            models.CheckConstraint(
                condition=Q(changes_close__isnull=True)
                | (Q(registration_closes__isnull=False) & Q(changes_close__gte=F("registration_closes"))),
                name="event_changes_close_after_registration_closes"),
            *[models.CheckConstraint(condition=Q(**{f"{name}__isnull": True}) | Q(**{f"{name}__lte": F("start")}),
                                     name=f"event_{name}_not_after_start") for name in DEADLINE_FIELDS],
            *address_constraints("event"),
        ]

    def __str__(self) -> str:
        return self.name

    class Status(models.TextChoices):
        """Der Zustand im Lebenszyklus (#359, #356 N2); „Anmeldung offen“ und „Geschlossen“ ergänzt #360."""

        DRAFT = "entwurf", texts.STATE_DRAFT
        ANNOUNCED = "angekuendigt", texts.STATE_ANNOUNCED
        OPEN = "offen", texts.STATE_OPEN
        CLOSED = "geschlossen", texts.STATE_CLOSED
        RUNNING = "laeuft", texts.STATE_RUNNING
        ENDED = "beendet", texts.STATE_ENDED

    @property
    def days(self) -> int:
        """Die Dauer in Tagen, Beginn und Ende mitgezählt: 02.06. bis 05.06. sind 4 Tage (#379, Kachel „Grunddaten“)."""
        return (self.end - self.start).days + 1

    def begins_at(self) -> datetime:
        """Der Beginn als Zeitpunkt in der Zeit des Tools; ohne Uhrzeit um 0:00 des ersten Tags (#359)."""
        return timezone.make_aware(datetime.combine(self.start, self.start_time or time(0, 0)))

    def ends_at(self) -> datetime:
        """Das Ende als Zeitpunkt in der Zeit des Tools; ohne Uhrzeit um 0:00 nach dem letzten Tag (#359)."""
        if self.end_time is None:
            return timezone.make_aware(datetime.combine(self.end + timedelta(days=1), time(0, 0)))
        return timezone.make_aware(datetime.combine(self.end, self.end_time))

    def status_at(self, now: datetime) -> "Event.Status":
        """Der Zustand zum Zeitpunkt `now` (#359, seit #360 mit den Fristen): aus „Veröffentlicht“, Fristen, Beginn und Ende.

        Nicht veröffentlicht ist sie ein Entwurf, auch wenn der Zeitraum vorbei ist (#359, Frage 4); Fristen ändern daran
        nichts. Veröffentlicht vor dem Beginn ist sie „Angekündigt“, solange der Anmeldestart in der Zukunft liegt,
        „Geschlossen“ nach dem Anmeldeschluss und sonst „Anmeldung offen“: ohne Anmeldestart ab dem Veröffentlichen,
        ohne Anmeldeschluss bis zum Beginn (#360, Fragen 2, 3 und 3a). Ab Beginn bis vor dem Ende „Läuft“, ab dem Ende
        „Beendet“. Ein verschobener Anmeldeschluss öffnet die Anmeldung so von selbst wieder (VER-09).
        """
        if not self.published:
            return self.Status.DRAFT
        if now < self.begins_at():
            if self.registration_opens and now < day_begins(self.registration_opens):
                return self.Status.ANNOUNCED
            if self.registration_closes and now >= day_ends(self.registration_closes):
                return self.Status.CLOSED
            return self.Status.OPEN
        if now < self.ends_at():
            return self.Status.RUNNING
        return self.Status.ENDED

    @property
    def status(self) -> "Event.Status":
        """Der Zustand jetzt, nach der Uhr des Servers (`status_at()`)."""
        return self.status_at(timezone.now())

    def starts_before(self, now: datetime) -> bool:
        """Liegt der Beginn vor dem Tag von `now`? Dann lässt sie sich nicht veröffentlichen (VER-03, Frage 2).

        Heute ist immer erlaubt, gleich zu welcher Uhrzeit (Z9, wie #379).
        """
        return self.start < timezone.localtime(now).date()

    def changes_closed(self, now: datetime) -> bool:
        """Ist der Änderungsschluss zum Zeitpunkt `now` vorbei? Er gilt bis zum Ende seines Tags (#360, Frage 1)."""
        return self.changes_close is not None and now >= day_ends(self.changes_close)

    def registration_closed(self, now: datetime) -> bool:
        """Ist der Anmeldeschluss zum Zeitpunkt `now` vorbei? Er gilt bis zum Ende seines Tags (#360, Frage 1)."""
        return self.registration_closes is not None and now >= day_ends(self.registration_closes)

    def latest_deadline(self) -> date | None:
        """Die späteste eingetragene Frist; vor ihr darf der Beginn nicht liegen (#360, FG4)."""
        return max(filter(None, (getattr(self, name) for name in DEADLINE_FIELDS)), default=None)

    def has_begun(self, now: datetime) -> bool:
        """Hat sie zum Zeitpunkt `now` schon begonnen? Dann lässt sich die Veröffentlichung nicht zurücknehmen (Frage 3)."""
        return now >= self.begins_at()


def day_begins(day: date) -> datetime:
    """0:00 eines Tags in der Zeit des Tools (Deutschland), auch in der Sommerzeit: ab dann gilt ein Anmeldestart (#360)."""
    return timezone.make_aware(datetime.combine(day, time(0, 0)))


def day_ends(day: date) -> datetime:
    """0:00 des Tags danach in der Zeit des Tools: bis davor gelten Anmeldeschluss und Änderungsschluss (#360)."""
    return day_begins(day + timedelta(days=1))


def deadline_problems(start: date, values: dict) -> dict[str, str]:
    """Was an den Fristen in `values` nicht stimmt, je Feld der Satz dazu; leer, wenn alles passt (#360, Fragen 3 bis 5).

    Jede Frist ist freiwillig. Der Anmeldeschluss liegt nicht vor dem Anmeldestart, der Änderungsschluss nicht vor dem
    Anmeldeschluss und nur mit ihm (VER-09); gleicher Tag ist erlaubt. Jede Frist liegt spätestens am Tag des Beginns
    `start`. Fristen in der Vergangenheit sind erlaubt (Frage 5). Dieselbe Prüfung nutzen das Formular und, unter
    Sperre der Veranstaltung, `Rights.edit_deadlines()`; die Datenbank setzt dieselben Regeln durch.
    """
    opens, closes, changes = (values.get(name) for name in DEADLINE_FIELDS)
    problems = {}
    after_start = (texts.OPENS_AFTER_START, texts.CLOSES_AFTER_START, texts.CHANGES_AFTER_START)
    for name, value, text in zip(DEADLINE_FIELDS, (opens, closes, changes), after_start, strict=True):
        if value is not None and value > start:
            problems[name] = str(text)
    if opens and closes and closes < opens and "registration_closes" not in problems:
        problems["registration_closes"] = str(texts.CLOSES_BEFORE_OPENS)
    if changes and "changes_close" not in problems:
        if closes is None:
            problems["changes_close"] = str(texts.CHANGES_WITHOUT_CLOSES)
        elif changes < closes:
            problems["changes_close"] = str(texts.CHANGES_BEFORE_CLOSES)
    return problems


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
