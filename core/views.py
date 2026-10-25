"""Seiten der App „core“."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from access.addresses import checks_rights, without_personal_data


# Zeigt nur die angemeldete Person selbst (BER-01, Grund 1), nie eine andere.
@checks_rights("EP-01", "EP-02")
def start(request: HttpRequest) -> HttpResponse:
    """Startseite nach dem Login: Begrüßung mit Name und Mail aus Keycloak (#5, ORG-03).

    Nur mit Login erreichbar und zeigt nur die Daten der angemeldeten Person selbst. Fehlt
    in Keycloak der Vor- oder Nachname, steht dort ein Hinweis, ihn im DPV-Konto zu ergänzen.
    """
    name_incomplete = not (request.user.first_name and request.user.last_name)
    return render(request, "core/start.html", {"name_incomplete": name_incomplete})


@checks_rights("EP-01", "EP-02", "EP-05")
def profile(request: HttpRequest) -> HttpResponse:
    """Gerüst für „Mein Profil“ (#96)."""
    return render(request, "core/profil.html")


def _example(title, period, place, org, state, registered=None, capacity=None, picture=None, draft=False) -> dict:
    """Eine erfundene Veranstaltung für die Musterseite."""
    return {
        "title": title, "period": period, "place": place, "org": org, "state": state,
        "registered": registered, "capacity": capacity, "picture": picture, "draft": draft,
        "full": capacity is not None and registered is not None and registered >= capacity,
        "percent": min(100, round(registered / capacity * 100)) if capacity and registered is not None else None,
    }


@without_personal_data("Musterseite: nur erfundene Beispiele (#7).")
def pattern_library(request: HttpRequest) -> HttpResponse:
    """Musterseite (#7): alle Bausteine der Grundgestaltung mit erfundenen Beispielen.

    Zeigt oben den Aufbau des späteren Dashboards (#28), darunter die übrigen Bausteine.
    Die Navigation zeigt alle geplanten Bereiche, gekennzeichnet als Beispiel; auf echten
    Seiten steht nur, was es gibt (core/navigation.py). Namen, Orte und Personen sind
    erfunden; die Zustände sind vorläufig, die endgültigen klärt #29.
    """
    open_ = ("ok", _("Anmeldung offen"))
    soon = ("bald", _("Anmeldung ab 01.12."))
    closed = ("zu", _("Anmeldung geschlossen"))
    draft = ("entwurf", _("Entwurf"))
    events = [
        _example("Pfingstlager 2027", "Fr 14.05. – Mo 17.05.2027", "Jugendzeltplatz Erlengrund", "Stamm Walhall",
                 open_, 23, 40, picture="lager"),
        _example("Leitungsschulung Nord", "Sa 20.11.2027, 10–17 Uhr", "Pfadfinderheim Boreas", "Bund Nord",
                 open_, 16, 16),
        _example("Stammeswochenende Walhall", "Fr 05.11. – So 07.11.2027", "Burg Rabenstein", "Stamm Walhall",
                 closed, 31),
        _example("Bundesfahrt 2028", "Sa 15.07. – Sa 29.07.2028", "Südschweden", "Bund Nord", soon, picture="fahrt"),
        _example("Stammesrat Zugvögel", "Sa 13.11.2027, 14–18 Uhr", "Gemeindehaus Lindenhof", "Stamm Zugvögel",
                 open_, 12),
        _example("Herbsttreffen der Zugvögel", "Fr 08.10. – So 10.10.2027", _("Ort noch offen"), "Stamm Zugvögel",
                 draft, draft=True),
    ]
    registered, waiting, cancelled = ("ok", _("angemeldet")), ("warte", _("Warteliste")), ("ab", _("abgemeldet"))
    participants = [
        ("Erika Testfrau", "Stamm Walhall", 17, registered),
        ("Kim Beispiel", "Stamm Walhall", 15, registered),
        ("Noah Muster", "Stamm Zugvögel", 16, waiting),
        ("Lina Probe", "Stamm Boreas", 14, cancelled),
        ("Max Testmann", "Stamm Zugvögel", 19, registered),
    ]
    nav_example = [
        {"url": "#inhalt", "label": label, "icon": icon, "active": icon == "home"}
        for label, icon in [(_("Startseite"), "home"), (_("Veranstaltungen"), "kalender"),
                            (_("Teilnehmende"), "personen"), (_("Organisation"), "organisation"),
                            (_("Einstellungen"), "einstellungen")]
    ]
    orgs = ["Stamm Walhall", "Stamm Zugvögel", "Stamm Boreas"]
    context = {"events": events, "participants": participants, "orgs": orgs, "nav_items": nav_example,
               "nav_example": True}
    return render(request, "core/muster.html", context)
