"""Seiten der Kreise (#381, GRP-01, GRP-02): „Kreise“, „Kreis anlegen“, die Seite je Kreis, „Person einladen“,
„Zurücknehmen“, „Annehmen“ und „Ablehnen“.

Was jemand sieht und darf, fragt jede Seite die zentrale Rechteprüfung (`request.rights`, Abschnitt „Kreise“ in
`access/rights.py`); hier steht nur, wie es auf die Seite kommt. Dialoge haben wie überall eine eigene Adresse und
kommen offen vom Server, damit alles auch ohne Skript geht. Ein Protokoll gibt es für Kreise nicht (#141 F14).
"""

from django.contrib import messages
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import cache_control

from access.addresses import checks_rights
from access.keys import is_key, new_key
from access.rights import WILDCARDS
from accounts.models import display_name
from circles import texts
from core.forms import CircleForm, FederationSearchForm
from units import texts as unit_texts
from units.organisation import Hit

READING = ("GET", "HEAD")
CIRCLE_ROWS = ("KR-01", "KR-02", "KR-03", "KR-04", "KR-05", "KR-07", "KR-08", "KR-10")
INVITE_ROWS = ("KR-02", "KR-05", "KR-06", "KR-07", "KR-08", "KR-10", "PK-13", "PK-14", "PK-24")
ANSWER_ROWS = ("KR-02", "KR-04", "KR-05", "KR-09")


def _names(row: dict) -> tuple[str, str]:
    """Name und Zusatz wie überall: groß der Fahrtenname, dahinter der volle Name; ohne Fahrtenname nur der Name (#111)."""
    full = " ".join(part for part in (row["first_name"], row["last_name"]) if part)
    if row["scout_name"]:
        return row["scout_name"], full
    return full or row["username"], ""


def _person(row: dict, **extra) -> dict:
    """Eine Person für den Baustein „Person in einer Liste“: Kreis, Name, Zusatz, „das bist du“, Marke „Verwaltend“."""
    name, more = _names(row)
    return {"initial": name[:1].upper(), "name": name, "extra": more, "is_self": row.get("is_self", False),
            "shown_roles": [texts.MANAGING] if row.get("manages") else [], **extra}


def _invitation_block(entry: dict) -> dict:
    """Eine offene Einladung für den Baustein „Einladung“: Kreis, wer einlädt, Beschreibung, beide Knöpfe."""
    return {"title": entry["circle_name"], "by_line": texts.INVITES_YOU % {"name": entry["by"]},
            "text": entry["description"],
            "accept_action": reverse("circle_accept", args=[entry["key"]]),
            "decline_action": reverse("circle_decline", args=[entry["key"]])}


# Welche eigenen Einladungen eine Seite zuletzt gezeigt hat, je mit dem Kreis (unabhängige Prüfung, M2; Sebastian,
# 27.11.2026: „Satz statt ‚nicht gefunden‘“). So erkennt „Annehmen“ oder „Ablehnen“ eine eigene Einladung, die es
# inzwischen nicht mehr gibt, ohne dass eine fremde Kennung etwas verrät: Sie stand nie hier und bleibt „nicht gefunden“.
SHOWN_INVITATIONS = "kreise_einladungen"
SHOWN_MOST = 50


def _remember_shown(request: HttpRequest, invitations: list[dict]) -> None:
    """Merkt sich in der Sitzung die gezeigten eigenen Einladungen, höchstens `SHOWN_MOST`, die neuesten zuletzt."""
    if not invitations:
        return
    shown = dict(request.session.get(SHOWN_INVITATIONS, {}))
    for entry in invitations:
        shown.pop(entry["key"], None)
        shown[entry["key"]] = entry["circle_key"]
    request.session[SHOWN_INVITATIONS] = dict(list(shown.items())[-SHOWN_MOST:])


