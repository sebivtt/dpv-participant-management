"""Formulare der App „core“: das Beispielformular des Bausteinkatalogs (#176), die Suche beim Benennen (#190) und Aufnehmen (#285) und der Name beim Anlegen und Umbenennen (#95)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from units import texts as unit_texts
# Höchstlänge eines Namens wie im Datenmodell (units/models.py, Feld `name`).
UNIT_NAME_MAX_LENGTH = 100


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
    """Der Name im Dialog „… anlegen“ und „Umbenennen“ (#95): Pflicht, höchstens 100 Zeichen, ohne Leerzeichen am Rand.

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
