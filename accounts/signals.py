"""Schritte direkt nach dem Login (#5)."""

from allauth.account.signals import user_logged_in
from django.dispatch import receiver

from accounts.session import remember_login


@receiver(user_logged_in, dispatch_uid="accounts.signals.after_login")
def after_login(sender, request, response, user, sociallogin=None, **kwargs) -> None:
    """Merkt sich nach dem Login, was fürs Abmelden und den Hinweis „Sitzung abgelaufen“ nötig ist."""
    remember_login(request, response, getattr(sociallogin, "keycloak_id_token", ""))
