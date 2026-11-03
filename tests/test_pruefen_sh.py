"""Tests für das Prüfskript `pruefen.sh` (#235, `CLAUDE.md`, Ablauf je Aufgabe Nr. 4).

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
    log.write(json.dumps({{"args": args, "async": os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")}}) + "\\n")
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

    def start(self, *args):
        (self.fake_dir / "fake.json").write_text(json.dumps(self.config), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "DJANGO_ALLOW_ASYNC_UNSAFE")}
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
