"""Tests für den Ablauf der Prüfung auf GitHub (.github/workflows/ci.yml), Issues #133, #256, #276 und #307.

Das Installieren der Test-Browser hängt manchmal, weil der Ubuntu-Paketserver auf dem
betroffenen Rechner immer langsamer liefert. Entschieden ist (#133, 23.10.2026): abfangen.
Die Browser kommen aus dem Zwischenspeicher von GitHub, und scheitert die Installation, ist
der Lauf rot mit klarer Meldung.

Issue #276 (06.11.2026): Ein zweiter Versuch im selben Lauf half 3 von 7 Mal, ein dritter nie, ein
kompletter Neustart fast immer. Deshalb gibt es nur noch einen Versuch mit 5 Minuten; danach
ist der Lauf rot, und ein Neustart bekommt einen neuen Rechner. Der Schritt „Alle Prüfungen“
behielt damals seine 45 Minuten (#256), der ganze Lauf hatte 55.

Issue #307 (13.11.2026): Die Prüfungen laufen in sechs Teilen gleichzeitig auf eigenen Rechnern
(`./pruefen.sh teil <name>`); nur die drei Teile mit Rauchtest installieren einen Browser, je
ihren eigenen. Jeder Teil läuft zu Ende, auch wenn ein anderer rot ist. Die Gesamtprüfung „Alle
Prüfungen (pruefen.sh)“ ist nur grün, wenn alle Teile grün sind. Die Zeitlimits gelten je Teil;
die Summe wird hier nachgerechnet.

Diese Tests sorgen dafür, dass das nicht still aus ci.yml verschwindet. Ob GitHub es
tatsächlich so ausführt, zeigt erst ein Lauf dort.
"""

import re
import subprocess
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CI = BASE_DIR / ".github" / "workflows" / "ci.yml"
INSTALL_NAME = "Browser für den Rauchtest installieren"
INSTALL_COMMAND = "uv run --locked playwright install --with-deps ${{ matrix.browser }}"
TEIL_COMMAND = "./pruefen.sh teil ${{ matrix.teil }}"
BROWSER_CONDITION = "matrix.browser"


def _workflow() -> dict:
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def _job() -> dict:
    return _workflow()["jobs"]["pruefen"]


def _gesamt() -> dict:
    return _workflow()["jobs"]["gesamt"]


def _steps() -> list[dict]:
    return _job()["steps"]


def _install_steps() -> list[dict]:
    return [step for step in _steps() if "playwright install" in step.get("run", "")]


def _install() -> dict:
    steps = _install_steps()
    assert len(steps) == 1, [step.get("name") for step in steps]
    return steps[0]


def _tests() -> dict:
    tests = [step for step in _steps() if "./pruefen.sh" in step.get("run", "")]
    assert len(tests) == 1
    return tests[0]


def _teile_aus_dem_skript() -> list[str]:
    done = subprocess.run(  # noqa: S603 -- festes Skript dieses Repos, nur die Liste der Teile
        ["/bin/sh", str(BASE_DIR / "pruefen.sh"), "teile"], capture_output=True, text=True, timeout=30, check=False
    )
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout.split()


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
    # Einzige Bedingung: Der Teil hat einen Browser (#307); sonst gibt es nichts zu installieren.
    assert _condition(install) == BROWSER_CONDITION
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
    # Neu gestartet werden nur die gescheiterten Teile (#307).
    assert "Re-run failed jobs" in step["run"]
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
    # Je Browser ein eigener Eintrag, weil jeder Teil nur seinen Browser installiert (#307).
    assert "${{ matrix.browser }}" in cache["with"]["key"]
    assert _condition(cache) == _condition(version_step) == BROWSER_CONDITION
    sync = next(step for step in _steps() if step.get("run") == "uv sync --locked")
    assert _index(sync) < _index(version_step) < _index(cache) < _index(_install())


# Fester Rest je Teil außer Installation und Prüfungen (#276): Vorlauf bis zur Installation bis
# gut 1 Minute (Container, Keycloak starten, Zwischenspeicher; Lauf 41899114419: 41 Sekunden),
# Warten auf Keycloak höchstens 3 Minuten (90 Versuche à 2 Sekunden), Aufräumen und Hochladen des
# Ergebnisses wenige Sekunden. Hängt die Installation, endet der Teil nach ihren 5 Minuten rot,
# ohne dass Prüfungen laufen; die Summe muss also nur für eine erfolgreiche Installation und die
# Prüfungen reichen. Vor #307 brauchten alle Prüfungen nacheinander höchstens knapp 34 Minuten,
# davon der Rauchtest in allen drei Browsern rund 19 und die übrigen Tests rund 9.
REST_MINUTEN = 5


def test_der_schritt_mit_den_pruefungen_eines_teils_hat_ein_eigenes_zeitlimit_von_25_minuten():
    assert _tests()["timeout-minutes"] == 25


def test_jeder_teil_hat_ein_zeitlimit_von_35_minuten():
    assert _job()["timeout-minutes"] == 35


def test_installation_pruefungen_und_rest_passen_ins_zeitlimit_eines_teils():
    summe = _install()["timeout-minutes"] + _tests()["timeout-minutes"] + REST_MINUTEN

    assert summe <= _job()["timeout-minutes"]