def _circles_page(request: HttpRequest, dialog: dict | None = None) -> HttpResponse:
    """Die Seite „Kreise“: oben „Einladungen“, immer da, darunter „Meine Kreise“ mit „Kreis anlegen“ (#141 F10)."""
    rights = request.rights
    rights.require_section(rights.may_use_circles())
    own = rights.own_invitations()
    _remember_shown(request, own)
    invitations = [_invitation_block(entry) for entry in own]
    entries = [{"href": reverse("circle_page", args=[entry.key]), "symbol": "kreis", "title": entry.name,
                "line": texts.MEMBER_COUNT % {"count": entry.member_count},
                "mark": texts.MANAGING if entry.managed else ""} for entry in rights.own_circles()]
    return render(request, "core/kreise.html", {
        "invitations": invitations, "invitations_title": texts.INVITATIONS, "invitations_count": str(len(invitations)),
        "no_invitations": texts.NO_INVITATIONS, "entries": entries, "circles_title": texts.MY_CIRCLES,
        "circles_count": str(len(entries)), "create_href": reverse("circle_create"), "create_label": texts.CREATE_TITLE,
        "none_yet": texts.NONE_YET, "dialog": dialog,
    })


# Die Adresse hat keine Kennung: Die Seite zeigt nur Kreise, in denen die Person Mitglied ist, und Einladungen an sie.
@checks_rights(*CIRCLE_ROWS)
def circles(request: HttpRequest) -> HttpResponse:
    """Seite „Kreise“ (#381): Einladungen und die eigenen Kreise; ohne Zuordnung „kein Zugriff“ (KR-02)."""
    if request.method not in READING:
        raise Http404
    return _circles_page(request)


@checks_rights(*CIRCLE_ROWS)
# Wie bei „Veranstaltung erstellen“ (core/views.py): nie zwischenspeichern, aber ohne „Expires“ mit der Uhrzeit.
@cache_control(max_age=0, no_cache=True, no_store=True, must_revalidate=True, private=True)
def circle_create(request: HttpRequest) -> HttpResponse:
    """Dialog „Kreis anlegen“ zeigen und den Kreis anlegen (KR-01, GRP-01).

    Der Dialog bekommt beim Öffnen eine eigene Kennung (`creation_key`), damit ein Doppelklick nur einen Kreis anlegt
    (AG3). Danach geht es zur Seite des neuen Kreises mit der kurzen Meldung; bei einem Fehler bleibt der Dialog mit den
    Eingaben und dem Fehler am Feld offen (AG2). Ohne Zuordnung „kein Zugriff“, auch mit abgeschicktem Formular (KR-02).
    Der Browser speichert den Dialog nicht, damit „Zurück“ eine neue Kennung bringt.
    """
    rights = request.rights
    rights.require_section(rights.may_use_circles())
    if request.method == "POST":
        creation_key = request.POST.get("creation_key", "")
        if not is_key(creation_key):
            raise Http404
        form = CircleForm(request.POST)
        if form.is_valid():
            created = rights.create_circle(form.cleaned_data, creation_key)
            messages.success(request, texts.CREATED % {"circle": created.name})
            return redirect("circle_page", circle=created.key)
    elif request.method in READING:
        form, creation_key = CircleForm(), new_key()
    else:
        raise Http404
    dialog = {
        "title": texts.CREATE_TITLE, "subtitle": texts.CREATE_SUBTITLE, "close_href": reverse("circles"),
        "confirm_action": reverse("circle_create"), "confirm_label": texts.CREATE_TITLE, "confirm_primary": True,
        "form_id": "f-dialog", "novalidate": True, "hidden": [("creation_key", creation_key)], "circle_form": form,
    }
    return _circles_page(request, dialog=dialog)


def _circle_page(request: HttpRequest, circle: str, dialog: dict | None = None) -> HttpResponse:
    """Die Seite eines Kreises: für Mitglieder mit Mitgliedern, für Verwaltende mit „Offene Einladungen“ und
    „Person einladen“, für Eingeladene mit Name, Beschreibung und der Fläche „Einladung“, ohne Mitglieder (KR-03,
    KR-04, AV5)."""
    rights = request.rights
    found, membership = rights.circle(circle)
    back = {"href": reverse("circles"), "label": texts.NAV, "current": found.name}
    if membership is None:
        invitation = rights.invitation_to(found)
        if invitation is None:
            # Die Einladung ist gerade verschwunden, etwa zurückgenommen: wie ein Kreis, den es nicht gibt.
            raise Http404
        _remember_shown(request, [invitation])
        # Die Beschreibung steht schon im Seitenkopf, deshalb nicht noch einmal in der Einladung (Vorschau, 27.11.2026).
        return render(request, "core/kreis.html", {
            "circle": found, "back": back, "title": found.name, "invitation_title": texts.INVITATION_TITLE,
            "invitation": {**_invitation_block(invitation), "text": ""}, "invited_hint": texts.INVITED_HINT})
    members = [_person(row) for row in rights.circle_members(found, membership)]
    pending = [_person(row, remove_href=reverse("circle_withdraw", args=[found.key, row["key"]]),
                       remove_label=texts.WITHDRAW_BUTTON) for row in rights.circle_invitations(found, membership)]
    return render(request, "core/kreis.html", {
        "circle": found, "back": back, "title": found.name, "members": members, "members_title": texts.MEMBERS,
        "members_count": texts.MEMBER_COUNT % {"count": len(members)}, "manages": membership.manages,
        "invite_href": reverse("circle_invite", args=[found.key]), "invite_label": texts.INVITE_TITLE,
        "pending": pending, "pending_title": texts.OPEN_INVITATIONS, "pending_count": str(len(pending)),
        "no_pending": texts.NO_OPEN_INVITATIONS, "only_managers": texts.ONLY_MANAGERS, "dialog": dialog,
    })


