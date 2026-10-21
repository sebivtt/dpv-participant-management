"""Tests für das Fehlerprotokoll ohne Personendaten (#6, DSG-08).

Geprüft wird die tatsächliche Ausgabe der eingestellten Log-Ausgaben, nicht nur, was an
Django übergeben wird. Alle Daten sind erfunden.
"""

import io
import logging
import re

import pytest
from django.contrib.auth.models import User
from django.db import OperationalError, connection

pytestmark = pytest.mark.urls("tests.urls")

# Fehlernummer wie 7F3K-92QA: ohne 0, 1, I, L und O, die man leicht verwechselt.
ERROR_NUMBER = re.compile(r"[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}")

# Erfundene Werte, die nie im Log stehen dürfen: Formularinhalt, Sitzungsinhalt,
# Kontonummer, Benutzername, Mail, echte Nummer aus der Adresse, Parameter der Adresse
# und ein Wort aus dem Meldungstext des Fehlers.
ACCOUNT_NUMBER = 4242424
NUMBER_IN_ADDRESS = 987654
NEVER_IN_LOG = [
    "Testallergie Erdnuss",
    "Testsitzung Geheimnis",
    str(ACCOUNT_NUMBER),
    "erika",
    str(NUMBER_IN_ADDRESS),
    "suche",
    "Testfehler",
]


@pytest.fixture
def log_output(capsys):
    """Fängt alles ab, was die eingestellten Log-Ausgaben schreiben, und gibt es als Text zurück.

    Die Ausgaben des Tools werden beim Start eingerichtet und schreiben dann an ihr festes Ziel.
    Deshalb wird ihr Ziel für die Dauer des Tests umgelenkt. Was ohne eingerichtete Ausgabe
    trotzdem erscheint (Pythons Notausgabe), fängt capsys ab. Die Aufzeichnung von pytest
    selbst bleibt außen vor; sie gibt es im Betrieb nicht.
    """
    buffer = io.StringIO()
    loggers = [logging.getLogger(), *logging.Logger.manager.loggerDict.values()]
    handlers = {
        handler
        for logger in loggers
        if isinstance(logger, logging.Logger)
        for handler in logger.handlers
        # pytest hängt eigene Aufzeichnungen an; die gehören nicht zum Tool.
        if isinstance(handler, logging.StreamHandler) and not type(handler).__module__.startswith("_pytest")
    }
    previous = {handler: handler.setStream(buffer) for handler in handlers}

    def read() -> str:
        captured = capsys.readouterr()
        return buffer.getvalue() + captured.out + captured.err

    yield read
    for handler, stream in previous.items():
        handler.setStream(stream)


@pytest.fixture
def client(client):
    """Testbrowser, der bei einem Fehler wie im Betrieb die Fehlerseite zeigt, statt den Test abzubrechen."""
    client.raise_request_exception = False
    return client


@pytest.fixture
def erika(client, db):
    """Angemeldetes erfundenes Testkonto mit einem Eintrag in der Sitzung."""
    account = User.objects.create(
        id=ACCOUNT_NUMBER, username="erika.testfrau", email="erika@example.org", first_name="Erika"
    )
    client.force_login(account)
    session = client.session
    session["notiz"] = "Testsitzung Geheimnis"
    session.save()
    return account


def _assert_nothing_personal(log: str) -> None:
    for value in NEVER_IN_LOG:
        assert value.lower() not in log.lower(), f"„{value}“ steht im Log:\n{log}"


def _error_number_on_page(response) -> str:
    page = response.content.decode()
    match = ERROR_NUMBER.search(page)
    assert match, f"Keine Fehlernummer auf der Fehlerseite:\n{page}"
    return match.group()


def _trigger_error(client):
    return client.post(
        f"/test/{NUMBER_IN_ADDRESS}/?suche=Erika+Testfrau",
        {"allergie": "Testallergie Erdnuss"},
    )


# Szenario 1
def test_fehler_steht_mit_nummer_im_log_ohne_formular_sitzung_und_konto(client, erika, log_output):
    response = _trigger_error(client)

    assert response.status_code == 500
    number = _error_number_on_page(response)
    log = log_output()
    assert f"Fehler {number}" in log
    assert "ValueError" in log
    assert "tests/urls.py" in log  # Stelle im Code
    _assert_nothing_personal(log)


