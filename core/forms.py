"""Formulare der App „core“: das Beispielformular des Bausteinkatalogs (#176), die Suche beim Benennen (#190) und Aufnehmen (#285), der Name beim Anlegen und Bearbeiten einer Organisation (#95), die Angaben einer verwalteten Person (#117) und einer Veranstaltung (#100, #379)."""

from datetime import date, time

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.keycloak_abgleich import trimmed
from accounts.models import SCOUT_NAME_MAX_LENGTH
from events import texts as event_texts
from events.models import LOCATION_MAX_LENGTH
from events.models import NAME_MAX_LENGTH as EVENT_NAME_MAX_LENGTH
from persons import texts as person_texts
from persons.models import NAME_MAX_LENGTH
from units import texts as unit_texts

# Höchstlänge eines Namens wie im Datenmodell (units/models.py, Feld `name`).
UNIT_NAME_MAX_LENGTH = 100
# Wie weit ein Geburtsdatum höchstens zurückliegt (#117, Frage 5); eine Altersgrenze gibt es nicht (PER-02).
BIRTH_DATE_MAX_YEARS = 120


class PatternForm(forms.Form):
    """Ein Pflichtfeld mit Fehler am Feld und ein freiwilliges Feld; gespeichert wird nichts."""

    name = forms.CharField(
        label=_("Name der Veranstaltung"),
        error_messages={"required": _("Gib einen Namen für die Veranstaltung ein.")},
        widget=forms.TextInput(attrs={"autocomplete": "off", "autocapitalize": "sentences"}),
    )
    place = forms.CharField(
        label=_("Ort"),
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "autocapitalize": "words"}),
    )

    @classmethod
    def example(cls) -> "PatternForm":
        """Das Formular, wie es nach dem Abschicken ohne Namen aussieht: mit Fehler am Pflichtfeld."""
        form = cls(data={"name": "", "place": "Burg Rabenstein"})
        form.is_valid()
        return form


class AccountSearchForm(forms.Form):
    """Das Suchfeld im Dialog „… benennen“ (#190): Name, Fahrtenname, Mail oder Benutzername.

    Nimmt nur den Suchbegriff an; in welcher Organisation benannt wird, kommt aus der Adresse.
    Leerzeichen am Rand zählen nicht. Mails und Benutzernamen werden nicht korrigiert und
    nicht großgeschrieben, damit die genaue Suche am Handy trifft.
    """

    suche = forms.CharField(
        label=_("Name, Fahrtenname, Mail oder Benutzername"),
        required=False,
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "autofocus": True,
            }
        ),
    )


