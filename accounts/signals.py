"""Schritte direkt nach dem Login (#5)."""

from allauth.account.signals import user_logged_in
from django.contrib.auth.signals import user_logged_in as django_user_logged_in
from django.dispatch import receiver

from accounts.session import remember_login, remember_login_time


@receiver(user_logged_in, dispatch_uid="accounts.signals.after_login")
def after_login(sender, request, response, user, sociallogin=None, **kwargs) -> None:
    """Merkt sich nach dem Login, was fürs Abmelden und den Hinweis „Sitzung abgelaufen“ nötig ist."""
    remember_login(request, response, getattr(sociallogin, "keycloak_id_token", ""))


@receiver(django_user_logged_in, dispatch_uid="accounts.signals.login_time")
def after_any_login(sender, request, user, **kwargs) -> None:
    """Merkt sich den Zeitpunkt jedes Logins für die Obergrenze der Sitzung (#8).

    Djangos eigenes Signal statt dem von allauth, damit kein Weg zum Login ihn auslässt.
    """
    remember_login_time(request)
