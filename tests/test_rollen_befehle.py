"""Tests für den Befehl, mit dem Admins auf dem Server ernannt und entfernt werden (#89).

Bis ADM-01 (P6) wird jeder Admin so ernannt, nie über das Tool, über Keycloak oder als erstes
angemeldetes Konto. Die Nummern verweisen auf die Szenarien im Issue #89. Die Einträge im
Protokoll der Rollenänderungen prüft tests/test_rollen_protokoll.py (#91).
"""

import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from roles.models import SERVER_COMMAND, Role

pytestmark = pytest.mark.django_db

UNKNOWN = "Kein Konto mit diesem Benutzernamen. Die Person muss sich zuerst einmal im Tool anmelden."


def run(*arguments: str) -> str:
    """Ruft den Befehl auf wie ein Admin auf dem Server und gibt seine Ausgabe zurück."""
    output = io.StringIO()
    call_command(*arguments, stdout=output, stderr=output)
    return output.getvalue()


def refused(*arguments: str) -> str:
    """Ruft den Befehl auf, der ablehnen muss, und gibt den genannten Grund zurück."""
    with pytest.raises(CommandError) as error:
        run(*arguments)
    return str(error.value)


def admins() -> list[str]:
    return list(Role.objects.filter(kind=Role.Kind.ADMIN).values_list("user__username", flat=True))


@pytest.fixture
def erika():
    """Ein Konto, das sich schon einmal angemeldet hat."""
    return get_user_model().objects.create(username="erika.testfrau", first_name="Erika", last_name="Testfrau")


def test_admin_ernennen(erika):
    """S15."""
    assert "erika.testfrau ist jetzt Admin." in run("admin", "grant", "erika.testfrau")

    assert admins() == ["erika.testfrau"]
    erika.refresh_from_db()
    assert not erika.is_superuser
    assert not erika.is_staff


def test_zweimal_ernennen_aendert_nichts(erika):
    run("admin", "grant", "erika.testfrau")

    assert "erika.testfrau ist schon Admin." in run("admin", "grant", "erika.testfrau")
    assert admins() == ["erika.testfrau"]


def test_unbekannter_benutzername(erika):
    """S16: auch beim Entfernen."""
    assert UNKNOWN in refused("admin", "grant", "max.testmann")
    assert UNKNOWN in refused("admin", "revoke", "max.testmann")
    assert admins() == []


def test_admin_entfernen_auch_den_letzten(erika):
    """S17: Mit Zugang zum Server lässt sich jederzeit ein neuer ernennen."""
    run("admin", "grant", "erika.testfrau")

    assert "erika.testfrau ist jetzt kein Admin mehr." in run("admin", "revoke", "erika.testfrau")
    assert admins() == []


def test_entfernen_wer_kein_admin_ist(erika):
    assert "erika.testfrau ist kein Admin." in refused("admin", "revoke", "erika.testfrau")


def test_entfernen_laesst_andere_rollen_stehen(erika):
    """S18."""
    from units.models import Unit

    dpv = Unit(kind=Unit.Kind.FEDERATION, name="DPV")
    dpv.save(by=SERVER_COMMAND)
    Role(user=erika, kind=Role.Kind.FEDERATION_LEAD, unit=dpv).save(by=SERVER_COMMAND)
    run("admin", "grant", "erika.testfrau")

    run("admin", "revoke", "erika.testfrau")

    assert list(Role.objects.values_list("kind", flat=True)) == [Role.Kind.FEDERATION_LEAD]
