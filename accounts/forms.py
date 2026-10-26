"""Formulare rund um das eigene Konto: der Fahrtenname auf „Mein Profil“ (#111)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from accounts import texts
from accounts.keycloak_abgleich import trimmed
from accounts.models import SCOUT_NAME_MAX_LENGTH


class ScoutNameForm(forms.Form):
    """Der eigene Fahrtenname: freiwillig, höchstens 50 Zeichen, Leerzeichen am Rand entfernt.

    Das Formular nimmt nur den Fahrtennamen an. Wessen Konto es ändert, bestimmt allein die
    Anmeldung, nie ein Feld der Anfrage (EP-04). Leerzeichen am Rand zählen wie beim Namen
    aus Keycloak auch in unsichtbarer Form (`trimmed()`, #77); was danach leer ist, gilt als
    kein Fahrtenname. Die Länge prüft erst der Server: Ein `maxlength` im Feld schnitte beim
    Einfügen still ab, statt den Fehler am Feld zu zeigen.
    """

    scout_name = forms.CharField(
        label=_("Fahrtenname"),
        required=False,
        strip=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Noch nicht angegeben"),
                # Ein Name: Großbuchstabe am Wortanfang, keine Korrektur in ein bekanntes Wort.
                "autocomplete": "nickname",
                "autocapitalize": "words",
                "autocorrect": "off",
                "spellcheck": "false",
            }
        ),
    )

    def clean_scout_name(self) -> str:
        value = trimmed(self.cleaned_data["scout_name"])
        if len(value) > SCOUT_NAME_MAX_LENGTH:
            raise forms.ValidationError(texts.SCOUT_NAME_TOO_LONG, code="max_length")
        return value
