"""Seiten der App „core“."""

import logging

from django.contrib import messages
from django.db import DatabaseError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from access.addresses import checks_rights, without_personal_data
from accounts import texts as account_texts
from accounts.forms import ScoutNameForm
from core.forms import PatternForm
from roles.models import Role

logger = logging.getLogger(__name__)


def _name_incomplete(user) -> bool:
    """Fehlt im DPV-Konto der Vor- oder Nachname? Dann steht ein Hinweis zum Ergänzen da (#5).

    Startseite und „Mein Profil“ fragen beide hier, damit sie dieselbe Regel haben (#96).
    Ein Name nur aus Leerzeichen ist hier schon leer: Der Login entfernt Leerzeichen am Rand (#77).
    """
    return not (user.first_name and user.last_name)


# Zeigt nur die angemeldete Person selbst (BER-01, Grund 1), nie eine andere.
@checks_rights("EP-01", "EP-02")
def start(request: HttpRequest) -> HttpResponse:
    """Startseite nach dem Login: Begrüßung mit dem Vornamen aus Keycloak (#5, ORG-03).

    Nur mit Login erreichbar und zeigt nur die Daten der angemeldeten Person selbst. Fehlt
    in Keycloak der Vor- oder Nachname, steht dort ein Hinweis, ihn im DPV-Konto zu ergänzen.
    Name und Mail stehen seit #96 auf „Mein Profil“, nicht mehr hier.
    """
    return render(request, "core/start.html", {"name_incomplete": _name_incomplete(request.user)})


# Die Adresse hat keine Kennung: Die Seite zeigt immer die angemeldete Person und liest nichts
# aus der Anfrage, auch keine angehängten Parameter oder Formularfelder (EP-02).
@checks_rights("EP-01", "EP-02", "EP-05")
def profile(request: HttpRequest) -> HttpResponse:
    """„Mein Profil“ (#96, PER-01, ORG-05): Angaben, Mitgliedschaft und Rollen.

    Grundregel (Sebastian, 22.10.2026): Die Seite zeigt alles, was das Tool über die Person
    speichert; neue Angaben kommen hier dazu. Ändern lässt sich nur der Fahrtenname (#111, W1);
    Name und Mail kommen bei jedem Login aus dem DPV-Konto (EP-05). Rollen und Einheiten liest
    die Seite bei jedem Aufruf frisch über die zentrale Rechteprüfung. Die Mitgliedschaft steht
    in einer eigenen Fläche, die übrigen Rollen als Kacheln darunter (#161).
    """
    return _profile_page(request, ScoutNameForm(initial={"scout_name": request.user.scout_name}))


# Ändert nur das Konto der Anmeldung: Die Adresse hat keine Kennung, und das Formular nimmt nur
# den Fahrtennamen an; Kennungen im Formular oder in der Adresse bleiben unbeachtet (EP-04).
@checks_rights("EP-03", "EP-04")
def profile_scout_name(request: HttpRequest) -> HttpResponse:
    """Speichert den eigenen Fahrtennamen von „Mein Profil“ (#111, EP-03).

    Gelingt es, geht es zurück zu „Mein Profil“ mit der Erfolgsmeldung; ein Neuladen schickt
    das Formular dann nicht noch einmal. Ist die Eingabe zu lang, zeigt die Seite den Fehler am
    Feld und behält die Eingabe. Scheitert das Speichern technisch, zeigt sie die
    Fehlermeldung; ins Log kommt eine Zeile ohne den Fahrtennamen und ohne Konto (#6).

    Ohne abgeschicktes Feld geht es ohne Speichern zu „Mein Profil“: Wer beim Speichern
    abgemeldet war, landet nach dem Login mit einem einfachen Aufruf hier, und ein Formular ohne
    das Feld ist kein leeres Feld, das den Fahrtennamen löschen dürfte (unabhängige Prüfung).
    """
    if request.method != "POST" or "scout_name" not in request.POST:
        return redirect("profile")
    form = ScoutNameForm(request.POST)
    if not form.is_valid():
        return _profile_page(request, form)
    value = form.cleaned_data["scout_name"]
    try:
        request.user.set_scout_name(value)
    except DatabaseError as error:
        logger.error("Fahrtenname nicht gespeichert: %s", type(error).__name__)
        return _profile_page(request, form, save_failed=True)
    text = account_texts.SCOUT_NAME_SAVED if value else account_texts.SCOUT_NAME_DELETED
    messages.success(request, text, extra_tags=SCOUT_NAME_TAG)
    return redirect("profile")


