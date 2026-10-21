"""Hinweise rund um den Login (#5), übersetzbar (NFA-02) und in der Du-Form."""

from django.conf import settings
from django.utils.translation import gettext, gettext_lazy

LOGIN_CANCELLED = gettext_lazy("Die Anmeldung wurde abgebrochen. Du kannst es noch einmal versuchen.")
KEYCLOAK_UNREACHABLE = gettext_lazy("Die Anmeldung ist gerade nicht möglich. Versuche es später noch einmal.")
SESSION_EXPIRED = gettext_lazy("Deine Sitzung ist abgelaufen. Bitte melde dich neu an.")


def no_mail() -> str:
    """Hinweis, wenn Keycloak keine Mail liefert; nennt die eingestellte Adresse für Hilfe."""
    return gettext(
        "Die Anmeldung ist nicht möglich, weil in deinem DPV-Konto keine Mail eingetragen ist. "
        "Wende dich an %(address)s."
    ) % {"address": settings.ACCOUNT_HELP_EMAIL}
