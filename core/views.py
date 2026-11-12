"""Seiten der App „core“."""

import logging
from datetime import date

from django.conf import settings
from django.contrib import messages
from django.db import DatabaseError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from access.addresses import checks_rights, without_personal_data
from access.keys import is_key, new_key
from access.rights import SUGGESTION_MIN, SUPPORT_REASONS, WILDCARDS, Rights, unit_label
from accounts import texts as account_texts
from accounts.forms import ScoutNameForm
from core.forms import (
    AccountSearchForm,
    FederationSearchForm,
    ManagedPersonAddForm,
    ManagedPersonForm,
    PatternForm,
    UnitNameForm,
)
from persons import texts as person_texts
from persons.models import EDITABLE_FIELDS
from roles import texts as role_texts
from roles.models import Role
from units.models import Unit
from units import texts
from units.organisation import (
    ADD_MANAGED_ID,
    FEDERATION_SLUGS,
    SLUG_OF,
    Federation,
    Hit,
    Lead,
    Mark,
    Node,
    Organisation,
    Page,
    admission,
    create_dialog,
    delete_dialog,
    edit_dialog,
    exit_dialog,
    expulsion_dialog,
    move_dialog,
    federation_done,
    hits,
    edit_anchor,
    managed_dialog,
    rings_question,
    support_dialog,
)

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


# Ändert nur die eigene Rolle: Die Adresse hat keine Kennung, und es gibt höchstens eine Rolle im
# DPV-Veranstaltungsteam je Person (RO-20).
@checks_rights("RO-18", "RO-20")
def profile_leave_team(request: HttpRequest) -> HttpResponse:
    """„Rolle abgeben“ beim DPV-Veranstaltungsteam auf „Mein Profil“: Rückfrage zeigen und abgeben (V10).

    Lesend zeigt die Adresse „Mein Profil“ mit offener Rückfrage; das Formular gibt die Rolle ab.
    Ohne Rolle im Team ist die Adresse „nicht gefunden“ und ändert nichts.
    """
    rights = request.rights
    if request.method == "POST":
        if not rights.leave_team():
            raise Http404
        messages.success(request, texts.FEDERATION_GAVE_UP[Role.Kind.EVENT_TEAM])
        return redirect("profile")
    if request.method not in READING or rights.own_team_role() is None:
        raise Http404
    removal = {"title": texts.FEDERATION_GIVE_UP_QUESTION[Role.Kind.EVENT_TEAM], "lines": [],
               "close_href": reverse("profile"), "confirm_action": request.path, "confirm_label": texts.GIVE_UP_BUTTON}
    form = ScoutNameForm(initial={"scout_name": request.user.scout_name})
    return _profile_page(request, form, removal=removal)


# Ändert nur die eigene Mitgliedschaft: Die Adresse hat keine Kennung einer Person, und die
# Mitgliedschaft kommt nie aus dem Formular; nur die Ebene der eigenen Kette (EP-07, PG6).
@checks_rights("EP-06", "EP-07")
def profile_leave(request: HttpRequest) -> HttpResponse:
    """„Austreten“ auf „Mein Profil“: Dialog mit den Ebenen der eigenen Kette zeigen und austreten (EP-06).

    Lesend zeigt die Adresse „Mein Profil“ mit offenem Dialog; das Formular tritt aus und führt zurück
    zu „Mein Profil“ mit der kurzen Meldung. Ohne Mitgliedschaft ist die Adresse „nicht gefunden“.
    """
    rights = request.rights
    if request.method == "POST":
        messages.success(request, rights.leave_own(request.POST.get("ebene", ""), request.POST.get("von", "")))
        return redirect("profile")
    found = rights.exit_options()
    if request.method not in READING or found is None:
        raise Http404
    removal = exit_dialog(*found, action=request.path)
    return _profile_page(request, ScoutNameForm(initial={"scout_name": request.user.scout_name}), removal=removal)


def _profile_page(request: HttpRequest, form: ScoutNameForm, save_failed: bool = False, removal=None) -> HttpResponse:
    """„Mein Profil“ mit dem Formular für den Fahrtennamen, frisch oder mit der letzten Eingabe."""
    roles = request.rights.own_roles()
    membership = next((role for role in roles if role.kind == Role.Kind.MEMBER), None)
    context = {
        **_notices(request),
        "removal": removal,
        "membership": _tile(membership, label=_("Mitgliedschaft")) if membership else None,
        # Der Knopf „Austreten“ in der Fläche der Mitgliedschaft (#286, EP-06).
        "exit_href": reverse("profile_leave") if membership else None,
        "exit_label": texts.EXIT_BUTTON,
        "tiles": [_tile(role) for role in roles if role is not membership],
        "scout_name_form": form,
        "scout_name_just_saved": _scout_name_just_saved(request),
        "save_failed": account_texts.SCOUT_NAME_FAILED if save_failed else "",
    }
    return render(request, "core/profil.html", context)


# Seite „Organisation“ (#189, Teil 1 von #93), nur Anzeige. Benennen und Entfernen haben eigene
# Adressen (#190, #191); diese Seiten nehmen deshalb nur lesende Aufrufe an. Jede
# andere Anfrage, etwa ein manipuliertes Formular an die Leseseite, zeigt „nicht gefunden“ und
# ändert nichts (AV5).
READING = ("GET", "HEAD")



# Die Adresse hat keine Kennung: Sie zeigt immer die Gliederung der angemeldeten Person (EH-01)
# oder, für die Verbandsleitung, die Seite „Verband“ (#94).
@checks_rights("EH-01", "EH-03", "EH-04", "EH-05", "EH-07", "EH-08", "EH-09", "RO-01", "RO-03", "RO-04", "RO-05",
               "RO-09", "RO-21", "RO-22", "VP-02", "VP-06")
def organisation(request: HttpRequest) -> HttpResponse:
    """„Organisation“: die Gliederung des eigenen Bundes, am PC daneben die Seite der eigenen Organisation.

    Nur für Leitungen von Gruppe bis Bund und die Verbandsleitung (EH-08); alle anderen bekommen
    „kein Zugriff“ (EH-09). Am Handy steht nur die Gliederung; ein Tipp öffnet die Seite der
    Organisation. Die Verbandsleitung sieht die Seite „Verband“, auch wenn sie zusätzlich Leitung
    ist; ihre Bünde öffnet sie von dort (Frage 3 vom 28.10.2026).
    """
    rights = request.rights
    rights.require_section(rights.sees_menu())
    if request.method not in READING:
        raise Http404
    if rights.is_federation_lead():
        return _federation_page(request)
    shown = Organisation(rights, request.user)
    start = shown.start_unit()
    return render(request, "core/organisation.html", {"outline": shown.outline(current=start),
                                                       "page": shown.page(start) if start else None, "start": True})


# Die Organisation kommt nur aus der Adresse, über ihre Kennung (CONTRIBUTING.md, Abschnitt 4).
@checks_rights("EH-01", "EH-03", "EH-07", "EH-09", "EH-28", "RO-01", "RO-03", "RO-04", "RO-09", "RO-21", "RO-22", "VP-02",
               "VP-03", "VP-06")
def organisation_unit(request: HttpRequest, unit: str) -> HttpResponse:
    """Seite einer Organisation: im eigenen Bereich zum Verwalten, auf der Kette nach oben nur zum Lesen (Frage C).

    Jede andere Organisation, auch eine erfundene oder fremde Kennung, ist „nicht gefunden“, genau
    wie eine, die es nicht gibt (RO-04, EH-03, AV1 bis AV6).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.opens_unit)
    if request.method not in READING:
        raise Http404
    shown = Organisation(rights, request.user)
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found),
                                                       "page": shown.page(found), "start": False})


# Leitung benennen (#190, Teil 2 von #93). Der Dialog hat eine eigene Adresse unter der Seite der
# Organisation, damit er auch ohne Skript geht: Der Knopf „… benennen“ führt dorthin, „Suchen“ und
# „Benennen“ schicken Formulare dorthin, und jede Antwort zeigt die Seite mit offenem Dialog. Die
# Organisation kommt immer aus der Adresse, nie aus dem Formular (BV7). Wer dort nicht benennen
# darf, bekommt auf allen drei Adressen „nicht gefunden“, auch per Skript (BV5, BV6, BV8).
APPOINT_ROWS = ("PK-09", "PK-10", "PK-11", "PK-12", "PK-13", "PK-14", "PK-15", "PK-16", "PK-24",
                "RO-10", "RO-11", "RO-12", "RO-13", "RO-14", "RO-17", "EP-08", "VP-14", "VP-15")


def _appointing(request: HttpRequest, unit: str) -> Unit:
    """Die Organisation aus der Adresse, wenn die Person dort Leitungen benennen darf; sonst „nicht gefunden“."""
    rights = request.rights
    return rights.entry(Unit.objects.all(), unit, allowed=rights.may_appoint)


def _appoint_page(request: HttpRequest, found: Unit, form: AccountSearchForm | None = None, hits=None,
                  hits_title="", notice=None) -> HttpResponse:
    """Die Seite der Organisation mit offenem Dialog „… benennen“; `notice` ist (Art, Text) einer Meldung im Dialog."""
    shown = Organisation(request.rights, request.user)
    page = shown.page(found)
    dialog = {
        "title": page.appoint_label,
        "subtitle": texts.APPOINT_FOR % {"unit": found.name},
        "close_href": reverse("organisation_unit", args=[found.key]),
        "form": form or AccountSearchForm(),
        "search_action": reverse("organisation_search", args=[found.key]),
        "suggestions_href": reverse("organisation_suggestions", args=[found.key]),
        "help_text": texts.APPOINT_HELP,
        "appoint_action": reverse("organisation_appoint", args=[found.key]),
        "hits": hits or [],
        "hits_title": hits_title,
        "notice": notice,
    }
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": page,
                                                       "start": False, "dialog": dialog})


@checks_rights(*APPOINT_ROWS)
def organisation_appoint(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „… benennen“ öffnen und eine Person benennen (RO-10, RO-11).

    Lesend zeigt die Adresse den leeren Dialog. Ein Formular mit der Kennung einer Person
    benennt sie; die Rolle gilt sofort, ohne Zustimmung und ohne Nachricht (B2). Danach geht es
    zurück zur Seite der Organisation mit einer kurzen Meldung (B15). Lehnt die Rechteprüfung
    ab, bleibt der Dialog offen und nennt den Grund an der Stelle der Handlung.

    Mit `verwaltet=ja` ist die Kennung die einer verwalteten Person, und eingetragen wird eine angezeigte
    Leitungsrolle ohne Rechte (#99, VP-14). Das Feld wählt nur die Tabelle, in der die Kennung gesucht wird;
    eine Kennung der anderen Art findet dort nichts und ist „nicht gefunden“.
    """
    found = _appointing(request, unit)
    if request.method == "POST":
        appoint = request.rights.appoint_displayed if request.POST.get("verwaltet") == "ja" else request.rights.appoint
        done, text = appoint(found, request.POST.get("person"))
        if done:
            messages.success(request, text)
            return redirect("organisation_unit", unit=found.key)
        return _appoint_page(request, found, notice=("warning", text))
    if request.method not in READING:
        raise Http404
    return _appoint_page(request, found)


