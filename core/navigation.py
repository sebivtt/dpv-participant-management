"""Navigation der Seitenleiste und des Handy-Menüs (#7).

Die Leiste zeigt nur, was es gibt, und nur Personen, die es nutzen dürfen; leere
Platzhalter gibt es nicht (Gestaltungskonzept, docs/gestaltung.md). Eine neue Funktion
trägt hier ihren Punkt ein, mit einer Prüfung, wer ihn sieht. Das Ausblenden ersetzt nie
die Rechteprüfung der Seite selbst auf dem Server (CONTRIBUTING.md, Abschnitt 4).
"""

from collections.abc import Callable
from dataclasses import dataclass

from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class NavItem:
    """Ein Punkt der Navigation: Adresse (Name in config/urls.py), Beschriftung, Symbol und wer ihn sieht."""

    url_name: str
    label: str | Promise
    icon: str
    visible_for: Callable[[HttpRequest], bool] = lambda request: True


NAV_ITEMS = [
    NavItem("start", _("Startseite"), "home"),
]


def items_for(request: HttpRequest) -> list[dict]:
    """Die Punkte, die diese Person sieht, mit Adresse und Markierung des aktiven Punkts."""
    match = getattr(request, "resolver_match", None)
    current = match.url_name if match else None
    return [
        {"url": reverse(item.url_name), "label": item.label, "icon": item.icon, "active": item.url_name == current}
        for item in NAV_ITEMS
        if item.visible_for(request)
    ]


def navigation(request: HttpRequest) -> dict:
    """Stellt die Navigation jeder Seite bereit; ohne Login gibt es keine.

    Auf der Seite „ungültige Anfrage“ (400) kennt die Anfrage noch keine Person: Django lehnt
    sie ab, bevor der Login-Baustein läuft. Auch dann gibt es keine Navigation (#58).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_items": []}
    return {"nav_items": items_for(request)}
