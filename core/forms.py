"""Beispielformular für den Bausteinkatalog (#176): zeigt den Baustein Textfeld mit erfundenen Werten (#111)."""

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
