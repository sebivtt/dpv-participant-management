"""Login-Seite, Login über Keycloak und Abmelden (#5).

Diese Adressen sind als einzige ohne Login erreichbar (@login_not_required); der Rundumtest
in tests/test_rundumtest.py achtet darauf, dass es dabei bleibt.
"""

from urllib.parse import urlencode

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.views import OAuth2CallbackView
from allauth.socialaccount.providers.openid_connect.views import OpenIDConnectOAuth2Adapter
from allauth.socialaccount.providers.openid_connect.views import login as allauth_login
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as django_logout
from django.contrib.auth.decorators import login_not_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from requests import RequestException

from accounts import texts
from accounts.adapter import logger
from accounts.session import LOGOUT_HINT_SESSION_KEY, forget_login, session_expired

PROVIDER_ID = "keycloak"


@login_not_required
def login_page(request: HttpRequest) -> HttpResponse:
    """Login-Seite mit dem Knopf zum Login über Keycloak und dem Registrierungslink.

    Wer schon angemeldet ist, kommt zur Startseite. Ist der Registrierungslink ausgeblendet
    (REGISTRATION_LINK_ENABLED), steht dort stattdessen, an wen man sich für ein Konto wendet.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    expired = session_expired(request)
    start = reverse("openid_connect_login", kwargs={"provider_id": PROVIDER_ID})
    context = {
        "start": start,
        # prompt=create öffnet bei Keycloak direkt die Registrierung statt des Logins.
        "registration_start": f"{start}?{urlencode({'auth_params': 'prompt=create'})}",
        "registration_link_enabled": settings.REGISTRATION_LINK_ENABLED,
        "help_email": settings.ACCOUNT_HELP_EMAIL,
        "next": request.GET.get("next", ""),
        "session_expired_hint": texts.SESSION_EXPIRED if expired else "",
    }
    response = render(request, "accounts/login.html", context)
    if expired:
        forget_login(response)
    return response


def _keycloak_unreachable(request: HttpRequest, error: RequestException) -> HttpResponse:
    """Zurück zur Login-Seite mit Hinweis, wenn Keycloak nicht antwortet; im Log nur die Art des Fehlers."""
    logger.warning("Login nicht möglich: Keycloak nicht erreichbar (%s)", type(error).__name__)
    messages.warning(request, texts.KEYCLOAK_UNREACHABLE)
    return redirect("account_login")


@login_not_required
def keycloak_login(request: HttpRequest, provider_id: str) -> HttpResponse:
    """Startet den Login: leitet zu Keycloak weiter. Ist Keycloak nicht erreichbar, zurück zur Login-Seite."""
    try:
        return allauth_login(request, provider_id)
    except RequestException as error:
        return _keycloak_unreachable(request, error)


class KeycloakAdapter(OpenIDConnectOAuth2Adapter):
    """Wie allauths Anbindung an OpenID Connect, hebt aber das Kennungs-Token für das Abmelden auf.

    allauth bewahrt es nicht auf. Ohne es fragt Keycloak beim Abmelden nach, ob man sich
    wirklich abmelden will (accounts/session.py).
    """

    def complete_login(self, request: HttpRequest, app, token, **kwargs):
        """Schließt den Login ab wie allauth und hängt das Kennungs-Token an den Login an."""
        sociallogin = super().complete_login(request, app, token, **kwargs)
        sociallogin.keycloak_id_token = kwargs["response"].get("id_token", "")
        return sociallogin


@login_not_required
def keycloak_callback(request: HttpRequest, provider_id: str) -> HttpResponse:
    """Rückkehr von Keycloak. Prüfung und Abschluss des Logins übernimmt allauth (accounts/adapter.py).

    Fehler beim Austausch mit Keycloak fängt meist allauth ab; die Einstellungen des Realms
    fragt allauth aber vorher ab, ohne Fehler abzufangen. Deshalb auch hier der Hinweis.
    """
    try:
        view = OAuth2CallbackView.adapter_view(KeycloakAdapter(request, provider_id))
        return view(request)
    except SocialApp.DoesNotExist as error:
        raise Http404 from error
    except RequestException as error:
        return _keycloak_unreachable(request, error)


@login_not_required
@require_POST
def logout(request: HttpRequest) -> HttpResponse:
    """Meldet vollständig ab: im Tool und danach bei Keycloak.

    Nur per Formular (POST) mit Formularschutz, damit keine fremde Seite jemanden abmelden
    kann. Ohne Login erreichbar, damit auch nach abgelaufener Sitzung die Abmeldung bei
    Keycloak gelingt; dann fragt Keycloak einmal nach, weil das Kennungs-Token fehlt.
    Keycloak schickt danach zurück zur Login-Seite.
    """
    id_token = request.session.get(LOGOUT_HINT_SESSION_KEY, "")
    django_logout(request)
    parameters = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": request.build_absolute_uri(reverse("account_login")),
    }
    if id_token:
        parameters["id_token_hint"] = id_token
    response = HttpResponseRedirect(
        f"{settings.KEYCLOAK_REALM_URL}/protocol/openid-connect/logout?{urlencode(parameters)}"
    )
    forget_login(response)
    return response
