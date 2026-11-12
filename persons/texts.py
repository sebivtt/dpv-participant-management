"""Texte zu verwalteten Personen (#117), übersetzbar (NFA-02).

Wortlaute aus dem Text von #117 und der Nachklärung nach dem Zielbild (N6, N7); nach außen heißt
es „Organisation“, nie „Einheit“ (#96).
"""

from django.utils.translation import gettext_lazy

# Knöpfe und Dialog (N6)
ADD_TITLE = gettext_lazy("Verwaltete Person anlegen")
ADD_BUTTON = gettext_lazy("Anlegen")
EDIT_BUTTON = gettext_lazy("Bearbeiten")
EDIT_TITLE = gettext_lazy("%(person)s bearbeiten")
SAVE_BUTTON = gettext_lazy("Speichern")
# Die Zeile unter dem Titel des Dialogs, wie im Zielbild.
IN_UNIT = gettext_lazy("in %(unit)s · ohne Konto, verwaltet")
MARK_MANAGED = gettext_lazy("verwaltet")

# Felder
FIRST_NAME = gettext_lazy("Vorname")
LAST_NAME = gettext_lazy("Nachname")
BIRTH_DATE = gettext_lazy("Geburtsdatum")
SCOUT_NAME = gettext_lazy("Fahrtenname")

# Fehler am Feld
FIRST_NAME_EMPTY = gettext_lazy("Bitte gib den Vornamen ein.")
LAST_NAME_EMPTY = gettext_lazy("Bitte gib den Nachnamen ein.")
BIRTH_DATE_EMPTY = gettext_lazy("Bitte gib das Geburtsdatum ein.")
FIRST_NAME_TOO_LONG = gettext_lazy("Der Vorname darf höchstens 100 Zeichen lang sein.")
LAST_NAME_TOO_LONG = gettext_lazy("Der Nachname darf höchstens 100 Zeichen lang sein.")
SCOUT_NAME_TOO_LONG = gettext_lazy("Der Fahrtenname darf höchstens 30 Zeichen lang sein.")
BIRTH_DATE_FUTURE = gettext_lazy("Das Geburtsdatum liegt in der Zukunft.")
BIRTH_DATE_TOO_OLD = gettext_lazy("Das Geburtsdatum liegt mehr als 120 Jahre zurück.")
BIRTH_DATE_INVALID = gettext_lazy("Bitte gib ein gültiges Geburtsdatum ein.")

# Kurze Meldungen und gleichzeitiges Bearbeiten
ADDED = gettext_lazy("%(person)s gehört jetzt zu %(unit)s.")
SAVED = gettext_lazy("Die Angaben zu %(person)s sind gespeichert.")
CHANGED_MEANWHILE = gettext_lazy(
    "%(person)s wurde inzwischen von jemand anderem geändert. Bitte prüfe die Angaben und speichere erneut."
)

# Regel beim Speichern
NOT_IN_FEDERATION = gettext_lazy("Eine verwaltete Person gehört zu einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie zum Verband.")

# Abschnitt „Personen“ ohne Personen (N7); der zweite Satz nur, wer dort anlegen darf.
NOBODY_YET = gettext_lazy("Dieser Organisation sind noch keine Personen zugeordnet.")
NOBODY_YET_ADD = gettext_lazy("Du kannst oben eine verwaltete Person anlegen oder eine bereits registrierte Person aufnehmen.")
