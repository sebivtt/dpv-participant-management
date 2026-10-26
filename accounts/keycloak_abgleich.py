"""Abgleich mit Keycloak bei jedem Login: Mail-Liste von allauth und Benutzername (#76, ORG-03).

Eigene Datei, weil sie Anmeldedaten selbst aus der Datenbank liest und schreibt. Der Rundumtest
lässt das nur hier zu (`tests/test_rundumtest.py`): Die Funktionen ändern allein das Konto, das
sich gerade anmeldet, mit den Angaben aus Keycloak, und zeigen nichts an. Aufgerufen werden sie
nur aus `accounts/adapter.py`.
"""

import logging
import re

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialLogin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)

# Leerzeichen jeder Art: alles, was Python als Leerraum kennt (auch das geschützte und das
# schmale Leerzeichen), dazu die unsichtbaren Zeichen, die es nicht dazu zählt (#77).
_INVISIBLE = r"\s\u00ad\u180e\u200b-\u200d\u2060\ufeff"
_EDGE_SPACES = re.compile(f"^[{_INVISIBLE}]+|[{_INVISIBLE}]+$")


def trimmed(value, max_length: int | None = None) -> str:
    """Entfernt Leerzeichen am Anfang und Ende einer Angabe aus Keycloak (#77).

    Gilt für Vorname, Nachname, Mail und Benutzername; was danach leer ist, gilt als fehlend.
    Innen bleibt alles, wie es im DPV-Konto steht, auch mehrere Leerzeichen hintereinander:
    Das Tool reinigt den Namen, verändert ihn aber nicht (Sebastian, 22.10.2026).

    `max_length` kürzt zu lange Angaben auf die Länge, die das Tool speichert. Danach wird
    erneut gereinigt: Fällt das Kürzen mitten in einen Namen, stünde sonst wieder ein
    Leerzeichen am Ende („Anna Lena“ gekürzt zu „Anna “).
    """
    value = _EDGE_SPACES.sub("", value or "")
    if max_length is None:
        return value
    return _EDGE_SPACES.sub("", value[:max_length])


def align_mail_list(user, sociallogin: SocialLogin) -> None:
    """Gleicht allauths Mail-Liste an Keycloak an (#76, ORG-03).

    Danach steht dort genau ein Eintrag: die Mail aus Keycloak in genau dieser Schreibweise, ohne
    Leerzeichen am Rand (#77), und Keycloaks Angabe, ob sie bestätigt ist (`email_verified`).
    Ältere Einträge werden gelöscht.
    Die Liste nutzt das Tool selbst noch nicht; die Prüfung „Mail bestätigt“ (#10) kann darauf
    aufbauen. Dass Keycloak eine Mail liefert, hat `pre_social_login` schon geprüft.
    """
    provider = sociallogin.account.get_provider()
    address = provider.extract_email_addresses(sociallogin.account.extra_data)[0]
    email = trimmed(address.email)
    with transaction.atomic():
        # Sperrt die eigene Kontozeile: Zwei gleichzeitige Logins derselben Person mit
        # verschiedenen Mails liefen sonst beide in die Regel „nur ein Haupteintrag“.
        get_user_model().objects.select_for_update().filter(pk=user.pk).exists()
        EmailAddress.objects.filter(user=user).exclude(email=email).delete()
        EmailAddress.objects.update_or_create(
            user=user, email=email, defaults={"verified": bool(address.verified), "primary": True}
        )


def take_over_username(user, data: dict) -> None:
    """Übernimmt den Benutzernamen aus Keycloak in ein bestehendes Konto (#76).

    Die Suche nach Konten (#93) geht über den genauen Benutzernamen, deshalb muss er aktuell
    sein. Ist er im Tool schon an ein anderes Konto vergeben, bleibt der alte, und der Login
    gelingt trotzdem; beim nächsten Login wird es erneut versucht. Vergeben heißt wie bei
    allauths erstem Login: auch in anderer Groß- und Kleinschreibung. Ins Log kommt dann nur eine
    Zeile ohne Benutzernamen, Mail und Kontonummer (#6). Liefert Keycloak keinen
    Benutzernamen, bleibt der bisherige.
    """
    username = trimmed(data.get("username"), get_user_model()._meta.get_field("username").max_length)
    if not username or username == user.username:
        return
    users = get_user_model().objects
    # Erst nachsehen statt nur auf die Datenbank zu bauen: Deren eigenes Log nennt bei einem
    # abgelehnten Speichern den Namen. Die Sperre der Datenbank bleibt für den Wettlauf.
    if users.filter(username__iexact=username).exclude(pk=user.pk).exists():
        logger.warning("Benutzername aus Keycloak im Tool schon vergeben, alter bleibt")
        return
    try:
        # Eigener Sicherungspunkt: Ein vergebener Name bricht sonst die ganze Anfrage ab.
        with transaction.atomic():
            users.filter(pk=user.pk).update(username=username)
    except IntegrityError:
        logger.warning("Benutzername aus Keycloak im Tool schon vergeben, alter bleibt")
        return
    user.username = username
