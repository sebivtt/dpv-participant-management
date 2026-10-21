"""Bausteine der Grundgestaltung für die Vorlagen (#7): Symbole, Statuskennzeichen, Fußbereich, Band der Testumgebung (#58).

Alle Bausteine kommen ohne Anfrage, Sitzung und Datenbank aus, damit sie auch auf der
Fehlerseite funktionieren (core/errors.py).
"""

from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.timezone import localdate

register = template.Library()

# Symbol je Art eines Statuskennzeichens. Ein Kennzeichen hat immer Wort und Symbol, nie nur
# eine Farbe (NFA-03).
STATUS_ICONS = {
    "ok": "haken",
    "warte": "uhr",
    "ab": "nein",
    "entwurf": "stift",
    "bald": "kalender",
    "zu": "schloss",
}


@register.simple_tag
def icon(name: str) -> SafeString:
    """Ein Symbol aus core/templates/core/_symbole.svg; für Bildschirmleser ausgeblendet.

    Symbole ergänzen Beschriftungen, sie ersetzen sie nie. Wo ein Symbol allein steht,
    bekommt sein Knopf oder Link selbst eine Beschriftung.
    """
    return format_html('<svg class="ic" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>', name)


@register.inclusion_tag("core/_status.html")
def status(kind: str, label: str) -> dict:
    """Statuskennzeichen mit Wort und Symbol, z. B. „Anmeldung offen“ mit Haken."""
    return {"kind": kind, "label": label, "icon_name": STATUS_ICONS[kind]}


def copyright_years(today=None) -> str:
    """Jahreszahl für den Copyright-Hinweis: „2026“, ab dem Folgejahr „2026–2027“."""
    start = settings.COPYRIGHT_START_YEAR
    current = (today or localdate()).year
    return str(start) if current <= start else f"{start}–{current}"


@register.inclusion_tag("core/_fuss.html")
def fussbereich() -> dict:
    """Fußbereich jeder Seite: Impressum und Datenschutz links, Copyright rechts."""
    return {
        "impressum_url": settings.IMPRESSUM_URL,
        "datenschutz_url": settings.DATENSCHUTZ_URL,
        "holder": settings.COPYRIGHT_HOLDER,
        "years": copyright_years(localdate()),
    }


@register.inclusion_tag("core/_testband.html")
def testumgebung_band() -> dict:
    """Band „Testumgebung“ oben auf jeder Seite, nur wenn die Testumgebung eingeschaltet ist (#58).

    Mit Symbol und Text, nicht nur in Farbe (NFA-03). Als Hinweis (role="note") ohne Fokus,
    damit die Tastatur weiter mit dem ersten Tab zum Inhalt kommt.
    """
    return {"show": settings.TEST_ENVIRONMENT}