@checks_rights(*CIRCLE_ROWS)
def circle_page(request: HttpRequest, circle: str) -> HttpResponse:
    """Seite eines Kreises über seine Kennung (#64); wer weder Mitglied noch eingeladen ist, bekommt „nicht gefunden“ (KR-05)."""
    if request.method not in READING:
        raise Http404
    return _circle_page(request, circle)


def _invite_page(request: HttpRequest, circle: str, form=None, hits=None, notice=None) -> HttpResponse:
    """Die Seite des Kreises mit offenem Dialog „Person einladen“; `notice` ist (Art, Text) einer Meldung im Dialog."""
    found = request.rights.managed_circle(circle)
    dialog = {
        "title": texts.INVITE_TITLE, "subtitle": texts.INVITE_IN % {"circle": found.name},
        "close_href": reverse("circle_page", args=[found.key]), "form": form or FederationSearchForm(),
        "help_text": texts.SEARCH_HELP, "search_action": reverse("circle_search", args=[found.key]),
        "appoint_action": reverse("circle_invite", args=[found.key]), "action_label": texts.INVITE_BUTTON,
        "hits": hits or [], "hits_title": texts.HITS_TITLE if hits else "", "notice": notice,
    }
    return _circle_page(request, circle, dialog=dialog)


@checks_rights(*INVITE_ROWS)
def circle_invite(request: HttpRequest, circle: str) -> HttpResponse:
    """Dialog „Person einladen“ öffnen und eine Person einladen (KR-08); nur für Verwaltende, sonst „nicht gefunden“ (KR-07).

    Lesend zeigt die Adresse den leeren Dialog. Ein Formular mit der Kennung eines Kontos lädt es ein; Mitglied wird
    die Person erst mit „Annehmen“ (GRP-02). Danach geht es zur Seite des Kreises mit der kurzen Meldung; lehnt die
    Rechteprüfung ab, bleibt der Dialog offen und nennt den Grund an der Stelle der Handlung (AV2, AG1).
    """
    rights = request.rights
    found = rights.managed_circle(circle)
    if request.method == "POST":
        done, text = rights.invite(found.key, request.POST.get("person"))
        if done:
            messages.success(request, text)
            return redirect("circle_page", circle=found.key)
        return _invite_page(request, circle, notice=("warning", text))
    if request.method not in READING:
        raise Http404
    return _invite_page(request, circle)


@checks_rights(*INVITE_ROWS)
def circle_search(request: HttpRequest, circle: str) -> HttpResponse:
    """„Suchen“ im Dialog „Person einladen“: ein Konto über die genaue bestätigte Mail oder den genauen Benutzernamen (KR-06).

    Wie bei Leitungen (PK-13, PK-15): Jede Suche mit Begriff zählt fürs Suchlimit, zusammen mit den Suchen als Leitung
    (PK-24), auch ohne Treffer; ein leeres Feld oder nur Platzhalter zeigen nichts und zählen nicht. Lesend führt die
    Adresse zum leeren Dialog.
    """
    rights = request.rights
    found = rights.managed_circle(circle)
    if request.method != "POST":
        if request.method not in READING:
            raise Http404
        return redirect("circle_invite", circle=found.key)
    form = FederationSearchForm(request.POST)
    if not form.is_valid():
        return _invite_page(request, circle, form=form)
    text = form.cleaned_data["suche"].strip()
    if not text or set(text) <= WILDCARDS:
        return _invite_page(request, circle, form=form)
    wait = rights.count_search()
    if wait:
        return _invite_page(request, circle, form=form, notice=("error", unit_texts.SEARCH_LIMIT % {"minutes": wait}))
    entries = rights.find_for_circle(found, text)
    if not entries:
        return _invite_page(request, circle, form=form, notice=("warning", texts.NO_ACCOUNT))
    hits = [Hit(key=entry["key"], name=_names(entry)[0], extra=_names(entry)[1], place="", note=entry["refusal"],
                warning="", hint="") for entry in entries]
    return _invite_page(request, circle, form=form, hits=hits)


