"""Tests für den Leistungstest am Ende jeder Phase (#145, NFA-05): alt gegen neu, Grenzen, Markierung, Ergebnisse.

Für #145 gibt es keine Szenarien (Klärung vom 13.11.2026: Nutzende merken im Tool nichts davon). Die Tests
prüfen die Akzeptanzkriterien aus dem Text von #145. Sie laufen bei jedem Prüflauf mit, mit erfundenen Zeiten;
gemessen wird hier nichts (das macht `tests/leistungstest.py` nur am Phasenende).
"""

import json
import re

import pytest
import yaml
from django.conf import settings

from tests import leistungstest
from tests.leistungsvergleich import check_inputs, compare, load, main, marker, section

BASE_DIR = settings.BASE_DIR
WORKFLOW = BASE_DIR / ".github" / "workflows" / "leistungstest.yml"
SKILL = BASE_DIR / ".claude" / "skills" / "phase-steuern" / "SKILL.md"
RESULTS_FILE = BASE_DIR / "docs" / "leistungstest.md"


def rows_by_page(new, old):
    return {row["page"]: row for row in compare(new, old)}


def write(tmp_path, name, pages, unmeasured=()):
    path = tmp_path / name
    path.write_text(json.dumps({"seiten": pages, "ohne_messung": list(unmeasured)}), encoding="utf-8")
    return str(path)


# ---------- Grenzen ----------


def test_ueber_2_sekunden_blockiert_immer_auch_ohne_verschlechterung():
    rows = rows_by_page({"Seite mit 500 Personen": [2.1, 2.2, 2.0]}, {"Seite mit 500 Personen": [2.3]})

    assert rows["Seite mit 500 Personen"]["verdict"] == "rot"


def test_genau_2_sekunden_blockiert_wie_im_leistungstest_aus_104():
    assert rows_by_page({"Seite": [2.0]}, None)["Seite"]["verdict"] == "rot"


def test_mehr_als_25_prozent_langsamer_haelt_die_phase_an_bis_sebastian_entscheidet():
    rows = rows_by_page({"Seite mit 500 Personen": [1.2]}, {"Seite mit 500 Personen": [0.9]})

    row = rows["Seite mit 500 Personen"]
    assert row["verdict"] == "anhalten"
    assert row["change"] == pytest.approx(1.2 / 0.9 - 1)


def test_bis_25_prozent_langsamer_steht_nur_im_ergebnis():
    rows = rows_by_page({"Gliederung": [0.5], "Genau 25 %": [1.25], "Schneller": [0.4]},
                        {"Gliederung": [0.45], "Genau 25 %": [1.0], "Schneller": [0.8]})

    assert {page: row["verdict"] for page, row in rows.items()} == {
        "Gliederung": "gruen", "Genau 25 %": "gruen", "Schneller": "gruen"}
    assert rows["Schneller"]["change"] == pytest.approx(-0.5)


def test_seite_ohne_wert_der_vorigen_phase_prueft_nur_gegen_2_sekunden():
    rows = rows_by_page({"Seite einer Veranstaltung": [1.9], "Neu und langsam": [2.4]}, {"Gliederung": [0.1]})

    assert rows["Seite einer Veranstaltung"]["previous"] is None
    assert rows["Seite einer Veranstaltung"]["change"] is None
    assert rows["Seite einer Veranstaltung"]["verdict"] == "gruen"
    assert rows["Neu und langsam"]["verdict"] == "rot"


def test_der_erste_lauf_ohne_vorige_phase_legt_den_ausgangswert_ab():
    rows = compare({"Gliederung „Organisation“": [0.6], "Seite mit 500 Personen": [1.0]}, None)

    assert [row["verdict"] for row in rows] == ["gruen", "gruen"]
    text = section(rows, phase="P2", previous="", commit="0123456789abcdef", day="30.06.2027", unmeasured=[],
                   dropped=[])
    assert "Ausgangswert" in text
    assert "| Gliederung „Organisation“ | 0,60 s | – | – | im Rahmen |" in text


# ---------- Alt gegen neu in einem Lauf ----------


