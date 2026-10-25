"""Was sich das Tool zu einer Anmeldung merkt, fürs Abmelden und den Hinweis „Sitzung abgelaufen“ (#5).

Dazu die Obergrenze der Sitzung (#8): spätestens 12 Stunden nach dem Login ist Schluss.
"""

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

# Kennungs-Token von Keycloak in der Sitzung. Mit ihm meldet Keycloak beim Abmelden ohne
# Rückfrage ab („Möchtest du dich wirklich abmelden?“ entfällt).
LOGOUT_HINT_SESSION_KEY = "accounts_keycloak_id_token"

# Zeitpunkt des Logins in der Sitzung (Sekunden seit 1970), für die Obergrenze von 12 Stunden (#8).
LOGIN_TIME_SESSION_KEY = "accounts_login_time"

# Cookie, das nur „war hier angemeldet“ bedeutet, ohne Bezug zur Person. Es überdauert die
# Sitzung; so unterscheidet die Login-Seite „Sitzung abgelaufen“ von „nie angemeldet“.
# Beim Abmelden und nach dem Hinweis wird es gelöscht.
LOGGED_IN_BEFORE_COOKIE = "dpv_war_angemeldet"
LOGGED_IN_BEFORE_DAYS = 30


def remember_login(request: HttpRequest, response: HttpResponse, id_token: str) -> None:
    """Merkt sich nach dem Login das Kennungs-Token und setzt das Cookie „war angemeldet“."""
    request.session[LOGOUT_HINT_SESSION_KEY] = id_token
    response.set_cookie(
        LOGGED_IN_BEFORE_COOKIE,
        "1",
        max_age=LOGGED_IN_BEFORE_DAYS * 24 * 60 * 60,
        secure=request.is_secure(),
        httponly=True,
        samesite="Lax",
    )


def session_expired(request: HttpRequest) -> bool:
    """Sagt, ob jemand angemeldet war, sich nicht abgemeldet hat und jetzt keine Sitzung mehr hat."""
    return not request.user.is_authenticated and request.COOKIES.get(LOGGED_IN_BEFORE_COOKIE) == "1"


def forget_login(response: HttpResponse) -> None:
    """Löscht das Cookie „war angemeldet“."""
    response.delete_cookie(LOGGED_IN_BEFORE_COOKIE, samesite="Lax")


def remember_login_time(request: HttpRequest) -> None:
    """Merkt sich beim Login den Zeitpunkt, ab dem die Obergrenze zählt."""
    request.session[LOGIN_TIME_SESSION_KEY] = timezone.now().timestamp()


def login_too_old(request: HttpRequest) -> bool:
    """Sagt, ob der Login SESSION_MAX_HOURS oder länger her ist. Ohne Zeitpunkt gilt er als zu alt."""
    login_time = request.session.get(LOGIN_TIME_SESSION_KEY)
    if not isinstance(login_time, int | float):
        return True
    return timezone.now().timestamp() - login_time >= settings.SESSION_MAX_HOURS * 60 * 60


class SessionMaxAgeMiddleware:
    """Meldet im Tool ab, wessen Login SESSION_MAX_HOURS her ist, auch bei laufender Aktivität (#8).

    Danach geht es weiter wie nach 2 Stunden ohne Klick: Die Login-Pflicht leitet zur
    Login-Seite, dort steht „Sitzung abgelaufen“. Beim neuen Login merkt Keycloak, ob das Konto
    gesperrt oder gelöscht ist; das Tool fragt dafür nie selbst bei Keycloak nach. Konto, Rollen
    und Anmeldungen bleiben, wie sie sind.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated and login_too_old(request):
            logout(request)
        return self.get_response(request)