@checks_rights(*INVITE_ROWS)
def circle_withdraw(request: HttpRequest, circle: str, invitation: str) -> HttpResponse:
    """Rückfrage „Einladung an … zurücknehmen?“ und Zurücknehmen (KR-08, A6); nur für Verwaltende, sonst „nicht gefunden“."""
    rights = request.rights
    found, entry = rights.withdrawal(circle, invitation)
    if request.method == "POST":
        messages.success(request, rights.withdraw(found.key, entry["key"]))
        return redirect("circle_page", circle=found.key)
    if request.method not in READING:
        raise Http404
    name = display_name(entry["first_name"], entry["last_name"], entry["scout_name"]) or entry["username"]
    dialog = {
        "title": texts.WITHDRAW_TITLE % {"name": name}, "subtitle": found.name,
        "close_href": reverse("circle_page", args=[found.key]), "lines": [texts.WITHDRAW_TEXT],
        "confirm_action": request.path, "confirm_label": texts.WITHDRAW_BUTTON,
    }
    return _circle_page(request, circle, dialog=dialog)


def _answer(request: HttpRequest, invitation: str, accept: bool) -> HttpResponse:
    """„Annehmen“ oder „Ablehnen“ einer eigenen Einladung (KR-09); eine fremde ist „nicht gefunden“ (AV6).

    Nur als Formular; lesend führt die Adresse zur Seite „Kreise“. Nach „Annehmen“ geht es zur Seite des Kreises, nach
    „Ablehnen“ zur Seite „Kreise“, je mit der kurzen Meldung. Gibt es die Einladung inzwischen nicht mehr, steht dort
    „Diese Einladung gibt es nicht mehr.“ (AG4).
    """
    rights = request.rights
    try:
        rights.invitation(invitation)
    except Http404:
        return _answer_gone(request, invitation)
    if request.method != "POST":
        if request.method not in READING:
            raise Http404
        return redirect("circles")
    found, text = rights.answer_invitation(invitation, accept)
    if found is None:
        messages.warning(request, text)
        return redirect("circles")
    messages.success(request, text)
    return redirect("circle_page", circle=found.key) if accept else redirect("circles")


def _answer_gone(request: HttpRequest, invitation: str) -> HttpResponse:
    """Eine eigene Einladung, die es nicht mehr gibt: nach dem Doppelklick auf „Annehmen“ die Seite des Kreises, sonst
    „Kreise“ mit „Diese Einladung gibt es nicht mehr.“ (AG4). Eine Kennung, die nie als eigene gezeigt wurde, bleibt
    „nicht gefunden“ (AV6), lesend jede.
    """
    circle = request.session.get(SHOWN_INVITATIONS, {}).get(invitation) if request.method == "POST" else None
    if circle is None:
        raise Http404
    try:
        _found, membership = request.rights.circle(circle)
    except Http404:
        membership = None
    if membership is not None:
        return redirect("circle_page", circle=circle)
    messages.warning(request, texts.GONE)
    return redirect("circles")


@checks_rights(*ANSWER_ROWS)
def circle_accept(request: HttpRequest, invitation: str) -> HttpResponse:
    """Eine eigene Einladung annehmen; erst damit ist die Person Mitglied (GRP-02, KR-09, A3)."""
    return _answer(request, invitation, accept=True)


@checks_rights(*ANSWER_ROWS)
def circle_decline(request: HttpRequest, invitation: str) -> HttpResponse:
    """Eine eigene Einladung ablehnen, still: Sie verschwindet, auch bei den Verwaltenden (KR-09, A5)."""
    return _answer(request, invitation, accept=False)
