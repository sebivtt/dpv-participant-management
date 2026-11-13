"""Tests für das Prüfskript `pruefen.sh` (#235, `CLAUDE.md`, Ablauf je Aufgabe Nr. 4; Teile #307).

Das Skript läuft hier in einer Wegwerf-Kopie. Statt `uv` steht im Suchpfad ein Platzhalter: Er
schreibt jeden Aufruf mit seinen Argumenten in eine Protokolldatei, gibt erfundene pytest-
Zusammenfassungen aus und lehnt jeden unbekannten Aufruf ab. So braucht der Test weder Datenbank
noch Docker und läuft in Sekunden. Geprüft wird das Skript, nicht die Prüfungen selbst.

Nicht jede Schreibweise der Meldungen wird einzeln geprüft, sondern ihr Inhalt.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "pruefen.sh"

FAKE_UV = f"""#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
here = os.environ["FAKE_DIR"]
with open(os.path.join(here, "aufrufe.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps({{
        "args": args,
        "async": os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE"),
        "browser": os.environ.get("RAUCHTEST_BROWSER"),
    }}) + "\\n")
config = json.load(open(os.path.join(here, "fake.json"), encoding="utf-8"))
line = " ".join(args)


def kind():
    if args[:2] == ["lock", "--check"]:
        return "lock"
    if args[:1] == ["export"]:
        return "export"
    if args[:2] != ["run", "--locked"]:
        return None
    rest = args[2:]
    if rest[:2] == ["--env-file", ".env"]:
        rest = rest[2:]
    if rest[:2] == ["ruff", "check"]:
        return "ruff"
    if rest[:3] == ["python", "manage.py", "check"]:
        return "check"
    if rest[:3] == ["python", "manage.py", "makemigrations"]:
        return "migrations"
    if rest[:1] == ["pip-audit"]:
        return "audit"
    if rest[:1] == ["pytest"]:
        if any(arg.startswith("rauchtests") for arg in rest):
            return "pytest-rauch"
        if any(arg.startswith("containertests") for arg in rest):
            return "pytest-container"
        return "pytest-tests"
    return None


step = kind()
if step is None:
    print("Platzhalter: unbekannter Aufruf: " + line, file=sys.stderr)
    sys.exit(99)
if step.startswith("pytest"):
    print(config.get("ausgabe", {{}}).get(step, "=== 5 passed in 1.00s ==="))
else:
    print("ok: " + step)
