"""Texte zu Veranstaltungen (#100, #379) und Anmeldungen (#101), übersetzbar (NFA-02).

Wortlaute aus dem Text von #100 und den Szenarien vom 30.10.2026, für Anmeldungen aus den Szenarien zu #101 vom
15.11.2026, für Uhrzeiten, Ort, Prüfungen und Leitungsseite aus dem Text von #379 und seinen Szenarien vom
17.11.2026, für das Anlegen in Schritten aus dem Text von #380 und seinen Szenarien vom 17.11.2026.
"""

from django.utils.translation import gettext_lazy, ngettext_lazy

# Seitenleiste, Liste und Knöpfe
NAV = gettext_lazy("Veranstaltungen")
LIST_TITLE = gettext_lazy("Von mir geleitet")
NONE_YET = gettext_lazy("Du leitest noch keine Veranstaltung.")
CREATE_TITLE = gettext_lazy("Veranstaltung erstellen")
EDIT_TITLE = gettext_lazy("%(event)s bearbeiten")
SAVE_BUTTON = gettext_lazy("Speichern")
# Zeitraum in Liste und Seite; ein Tag steht ohne „bis“.
PERIOD = gettext_lazy("%(start)s bis %(end)s")
# Ein Tag mit Uhrzeit in der Liste „Von mir geleitet“: „02.06.2028, 18:00“ (#379, A5).
DAY_WITH_TIME = gettext_lazy("%(day)s, %(time)s")
# Hinter dem Zeitraum der Ort, im Kopf der Leitungsseite und in der Liste (#379, A2, A5).
WITH_LOCATION = gettext_lazy("%(period)s · %(location)s")

# Leitungsseite (#379): Kachel „Grunddaten“ mit Kalenderblättern
BASICS = gettext_lazy("Grunddaten")
BASICS_EDIT = gettext_lazy("Grunddaten bearbeiten")
SHEET_START = gettext_lazy("Beginn:")
SHEET_END = gettext_lazy("Ende:")
DAYS = ngettext_lazy("%(count)s Tag", "%(count)s Tage", "count")
LOCATION_LABEL = gettext_lazy("Ort:")

# Felder
NAME = gettext_lazy("Name")
START = gettext_lazy("Beginn")
END = gettext_lazy("Ende")
# Die Uhrzeit steht im Baustein „Datumsfeld“ rechts neben dem Datum; Vorleseprogramme hören diese Namen (#379).
START_TIME = gettext_lazy("Uhrzeit Beginn")
END_TIME = gettext_lazy("Uhrzeit Ende")
LOCATION = gettext_lazy("Ort")
DURATION_OK = gettext_lazy("Ja, die Dauer stimmt")

# Fehler am Feld
NAME_EMPTY = gettext_lazy("Bitte gib den Namen ein.")
NAME_TOO_LONG = gettext_lazy("Der Name darf höchstens 100 Zeichen lang sein.")
START_EMPTY = gettext_lazy("Bitte gib den Beginn ein.")
END_EMPTY = gettext_lazy("Bitte gib das Ende ein.")
DATE_INVALID = gettext_lazy("Bitte gib ein gültiges Datum ein.")
END_BEFORE_START = gettext_lazy("Das Ende liegt vor dem Beginn.")
TIME_INVALID = gettext_lazy("Bitte gib eine gültige Uhrzeit ein.")
LOCATION_TOO_LONG = gettext_lazy("Der Ort darf höchstens 100 Zeichen lang sein.")
# VER-03, Fragen 2 und 3 aus #29: „vor dem heutigen Tag“; Nachfrage ab 29 Tagen, gezählt wie in der Kachel.
START_IN_PAST = gettext_lazy("Der Beginn liegt in der Vergangenheit.")
DURATION_QUESTION = gettext_lazy("Die Veranstaltung dauert %(count)s Tage. Stimmt das?")

# Anlegen in Schritten (#380): Fortschrittsanzeige, Kopf, Knöpfe und der Dialog „Anlegen abbrechen?“
STEP = gettext_lazy("Schritt %(number)s")
STEP_SUMMARY = gettext_lazy("Zusammenfassung")
DRAFT_HEAD = gettext_lazy("Entwurf · Veranstaltung erstellen")
BASICS_CHANGE = gettext_lazy("Grunddaten ändern")
NEXT = gettext_lazy("Weiter")
BACK = gettext_lazy("Zurück")
CANCEL = gettext_lazy("Abbrechen")
SAVE_EVENT = gettext_lazy("Veranstaltung speichern")
CANCEL_QUESTION = gettext_lazy("Anlegen abbrechen?")
CANCEL_TEXT = gettext_lazy("%(event)s ist als Entwurf gespeichert. Du kannst ihn speichern und später auf der "
                           "Leitungsseite weitermachen oder ihn löschen.")
# Ohne „oder ihn löschen“, wenn „Entwurf löschen“ nicht geht: mit Mitleitung oder Anmeldung (#380, BV3).
CANCEL_TEXT_KEEP = gettext_lazy("%(event)s ist als Entwurf gespeichert. Du kannst ihn speichern und später auf der "
                                "Leitungsseite weitermachen.")
DELETE_DRAFT = gettext_lazy("Entwurf löschen")
SAVE_DRAFT = gettext_lazy("Entwurf speichern")

# Kurze Meldungen (#186). Nach „Veranstaltung speichern“ und „Entwurf speichern“ derselbe Satz (#380).
SAVED_AS_DRAFT = gettext_lazy("%(event)s ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung.")
DRAFT_DELETED = gettext_lazy("Der Entwurf %(event)s ist gelöscht.")
SAVED = gettext_lazy("Die Angaben zu %(event)s sind gespeichert.")
# Gleichzeitiges Speichern wie bei verwalteten Personen (#379, AG7; Muster in persons/texts.py). Ohne „von jemand
# anderem“, weil es auch das eigene zweite Fenster sein kann.
CHANGED_MEANWHILE = gettext_lazy("%(event)s wurde inzwischen geändert. Bitte prüfe die Angaben und speichere erneut.")

# Anmeldungen (#101): Abschnitt auf der Seite der Veranstaltung und Seite der Anmeldung
REGISTRATIONS = gettext_lazy("Anmeldungen")
NO_REGISTRATIONS = gettext_lazy("Zu dieser Veranstaltung gibt es noch keine Anmeldungen.")
REGISTRATION_TITLE = gettext_lazy("Anmeldung")
CONTACT = gettext_lazy("Ansprechperson: %(person)s")
REGISTERED_PERSONS = gettext_lazy("Angemeldete Personen")
# Ablehnungen im Datenmodell; in P2 sieht sie nur, wer Anmeldungen im Programm anlegt (AN-06).
REGISTRATION_ONLY_WITH_PERSONS = gettext_lazy(
    "Eine Anmeldung entsteht nur zusammen mit ihrer Veranstaltung, ihrer Ansprechperson und mindestens einer Person.")
NOT_REGISTERABLE = gettext_lazy("Diese Personen kannst du nicht anmelden: %(persons)s.")
