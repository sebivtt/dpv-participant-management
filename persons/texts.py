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

# Bestätigung der Einwilligung (#98): genau der Satz aus DSG-02, ohne Hilfesatz (Klärung vom 22.10.2026, Frage 2).
CONSENT = gettext_lazy(
    "Die Person bzw. bei Minderjährigen die Erziehungsberechtigten haben der Speicherung der Daten zugestimmt."
)
CONSENT_MISSING = gettext_lazy("Bitte bestätige die Einwilligung. Ohne sie wird die Person nicht gespeichert.")

# Kurze Meldungen und gleichzeitiges Bearbeiten
ADDED = gettext_lazy("%(person)s gehört jetzt zu %(unit)s.")
SAVED = gettext_lazy("Die Angaben zu %(person)s sind gespeichert.")
CHANGED_MEANWHILE = gettext_lazy(
    "%(person)s wurde inzwischen von jemand anderem geändert. Bitte prüfe die Angaben und speichere erneut."
)

# Löschen im Dialog „Bearbeiten“ (#118, Zielbild zu #117, Fassung 1, N5); Verschieben und Austragen
# nutzen dieselben Sätze wie bei Personen mit Konto (units/texts.py, #286, #287).
DELETE_BUTTON = gettext_lazy("Verwaltete Person löschen")
DELETE_QUESTION = gettext_lazy("%(person)s endgültig löschen?")
DELETE_CANNOT_UNDO = gettext_lazy("Das lässt sich nicht rückgängig machen.")
DELETE_CONFIRM = gettext_lazy("Endgültig löschen")
DELETE_KEEP = gettext_lazy("Nicht löschen")
DELETED = gettext_lazy("%(person)s wurde gelöscht.")

# Regel beim Speichern
NOT_IN_FEDERATION = gettext_lazy("Eine verwaltete Person gehört zu einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie zum Verband.")

# Abschnitt „Personen“ ohne Personen (N7); der zweite Satz nur, wer dort anlegen darf.
NOBODY_YET = gettext_lazy("Dieser Organisation sind noch keine Personen zugeordnet.")
NOBODY_YET_ADD = gettext_lazy("Du kannst oben eine verwaltete Person anlegen oder eine bereits registrierte Person aufnehmen.")

# Angezeigte Leitungsrollen (#99, PER-07), Wortlaut nach dem Text von #99 und den Szenarien vom 11.11.2026.
# Eintragen, „schon …“, Entfernen und die Ablehnung beim Verschieben nutzen die Sätze für Leitungen mit
# Konto (units/texts.py, #190, #191, PK-25).
DISPLAYED_HINT = gettext_lazy("%(person)s hat kein Konto. Die Rolle wird nur angezeigt und gibt keine Rechte.")
# Im Abschnitt „Personen“ unter dem Namen; in der Liste der Leitungen steht „ohne Konto, nur Anzeige“ in der Vorlage.
DISPLAYED_ROLE_AT = gettext_lazy("%(role)s %(unit)s (nur Anzeige)")
DISPLAYED_OFF_PATH = gettext_lazy(
    "%(person)s gehört zu %(unit)s und kann deshalb keine Leitung bei %(target)s sein."
)
# Nur am Tool vorbei möglich: Das Tool bietet keine falsche Ebene an und ändert keine gespeicherte Rolle.
DISPLAYED_WRONG_LEVEL = gettext_lazy("Diese Leitungsrolle passt nicht zur Ebene der Organisation.")
DISPLAYED_FIXED = gettext_lazy("Eine angezeigte Leitungsrolle lässt sich nicht ändern, nur entfernen und neu eintragen.")
