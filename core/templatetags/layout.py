"""Bausteine der Grundgestaltung für die Vorlagen (#7): Symbole, Statuskennzeichen, Meldungen (#165), Fußbereich, Band der Testumgebung (#58).

Alle Bausteine kommen ohne Anfrage, Sitzung und Datenbank aus, damit sie auch auf der
Fehlerseite funktionieren (core/errors.py).
"""

from django import template
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.utils.timezone import localdate
from django.utils.translation import gettext_lazy

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


# Je Art einer Meldung: Klasse, Symbol und das Wort, das Vorleseprogramme vorweg ansagen. Die
# Schlüssel sind die Stufen von Djangos Meldungen (message.level_tag), damit die Login-Seite sie
# direkt weitergeben kann. Farben wie die Statuskennzeichen (core/static/core/app.css).
MESSAGE_KINDS = {
    "info": ("ist-info", "info", gettext_lazy("Information:")),
    "warning": ("ist-warnung", "hinweis", gettext_lazy("Warnung:")),
    "error": ("ist-fehler", "nein", gettext_lazy("Fehler:")),
    "success": ("ist-erfolg", "erfolg", gettext_lazy("Erfolg:")),
}

# Nach einer Handlung angesagt: Warnung und Fehler sofort, Info und Erfolg, sobald das
# Vorleseprogramm frei ist.
LIVE_ROLES = {"info": "status", "success": "status", "warning": "alert", "error": "alert"}


@register.inclusion_tag("core/_meldung.html")
def meldung(kind: str, text: str = "", title: str = "", icon: str = "", live: bool = False) -> dict:
    """Meldung einer der vier Arten (#165, docs/gestaltung.md): Info, Warnung, Fehler, Erfolg.

    `title` steht fett als eigene Zeile über `text`. Ein passenderes Symbol als das der Art
    ist erlaubt (`icon`, z. B. das Schloss). Die Art ist nie nur Farbe: Jede hat ihr Symbol,
    und Vorleseprogramme hören vorweg ihr Wort, etwa „Warnung:“. `live` nur für Meldungen
    nach einer Handlung (Login-Seite); fest auf einer Seite stehende werden nicht ungefragt
    angesagt. Eine unbekannte Art, etwa eine eigene Stufe einer Django-Meldung, erscheint als
    Information, statt die Seite mit einem Serverfehler zu sperren.
    """
    kind = kind if kind in MESSAGE_KINDS else "info"
    css_class, icon_name, prefix = MESSAGE_KINDS[kind]
    return {
        "css_class": css_class,
        "icon_name": icon or icon_name,
        "prefix": prefix,
        "role": LIVE_ROLES[kind] if live else "note",
        "title": title,
        "text": text,
    }


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
    damit die Tastatur weiter mit dem ersten Tab zum Inhalt kommt. Gestreift und mit
    Laborsymbol, damit es nicht wie eine Warnmeldung aussieht (#165).
    """
    return {"show": settings.TEST_ENVIRONMENT}
