"""Abgleich mit Keycloak bei jedem Login: Mail-Liste von allauth und Benutzername (#76, ORG-03).

Eigene Datei, weil sie Anmeldedaten selbst aus der Datenbank liest und schreibt. Der Rundumtest
lässt das nur hier zu (`tests/test_rundumtest.py`): Die Funktionen ändern allein das Konto, das
sich gerade anmeldet, mit den Angaben aus Keycloak, und zeigen nichts an. Aufgerufen werden sie
nur aus `accounts/adapter.py`.
"""

import logging

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)


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
    username = (data.get("username") or "")[: get_user_model()._meta.get_field("username").max_length]
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
