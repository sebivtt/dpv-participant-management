"""Fängt die tatsächliche Ausgabe des Logs ab, für Tests ohne Personendaten im Log (#6, #5, #25)."""

import io
import logging

import pytest


def _is_from_pytest(handler: logging.Handler) -> bool:
    """Erkennt die Aufzeichnungen, die pytest selbst an Logger hängt; die gehören nicht zum Tool."""
    return type(handler).__module__.startswith("_pytest")


def _all_loggers() -> list[logging.Logger]:
    return [
        logging.getLogger(),
        *(logger for logger in logging.Logger.manager.loggerDict.values() if isinstance(logger, logging.Logger)),
    ]


@pytest.fixture
def log_output(capsys):
    """Fängt alles ab, was die eingestellten Log-Ausgaben schreiben, und gibt es als Text zurück.

    Die Ausgaben des Tools werden beim Start eingerichtet und schreiben dann an ihr festes Ziel.
    Deshalb wird ihr Ziel für die Dauer des Tests umgelenkt. Was ohne eingerichtete Ausgabe
    trotzdem erscheint (Pythons Notausgabe), fängt capsys ab.

    Seit pytest 9.1.0 hängt pytest seine Aufzeichnungen auch an Logger, die nichts
    weitergeben. Dann hat jeder Logger während der Tests eine Ausgabe, und die Notausgabe
    springt nie an; genau deshalb blieb #25 unbemerkt. Für die Dauer des Tests werden diese
    Aufzeichnungen deshalb von allen Loggern außer dem obersten abgehängt, damit der Test
    sieht, was im Betrieb erscheint.
    """
    buffer = io.StringIO()
    loggers = _all_loggers()
    handlers = {
        handler
        for logger in loggers
        for handler in logger.handlers
        if isinstance(handler, logging.StreamHandler) and not _is_from_pytest(handler)
    }
    previous = {handler: handler.setStream(buffer) for handler in handlers}
    detached = [
        (logger, handler)
        for logger in loggers
        if logger is not logging.getLogger()
        for handler in logger.handlers
        if _is_from_pytest(handler)
    ]
    for logger, handler in detached:
        logger.removeHandler(handler)

    def read() -> str:
        captured = capsys.readouterr()
        return buffer.getvalue() + captured.out + captured.err

    yield read
    for logger, handler in detached:
        logger.addHandler(handler)
    for handler, stream in previous.items():
        handler.setStream(stream)
