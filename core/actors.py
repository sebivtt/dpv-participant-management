"""Wer eine Änderung macht: gemeinsam für das Protokoll der Rollen (#91) und der Struktur (#131).

Beide Protokolle verlangen bei jeder Änderung die Angabe `by`: ein gespeichertes Konto oder
`SERVER_COMMAND`. Ohne sie lehnt das Tool ab, damit keine Seite den Urheber still vergisst.
"""

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy

# Urheber von Änderungen per Befehl auf dem Server. Wer ihn eingetippt hat, weiß das Tool nicht (#91).
SERVER_COMMAND = object()
SERVER_COMMAND_NAME = gettext_lazy("Befehl auf dem Server")


def check_actor(by) -> None:
    """Lehnt eine Änderung ab, die nicht nennt, wer sie macht."""
    if by is SERVER_COMMAND or (isinstance(by, get_user_model()) and by.pk is not None):
        return
    raise ValueError("Wer ändert, muss ein gespeichertes Konto oder SERVER_COMMAND sein.")


def actor_id(by) -> int | None:
    """Die Kennung des Kontos, das ändert; bei Befehlen auf dem Server keine."""
    return None if by is SERVER_COMMAND else by.pk


def actor_name(by) -> str:
    """Wie der Urheber im Protokoll heißt, zum Zeitpunkt der Änderung."""
    return str(SERVER_COMMAND_NAME) if by is SERVER_COMMAND else person_name(by)


def person_name(user) -> str:
    """Der Name für Meldungen; ohne Namen in Keycloak der Benutzername."""
    return user.get_full_name() or user.username
