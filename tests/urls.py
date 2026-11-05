"""Adressen nur für die Tests des Fehlerprotokolls (#6), für „nicht gefunden“ (#64) und für die Suche nach Nummern (#156). Im Tool selbst gibt es sie nicht.

Übernimmt Adressen und Fehlerseite aus config/urls.py. Fehlt dort die Fehlerseite,
schlägt schon der Import fehl, und die Tests werden rot.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from config.urls import handler500
from config.urls import urlpatterns as tool_urlpatterns
from units.models import Unit

__all__ = ["handler500", "urlpatterns"]


@csrf_exempt
@login_not_required
def fail_with_personal_data(request: HttpRequest, number: int) -> HttpResponse:
    """Löst absichtlich einen Fehler aus, dessen Meldungstext Formular-, Sitzungs- und Kontodaten enthält.

    So steht im Meldungstext alles, was nie ins Log darf. Ein Log, das den Meldungstext
    übernimmt, fällt damit sofort auf. Ohne Login erreichbar, weil ein Test den Fehler auch
    ohne angemeldetes Konto auslöst; sonst leitete die Login-Pflicht (#5) vorher zum Login weiter.
    """
    raise ValueError(
        f"Testfehler mit {request.POST.get('allergie')} {request.session.get('notiz')} "
        f"Konto {request.user.pk} {request.user.get_username()} Nummer {number}"
    )


@login_not_required
def fail_with_database(request: HttpRequest) -> HttpResponse:
    """Fragt die Datenbank ab; ist sie nicht erreichbar, entsteht ein Fehler.

    Ohne Login erreichbar, weil der Test den Fehler ohne angemeldetes Konto auslöst; sonst
    leitete die Login-Pflicht (#5) zum Login weiter, bevor der Fehler entsteht.
    """
    get_user_model().objects.count()
    return HttpResponse("nicht erreicht")


def not_found(request: HttpRequest, number: int) -> HttpResponse:
    """Die Adresse gibt es, den Eintrag mit dieser Nummer nicht."""
    raise Http404


def forbidden(request: HttpRequest, number: int) -> HttpResponse:
    """Die Adresse gibt es, aber der Zugriff ist verboten."""
    raise PermissionDenied


# Seiten, wie sie ab #65, #93 und #117 kommen: Einträge nur über die zentrale Rechteprüfung (#64).


def show_person(request: HttpRequest, key: str) -> HttpResponse:
    """Zeigt eine Person, die die angemeldete Person sehen darf; auch per Formular."""
    return HttpResponse(request.rights.person(key).get_full_name())


def remove_member(request: HttpRequest, key: str) -> HttpResponse:
    """Eine Aktion an einer sichtbaren Person, die nur die Leitung ihrer Einheit darf (PK-21, PK-22)."""
    rights = request.rights
    person = rights.entry(rights.persons(), key, allowed=rights.leads_unit_of)
    return HttpResponse(f"entfernt: {person.get_full_name()}")


def lead_unit(request: HttpRequest, key: str) -> HttpResponse:
    """Eine Aktion an einer Einheit, die nur ihre Leitung darf, selbst oder einspringend (EH-18, EH-19)."""
    rights = request.rights
    found = rights.entry(Unit.objects.all(), key, allowed=rights.leads_unit)
    return HttpResponse(f"geleitet: {found.name}")


def forbidden_entry(request: HttpRequest, key: str) -> HttpResponse:
    """Eine Seite mit Kennung, die fälschlich „kein Zugriff“ meldet statt „nicht gefunden“."""
    raise PermissionDenied


def lead_unit_from_parameter(request: HttpRequest) -> HttpResponse:
    """Wählt eine Einheit über einen angehängten Parameter oder ein Formularfeld `einheit`, z. B. aus einer Auswahlliste (#156)."""
    rights = request.rights
    key = request.POST.get("einheit") if request.method == "POST" else request.GET.get("einheit")
    found = rights.entry(Unit.objects.all(), key, allowed=rights.leads_unit)
    return HttpResponse(f"geleitet: {found.name}")


# Seiten, die eine interne Nummer zeigen, und eine, die es nicht tut: Gegenproben für die Suche
# nach Nummern (#156). Sie zeigen die Nummer der Sippe Falken.


def _falken() -> Unit:
    return Unit.objects.get(name="Sippe Falken")


def number_in_link(request: HttpRequest) -> HttpResponse:
    return HttpResponse(f'<a href="/einheit/?einheit={_falken().pk}">Sippe Falken</a>')


def number_in_hidden_field(request: HttpRequest) -> HttpResponse:
    return HttpResponse(f'<form method="post"><input type="hidden" name="einheit" value="{_falken().pk}"></form>')


def number_in_hx_vals(request: HttpRequest) -> HttpResponse:
    return HttpResponse(f"<button hx-post=\"/einheit/\" hx-vals='{{\"einheit\": {_falken().pk}}}'>Wählen</button>")


def number_in_redirect(request: HttpRequest) -> HttpResponse:
    return HttpResponseRedirect(f"/einheit/?einheit={_falken().pk}")


def number_in_cookie(request: HttpRequest) -> HttpResponse:
    response = HttpResponse("Sippe Falken")
    response.set_cookie("einheit", str(_falken().pk))
    return response


def number_of_person(request: HttpRequest, key: str) -> HttpResponse:
    """Eine Seite mit Kennung, die die Nummer der gezeigten Person verrät."""
    return HttpResponse(f'<a href="/person/?id={request.rights.person(key).pk}">Person</a>')


def without_number(request: HttpRequest) -> HttpResponse:
    """Kennung, Jahreszahl und andere Zahlen, aber keine interne Nummer."""
    falken = _falken()
    return HttpResponse(
        f'<a href="/test/einheit/{falken.key}/">{falken.name}</a> Sommerlager 2026, 12 Plätze, 1. Juli'
        f'<input type="hidden" name="einheit" value="{falken.key}">'
    )


def lead_section(request: HttpRequest) -> HttpResponse:
    """Ein ganzer Bereich ohne Kennung, nur für Leitungen; im Tool kommt so „Organisation“ (#93)."""
    request.rights.require_section(bool(request.rights.area))
    return HttpResponse("Bereich für Leitungen")


urlpatterns = [
    *tool_urlpatterns,
    path("test/<int:number>/", fail_with_personal_data),
    path("test/datenbank/", fail_with_database),
    path("test/<int:number>/nicht-da/", not_found),
    path("test/<int:number>/verboten/", forbidden),
    path("test/person/<key:key>/", show_person),
    path("test/person/<key:key>/entfernen/", remove_member),
    path("test/person/<key:key>/kein-zugriff/", forbidden_entry),
    path("test/einheit/<key:key>/", lead_unit),
    path("test/einheit/", lead_unit_from_parameter),
    path("test/leitungen/", lead_section),
    path("test/nummer/link/", number_in_link, name="number_in_link"),
    path("test/nummer/verstecktes-feld/", number_in_hidden_field, name="number_in_hidden_field"),
    path("test/nummer/hx-vals/", number_in_hx_vals, name="number_in_hx_vals"),
    path("test/nummer/weiterleitung/", number_in_redirect, name="number_in_redirect"),
    path("test/nummer/cookie/", number_in_cookie, name="number_in_cookie"),
    path("test/nummer/keine/", without_number, name="without_number"),
    path("test/nummer/<key:key>/", number_of_person, name="number_of_person"),
]
