"""Rundumtest: Jede Adresse verlangt einen Login, außer den Login-Seiten (#5, CONTRIBUTING.md, Abschnitt 4).

Geht alle Adressen des Tools durch, auch solche, die später dazukommen. Eine neue Adresse
ist ohne eigenes Zutun geschützt; wer sie öffentlich machen will, muss sie hier eintragen
und begründen.
"""

import re

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

# Die einzigen Adressen, die ohne Login antworten dürfen, mit Begründung.
PUBLIC = {
    # Die Login-Seite selbst.
    "account_login",
    # Start und Rückkehr des Logins bei Keycloak; davor ist noch niemand angemeldet.
    "openid_connect_login",
    "openid_connect_callback",
    # Abmelden auch ohne gültige Sitzung, damit nach abgelaufener Sitzung die Abmeldung
    # bei Keycloak trotzdem gelingt. Geschützt durch den Formularschutz (CSRF).
    "account_logout",
}


def _all_patterns(patterns, prefix: str = ""):
    """Liefert jede Adresse des Tools als (Muster, Eintrag), auch aus eingebundenen Listen."""
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _all_patterns(entry.url_patterns, prefix + str(entry.pattern))
        elif isinstance(entry, URLPattern):
            yield prefix + str(entry.pattern), entry


def _example_address(pattern: str) -> str:
    """Macht aus einem Muster wie anmelden/<str:provider_id>/start/ eine aufrufbare Adresse."""
    address = re.sub(r"<(?:\w+:)?\w+>", "1", pattern)
    address = re.sub(r"\(\?P<\w+>[^)]*\)", "1", address).lstrip("^").rstrip("$")
    return "/" + address


ALL = list(_all_patterns(get_resolver().url_patterns))


def test_rundumtest_findet_die_adressen_des_tools():
    names = {entry.name for _pattern, entry in ALL}
    assert {"start", *PUBLIC} <= names


def test_nur_die_login_seiten_sind_als_oeffentlich_markiert():
    public = {entry.name for _pattern, entry in ALL if getattr(entry.callback, "login_required", True) is False}

    assert public == PUBLIC


@pytest.mark.django_db
@pytest.mark.parametrize(("pattern", "entry"), [p for p in ALL if p[1].name not in PUBLIC], ids=lambda p: str(p))
def test_jede_andere_adresse_leitet_ohne_login_zum_login(client, pattern, entry):
    address = _example_address(pattern)

    for method in (client.get, client.post):
        response = method(address)
        assert response.status_code == 302, f"{address} antwortet ohne Login mit {response.status_code}"
        assert response["Location"].startswith("/anmelden/?next=")
