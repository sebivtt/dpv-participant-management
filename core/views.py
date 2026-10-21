"""Seiten der App „core“."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def start(request: HttpRequest) -> HttpResponse:
    """Startseite nach dem Login: Begrüßung mit Name und Mail aus Keycloak (#5, ORG-03).

    Nur mit Login erreichbar und zeigt nur die Daten der angemeldeten Person selbst. Fehlt
    in Keycloak der Vor- oder Nachname, steht dort ein Hinweis, ihn im DPV-Konto zu ergänzen.
    """
    name_incomplete = not (request.user.first_name and request.user.last_name)
    return render(request, "core/start.html", {"name_incomplete": name_incomplete})
