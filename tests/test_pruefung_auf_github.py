"""Tests für den Ablauf der Prüfung auf GitHub (.github/workflows/ci.yml), Issue #133.

Das Installieren der Test-Browser hing mehrmals, weil der Ubuntu-Paketserver langsam war; der
ganze Lauf brach dann nach 35 Minuten ab, ohne dass ein Test gelaufen war. Entschieden ist
(#133, 23.10.2026): abfangen. Der Schritt bekommt ein eigenes Zeitlimit von 10 Minuten,
höchstens drei Versuche, die Browser kommen aus dem Zwischenspeicher von GitHub, und scheitern
alle Versuche, ist der Lauf rot mit klarer Meldung. Diese Tests sorgen dafür, dass das nicht
still aus ci.yml verschwindet. Ob GitHub es tatsächlich so ausführt, zeigt erst ein Lauf dort.
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
    return [step for step in _steps() if step.get("name", "").startswith(INSTALL_NAME)]


def _index(step: dict) -> int:
    return _steps().index(step)


def _condition(step: dict) -> str:
    return " ".join(str(step.get("if", "")).split())


def test_browser_installation_hat_hoechstens_drei_versuche():
    attempts = _install_steps()

    assert len(attempts) == 3
    for attempt in attempts:
        assert INSTALL_COMMAND in attempt["run"]


def test_jeder_versuch_hat_ein_eigenes_zeitlimit_von_zehn_minuten():
    for attempt in _install_steps():
        assert attempt["timeout-minutes"] == 10, attempt["name"]


def test_ein_gescheiterter_versuch_bricht_den_lauf_nicht_sofort_ab():
    for attempt in _install_steps():
        assert attempt["continue-on-error"] is True, attempt["name"]


def test_weiterer_versuch_nur_wenn_der_vorige_gescheitert_ist():
    first, second, third = _install_steps()

    assert "if" not in first
    assert _condition(second) == f"steps.{first['id']}.outcome == 'failure'"
    assert _condition(third) == f"steps.{second['id']}.outcome == 'failure'"


def test_scheitern_alle_versuche_ist_der_lauf_rot_mit_klarer_meldung():
    third = _install_steps()[-1]
    final = [step for step in _steps() if _condition(step) == f"steps.{third['id']}.outcome == 'failure'"]

    assert len(final) == 1
    step = final[0]
    assert "continue-on-error" not in step
    assert "::error" in step["run"]
    assert "Browser-Installation" in step["run"]
    assert "Neustart" in step["run"]
    assert step["run"].strip().endswith("exit 1")
    # Die Meldung kommt, bevor ein Test laufen könnte.
    tests = next(step for step in _steps() if step.get("run", "").strip() == "./pruefen.sh")
    assert _index(third) < _index(step) < _index(tests)


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
    assert _index(sync) < _index(version_step) < _index(cache) < _index(_install_steps()[0])


def test_der_ganze_lauf_behaelt_sein_zeitlimit_von_35_minuten():
    assert _job()["timeout-minutes"] == 35
