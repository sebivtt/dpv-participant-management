"""Anpassungen an allauth für den Login über Keycloak (#5).

allauth übernimmt den Austausch mit Keycloak. Hier steht, was das Tool anders macht als
allauths Grundeinstellung: Name, Mail und Benutzername bei jedem Login neu übernehmen, dazu
allauths Mail-Liste angleichen (#76), ohne Mail ablehnen,
nur den Login zulassen (kein Verknüpfen weiterer Konten), und bei jedem Problem zurück zur
Login-Seite mit einem kurzen Hinweis statt einer Fehlerseite.
"""

import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthError, AuthProcess
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import resolve_url
from requests import RequestException

from accounts import texts

logger = logging.getLogger(__name__)

# Die Fehlerwerte, die allauth beim gescheiterten Login liefert (allauth 65.20.1). Nur sie
# kommen ins Log; ein anderer Wert könnte frei gewählten Text aus der Adresse enthalten (#75).
KNOWN_AUTH_ERRORS = (AuthError.UNKNOWN, AuthError.CANCELLED, AuthError.DENIED)


def back_to_login_page(request: HttpRequest, hint: str) -> ImmediateHttpResponse:
    """Bricht den Login ab und führt mit dem Hinweis zurück zur Login-Seite."""
    messages.warning(request, hint)
    return ImmediateHttpResponse(HttpResponseRedirect(resolve_url("account_login")))


def _max_length(field: str) -> int:
    """Höchstlänge eines Feldes im Kontenmodell."""
    return get_user_model()._meta.get_field(field).max_length


def keycloak_data(sociallogin: SocialLogin) -> dict:
    """Die Angaben, die Keycloak beim Login zur Person geliefert hat (Name, Mail, Kennung)."""
    return sociallogin.account.get_provider().extract_common_fields(sociallogin.account.extra_data)


def align_mail_list(user, sociallogin: SocialLogin) -> None:
    """Gleicht allauths Mail-Liste an Keycloak an (#76, ORG-03).

    Danach steht dort genau ein Eintrag: die Mail aus Keycloak in genau dieser Schreibweise und
    Keycloaks Angabe, ob sie bestätigt ist (`email_verified`). Ältere Einträge werden gelöscht.
    Die Liste nutzt das Tool selbst noch nicht; die Prüfung „Mail bestätigt“ (#10) kann darauf
    aufbauen. Dass Keycloak eine Mail liefert, hat `pre_social_login` schon geprüft.
    """
    provider = sociallogin.account.get_provider()
    address = provider.extract_email_addresses(sociallogin.account.extra_data)[0]
    with transaction.atomic():
        EmailAddress.objects.filter(user=user).exclude(email=address.email).delete()
        EmailAddress.objects.update_or_create(
            user=user, email=address.email, defaults={"verified": bool(address.verified), "primary": True}
        )


