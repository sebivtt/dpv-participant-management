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
from django.db import IntegrityError, transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.cache import add_never_cache_headers
from django.views.decorators.http import require_POST
from requests import RequestException

from access.addresses import checks_rights, without_personal_data
from accounts import texts
from accounts.adapter import logger
from accounts.session import (
    LOGOUT_HINT_SESSION_KEY,
    forget_login,
    forget_logout,
    just_logged_out,
    remember_logout,
    session_expired,
)

PROVIDER_ID = "keycloak"


@without_personal_data("Login-Seite: Hinweise zum Login, keine Angaben einer Person (#5).")
@login_not_required
def login_page(request: HttpRequest) -> HttpResponse:
    """Login-Seite mit dem Knopf zum Login über Keycloak und dem Registrierungslink.

    Wer schon angemeldet ist, kommt zur Startseite. Ist der Registrierungslink ausgeblendet
    (REGISTRATION_LINK_ENABLED), steht dort stattdessen, an wen man sich für ein Konto wendet.
    Gleich nach dem Abmelden steht dort einmal „Du bist abgemeldet.“ (#280), sonst nach
    abgelaufener Sitzung einmal „Sitzung abgelaufen“.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    logged_out = just_logged_out(request)
    expired = session_expired(request)
    start = reverse("openid_connect_login", kwargs={"provider_id": PROVIDER_ID})
    context = {
        "start": start,
        # prompt=create öffnet bei Keycloak direkt die Registrierung statt des Logins.
        "registration_start": f"{start}?{urlencode({'auth_params': 'prompt=create'})}",
        "registration_link_enabled": settings.REGISTRATION_LINK_ENABLED,
        "help_email": settings.ACCOUNT_HELP_EMAIL,
        "next": request.GET.get("next", ""),
        "info_hint": texts.LOGGED_OUT if logged_out else texts.SESSION_EXPIRED if expired else "",
    }
    response = render(request, "accounts/login.html", context)
    if expired:
        forget_login(response)
    if logged_out:
        forget_logout(response)
    return response


# Fehler, wenn Keycloak nicht antwortet oder unter der eingestellten Adresse etwas anderes
# antwortet als Keycloak; dann fehlen in den Einstellungen des Realms Angaben (KeyError).
KEYCLOAK_FAILURES = (RequestException, KeyError)

# Die einzige zusätzliche Angabe, die beim Start an Keycloak gehen darf: Registrierung statt Login.
ALLOWED_START_QUERIES = [{}, {"auth_params": "prompt=create"}]


def _keycloak_unreachable(request: HttpRequest, error: Exception) -> HttpResponse:
    """Zurück zur Login-Seite mit Hinweis, wenn Keycloak nicht antwortet; im Log nur die Art des Fehlers."""
    logger.warning("Login nicht möglich: Keycloak nicht erreichbar (%s)", type(error).__name__)
    messages.error(request, texts.KEYCLOAK_UNREACHABLE)
    return redirect("account_login")


@without_personal_data("Startet nur den Login und leitet zu Keycloak weiter.")
@login_not_required
def keycloak_login(request: HttpRequest, provider_id: str) -> HttpResponse:
    """Startet den Login: leitet zu Keycloak weiter. Ist Keycloak nicht erreichbar, zurück zur Login-Seite.

    Nur per Formular (POST); ein bloßer Link führt zur Login-Seite, statt eine Seite von
    allauth zu zeigen. allauth reicht Angaben aus der Adresse (auth_params, scope) an Keycloak
    weiter, auch solche, die den Login verändern (z. B. eine andere Rückkehradresse). Erlaubt
    ist deshalb nur die Registrierung.
    """
    if request.method != "POST":
        return redirect("account_login")
    if request.GET.dict() not in ALLOWED_START_QUERIES:
        logger.warning("Login abgelehnt: unzulässige Angaben beim Start")
        messages.error(request, texts.LOGIN_CANCELLED)
        return redirect("account_login")
    try:
        return allauth_login(request, provider_id)
    except KEYCLOAK_FAILURES as error:
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


# Der Login selbst legt beim ersten Mal das Konto an und schreibt die Daten des Logins (EP-09, TD-01).
@checks_rights("EP-09", "TD-01")
@login_not_required
def keycloak_callback(request: HttpRequest, provider_id: str) -> HttpResponse:
    """Rückkehr von Keycloak. Prüfung und Abschluss des Logins übernimmt allauth (accounts/adapter.py).

    Fehler beim Austausch mit Keycloak fängt meist allauth ab; die Einstellungen des Realms
    fragt allauth aber vorher ab, ohne Fehler abzufangen. Deshalb auch hier der Hinweis.

    Alles läuft in einer Transaktion: Kommen zwei Rückkehren für dasselbe neue Konto fast
    gleichzeitig (Doppelklick, zwei Tabs), legt die zweite sonst ein Konto ohne Verknüpfung
    an und endet mit einem Fehler. So wird sie ganz zurückgenommen und führt zur Login-Seite;
    der nächste Klick auf „Anmelden“ findet das Konto der ersten.
    """
    try:
        with transaction.atomic():
            view = OAuth2CallbackView.adapter_view(KeycloakAdapter(request, provider_id))
            return view(request)
    except SocialApp.DoesNotExist as error:
        raise Http404 from error
    except IntegrityError:
        logger.warning("Login nicht abgeschlossen: gleichzeitiger Login mit demselben Konto")
        messages.error(request, texts.LOGIN_CANCELLED)
        return redirect("account_login")
    except KEYCLOAK_FAILURES as error:
        return _keycloak_unreachable(request, error)


@without_personal_data(
    "Beendet die Sitzung. Die kurze Seite enthält nur das eigene Kennungs-Token der Person, die sich "
    "gerade abmeldet, verdeckt im Formular an Keycloak und vom Browser nicht gespeichert (#280)."
)
@login_not_required
@require_POST
def logout(request: HttpRequest) -> HttpResponse:
    """Meldet vollständig ab: im Tool und danach bei Keycloak.

    Nur per Formular (POST) mit Formularschutz, damit keine fremde Seite jemanden abmelden
    kann. Ohne Login erreichbar, damit auch nach abgelaufener Sitzung die Abmeldung bei
    Keycloak gelingt; dann fragt Keycloak einmal nach, weil das Kennungs-Token fehlt.

    Das Token geht in einem Formular an Keycloak, das sich mit Skript selbst abschickt, und
    nicht in einer Adresse (#280): In der Grundeinstellung von Keycloak stehen darin Name und
    Mail, und eine Adresse landet im Browserverlauf und in fremden Protokollen. Die kurze Seite
    speichert der Browser nicht. Keycloak schickt danach zurück zur Login-Seite.
    """
    id_token = request.session.get(LOGOUT_HINT_SESSION_KEY, "")
    django_logout(request)
    fields = {
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "post_logout_redirect_uri": request.build_absolute_uri(reverse("account_login")),
    }
    if id_token:
        fields["id_token_hint"] = id_token
    context = {"action": f"{settings.KEYCLOAK_REALM_URL}/protocol/openid-connect/logout", "fields": fields}
    response = render(request, "accounts/abmelden.html", context)
    add_never_cache_headers(response)
    forget_login(response)
    remember_logout(request, response)
    return response
