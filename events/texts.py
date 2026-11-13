"""Texte zu Veranstaltungen (#100), übersetzbar (NFA-02).

Wortlaute aus dem Text von #100 und den Szenarien vom 30.10.2026.
"""

from django.utils.translation import gettext_lazy

# Seitenleiste, Liste und Knöpfe
NAV = gettext_lazy("Veranstaltungen")
LIST_TITLE = gettext_lazy("Veranstaltungen, die du leitest")
NONE_YET = gettext_lazy("Du leitest noch keine Veranstaltung.")
CREATE_TITLE = gettext_lazy("Veranstaltung erstellen")
CREATE_BUTTON = gettext_lazy("Anlegen")
EDIT_TITLE = gettext_lazy("%(event)s bearbeiten")
SAVE_BUTTON = gettext_lazy("Speichern")
# Zeitraum in Liste und Seite; ein Tag steht ohne „bis“.
PERIOD = gettext_lazy("%(start)s bis %(end)s")

# Felder
NAME = gettext_lazy("Name")
START = gettext_lazy("Beginn")
END = gettext_lazy("Ende")

# Fehler am Feld
NAME_EMPTY = gettext_lazy("Bitte gib den Namen ein.")
NAME_TOO_LONG = gettext_lazy("Der Name darf höchstens 100 Zeichen lang sein.")
START_EMPTY = gettext_lazy("Bitte gib den Beginn ein.")
END_EMPTY = gettext_lazy("Bitte gib das Ende ein.")
DATE_INVALID = gettext_lazy("Bitte gib ein gültiges Datum ein.")
END_BEFORE_START = gettext_lazy("Das Ende liegt vor dem Beginn.")

# Kurze Meldungen (#186)
CREATED = gettext_lazy("%(event)s ist angelegt. Du leitest diese Veranstaltung.")
SAVED = gettext_lazy("Die Angaben zu %(event)s sind gespeichert.")
