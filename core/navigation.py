"""Navigation der Seitenleiste und des Handy-Menüs (#7).

Die Leiste zeigt nur, was es gibt, und nur Personen, die es nutzen dürfen; leere
Platzhalter gibt es nicht (Gestaltungskonzept, docs/gestaltung.md). Eine neue Funktion
trägt hier ihren Punkt ein, mit einer Prüfung, wer ihn sieht. Das Ausblenden ersetzt nie
die Rechteprüfung der Seite selbst auf dem Server (CONTRIBUTING.md, Abschnitt 4).
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import Promise
from django.utils.timezone import localtime
from django.utils.translation import gettext_lazy as _

from access.rights import SUPPORT_EXPIRED_SESSION_KEY, unit_label
from roles import texts as role_texts


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
    # Leitungen von Gruppe bis Bund (#189) und die Verbandsleitung (#94, EH-08); die Seite prüft selbst noch einmal.
    NavItem("organisation", _("Organisation"), "organisation", lambda request: request.rights.sees_menu(),
            also_active=("organisation_unit", "federation_appoint_verbandsleitung", "federation_search_verbandsleitung",
                         "federation_appoint_team", "federation_search_team", "federation_appoint_lead",
                         "federation_search_lead", "federation_remove", "organisation_support")),
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


class SupportShown:
    """Was jede Seite mit Login zum Support-Zugang zeigt (#92): den Balken und die Meldung nach Ablauf.

    Beides wird erst gelesen, wenn eine Vorlage danach fragt (`core/templates/base_app.html`). So
    verbraucht ein Stück Seite, etwa die Vorschläge beim Tippen, die Meldung nach Ablauf nicht, und
    Seiten ohne Seitenleiste fragen die Datenbank nicht danach.
    """

    def __init__(self, request: HttpRequest) -> None:
        self.request = request

    @cached_property
    def bar(self) -> dict | None:
        """Organisation, Endzeit und Adresse von „beenden“, solange ein Zugang läuft; sonst None (N1, Frage 3)."""
        rights = getattr(self.request, "rights", None)
        support = rights.support if rights is not None else None
        if support is None:
            return None
        return {"label": unit_label(support.unit), "until": localtime(support.ends_at).strftime("%H:%M"),
                "end_action": reverse("support_end")}

    @cached_property
    def expired(self) -> dict | None:
        """Die Meldung nach Ablauf, einmal: ohne abgeschicktes Formular eine Information, sonst eine Warnung (SA1, SA2, N2)."""
        session = getattr(self.request, "session", None)
        # Eine Anfrage aus dem Skript (etwa Vorschläge beim Tippen) zeigt die Meldung nicht; sie bleibt für die Seite (Befund 2).
        if self.request.headers.get("Sec-Fetch-Dest") == "empty":
            return None
        found = session.pop(SUPPORT_EXPIRED_SESSION_KEY, None) if session is not None else None
        if not found:
            return None
        return {"text": role_texts.SUPPORT_EXPIRED % {"unit": found["unit"]}, "unsaved": found["unsaved"],
                "unsaved_text": role_texts.SUPPORT_UNSAVED}


def support(request: HttpRequest) -> dict:
    """Stellt Balken und Meldung des Support-Zugangs für jede Seite bereit (#92); ohne Login gibt es beides nicht."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"support": None}
    return {"support": SupportShown(request)}
