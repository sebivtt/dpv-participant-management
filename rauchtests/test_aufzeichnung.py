"""Belege bei Rot (#349): Aufzeichnung des Browsers für jeden roten Rauchtest auf GitHub.

Auf GitHub setzt der Prüfablauf RAUCHTEST_SPUREN (.github/workflows/ci.yml); dann zeichnet jeder
Browser-Kontext auf (Playwright-Trace), und nach dem Test bleibt die Aufzeichnung nur liegen, wenn er
rot war. Ohne RAUCHTEST_SPUREN, also lokal, zeichnet nichts auf. Ob ci.yml die Aufzeichnungen und das
Protokoll von Keycloak zum Herunterladen hochlädt, prüft tests/test_pruefung_auf_github.py.
Alle Konten und Daten sind erfunden.
"""

import zipfile

import pytest

from rauchtests.conftest import BASE, keep_traces

pytestmark = pytest.mark.django_db(transaction=True)


def _visit(browser, close: bool):
    context = browser.new_context()
    context.new_page().goto(f"{BASE}/")
    if close:
        context.close()
    return context


def test_bei_rot_bleibt_die_aufzeichnung_liegen_bei_gruen_nicht(browser, tool, tmp_path, monkeypatch):
    monkeypatch.setenv("RAUCHTEST_SPUREN", str(tmp_path))

    _visit(browser, close=True)
    assert keep_traces("gruen", failed=False) == []

    _visit(browser, close=True)
    # Ein Kontext, den der Test nicht selbst geschlossen hat, zählt ebenso.
    still_open = _visit(browser, close=False)
    kept = keep_traces("rot", failed=True)
    still_open.close()

    assert sorted(path.name for path in kept) == ["rot-1.zip", "rot-2.zip"]
    assert sorted(path.name for path in tmp_path.iterdir()) == ["rot-1.zip", "rot-2.zip"]
    for path in kept:
        with zipfile.ZipFile(path) as trace:
            recorded = b"".join(trace.read(name) for name in trace.namelist() if name.endswith(".trace"))
        assert f"{BASE}/".encode() in recorded


def test_ohne_ablageort_zeichnet_nichts_auf(browser, tool, tmp_path, monkeypatch):
    monkeypatch.delenv("RAUCHTEST_SPUREN", raising=False)

    _visit(browser, close=True)

    assert keep_traces("rot", failed=True) == []
    assert list(tmp_path.iterdir()) == []
