"""Katalogtests: Tests, die den Bausteinkatalog unter /bausteine/ aufrufen (#304).

Jeder solche Test trägt das Kennzeichen ``@pytest.mark.bausteinkatalog``. Der schnelle Lauf
(``./pruefen.sh schnell``) nimmt alle so gekennzeichneten Tests immer mit, auch wenn ihre Datei
nicht genannt ist: Eine Änderung an einem gemeinsamen Baustein ändert den Katalog, und dessen
Tests stehen in vielen Dateien (docs/entscheidungen.md, 13.11.2026, #304).

Zwei Teile, geladen über ``pytest_plugins`` in tests/conftest.py und rauchtests/conftest.py:

- Auswahl: Mit ``--schnelle-auswahl=<Dateien>`` behält pytest von allem Gesammelten nur die Tests
  dieser Dateien und die gekennzeichneten. pruefen.sh gibt dazu den ganzen Ordner an; so läuft
  jeder Test genau einmal, auch wenn eine genannte Datei selbst Katalogtests enthält.
- Wache: Ruft ein Test den Katalog auf, ohne das Kennzeichen zu tragen, ist er beim Abbau rot, und
  die Meldung nennt ihn. Erkannt wird die Anfrage selbst (Signal ``request_started`` von Django),
  über den Test-Client wie über den Server des Rauchtests, gleich wie der Test die Adresse schreibt.
  Prüfen kann die Wache nur Tests, die laufen; im vollen Lauf auf GitHub sind das alle.
"""

import threading
from pathlib import Path

import pytest
from django.core.signals import request_started

MARK = "bausteinkatalog"
OPTION = "--schnelle-auswahl"
CATALOG = "/bausteine/"

# Gesetzt, sobald im laufenden Test eine Anfrage an den Katalog ging. Ein Event, weil der Server
# des Rauchtests Anfragen in eigenen Fäden bearbeitet.
_requested = threading.Event()


def catalog_requested() -> bool:
    """Ob der laufende Test den Katalog aufgerufen hat."""
    return _requested.is_set()


def _note_request(sender, environ=None, scope=None, **kwargs):
    # WSGI (Test-Client, Server des Rauchtests) meldet environ, ASGI meldet scope.
    path = (environ or {}).get("PATH_INFO") or (scope or {}).get("path") or ""
    if path.startswith(CATALOG):
        _requested.set()


# Einmal je Prozess; dispatch_uid verhindert eine doppelte Verbindung.
request_started.connect(_note_request, weak=False, dispatch_uid="tests.katalogtests")


def pytest_addoption(parser):
    parser.addoption(
        OPTION,
        default=None,
        metavar="DATEIEN",
        help="Schneller Lauf (pruefen.sh): nur die Tests dieser Dateien (durch Leerzeichen getrennt) und alle Katalogtests.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", f"{MARK}: Test ruft den Bausteinkatalog auf; läuft im schnellen Lauf immer mit (#304)")


def pytest_collection_modifyitems(config, items):
    files = config.getoption(OPTION)
    if files is None:
        return
    base = Path(config.invocation_params.dir)
    named = {(base / name).resolve() for name in files.split()}
    keep, dropped = [], []
    for item in items:
        selected = item.path.resolve() in named or item.get_closest_marker(MARK) is not None
        (keep if selected else dropped).append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = keep


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    _requested.clear()


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item, nextitem):
    # trylast: nach dem Abbau der Fixtures, damit auch deren Anfragen zählen.
    requested = _requested.is_set()
    _requested.clear()
    if requested and item.get_closest_marker(MARK) is None:
        pytest.fail(
            f"{item.nodeid} ruft den Bausteinkatalog ({CATALOG}) auf, trägt aber nicht das Kennzeichen "
            f"@pytest.mark.{MARK}. Ohne Kennzeichen läuft er im schnellen Lauf nicht immer mit "
            "(tests/katalogtests.py, #304).",
            pytrace=False,
        )