# --- Teile gleichzeitig auf eigenen Rechnern (#307) ---------------------------------------------


def test_die_teile_auf_github_sind_genau_die_teile_aus_pruefen_sh():
    matrix = _job()["strategy"]["matrix"]

    assert set(matrix) == {"include"}, "nur die Liste der Teile, keine weiteren Kombinationen"
    assert [eintrag["teil"] for eintrag in matrix["include"]] == _teile_aus_dem_skript()


def test_nur_die_teile_mit_rauchtest_haben_einen_browser_und_zwar_ihren_eigenen():
    for eintrag in _job()["strategy"]["matrix"]["include"]:
        teil = eintrag["teil"]
        if teil.startswith("rauchtest-"):
            assert eintrag == {"teil": teil, "browser": teil.removeprefix("rauchtest-")}
        else:
            assert eintrag == {"teil": teil}


def test_jeder_teil_laeuft_zu_ende_auch_wenn_ein_anderer_rot_ist():
    strategy = _job()["strategy"]

    assert strategy["fail-fast"] is False
    assert "max-parallel" not in strategy
    assert "continue-on-error" not in _job()


def test_jeder_teil_ruft_pruefen_sh_mit_seinem_namen_auf():
    tests = _tests()

    assert tests["run"].strip() == TEIL_COMMAND
    assert "if" not in tests
    assert "continue-on-error" not in tests
    assert "matrix.teil" in _job()["name"]


def test_jeder_teil_laedt_sein_ergebnis_hoch_auch_wenn_er_rot_ist():
    tests = _tests()
    ergebnis = tests["env"]["PRUEFTEIL_ERGEBNIS"]
    uploads = [step for step in _steps() if str(step.get("uses", "")).startswith("actions/upload-artifact@")]

    assert len(uploads) == 1
    upload = uploads[0]
    assert re.fullmatch(r"actions/upload-artifact@[0-9a-f]{40}", upload["uses"])
    assert _condition(upload) == "always()"
    assert upload["with"]["path"] == ergebnis
    assert "${{ matrix.teil }}" in ergebnis and "${{ runner.temp }}" in ergebnis
    assert upload["with"]["name"] == "ergebnis-${{ matrix.teil }}"
    # Beim Neustart gescheiterter Teile ersetzt das neue Ergebnis das alte.
    assert upload["with"]["overwrite"] is True
    assert _index(tests) < _index(upload)


def test_die_gesamtpruefung_wartet_auf_alle_teile_und_laeuft_immer():
    gesamt = _gesamt()

    assert gesamt["name"] == "Alle Prüfungen (pruefen.sh)"
    assert gesamt["needs"] == "pruefen"
    assert _condition(gesamt) == "always()"
    assert set(_workflow()["jobs"]) == {"pruefen", "gesamt"}


def test_die_gesamtpruefung_fasst_die_ergebnisse_aller_teile_mit_pruefen_sh_zusammen():
    steps = _gesamt()["steps"]
    downloads = [step for step in steps if "gh run download" in step.get("run", "")]
    gesamt = [step for step in steps if "./pruefen.sh gesamt" in step.get("run", "")]

    assert len(downloads) == 1 and len(gesamt) == 1
    download, zusammenfassen = downloads[0], gesamt[0]
    # Über die Schnittstelle von GitHub für den ganzen Lauf, nicht über actions/download-artifact:
    # Nach „Re-run failed jobs“ müssen auch die Ergebnisse der grünen Teile aus dem ersten Versuch
    # da sein (Befund M1 der unabhängigen Prüfung).
    assert not [step for step in steps if "download-artifact" in str(step.get("uses", ""))]
    assert '"$GITHUB_RUN_ID"' in download["run"]
    assert "--pattern 'ergebnis-*'" in download["run"]
    assert download["env"]["GH_TOKEN"] == "${{ github.token }}"  # noqa: S105 -- Verweis auf den Schlüssel des Laufs, kein Passwort
    assert _gesamt()["permissions"] == {"actions": "read", "contents": "read"}
    assert zusammenfassen["run"].strip() == './pruefen.sh gesamt "$RUNNER_TEMP/ergebnisse"'
    assert '"$RUNNER_TEMP/ergebnisse"' in download["run"]
    assert steps.index(download) < steps.index(zusammenfassen)
    assert "continue-on-error" not in zusammenfassen


def test_die_gesamtpruefung_ist_rot_wenn_ein_teil_nicht_gruen_beendet_ist():
    steps = _gesamt()["steps"]
    pruefung = [step for step in steps if "needs.pruefen.result" in _condition(step)]

    assert len(pruefung) == 1
    step = pruefung[0]
    # Läuft auch, wenn die Zusammenfassung schon rot war, und nur, wenn nicht alle Teile grün sind:
    # abgebrochen, übersprungen oder rot.
    assert _condition(step) == "always() && needs.pruefen.result != 'success'"
    assert "::error" in step["run"]
    assert step["run"].strip().endswith("exit 1")
    assert "continue-on-error" not in step


def test_die_gesamtpruefung_hat_ein_kurzes_zeitlimit():
    assert _gesamt()["timeout-minutes"] <= 5
