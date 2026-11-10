"""Formulare der App „core“: das Beispielformular des Bausteinkatalogs (#176) und die Suche beim Benennen (#190) und Aufnehmen (#285)."""

from django import forms
from django.utils.translation import gettext_lazy as _


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
