"""Tests für die Sicherheitsrichtlinie für Skripte (Content-Security-Policy, #278).

Die Kürzel verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #278. Hier wird geprüft, was der
Server schickt; ob der Browser sich daran hält und kein Verstoß auftritt, prüft
rauchtests/test_sicherheitsrichtlinie.py, die Testumgebung im Container (E5) containertests/.
Alle Daten sind erfunden.
"""

import pytest
from django.conf import settings
from django.test import Client

from tests.test_fehlerseiten import ERROR_PAGES, _logged_in_client

pytestmark = pytest.mark.django_db

HEADER = "Content-Security-Policy"


def _expected() -> dict[str, list[str]]:
    """Inhalt der Richtlinie laut Akzeptanzkriterium von #278, je Regel die erlaubten Quellen."""
    return {
        "default-src": ["'none'"],
        "script-src": ["'self'"],
        "style-src": ["'self'"],
        "font-src": ["'self'"],
        "img-src": ["'self'", "data:"],
        "connect-src": ["'self'"],
        "object-src": ["'none'"],
        "base-uri": ["'none'"],
        "frame-ancestors": ["'none'"],
        "form-action": ["'self'", f"{settings.KEYCLOAK_REALM_URL}/"],
    }


def _rules(response) -> dict[str, list[str]]:
    rules = {}
    for part in response.headers[HEADER].split(";"):
        name, *sources = part.split()
        rules[name] = sources
    return rules


# E4: Login-Seite, Startseite und Dateien vom eigenen Server tragen die ganze Richtlinie.
@pytest.mark.parametrize(
    "address, logged_in",
    [("/anmelden/", False), ("/", True), ("/static/core/app.js", False)],
    ids=["login-seite", "startseite", "datei-vom-eigenen-server"],
)
def test_antworten_tragen_die_ganze_richtlinie(address, logged_in):
    client = _logged_in_client() if logged_in else Client()

    response = client.get(address)

    assert response.status_code == 200
    assert _rules(response) == _expected()


# E4: auch „nicht gefunden“, „kein Zugriff“, „Formular abgelaufen“, „ungültige Anfrage“ und „Serverfehler“
@pytest.mark.urls("tests.urls")
@pytest.mark.parametrize("request_page, status", ERROR_PAGES)
def test_jede_fehlerseite_traegt_die_ganze_richtlinie(request_page, status):
    response = request_page(_logged_in_client())

    assert response.status_code == status
    assert _rules(response) == _expected()


# Gleich streng überall: nie nur beobachtend, nie mit eingebettetem Code oder Ausführen von Text als Code.
def test_richtlinie_wirkt_und_erlaubt_keinen_eingebetteten_code():
    response = Client().get("/anmelden/")

    assert f"{HEADER}-Report-Only" not in response.headers
    assert "unsafe" not in response.headers[HEADER]
    assert "nonce" not in response.headers[HEADER]
    assert settings.SECURE_CSP_REPORT_ONLY == {}