class FederationSearchForm(AccountSearchForm):
    """Das Suchfeld nur über Mail oder Benutzername, ohne Namen: im Dialog der Verbandsleitung (#94, Frage 4, PK-12) und in „Person aufnehmen“ (#285)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["suche"].label = _("Mail oder Benutzername")


class UnitNameForm(forms.Form):
    """Der Name im Dialog „… anlegen“ und „… bearbeiten“ (#95): Pflicht, höchstens 100 Zeichen, ohne Leerzeichen am Rand.

    Nimmt nur den Namen an; welche Organisation und welche Art, kommt aus der Adresse (OV1, OV4).
    Die Länge prüft erst der Server, wie beim Fahrtennamen: Ein `maxlength` schnitte beim Einfügen
    still ab. Das Feld gehört über sein Attribut „form“ zum Formular des Knopfs im Dialog, damit
    Enter und der Knopf denselben Namen schicken. Am Handy Großbuchstabe am Wortanfang, ohne Korrektur.
    """

    name = forms.CharField(
        label=unit_texts.NAME_LABEL,
        error_messages={"required": unit_texts.NAME_EMPTY},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "words",
                "autocorrect": "off",
                "spellcheck": "false",
                "autofocus": True,
                "form": "f-dialog",
                "data-hoechstens": UNIT_NAME_MAX_LENGTH,
                "data-zu-lang": unit_texts.NAME_TOO_LONG,
            }
        ),
    )

    def clean_name(self) -> str:
        value = self.cleaned_data["name"]
        if len(value) > UNIT_NAME_MAX_LENGTH:
            raise forms.ValidationError(unit_texts.NAME_TOO_LONG, code="max_length")
        return value


def _name_field(label, empty) -> forms.CharField:
    """Vor- oder Nachname im Dialog einer verwalteten Person: Pflicht, die Länge prüft erst `clean_…()`."""
    return forms.CharField(
        label=label,
        strip=False,
        error_messages={"required": empty},
        widget=forms.TextInput(
            attrs={
                # Ein Name: Großbuchstabe am Wortanfang, keine Korrektur in ein bekanntes Wort.
                "autocomplete": "off",
                "autocapitalize": "words",
                "autocorrect": "off",
                "spellcheck": "false",
                "form": "f-dialog",
                "data-hoechstens": NAME_MAX_LENGTH,
            }
        ),
    )


class ManagedPersonForm(forms.Form):
    """Die vier Angaben im Dialog „Verwaltete Person anlegen“ und „… bearbeiten“ (#117, PER-02).

    Vor- und Nachname sind Pflicht, höchstens 50 Zeichen (#330); das Geburtsdatum ist Pflicht, liegt nicht
    in der Zukunft und höchstens 120 Jahre zurück; der Fahrtenname ist freiwillig, höchstens 30
    Zeichen (#214). Leerzeichen am Rand zählen wie beim Fahrtennamen auch in unsichtbarer Form nicht
    (`trimmed()`, #77); nur Leerzeichen gilt als leer. Die Längen prüft erst der Server, damit beim
    Einfügen nichts still abgeschnitten wird. Das Formular nimmt nur diese vier Angaben an: In welcher
    Organisation, kommt aus der Adresse (MV4), und Gesundheitsangaben gibt es nicht (FRM-04, MV6).
    Alle Felder gehören über ihr Attribut „form“ zum Formular des Knopfs im Dialog.
    """

    first_name = _name_field(person_texts.FIRST_NAME, person_texts.FIRST_NAME_EMPTY)
    last_name = _name_field(person_texts.LAST_NAME, person_texts.LAST_NAME_EMPTY)
    birth_date = forms.DateField(
        label=person_texts.BIRTH_DATE,
        # Das Datumsfeld des Browsers schickt immer diese Form, egal wie es das Datum anzeigt (N3).
        input_formats=["%Y-%m-%d"],
        error_messages={"required": person_texts.BIRTH_DATE_EMPTY, "invalid": person_texts.BIRTH_DATE_INVALID},
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "autocomplete": "off", "form": "f-dialog"}),
    )
    scout_name = forms.CharField(
        label=person_texts.SCOUT_NAME,
        required=False,
        strip=False,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "words",
                "autocorrect": "off",
                "spellcheck": "false",
                "form": "f-dialog",
                "data-hoechstens": SCOUT_NAME_MAX_LENGTH,
                "data-zu-lang": person_texts.SCOUT_NAME_TOO_LONG,
            }
        ),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update(autofocus=True, **{"data-zu-lang": person_texts.FIRST_NAME_TOO_LONG})
        self.fields["last_name"].widget.attrs["data-zu-lang"] = person_texts.LAST_NAME_TOO_LONG
        # Tage in der Zukunft lässt das Datumsfeld des Browsers gar nicht erst wählen; geprüft wird trotzdem unten.
        self.fields["birth_date"].widget.attrs["max"] = timezone.localdate().isoformat()

    def _name(self, field: str, too_long) -> str:
        value = trimmed(self.cleaned_data[field])
        if not value:
            raise forms.ValidationError(self.fields[field].error_messages["required"], code="required")
        if len(value) > NAME_MAX_LENGTH:
            raise forms.ValidationError(too_long, code="max_length")
        return value

    def clean_first_name(self) -> str:
        return self._name("first_name", person_texts.FIRST_NAME_TOO_LONG)

    def clean_last_name(self) -> str:
        return self._name("last_name", person_texts.LAST_NAME_TOO_LONG)

    def clean_birth_date(self) -> date:
        """Nicht in der Zukunft, höchstens 120 Jahre zurück: am 28.10.2026 geht der 28.10.1906, der 27.10.1906 nicht (MG4)."""
        value = self.cleaned_data["birth_date"]
        today = timezone.localdate()
        if value > today:
            raise forms.ValidationError(person_texts.BIRTH_DATE_FUTURE, code="future")
        try:
            oldest = today.replace(year=today.year - BIRTH_DATE_MAX_YEARS)
        except ValueError:
            # Heute ist der 29. Februar, den es vor 120 Jahren nicht gab: Die Grenze ist dann der 1. März.
            oldest = date(today.year - BIRTH_DATE_MAX_YEARS, 3, 1)
        if value < oldest:
            raise forms.ValidationError(person_texts.BIRTH_DATE_TOO_OLD, code="too_old")
        return value

    def clean_scout_name(self) -> str:
        value = trimmed(self.cleaned_data["scout_name"])
        if len(value) > SCOUT_NAME_MAX_LENGTH:
            raise forms.ValidationError(person_texts.SCOUT_NAME_TOO_LONG, code="max_length")
        return value


class ManagedPersonAddForm(ManagedPersonForm):
    """Der Dialog „Verwaltete Person anlegen“: die vier Angaben und der Regler der Einwilligung (#98, DSG-02).

    Der Regler ist Pflicht und steht beim Öffnen immer auf „aus“ (N2): Ohne ihn wird niemand angelegt,
    auch nicht über ein manipuliertes Formular. Welches Konto wann bestätigt hat, nimmt das Formular
    nicht an; das setzt `Rights.add_managed()` aus der Anmeldung und der Uhr des Servers. Beim Bearbeiten
    gibt es den Regler nicht (`ManagedPersonForm`), eine mitgeschickte Bestätigung zählt dort nicht.
    """

    consent = forms.BooleanField(
        label=person_texts.CONSENT,
        error_messages={"required": person_texts.CONSENT_MISSING},
        widget=forms.CheckboxInput(attrs={"form": "f-dialog", "value": "an"}),
    )


# Vorausgefüllte Uhrzeiten beim Anlegen, wie „Freitag 18:00 bis Sonntag 12:00“ in VER-02 (#379).
START_TIME_DEFAULT = time(18, 0)
END_TIME_DEFAULT = time(12, 0)
# Ab so vielen Tagen fragt das Tool nach, ob die Dauer stimmt: „über 4 Wochen“ (VER-03, Frage 3 aus #29).
DURATION_QUESTION_DAYS = 29


def _event_date(label, empty) -> forms.DateField:
    """Beginn oder Ende einer Veranstaltung: Pflicht, ein Tag, im Baustein „Datumsfeld“ (#117, N3)."""
    return forms.DateField(
        label=label,
        # Das Datumsfeld des Browsers schickt immer diese Form, egal wie es das Datum anzeigt (N3 zu #117).
        input_formats=["%Y-%m-%d"],
        error_messages={"required": empty, "invalid": event_texts.DATE_INVALID},
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", "autocomplete": "off", "form": "f-dialog"}),
    )


def _event_time(label) -> forms.TimeField:
    """Uhrzeit zu Beginn oder Ende: freiwillig, im Baustein „Datumsfeld“ rechts neben dem Datum (#379, VER-02)."""
    return forms.TimeField(
        label=label,
        required=False,
        # Das Uhrzeitfeld des Browsers schickt „18:00“, manche mit Sekunden; angezeigt wird wie überall „18:00“.
        input_formats=["%H:%M", "%H:%M:%S"],
        error_messages={"invalid": event_texts.TIME_INVALID},
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time", "autocomplete": "off", "form": "f-dialog"}),
    )


class EventForm(forms.Form):
    """Die Angaben in „Veranstaltung erstellen“ und im Dialog des Stifts der Kachel „Grunddaten“ (#100, #379).

    Der Name ist Pflicht, höchstens 100 Zeichen; Leerzeichen am Rand zählen wie bei #77 auch in unsichtbarer
    Form nicht (`trimmed()`), nur Leerzeichen gilt als leer. Die Länge prüft erst der Server, damit beim Einfügen
    nichts still abgeschnitten wird. Gleiche Namen sind erlaubt (VG7). Beginn und Ende sind Pflicht, ihre
    Uhrzeiten freiwillig (VER-02); ohne Uhrzeit gilt der ganze Tag. Der Ort ist freiwillig, höchstens 100
    Zeichen, nur Leerzeichen gilt als leer (VER-04). Das Formular nimmt nur diese Angaben an: Wer die
    Veranstaltung leitet, kommt aus der Anmeldung (VV3). Alle Felder gehören über ihr Attribut „form“ zum
    Formular des Knopfs im Dialog.

    Prüfungen nach VER-03 (Fragen 2 und 3 aus #29), beim Anlegen und beim Bearbeiten; `before` ist beim
    Bearbeiten die Veranstaltung, wie sie gespeichert ist:

    - Das Ende liegt nie vor dem Beginn, am selben Tag auch nicht mit früherer Uhrzeit (AG3).
    - Der Beginn liegt nicht vor dem heutigen Tag; heute ist zu jeder Uhrzeit erlaubt. Geprüft wird nur, wenn
      der Beginn (Tag oder Uhrzeit) eingegeben oder geändert wird; bei einer laufenden Veranstaltung blockiert
      das Ändern von Name oder Ende nicht (AG1, AG2).
    - Ab 29 Tagen, gezählt wie in der Kachel, fragt es nach, ob die Dauer stimmt, wenn Beginn oder Ende
      eingegeben oder geändert werden (AG4). Bestätigt ist erst, wenn „Ja, die Dauer stimmt“ für genau diese
      Zahl an Tagen angetippt ist; nach einer anderen Dauer kommt die Frage neu, mit Schalter auf „aus“.
    """

    name = forms.CharField(
        label=event_texts.NAME,
        strip=False,
        error_messages={"required": event_texts.NAME_EMPTY},
        widget=forms.TextInput(
            attrs={
                # Ein Name wie „Probelager 2027“: Großbuchstabe am Satzanfang, keine Korrektur in ein bekanntes Wort.
                "autocomplete": "off",
                "autocapitalize": "sentences",
                "autocorrect": "off",
                "spellcheck": "false",
                "autofocus": True,
                "form": "f-dialog",
                "data-hoechstens": EVENT_NAME_MAX_LENGTH,
                "data-zu-lang": event_texts.NAME_TOO_LONG,
            }
        ),
    )
    start = _event_date(event_texts.START, event_texts.START_EMPTY)
    start_time = _event_time(event_texts.START_TIME)
    end = _event_date(event_texts.END, event_texts.END_EMPTY)
    end_time = _event_time(event_texts.END_TIME)
    location = forms.CharField(
        label=event_texts.LOCATION,
        required=False,
        strip=False,
        widget=forms.TextInput(
            attrs={
                # Eine Bezeichnung wie „Burg Ludwigstein“: wie beim Namen, ohne Korrektur in ein bekanntes Wort.
                "autocomplete": "off",
                "autocapitalize": "sentences",
                "autocorrect": "off",
                "spellcheck": "false",
                "form": "f-dialog",
                "data-hoechstens": LOCATION_MAX_LENGTH,
                "data-zu-lang": event_texts.LOCATION_TOO_LONG,
            }
        ),
    )
    # Steht nur da, wenn die Nachfrage zur Dauer kommt (Baustein „Schalter“, #379); sein Wert ist die Zahl der Tage.
    duration_ok = forms.BooleanField(
        label=event_texts.DURATION_OK,
        required=False,
        widget=forms.CheckboxInput(attrs={"form": "f-dialog"}),
    )

    def __init__(self, *args, before=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.before = before
        # Die Zahl der Tage, nach der das Tool gerade fragt; 0 heißt: keine Nachfrage, kein Schalter.
        self.duration_question = 0

    @classmethod
    def for_create(cls) -> "EventForm":
        """Das leere Formular „Veranstaltung erstellen“: Tage leer, Uhrzeiten 18:00 und 12:00 (VER-02, A4)."""
        return cls(initial={"start_time": START_TIME_DEFAULT, "end_time": END_TIME_DEFAULT})

    def clean_name(self) -> str:
        value = trimmed(self.cleaned_data["name"])
        if not value:
            raise forms.ValidationError(event_texts.NAME_EMPTY, code="required")
        if len(value) > EVENT_NAME_MAX_LENGTH:
            raise forms.ValidationError(event_texts.NAME_TOO_LONG, code="max_length")
        return value

    def clean_location(self) -> str:
        value = trimmed(self.cleaned_data["location"])
        if len(value) > LOCATION_MAX_LENGTH:
            raise forms.ValidationError(event_texts.LOCATION_TOO_LONG, code="max_length")
        return value

    def clean(self) -> dict:
        """Ende vor Beginn, Beginn vor heute und die Nachfrage zur Dauer; die Fehler stehen am Feld (VER-03)."""
        cleaned = super().clean()
        start, end = cleaned.get("start"), cleaned.get("end")
        if start is not None and start < timezone.localdate() and self._changed("start", "start_time"):
            self.add_error("start", forms.ValidationError(event_texts.START_IN_PAST, code="in_past"))
        if start is None or end is None:
            return cleaned
        start_time, end_time = cleaned.get("start_time"), cleaned.get("end_time")
        if end < start or (end == start and start_time and end_time and end_time < start_time):
            self.add_error("end", forms.ValidationError(event_texts.END_BEFORE_START, code="before_start"))
            return cleaned
        days = (end - start).days + 1
        # Ist der Beginn ohnehin falsch, fragt das Tool noch nicht nach der Dauer; erst muss der Beginn stimmen.
        if "start" not in self.errors and days >= DURATION_QUESTION_DAYS and self._changed("start", "start_time", "end", "end_time"):
            self._ask_duration(days)
        return cleaned

    def _changed(self, *names) -> bool:
        """Sind diese Angaben neu eingegeben (beim Anlegen) oder anders als gespeichert (beim Bearbeiten)?"""
        if self.before is None:
            return True
        return any(self.cleaned_data.get(name) != getattr(self.before, name) for name in names)

    def _ask_duration(self, days: int) -> None:
        """Fragt nach, ob `days` Tage stimmen; bestätigt ist nur der Schalter mit genau dieser Zahl (AG4)."""
        self.duration_question = days
        name = self.add_prefix("duration_ok")
        self.fields["duration_ok"].widget.attrs["value"] = str(days)
        if self.data.get(name) == str(days):
            return
        # Eine Bestätigung für eine andere Dauer zählt nicht; der Schalter steht dann wieder auf „aus“.
        if name in self.data:
            self.data = self.data.copy()
            self.data.pop(name)
        self.add_error("end", forms.ValidationError(event_texts.DURATION_QUESTION % {"count": days},
                                                    code="duration"))
