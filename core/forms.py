"""Formulare der App „core“: das Beispielformular des Bausteinkatalogs (#176), die Suche beim Benennen (#190) und Aufnehmen (#285), der Name beim Anlegen und Bearbeiten einer Organisation (#95), die Angaben einer verwalteten Person (#117) und einer Veranstaltung (#100, #379), die Adresse aus dem Baustein „Adressfeld“ (#163)."""

import re
from datetime import date, time
from decimal import Decimal, InvalidOperation

from django import forms
from django.core import signing
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.keycloak_abgleich import trimmed
from accounts.models import SCOUT_NAME_MAX_LENGTH
from core import address_texts
from core.countries import COUNTRIES
from core.models import CITY_MAX_LENGTH, GERMANY, POSTAL_CODE_MAX_LENGTH, STATES, STREET_MAX_LENGTH
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


def _whole_minute(value):
    """Eine Uhrzeit ohne Sekunden: Der Dialog zeigt nur Stunde und Minute, sonst gälte der Beginn später als geändert.

    Unabhängige Prüfung, V1: Kommt „10:00:30“ am Browser vorbei, zeigt der Dialog „10:00“; beim nächsten Speichern
    sähe das wie ein geänderter Beginn aus, und bei einer laufenden Veranstaltung käme „… in der Vergangenheit“.
    """
    return value.replace(second=0, microsecond=0) if value else value


# Ein Treffer der Adresssuche reist als signierter Text mit: im Knopf „Übernehmen“ und danach versteckt im Formular
# („coordinates“). So kommen Koordinaten nur aus einem Treffer, den der Server gefunden hat (#163, A4).
PLACE_SALT = "adressfeld.treffer"
PLACE_PARTS = ("street", "postal_code", "city", "state", "country")
# Nur die Ziffern 0 bis 9; `\d` nähme auch andere Schriften an, etwa „９９９９９“ (Befund B3 der unabhängigen Prüfung).
GERMAN_POSTAL_CODE = re.compile(r"[0-9]{5}")


def place_token(values: dict) -> str:
    """Der signierte Text zu einer Adresse mit Koordinaten: die Teile aus `PLACE_PARTS`, `latitude` und `longitude`."""
    # Ohne Zeitstempel: Derselbe Treffer ergibt immer denselben Text, die Seite also dieselbe Antwort (#156).
    return signing.Signer(salt=PLACE_SALT).sign_object(
        {name: str(values.get(name) or "") for name in (*PLACE_PARTS, "latitude", "longitude")}, compress=True)


def place_from_token(token: str) -> dict | None:
    """Die Adresse mit Koordinaten aus einem signierten Text; verändert oder in falscher Form None."""
    try:
        values = signing.Signer(salt=PLACE_SALT).unsign_object(token or "")
    except signing.BadSignature:
        return None
    if not isinstance(values, dict) or not all(isinstance(values.get(name), str)
                                               for name in (*PLACE_PARTS, "latitude", "longitude")):
        return None
    return values


def _coordinate(text: str, limit: int) -> Decimal | None:
    """Eine Koordinate mit sieben Stellen nach dem Komma, oder None, wenn sie keine ist."""
    try:
        value = Decimal(text).quantize(Decimal("0.0000001"))
    except (InvalidOperation, ValueError):
        return None
    return value if value.is_finite() and -limit <= value <= limit else None


def _address_text(label, too_long, limit: int, counted: bool, **attrs) -> forms.CharField:
    """Ein Textfeld des Adressfelds, freiwillig; ob es Pflicht ist, entscheidet `AddressForm.clean()`."""
    widget_attrs = {"autocomplete": "off", "autocorrect": "off", "spellcheck": "false", **attrs}
    if counted:
        # Die Zahl der Zeichen beim Tippen wie beim Ort der Veranstaltung (#215); bei der kurzen PLZ nicht.
        widget_attrs.update({"data-hoechstens": limit, "data-zu-lang": too_long})
    return forms.CharField(label=label, required=False, strip=False, widget=forms.TextInput(attrs=widget_attrs))