def test_es_zaehlt_der_mittlere_wert_aller_durchgaenge(tmp_path):
    first = write(tmp_path, "neu-1.json", {"Seite": [0.1, 0.2, 0.9]})
    second = write(tmp_path, "neu-2.json", {"Seite": [0.3, 0.4]}, unmeasured=["event_page"])

    times, unmeasured = load([first, second])

    assert times == {"Seite": [0.1, 0.2, 0.9, 0.3, 0.4]}
    assert unmeasured == ["event_page"]
    assert compare(times, None)[0]["time"] == pytest.approx(0.3)


def test_ergebnis_je_seite_mit_zeit_wert_der_vorigen_phase_und_abweichung():
    rows = compare({"Seite mit 500 Personen": [1.2], "Gliederung „Organisation“": [0.66], "Neue Seite": [0.3]},
                   {"Seite mit 500 Personen": [0.9], "Gliederung „Organisation“": [0.6]})

    text = section(rows, phase="P3", previous="phasenende-p2", commit="0123456789abcdef", day="31.12.2027",
                   unmeasured=["event_page"], dropped=["Alte Seite"])

    assert text.startswith("## P3\n")
    assert "`0123456`" in text and "`phasenende-p2`" in text and "31.12.2027" in text
    assert "| Seite | Zeit | Wert der vorigen Phase | Abweichung | Ergebnis |" in text
    assert "| Seite mit 500 Personen | 1,20 s | 0,90 s | +33,3 % | mehr als 25 % langsamer: Sebastian entscheidet |" in text
    assert "| Gliederung „Organisation“ | 0,66 s | 0,60 s | +10,0 % | im Rahmen |" in text
    assert "| Neue Seite | 0,30 s | – | neue Seite | im Rahmen |" in text
    assert re.search(r"ohne Messung.*event_page", text)
    assert re.search(r"nicht mehr gemessen.*Alte Seite", text)


def test_auswertung_ist_rot_bei_2_sekunden_oder_mehr_als_25_prozent_und_sonst_gruen(tmp_path, capsys):
    old = write(tmp_path, "alt-1.json", {"Seite": [1.0]})
    common = ["auswerten", "--phase", "P3", "--vorige", "phasenende-p2", "--commit", "abc1234", "--alt", old]

    assert main([*common, "--neu", write(tmp_path, "gruen.json", {"Seite": [1.1]})]) == 0
    assert main([*common, "--neu", write(tmp_path, "anhalten.json", {"Seite": [1.3]})]) == 1
    assert main([*common, "--neu", write(tmp_path, "rot.json", {"Seite": [2.5]})]) == 1
    assert "| Seite | 1,10 s | 1,00 s | +10,0 % | im Rahmen |" in capsys.readouterr().out


def test_fehlt_eine_ergebnisdatei_ist_die_auswertung_rot(tmp_path, capsys):
    new = write(tmp_path, "neu-1.json", {"Seite": [0.5]})

    code = main(["auswerten", "--phase", "P3", "--vorige", "phasenende-p2", "--commit", "abc1234",
                 "--alt", str(tmp_path / "alt-1.json"), "--neu", new])

    assert code == 1
    assert "alt-1.json" in capsys.readouterr().out


# ---------- Markierung ----------


def test_das_ende_jeder_phase_hat_eine_feste_markierung():
    assert marker("P2") == "phasenende-p2"
    assert marker("P10") == "phasenende-p10"


@pytest.mark.parametrize(("phase", "previous"), [("P2", ""), ("P3", "phasenende-p2"), ("P10", "phasenende-p9")])
def test_eingaben_passen_zur_phase(phase, previous):
    check_inputs(phase, previous)


@pytest.mark.parametrize(("phase", "previous"), [
    ("P3", ""),  # nur am Ende von P2 gibt es keine vorige Phase
    ("P3", "phasenende-p1"),  # nicht die direkt vorige Phase
    ("P2", "phasenende-p1"),  # P1 hat keine Markierung, P2 ist der Ausgangswert
    ("p3", "phasenende-p2"),
    ("P3; echo x", "phasenende-p2"),
    ("P3", "main"),
])
def test_falsche_eingaben_brechen_ab(phase, previous):
    with pytest.raises(ValueError):
        check_inputs(phase, previous)


