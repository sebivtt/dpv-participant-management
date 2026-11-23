"""Tests zum Nachweis des Logins auf dem Server über den Test-Realm des DPV (README.md), #63.

Die Testumgebung auf dem Server (#59) meldet sich am Test-Realm `dpv-test` im Keycloak des DPV an.
Nachgewiesen wird das von Hand: Sebastian geht die Checkliste im README einmal durch und trägt das
Ergebnis in #106 ein.

Szenarien: keine (#63, Klärung vom 15.11.2026, Frage 7, bestätigt am 23.11.2026); diese Tests halten
die Akzeptanzkriterien zur Doku technisch fest. Dass die Importdatei den Anzeigenamen hat, prüft
tests/test_testrealm_datei.py, dass Keycloak ihn zeigt, tests/test_testrealm_echt.py.
"""

import re

from tests.test_testumgebung_server import ENTSCHEIDUNGEN, README, _abschnitt


def _anleitung() -> str:
    return _abschnitt(README.read_text(encoding="utf-8"), "Testumgebung auf dem Server")


def _checkliste() -> str:
    """Der Teil „Nachweis: Login über den Test-Realm“ bis zur nächsten fetten Zwischenüberschrift."""
    treffer = re.search(r"^\*\*Nachweis: Login über den Test-Realm\*\*[^\n]*\n(.*?)(?=^\*\*|\Z)", _anleitung(), re.MULTILINE | re.DOTALL)
    assert treffer, "Die Checkliste „Nachweis: Login über den Test-Realm“ fehlt in „Testumgebung auf dem Server“"
    return treffer.group(1)


def test_die_checkliste_nennt_jeden_punkt_aus_dem_issue():
    checkliste = _checkliste()

    # Anmelden, abmelden, erneut anmelden mit Passwort.
    assert "erika.testfrau" in checkliste and "„Hallo Erika!“" in checkliste
    assert "„Abmelden“" in checkliste
    assert "Passwort" in checkliste and "verlangt" in checkliste
    # Konto ohne Namen.
    assert "ohne.name" in checkliste and "„Hallo!“" in checkliste
    # Kontosuche beim Benennen über die genaue Mail (#251).
    assert "benennen" in checkliste and "@example.org" in checkliste and "#251" in checkliste
    # Keycloak-Fassung mit Datum in #38; Ergebnis mit Datum und Stand von main in #106.
    assert "Fassung" in checkliste and "#38" in checkliste
    assert "#106" in checkliste and "`main`" in checkliste


def test_die_checkliste_laeuft_ohne_ki_und_nennt_die_anzeige_von_keycloak():
    checkliste = _checkliste()

    assert "ohne KI" in checkliste
    # Die Login-Seite des Test-Realms, mit dem Link „Registrieren“ auf der Seite des Tools (#63).
    assert "„Anmeldetool Test“" in checkliste
    assert "„Noch kein Konto? Registrieren“" in checkliste
    # Der Link führt im Test-Realm zur Fehlerseite von Keycloak, nicht zur Login-Seite (#63, Antwort
    # Sebastian vom 23.11.2026: „A) Link bleibt (Empfohlen)“).
    assert "„Registrierung nicht erlaubt.“" in checkliste


def test_nur_mit_erfundenen_testkonten_nie_mit_dem_verwaltungskonto():
    checkliste = _checkliste()

    assert "nur mit den erfundenen Testkonten" in checkliste
    assert "Verwaltungskonto" in checkliste


def test_neuer_eintrag_in_den_entscheidungen_nennt_was_er_ersetzt():
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    eintrag = re.search(r"^## 2026-11-2\d · [^\n]*\(#63\)\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert eintrag, "Eintrag zu #63 fehlt"
    uebersicht = _abschnitt(text, "Geltende Grundsätze")
    zeilen_63 = [zeile for zeile in uebersicht.splitlines() if zeile.startswith("|") and "#63" in zeile.split("|")[2]]

    ersetzt = "22.10.2026, „Test-Realm im Keycloak des DPV"
    assert ersetzt in eintrag.group(1)
    assert "„Anmeldetool Test“" in eintrag.group(1)
    for nummer in ("Nr. 5", "Nr. 7"):
        assert any(ersetzt in zeile and nummer in zeile for zeile in zeilen_63), nummer
