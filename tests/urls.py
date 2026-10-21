"""Adressen nur für die Tests des Fehlerprotokolls (#6). Im Tool selbst gibt es sie nicht.

Übernimmt Adressen und Fehlerseite aus config/urls.py. Fehlt dort die Fehlerseite,
schlägt schon der Import fehl, und die Tests werden rot.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from config.urls import handler500
from config.urls import urlpatterns as tool_urlpatterns

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


urlpatterns = [
    *tool_urlpatterns,
    path("test/<int:number>/", fail_with_personal_data),
    path("test/datenbank/", fail_with_database),
    path("test/<int:number>/nicht-da/", not_found),
    path("test/<int:number>/verboten/", forbidden),
]
