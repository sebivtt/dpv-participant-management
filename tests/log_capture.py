"""Fängt die tatsächliche Ausgabe des Logs ab, für Tests ohne Personendaten im Log (#6, #5, #25)."""

import io
import logging

import pytest


@pytest.fixture
def log_output(capsys):
    """Fängt alles ab, was die eingestellten Log-Ausgaben schreiben, und gibt es als Text zurück.

    Die Ausgaben des Tools werden beim Start eingerichtet und schreiben dann an ihr festes Ziel.
    Deshalb wird ihr Ziel für die Dauer des Tests umgelenkt. Die Aufzeichnung von pytest
    selbst bleibt außen vor; sie gibt es im Betrieb nicht.

    Pythons Notausgabe sieht dieses Werkzeug nicht: Seit pytest 9.1.0 hängt pytest bei jedem
    Testschritt eigene Aufzeichnungen an alle Logger, die nichts weitergeben, und dann springt
    die Notausgabe nie an. Deshalb blieb #25 unbemerkt. Die Notausgabe prüft ein eigener
    Prozess ohne pytest (tests/anfragen_ohne_pytest.py).
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
