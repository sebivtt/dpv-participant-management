"""Seiten der App „core“."""

import logging

from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, HttpRequest, HttpResponse
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


def _notices(request: HttpRequest) -> dict:
    """Die beiden Warnungen, die Startseite und „Mein Profil“ gleich zeigen: Name fehlt (#5), keiner Organisation zugeordnet (#9)."""
    return {"name_incomplete": _name_incomplete(request.user), "unassigned": not request.rights.has_roles()}


# Zeigt nur die angemeldete Person selbst (BER-01, Grund 1), nie eine andere.
@checks_rights("EP-01", "EP-02")
def start(request: HttpRequest) -> HttpResponse:
    """Startseite nach dem Login: Begrüßung mit dem Vornamen aus Keycloak (#5, ORG-03).

    Nur mit Login erreichbar und zeigt nur die Daten der angemeldeten Person selbst. Fehlt
    in Keycloak der Vor- oder Nachname, steht dort ein Hinweis, ihn im DPV-Konto zu ergänzen;
    ohne Mitgliedschaft und ohne Rolle der Hinweis, dass die Person noch keiner Organisation
    zugeordnet ist (#9). Name und Mail stehen seit #96 auf „Mein Profil“, nicht mehr hier.
    """
    return render(request, "core/start.html", _notices(request))


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
    return any(SCOUT_NAME_TAG in (message.extra_tags or "").split() for message in messages.get_messages(request))


