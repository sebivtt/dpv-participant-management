"""Was sich das Tool zu einer Anmeldung merkt, fürs Abmelden und den Hinweis „Sitzung abgelaufen“ (#5)."""

from django.http import HttpRequest, HttpResponse

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
