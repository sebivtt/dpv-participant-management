"""Was die Testumgebung vom späteren Betrieb unterscheidet (#58).

Die Testumgebung läuft offen im Internet, mit nur erfundenen Daten. Damit sie niemand für
das echte Tool hält, trägt jede Seite ein Band (core/templatetags/layout.py), und jede
Antwort bittet Suchmaschinen, sie nicht aufzunehmen. Beides gilt nur, wenn die Testumgebung
eingeschaltet ist (TEST_ENVIRONMENT in config/settings.py).
"""

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


class NoIndexMiddleware:
    """Bittet in der Testumgebung Suchmaschinen, keine Antwort aufzunehmen und keinem Link zu folgen.

    Als Kopfzeile der Antwort statt als Angabe im HTML, damit es auch für Fehlerseiten,
    Weiterleitungen, Gestaltung und Bilder gilt.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if settings.TEST_ENVIRONMENT:
            response["X-Robots-Tag"] = "noindex, nofollow"
        return response