@checks_rights(*APPOINT_ROWS)
def organisation_search(request: HttpRequest, unit: str) -> HttpResponse:
    """„Suchen“ im Dialog: ein Konto über die genaue bestätigte Mail oder den genauen Benutzernamen (PK-13, PK-24).

    Jede Suche mit Begriff zählt fürs Suchlimit, auch ohne Treffer; eine abgewiesene nicht. Ein
    leeres Feld oder nur Platzhalterzeichen wie „*“ zeigen nichts und zählen nicht (PK-15).
    Lesend führt die Adresse zum leeren Dialog, etwa nach einem Login mitten im Suchen.
    """
    found = _appointing(request, unit)
    if request.method != "POST":
        if request.method not in READING:
            raise Http404
        return redirect("organisation_appoint", unit=found.key)
    form = AccountSearchForm(request.POST)
    if not form.is_valid():
        return _appoint_page(request, found, form=form)
    text = form.cleaned_data["suche"].strip()
    if not text or set(text) <= WILDCARDS:
        return _appoint_page(request, found, form=form)
    rights = request.rights
    wait = rights.count_search()
    if wait:
        return _appoint_page(request, found, form=form, notice=("error", texts.SEARCH_LIMIT % {"minutes": wait}))
    rights.record_search(lambda checked: checked.may_appoint(found))
    entries = rights.find_accounts(text)
    if not entries:
        return _appoint_page(request, found, form=form, notice=("warning", texts.NO_ACCOUNT))
    return _appoint_page(request, found, form=form, hits=hits(entries, found), hits_title=texts.HITS_TITLE)


@checks_rights(*APPOINT_ROWS)
def organisation_suggestions(request: HttpRequest, unit: str) -> HttpResponse:
    """Vorschläge beim Tippen, nur das Stück mit der Liste; das Skript des Dialogs fragt sie ab (PK-09, PK-10).

    Erst ab 3 Zeichen, höchstens 10, nur Personen im eigenen Bereich; sie zählen nicht als Suche. Der
    getippte Name kommt als Formular, nie in der Adresse, damit er in keinem Protokoll eines
    Webservers landet (unabhängige Prüfung).
    """
    found = _appointing(request, unit)
    if request.method != "POST":
        raise Http404
    text = request.POST.get("suche", "").strip()
    if len(text) >= SUGGESTION_MIN:
        # Vorschläge zeigen Namen von Personen; im Support-Zugang zählen sie wie eine Seite (#92).
        request.rights.record_view(found)
    # Mit der Organisation des Dialogs kommen verwaltete Personen auf ihrem Leitungspfad dazu (#99).
    entries = request.rights.suggestions(text, unit=found)
    context = {"hits": hits(entries, found), "hits_title": texts.SUGGESTIONS_TITLE,
               "empty": texts.NO_SUGGESTIONS if len(text) >= SUGGESTION_MIN else "",
               "appoint_action": reverse("organisation_appoint", args=[found.key])}
    return render(request, "core/_treffer.html", context)


# Leitung entfernen und Rolle abgeben (#191, Teil 3 von #93). Wie beim Benennen hat die Bestätigung
# eine eigene Adresse unter der Seite der Organisation, damit sie auch ohne Skript geht: „Entfernen“
# und „Rolle abgeben“ führen dorthin, der rote Knopf schickt das Formular dorthin. Die Organisation
# kommt aus der Adresse, die Rolle über ihre Kennung; eine Rolle einer anderen Organisation, eine
# Mitgliedschaft, die Verbandsleitung oder Admin sind dort „nicht gefunden“ (CV3).
REMOVE_ROWS = ("RO-10", "RO-11", "RO-13", "RO-14", "RO-17", "RO-18", "RO-19", "RO-20", "RO-21", "RO-22")


@checks_rights(*REMOVE_ROWS)
def organisation_remove(request: HttpRequest, unit: str, role: str) -> HttpResponse:
    """Bestätigung „… entfernen?“ oder „Deine Rolle … abgeben?“ zeigen und die Rolle entfernen.

    Lesend zeigt die Adresse die Seite der Organisation mit offenem Dialog; „Abbrechen“ ändert
    nichts (C9). Das Formular entfernt die Rolle; danach steht die kurze Meldung dort, wohin die
    Person noch darf: auf der Seite der Organisation, sonst in der Übersicht „Organisation“, ohne
    Leitungsrolle auf „Mein Profil“ (C13).
    """
    found = _appointing(request, unit)
    rights = request.rights
    if request.method == "POST":
        messages.success(request, rights.remove(found, role))
        return redirect(_after_removal(request, found))
    if request.method not in READING:
        raise Http404
    shown = Organisation(rights, request.user)
    removal = shown.removal(found, rights.removal(found, role), action=request.path)
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": shown.page(found),
                                                       "start": False, "removal": removal})


# Angezeigte Leitungsrollen verwalteter Personen entfernen (#99, PER-07). Eigene Adresse neben der für Rollen
# mit Konto (#191), damit eine Kennung der einen Art unter der anderen nie etwas findet.
DISPLAYED_ROWS = ("VP-14", "VP-15", "VP-16", "RO-09")


@checks_rights(*DISPLAYED_ROWS)
def organisation_remove_displayed(request: HttpRequest, unit: str, role: str) -> HttpResponse:
    """Bestätigung „… entfernen?“ zeigen und die angezeigte Leitungsrolle entfernen (VP-14, L6).

    Wie beim Entfernen einer Leitung mit Konto (#191): Lesend zeigt die Adresse die Seite der Organisation
    mit offenem Dialog, das Formular entfernt und führt zur Seite mit der kurzen Meldung. Die eigenen Rechte
    ändern sich dabei nie, weil die angezeigte Rolle keine gibt.
    """
    found = _appointing(request, unit)
    rights = request.rights
    if request.method == "POST":
        messages.success(request, rights.remove_displayed(found, role))
        return redirect("organisation_unit", unit=found.key)
    if request.method not in READING:
        raise Http404
    shown = Organisation(rights, request.user)
    return _with_dialog(request, found, shown.removal(found, rights.displayed_removal(found, role), action=request.path))


def _after_removal(request: HttpRequest, found: Unit) -> str:
    """Wohin es nach dem Entfernen geht; die Rechte frisch, weil die eigene Rolle gerade weg sein kann."""
    rights = Rights(request.user)
    if rights.opens_unit(found):
        return reverse("organisation_unit", args=[found.key])
    if rights.sees_organisation():
        return reverse("organisation")
    return reverse("profile")


# Person aufnehmen (#285, Teil 1 von #65). Wie beim Benennen hat der Dialog eine eigene Adresse unter
# der Seite der Organisation, damit er auch ohne Skript geht: „Person aufnehmen“ führt dorthin,
# „Suchen“ und „Aufnehmen“ schicken Formulare dorthin. Vorschläge beim Tippen gibt es nicht (#65 N3).
# Die Organisation kommt immer aus der Adresse, nie aus dem Formular. Wer dort nicht aufnehmen darf,
# bekommt auf beiden Adressen „nicht gefunden“, auch per Skript (PK-23, PK-26, EP-08).
ADMIT_ROWS = ("PK-13", "PK-16", "PK-17", "PK-18", "PK-23", "PK-24", "PK-26", "EP-08", "EH-18")


def _admitting(request: HttpRequest, unit: str) -> Unit:
    """Die Organisation aus der Adresse, wenn die Person dort aufnehmen darf; sonst „nicht gefunden“."""
    rights = request.rights
    return rights.entry(Unit.objects.all(), unit, allowed=rights.may_admit)


def _admit_page(request: HttpRequest, found: Unit, form: FederationSearchForm | None = None, hits_found=None,
                notice=None) -> HttpResponse:
    """Die Seite der Organisation mit offenem Dialog „Person aufnehmen“; `notice` ist (Art, Text) einer Meldung."""
    shown = Organisation(request.rights, request.user)
    page = shown.page(found)
    dialog = {
        "title": texts.ADMIT_TITLE,
        "subtitle": texts.ADMIT_FOR % {"unit": unit_label(found)},
        "close_href": reverse("organisation_unit", args=[found.key]),
        "form": form or FederationSearchForm(),
        "help_text": texts.ADMIT_HELP,
        "search_action": reverse("organisation_admit_search", args=[found.key]),
        "appoint_action": reverse("organisation_admit", args=[found.key]),
        "action_label": texts.ADMIT_BUTTON,
        "hits": hits_found or [],
        "hits_title": texts.HITS_TITLE if hits_found else "",
        "notice": notice,
    }
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": page,
                                                       "start": False, "dialog": dialog})