class AddressForm(forms.Form):
    """Die Felder des Bausteins „Adressfeld“ (#163): Straße und Hausnummer, PLZ, Ort, Bundesland und Land.

    Die Adresse ist freiwillig. Sobald etwas eingetragen ist (das vorgewählte Land Deutschland allein zählt nicht),
    sind PLZ und Ort Pflicht; in Deutschland hat die PLZ 5 Ziffern (G4, G5). Leerzeichen am Rand zählen nicht. Bei
    einem anderen Land wird kein Bundesland gespeichert (G7). Ohne Eintrag sind alle Teile leer, auch das Land.
    Koordinaten gibt es nur aus einem übernommenen Treffer der Adresssuche, versteckt als `coordinates`; passt die
    Adresse beim Speichern nicht mehr genau zum Treffer, fallen sie weg (A4). `cleaned_data` enthält danach alle Felder
    aus `core.models.ADDRESS_FIELDS`. Ein Formular mit Adresse erbt von dieser Klasse.
    """

    street = _address_text(address_texts.STREET, address_texts.STREET_TOO_LONG, STREET_MAX_LENGTH, True,
                           autocapitalize="sentences")
    postal_code = _address_text(address_texts.POSTAL_CODE, address_texts.POSTAL_CODE_TOO_LONG, POSTAL_CODE_MAX_LENGTH,
                                False, autocapitalize="characters")
    city = _address_text(address_texts.CITY, address_texts.CITY_TOO_LONG, CITY_MAX_LENGTH, True,
                         autocapitalize="words")
    state = forms.ChoiceField(label=address_texts.STATE, required=False,
                              choices=[("", address_texts.CHOOSE), *STATES])
    country = forms.ChoiceField(label=address_texts.COUNTRY, required=False, choices=COUNTRIES, initial=GERMANY)
    coordinates = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean(self) -> dict:
        cleaned = super().clean()
        if not all(name in cleaned for name in PLACE_PARTS):
            # Ein Feld ist schon falsch (etwa ein Land, das es nicht gibt); der Fehler steht dort.
            return cleaned
        street, postal_code, city = (trimmed(cleaned[name]) for name in ("street", "postal_code", "city"))
        country = cleaned["country"] or GERMANY
        state = cleaned["state"] if country == GERMANY else ""
        cleaned.update(latitude=None, longitude=None)
        if not (street or postal_code or city or state) and country == GERMANY:
            cleaned.update(street="", postal_code="", city="", state="", country="")
            return cleaned
        cleaned.update(street=street, postal_code=postal_code, city=city, state=state, country=country)
        for name, value, limit, too_long in (
            ("street", street, STREET_MAX_LENGTH, address_texts.STREET_TOO_LONG),
            ("postal_code", postal_code, POSTAL_CODE_MAX_LENGTH, address_texts.POSTAL_CODE_TOO_LONG),
            ("city", city, CITY_MAX_LENGTH, address_texts.CITY_TOO_LONG),
        ):
            if len(value) > limit:
                self.add_error(name, forms.ValidationError(too_long, code="max_length"))
        if not postal_code:
            self.add_error("postal_code", forms.ValidationError(address_texts.POSTAL_CODE_EMPTY, code="required"))
        elif country == GERMANY and not GERMAN_POSTAL_CODE.fullmatch(postal_code):
            self.add_error("postal_code", forms.ValidationError(address_texts.FIVE_DIGITS, code="five_digits"))
        if not city:
            self.add_error("city", forms.ValidationError(address_texts.CITY_EMPTY, code="required"))
        place = place_from_token(cleaned.get("coordinates", ""))
        if place and all(place[name] == cleaned[name] for name in PLACE_PARTS):
            latitude, longitude = _coordinate(place["latitude"], 90), _coordinate(place["longitude"], 180)
            if latitude is not None and longitude is not None:
                cleaned.update(latitude=latitude, longitude=longitude)
        return cleaned


def address_initial(entry) -> dict:
    """Die Felder des Adressfelds mit der gespeicherten Adresse, ohne Adresse mit „Deutschland“ vorgewählt (#163)."""
    values = {name: getattr(entry, name) for name in PLACE_PARTS}
    values["country"] = values["country"] or GERMANY
    if entry.latitude is not None:
        values["coordinates"] = place_token({**values, "latitude": entry.latitude, "longitude": entry.longitude})
    return values


class EventForm(AddressForm):
    """Die Angaben in „Veranstaltung erstellen“ und im Dialog des Stifts der Kachel „Grunddaten“ (#100, #379).

    Der Name ist Pflicht, höchstens 100 Zeichen; Leerzeichen am Rand zählen wie bei #77 auch in unsichtbarer
    Form nicht (`trimmed()`), nur Leerzeichen gilt als leer. Die Länge prüft erst der Server, damit beim Einfügen
    nichts still abgeschnitten wird. Gleiche Namen sind erlaubt (VG7). Beginn und Ende sind Pflicht, ihre
    Uhrzeiten freiwillig (VER-02); ohne Uhrzeit gilt der ganze Tag. Der Ort ist freiwillig, höchstens 100
    Zeichen, nur Leerzeichen gilt als leer (VER-04). Das Formular nimmt nur diese Angaben an: Wer die
    Veranstaltung leitet, kommt aus der Anmeldung (VV3). Alle Felder gehören über ihr Attribut „form“ zum
    Formular des Knopfs im Dialog; in Schritt 1 beim Anlegen (#380) zum Formular des Schritts (`form_id`).

    Dazu seit #163 die freiwillige Adresse des Orts aus dem Baustein „Adressfeld“ (`AddressForm`).

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

    def __init__(self, *args, before=None, form_id: str = "f-dialog", **kwargs):
        super().__init__(*args, **kwargs)
        self.before = before
        for field in self.fields.values():
            field.widget.attrs["form"] = form_id
        # Die Zahl der Tage, nach der das Tool gerade fragt; 0 heißt: keine Nachfrage, kein Schalter.
        self.duration_question = 0

    @classmethod
    def for_create(cls, **kwargs) -> "EventForm":
        """Das leere Formular „Veranstaltung erstellen“: Tage leer, Uhrzeiten 18:00 und 12:00 (VER-02, A4)."""
        return cls(initial={"start_time": START_TIME_DEFAULT, "end_time": END_TIME_DEFAULT, "country": GERMANY}, **kwargs)

    def clean_name(self) -> str:
        value = trimmed(self.cleaned_data["name"])
        if not value:
            raise forms.ValidationError(event_texts.NAME_EMPTY, code="required")
        if len(value) > EVENT_NAME_MAX_LENGTH:
            raise forms.ValidationError(event_texts.NAME_TOO_LONG, code="max_length")
        return value

    def clean_start_time(self):
        return _whole_minute(self.cleaned_data["start_time"])

    def clean_end_time(self):
        return _whole_minute(self.cleaned_data["end_time"])

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
