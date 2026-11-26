"""Einladungstext einer Veranstaltung (#358, VER-05): bereinigen, Zeichen zählen und die ersten Zeilen zeigen.

Gerüst für die Tests; die Regeln kommen mit der Umsetzung von #358.
"""

from django.utils.safestring import SafeString, mark_safe

# Die ersten höchstens 300 Zeichen auf Zusammenfassung und Kachel (#358, Frage 10).
EXCERPT_LENGTH = 300


def clean(html: str) -> str:
    """Bereinigt einen Einladungstext auf die erlaubten Formatierungen."""
    return html


def visible_length(html: str) -> int:
    """Die Zahl der sichtbaren Zeichen, ohne Formatierung."""
    return 0


def excerpt(html: str, limit: int = EXCERPT_LENGTH) -> SafeString:
    """Die ersten höchstens `limit` Zeichen mit Formatierung."""
    return mark_safe("")