def test_der_ablauf_prueft_die_eingaben_bevor_er_den_alten_stand_holt():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["messen"]["steps"]
    check = next(index for index, step in enumerate(steps) if "leistungsvergleich.py pruefen" in step.get("run", ""))
    old = next(index for index, step in enumerate(steps) if step.get("with", {}).get("path") == "alt")

    assert check < old
    assert steps[old]["with"]["ref"] == "refs/tags/${{ inputs.vorige_phase }}"
    assert steps[old]["if"] == "inputs.vorige_phase != ''"


# ---------- Ablauf auf GitHub ----------


def test_der_ablauf_misst_abwechselnd_alt_und_neu_im_selben_lauf_und_wertet_aus():
    text = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on", workflow.get(True))
    inputs = triggers["workflow_dispatch"]["inputs"]
    runs = "\n".join(step.get("run", "") for step in workflow["jobs"]["messen"]["steps"])

    assert set(triggers) == {"workflow_dispatch"}
    assert inputs["phase"]["required"] is True
    assert inputs["vorige_phase"]["required"] is False
    loop = re.search(r"for runde in [^;\n]+; do(.*?)\bdone\b", runs, flags=re.S)
    assert loop, "Durchgänge fehlen"
    body = loop.group(1)
    assert 0 <= body.index("alt") < body.index("neu")
    assert body.count("pytest tests/leistungstest.py") == 2
    assert "LEISTUNGSTEST_ERGEBNIS" in body
    assert "leistungsvergleich.py auswerten" in runs


def test_eingaben_kommen_nur_ueber_umgebungsvariablen_in_die_befehle():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    for step in workflow["jobs"]["messen"]["steps"]:
        assert "${{" not in step.get("run", ""), step.get("name")


# ---------- Seiten mit Personen ohne Messung ----------


def test_der_test_meldet_seiten_mit_personen_ohne_messung():
    unmeasured = leistungstest.unmeasured_pages()

    assert "event_page" in unmeasured
    for measured in ("organisation", "organisation_unit", "organisation_suggestions", "organisation_admit_search"):
        assert measured not in unmeasured
    assert "profile" not in unmeasured, "zeigt nur die angemeldete Person selbst"
    assert "building_blocks" not in unmeasured, "ohne Personendaten"


def test_gemessene_und_ausgenommene_seiten_gibt_es_und_sie_zeigen_personen():
    from django.urls import get_resolver

    from tests.test_rundumtest import _all_patterns

    views = {entry.name: entry.callback for _pattern, entry in _all_patterns(get_resolver().url_patterns)}
    named = [*leistungstest.PAGES.values(), *leistungstest.NOT_MEASURED]
    for name in named:
        assert name in views, name
        assert getattr(views[name], "rights_rows", None), name
    assert all(reason.strip() for reason in leistungstest.NOT_MEASURED.values())


def test_die_ergebnisse_eines_laufs_landen_in_einer_datei_fuer_den_vergleich(tmp_path, monkeypatch):
    monkeypatch.setattr(leistungstest, "RESULTS", {"Seite mit 500 Personen": [0.5, 0.6]})
    path = tmp_path / "neu-1.json"

    leistungstest.write_results(str(path))

    times, unmeasured = load([str(path)])
    assert times == {"Seite mit 500 Personen": [0.5, 0.6]}
    assert unmeasured == leistungstest.unmeasured_pages()


def test_jede_gemessene_seite_steht_in_pages():
    with pytest.raises(AssertionError):
        leistungstest.check_page("Unbekannte Seite", [0.1])


# ---------- Ablage und Schritt am Phasenende ----------


def test_die_ergebnisse_jeder_phase_liegen_in_docs():
    text = RESULTS_FILE.read_text(encoding="utf-8")

    assert "## P2" in text
    assert "docs/leistungstest.md" in (BASE_DIR / "README.md").read_text(encoding="utf-8")


def test_phase_steuern_nennt_den_leistungstest_am_phasenende():
    text = SKILL.read_text(encoding="utf-8")
    end = text.split("## 5. Abschluss", 1)[1]

    assert "Leistungstest" in end
    for step in ("Erweitern", "Messen", "Ablegen", "Markieren"):
        assert f"**{step}" in end, step
    assert "phasenende-p" in end
    assert "docs/leistungstest.md" in end