sys.exit(1 if step in config.get("rot", []) else 0)
"""


class Lauf:
    def __init__(self, tmp_path):
        self.root = tmp_path / "kopie"
        self.fake_dir = tmp_path / "platzhalter"
        self.root.mkdir()
        self.fake_dir.mkdir()
        shutil.copy(SCRIPT, self.root / "pruefen.sh")
        for name in ["tests/test_a.py", "tests/test_b.py", "rauchtests/test_r.py", "containertests/test_c.py"]:
            path = self.root / name
            path.parent.mkdir(exist_ok=True)
            path.write_text("", encoding="utf-8")
        uv = self.fake_dir / "uv"
        uv.write_text(FAKE_UV, encoding="utf-8")
        uv.chmod(uv.stat().st_mode | stat.S_IXUSR)
        self.config = {"ausgabe": {}, "rot": []}

    def start(self, *args, env_extra=None):
        (self.fake_dir / "fake.json").write_text(json.dumps(self.config), encoding="utf-8")
        hidden = ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY", "DJANGO_ALLOW_ASYNC_UNSAFE", "RAUCHTEST_BROWSER", "PRUEFTEIL_ERGEBNIS")
        env = {k: v for k, v in os.environ.items() if k not in hidden}
        env.update(env_extra or {})
        env["PATH"] = f"{self.fake_dir}{os.pathsep}{env['PATH']}"
        env["FAKE_DIR"] = str(self.fake_dir)
        done = subprocess.run(  # noqa: S603 -- fester Aufruf der Wegwerf-Kopie des Skripts mit erfundenen Argumenten
            ["/bin/sh", str(self.root / "pruefen.sh"), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=False,
        )
        self.code = done.returncode
        self.out = done.stdout + done.stderr
        log = self.fake_dir / "aufrufe.jsonl"
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        self.calls = [json.loads(line) for line in lines]
        return self

    def called(self, *words):
        """Aufrufe, deren Argumente der Reihe nach die genannten Wörter enthalten."""
        found = []
        for call in self.calls:
            args = call["args"]
            position = 0
            for word in words:
                if word in args[position:]:
                    position = args.index(word, position) + 1
                else:
                    break
            else:
                found.append(call)
        return found

    def pytest_calls(self):
        return [call for call in self.calls if "pytest" in call["args"]]


@pytest.fixture
def lauf(tmp_path):
    return Lauf(tmp_path)


def _summary(passed=5, skipped=0):
    parts = [f"{passed} passed"] + ([f"{skipped} skipped"] if skipped else [])
    return f"=========== {', '.join(parts)} in 1.20s ==========="


def test_voller_lauf_startet_alle_acht_pruefungen(lauf):
    lauf.start()

    assert lauf.code == 0
    assert len(lauf.called("lock", "--check")) == 1
    assert len(lauf.called("ruff", "check")) == 1
    assert len(lauf.called("python", "manage.py", "check")) == 1
    assert len(lauf.called("python", "manage.py", "makemigrations", "--check", "--dry-run")) == 1
    pytest_calls = lauf.pytest_calls()
    assert len(pytest_calls) == 3
    tests, rauch, container = pytest_calls
    assert tests["args"][-2:] == ["pytest", "-rsfE"]
    assert rauch["args"][-2:] == ["rauchtests", "-rsfE"]
    assert container["args"][-2:] == ["containertests", "-rsfE"]
    # Nur der Rauchtest läuft mit der Ausnahme für Playwright, wie heute.
    assert (tests["async"], rauch["async"], container["async"]) == (None, "true", None)
    assert len(lauf.called("pip-audit")) == 1
    assert len(lauf.called("export")) == 1
    assert len(lauf.calls) == 9  # acht Prüfungen, die Paketprüfung braucht zwei Aufrufe


def test_voller_lauf_ohne_uebersprungenes_meldet_alle_pruefungen_gruen(lauf):
    lauf.start()

    assert lauf.code == 0
    assert "Alle Prüfungen grün." in lauf.out
    assert "Alle gelaufenen Prüfungen grün" not in lauf.out
    assert "Nicht bestanden" not in lauf.out


def test_voller_lauf_mit_uebersprungenem_nennt_die_zahl_und_verweist_auf_die_gruende(lauf):
    lauf.config["ausgabe"]["pytest-rauch"] = _summary(skipped=4)
    lauf.start()

    assert lauf.code == 0
    assert "Alle Prüfungen grün." not in lauf.out
    assert "Alle gelaufenen Prüfungen grün, 4 Tests übersprungen (Gründe oben unter SKIPPED)." in lauf.out


def test_schneller_lauf_ohne_dateien_startet_genau_die_vier_pruefungen_ohne_tests(lauf):
    lauf.start("schnell")

    assert lauf.code == 0
    assert len(lauf.calls) == 4
    assert [len(lauf.called(*words)) for words in (["lock"], ["ruff"], ["manage.py", "check"], ["makemigrations"])] == [1] * 4
    assert lauf.pytest_calls() == []
    assert not lauf.called("pip-audit") and not lauf.called("export")
    assert "Schneller Lauf grün" in lauf.out
    nicht_ausgewaehlt = lauf.out.split("Nicht ausgewählt:", 1)[1]
    for part in ["Tests", "Rauchtests", "Container", "pip-audit"]:
        assert part in nicht_ausgewaehlt, part
    assert "SKIPPED" not in lauf.out.split("Schneller Lauf grün", 1)[1]


def test_schneller_lauf_mit_zwei_dateien_startet_zwei_getrennte_pytest_laeufe(lauf):
    lauf.start("schnell", "tests/test_a.py", "rauchtests/test_r.py")

    assert lauf.code == 0
    tests, rauch = lauf.pytest_calls()
    assert tests["args"][-3:] == ["pytest", "-rsfE", "tests/test_a.py"]
    assert rauch["args"][-3:] == ["pytest", "-rsfE", "rauchtests/test_r.py"]
    assert (tests["async"], rauch["async"]) == (None, "true")
    assert not lauf.called("pip-audit") and not lauf.called("export")
    assert not any("containertests" in call["args"] for call in lauf.calls)
    assert "Schneller Lauf grün" in lauf.out


def test_schneller_lauf_gibt_mehrere_dateien_eines_ordners_an_einen_lauf(lauf):
    lauf.start("schnell", "tests/test_a.py", "tests/test_b.py")

    (tests,) = lauf.pytest_calls()
    assert tests["args"][-4:] == ["pytest", "-rsfE", "tests/test_a.py", "tests/test_b.py"]


def test_schneller_lauf_mit_uebersprungenen_nennt_zahl_und_nicht_ausgewaehltes(lauf):
    lauf.config["ausgabe"]["pytest-tests"] = _summary(skipped=2)
    lauf.start("schnell", "tests/test_a.py")

    assert lauf.code == 0
    schluss = lauf.out.split("Schneller Lauf grün", 1)[1]
    assert ", 2 Tests übersprungen (Gründe oben unter SKIPPED)" in schluss
    assert schluss.index("übersprungen") < schluss.index("Nicht ausgewählt:")


def test_uebersprungene_aus_zwei_laeufen_werden_addiert(lauf):
    lauf.config["ausgabe"]["pytest-tests"] = _summary(skipped=2)
    lauf.config["ausgabe"]["pytest-rauch"] = _summary(skipped=3)
    lauf.start("schnell", "tests/test_a.py", "rauchtests/test_r.py")

    assert "5 Tests übersprungen" in lauf.out


def test_fehlt_eine_zusammenfassung_steht_zahl_unbekannt_nie_null(lauf):
    lauf.config["ausgabe"]["pytest-rauch"] = "Der Lauf endete ohne Zusammenfassung."
    lauf.start("schnell", "tests/test_a.py", "rauchtests/test_r.py")

    assert "Zahl unbekannt" in lauf.out
    assert "Schneller Lauf grün" in lauf.out
    assert not re.search(r"\b0 Tests übersprungen", lauf.out)
    assert "Alle Prüfungen grün." not in lauf.out


@pytest.mark.parametrize("args", [(), ("schnell", "tests/test_a.py")])
def test_roter_schritt_ohne_tests_beendet_das_skript_rot_ohne_gruene_schlusszeile(lauf, args):
    lauf.config["rot"] = ["ruff"]
    lauf.start(*args)

    assert lauf.code == 1
    assert "Nicht bestanden:" in lauf.out
    assert "Code-Regeln (ruff)" in lauf.out.split("Nicht bestanden:", 1)[1]
    for gruen in ["Alle Prüfungen grün", "Alle gelaufenen Prüfungen grün", "Schneller Lauf grün"]:
        assert gruen not in lauf.out


def test_roter_test_bleibt_auch_bei_uebersprungenem_rot(lauf):
    lauf.config["rot"] = ["pytest-tests"]
    lauf.config["ausgabe"]["pytest-tests"] = "=========== 1 failed, 4 passed, 2 skipped in 1.20s ==========="
    lauf.start("schnell", "tests/test_a.py")

    assert lauf.code == 1
    assert "Schneller Lauf grün" not in lauf.out
    assert "Nicht bestanden:" in lauf.out


def test_jede_zeile_nennt_die_dauer_auch_bei_rot(lauf):
    lauf.config["rot"] = ["ruff"]
    lauf.start()

    dauer = r"\((?:\d+ min )?\d+ s\)"
    assert re.search(rf"^--> grün: .*{dauer}$", lauf.out, re.M)
    assert re.search(rf"^--> ROT: Code-Regeln \(ruff\) {dauer}$", lauf.out, re.M)
    assert len(re.findall(r"^--> (?:grün|ROT): ", lauf.out, re.M)) == 8
    assert len(re.findall(rf"^--> (?:grün|ROT): .*{dauer}$", lauf.out, re.M)) == 8


@pytest.mark.parametrize(
    "args",
    [
        ("schnell", "tests/gibt_es_nicht.py"),
        ("schnell", "pyproject.toml"),
        ("schnell", "containertests/test_c.py"),
        ("schnell", "tests/../pyproject.toml"),
        ("schnell", "/etc/hosts"),
        ("schnell", "--maxfail=1"),
        ("schnell", "tests/test_a.py", "-x"),
        ("--schnell",),
        ("langsam",),
        ("tests/test_a.py",),
    ],
)
def test_unbekannte_datei_oder_option_laesst_das_skript_mit_meldung_scheitern(lauf, args):
    lauf.start(*args)

    assert lauf.code != 0
    assert lauf.calls == [], "es darf noch keine Prüfung gelaufen sein"
    assert lauf.out.strip(), "es braucht eine Meldung"
    assert "Alle" not in lauf.out and "grün" not in lauf.out


# --- Teile für GitHub (#307) -------------------------------------------------------------------
# Auf GitHub laufen die Prüfungen gleichzeitig in Teilen auf eigenen Rechnern; jeder Teil ruft
# `./pruefen.sh teil <name>` auf. Am Ende fasst `./pruefen.sh gesamt <ordner>` die Ergebnisse
# zusammen. Lokal bleiben `./pruefen.sh` und `./pruefen.sh schnell` unverändert (Tests oben).

TEILE = ["grund", "tests-1", "tests-2", "rauchtest-chromium", "rauchtest-firefox", "rauchtest-webkit"]


def _teile(lauf):
    lauf.start("teile")
    assert lauf.code == 0, lauf.out
    assert lauf.calls == [], "die Liste der Teile startet keine Prüfung"
    return lauf.out.split()


def _alle_teile(lauf, env_extra=None):
    """Startet jeden Teil einmal und gibt je Teil die Aufrufe zurück."""
    calls = {}
    for teil in _teile(lauf):
        lauf.start("teil", teil, env_extra=env_extra)
        assert lauf.code == 0, (teil, lauf.out)
        calls[teil] = lauf.calls
        (lauf.fake_dir / "aufrufe.jsonl").unlink(missing_ok=True)
    return calls


def _testdateien(call):
    return [arg for arg in call["args"] if arg.startswith("tests/")]


def test_es_gibt_genau_sechs_teile(lauf):
    assert _teile(lauf) == TEILE


def test_die_teile_starten_zusammen_jede_pruefung_des_vollen_laufs_genau_einmal(lauf):
    calls = _alle_teile(lauf)
    alle = [call for teil in calls.values() for call in teil]

    for words in (["lock", "--check"], ["ruff", "check"], ["manage.py", "check"], ["makemigrations", "--check"], ["pip-audit"], ["export"]):
        treffer = [call for call in alle if all(word in call["args"] for word in words)]
        assert len(treffer) == 1, words
    container = [call for call in alle if "containertests" in call["args"]]
    assert len(container) == 1
    assert container[0]["args"][-2:] == ["containertests", "-rsfE"]
    assert container[0] in calls["grund"]


def test_jeder_teil_mit_rauchtest_startet_genau_einen_browser_mit_der_ausnahme_fuer_playwright(lauf):
    calls = _alle_teile(lauf)

    for browser in ["chromium", "firefox", "webkit"]:
        (rauch,) = calls[f"rauchtest-{browser}"]
        assert rauch["args"][-2:] == ["rauchtests", "-rsfE"]
        assert (rauch["async"], rauch["browser"]) == ("true", browser)
    for teil in ["grund", "tests-1", "tests-2"]:
        assert all(call["browser"] is None and call["async"] is None for call in calls[teil]), teil


def test_jede_testdatei_laeuft_in_genau_einem_der_beiden_testteile_auch_eine_neue(lauf):
    for name in ["tests/test_neu.py", "tests/unterordner/test_tief.py", "tests/unterordner/tief_test.py"]:
        path = lauf.root / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("", encoding="utf-8")
    # Keine Testdateien nach den Regeln von pytest: Hilfsdateien, Daten, Zwischenspeicher.
    for name in ["tests/hilfe.py", "tests/conftest.py", "tests/daten/test_daten.json", "tests/__pycache__/test_a.cpython-313.pyc"]:
        path = lauf.root / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("", encoding="utf-8")
    calls = _alle_teile(lauf)

    erste = [datei for call in calls["tests-1"] for datei in _testdateien(call)]
    zweite = [datei for call in calls["tests-2"] for datei in _testdateien(call)]
    erwartet = {"tests/test_a.py", "tests/test_b.py", "tests/test_neu.py", "tests/unterordner/test_tief.py", "tests/unterordner/tief_test.py"}
    assert sorted(erste + zweite) == sorted(erwartet), "jede Datei genau einmal"
    assert erste and zweite, "beide Teile bekommen Dateien"
    for teil in ["tests-1", "tests-2"]:
        (call,) = calls[teil]
        assert call["args"][-len(_testdateien(call)) - 2 : -len(_testdateien(call))] == ["pytest", "-rsfE"]


def test_ein_testteil_ohne_dateien_startet_pytest_nicht_ohne_dateien(lauf):
    # Ohne Dateien würde pytest alle Tests sammeln; dann liefen sie doppelt.
    (lauf.root / "tests" / "test_b.py").unlink()
    calls = _alle_teile(lauf)

    gesamt = [datei for teil in ["tests-1", "tests-2"] for call in calls[teil] for datei in _testdateien(call)]
    assert gesamt == ["tests/test_a.py"]
    for teil in ["tests-1", "tests-2"]:
        for call in calls[teil]:
            if "pytest" in call["args"]:
                assert _testdateien(call), teil


def test_ein_teil_schreibt_sein_ergebnis_mit_gelaufenen_und_uebersprungenen_tests(lauf, tmp_path):
    datei = tmp_path / "ergebnis" / "tests-1"
    datei.parent.mkdir()
    lauf.config["ausgabe"]["pytest-tests"] = "====== 7 passed, 2 skipped, 1 xfailed, 3 deselected in 1.20s ======"
    lauf.start("teil", "tests-1", env_extra={"PRUEFTEIL_ERGEBNIS": str(datei)})

    assert lauf.code == 0
    assert datei.read_text(encoding="utf-8").split() == ["teil=tests-1", "ergebnis=gruen", "gelaufen=8", "uebersprungen=2"]
    assert "Teil tests-1 grün" in lauf.out
    assert "8 Tests gelaufen" in lauf.out
    assert "2 übersprungen" in lauf.out


def test_ein_roter_teil_schreibt_rot_und_endet_rot(lauf, tmp_path):
    datei = tmp_path / "rauch"
    lauf.config["rot"] = ["pytest-rauch"]
    lauf.config["ausgabe"]["pytest-rauch"] = "====== 1 failed, 170 passed in 9.99s ======"
    lauf.start("teil", "rauchtest-webkit", env_extra={"PRUEFTEIL_ERGEBNIS": str(datei)})

    assert lauf.code == 1
    assert datei.read_text(encoding="utf-8").split() == ["teil=rauchtest-webkit", "ergebnis=rot", "gelaufen=171", "uebersprungen=0"]
    assert "Nicht bestanden:" in lauf.out
    assert "Teil rauchtest-webkit grün" not in lauf.out


def test_ein_teil_ohne_zusammenfassung_von_pytest_meldet_die_zahl_unbekannt(lauf, tmp_path):
    datei = tmp_path / "ergebnis"
    lauf.config["ausgabe"]["pytest-container"] = "Der Lauf endete ohne Zusammenfassung."
    lauf.start("teil", "grund", env_extra={"PRUEFTEIL_ERGEBNIS": str(datei)})

    inhalt = datei.read_text(encoding="utf-8").split()
    assert "gelaufen=unbekannt" in inhalt and "uebersprungen=unbekannt" in inhalt


def test_auf_github_meldet_ein_roter_teil_den_roten_test_wie_bisher(lauf):
    lauf.config["rot"] = ["pytest-tests"]
    lauf.config["ausgabe"]["pytest-tests"] = (
        "FAILED tests/test_a.py::test_kaputt - AssertionError: erfunden\n====== 1 failed, 4 passed in 1.20s ======"
    )
    lauf.start("teil", "tests-1", env_extra={"GITHUB_ACTIONS": "true"})

    assert lauf.code == 1
    assert "::error title=ROT::Tests (pytest)" in lauf.out
    assert "::warning title=Test::FAILED tests/test_a.py::test_kaputt" in lauf.out


@pytest.mark.parametrize("args", [("teil",), ("teil", "tests-3"), ("teil", "tests-1", "tests/test_a.py"), ("teile", "x"), ("gesamt",)])
def test_unbekannter_teil_oder_zusaetzliche_angaben_scheitern_ohne_pruefung(lauf, args):
    lauf.start(*args)

    assert lauf.code == 2
    assert lauf.calls == []
    assert lauf.out.startswith("pruefen.sh: ")


def _ergebnisse(ordner, **abweichend):
    ordner.mkdir(exist_ok=True)
    for nummer, teil in enumerate(TEILE):
        werte = {"teil": teil, "ergebnis": "gruen", "gelaufen": str(100 + nummer), "uebersprungen": str(nummer % 2)}
        werte.update(abweichend.get(teil, {}))
        if werte.get("fehlt"):
            continue
        (ordner / teil).write_text("".join(f"{k}={v}\n" for k, v in werte.items()), encoding="utf-8")
    return ordner


def test_gesamt_ist_gruen_wenn_alle_teile_gruen_sind_und_nennt_die_summen(lauf, tmp_path):
    ordner = _ergebnisse(tmp_path / "ergebnisse")
    lauf.start("gesamt", str(ordner))

    assert lauf.code == 0, lauf.out
    assert lauf.calls == [], "die Gesamtprüfung startet keine Prüfung"
    assert "Gelaufene Tests: 615" in lauf.out  # 100 + 101 + … + 105
    assert "Übersprungene Tests: 3" in lauf.out
    assert "Alle Teile grün" in lauf.out
    for teil in TEILE:
        assert teil in lauf.out


def test_gesamt_schreibt_die_summen_in_den_bericht_des_laufs(lauf, tmp_path):
    ordner = _ergebnisse(tmp_path / "ergebnisse")
    bericht = tmp_path / "bericht.md"
    lauf.start("gesamt", str(ordner), env_extra={"GITHUB_STEP_SUMMARY": str(bericht)})

    text = bericht.read_text(encoding="utf-8")
    assert "615" in text and "Gelaufene Tests" in text
    assert "Übersprungene Tests: 3" in text


def test_gesamt_ist_rot_wenn_ein_teil_rot_ist_und_nennt_ihn(lauf, tmp_path):
    ordner = _ergebnisse(tmp_path / "ergebnisse", **{"rauchtest-webkit": {"ergebnis": "rot"}})
    lauf.start("gesamt", str(ordner))

    assert lauf.code == 1
    schluss = lauf.out.split("Nicht bestanden:", 1)[1]
    assert "rauchtest-webkit" in schluss
    assert "tests-1" not in schluss
    assert "Alle Teile grün" not in lauf.out


@pytest.mark.parametrize("teil", TEILE)
def test_gesamt_ist_rot_wenn_ein_teil_fehlt_also_abgebrochen_oder_nicht_gelaufen_ist(lauf, tmp_path, teil):
    ordner = _ergebnisse(tmp_path / "ergebnisse", **{teil: {"fehlt": True}})
    lauf.start("gesamt", str(ordner))

    assert lauf.code == 1
    schluss = lauf.out.split("Nicht bestanden:", 1)[1]
    assert teil in schluss
    assert "abgebrochen oder nicht gelaufen" in schluss
    assert "Alle Teile grün" not in lauf.out


def test_gesamt_ist_rot_ohne_ergebnisordner(lauf, tmp_path):
    lauf.start("gesamt", str(tmp_path / "gibt-es-nicht"))

    assert lauf.code == 1
    assert "Alle Teile grün" not in lauf.out


@pytest.mark.parametrize("falsch", [{"ergebnis": "gelb"}, {"teil": "tests-2"}, {"gelaufen": "viele"}])
def test_gesamt_ist_rot_bei_einem_unlesbaren_ergebnis(lauf, tmp_path, falsch):
    ordner = _ergebnisse(tmp_path / "ergebnisse", **{"tests-1": falsch})
    lauf.start("gesamt", str(ordner))

    assert lauf.code == 1
    assert "tests-1" in lauf.out.split("Nicht bestanden:", 1)[1]


def test_gesamt_nennt_unbekannte_zahl_nie_als_null(lauf, tmp_path):
    ordner = _ergebnisse(tmp_path / "ergebnisse", grund={"gelaufen": "unbekannt", "uebersprungen": "unbekannt"})
    lauf.start("gesamt", str(ordner))

    assert lauf.code == 0
    assert "Gelaufene Tests: Zahl unbekannt" in lauf.out
    assert "Übersprungene Tests: Zahl unbekannt" in lauf.out


# --- Jeder echte Test in genau einem Teil (#307) -----------------------------------------------
# Die Tests oben prüfen das Skript mit erfundenen Dateien. Hier zählt, was pytest in diesem Repo
# wirklich sammelt: Jeder Test aus tests/ und rauchtests/ muss in genau einem Teil laufen, auch
# einer, der erst später dazukommt. Gesammelt wird nur, nichts ausgeführt.

BASE_DIR = SCRIPT.parent


def _gesammelt(*args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "RAUCHTEST_BROWSER"}
    env.update(env_extra or {})
    done = subprocess.run(  # noqa: S603 -- fester Aufruf von pytest dieses Repos, nur Sammeln
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", *args],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
        check=False,
    )
    return done.returncode, [line for line in done.stdout.splitlines() if "::" in line], done.stdout + done.stderr


def test_jede_echte_testdatei_aus_tests_laeuft_in_genau_einem_testteil(tmp_path):
    lauf = Lauf(tmp_path)
    for name in ["test_a.py", "test_b.py"]:
        (lauf.root / "tests" / name).unlink()
    for path in (BASE_DIR / "tests").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            kopie = lauf.root / path.relative_to(BASE_DIR)
            kopie.parent.mkdir(parents=True, exist_ok=True)
            kopie.write_text("", encoding="utf-8")
    calls = _alle_teile(lauf)
    teile = {teil: [datei for call in calls[teil] for datei in _testdateien(call)] for teil in ["tests-1", "tests-2"]}

    code, gesammelt, ausgabe = _gesammelt()
    assert code == 0, ausgabe[-3000:]
    dateien = {nodeid.split("::", 1)[0] for nodeid in gesammelt}
    assert len(gesammelt) > 1000, "pytest hat die Tests aus tests/ gesammelt"
    zaehlung = {datei: sum(teil.count(datei) for teil in teile.values()) for datei in dateien}
    assert {datei: n for datei, n in zaehlung.items() if n != 1} == {}, "jede Datei mit Tests in genau einem Teil"
    for teil, liste in teile.items():
        assert all((BASE_DIR / datei).is_file() for datei in liste), teil


def test_jeder_echte_rauchtest_laeuft_in_genau_einem_browserteil():
    code, alle, ausgabe = _gesammelt("rauchtests")
    assert code == 0, ausgabe[-3000:]
    assert len(alle) > 100

    je_teil = {}
    for browser in ["chromium", "firefox", "webkit"]:
        code, ids, ausgabe = _gesammelt("rauchtests", env_extra={"RAUCHTEST_BROWSER": browser})
        assert code == 0, (browser, ausgabe[-3000:])
        je_teil[browser] = ids
        andere = {"chromium", "firefox", "webkit"} - {browser}
        assert not [nodeid for nodeid in ids if any(f"[{name}" in nodeid for name in andere)], browser

    zaehlung = {nodeid: sum(ids.count(nodeid) for ids in je_teil.values()) for nodeid in alle}
    assert {nodeid: n for nodeid, n in zaehlung.items() if n != 1} == {}, "jeder Rauchtest in genau einem Teil"
    assert sorted(nodeid for ids in je_teil.values() for nodeid in ids) == sorted(alle), "kein Test kommt dazu"


def test_ein_unbekannter_browser_fuer_den_rauchtest_bricht_mit_meldung_ab():
    code, ids, ausgabe = _gesammelt("rauchtests", env_extra={"RAUCHTEST_BROWSER": "netscape"})

    assert code != 0
    assert ids == []
    assert "RAUCHTEST_BROWSER" in ausgabe
