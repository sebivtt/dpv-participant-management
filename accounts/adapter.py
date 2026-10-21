"""Anpassungen an allauth für den Login über Keycloak (#5).

allauth übernimmt den Austausch mit Keycloak. Hier steht, was das Tool anders macht als
allauths Grundeinstellung: Name und Mail bei jedem Login neu übernehmen, ohne Mail ablehnen,
nur den Login zulassen (kein Verknüpfen weiterer Konten), und bei jedem Problem zurück zur
Login-Seite mit einem kurzen Hinweis statt einer Fehlerseite.
"""

import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthProcess
from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import resolve_url
from requests import RequestException

from accounts import texts

logger = logging.getLogger(__name__)


def back_to_login_page(request: HttpRequest, hint: str) -> ImmediateHttpResponse:
    """Bricht den Login ab und führt mit dem Hinweis zurück zur Login-Seite."""
    messages.warning(request, hint)
    return ImmediateHttpResponse(HttpResponseRedirect(resolve_url("account_login")))


def keycloak_data(sociallogin: SocialLogin) -> dict:
    """Die Angaben, die Keycloak beim Login zur Person geliefert hat (Name, Mail, Kennung)."""
    return sociallogin.account.get_provider().extract_common_fields(sociallogin.account.extra_data)


class AccountAdapter(DefaultAccountAdapter):
    """Schaltet allauths eigene Meldungen ab.

    Sie sind englisch, nennen teils den Benutzernamen und würden auf der nächsten Seite
    erscheinen, etwa „Successfully signed in as erika.testfrau“. Das Tool zeigt nur eigene
    Hinweise in der Du-Form.
    """

    def add_message(self, *args, **kwargs) -> None:
        """Zeigt keine Meldung von allauth an."""


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Regeln des Tools für den Login über Keycloak."""

    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        """Prüft jeden Login, nachdem Keycloak geantwortet hat, und übernimmt Name und Mail.

        - Nur der Login selbst ist erlaubt. allauth kann auch ein weiteres Keycloak-Konto an
          ein bestehendes Konto hängen („connect“); das Tool verknüpft genau eines.
        - Ohne Mail kein Login. Ins Log kommt nur eine kurze Zeile ohne Personendaten (#6).
        - Bei einem bestehenden Konto kommen Name und Mail bei jedem Login neu aus Keycloak
          (ORG-03); allauth übernimmt sie sonst nur beim ersten Login.
        """
        if sociallogin.state.get("process", AuthProcess.LOGIN) != AuthProcess.LOGIN:
            logger.warning("Login abgelehnt: anderer Ablauf als Login angefragt")
            raise back_to_login_page(request, texts.LOGIN_CANCELLED)
        data = keycloak_data(sociallogin)
        if not data.get("email"):
            logger.warning("Login abgelehnt: Keycloak liefert keine Mail")
            raise back_to_login_page(request, texts.no_mail())
        if sociallogin.is_existing:
            user = sociallogin.user
            self.populate_user(request, sociallogin, data)
            user.save(update_fields=["first_name", "last_name", "email"])

    def populate_user(self, request: HttpRequest, sociallogin: SocialLogin, data: dict):
        """Übernimmt Benutzername, Mail, Vor- und Nachname aus Keycloak.

        Anders als allauths Grundeinstellung nur aus den getrennten Feldern für Vor- und
        Nachname. allauth teilt sonst den ganzen Namen am ersten Leerzeichen; fehlt in
        Keycloak der Vorname, stünde der Nachname dann als Vorname da („Hallo Testfrau!“).
        Den Benutzernamen setzt allauth nur bei neuen Konten.
        """
        user = sociallogin.user
        if not sociallogin.is_existing:
            user.username = data.get("username") or ""
        user.email = data.get("email") or ""
        user.first_name = data.get("first_name") or ""
        user.last_name = data.get("last_name") or ""
        return user

    def is_auto_signup_allowed(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        """Neue Konten entstehen immer direkt, ohne Formular im Tool (keine eigene Registrierung)."""
        return True

    def on_authentication_error(self, request: HttpRequest, provider, error=None, exception=None, extra_context=None):
        """Führt bei jedem gescheiterten Login zurück zur Login-Seite mit Hinweis, nie zu einer Fehlerseite.

        Ist Keycloak nicht erreichbar, lautet der Hinweis anders als bei einem abgebrochenen
        oder ungültigen Login, damit niemand vergeblich weiter probiert.
        """
        if isinstance(exception, RequestException):
            logger.warning("Login nicht möglich: Keycloak nicht erreichbar (%s)", type(exception).__name__)
            raise back_to_login_page(request, texts.KEYCLOAK_UNREACHABLE)
        logger.info("Login nicht abgeschlossen: %s", error)
        raise back_to_login_page(request, texts.LOGIN_CANCELLED)
