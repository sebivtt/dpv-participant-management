"""Adresssuche über den öffentlichen Suchdienst von OpenStreetMap (Nominatim) für den Baustein „Adressfeld“ (#163).

Gerüst: kommt mit der Umsetzung von #163.
"""

import time  # noqa: F401 (Gerüst)
from dataclasses import dataclass
from urllib.request import Request, urlopen  # noqa: F401 (Gerüst)


class Unavailable(Exception):
    """Die Adresssuche ist gerade nicht erreichbar (G2)."""


@dataclass(frozen=True)
class Place:
    """Ein Treffer der Adresssuche."""

    title: str
    street: str
    postal_code: str
    city: str
    state: str
    country: str
    latitude: str
    longitude: str


def _request(params: dict) -> list:
    """Fragt den Suchdienst; kommt mit der Umsetzung."""
    raise Unavailable


def search(text: str) -> list[Place]:
    """Sucht `text`; kommt mit der Umsetzung."""
    return []
