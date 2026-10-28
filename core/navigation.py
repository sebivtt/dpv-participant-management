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
    # Weitere Adressen, unter denen der Punkt hervorgehoben ist, z. B. die Seite je Organisation.
    also_active: tuple[str, ...] = ()


NAV_ITEMS = [
    NavItem("start", _("Startseite"), "home"),
    # Leitungen von Gruppe bis Bund (#189, EH-08); die Seite prüft selbst noch einmal.
    NavItem("organisation", _("Organisation"), "organisation", lambda request: request.rights.sees_organisation(),
            also_active=("organisation_unit",)),
]


def _current(request: HttpRequest) -> str | None:
    """Name der aufgerufenen Adresse in config/urls.py, z. B. "start"."""
    match = getattr(request, "resolver_match", None)
    return match.url_name if match else None


# Adressen, unter denen „Mein Profil“ steht: die Seite selbst und, mit Fehler, das Speichern des Fahrtennamens.
PROFILE_PAGES = ("profile", "profile_scout_name")


def items_for(request: HttpRequest) -> list[dict]:
    """Die Punkte, die diese Person sieht, mit Adresse und Markierung des aktiven Punkts."""
    current = _current(request)
    return [
        {"url": reverse(item.url_name), "label": item.label, "icon": item.icon,
         "active": current in (item.url_name, *item.also_active)}
        for item in NAV_ITEMS
        if item.visible_for(request)
    ]


def navigation(request: HttpRequest) -> dict:
    """Stellt die Navigation jeder Seite bereit; ohne Login gibt es keine.

    Auf der Seite „ungültige Anfrage“ (400) kennt die Anfrage noch keine Person: Django lehnt
    sie ab, bevor der Login-Baustein läuft. Auch dann gibt es keine Navigation (#58).

    „Mein Profil“ ist kein Punkt der Navigation; sein Zugang ist der Profilkreis, der
    hervorgehoben ist, solange die Seite offen ist (#13, docs/gestaltung.md). Das gilt auch, wenn
    die Seite nach dem Speichern des Fahrtennamens unter dessen Adresse steht (#111).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_items": []}
    return {"nav_items": items_for(request), "profile_active": _current(request) in PROFILE_PAGES}
