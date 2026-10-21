"""Stellt drei abgelehnte Anfragen in einem eigenen Prozess ohne pytest, wie im Betrieb (#25).

Aufgerufen von tests/test_fehlerprotokoll.py. Was dabei im Log erscheint, landet in der
Fehlerausgabe des Prozesses, auch das aus Pythons Notausgabe. Auf die normale Ausgabe kommen
nur die drei Statuscodes. Alle Daten sind erfunden.
"""

import sys

import django
from django.test.utils import override_settings, setup_test_environment

django.setup()
# Erlaubt den Servernamen „testserver“ des Testbrowsers, wie in pytest.
setup_test_environment()

# Erst nach django.setup() ladbar.
from django.test import Client

with override_settings(ROOT_URLCONF="tests.urls"):
    browser = Client(enforce_csrf_checks=True)
    responses = [
        # unbekannte Adresse mit frei gewähltem Text
        browser.get("/Erika-Testfrau-Allergie/"),
        # verdächtiger Servername mit frei gewähltem Text
        browser.get("/", HTTP_HOST="erika-testfrau-allergie.example"),
        # Formular ohne Formularschutz (CSRF), mit Nummer und Parameter in der Adresse
        browser.post("/test/987654/verboten/?suche=Erika", {"allergie": "Testallergie Erdnuss"}),
    ]

sys.stdout.write(" ".join(str(response.status_code) for response in responses) + "\n")
