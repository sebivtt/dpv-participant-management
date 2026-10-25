"""Zufällige Kennungen für Einträge in Adressen, Formularen und htmx-Anfragen (#64, Auslegung von BER-01).

Einträge stehen in Adressen nie mit ihrer laufenden Nummer, sondern mit einer zufälligen Kennung
(`key`), z. B. `/person/k7f3q9xm2abc4def5ghj/`. Aus laufenden Nummern ließe sich die Anzahl der
Einträge ablesen, und Adressen ließen sich durchprobieren. Die Nummer bleibt intern: Verweise
zwischen Tabellen und die Protokolle nutzen sie weiter, keine Seite zeigt sie.

Die Kennung hat 20 Zeichen aus Kleinbuchstaben und den Ziffern 2 bis 7 (das Alphabet von Base32),
also 100 Bit Zufall aus `secrets`. Selbst eine Milliarde Versuche pro Sekunde fänden bei einer
Million Einträgen im Mittel erst nach Millionen Jahren einen Treffer; die Kennung verrät nichts
über Anzahl oder Reihenfolge. Gegen eine UUID (36 Zeichen, mit Bindestrichen) spricht nur die
Länge; gegen `secrets.token_urlsafe` Groß- und Kleinschreibung und Sonderzeichen, die beim
Vorlesen oder Abtippen stören.

Adressen mit Kennung schreiben sie als `<key:…>` (`KeyConverter`, angemeldet in `config/urls.py`);
der Rundumtest lässt in Adressen mit Login keine andere Angabe zu.
"""

import re
import secrets

from django.db import models

KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"
KEY_LENGTH = 20
KEY_PATTERN = f"[a-z2-7]{{{KEY_LENGTH}}}"
# Der Name des Bausteins in Adressen: path("person/<key:person>/", …).
KEY_CONVERTER = "key"


def new_key() -> str:
    """Eine neue zufällige Kennung; doppelte Kennungen lehnt die Datenbank ab (eindeutiges Feld)."""
    return "".join(secrets.choice(KEY_ALPHABET) for _ in range(KEY_LENGTH))


def is_key(value) -> bool:
    """Hat `value` die Form einer Kennung? Alles andere kann kein Eintrag sein."""
    return isinstance(value, str) and re.fullmatch(KEY_PATTERN, value) is not None


def key_field() -> models.CharField:
    """Das Feld für die Kennung eines Eintrags: eindeutig, beim Anlegen gesetzt, danach unveränderlich."""
    return models.CharField(max_length=KEY_LENGTH, unique=True, default=new_key, editable=False)


def has_key(route: str) -> bool:
    """Steht im Muster einer Adresse eine Kennung, z. B. `person/<key:person>/`?"""
    return f"<{KEY_CONVERTER}:" in route


class KeyConverter:
    """Baustein `<key:…>` für Adressen: nimmt nur Text in der Form einer Kennung an.

    Eine Adresse mit einer kaputten Kennung gibt es damit gar nicht; sie zeigt „nicht gefunden“
    wie eine Kennung ohne Eintrag.
    """

    regex = KEY_PATTERN

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: str) -> str:
        return value
