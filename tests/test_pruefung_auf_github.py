"""Tests für den Ablauf der Prüfung auf GitHub (.github/workflows/ci.yml), Issues #133, #256 und #276.

Das Installieren der Test-Browser hängt manchmal, weil der Ubuntu-Paketserver auf dem
betroffenen Rechner immer langsamer liefert. Entschieden ist (#133, 23.10.2026): abfangen.
Die Browser kommen aus dem Zwischenspeicher von GitHub, und scheitert die Installation, ist
der Lauf rot mit klarer Meldung.

Issue #276 (06.11.2026): Ein zweiter Versuch im selben Lauf half 3 von 7 Mal, ein dritter nie, ein
kompletter Neustart fast immer. Deshalb gibt es nur noch einen Versuch mit 5 Minuten; danach
ist der Lauf rot, und ein Neustart bekommt einen neuen Rechner. Der Schritt „Alle Prüfungen“
behält seine 45 Minuten (#256), der ganze Lauf hat 55; die Summe wird hier nachgerechnet.

Diese Tests sorgen dafür, dass das nicht still aus ci.yml verschwindet. Ob GitHub es
tatsächlich so ausführt, zeigt erst ein Lauf dort.
"""

import re
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CI = BASE_DIR / ".github" / "workflows" / "ci.yml"
INSTALL_NAME = "Browser für den Rauchtest installieren"
INSTALL_COMMAND = "uv run --locked playwright install --with-deps chromium firefox webkit"


def _job() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))["jobs"]["pruefen"]


def _steps() -> list[dict]:
    return _job()["steps"]


def _install_steps() -> list[dict]:
    return [step for step in _steps() if INSTALL_COMMAND in step.get("run", "")]


def _install() -> dict:
    steps = _install_steps()
    assert len(steps) == 1, [step.get("name") for step in steps]
    return steps[0]


def _tests() -> dict:
    tests = [step for step in _steps() if step.get("run", "").strip() == "./pruefen.sh"]
    assert len(tests) == 1
    return tests[0]


def _index(step: dict) -> int:
    return _steps().index(step)


def _condition(step: dict) -> str:
    return " ".join(str(step.get("if", "")).split())


def test_browser_werden_in_genau_einem_schritt_ohne_weitere_versuche_installiert():
    install = _install()

    assert install["name"] == INSTALL_NAME
    # Auch keine Wiederholung innerhalb des Schritts und kein zweiter Aufruf an anderer Stelle.
    assert install["run"].strip() == INSTALL_COMMAND
    assert "uses" not in install
    assert [step for step in _steps() if "playwright install" in step.get("run", "")] == [install]
    assert "if" not in install
    assert [step["name"] for step in _steps() if step.get("name", "").startswith(INSTALL_NAME)] == [INSTALL_NAME]


def test_die_installation_hat_ein_zeitlimit_von_fuenf_minuten():
    assert _install()["timeout-minutes"] == 5


def test_scheitert_die_installation_ist_der_lauf_rot_mit_klarer_meldung():
    install = _install()
    # Die Installation darf nicht selbst den Lauf beenden, sonst käme die Meldung nicht;
    # das übernimmt der nächste Schritt.
    assert install["continue-on-error"] is True
    final = [step for step in _steps() if _condition(step) == f"steps.{install['id']}.outcome == 'failure'"]

    assert len(final) == 1
    step = final[0]
    assert "continue-on-error" not in step
    assert "::error" in step["run"]
    assert "Browser-Installation" in step["run"]
    assert "Kein Test ist gelaufen" in step["run"]
    assert "Neustart" in step["run"]
    assert step["run"].strip().endswith("exit 1")
    # Die Meldung kommt direkt nach der Installation, bevor ein Test laufen könnte.
    assert _index(install) + 1 == _index(step) < _index(_tests())


def test_browser_kommen_aus_dem_zwischenspeicher_passend_zur_playwright_fassung():
    caches = [step for step in _steps() if str(step.get("uses", "")).startswith("actions/cache@")]

    assert len(caches) == 1
    cache = caches[0]
    # Wie die anderen fremden Bausteine auf eine feste Fassung (Commit) festgelegt.
    assert re.fullmatch(r"actions/cache@[0-9a-f]{40}", cache["uses"])
    assert cache["with"]["path"] == "~/.cache/ms-playwright"
    # Der Schlüssel enthält die Playwright-Fassung, die uv aus uv.lock installiert hat.
    version_step = next(step for step in _steps() if "playwright" in str(step.get("id", "")) and "run" in step)
    assert "--locked" in version_step["run"]
    assert "version('playwright')" in version_step["run"]
    assert f"steps.{version_step['id']}.outputs.version" in cache["with"]["key"]
    sync = next(step for step in _steps() if step.get("run") == "uv sync --locked")
    assert _index(sync) < _index(version_step) < _index(cache) < _index(_install())


# Fester Rest im Lauf außer Installation und Prüfungen (#276): Vorlauf bis zur Installation bis
# gut 1 Minute (Container, Keycloak starten, Zwischenspeicher; Lauf 41899114419: 41 Sekunden),
# Warten auf Keycloak höchstens 3 Minuten (90 Versuche à 2 Sekunden), Aufräumen wenige
# Sekunden. Hängt die Installation, endet der Lauf nach ihren 5 Minuten rot, ohne dass
# Prüfungen laufen; die Summe muss also nur für eine erfolgreiche Installation und die
# Prüfungen reichen. Bisher brauchten die Prüfungen höchstens knapp 34 Minuten.
REST_MINUTEN = 5


def test_der_schritt_alle_pruefungen_hat_ein_eigenes_zeitlimit_von_45_minuten():
    assert _tests()["timeout-minutes"] == 45


def test_der_ganze_lauf_hat_ein_zeitlimit_von_55_minuten():
    assert _job()["timeout-minutes"] == 55


def test_installation_pruefungen_und_rest_passen_ins_zeitlimit_des_laufs():
    summe = _install()["timeout-minutes"] + _tests()["timeout-minutes"] + REST_MINUTEN

    assert summe <= _job()["timeout-minutes"]