def take_over_username(user, data: dict) -> None:
    """Übernimmt den Benutzernamen aus Keycloak in ein bestehendes Konto (#76).

    Die Suche nach Konten (#93) geht über den genauen Benutzernamen, deshalb muss er aktuell
    sein. Ist er im Tool schon an ein anderes Konto vergeben, bleibt der alte, und der Login
    gelingt trotzdem; beim nächsten Login wird es erneut versucht. Ins Log kommt dann nur eine
    Zeile ohne Benutzernamen, Mail und Kontonummer (#6). Liefert Keycloak keinen
    Benutzernamen, bleibt der bisherige.
    """
    username = (data.get("username") or "")[: _max_length("username")]
    if not username or username == user.username:
        return
    try:
        # Eigener Sicherungspunkt: Ein vergebener Name bricht sonst die ganze Anfrage ab.
        with transaction.atomic():
            get_user_model().objects.filter(pk=user.pk).update(username=username)
    except IntegrityError:
        logger.warning("Benutzername aus Keycloak im Tool schon vergeben, alter bleibt")
        return
    user.username = username


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
          Ebenso bei einer Mail, die länger ist, als das Tool speichern kann.
        - Ein im Tool gesperrtes Konto meldet sich nicht an. allauth zeigte sonst eine eigene
          Seite, die das Tool nicht hat; wie gesperrte Konten aussehen, klärt #8.
        - Bei einem bestehenden Konto kommen Name, Mail und Benutzername bei jedem Login neu
          aus Keycloak, und die Mail-Liste wird angeglichen (ORG-03, #76); allauth übernimmt
          sie sonst nur beim ersten Login.
        """
        if sociallogin.state.get("process", AuthProcess.LOGIN) != AuthProcess.LOGIN:
            logger.warning("Login abgelehnt: anderer Ablauf als Login angefragt")
            raise back_to_login_page(request, texts.LOGIN_CANCELLED)
        data = keycloak_data(sociallogin)
        if not data.get("email"):
            logger.warning("Login abgelehnt: Keycloak liefert keine Mail")
            raise back_to_login_page(request, texts.no_mail())
        if len(data["email"]) > _max_length("email"):
            logger.warning("Login abgelehnt: Mail aus Keycloak zu lang")
            raise back_to_login_page(request, texts.LOGIN_CANCELLED)
        if sociallogin.is_existing and not sociallogin.user.is_active:
            logger.warning("Login abgelehnt: Konto im Tool gesperrt")
            raise back_to_login_page(request, texts.LOGIN_CANCELLED)
        if sociallogin.is_existing:
            user = sociallogin.user
            self.populate_user(request, sociallogin, data)
            user.save(update_fields=["first_name", "last_name", "email"])
            take_over_username(user, data)
            align_mail_list(user, sociallogin)

    def save_user(self, request: HttpRequest, sociallogin: SocialLogin, form=None):
        """Legt beim ersten Login das Konto an und gleicht die Mail-Liste an (#76).

        allauth schreibt die Mail dabei klein, im Konto und in der Mail-Liste. Das Tool
        übernimmt sie wie bei jedem weiteren Login in der Schreibweise aus Keycloak.
        """
        user = super().save_user(request, sociallogin, form)
        email = keycloak_data(sociallogin)["email"]
        if user.email != email:
            user.email = email
            user.save(update_fields=["email"])
        align_mail_list(user, sociallogin)
        return user

    def populate_user(self, request: HttpRequest, sociallogin: SocialLogin, data: dict):
        """Übernimmt Benutzername, Mail, Vor- und Nachname aus Keycloak.

        Anders als allauths Grundeinstellung nur aus den getrennten Feldern für Vor- und
        Nachname. allauth teilt sonst den ganzen Namen am ersten Leerzeichen; fehlt in
        Keycloak der Vorname, stünde der Nachname dann als Vorname da („Hallo Testfrau!“).
        Den Benutzernamen setzt diese Methode nur bei neuen Konten; bei bestehenden übernimmt
        ihn `take_over_username`, weil er dort schon vergeben sein kann. Keycloak erlaubt längere Namen,
        als das Tool speichert; sie werden gekürzt statt mit einem Fehler abgewiesen.
        """
        user = sociallogin.user
        if not sociallogin.is_existing:
            user.username = (data.get("username") or "")[: _max_length("username")]
        user.email = data.get("email") or ""
        user.first_name = (data.get("first_name") or "")[: _max_length("first_name")]
        user.last_name = (data.get("last_name") or "")[: _max_length("last_name")]
        return user

    def is_auto_signup_allowed(self, request: HttpRequest, sociallogin: SocialLogin) -> bool:
        """Neue Konten entstehen immer direkt, ohne Formular im Tool (keine eigene Registrierung)."""
        return True

    def on_authentication_error(self, request: HttpRequest, provider, error=None, exception=None, extra_context=None):
        """Führt bei jedem gescheiterten Login zurück zur Login-Seite mit Hinweis, nie zu einer Fehlerseite.

        Ist Keycloak nicht erreichbar, lautet der Hinweis anders als bei einem abgebrochenen
        oder ungültigen Login, damit niemand vergeblich weiter probiert. Ins Log kommt nur
        einer der bekannten Fehlerwerte von allauth, sonst „anderer Wert“.
        """
        if isinstance(exception, RequestException):
            logger.warning("Login nicht möglich: Keycloak nicht erreichbar (%s)", type(exception).__name__)
            raise back_to_login_page(request, texts.KEYCLOAK_UNREACHABLE)
        logger.info("Login nicht abgeschlossen: %s", error if error in KNOWN_AUTH_ERRORS else "anderer Wert")
        raise back_to_login_page(request, texts.LOGIN_CANCELLED)