# Kennzeichen der Meldung nach dem Speichern; daran erkennt „Mein Profil“, dass das Feld den Fokus bekommt.
SCOUT_NAME_TAG = "fahrtenname"


def _scout_name_just_saved(request: HttpRequest) -> bool:
    """Kommt „Mein Profil“ gerade vom Speichern des Fahrtennamens? Dann bekommt das Feld den Fokus (#180, Szenario 9).

    Die Meldungen gelten dabei schon als gelesen; die Seite zeigt sie trotzdem, weil sie in
    derselben Anfrage dieselben bleiben, und beim nächsten Aufruf fehlen Meldung und Fokus.
    """
    return any(SCOUT_NAME_TAG in message.extra_tags.split() for message in messages.get_messages(request))


def _profile_page(request: HttpRequest, form: ScoutNameForm, save_failed: bool = False) -> HttpResponse:
    """„Mein Profil“ mit dem Formular für den Fahrtennamen, frisch oder mit der letzten Eingabe."""
    roles = request.rights.own_roles()
    membership = next((role for role in roles if role.kind == Role.Kind.MEMBER), None)
    context = {
        "name_incomplete": _name_incomplete(request.user),
        "membership": _tile(membership, label=_("Mitgliedschaft")) if membership else None,
        "tiles": [_tile(role) for role in roles if role is not membership],
        "scout_name_form": form,
        "scout_name_just_saved": _scout_name_just_saved(request),
        "save_failed": account_texts.SCOUT_NAME_FAILED if save_failed else "",
    }
    return render(request, "core/profil.html", context)


# Feste Sätze unter Rollen ohne Weg nach oben, statt der Beschreibungen im Zielbild
# (Sebastian, Nachklärung Kacheln zu #161 am 25.10.2026). Nur Text, keine gespeicherten Daten.
ROLE_NOTES = {
    Role.Kind.FEDERATION_LEAD: _("Leitung des Verbands"),
    Role.Kind.EVENT_TEAM: _("Veranstaltungen des Verbands"),
    Role.Kind.ADMIN: _("Verwaltung des ganzen Tools"),
}


def _tile(role: Role, label=None) -> dict:
    """Was eine Kachel unter „Organisation und Rollen“ zeigt: klein die Rolle, groß die Organisation, darunter der Weg (#161).

    Admin hängt an keiner Organisation; dort steht groß „DPV Anmeldetool“. Rollen im Verband
    und Admin zeigen statt des Wegs ihren festen Satz aus `ROLE_NOTES`.
    """
    return {
        "label": label or role.get_kind_display(),
        "org": role.unit.name if role.unit else _("DPV Anmeldetool"),
        "way": ROLE_NOTES.get(role.kind) or " › ".join(role.unit.names_above() if role.unit else []),
    }


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
    role = Role.Kind
    profile_example = {
        "name": "Kim",
        "scout_name": "Kiwi",
        # Feld zum Antippen (#180) mit erfundenem Fahrtennamen; eigene Kennungen, damit nichts mit
        # anderen Feldern der Seite zusammenfällt. Das Formular dort schickt nichts ab.
        "scout_name_form": ScoutNameForm(initial={"scout_name": "Kiwi"}, auto_id="muster_%s"),
        "details": [(_("Vorname"), "Kim", "person"), (_("Nachname"), "", "person"),
                    (_("E-Mail-Adresse"), "kim.beispiel@example.org", "mail")],
        "membership": {"label": _("Mitgliedschaft"), "org": "Sippe Falken", "way": "Pfadfinderbund Boreas › Stamm Walhall"},
        "tiles": [
            {"label": label, "org": org, "way": way} for label, org, way in [
                (role.GROUP_LEAD.label, "Meute Wölfe", "Pfadfinderbund Boreas › Stamm Walhall"),
                (role.TROOP_LEAD.label, "Stamm Walhall vom Nordseestrand", "Pfadfinderbund Boreas"),
                (role.EVENT_TEAM.label, "DPV", ROLE_NOTES[role.EVENT_TEAM]),
                (role.ADMIN.label, _("DPV Anmeldetool"), ROLE_NOTES[role.ADMIN]),
            ]
        ],
    }
    context = {"events": events, "participants": participants, "orgs": orgs, "nav_items": nav_example,
               "nav_example": True, "profile_example": profile_example, "pattern_form": PatternForm.example()}
    return render(request, "core/muster.html", context)
