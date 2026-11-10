"""Hinweise rund um den Login (#5), übersetzbar (NFA-02) und in der Du-Form."""

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy

LOGIN_CANCELLED = gettext_lazy("Die Anmeldung wurde abgebrochen. Du kannst es noch einmal versuchen.")
KEYCLOAK_UNREACHABLE = gettext_lazy("Die Anmeldung ist gerade nicht möglich. Versuche es später noch einmal.")
SESSION_EXPIRED = gettext_lazy("Deine Sitzung ist abgelaufen. Bitte melde dich neu an.")
LOGGED_OUT = gettext_lazy("Du bist abgemeldet.")


def no_mail() -> str:
    """Hinweis, wenn Keycloak keine Mail liefert; nennt die eingestellte Adresse für Hilfe."""
    return gettext(
        "Die Anmeldung ist nicht möglich, weil in deinem DPV-Konto keine Mail eingetragen ist. "
        "Wende dich an %(address)s."
    ) % {"address": settings.ACCOUNT_HELP_EMAIL}

# Fahrtenname auf „Mein Profil“ (#111), Wortlaute von Sebastian (Nachklärung vom 26.10.2026).
SCOUT_NAME_SAVED = gettext_lazy("Dein Fahrtenname ist gespeichert.")
SCOUT_NAME_DELETED = gettext_lazy("Dein Fahrtenname ist gelöscht.")
SCOUT_NAME_TOO_LONG = gettext_lazy("Dein Fahrtenname darf höchstens 30 Zeichen lang sein.")
SCOUT_NAME_FAILED = gettext_lazy("Dein Fahrtenname konnte nicht gespeichert werden. Versuche es noch einmal.")
