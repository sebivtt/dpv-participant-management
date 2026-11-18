"""Adresssuche über den öffentlichen Suchdienst von OpenStreetMap (Nominatim) für den Baustein „Adressfeld“ (#163).

Nach den Nutzungsregeln von Nominatim (https://operations.osmfoundation.org/policies/nominatim/, docs/entscheidungen.md,
18.11.2026): Nur der Server des Tools fragt, nie der Browser (#278); höchstens eine Anfrage pro Sekunde für alle
zusammen (`_wait_for_turn()`), mit Kennung der Anwendung (`ADDRESS_SEARCH_AGENT`); gleiche Suchen merkt sich der Server
einen Tag lang. Hinaus geht nur der Suchtext, ohne Name, Konto oder Internetadresse der Person. Der Suchtext steht in
keinem Protokoll: Scheitert die Suche, nennt die Zeile im Log nur die Art des Fehlers.
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import GERMANY, STATES, AddressSearchClock

logger = logging.getLogger(__name__)

# „Bis zu 5 Treffer“ (#163, Suche).
MOST_HITS = 5
# Wie lange der Server eine Suche mit ihren Treffern behält.
REMEMBER_SECONDS = 24 * 60 * 60
# Wartet eine Suche länger auf ihren Platz, weil viele gleichzeitig suchen, gilt sie als „nicht erreichbar“ (G2), statt
# die Seite minutenlang laden zu lassen.
LONGEST_WAIT_SECONDS = 5.0
# Wo in der Antwort von Nominatim die Straße und der Ort stehen, je nach Art des Orts.
STREET_KEYS = ("road", "pedestrian", "footway", "path", "cycleway", "square", "place")
CITY_KEYS = ("city", "town", "village", "hamlet", "municipality")
STATE_CODES = {code for code, _name in STATES}


class Unavailable(Exception):
    """Die Adresssuche ist gerade nicht erreichbar (G2)."""


@dataclass(frozen=True)
class Place:
    """Ein Treffer der Adresssuche: Bezeichnung, Teile der Adresse wie im Adressfeld und Koordinaten als Text."""

    title: str
    street: str
    postal_code: str
    city: str
    state: str
    country: str
    latitude: str
    longitude: str


def _request(params: dict) -> list:
    """Fragt den Suchdienst und gibt seine Antwort zurück; wirft bei Ausfall `OSError` oder `ValueError`.

    Die Anfrage trägt nur die Kennung der Anwendung, sonst keine Angaben: kein Cookie, keine Internetadresse der Person.
    """
    url = settings.ADDRESS_SEARCH_URL
    if not url.startswith(("https://", "http://")):
        raise ValueError
    request = Request(f"{url}?{urlencode(params)}",  # noqa: S310 -- feste Adresse aus den Einstellungen, nur http(s)
                      headers={"User-Agent": settings.ADDRESS_SEARCH_AGENT})
    with urlopen(request, timeout=settings.ADDRESS_SEARCH_TIMEOUT_SECONDS) as answer:  # noqa: S310 -- wie oben
        return json.loads(answer.read())


def _wait_for_turn() -> None:
    """Wartet, bis die vorige Anfrage des Tools eine Sekunde her ist, und trägt die eigene ein (G8).

    Gesperrt wird die eine Zeile der Uhr in der Datenbank, damit die Bremse auch über mehrere Prozesse gilt. Läge der
    eigene Platz mehr als `LONGEST_WAIT_SECONDS` in der Zukunft, wartet die Suche nicht, sondern ist nicht erreichbar.
    """
    interval = timedelta(seconds=settings.ADDRESS_SEARCH_INTERVAL_SECONDS)
    for _attempt in range(2):
        try:
            with transaction.atomic():
                clock, _created = AddressSearchClock.objects.select_for_update().get_or_create(
                    pk=1, defaults={"last_request": timezone.now() - interval})
                turn = max(timezone.now(), clock.last_request + interval)
                wait = (turn - timezone.now()).total_seconds()
                if wait > LONGEST_WAIT_SECONDS:
                    raise Unavailable
                if wait > 0:
                    time.sleep(wait)
                clock.last_request = turn
                clock.save(update_fields=["last_request"])
                return
        except IntegrityError:
            # Zwei Suchen haben die Zeile gleichzeitig zum ersten Mal angelegt; die zweite versucht es noch einmal.
            continue
    raise Unavailable


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _place(entry: dict) -> Place:
    """Ein Treffer aus der Antwort von Nominatim (`format=jsonv2`, `addressdetails=1`)."""
    address = entry.get("address") if isinstance(entry.get("address"), dict) else {}
    road = next((_text(address[key]) for key in STREET_KEYS if _text(address.get(key))), "")
    street = " ".join(filter(None, [road, _text(address.get("house_number"))])) if road else ""
    city = next((_text(address[key]) for key in CITY_KEYS if _text(address.get(key))), "")
    country = _text(address.get("country_code")).upper()
    state = _text(address.get("ISO3166-2-lvl4")).removeprefix(f"{GERMANY}-") if country == GERMANY else ""
    return Place(
        title=_text(entry.get("name")) or street or city,
        street=street,
        postal_code=_text(address.get("postcode")),
        city=city,
        state=state if state in STATE_CODES else "",
        country=country,
        latitude=_text(entry.get("lat")),
        longitude=_text(entry.get("lon")),
    )


def search(text: str, country: str = "") -> list[Place]:
    """Sucht `text` bei OpenStreetMap; gibt bis zu 5 Treffer zurück, ohne Treffer eine leere Liste (G1).

    Mit `country` (Kennung nach ISO 3166-1, außer dem vorgewählten Deutschland) sucht sie nur in diesem Land.
    Ist der Suchdienst nicht erreichbar, antwortet er zu langsam oder in falscher Form, ist das `Unavailable` (G2).
    """
    params = {"q": text, "format": "jsonv2", "addressdetails": "1", "limit": str(MOST_HITS), "accept-language": "de"}
    if country:
        params["countrycodes"] = country.lower()
    key = "adresssuche:" + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    remembered = cache.get(key)
    if remembered is not None:
        return remembered
    _wait_for_turn()
    try:
        answer = _request(params)
        if not isinstance(answer, list):
            raise ValueError
        places = [_place(entry) for entry in answer[:MOST_HITS] if isinstance(entry, dict)]
    except (OSError, ValueError) as error:
        # Nur die Art des Fehlers, nie seine Meldung: Sie kann den Suchtext oder die Adresse der Anfrage enthalten.
        logger.warning("Adresssuche nicht erreichbar: %s", type(error).__name__)
        raise Unavailable from None
    cache.set(key, places, REMEMBER_SECONDS)
    return places
