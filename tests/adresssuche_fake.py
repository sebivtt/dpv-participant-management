"""Nachgestellter Suchdienst von OpenStreetMap (Nominatim) für die Tests der Adresssuche (#163).

Kein Test und kein Rauchtest fragt den echten Suchdienst: Ohne das Kennzeichen `osm` bricht jede Anfrage mit einem
Fehler ab, der den Test rot macht. Mit `osm` antwortet der nachgestellte Dienst wie Nominatim mit erfundenen Orten
und merkt sich jede Anfrage, damit ein Test prüfen kann, was hinausgeht (V4) und wann (G8). Die Antworten haben die
Form von Nominatim (`format=jsonv2`, `addressdetails=1`). Alle Orte und Adressen sind erfunden; „Burg Ludwigstein“
ist als Bezeichnung aus dem Zielbild übernommen (#356).
"""

import time

import pytest
from django.core.cache import cache

from core import address_search


def place(name: str, road: str = "", number: str = "", postcode: str = "", city: str = "", state: str = "",
          iso: str = "", country_code: str = "de", lat: str = "51.0000000", lon: str = "9.0000000") -> dict:
    """Ein Treffer, wie Nominatim ihn liefert."""
    address = {"postcode": postcode, "country_code": country_code}
    if road:
        address["road"] = road
    if number:
        address["house_number"] = number
    if city:
        address["village"] = city
    if state:
        address["state"] = state
    if iso:
        address["ISO3166-2-lvl4"] = iso
    return {"name": name, "lat": lat, "lon": lon, "display_name": ", ".join(filter(None, [name, road, city])),
            "address": address}


BURG = place("Burg Ludwigstein", "Burgweg", "1", "99999", "Musterhausen", "Hessen", "DE-HE",
             lat="51.3260000", lon="9.9040000")
PARKPLATZ = place("Jugendburg Ludwigstein, Parkplatz", "Burgweg", "", "99999", "Musterhausen", "Hessen", "DE-HE")
STRASSE = place("Ludwigsteinstraße", "Ludwigsteinstraße", "", "99990", "Beispielheim", "Niedersachsen", "DE-NI")
BURGWEG = place("", "Burgweg", "1", "99999", "Musterhausen", "Hessen", "DE-HE", lat="51.3260000", lon="9.9040000")
SECHS = [place(f"Zeltplatz {number}", "Seeweg", str(number), "99996", "Seedorf", "Hessen", "DE-HE")
         for number in range(1, 7)]

# Welche Suchtexte welche Treffer bringen; jeder andere Suchtext findet nichts (G1).
ANSWERS = {
    "Burg Ludwigstein": [BURG, PARKPLATZ, STRASSE],
    "Burgweg 1, Musterhausen": [BURGWEG],
    "Burg Ludwigstein, Musterhausn": [BURG],
    "Zeltplatz am Seeweg": SECHS,
}


class FakeOsm:
    """Nimmt die Anfragen an Stelle von `core.address_search._request()` an."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.times: list[float] = []
        # Wie OpenStreetMap ausfällt (G2): None antwortet, sonst die Ausnahme, die die Anfrage wirft.
        self.failure: Exception | None = None

    def __call__(self, params: dict) -> list:
        self.calls.append(dict(params))
        self.times.append(time.monotonic())
        if self.failure is not None:
            raise self.failure
        return [dict(entry) for entry in ANSWERS.get(params.get("q", ""), [])]


def _no_real_search(params: dict) -> list:
    raise AssertionError("Ein Test hat den echten Suchdienst von OpenStreetMap gefragt; dafür gibt es das Kennzeichen osm.")


@pytest.fixture(autouse=True)
def _kein_echter_suchdienst(monkeypatch, settings):
    """Kein Test fragt OpenStreetMap; gemerkte Suchen aus einem früheren Test gelten nicht. Die Bremse wartet nicht,
    außer ein Test stellt sie selbst wieder auf eine Sekunde (G8)."""
    monkeypatch.setattr(address_search, "_request", _no_real_search)
    settings.ADDRESS_SEARCH_INTERVAL_SECONDS = 0
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def osm(monkeypatch) -> FakeOsm:
    """Der nachgestellte Suchdienst mit den erfundenen Orten aus `ANSWERS`."""
    fake = FakeOsm()
    monkeypatch.setattr(address_search, "_request", fake)
    return fake
