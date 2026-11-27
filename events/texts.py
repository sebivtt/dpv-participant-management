"""Texte zu Veranstaltungen (#100, #379) und Anmeldungen (#101), übersetzbar (NFA-02).

Wortlaute aus dem Text von #100 und den Szenarien vom 30.10.2026, für Anmeldungen aus den Szenarien zu #101 vom
15.11.2026, für Uhrzeiten, Ort, Prüfungen und Leitungsseite aus dem Text von #379 und seinen Szenarien vom
17.11.2026, für das Anlegen in Schritten aus dem Text von #380 und seinen Szenarien vom 17.11.2026, für Zustand und
Veröffentlichen aus dem Text von #359 und seinen Szenarien vom 17.11.2026, für den Einladungstext aus dem Text von #358,
seiner Nachklärung und seinen Szenarien vom 17.11.2026 (Fassung nach dem Zielbild), für die Fristen aus dem Text von
#360 und seinen Szenarien vom 17.11.2026.
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
# Seit der Vorschau zu #163 (Sebastian, 18.11.2026) steht die Bezeichnung mit der Adresse in einer eigenen Fläche „Ort“.
LOCATION = gettext_lazy("Bezeichnung")
PLACE = gettext_lazy("Ort")
DURATION_OK = gettext_lazy("Ja, die Dauer stimmt")

# Fehler am Feld
NAME_EMPTY = gettext_lazy("Bitte gib den Namen ein.")
NAME_TOO_LONG = gettext_lazy("Der Name darf höchstens 100 Zeichen lang sein.")
START_EMPTY = gettext_lazy("Bitte gib den Beginn ein.")
END_EMPTY = gettext_lazy("Bitte gib das Ende ein.")
DATE_INVALID = gettext_lazy("Bitte gib ein gültiges Datum ein.")
END_BEFORE_START = gettext_lazy("Das Ende liegt vor dem Beginn.")
TIME_INVALID = gettext_lazy("Bitte gib eine gültige Uhrzeit ein.")
LOCATION_TOO_LONG = gettext_lazy("Die Bezeichnung darf höchstens 100 Zeichen lang sein.")
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

# Einladungstext (#358): Schritt 2, Abschnitt der Zusammenfassung, Kachel und Dialog des Stifts
INVITATION = gettext_lazy("Einladungstext")
INVITATION_CHANGE = gettext_lazy("Einladungstext ändern")
INVITATION_EDIT = gettext_lazy("Einladungstext bearbeiten")
NO_INVITATION = gettext_lazy("Noch kein Einladungstext.")
# Am Feld, mit der Zahl in deutscher Schreibweise („10.001“); der Text bleibt im Editor (G1).
INVITATION_TOO_LONG = gettext_lazy("Der Einladungstext ist zu lang: höchstens %(limit)s Zeichen, jetzt %(count)s.")
INVITATION_SAVED = gettext_lazy("Der Einladungstext von %(event)s ist gespeichert.")
# Gleichzeitiges Speichern (G2), nach dem Muster bei verwalteten Personen, um den Satz zum eigenen Text ergänzt.
INVITATION_CHANGED_MEANWHILE = gettext_lazy(
    "Der Einladungstext von %(event)s wurde inzwischen von jemand anderem geändert. Dein Text steht unten noch im "
    "Editor und ist nicht gespeichert. Bitte prüfe ihn und speichere erneut.")

# Kurze Meldungen (#186). Nach „Veranstaltung speichern“ und „Entwurf speichern“ derselbe Satz (#380).
SAVED_AS_DRAFT = gettext_lazy("%(event)s ist als Entwurf gespeichert. Nur die Leitung sieht die Veranstaltung.")
DRAFT_DELETED = gettext_lazy("Der Entwurf %(event)s ist gelöscht.")
SAVED = gettext_lazy("Die Angaben zu %(event)s sind gespeichert.")
# Gleichzeitiges Speichern wie bei verwalteten Personen (#379, AG7; Muster in persons/texts.py). Ohne „von jemand
# anderem“, weil es auch das eigene zweite Fenster sein kann.
CHANGED_MEANWHILE = gettext_lazy("%(event)s wurde inzwischen geändert. Bitte prüfe die Angaben und speichere erneut.")

# Zustand und Veröffentlichen (#359): Zustandsmarke (#356 N2), Satz darunter (Frage 5), Schalter und Rückfragen
STATE_DRAFT = gettext_lazy("Entwurf")
STATE_ANNOUNCED = gettext_lazy("Angekündigt")
STATE_OPEN = gettext_lazy("Anmeldung offen")
STATE_CLOSED = gettext_lazy("Geschlossen")
STATE_RUNNING = gettext_lazy("Läuft")
STATE_ENDED = gettext_lazy("Beendet")
STATE_LABEL = gettext_lazy("Zustand")
ONLY_LEADS_SEE = gettext_lazy("Nur die Leitung sieht die Veranstaltung.")
START_PASSED = gettext_lazy("Der Beginn liegt in der Vergangenheit. Ändere ihn in den Grunddaten, um zu veröffentlichen.")
IS_PUBLISHED = gettext_lazy("Die Veranstaltung ist veröffentlicht.")
RUNS_UNTIL = gettext_lazy("Die Veranstaltung läuft bis %(end)s.")
ENDED_ON = gettext_lazy("Die Veranstaltung ist am %(end)s zu Ende gegangen.")
PUBLISHED_SWITCH = gettext_lazy("Veröffentlicht")
PUBLISH_QUESTION = gettext_lazy("%(event)s veröffentlichen?")
PUBLISH_TEXT = gettext_lazy("Danach sieht der Teilnahmekreis die Einladung.")
PUBLISH_BUTTON = gettext_lazy("Veröffentlichen")
WITHDRAW_QUESTION = gettext_lazy("Veröffentlichung von %(event)s zurücknehmen?")
WITHDRAW_TEXT = gettext_lazy("Danach sieht nur noch die Leitung die Veranstaltung; beim Teilnahmekreis verschwindet "
                             "die Einladung.")
WITHDRAW_BUTTON = gettext_lazy("Zurücknehmen")
# Kurze Meldungen (#186) danach; „schon …“, wenn jemand anderes oder ein zweites Fenster schneller war (ZG3).
PUBLISHED = gettext_lazy("%(event)s ist veröffentlicht.")
WITHDRAWN = gettext_lazy("Die Veröffentlichung von %(event)s ist zurückgenommen.")
ALREADY_PUBLISHED = gettext_lazy("%(event)s ist schon veröffentlicht.")
ALREADY_WITHDRAWN = gettext_lazy("%(event)s ist schon nicht mehr veröffentlicht.")
# Ablehnung beim Zurücknehmen ab Beginn (Frage 3, ZG4); beim Veröffentlichen mit Beginn vor heute START_PASSED.
ALREADY_BEGUN = gettext_lazy("Die Veranstaltung hat schon begonnen. Die Veröffentlichung lässt sich nicht mehr "
                             "zurücknehmen.")

# Fristen (#360): Schritt 3 „Anmeldung“, Kachel „Anmeldung“ mit Zeitleiste (auch in der Zusammenfassung) und Dialog
SIGNUP = gettext_lazy("Anmeldung")
SIGNUP_CHANGE = gettext_lazy("Anmeldung ändern")
SIGNUP_EDIT = gettext_lazy("Anmeldung bearbeiten")
DEADLINES = gettext_lazy("Fristen")
REGISTRATION_OPENS = gettext_lazy("Anmeldestart")
REGISTRATION_CLOSES = gettext_lazy("Anmeldeschluss")
CHANGES_CLOSE = gettext_lazy("Änderungsschluss")
# Fehler am Feld (Fragen 3 bis 5); im Stift „Grunddaten“ der Fehler am Beginn (FG4).
CLOSES_BEFORE_OPENS = gettext_lazy("Der Anmeldeschluss liegt vor dem Anmeldestart.")
CHANGES_BEFORE_CLOSES = gettext_lazy("Der Änderungsschluss liegt vor dem Anmeldeschluss.")
CHANGES_WITHOUT_CLOSES = gettext_lazy("Trag zuerst einen Anmeldeschluss ein.")
OPENS_AFTER_START = gettext_lazy("Der Anmeldestart liegt nach dem Beginn.")
CLOSES_AFTER_START = gettext_lazy("Der Anmeldeschluss liegt nach dem Beginn.")
CHANGES_AFTER_START = gettext_lazy("Der Änderungsschluss liegt nach dem Beginn.")
START_BEFORE_DEADLINE = gettext_lazy("Der Beginn liegt vor einer Frist der Anmeldung. Ändere zuerst die Fristen.")
DEADLINES_SAVED = gettext_lazy("Die Fristen von %(event)s sind gespeichert.")
# Zeitleiste der Kachel: „Heute“, an der nächsten künftigen Frist „in 27 Tagen“, „morgen“ oder „heute“.
TODAY = gettext_lazy("Heute")
IN_DAYS = gettext_lazy("in %(count)s Tagen")
TOMORROW = gettext_lazy("morgen")
TODAY_SMALL = gettext_lazy("heute")
UNTIL_THEN_LATE = gettext_lazy("bis dahin Nachmelden")
OPENS_NOT_SET = gettext_lazy("nicht festgelegt, öffnet mit dem Veröffentlichen")
CLOSES_NOT_SET = gettext_lazy("nicht festgelegt, offen bis zum Beginn")
CHANGES_NOT_SET = gettext_lazy("nicht festgelegt, Nachmelden bis zum Beginn")
# Satz unter der Marke auf der Leitungsseite, nach IS_PUBLISHED.
SIGNUP_OPENS_ON = gettext_lazy("Die Anmeldung öffnet am %(day)s.")
SIGNUP_RUNS_UNTIL = gettext_lazy("Die Anmeldung läuft bis %(day)s.")
SIGNUP_RUNS_UNTIL_START = gettext_lazy("Die Anmeldung läuft bis zum Beginn.")
SIGNUP_CLOSED_LATE_UNTIL = gettext_lazy("Die Anmeldung ist geschlossen. Nachmelden und Ändern bis %(day)s.")
SIGNUP_CLOSED_LATE_UNTIL_START = gettext_lazy("Die Anmeldung ist geschlossen. Nachmelden und Ändern bis zum Beginn.")
SIGNUP_CLOSED = gettext_lazy("Die Anmeldung ist geschlossen.")
# Klein unter der Marke in der Liste „Von mir geleitet“; nach dem Änderungsschluss nichts.
NOTE_FROM = gettext_lazy("Anmeldung ab %(day)s")
NOTE_UNTIL = gettext_lazy("bis %(day)s")
NOTE_UNTIL_START = gettext_lazy("bis zum Beginn")
NOTE_LATE_UNTIL = gettext_lazy("Nachmelden bis %(day)s")
NOTE_LATE_UNTIL_START = gettext_lazy("Nachmelden bis zum Beginn")
# Zusätzlicher Satz in der Rückfrage „… veröffentlichen?“ (#359, Ansicht 6b).
PUBLISH_OPENS_ON = gettext_lazy("Die Anmeldung öffnet am %(opens)s und läuft bis %(closes)s.")
PUBLISH_OPENS_ON_UNTIL_START = gettext_lazy("Die Anmeldung öffnet am %(opens)s und läuft bis zum Beginn.")
PUBLISH_OPENS_NOW = gettext_lazy("Die Anmeldung öffnet sofort und läuft bis %(closes)s.")
PUBLISH_OPENS_NOW_UNTIL_START = gettext_lazy("Die Anmeldung öffnet sofort und läuft bis zum Beginn.")
PUBLISH_ALREADY_CLOSED = gettext_lazy("Die Anmeldung ist schon geschlossen.")

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