def _profile_page(request: HttpRequest, form: ScoutNameForm, save_failed: bool = False) -> HttpResponse:
    """„Mein Profil“ mit dem Formular für den Fahrtennamen, frisch oder mit der letzten Eingabe."""
    roles = request.rights.own_roles()
    membership = next((role for role in roles if role.kind == Role.Kind.MEMBER), None)
    context = {
        **_notices(request),
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


# Einträge des Bausteinkatalogs (#176): nur Bausteine, die Sebastian an einem Zielbild oder in einer
# Klärung ausdrücklich freigegeben hat. Je Baustein das Vorlagenstück, das Seiten und Katalog
# einbinden, ein Satz zum Zweck, die Issues, die ihn entschieden haben, und die echten Seiten,
# die ihn nutzen. Ohne Seite zeigt der Katalog „noch auf keiner Seite“; ob das stimmt, prüft
# tests/test_bausteinkatalog.py an den Vorlagen.
BUILDING_BLOCKS = {
    "meldungen": {
        "name": _("Meldungen"), "template": "core/_meldung.html", "issues": [165],
        "purpose": _("Sagt in einer von vier Arten, was los ist: Information, wenn nichts zu tun ist; Warnung, "
                     "wenn man selbst etwas tun muss; Fehler, wenn etwas nicht geklappt hat; Erfolg, wenn es "
                     "geklappt hat."),
        "pages": [_("Login-Seite"), _("Startseite"), _("Mein Profil")],
    },
    "textfeld": {
        "name": _("Textfeld"), "template": "core/_textfeld.html", "issues": [111],
        "purpose": _("Eine Eingabe mit Beschriftung, bei Pflichtfeldern „(Pflicht)“, und dem Fehler rot direkt "
                     "darunter; jedes Formular bindet es ein, statt sein Feld selbst zu schreiben. Das Feld zum "
                     "Antippen nutzt dieselbe Eingabe und denselben Fehler."),
        "pages": [],
    },
    "antippfeld": {
        "name": _("Feld zum Antippen"), "template": "core/_antippfeld.html", "issues": [180],
        "purpose": _("Ein einzelnes Feld auf einer Seite mit Angaben: in Ruhe wie eine Angabe, angetippt eine "
                     "Eingabe mit „Verwerfen“ und „Speichern“."),
        "pages": [_("Mein Profil")],
    },
    "angabe": {
        "name": _("Gesperrte Angabe"), "template": "core/_angabe.html", "issues": [161],
        "purpose": _("Zeigt eine Angabe, die sich im Tool nicht ändern lässt: grau, mit Symbol und Schloss."),
        "pages": [_("Mein Profil")],
    },
    "kopfzeile": {
        "name": _("Kopfzeile mit Name"), "template": "core/_kopfzeile.html", "issues": [161, 180],
        "purpose": _("Steht oben auf einer Seite zu einer Person: der Kreis mit dem Anfangsbuchstaben, der "
                     "Fahrtenname groß und der Name kleiner und grauer dahinter."),
        "pages": [_("Mein Profil")],
    },
    "flaechenkopf": {
        "name": _("Überschrift einer Fläche"), "template": "core/_flaechenkopf.html", "issues": [161],
        "purpose": _("Überschrift einer Fläche mit einem Symbol im Kästchen davor."),
        "pages": [_("Mein Profil")],
    },
    "rollenkachel": {
        "name": _("Rollenkachel"), "template": "core/_rollenkachel.html", "issues": [161],
        "purpose": _("Zeigt eine Rolle mit Organisation und Weg darüber; die Mitgliedschaft als eigene "
                     "Fläche, die übrigen Rollen als Kacheln."),
        "pages": [_("Mein Profil")],
    },
    "profilkreis": {
        "name": _("Profilkreis"), "template": "core/_profilkreis.html", "issues": [7, 13],
        "purpose": _("Führt zu „Mein Profil“: der Kreis mit dem Anfangsbuchstaben, in der Seitenleiste mit dem "
                     "Vornamen; ohne Namen ein Personensymbol."),
        "pages": [_("jede Seite mit Login")],
    },
    "testband": {
        "name": _("Band der Testumgebung"), "template": "core/_testband.html", "issues": [58, 165],
        "purpose": _("Steht in der Testumgebung oben auf jeder Seite, damit niemand sie für das echte Tool "
                     "hält."),
        "pages": [_("jede Seite in der Testumgebung")],
    },
    "fehlerseite": {
        "name": _("Knöpfe der Fehlerseite"), "template": "core/_fehler_knoepfe.html", "issues": [21],
        "purpose": _("Führen von einer Fehlerseite zurück oder zur Startseite; „Zurück“ erscheint nur, wenn man "
                     "von einer Seite des Tools kam."),
        "pages": [_("Fehlerseiten")],
    },
}


@without_personal_data("Bausteinkatalog: nur erfundene Beispiele (#176).")
def building_blocks(request: HttpRequest) -> HttpResponse:
    """Bausteinkatalog (#176): jeder entschiedene Baustein mit erfundenen Beispielen.

    Jeder Baustein steht hier über dasselbe Vorlagenstück, das die echten Seiten einbinden,
    damit der Katalog nie vom echten Aussehen abweicht. Nur auf dem eigenen Rechner und in der
    Testumgebung; im Betrieb antwortet die Adresse wie eine, die es nicht gibt, für alle.
    """
    if not settings.BUILDING_BLOCKS_VISIBLE:
        raise Http404
    role = Role.Kind
    examples = {
        # Feld zum Antippen (#180) mit erfundenem Fahrtennamen; eigene Kennungen, damit nichts mit
        # anderen Feldern der Seite zusammenfällt. Das Formular hier schickt nichts ab.
        "scout_name_form": ScoutNameForm(initial={"scout_name": "Kiwi"}, auto_id="katalog_%s"),
        "membership": {"label": _("Mitgliedschaft"), "org": "Sippe Falken", "way": "Pfadfinderbund Boreas › Stamm Walhall"},
        "tiles": [
            {"label": label, "org": org, "way": way} for label, org, way in [
                (role.GROUP_LEAD.label, "Meute Wölfe", "Pfadfinderbund Boreas › Stamm Walhall"),
                (role.TROOP_LEAD.label, "Stamm Walhall vom Nordseestrand", "Pfadfinderbund Boreas"),
                (role.EVENT_TEAM.label, "DPV", ROLE_NOTES[role.EVENT_TEAM]),
                (role.ADMIN.label, _("DPV Anmeldetool"), ROLE_NOTES[role.ADMIN]),
            ]
        ],
        # Der Profilkreis liest nur den kurzen Namen; hier erfunden, nicht der der angemeldeten Person.
        "named": {"short_name": "Kim"},
        "unnamed": {"short_name": ""},
    }
    blocks = {key: dict(block, id=f"h-{key}") for key, block in BUILDING_BLOCKS.items()}
    context = {"blocks": blocks, "examples": examples, "pattern_form": PatternForm.example()}
    return render(request, "core/bausteine.html", context)