@checks_rights(*ADMIT_ROWS)
def organisation_admit(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „Person aufnehmen“ öffnen und eine Person mit Konto als Mitglied aufnehmen (PK-17).

    Lesend zeigt die Adresse den leeren Dialog. Ein Formular mit der Kennung einer Person nimmt sie
    auf; die Mitgliedschaft gilt sofort, ohne Zustimmung und ohne Nachricht. Danach geht es zurück
    zur Seite der Organisation mit einer kurzen Meldung (#186). Lehnt die Rechteprüfung ab, bleibt
    der Dialog offen und nennt den Grund an der Stelle der Handlung.
    """
    found = _admitting(request, unit)
    if request.method == "POST":
        done, text = request.rights.admit(found, request.POST.get("person"))
        if done:
            messages.success(request, text)
            return redirect("organisation_unit", unit=found.key)
        return _admit_page(request, found, notice=("warning", text))
    if request.method not in READING:
        raise Http404
    return _admit_page(request, found)


@checks_rights(*ADMIT_ROWS)
def organisation_admit_search(request: HttpRequest, unit: str) -> HttpResponse:
    """„Suchen“ im Dialog „Person aufnehmen“: über die genaue bestätigte Mail oder den genauen Benutzernamen (PK-13).

    Zählt zum selben Suchlimit wie das Benennen (PK-24, PG7); leer und nur Platzhalter zeigen
    nichts und zählen nicht (PK-15). Lesend führt die Adresse zum leeren Dialog.
    """
    found = _admitting(request, unit)
    if request.method != "POST":
        if request.method not in READING:
            raise Http404
        return redirect("organisation_admit", unit=found.key)
    form = FederationSearchForm(request.POST)
    if not form.is_valid():
        return _admit_page(request, found, form=form)
    text = form.cleaned_data["suche"].strip()
    if not text or set(text) <= WILDCARDS:
        return _admit_page(request, found, form=form)
    rights = request.rights
    wait = rights.count_search()
    if wait:
        return _admit_page(request, found, form=form, notice=("error", texts.SEARCH_LIMIT % {"minutes": wait}))
    rights.record_search(lambda checked: checked.may_admit(found))
    entries = rights.find_accounts(text)
    if not entries:
        return _admit_page(request, found, form=form, notice=("warning", texts.NO_ACCOUNT))
    hits_found, notice = admission(entries, found)
    return _admit_page(request, found, form=form, hits_found=hits_found, notice=notice)


# Austragen (#286, Teil 2 von #65). Wie beim Entfernen hat der Dialog eine eigene Adresse unter der
# Seite der Organisation, damit er auch ohne Skript geht: „Austragen“ führt dorthin, der rote Knopf
# schickt die Wahl dorthin. Die Organisation kommt immer aus der Adresse, die Person über ihre Kennung,
# nie aus dem Formular. Wer dort nicht austragen darf oder wer kein direktes Mitglied der Organisation
# ist, ist „nicht gefunden“, auch per Skript (PK-22, PK-23).
EXPEL_ROWS = ("PK-21", "PK-22", "PK-23", "EH-18", "EH-19")


@checks_rights(*EXPEL_ROWS)
def organisation_expel(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Dialog „… austragen?“ mit der Wahl zeigen und die Person austragen (PK-21).

    Lesend zeigt die Adresse die Seite der Organisation mit offenem Dialog; „Abbrechen“ ändert nichts.
    Das Formular trägt aus; danach steht die kurze Meldung dort, wohin die Person noch darf, wie nach
    dem Entfernen (auch wer sich selbst austrägt, kann dabei die Seite verlieren).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_expel)
    if request.method == "POST":
        messages.success(request, rights.expel(found, person, request.POST.get("wahl", "")))
        return redirect(_after_removal(request, found))
    if request.method not in READING:
        raise Http404
    shown = Organisation(rights, request.user)
    removal = expulsion_dialog(found, rights.expulsion(found, person), action=request.path)
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": shown.page(found),
                                                       "start": False, "removal": removal})


# Verschieben (#287, Teil 3 von #65). Wie beim Austragen hat der Dialog eine eigene Adresse unter der
# Seite der Organisation, damit er auch ohne Skript geht. Die Organisation der Person kommt immer aus
# der Adresse, die Person über ihre Kennung, das Ziel nur aus den Organisationen direkt darunter.
MOVE_ROWS = ("PK-19", "PK-20", "PK-23", "PK-25", "EP-10", "EH-18", "EH-19")


@checks_rights(*MOVE_ROWS)
def organisation_move(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Dialog „Verschieben“ zeigen und die Person in eine Organisation direkt darunter verschieben (PK-19).

    Lesend zeigt die Adresse die Seite der Organisation mit offenem Dialog; „Abbrechen“ ändert nichts.
    Das Formular verschiebt und führt zurück zur Seite der Organisation mit der kurzen Meldung (#186);
    die eigenen Rechte ändern sich dabei nie, weil Leitungsrollen beim Verschieben bleiben. Passt
    eine Leitungsrolle nicht zum Ziel, bleibt der Dialog offen, nennt sie und lässt das Ziel gewählt (PK-25).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_move)
    notice, chosen = "", ""
    if request.method == "POST":
        chosen = request.POST.get("ziel", "")
        done, text = rights.move(found, person, chosen)
        if done:
            messages.success(request, text)
            return redirect("organisation_unit", unit=found.key)
        notice = text
    elif request.method not in READING:
        raise Http404
    shown = Organisation(rights, request.user)
    removal = move_dialog(found, rights.moving(found, person), action=request.path, notice=notice, chosen=chosen)
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": shown.page(found),
                                                       "start": False, "removal": removal})


# Organisationen anlegen und bearbeiten (#95, ORG-06). Wie beim Verschieben hat jeder Dialog eine eigene
# Adresse unter der Seite der Organisation, damit er auch ohne Skript geht. Die Organisation darüber und die
# Art der neuen Organisation kommen immer aus der Adresse, nie aus dem Formular (OV1, OV4); das Formular
# bringt nur den Namen oder den gewählten Ring. Wer dort nicht darf, bekommt „nicht gefunden“, auch per
# Skript. Einen Löschknopf gibt es nicht (EH-21), ebenso kein Ausschalten von „hat Ringe“ (EH-25).
STRUCTURE_ROWS = ("EH-10", "EH-11", "EH-12", "EH-13", "EH-14", "EH-15", "EH-16", "EH-17", "EH-18", "EH-19",
                  "EH-20", "EH-21", "EH-23", "EH-24", "EH-25", "EH-26", "EH-27")


def _with_dialog(request: HttpRequest, found: Unit, dialog: dict) -> HttpResponse:
    """Die Seite der Organisation mit offenem Dialog, der kommt offen vom Server."""
    shown = Organisation(request.rights, request.user)
    return render(request, "core/organisation.html", {"outline": shown.outline(current=found), "page": shown.page(found),
                                                       "start": False, "removal": dialog})


@checks_rights(*STRUCTURE_ROWS)
def organisation_create(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „Gruppe anlegen“, „Stamm anlegen“ oder „Ring anlegen“ zeigen und anlegen (EH-10 bis EH-12).

    Danach steht die neue Organisation unter „Organisationen darunter“ der Seite, von der aus sie
    angelegt wurde, mit der kurzen Meldung (#186); sonst bleibt der Dialog offen, mit dem Grund als
    Fehler am Feld und der Eingabe darin.
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_create)
    if request.method == "POST":
        form = UnitNameForm(request.POST)
        if form.is_valid():
            done, text = rights.create(found, form.cleaned_data["name"])
            if done:
                messages.success(request, text)
                return redirect("organisation_unit", unit=found.key)
            form.add_error("name", text)
    elif request.method in READING:
        form = UnitNameForm()
    else:
        raise Http404
    return _with_dialog(request, found, create_dialog(found, form, action=request.path))


@checks_rights(*STRUCTURE_ROWS)
def organisation_edit(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „… bearbeiten“ zeigen und speichern: Name, Ring und „hat Ringe“ (EH-14, EH-16, EH-23).

    Den Stift und die Adresse hat, wer die Organisation umbenennen darf; Ring und Schalter zeigt
    der Dialog nur der Bundesleitung. Wird „hat Ringe“ neu eingeschaltet, kommt vor dem Speichern
    die Rückfrage aus O8. Gespeichert wird alles zusammen oder nichts; danach je Änderung eine kurze
    Meldung (#186). Bei einer Ablehnung bleibt der Dialog mit der Eingabe offen.

    Der Dialog schickt mit, was er beim Öffnen gezeigt hat (`name_vorher`, `ring_vorher`). Was die
    Person nicht geändert hat, gilt als „bleibt“, auch wenn inzwischen jemand anderes es geändert hat;
    so dreht ein veralteter Stand keine gleichzeitige Änderung zurück (OG4, unabhängige Prüfung, Befund 1).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.select_related("parent"), unit, allowed=rights.may_rename)
    ring_key = request.POST.get("ring") if request.method == "POST" else None
    rings_on = request.method == "POST" and request.POST.get("hat_ringe") == "an"
    shown_name = request.POST.get("name_vorher") if request.method == "POST" else None
    shown_ring = request.POST.get("ring_vorher") if request.method == "POST" else None
    notice = ""
    if request.method == "POST":
        form = UnitNameForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            if rings_on and request.POST.get("bestaetigt") != "ja" and rights.may_introduce_rings(found):
                return _with_dialog(request, found, rings_question(found, action=request.path, name=name,
                                                                   shown_name=shown_name))
            result = rights.edit(found, name=None if name == shown_name else name,
                                 ring_key=None if ring_key == shown_ring else ring_key, rings_on=rings_on)
            if not result["errors"]:
                for text in result["messages"]:
                    messages.success(request, text)
                return redirect("organisation_unit", unit=found.key)
            if "name" in result["errors"]:
                form.add_error("name", result["errors"]["name"])
            notice = result["errors"].get("ring", "")
    elif request.method in READING:
        form = UnitNameForm(initial={"name": found.name})
    else:
        raise Http404
    rings = rights.rings_of(found) if rights.may_change_ring(found) else None
    # Den Schalter sieht nur die Bundesleitung des Bundes selbst, eingeschaltet gesperrt (EH-23, EH-24, EH-25).
    switch = found.kind == Unit.Kind.ASSOCIATION and rights.leads_itself(found)
    dialog = edit_dialog(found, form, action=request.path, rings=rings, rings_switch=switch, ring_key=ring_key or "",
                         rings_on=rings_on, ring_notice=notice, shown_name=shown_name, shown_ring=shown_ring)
    return _with_dialog(request, found, dialog)


# Verwaltete Personen anlegen und bearbeiten (#117, PER-02). Wie die übrigen Dialoge der Seite hat jeder eine
# eigene Adresse unter der Seite der Organisation, damit er auch ohne Skript geht. Die Organisation kommt immer
# aus der Adresse, die Person über ihre Kennung, nie aus dem Formular (MV4).
ADD_MANAGED_ROWS = ("VP-01", "VP-03", "VP-06", "VP-17", "EH-18")
EDIT_MANAGED_ROWS = ("VP-02", "VP-03", "VP-04", "VP-05", "VP-06")


@checks_rights(*ADD_MANAGED_ROWS)
@never_cache
def organisation_add_managed(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „Verwaltete Person anlegen“ zeigen und die Person in dieser Organisation anlegen (VP-01, EH-18).

    Den Knopf und die Adresse hat nur, wer dort anlegen darf (VP-17). Der Dialog bekommt beim Öffnen eine
    eigene Kennung (`creation_key`), damit ein Doppelklick niemanden zweimal anlegt (MG7). Danach geht es
    zurück zur Seite, zum Knopf, mit der kurzen Meldung (#186); bei einem Fehler bleibt der Dialog mit
    den Eingaben und dem Fehler am Feld offen. Eine Kennung des Dialogs in falscher Form ist „nicht gefunden“.
    Der Browser speichert den Dialog nicht: Nach „Zurück“ kommt er neu, mit neuer Kennung, sonst legte ein
    zweites Anlegen daraus stillschweigend niemanden an (unabhängige Prüfung, Befund 2).
    Unter den Feldern steht der Regler der Einwilligung, beim Öffnen auf „aus“ (#98, DSG-02).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_add_managed)
    if request.method == "POST":
        creation_key = request.POST.get("creation_key", "")
        if not is_key(creation_key):
            raise Http404
        form = ManagedPersonAddForm(request.POST)
        if form.is_valid():
            text = rights.add_managed(found, form.cleaned_data, creation_key)
            if text:
                messages.success(request, text)
            return redirect(f"{reverse('organisation_unit', args=[found.key])}#{ADD_MANAGED_ID}")
    elif request.method in READING:
        form, creation_key = ManagedPersonAddForm(), new_key()
    else:
        raise Http404
    dialog = managed_dialog(found, form, action=request.path, hidden=[("creation_key", creation_key)])
    return _with_dialog(request, found, dialog)


@checks_rights(*EDIT_MANAGED_ROWS)
def organisation_edit_managed(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Dialog „… bearbeiten“ einer verwalteten Person zeigen und ihre Angaben speichern (VP-02).

    Die Organisation kommt aus der Adresse, die Person über ihre Kennung; gehört sie nicht direkt zu dieser
    Organisation oder darf die Person sie nicht sehen, ist das „nicht gefunden“ (VP-03, MV4, MV5), auch
    für eine gerade entfernte Leitung im schon offenen Dialog (MW1). Der Dialog schickt den Stand beim
    Öffnen mit (`version`); hat inzwischen jemand anderes gespeichert, zeigt er dessen Stand mit dem Satz
    aus MG6 und überschreibt nichts. Danach geht es zurück zur Seite, zum Knopf „Bearbeiten“. Seit #118
    steht links unten „Verwaltete Person löschen“, nur für wer löschen darf (VP-09, VP-10).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit)
    entry = rights.managed_person(found, person)
    conflict = ""
    if request.method == "POST":
        version = request.POST.get("version", "")
        form = ManagedPersonForm(request.POST)
        if form.is_valid():
            done, entry, text = rights.edit_managed(found, person, form.cleaned_data, version)
            if done:
                messages.success(request, text)
                return redirect(f"{reverse('organisation_unit', args=[found.key])}#{edit_anchor(entry)}")
            form, version, conflict = ManagedPersonForm(initial=_managed_values(entry)), entry.version, text
    elif request.method in READING:
        form, version = ManagedPersonForm(initial=_managed_values(entry)), entry.version
    else:
        raise Http404
    # Den Knopf „Verwaltete Person löschen“ hat nur, wer löschen darf, nicht jede, die bearbeiten darf (#118, N5).
    delete_href = (reverse("organisation_delete_managed", args=[found.key, entry.key])
                   if rights.may_delete_managed(found) else None)
    dialog = managed_dialog(found, form, action=request.path, entry=entry, hidden=[("version", version)],
                            conflict=conflict, delete_href=delete_href)
    return _with_dialog(request, found, dialog)


# Verschieben, Austragen und Löschen verwalteter Personen (#118, PER-02). Wie bei Personen mit Konto (#286,
# #287) hat jeder Dialog eine eigene Adresse unter der Seite der Organisation, damit er auch ohne Skript geht.
# Die Organisation der Person kommt immer aus der Adresse, die Person über ihre Kennung, das Ziel beim
# Verschieben nur aus den Organisationen direkt darunter. Wer dort nicht darf, bekommt „nicht gefunden“,
# auch per Skript; Kennungen von Personen mit Konto finden hier nie etwas (VV6).
MOVE_MANAGED_ROWS = ("VP-07", "VP-08", "EH-18", "EH-19")
EXPEL_MANAGED_ROWS = ("VP-18", "EH-18", "EH-19")
DELETE_MANAGED_ROWS = ("VP-09", "VP-10", "EH-18", "EH-19")


@checks_rights(*MOVE_MANAGED_ROWS)
def organisation_move_managed(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Dialog „Verschieben“ einer verwalteten Person zeigen und sie in eine Organisation direkt darunter verschieben (VP-07).

    Derselbe Dialog wie bei Personen mit Konto (#287). Danach geht es zurück zur Seite mit der kurzen Meldung.
    Passt eine angezeigte Leitungsrolle nicht zum Ziel, bleibt der Dialog offen, nennt sie und lässt das Ziel
    gewählt, wie PK-25 bei Personen mit Konto (#99, LG2).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_move)
    notice, chosen = "", ""
    if request.method == "POST":
        chosen = request.POST.get("ziel", "")
        done, text = rights.move_managed(found, person, chosen)
        if done:
            messages.success(request, text)
            return redirect("organisation_unit", unit=found.key)
        notice = text
    elif request.method not in READING:
        raise Http404
    dialog = move_dialog(found, rights.moving_managed(found, person), action=request.path, notice=notice, chosen=chosen)
    return _with_dialog(request, found, dialog)


@checks_rights(*EXPEL_MANAGED_ROWS)
def organisation_expel_managed(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Dialog „… austragen?“ einer verwalteten Person zeigen und sie eine Ebene nach oben austragen (VP-18).

    Derselbe Dialog wie bei Personen mit Konto (#286), mit der einzigen Möglichkeit „gehört danach direkt zu …“.
    Danach geht es zurück zur Seite mit der kurzen Meldung; die eigenen Rechte ändern sich dabei nicht.
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_expel_managed)
    if request.method == "POST":
        messages.success(request, rights.expel_managed(found, person, request.POST.get("wahl", "")))
        return redirect("organisation_unit", unit=found.key)
    if request.method not in READING:
        raise Http404
    removal = expulsion_dialog(found, rights.expulsion_managed(found, person), action=request.path)
    return _with_dialog(request, found, removal)


@checks_rights(*DELETE_MANAGED_ROWS)
def organisation_delete_managed(request: HttpRequest, unit: str, person: str) -> HttpResponse:
    """Rückfrage „… endgültig löschen?“ zeigen und die verwaltete Person endgültig löschen (VP-09).

    Lesend zeigt die Adresse die Rückfrage im Dialog „Bearbeiten“; „Nicht löschen“ führt zurück in ihn, × zur
    Seite. „Endgültig löschen“ löscht und führt zur Seite mit der kurzen Meldung „… wurde gelöscht.“.
    """
    rights = request.rights
    found = rights.entry(Unit.objects.all(), unit, allowed=rights.may_delete_managed)
    if request.method == "POST":
        messages.success(request, rights.delete_managed(found, person))
        return redirect("organisation_unit", unit=found.key)
    if request.method not in READING:
        raise Http404
    return _with_dialog(request, found, delete_dialog(found, rights.deleting_managed(found, person), action=request.path))


def _managed_values(entry) -> dict:
    """Die gespeicherten Angaben einer verwalteten Person für den Dialog „… bearbeiten“."""
    return {name: getattr(entry, name) for name in EDITABLE_FIELDS}


# Seite „Verband“ der Verbandsleitung (#94). Benennen und Entfernen haben wie auf der Seite einer
# Organisation eigene Adressen, damit die Dialoge ohne Skript gehen; sie liegen unter
# „/organisation/verband/“, weil die Verbandsleitung die Seite eines Bundes nicht öffnet (EH-05).
# Rolle und Organisation kommen immer aus der Adresse, nie aus dem Formular. Ohne Rolle
# Verbandsleitung sind alle diese Adressen „nicht gefunden“, auch per Skript (RO-18, VV7).
FEDERATION_ROWS = ("PK-12", "PK-13", "PK-14", "PK-15", "PK-16", "PK-24", "RO-12", "RO-14", "RO-15", "RO-16",
                   "RO-17", "RO-18", "RO-19", "RO-20", "EH-27")


def _federation_page(request: HttpRequest, dialog=None, removal=None, status=200) -> HttpResponse:
    """Die Seite „Verband“, auf Wunsch mit offenem Dialog zum Benennen oder zur Bestätigung."""
    shown = Federation(request.rights, request.user)
    federation_key = [shown.federation.key] if shown.federation else None
    context = {
        "federation_leads": shown.federation_leads(),
        "team": shown.team(),
        "associations": shown.associations(),
        "appoint_federation_lead": federation_key and reverse(f"federation_appoint_{SLUG_OF[Role.Kind.FEDERATION_LEAD]}",
                                                              args=federation_key),
        "appoint_team": federation_key and reverse(f"federation_appoint_{SLUG_OF[Role.Kind.EVENT_TEAM]}", args=federation_key),
        # Dieselben Wortlaute wie die Titel der Dialoge, damit Knopf und Dialog gleich heißen.
        "labels": {"federation_lead": texts.APPOINT_FEDERATION_LEAD, "team": texts.APPOINT_TEAM,
                   "association_lead": texts.APPOINT_TITLE % {"role": Role.Kind.ASSOCIATION_LEAD.label}},
        "dialog": dialog,
        "removal": removal,
    }
    return render(request, "core/verband.html", context, status=status)


def _federation_target(request: HttpRequest, unit: str, slug: str | None = None) -> tuple[str, Unit]:
    """Rolle und Organisation des Dialogs aus der Adresse: ohne `slug` ein Bund, sonst der Verband; ohne Recht „nicht gefunden“ (VV7)."""
    rights = request.rights
    if not rights.is_federation_lead():
        raise Http404
    if slug is None:
        found = rights.entry(Unit.objects.filter(kind=Unit.Kind.ASSOCIATION), unit)
        return Role.Kind.ASSOCIATION_LEAD, found
    kind = FEDERATION_SLUGS.get(slug)
    if kind is None:
        raise Http404
    return kind, rights.entry(Unit.objects.filter(kind=Unit.Kind.FEDERATION), unit)


def _federation_dialog(request: HttpRequest, kind: str, found: Unit, form=None, hits_found=None, notice=None):
    """Der Dialog „… benennen“ der Verbandsleitung: nur „Suchen“ über Mail oder Benutzernamen, keine Vorschläge (PK-12)."""
    if kind == Role.Kind.ASSOCIATION_LEAD:
        title, subtitle = texts.APPOINT_TITLE % {"role": kind.label}, texts.APPOINT_FOR % {"unit": found.name}
        search_action = reverse("federation_search_lead", args=[found.key])
        appoint_action = reverse("federation_appoint_lead", args=[found.key])
    else:
        title = texts.APPOINT_FEDERATION_LEAD if kind == Role.Kind.FEDERATION_LEAD else texts.APPOINT_TEAM
        subtitle = texts.APPOINT_FOR_FEDERATION if kind == Role.Kind.FEDERATION_LEAD else texts.APPOINT_FOR_TEAM
        search_action = reverse(f"federation_search_{SLUG_OF[kind]}", args=[found.key])
        appoint_action = reverse(f"federation_appoint_{SLUG_OF[kind]}", args=[found.key])
    dialog = {
        "title": title,
        "subtitle": subtitle,
        "close_href": reverse("organisation"),
        "form": form or FederationSearchForm(),
        "search_action": search_action,
        "appoint_action": appoint_action,
        "hits": hits_found or [],
        "hits_title": texts.HITS_TITLE if hits_found else "",
        "notice": notice,
    }
    return _federation_page(request, dialog=dialog)


def _federation_appoint(request: HttpRequest, kind: str, found: Unit) -> HttpResponse:
    if request.method == "POST":
        done, text, _values = request.rights.appoint_in_federation(kind, found, request.POST.get("person"))
        if done:
            messages.success(request, text)
            return redirect("organisation")
        return _federation_dialog(request, kind, found, notice=("warning", text))
    if request.method not in READING:
        raise Http404
    return _federation_dialog(request, kind, found)


def _federation_search(request: HttpRequest, kind: str, found: Unit, again: str) -> HttpResponse:
    """„Suchen“ wie bei `organisation_search()`: zählt fürs Suchlimit, leer und nur Platzhalter zählen nicht."""
    if request.method != "POST":
        if request.method not in READING:
            raise Http404
        return redirect(again)
    form = FederationSearchForm(request.POST)
    if not form.is_valid():
        return _federation_dialog(request, kind, found, form=form)
    text = form.cleaned_data["suche"].strip()
    if not text or set(text) <= WILDCARDS:
        return _federation_dialog(request, kind, found, form=form)
    rights = request.rights
    wait = rights.count_search()
    if wait:
        return _federation_dialog(request, kind, found, form=form, notice=("error", texts.SEARCH_LIMIT % {"minutes": wait}))
    entries = rights.find_accounts(text)
    if not entries:
        return _federation_dialog(request, kind, found, form=form, notice=("warning", texts.NO_ACCOUNT))
    return _federation_dialog(request, kind, found, form=form, hits_found=hits(entries, found, kind=kind))


@checks_rights(*FEDERATION_ROWS)
def federation_appoint(request: HttpRequest, unit: str, role: str) -> HttpResponse:
    """Dialog „Verbandsleitung benennen“ oder „Teammitglied benennen“ öffnen und benennen (RO-15, V6)."""
    kind, found = _federation_target(request, slug=role, unit=unit)
    return _federation_appoint(request, kind, found)


@checks_rights(*FEDERATION_ROWS)
def federation_search(request: HttpRequest, unit: str, role: str) -> HttpResponse:
    """„Suchen“ im Dialog für Verbandsleitung oder Team (PK-13, PK-24)."""
    kind, found = _federation_target(request, slug=role, unit=unit)
    return _federation_search(request, kind, found, reverse(f"federation_appoint_{role}", args=[found.key]))


@checks_rights(*FEDERATION_ROWS)
def federation_appoint_lead(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „Bundesleitung benennen“ für einen Bund öffnen und benennen (RO-15, V4, V5)."""
    kind, found = _federation_target(request, unit=unit)
    return _federation_appoint(request, kind, found)


@checks_rights(*FEDERATION_ROWS)
def federation_search_lead(request: HttpRequest, unit: str) -> HttpResponse:
    """„Suchen“ im Dialog „Bundesleitung benennen“ (PK-13, PK-24)."""
    kind, found = _federation_target(request, unit=unit)
    return _federation_search(request, kind, found, reverse("federation_appoint_lead", args=[found.key]))


@checks_rights(*FEDERATION_ROWS)
def federation_remove(request: HttpRequest, role: str) -> HttpResponse:
    """Bestätigung zum Entfernen oder Abgeben auf der Seite „Verband“ zeigen und die Rolle entfernen (V7 bis V9).

    Nur Bundesleitungen, Verbandsleitungen und Teammitglieder; jede andere Kennung, etwa die einer
    Stammesleitung, einer Mitgliedschaft oder von Admin, ist „nicht gefunden“ (VV5, VV9). Nach dem
    Entfernen steht die kurze Meldung auf der Seite „Verband“, ohne Rolle mehr dort auf „Mein Profil“.
    """
    rights = request.rights
    if request.method == "POST":
        removed, shown = rights.remove_in_federation(role)
        messages.success(request, federation_done(removed, shown))
        return redirect("organisation" if Rights(request.user).sees_menu() else "profile")
    if request.method not in READING:
        raise Http404
    found, shown = rights.removal_in_federation(role)
    removal = Federation(rights, request.user).removal(found, shown, action=request.path)
    return _federation_page(request, removal=removal)


# Support-Zugang der Admins (#92, BER-02). Der Dialog hat wie die übrigen eine eigene Adresse unter der Seite der
# Organisation, damit er auch ohne Skript geht; die Organisation kommt nur aus der Adresse. „beenden“ im Balken
# schickt ein Formular an eine Adresse ohne Kennung. Wer nicht Admin ist, bekommt beim Starten „nicht gefunden“
# und beim Beenden „kein Zugriff“, auch per Skript (SZ-02, SV3).
SUPPORT_ROWS = ("SZ-01", "SZ-02", "SZ-03", "SZ-04", "SZ-05", "SZ-06", "PR-05", "PR-06")


@checks_rights(*SUPPORT_ROWS)
def organisation_support(request: HttpRequest, unit: str) -> HttpResponse:
    """Dialog „Support-Zugang für … starten“ zeigen und den Zugang mit Anlass starten (SZ-01).

    Ohne gewählten Anlass oder mit einem Wert außerhalb der festen Liste bleibt der Dialog offen und
    sagt „Bitte wähle einen Anlass.“; es startet nichts (SV6). Danach geht es zur Seite der
    Organisation mit der kurzen Meldung, bei einem Wechsel mit beiden Sätzen (S7).
    """
    rights = request.rights
    found = rights.entry(Unit.objects.select_related("parent"), unit, allowed=rights.may_support)
    notice = ""
    if request.method == "POST":
        reason = request.POST.get("anlass", "")
        if reason in SUPPORT_REASONS:
            text = rights.start_support(found, reason)
            if text:
                messages.success(request, text)
            return redirect("organisation_unit", unit=found.key)
        notice = role_texts.SUPPORT_CHOOSE_REASON
    elif request.method not in READING:
        raise Http404
    return _with_dialog(request, found, support_dialog(found, action=request.path, notice=notice))


@checks_rights(*SUPPORT_ROWS)
def support_end(request: HttpRequest) -> HttpResponse:
    """„beenden“ im Balken: den laufenden Support-Zugang beenden; danach zur Seite seiner Organisation (S6).

    Nur per Formular. Läuft keiner mehr, etwa nach „beenden“ in einem zweiten Fenster, geht es ohne
    Meldung zu „Organisation“.
    """
    rights = request.rights
    rights.require_section(rights.is_admin())
    if request.method != "POST":
        raise Http404
    support = rights.support
    text = rights.end_support()
    if text:
        messages.success(request, text)
    # Ohne Organisation, etwa nach dem Notfall-Löschen, geht es zu „Organisation“ (Befund 3).
    if not text or support is None:
        return redirect("organisation")
    return redirect("organisation_unit", unit=support.unit.key)


def _tile(role: Role, label=None) -> dict:
    """Was eine Kachel unter „Organisation und Rollen“ zeigt: klein die Rolle, groß die Organisation (#161).

    Nur die Mitgliedschaft zeigt darunter den Weg nach oben (ORG-05); die Rollen zeigen keine
    zweite Zeile (#219). Admin hängt an keiner Organisation; dort steht groß „DPV Anmeldetool“.
    Beim DPV-Veranstaltungsteam steht darunter „Rolle abgeben“ (#94).
    """
    return {
        "label": label or role.get_kind_display(),
        "org": role.unit.name if role.unit else _("DPV Anmeldetool"),
        "way": " › ".join(role.unit.names_above()) if role.kind == Role.Kind.MEMBER else "",
        # Nur das DPV-Veranstaltungsteam gibt seine Rolle hier ab (RO-20, Frage 5 vom 28.10.2026, W1).
        "give_up_href": reverse("profile_leave_team") if role.kind == Role.Kind.EVENT_TEAM else None,
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
        "pages": [_("Login-Seite"), _("Startseite"), _("Mein Profil"), _("Organisation")],
    },
    "textfeld": {
        "name": _("Textfeld"), "template": "core/_textfeld.html", "issues": [111, 190, 215],
        "purpose": _("Eine Eingabe mit Beschriftung, bei Pflichtfeldern „(Pflicht)“, und dem Fehler rot direkt "
                     "darunter; jedes Formular bindet es ein, statt sein Feld selbst zu schreiben. Das Feld zum "
                     "Antippen nutzt dieselbe Eingabe und denselben Fehler. Als Suchfeld steht der Knopf zum "
                     "Abschicken rechts daneben und ein Satz darunter. Hat das Feld eine fachliche Grenze, "
                     "steht beim Tippen rechts darunter die Zahl der Zeichen, etwa „12/30“, rot mit Meldung, "
                     "sobald der Text zu lang ist."),
        "pages": [_("Organisation")],
    },
    "datumsfeld": {
        "name": _("Datumsfeld"), "template": "core/_datumsfeld.html", "issues": [117],
        "purpose": _("Ein Datum über das Feld des Browsers, mit Beschriftung, bei Pflichtfeldern „(Pflicht)“, und "
                     "dem Fehler rot direkt darunter, wie beim Textfeld. Der Browser zeigt das Datum in seiner "
                     "Schreibweise und bietet seinen Kalender an, am Handy die Drehräder; Tage in der Zukunft lässt "
                     "er nicht wählen, wo das Formular es so festlegt."),
        "pages": [_("Organisation")],
    },
    "kurzmeldung": {
        "name": _("Kurze Meldung"), "template": "core/_kurzmeldung.html", "issues": [186],
        "purpose": _("Bestätigt eine eigene Handlung, etwa „gespeichert“: erscheint als Erfolg oder Information "
                     "unten über dem Inhalt, mit Schatten und ×, und verschwindet nach rund 6 Sekunden. Was einen "
                     "Zustand beschreibt, steht fest auf der Seite; eine Fehlermeldung steht fest an der Stelle "
                     "der Handlung."),
        "pages": [_("Mein Profil")],
    },
    "antippfeld": {
        "name": _("Feld zum Antippen"), "template": "core/_antippfeld.html", "issues": [180, 207, 215],
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
        "name": _("Überschrift einer Fläche"), "template": "core/_flaechenkopf.html",
        "issues": [161, 190, 94, 218, 285, 117],
        "purpose": _("Überschrift einer Fläche mit einem Symbol im Kästchen davor; rechts darf ein Knopf mit Plus "
                     "stehen, etwa „Gruppenleitung benennen“, links daneben ein zweiter zart blauer, etwa "
                     "„Verwaltete Person anlegen“. Der Titel darf ein Link sein, etwa der eigene Bund "
                     "auf der Seite „Verband“. Hinter dem Titel darf klein und grau eine Zahl stehen, etwa "
                     "„4 Personen“."),
        "pages": [_("Mein Profil"), _("Organisation")],
    },
    "rollenkachel": {
        "name": _("Rollenkachel"), "template": "core/_rollenkachel.html", "issues": [161, 189, 94, 219],
        "purpose": _("Zeigt eine Rolle mit ihrer Organisation; die Mitgliedschaft als eigene Fläche mit dem Weg "
                     "darüber, die übrigen Rollen als Kacheln ohne zweite Zeile. Unter „Organisationen darunter“ "
                     "ist die Kachel anklickbar und zeigt ihre Leitungen, ohne Zugriff grau ohne blauen Streifen. "
                     "Unten darf ein kleiner Knopf „Rolle abgeben“ stehen, etwa beim DPV-Veranstaltungsteam."),
        "pages": [_("Mein Profil"), _("Organisation")],
    },
    "gliederungsbaum": {
        "name": _("Gliederung"), "template": "core/_gliederung.html", "issues": [189],
        "purpose": _("Zeigt einen Bund als Baum: je Organisation Art, Name, Marke und Leitungen; anklickbar nur mit "
                     "Zugriff, alle ohne Zugriff zugeklappt unter „… weitere ohne Zugriff“."),
        "pages": [_("Organisation")],
    },
    "kennmarke": {
        "name": _("Marke"), "template": "core/_kennmarke.html", "issues": [189, 94, 218, 117],
        "purpose": _("Kleine runde Pille mit Wort an einer Organisation oder Person: „Du springst ein“, „nur "
                     "lesen“, „gesperrt“ oder „verwaltet“."),
        "pages": [_("Organisation")],
    },
    "leitung": {
        "name": _("Person in einer Liste"), "template": "core/_leitung.html", "issues": [189, 191, 285, 286, 287, 117, 99],
        "purpose": _("Eine Leitung oder Person mit Kreis: oben Fahrtenname, Name und bei sich selbst „das bist du“, "
                     "darunter links die Rollen und rechts die Mail, wo die Seite sie zeigen darf. Eine Leitung hat "
                     "genau eine Rolle, eine Person im Abschnitt „Personen“ keine, eine oder mehrere "
                     "Leitungsrollen. Ganz rechts ist Platz für Knöpfe; wo man Leitungen entfernen darf, steht dort "
                     "„Entfernen“, beim eigenen Eintrag „Rolle abgeben“; wo man Personen verschieben oder "
                     "austragen darf, „Verschieben“ und „Austragen“. Eine verwaltete Person hat einen grauen Kreis, "
                     "die Marke „verwaltet“ statt der Mail und rechts „Bearbeiten“. Eine angezeigte Leitungsrolle "
                     "einer verwalteten Person hat einen grauen Kreis und hinter dem Namen „ohne Konto, nur "
                     "Anzeige“; im Abschnitt „Personen“ steht sie als Rolle mit „(nur Anzeige)“."),
        "pages": [_("Organisation")],
    },
    "knopfentfernen": {
        "name": _("Knopf „Entfernen“"), "template": "core/_knopf_entfernen.html", "issues": [191, 286],
        "purpose": _("Für Handlungen, die etwas wegnehmen, etwa „Entfernen“ bei einer Leitung, „Austragen“ bei einer "
                     "Person oder „Austreten“: zarte rote Fläche mit roter Schrift, die Farben der Fehlermeldung. "
                     "Er führt zur Bestätigung, nie gleich zur Handlung."),
        "pages": [_("Mein Profil"), _("Organisation")],
    },
    "knopfverschieben": {
        "name": _("Zart blauer Knopf"), "template": "core/_knopf_verschieben.html", "issues": [287, 117, 92],
        "purpose": _("Für Handlungen, die etwas umstellen oder öffnen, ohne etwas wegzunehmen, etwa „Verschieben“ bei "
                     "einer Person oder „Bearbeiten“ bei einer verwalteten Person: Knopf mit zarter blauer Fläche und "
                     "blauer Schrift, die Farben der Informationsmeldung, meist klein. Beschriftung und Symbol sind "
                     "wählbar; groß und mit Schild steht er als „Support-Zugang starten“ im Kopf einer Organisation. "
                     "Er führt zum Dialog, nie gleich zur Handlung."),
        "pages": [_("Organisation")],
    },
    "stift": {
        "name": _("Bearbeiten-Symbol"), "template": "core/_stift.html", "issues": [95],
        "purpose": _("Ein Stift oben rechts in einer Fläche, dort, wo ein Dialog sein × hat. Er öffnet den Dialog "
                     "„… bearbeiten“, in dem alle Einstellungen dieser Sache an einem Ort stehen, etwa Name und "
                     "Ring einer Organisation. Er steht nur, wo man bearbeiten darf."),
        "pages": [_("Organisation")],
    },
    "schalter": {
        "name": _("Schalter"), "template": "core/_schalter.html", "issues": [95, 98],
        "purpose": _("Schaltet etwas ein oder aus, nach dem Zielbild „Mein Profil“: links ein fetter Titel und ein "
                     "Satz, rechts der runde Schalter, eingeschaltet blau. Gesperrt steht er grau da, etwa wenn "
                     "sich etwas nicht zurücknehmen lässt (zweites Beispiel). Gespeichert wird erst mit dem Knopf "
                     "des Dialogs. Als Regler der Einwilligung (drittes Beispiel) steht er ohne Satz beim Öffnen "
                     "auf „aus“, Vorleseprogramme sagen ihn als Ankreuzfeld an, und fehlt die Bestätigung, steht "
                     "der Fehler rot darunter, wie beim Textfeld."),
        "pages": [_("Organisation")],
    },
    "orgakopf": {
        "name": _("Kopf einer Organisationsseite"), "template": "core/_orgakopf.html", "issues": [189, 218, 95, 92],
        "purpose": _("Steht oben auf der Seite einer Organisation: der Pfad nach oben, der Name groß, darunter "
                     "Art und Organisation darüber, rechts die Marke. Wo man die Organisation bearbeiten darf, "
                     "steht oben rechts der Stift. Für die Verbandsleitung steht der Verband als erste Ebene im "
                     "Pfad und führt zur Seite „Verband“ (zweites Beispiel). Für Admins steht rechts neben dem "
                     "Titel „Support-Zugang starten“, am Handy unter dem Namen (drittes Beispiel)."),
        "pages": [_("Organisation")],
    },
    "dialog": {
        "name": _("Dialog"), "template": "core/_dialog_auf.html", "issues": [190, 191, 94, 286, 287, 95, 117, 118],
        "purpose": _("Ein Fenster über der Seite mit Titel, Zeile darunter und × oben rechts, unten „Abbrechen“; "
                     "mit Escape oder Tippen daneben zurück zur Seite. Er hat eine eigene Adresse und geht so "
                     "auch ohne Skript. Zum Bestätigen steht unten neben „Abbrechen“ ein roter Knopf, etwa "
                     "„Entfernen“, oder, wo nichts weggenommen wird, ein dunkelblauer, etwa „Verschieben“; er "
                     "schickt eine Wahl aus der „Auswahl im Dialog“ oder Felder mit, etwa den Namen beim Anlegen. "
                     "Danach bekommt der Knopf, der den Dialog geöffnet hat, wieder den Fokus, wo die Seite ihm eine "
                     "Kennung gibt, etwa bei verwalteten Personen. Links unten kann ein zart roter Knopf stehen, etwa "
                     "„Verwaltete Person löschen“ (drittes Beispiel), und „Abbrechen“ kann anders heißen und "
                     "woandershin führen, etwa „Nicht löschen“ zurück in den Dialog „Bearbeiten“ (viertes Beispiel)."),
        "pages": [_("Mein Profil"), _("Organisation")],
    },
    "auswahl": {
        "name": _("Auswahl im Dialog"), "template": "core/_auswahl.html", "issues": [286, 287, 95, 92],
        "purpose": _("Wahlmöglichkeiten in einem Dialog als Optionsfelder untereinander, die erste gewählt oder, etwa "
                     "beim Anlass eines Support-Zugangs, keine; darunter "
                     "die Vorschau der gewählten Möglichkeit, die mit der Wahl wechselt, auch ohne Skript. Die "
                     "Vorschau ist freiwillig, beim Verschieben gibt es keine. Die Überschrift darf sichtbar sein, etwa "
                     "„Ring“ im Dialog „… bearbeiten“. Nach einer Ablehnung bleibt die "
                     "abgelehnte Möglichkeit gewählt. Der Knopf des Dialogs schickt die Wahl mit, etwa beim "
                     "Austragen, beim Austreten und beim Verschieben."),
        "pages": [_("Mein Profil"), _("Organisation")],
    },
    "trefferliste": {
        "name": _("Trefferliste"), "template": "core/_treffer.html", "issues": [190, 285, 99],
        "purpose": _("Vorschläge oder Treffer einer Suche: Kreis, Fahrtenname und Name, darunter die Organisation, "
                     "rechts „Benennen“. Bei sich selbst steht statt des Knopfs ein Satz, bei jemandem, der woanders "
                     "Mitglied ist, eine Warnung. Im Dialog „Person aufnehmen“ ohne Organisation darunter, mit dem "
                     "Knopf „Aufnehmen“. Eine verwaltete Person hat die Marke „verwaltet“ und darunter den Satz, "
                     "dass die Rolle nur angezeigt wird und keine Rechte gibt."),
        "pages": [_("Organisation")],
    },
    "profilkreis": {
        "name": _("Profilkreis"), "template": "core/_profilkreis.html", "issues": [7, 13],
        "purpose": _("Führt zu „Mein Profil“: der Kreis mit dem Anfangsbuchstaben, in der Seitenleiste mit dem "
                     "Vornamen; ohne Namen ein Personensymbol."),
        "pages": [_("jede Seite mit Login")],
    },
    "supportbalken": {
        "name": _("Balken Support-Zugang"), "template": "core/_supportbalken.html", "issues": [92],
        "purpose": _("Steht auf jeder Seite, solange ein Admin im Support-Zugang ist: dunkelblau mit weißer Schrift "
                     "und Schild, die Organisation und bis wann der Zugang läuft, rechts der weiße Knopf „beenden“. "
                     "Am PC bleibt er beim Scrollen oben im Inhalt, am Handy steht er oben auf der Seite und bricht "
                     "um. Er ist weder Sonnengelb wie das Band der Testumgebung noch eine der vier Meldungsarten."),
        "pages": [_("jede Seite mit Login im Support-Zugang")],
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


def _organisation_examples() -> dict:
    """Erfundene Beispiele für die Bausteine der Seite „Organisation“ (#189), ohne Datenbank."""
    kind = Unit.Kind
    boreas = Unit(kind=kind.ASSOCIATION, name="Pfadfinderbund Boreas")
    walhall = Unit(kind=kind.TROOP, name="Walhall")
    covers, read = Mark(_("Du springst ein"), "ein"), Mark(_("nur lesen"), "lesen")

    def node(unit, kind_label, mark=None, leads="", href="#h-gliederung", access="manage", **more):
        return Node(unit=unit, kind=kind_label, access=access, href=href, mark=mark, leads=leads, current=False, **more)

    falken = node(Unit(name="Sippe Falken"), kind.GROUP.label, covers, "keine Gruppenleitung")
    woelfe = node(Unit(name="Meute Wölfe"), kind.GROUP.label, leads="Gruppenleitung: Wolke")
    adler = node(Unit(name="Sippe Adler"), kind.GROUP.label, href=None, access="name")
    zugvoegel = node(Unit(name="Zugvögel"), kind.TROOP.label, href=None, access="name", children=[adler])
    troop = node(walhall, kind.TROOP.label, leads="Stammesleitung: Wirbelwind, Wiesel", children=[woelfe, falken])
    troop.current = True
    outline = [node(boreas, kind.ASSOCIATION.label, read, "Bundesleitung: Brummbär", access="read",
                    children=[troop], folded=[zugvoegel])]
    leads = [
        Lead(name="Wirbelwind", extra="Wanda Beispiel", role="Stammesleitung", mail="wanda.beispiel@example.org",
             locked=False, is_self=True, remove_href="#h-dialog", remove_label=texts.GIVE_UP_BUTTON),
        Lead(name="Funke", extra="Fiete Muster", role="Gruppenleitung", mail="", locked=True, is_self=False,
             remove_href="#h-dialog", remove_label=texts.REMOVE_BUTTON),
        Lead(name="kim.ohne.namen", extra="", role="Stammesleitung", mail="", locked=False, is_self=False,
             remove_href="#h-dialog", remove_label=texts.REMOVE_BUTTON),
        # Eine angezeigte Leitungsrolle einer verwalteten Person (#99): grauer Kreis, „ohne Konto, nur Anzeige“.
        Lead(name="Tim Probe", extra="", role="Stammesleitung", mail="", locked=False, is_self=False, display_only=True,
             remove_href="#h-dialog", remove_label=texts.REMOVE_BUTTON),
    ]
    page = Page(unit=walhall, access="manage", path=[("Pfadfinderbund Boreas", "#h-orgakopf")],
                kind_line="Stamm in Pfadfinderbund Boreas", mark=covers, leads=leads, notice="", tiles=None, empty="",
                edit_href="#h-orgakopf", edit_label="Stamm Walhall bearbeiten")
    # Wie die Verbandsleitung den Kopf sieht, wenn sie zugleich Leitung in Boreas ist (#218).
    federation_page = Page(unit=Unit(kind=kind.TROOP, name="Zugvögel"), access="manage",
                           path=[("DPV", "#h-orgakopf"), ("Pfadfinderbund Boreas", "#h-orgakopf")],
                           kind_line="Stamm in Pfadfinderbund Boreas", mark=None, leads=leads, notice="", tiles=None,
                           empty="")
    tiles = [
        {"label": kind.GROUP.label, "org": "Meute Wölfe", "way": "Gruppenleitung: Wolke", "href": "#h-rollenkachel"},
        {"label": kind.GROUP.label, "org": "Sippe Falken", "href": "#h-rollenkachel", "mark": covers},
        {"label": kind.TROOP.label, "org": "Zugvögel", "no_access": True},
    ]
    hit_list = [
        Hit(key="", name="Flink", extra="Finn Muster", place="Sippe Falken", note="", warning="", hint=""),
        Hit(key="", name="Wirbelwind", extra="Wanda Beispiel", place="Walhall", warning="", hint="",
            note=texts.NOT_YOURSELF % {"unit": "Walhall"}),
        Hit(key="", name="Ameise", extra="Anton Muster", place=texts.ELSEWHERE, note="", hint="",
            warning=texts.MEMBER_ELSEWHERE),
        Hit(key="", name="Otter", extra="Otto Ohne", place=texts.NOWHERE, note="", warning="",
            hint=texts.BECOMES_MEMBER % {"unit": "Sippe Falken"}),
        # Eine verwaltete Person (#99): Marke „verwaltet“ und der Satz, dass die Rolle nur angezeigt wird.
        Hit(key="", name="Kiwi", extra="Lena Probe", place="Sippe Falken", note="", warning="", managed=True,
            hint=person_texts.DISPLAYED_HINT % {"person": "Kiwi (Lena Probe)"}),
    ]
    dialog = {"title": texts.APPOINT_TITLE % {"role": "Gruppenleitung"},
              "subtitle": texts.APPOINT_FOR % {"unit": "Sippe Falken"}, "close_href": "#h-dialog-beispiel",
              "form": AccountSearchForm(auto_id="katalog_%s")}
    removal = {"title": texts.REMOVE_QUESTION % {"person": "Funke (Fiete Muster)", "role": "Gruppenleitung", "unit": "Sippe Falken"},
               "lines": [f"{texts.LAST_LEAD_COVERED % {'unit': 'Sippe Falken', 'role': 'Gruppenleitung', 'cover': 'Stamm Walhall'}} "
                         f"{texts.ANYWAY_REMOVE}"],
               "close_href": "#h-dialog", "confirm_action": "#h-dialog", "confirm_label": texts.REMOVE_BUTTON,
               "preview_id": "h-dialog-entfernen"}
    # Löschen einer verwalteten Person (#118): der Knopf links unten im Dialog „Bearbeiten“ und die Rückfrage danach.
    managed_edit = {"title": person_texts.EDIT_TITLE % {"person": "Kiwi (Lena Probe)"},
                    "subtitle": person_texts.IN_UNIT % {"unit": "Sippe Falken"}, "close_href": "#h-dialog",
                    "side_href": "#h-dialog", "side_label": person_texts.DELETE_BUTTON, "confirm_action": "#h-dialog",
                    "confirm_label": person_texts.SAVE_BUTTON, "confirm_primary": True,
                    "preview_id": "h-dialog-bearbeiten"}
    deleting = {"title": person_texts.DELETE_QUESTION % {"person": "Kiwi (Lena Probe)"},
                "subtitle": person_texts.IN_UNIT % {"unit": "Sippe Falken"}, "lines": [person_texts.DELETE_CANNOT_UNDO],
                "close_href": "#h-dialog", "cancel_href": "#h-dialog", "cancel_label": person_texts.DELETE_KEEP,
                "confirm_action": "#h-dialog", "confirm_label": person_texts.DELETE_CONFIRM,
                "preview_id": "h-dialog-loeschen"}
    # Austragen mit Wahl und Vorschau (#286), erfunden wie im Beispiel des Issues.
    person = "Flink (Finn Muster)"
    expulsion = {
        "title": texts.EXPEL_QUESTION % {"person": person, "unit": "Sippe Falken"},
        "close_href": "#h-auswahl", "confirm_action": "#h-auswahl", "confirm_label": texts.EXPEL_BUTTON,
        "form_id": "katalog-auswahl", "preview_id": "h-dialog-austragen",
        "choice": {"name": "katalog-wahl", "legend": texts.EXPEL_LEGEND % {"person": person}, "options": [
            {"value": "hoch", "label": texts.EXPEL_UP % {"person": person, "target": "Stamm Walhall"},
             "lines": [texts.EXPEL_PREVIEW_UP % {"person": person, "unit": "Sippe Falken", "target": "Stamm Walhall"},
                       texts.ENDING_ROLES % {"roles": texts.ROLE_OF % {"role": "Gruppenleitung", "unit": "Sippe Falken"}},
                       texts.LAST_LEAD_COVERED % {"unit": "Sippe Falken", "role": "Gruppenleitung",
                                                  "cover": "Stamm Walhall"},
                       texts.REGISTRATIONS_STAY]},
            {"value": "ganz", "label": texts.EXPEL_NONE % {"person": person},
             "lines": [texts.EXPEL_PREVIEW_NONE % {"person": person, "unit": "Sippe Falken"},
                       texts.ENDING_ROLES % {"roles": texts.ROLE_OF % {"role": "Gruppenleitung", "unit": "Sippe Falken"}},
                       texts.LAST_LEAD_COVERED % {"unit": "Sippe Falken", "role": "Gruppenleitung",
                                                  "cover": "Stamm Walhall"},
                       texts.REGISTRATIONS_STAY]},
        ]},
    }
    # Personen im Abschnitt „Personen“ (#285): mit zwei Rollen, mit einer und ohne Rolle.
    persons = [
        Lead(name="Wirbelwind", extra="Wanda Beispiel", role="", mail="wanda.beispiel@example.org", locked=False,
             is_self=True, role_names=["Stammesleitung Stamm Walhall", "Gruppenleitung Sippe Falken"]),
        Lead(name="Wolke", extra="Wim Muster", role="", mail="wim.muster@example.org", locked=False, is_self=False,
             role_names=["Gruppenleitung Meute Wölfe"]),
        Lead(name="Wilma Muster", extra="", role="", mail="wilma.muster@example.org", locked=False, is_self=False,
             move_href="#h-leitung", expel_href="#h-leitung"),
        # Eine verwaltete Person (#117): grauer Kreis, Marke „verwaltet“, ohne Mail, mit „Bearbeiten“; seit #118
        # dahinter „Verschieben“ und „Austragen“ wie bei Personen mit Konto.
        Lead(name="Kiwi", extra="Lena Probe", role="", mail="", locked=False, is_self=False, managed=True,
             edit_href="#h-leitung", move_href="#h-leitung", expel_href="#h-leitung",
             # Seit #99 mit ihrer angezeigten Leitungsrolle.
             role_names=[person_texts.DISPLAYED_ROLE_AT % {"role": "Gruppenleitung", "unit": "Sippe Falken"}]),
    ]
    # Verschieben mit Wahl ohne Vorschau und blauem Knopf (#287), erfunden wie im Beispiel des Issues.
    moving = {
        "title": texts.MOVE_TITLE, "subtitle": texts.MOVE_FROM % {"person": "Flink (Finn Muster)", "unit": "Stamm Walhall"},
        "lines": [texts.MOVE_QUESTION], "close_href": "#h-auswahl", "confirm_action": "#h-auswahl",
        "confirm_label": texts.MOVE_BUTTON, "confirm_primary": True, "form_id": "katalog-verschieben",
        "preview_id": "h-dialog-verschieben",
        "choice": {"name": "katalog-ziel", "legend": texts.MOVE_QUESTION, "options": [
            {"value": "woelfe", "label": "Meute Wölfe", "lines": []},
            {"value": "falken", "label": "Sippe Falken", "lines": []},
        ]},
    }
    admit_hits = [Hit(key="", name="Otter", extra="Otto Ohne", place="", note="", warning="", hint="")]
    # Schalter (#95): wie beim Bund Boreas vor dem Einschalten und wie bei Mosaik, wo er gesperrt ist.
    switches = [
        {"name": "katalog-ringe", "value": "an", "title": texts.HAS_RINGS_TITLE, "text": texts.HAS_RINGS_OFF,
         "checked": False, "locked": False},
        {"name": "katalog-ringe-an", "value": "an", "title": texts.HAS_RINGS_TITLE, "text": texts.HAS_RINGS_LOCKED,
         "checked": True, "locked": True},
        # Der Regler der Einwilligung (#98) beim Öffnen, ohne Satz, als Ankreuzfeld angesagt. Ohne Fehler: Der Katalog
        # zeigt nur ein Feld mit Fehler (Textfeld); den Fehler am Regler zeigt der Dialog selbst.
        {"name": "katalog-einwilligung", "value": "an", "title": person_texts.CONSENT, "checkbox": True},
    ]
    edit_example = {"name": "Sippe Falken", "label": texts.EDIT_TITLE % {"unit": "Sippe Falken"}}
    # Wie ein Admin ohne Support-Zugang den Kopf sieht (#92): nur Pfad, Name und Art, rechts der zart blaue Knopf.
    support_page = Page(unit=Unit(kind=kind.TROOP, name="Zugvögel"), access="head",
                        path=[("Pfadfinderbund Boreas", "#h-orgakopf")], kind_line="Stamm in Pfadfinderbund Boreas",
                        mark=None, leads=[], notice="", tiles=None, empty="", support_href="#h-orgakopf")
    return {"switches": switches, "edit_example": edit_example, "persons": persons, "persons_count": texts.PERSONS_COUNT % {"count": 4}, "admit_hits": admit_hits,
            "outline": outline, "org_page": page, "org_federation_page": federation_page, "org_support_page": support_page,
            "support_bar": {"label": "Stamm Walhall", "until": "14:35", "end_action": "#h-supportbalken"}, "org_leads": leads, "org_tiles": tiles,
            "org_marks": [covers, read, Mark(_("gesperrt"), "gesperrt"), Mark(_("verwaltet"), "verwaltet")], "dialog": dialog, "removal": removal, "managed_edit": managed_edit, "deleting": deleting, "expulsion": expulsion, "moving": moving, "hits": hit_list,
            "no_account": ("warning", texts.NO_ACCOUNT)}


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
        # Datumsfeld (#117) mit erfundenem Datum; der Fehler am Feld sieht aus wie beim Textfeld darüber.
        "date_form": ManagedPersonForm(initial={"birth_date": date(2015, 5, 14)}, auto_id="katalog_datum_%s"),
        "membership": {"label": _("Mitgliedschaft"), "org": "Sippe Falken", "way": "Pfadfinderbund Boreas › Stamm Walhall"},
        # Rollen ohne zweite Zeile (#219); die lange Organisation zeigt den Umbruch.
        "tiles": [
            {"label": label, "org": org} for label, org in [
                (role.GROUP_LEAD.label, "Meute Wölfe"),
                (role.TROOP_LEAD.label, "Stamm Walhall vom Nordseestrand"),
                (role.ADMIN.label, _("DPV Anmeldetool")),
            ]
        ] + [{"label": role.EVENT_TEAM.label, "org": "DPV", "give_up_href": "#h-rollenkachel"}],
        # Vier kurze Meldungen nacheinander zeigen den Stapel (#186, Szenarien 12 und 13).
        "short_stack": ["Leitung Sippe Falken ist benannt.", "Leitung Sippe Eulen ist benannt.",
                        "Leitung Meute Wölfe ist benannt.", "Leitung Sippe Biber ist benannt."],
        # Seite „Organisation“ (#189), erfunden wie in den Szenarien; nichts kommt aus der Datenbank.
        **_organisation_examples(),
        # Der Profilkreis liest nur den kurzen Namen; hier erfunden, nicht der der angemeldeten Person.
        "named": {"short_name": "Kim"},
        "unnamed": {"short_name": ""},
    }
    blocks = {key: dict(block, id=f"h-{key}") for key, block in BUILDING_BLOCKS.items()}
    context = {"blocks": blocks, "examples": examples, "pattern_form": PatternForm.example()}
    return render(request, "core/bausteine.html", context)
