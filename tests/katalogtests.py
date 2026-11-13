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
- Ausnahme: Tests, die der Reihe nach jede Adresse des Tools aufrufen (etwa zu Rechten oder
  „nicht gefunden“), treffen dabei auch den Katalog. Sie tragen statt des Katalog-Kennzeichens
  ``@pytest.mark.alle_adressen``; die Wache lässt sie gelten, und der schnelle Lauf nimmt sie nicht
  immer mit, weil sie zusammen Minuten dauern (Nachklärung zu #304 vom 13.11.2026).
"""

import threading
from pathlib import Path

import pytest
from django.core.signals import request_started

MARK = "bausteinkatalog"
ALL_ADDRESSES = "alle_adressen"
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
    config.addinivalue_line(
        "markers",
        f"{ALL_ADDRESSES}: Test ruft der Reihe nach jede Adresse auf, auch den Katalog; läuft nicht immer mit (#304)",
    )


def pytest_collection_modifyitems(config, items):
    files = config.getoption(OPTION)
    if files is None:
        return
    base = Path(config.invocation_params.dir)
    named = {(base / name).resolve(): name for name in files.split()}
    # Eine genannte Datei ohne gesammelte Tests (etwa eine Hilfsdatei) fiele sonst still weg; bevor
    # pytest den Ordner sammelte, war der Lauf dann rot (Befund G2 der unabhängigen Prüfung zu #304).
    collected = {item.path.resolve() for item in items}
    without_tests = sorted(name for path, name in named.items() if path not in collected)
    if without_tests:
        config.hook.pytest_deselected(items=list(items))
        items[:] = []  # pytest meldet die Sammlung auch nach dem Abbruch; dann ohne Tests
        pytest.exit(
            f"Ohne Tests: {' '.join(without_tests)} (genannt hinter „schnell“, pytest sammelt dort keine Tests).",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )
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
    if requested and item.get_closest_marker(MARK) is None and item.get_closest_marker(ALL_ADDRESSES) is None:
        pytest.fail(
            f"{item.nodeid} ruft den Bausteinkatalog ({CATALOG}) auf, trägt aber nicht das Kennzeichen "
            f"@pytest.mark.{MARK}. Ohne Kennzeichen läuft er im schnellen Lauf nicht immer mit "
            f"(tests/katalogtests.py, #304). Ruft er der Reihe nach jede Adresse auf, gehört stattdessen "
            f"@pytest.mark.{ALL_ADDRESSES} daran.",
            pytrace=False,
        )
