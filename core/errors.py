"""Fehlerprotokoll ohne Personendaten (DSG-08, #6).

Ins Log kommt nur, was zum Nachvollziehen eines Fehlers nötig ist und nichts über eine
Person verrät: Fehlernummer, Zeitpunkt, Muster der Adresse, Art des Fehlers und Stelle im
Code. Der Meldungstext eines Fehlers bleibt draußen, weil er oft genau die Daten enthält,
um die es geht (z. B. „Mail erika@… existiert schon“). Statt der echten Adresse steht ihr
Muster im Log, weil schon die Adresse eine Kontonummer enthalten kann (z. B. /konto/17/).
"""

import logging
import secrets
import sys
import traceback
from pathlib import Path
from types import TracebackType

from django.conf import settings
from django.core.signals import got_request_exception
from django.http import HttpRequest, HttpResponse, HttpResponseServerError
from django.template.loader import get_template
from django.urls import Resolver404, resolve

logger = logging.getLogger(__name__)

# Ohne 0, 1, I, L und O, die man beim Vorlesen oder Abtippen leicht verwechselt.
ERROR_NUMBER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
UNKNOWN_ADDRESS = "unbekannte Adresse"


def new_error_number() -> str:
    """Erzeugt eine zufällige Fehlernummer wie 7F3K-92QA, die nichts über die Person verrät."""
    characters = "".join(secrets.choice(ERROR_NUMBER_ALPHABET) for _ in range(8))
    return f"{characters[:4]}-{characters[4:]}"


def address_pattern(request: HttpRequest) -> str:
    """Gibt das Muster der aufgerufenen Adresse zurück, z. B. /anmeldungen/<int:pk>/.

    Echte Nummern und angehängte Parameter stehen darin nie. Passt die Adresse zu keinem
    Muster, kommt „unbekannte Adresse“ zurück; sonst könnte jede Person beliebigen Text
    über die Adresse ins Log schreiben.
    """
    match = request.resolver_match
    if match is None:
        try:
            match = resolve(request.path_info, getattr(request, "urlconf", None))
        except Resolver404:
            return UNKNOWN_ADDRESS
    return f"/{match.route}"


def _code_location(filename: str) -> str:
    """Kürzt den Dateipfad auf den Teil, der zum Finden nötig ist, ohne Benutzerordner des Rechners."""
    path = Path(filename)
    if "site-packages" in path.parts:
        return "/".join(path.parts[path.parts.index("site-packages") + 1 :])
    if path.is_relative_to(settings.BASE_DIR):
        return str(path.relative_to(settings.BASE_DIR))
    return path.name


def describe_exception(error_type: type[BaseException], tb: TracebackType | None) -> str:
    """Beschreibt einen Fehler nur durch seine Art und die Stellen im Code, ohne den Meldungstext."""
    name = error_type.__qualname__
    if error_type.__module__ != "builtins":
        name = f"{error_type.__module__}.{name}"
    frames = [
        f"  {_code_location(frame.filename)}:{frame.lineno} in {frame.name}" for frame in traceback.extract_tb(tb)
    ]
    return "\n".join([name, *frames])


class SafeFormatter(logging.Formatter):
    """Log-Ausgabe, die bei Fehlern nur Art und Stellen im Code zeigt, nie den Meldungstext.

    Gilt für alle Log-Einträge, auch aus fremden Paketen, damit kein späterer
    logger.exception() den Meldungstext doch noch ins Log bringt.
    """

    def formatException(self, ei) -> str:
        """Ersetzt Pythons vollständige Fehlerausgabe durch die Beschreibung ohne Meldungstext."""
        error_type, _error, tb = ei
        return describe_exception(error_type, tb)


def log_uncaught_exception(sender, request: HttpRequest, **kwargs) -> None:
    """Vermerkt einen unerwarteten Fehler mit neuer Fehlernummer im Log.

    Wird von Django bei jedem nicht abgefangenen Fehler aufgerufen, auch bei Fehlern in
    den Bausteinen vor und nach der Seite. Die Nummer hängt an der Anfrage, damit die
    Fehlerseite dieselbe zeigt.
    """
    error_type, _error, tb = sys.exc_info()
    request.error_number = new_error_number()
    logger.error(
        "Fehler %s bei %s: %s",
        request.error_number,
        address_pattern(request),
        describe_exception(error_type, tb) if error_type else "unbekannt",
    )


def connect_error_log() -> None:
    """Meldet das Fehlerprotokoll bei Django an. Aufgerufen beim Start des Tools (core/apps.py)."""
    got_request_exception.connect(log_uncaught_exception, dispatch_uid="core.errors.log_uncaught_exception")


def server_error(request: HttpRequest) -> HttpResponse:
    """Fehlerseite bei einem unerwarteten Fehler: kurzer Hinweis und Fehlernummer, keine technischen Einzelheiten.

    Fragt weder Datenbank noch Sitzung ab, damit sie auch erscheint, wenn gerade die
    Datenbank der Grund für den Fehler ist.
    """
    error_number = getattr(request, "error_number", None)
    content = get_template("500.html").render({"error_number": error_number})
    return HttpResponseServerError(content)


class ClientErrorLogMiddleware:
    """Vermerkt „nicht gefunden“ und „kein Zugriff“ als kurze Zeile im Log, ohne Fehlernummer und Konto.

    Ersetzt Djangos eigene Zeilen dazu, die die echte Adresse enthalten. Viele „kein Zugriff“
    können ab P2 ein Zeichen sein, dass jemand fremde Daten sucht.
    """

    MESSAGES = {404: "Nicht gefunden", 403: "Kein Zugriff"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        message = self.MESSAGES.get(response.status_code)
        if message:
            logger.warning("%s: %s", message, address_pattern(request))
        return response
