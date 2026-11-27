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
from circles import texts as circle_texts
from events import texts as event_texts
from roles import texts as role_texts


@dataclass(frozen=True)
class NavItem:
    """Ein Punkt der Navigation: Adresse (Name in config/urls.py), Beschriftung, Symbol und wer ihn sieht."""

    url_name: str
    label: str | Promise
    icon: str
    visible_for: Callable[[HttpRequest], bool] = lambda request: True
    # Hervorgehoben auf jeder Adresse, die mit der eigenen beginnt, also auf allen Seiten und Dialogen
    # des Bereichs (#266). Ohne nur auf der eigenen Adresse, wie bei der Startseite unter „/“.
    area: bool = True


NAV_ITEMS = [
    NavItem("start", _("Startseite"), "home", area=False),
    # Leitungen von Gruppe bis Bund (#189) und die Verbandsleitung (#94, EH-08); die Seite prüft selbst noch einmal.
    NavItem("organisation", _("Organisation"), "organisation", lambda request: request.rights.sees_menu()),
    # Mit Zuordnung immer, ohne nur, solange die Person eine Veranstaltung leitet (#100); die Seiten prüfen selbst.
    NavItem("events", event_texts.NAV, "kalender", lambda request: request.rights.sees_events()),
    # Nur mit Zuordnung (#381, BER-03, KR-02); die Seiten prüfen selbst.
    NavItem("circles", circle_texts.NAV, "kreis", lambda request: request.rights.may_use_circles()),
]


def _active(request: HttpRequest, url: str, area: bool = True) -> bool:
    """Steht die Anfrage unter `url`, mit `area` auch auf einer Adresse darunter, z. B. einem Dialog (#266)?

    Hervorgehoben wird nach dem Anfang der Adresse statt nach einer Liste von Hand; so hebt auch eine
    neue Adresse ihren Punkt hervor. Die Adressen enden mit „/“, also gehört „/organisationen/“
    nicht zu „/organisation/“.
    """
    return request.path.startswith(url) if area else request.path == url


def items_for(request: HttpRequest) -> list[dict]:
    """Die Punkte, die diese Person sieht, mit Adresse und Markierung des aktiven Punkts."""
    items = []
    for item in NAV_ITEMS:
        if item.visible_for(request):
            url = reverse(item.url_name)
            active = _active(request, url, item.area)
            items.append({"url": url, "label": item.label, "icon": item.icon, "active": active})
    return items


def navigation(request: HttpRequest) -> dict:
    """Stellt die Navigation jeder Seite bereit; ohne Login gibt es keine.

    Auf der Seite „ungültige Anfrage“ (400) kennt die Anfrage noch keine Person: Django lehnt
    sie ab, bevor der Login-Baustein läuft. Auch dann gibt es keine Navigation (#58).

    „Mein Profil“ ist kein Punkt der Navigation; sein Zugang ist der Profilkreis, der
    hervorgehoben ist, solange die Seite offen ist (#13, docs/gestaltung.md). Das gilt auf jeder
    Adresse unter `/profil/`: nach dem Speichern des Fahrtennamens (#111) und mit offenem Dialog
    „Austreten“ oder „Rolle abgeben“ (#266).
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {"nav_items": []}
    return {"nav_items": items_for(request), "profile_active": _active(request, reverse("profile"))}


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
