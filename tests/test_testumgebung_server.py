"""Tests zur Anleitung „Testumgebung auf dem Server“ (README.md), #59.

Die Testumgebung läuft auf dem Produktivserver des DPV unter anmeldetool.scout-tools.de, mit dem Abbild
aus der GitHub Container Registry (#302), das der Server von selbst holt. Die Seite des Servers richtet
der DPV-Admin im Repo des DPV-Servers ein; dieses Repo bringt die Anleitung für Sebastian, den Hinweis
zum Log der Datenbank und den neuen Eintrag in docs/entscheidungen.md.

Szenarien: keine (#59, Klärung vom 15.11.2026, Frage 7, bestätigt am 23.11.2026); diese Tests halten
die Akzeptanzkriterien zur Doku technisch fest. Nachgewiesen wird die Anleitung von Hand.
"""

import re
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
README = BASE_DIR / "README.md"
BETRIEB = BASE_DIR / "docs" / "betrieb.md"
ENTSCHEIDUNGEN = BASE_DIR / "docs" / "entscheidungen.md"
ENV_SERVER = BASE_DIR / "testumgebung" / ".env.example"
COMPOSE = BASE_DIR / "testumgebung" / "docker-compose.yml"
ABLAUF = BASE_DIR / ".github" / "workflows" / "abbild-veroeffentlichen.yml"

DOMAIN = "anmeldetool.scout-tools.de"


def _abschnitt(text: str, ueberschrift: str) -> str:
    """Der Abschnitt mit dieser Überschrift (## …) bis zur nächsten Überschrift derselben Ebene."""
    treffer = re.search(rf"^## {re.escape(ueberschrift)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert treffer, f"Abschnitt „{ueberschrift}“ fehlt"
    return treffer.group(1)


def _anleitung() -> str:
    return _abschnitt(README.read_text(encoding="utf-8"), "Testumgebung auf dem Server")


def test_die_anleitung_nennt_testdomain_abbild_ersten_admin_testdaten_stand_und_zurueckspielen():
    anleitung = _anleitung()
    abbild = yaml.safe_load(ABLAUF.read_text(encoding="utf-8"))["env"]["ABBILD"]

    assert f"https://{DOMAIN}/" in anleitung
    # Dasselbe Paket, das der Ablauf aus #302 veröffentlicht.
    assert abbild.replace("${{ github.repository }}", "sebivtt/dpv-participant-management") in anleitung
    assert "admin.test" in anleitung and "admin grant admin.test" in anleitung
    assert "manage.py testdata" in anleitung
    assert "Welcher Stand läuft" in anleitung
    assert "Früheren Stand wieder einspielen" in anleitung
    # Was der Admin einrichtet, steht nur als Verweis auf das Repo des DPV-Servers.
    assert "github.com/dpvonline/azure-docker" in anleitung


def test_benutzername_und_adresse_des_servers_stehen_nicht_im_repo():
    anleitung = _anleitung()

    anmeldungen = re.findall(r"^\s*ssh .*$", anleitung, re.MULTILINE)
    assert anmeldungen, "Der Schritt zum Anmelden am Server fehlt"
    for zeile in anmeldungen:
        assert "BENUTZER@SERVER" in zeile, zeile


def test_auf_dem_server_nie_den_ganzen_stapel_des_dpv_anhalten():
    """Im Ordner des DPV-Servers wirkt ein Befehl ohne Dienstnamen auf alle Dienste des DPV."""
    befehle = re.findall(r"^\s*((?:sudo \S+ )?(?:sudo )?docker compose .*)$", _anleitung(), re.MULTILINE)

    assert befehle
    for befehl in befehle:
        assert " down" not in befehl and "--volumes" not in befehl, befehl
        teile = befehl.split()
        if verb := next((teil for teil in teile if teil in ("up", "stop", "restart", "pull", "start")), None):
            dienste = [teil for teil in teile[teile.index(verb) + 1 :] if not teil.startswith("-")]
            assert dienste and all(dienst.startswith("anmeldetool") for dienst in dienste), befehl


def test_kein_verweis_mehr_auf_spaeter_in_59():
    readme = README.read_text(encoding="utf-8")

    for satz in ("Anleitung in #59", "legt #59 fest", "mit #59 nachgeprüft", "sobald die Testdomain feststeht"):
        assert satz not in readme, satz
    assert "#59" not in ENV_SERVER.read_text(encoding="utf-8")
    assert "Anleitung: #59" not in BETRIEB.read_text(encoding="utf-8")


def _log_einstellungen_der_testumgebung() -> list[str]:
    befehl = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]["datenbank"]["command"]
    return [teil for teil in befehl if "=" in teil]


def test_der_hinweis_zum_log_der_datenbank_nennt_dieselben_einstellungen_wie_die_testumgebung():
    """#324, „Technische Wahl“, Nr. 3: im gemeinsamen Postgres nur für die Datenbank des Tools (#59)."""
    hinweis = _abschnitt(BETRIEB.read_text(encoding="utf-8"), "Beim Einrichten auf dem Server (#59)")
    eingestellt = dict(re.findall(r"ALTER DATABASE anmeldetool SET (\w+) = '?([\w-]+)'?;", hinweis))

    for einstellung in _log_einstellungen_der_testumgebung():
        name, wert = einstellung.split("=")
        assert eingestellt.get(name) == wert, einstellung
    # Ein gemeinsamer Server kann lange Befehle mit ihren Werten ins Log schreiben; hier nie.
    assert eingestellt.get("log_min_duration_statement") == "-1"


def test_neuer_eintrag_in_den_entscheidungen_nennt_was_er_ersetzt():
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    eintrag = re.search(r"^## 2026-11-2\d · [^\n]*\(#59\)\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert eintrag, "Eintrag zu #59 fehlt"
    uebersicht = _abschnitt(text, "Geltende Grundsätze")
    zeilen_59 = [zeile for zeile in uebersicht.splitlines() if zeile.startswith("|") and "#59" in zeile.split("|")[2]]

    for ersetzt in ("22.10.2026, „Testumgebung im Container", "21.10.2026, „Antwort des DPV-Admins"):
        assert ersetzt in eintrag.group(1), ersetzt
        assert any(ersetzt in zeile for zeile in zeilen_59), ersetzt
    for nummer in ("Nr. 3", "Nr. 5", "„Folge daraus“", "„Hinweise der KI“"):
        assert nummer in eintrag.group(1), nummer
    # Ersetzt wird auch der Hinweis zum eigenen Netz (Akzeptanzkriterium von #59).
    assert any("eigenes Netz" in zeile for zeile in zeilen_59)
