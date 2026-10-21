"""Stellt drei abgelehnte Anfragen in einem eigenen Prozess ohne pytest, wie im Betrieb (#25).

Aufgerufen von tests/test_fehlerprotokoll.py. Was dabei im Log erscheint, landet in der
Fehlerausgabe des Prozesses, auch das aus Pythons Notausgabe. Auf die normale Ausgabe kommen
nur die vier Statuscodes. Alle Daten sind erfunden.

Die Anfragen greifen nicht auf die Datenbank zu. Wer hier eine Anfrage ergänzt, die das doch
tut: Dieser Prozess nutzt nicht die Testdatenbank von pytest, sondern die aus der Umgebung.
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
        # unerwarteter Fehler, dessen Meldungstext Formulardaten enthält; zeigt die Fehlerseite
        Client(raise_request_exception=False).post("/test/987654/?suche=Erika", {"allergie": "Testallergie Erdnuss"}),
    ]

sys.stdout.write(" ".join(str(response.status_code) for response in responses) + "\n")
