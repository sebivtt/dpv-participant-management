"""Datenmodell der App „core“: die Adresse aus dem Baustein „Adressfeld“ (#163) und die Uhr der Adresssuche.

Die Adresse ist ein gemeinsamer Teil für jedes Datenmodell mit Adresse (`PostalAddress`). In P3 nutzt ihn nur der Ort
einer Veranstaltung (VER-04); Profil, Anmeldung und Stamm binden ihn mit ihrer ersten Seite ein (#163, Frage 9).
"""

from django.db import models
from django.db.models import Q
from django.db.models.functions import Trim
from django.utils.translation import gettext_lazy as _

# Längen der Felder; die Länge prüft erst der Server, damit beim Einfügen nichts still abgeschnitten wird (#215).
STREET_MAX_LENGTH = 100
POSTAL_CODE_MAX_LENGTH = 10
CITY_MAX_LENGTH = 100
# Vorgewählt in der Auswahl „Land“; davon hängen die Prüfung auf 5 Ziffern und das Bundesland ab (#163, N2).
GERMANY = "DE"
# Die 16 Länder für die Auswahl „Bundesland“, nur bei Deutschland (#163, Frage 4). Die Kennung ist der zweite Teil der
# Kennung nach ISO 3166-2 („DE-HE“), die auch OpenStreetMap zu jedem Treffer liefert.
STATES = (
    ("BW", _("Baden-Württemberg")),
    ("BY", _("Bayern")),
    ("BE", _("Berlin")),
    ("BB", _("Brandenburg")),
    ("HB", _("Bremen")),
    ("HH", _("Hamburg")),
    ("HE", _("Hessen")),
    ("MV", _("Mecklenburg-Vorpommern")),
    ("NI", _("Niedersachsen")),
    ("NW", _("Nordrhein-Westfalen")),
    ("RP", _("Rheinland-Pfalz")),
    ("SL", _("Saarland")),
    ("SN", _("Sachsen")),
    ("ST", _("Sachsen-Anhalt")),
    ("SH", _("Schleswig-Holstein")),
    ("TH", _("Thüringen")),
)
# Die Felder einer Adresse, wie das Formular sie liefert und die Datenbank sie speichert.
ADDRESS_FIELDS = ("street", "postal_code", "city", "state", "country", "latitude", "longitude")


class PostalAddress(models.Model):
    """Eine freiwillige Adresse: Straße und Hausnummer, PLZ, Ort, Bundesland und Land, dazu unsichtbar Koordinaten.

    Ohne Adresse sind alle Felder leer. Mit Adresse sind PLZ, Ort und Land gesetzt; das Bundesland nur bei
    Deutschland (#163, Pflicht und G7). Die Koordinaten kommen nur aus einem übernommenen Treffer der Adresssuche
    und fallen weg, sobald die Adresse danach von Hand geändert wird (A4). Die Regeln setzt auch die Datenbank durch
    (`address_constraints()`); jedes Datenmodell mit Adresse nimmt sie in seine Prüfungen auf.
    """

    street = models.CharField(max_length=STREET_MAX_LENGTH, blank=True, default="")
    postal_code = models.CharField(max_length=POSTAL_CODE_MAX_LENGTH, blank=True, default="")
    city = models.CharField(max_length=CITY_MAX_LENGTH, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="", choices=STATES)
    country = models.CharField(max_length=2, blank=True, default="")
    # Sieben Stellen nach dem Komma sind etwa ein Zentimeter; mehr liefert OpenStreetMap nicht.
    latitude = models.DecimalField(max_digits=9, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        abstract = True


def address_constraints(prefix: str) -> list[models.CheckConstraint]:
    """Die Prüfungen der Datenbank für eine Adresse (#163); `prefix` macht ihre Namen je Tabelle eindeutig."""
    empty = Q(street="", postal_code="", city="", state="", country="")
    return [
        models.CheckConstraint(
            condition=Q(street=Trim("street"), postal_code=Trim("postal_code"), city=Trim("city")),
            name=f"{prefix}_address_trimmed"),
        # Ganz leer oder mit PLZ, Ort und Land (Pflicht, sobald etwas eingetragen ist).
        models.CheckConstraint(condition=empty | (~Q(postal_code="") & ~Q(city="") & ~Q(country="")),
                               name=f"{prefix}_address_complete"),
        # Ein Bundesland nur in Deutschland (G7).
        models.CheckConstraint(condition=Q(state="") | Q(country=GERMANY), name=f"{prefix}_address_state_germany"),
        # Koordinaten beide oder keine, und nur zu einer Adresse.
        models.CheckConstraint(
            condition=Q(latitude__isnull=True, longitude__isnull=True)
            | (Q(latitude__isnull=False, longitude__isnull=False) & ~Q(city="")),
            name=f"{prefix}_address_coordinates"),
    ]


class AddressSearchClock(models.Model):
    """Wann das Tool zuletzt bei OpenStreetMap gesucht hat; genau eine Zeile, ohne Suchtext (#163, Bremse).

    Die Nutzungsregeln erlauben höchstens eine Anfrage pro Sekunde, für alle zusammen. Jede Anfrage sperrt diese
    Zeile kurz, wartet, bis die vorige eine Sekunde her ist, und trägt ihre Zeit ein (`core/address_search.py`). So
    gilt die Bremse auch über mehrere Prozesse des Servers hinweg.
    """

    last_request = models.DateTimeField()