def test_fehlerseite_zeigt_hinweis_und_keine_technischen_einzelheiten(client, erika):
    response = _trigger_error(client)

    page = response.content.decode()
    assert "Da ist etwas schiefgelaufen." in page
    assert "Wenn du dich meldest, nenne bitte diese Nummer:" in page
    for detail in ["ValueError", "Traceback", "tests/urls.py", "Testallergie Erdnuss", "Testsitzung Geheimnis"]:
        assert detail not in page


# Szenario 2
def test_im_log_steht_das_muster_der_adresse_ohne_nummer_und_parameter(client, erika, log_output):
    _trigger_error(client)

    log = log_output()
    assert "/test/<int:number>/" in log
    assert str(NUMBER_IN_ADDRESS) not in log
    assert "suche" not in log


# Szenario 3
def test_meldungstext_des_fehlers_steht_nicht_im_log(client, erika, log_output):
    _trigger_error(client)

    log = log_output()
    assert "ValueError" in log
    assert "Testfehler" not in log


def test_auch_andere_logeintraege_zeigen_vom_fehler_nur_die_art(log_output):
    # Schützt auch spätere Log-Einträge aus eigenem Code und aus fremden Paketen.
    for logger_name in ["core.beispiel", "fremdes.paket"]:
        try:
            raise ValueError("erika@example.org existiert schon")
        except ValueError:
            logging.getLogger(logger_name).exception("Beispiel")

    log = log_output()
    assert log.count("ValueError") == 2
    assert "erika" not in log


# Szenario 4
def test_zwei_fehler_bekommen_verschiedene_nummern(client, erika):
    first = _error_number_on_page(_trigger_error(client))
    second = _error_number_on_page(_trigger_error(client))

    assert first != second


# Szenario 5
@pytest.mark.django_db
def test_fehler_ohne_login_gleiche_fehlerseite_und_gleicher_logeintrag(client, log_output):
    response = _trigger_error(client)

    assert response.status_code == 500
    number = _error_number_on_page(response)
    log = log_output()
    assert f"Fehler {number} bei /test/<int:number>/: ValueError" in log
    _assert_nothing_personal(log)


# Szenario 6
def test_fehlerberichte_gehen_nicht_per_mail_raus(client, erika, mailoutbox, settings):
    settings.ADMINS = [("Admin", "admin@example.org")]
    settings.MANAGERS = [("Admin", "admin@example.org")]

    _trigger_error(client)

    assert mailoutbox == []


# Szenario 7
@pytest.mark.django_db
def test_fehlerseite_erscheint_auch_ohne_datenbank(client, log_output):
    def database_unreachable(execute, sql, params, many, context):
        raise OperationalError("Datenbank nicht erreichbar")

    with connection.execute_wrapper(database_unreachable):
        response = client.get("/test/datenbank/")

    assert response.status_code == 500
    number = _error_number_on_page(response)
    assert f"Fehler {number} bei /test/datenbank/: django.db.utils.OperationalError" in log_output()


# Szenario 8
@pytest.mark.parametrize(
    ("address", "log_line"),
    [
        (f"/test/{NUMBER_IN_ADDRESS}/nicht-da/?suche=Erika", "Nicht gefunden: /test/<int:number>/nicht-da/"),
        (f"/test/{NUMBER_IN_ADDRESS}/verboten/?suche=Erika", "Kein Zugriff: /test/<int:number>/verboten/"),
    ],
)
def test_nicht_gefunden_und_kein_zugriff_als_kurze_zeile_ohne_nummer_und_konto(
    client, erika, log_output, address, log_line
):
    response = client.get(address)

    assert response.status_code in (403, 404)
    log = log_output()
    assert log_line in log
    assert not ERROR_NUMBER.search(log)
    _assert_nothing_personal(log)


# Szenario 9
@pytest.mark.django_db
def test_text_in_einer_unbekannten_adresse_kommt_nicht_ins_log(client, log_output):
    response = client.get("/Erika-Testfrau-Allergie/")

    assert response.status_code == 404
    log = log_output()
    assert "Nicht gefunden: unbekannte Adresse" in log
    assert "erika" not in log.lower()
    assert "allergie" not in log.lower()
