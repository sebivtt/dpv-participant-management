"""Fängt die tatsächliche Ausgabe des Logs ab, für Tests ohne Personendaten im Log (#6, #5)."""

import io
import logging

import pytest


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
