"""Texte des Bausteins „Adressfeld“ mit Adresssuche (#163), übersetzbar (NFA-02).

Wortlaute aus dem Text von #163, seinem Zielbild (Fassung 2) und der Nachklärung vom 17.11.2026.
"""

from django.utils.translation import gettext_lazy

ADDRESS = gettext_lazy("Adresse")
STREET = gettext_lazy("Straße und Hausnummer")
POSTAL_CODE = gettext_lazy("PLZ")
CITY = gettext_lazy("Ort")
STATE = gettext_lazy("Bundesland")
COUNTRY = gettext_lazy("Land")
CHOOSE = gettext_lazy("Bitte wählen")

# Suche (Zielbild, Ansichten 1 bis 4)
SEARCH = gettext_lazy("Adresse suchen")
SEARCH_HINT = gettext_lazy("Sucht mit der Bezeichnung oder einer Straße mit PLZ oder Ort.")
HITS = gettext_lazy("Treffer")
TAKE = gettext_lazy("Übernehmen")
SOURCE = gettext_lazy("Adressdaten ©")
SOURCE_LINK = gettext_lazy("OpenStreetMap-Mitwirkende")
NOTHING_FOUND = gettext_lazy("Keine Adresse gefunden. Du kannst sie unten selbst eintragen.")
UNAVAILABLE = gettext_lazy("Die Adresssuche ist gerade nicht erreichbar. Du kannst die Adresse unten selbst eintragen.")
TOO_LITTLE = gettext_lazy("Für die Suche gib bitte die Bezeichnung oder eine Straße mit PLZ oder Ort ein.")

# Fehler am Feld (Nachklärung Z1). Die Höchstlängen sind keine fachliche Regel, sondern die Größe der Felder in der
# Datenbank; ihre Sätze folgen dem Muster der übrigen Felder.
POSTAL_CODE_EMPTY = gettext_lazy("Bitte gib die PLZ ein.")
CITY_EMPTY = gettext_lazy("Bitte gib den Ort ein.")
FIVE_DIGITS = gettext_lazy("Bitte gib 5 Ziffern ein.")
STREET_TOO_LONG = gettext_lazy("Straße und Hausnummer dürfen höchstens 100 Zeichen lang sein.")
POSTAL_CODE_TOO_LONG = gettext_lazy("Die PLZ darf höchstens 10 Zeichen lang sein.")
CITY_TOO_LONG = gettext_lazy("Der Ort darf höchstens 100 Zeichen lang sein.")
