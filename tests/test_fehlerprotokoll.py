"""Tests für das Fehlerprotokoll ohne Personendaten (#6, DSG-08).

Geprüft wird die tatsächliche Ausgabe der eingestellten Log-Ausgaben, nicht nur, was an
Django übergeben wird. Alle Daten sind erfunden.
"""

import logging
import os
import re
import subprocess
import sys

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.db import OperationalError, connection
from django.test import Client

pytestmark = pytest.mark.urls("tests.urls")

# Seit #5 hat das Tool ein eigenes Kontenmodell; Djangos Standardmodell gibt es nicht mehr.
User = get_user_model()

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


# #75: Auch die Log-Zeile selbst zeigt von einem Fehler nur die Art, nicht nur der Ablauf darunter.
# Szenarien 1 bis 3 und 9 aus dem Issue; erfundene Mail im Meldungstext.
@pytest.mark.parametrize("logger_name", ["core", "allauth"])
def test_fehler_als_logzeile_oder_platzhalter_zeigt_nur_die_art(log_output, logger_name):
    log_target = logging.getLogger(logger_name)
    try:
        raise ValueError("erika.testfrau@example.org")
    except ValueError as error:
        log_target.exception(error)
        log_target.error("Fehler: %s", error)
        log_target.error("Fehler: %(fehler)s", {"fehler": error})

    log = log_output()
    assert "erika" not in log
    assert f"{logger_name} ValueError\n" in log
    assert log.count("Fehler: ValueError") == 2


# Szenario 4 aus #75
def test_normale_logzeile_mit_platzhalter_bleibt_unveraendert(log_output):
    logging.getLogger("core").warning("Nicht gefunden: %s", "/profil/")

    assert "core Nicht gefunden: /profil/\n" in log_output()


# Szenario 10 aus #75
def test_fehler_aus_fremdem_paket_steht_mit_vollem_namen_in_der_logzeile(log_output):
    logging.getLogger("allauth").error("Datenbank: %s", OperationalError("erika@example.org"))

    log = log_output()
    assert "Datenbank: django.db.utils.OperationalError" in log
    assert "erika" not in log


def test_andere_ausgaben_bekommen_den_logeintrag_unveraendert(log_output):
    # Der Schutz arbeitet auf einer Kopie; der Eintrag selbst bleibt, wie er ist.
    entries = []

    class Collect(logging.Handler):
        def emit(self, record):
            entries.append(record)

    collector = Collect()
    log_target = logging.getLogger("core")
    log_target.addHandler(collector)
    try:
        error = ValueError("erika@example.org")
        log_target.error("Fehler: %s", error)
    finally:
        log_target.removeHandler(collector)

    assert "erika" not in log_output()
    assert entries[0].args == (error,)


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


# Befunde der unabhängigen Prüfung
@pytest.mark.django_db
def test_kein_zugriff_wegen_fehlendem_formularschutz_ohne_echte_adresse(log_output):
    # Djangos Schutz gegen untergeschobene Formulare (CSRF) lehnt in einem Baustein vor der
    # Seite ab. Auch dann steht nur die kurze Zeile mit dem Muster im Log.
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(User.objects.create(id=ACCOUNT_NUMBER, username="erika.testfrau"))

    response = browser.post(f"/test/{NUMBER_IN_ADDRESS}/verboten/?suche=Erika", {"allergie": "Testallergie Erdnuss"})

    assert response.status_code == 403
    log = log_output()
    assert "Kein Zugriff: /test/<int:number>/verboten/" in log
    _assert_nothing_personal(log)


@pytest.mark.django_db
def test_verdaechtige_anfrage_schreibt_keinen_frei_gewaehlten_text_ins_log(client, log_output):
    # Den Namen des Servers (Host) bestimmt, wer die Anfrage schickt.
    response = client.get("/", HTTP_HOST="erika-testfrau-allergie.example")

    assert response.status_code == 400
    log = log_output()
    assert "Ungültige Anfrage: /" in log
    assert "erika" not in log.lower()
    assert "allergie" not in log.lower()


def test_fehler_im_fehlerprotokoll_verhindert_die_fehlerseite_nicht(client, erika, log_output, monkeypatch):
    def broken(request):
        raise RuntimeError("Testfehler im Fehlerprotokoll")

    monkeypatch.setattr("core.errors.address_pattern", broken)

    response = _trigger_error(client)

    assert response.status_code == 500
    number = _error_number_on_page(response)
    log = log_output()
    assert f"Fehler {number}" in log
    _assert_nothing_personal(log)


# #25: Djangos eigene Zeilen kamen über Pythons Notausgabe doch ins Log. In pytest selbst ist
# das nicht zu sehen: Seit pytest 9.1.0 hängt pytest bei jedem Testschritt eigene Aufzeichnungen
# an alle Logger, die nichts weitergeben, und verdeckt so die Notausgabe. Deshalb laufen die
# Anfragen hier in einem eigenen Python-Prozess ohne pytest, wie im Betrieb.
def test_djangos_eigene_zeilen_erscheinen_auch_nicht_ueber_die_notausgabe():
    command = [sys.executable, "-m", "tests.anfragen_ohne_pytest"]
    result = subprocess.run(  # noqa: S603 -- fester Befehl mit dem eigenen Python, keine Eingaben von außen
        command,
        cwd=django_settings.BASE_DIR,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path), "DJANGO_SETTINGS_MODULE": "config.settings"},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    log = result.stderr

    # Die vier Anfragen wurden wirklich abgelehnt, und die eigenen kurzen Zeilen stehen im Log.
    assert result.returncode == 0, log
    assert result.stdout.split() == ["404", "400", "403", "500"]
    assert "Nicht gefunden: unbekannte Adresse" in log
    assert "Ungültige Anfrage: /" in log
    assert "Kein Zugriff: /test/<int:number>/verboten/" in log
    assert ERROR_NUMBER.search(log), log
    # Djangos eigene Zeilen fehlen, auch über die Notausgabe.
    for django_text in ["Not Found", "Invalid HTTP_HOST", "Forbidden", "Internal Server Error"]:
        assert django_text not in log, f"Djangos eigene Zeile steht im Log:\n{log}"
    assert "allergie" not in log.lower()
    _assert_nothing_personal(log)


def test_pythons_notausgabe_bleibt_an():
    # Unvorhergesehene Fehler aus falsch eingestellten Loggern sollen nicht still verschwinden.
    assert logging.lastResort is not None


def test_jeder_logger_ohne_weitergabe_hat_eine_ausgabe(settings):
    # Wache: Ein Logger ohne Ausgabe, der nichts weitergibt, landet in Pythons Notausgabe.
    # Gilt für die Einstellungen und für Logger aus Paketen. Die Aufzeichnungen von pytest
    # zählen nicht, weil es sie im Betrieb nicht gibt.
    in_settings = [
        name
        for name, config in settings.LOGGING.get("loggers", {}).items()
        if config.get("propagate", True) is False and not config.get("handlers")
    ]
    live = [
        name
        for name, logger in logging.Logger.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
        and not logger.propagate
        and not [handler for handler in logger.handlers if not type(handler).__module__.startswith("_pytest")]
    ]
    assert in_settings == [], f"Ohne Ausgabe in den Einstellungen: {in_settings}"
    assert live == [], f"Ohne Ausgabe beim Start: {sorted(live)}"
