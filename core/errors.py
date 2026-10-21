"""Fehlerprotokoll ohne Personendaten (DSG-08, #6). Leeres Gerüst, die Regeln folgen."""

from django.http import HttpRequest, HttpResponse, HttpResponseServerError


def server_error(request: HttpRequest) -> HttpResponse:
    """Fehlerseite bei einem unerwarteten Fehler. Noch leer."""
    return HttpResponseServerError()


class ClientErrorLogMiddleware:
    """Vermerkt „nicht gefunden“ und „kein Zugriff“ im Log. Noch leer."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)
