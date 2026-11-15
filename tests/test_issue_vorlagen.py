"""Tests für die Issue-Vorlagen und den Leitfaden des externen Reviews am Phasenende (#26).

Eine fehlerhafte Vorlage zeigt GitHub ohne Fehlermeldung einfach nicht an. Diese Tests prüfen
deshalb den Aufbau aller Vorlagen und, ob die Vorlagen des Reviews die Felder enthalten, die
#26 verlangt. Ob GitHub sie tatsächlich anzeigt, zeigt erst ein Blick auf GitHub selbst.
"""

import re
import shlex
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / ".github" / "ISSUE_TEMPLATE"
GUIDE = BASE_DIR / "docs" / "review-leitfaden.md"

# Feldarten, die GitHub in Issue-Vorlagen kennt (docs.github.com, „Syntax for GitHub's form schema“).
FIELD_TYPES = {"markdown", "input", "textarea", "dropdown", "checkboxes"}
TOP_LEVEL_KEYS = {"name", "description", "title", "labels", "assignees", "projects", "type", "body"}
STAGES = ["blockierend", "zeitnah", "später", "Fehlalarm oder Duplikat", "akzeptiertes Risiko"]
TEMPLATES = sorted(path for path in TEMPLATE_DIR.glob("*.yml") if path.name != "config.yml")


def _load(name: str) -> dict:
    return yaml.safe_load((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def _fields(template: dict) -> dict[str, dict]:
    """Die Eingabefelder einer Vorlage nach ihrer Kennung, ohne reine Hinweistexte."""
    return {field["id"]: field for field in template["body"] if field["type"] != "markdown"}


def _required(field: dict) -> bool:
    return field.get("validations", {}).get("required", False) is True


def test_die_vorlagen_des_reviews_gibt_es():
    names = {path.name for path in TEMPLATES}

    assert {"externes-review.yml", "review-befund.yml"} <= names


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda path: path.name)
def test_jede_issue_vorlage_ist_gueltig_aufgebaut(path):
    template = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert isinstance(template.get("name"), str) and template["name"].strip()
    assert isinstance(template.get("description"), str) and template["description"].strip()
    assert isinstance(template.get("body"), list) and template["body"]
    # Unbekannte Schlüssel lassen GitHub die ganze Vorlage verwerfen.
    assert set(template) <= TOP_LEVEL_KEYS, set(template) - TOP_LEVEL_KEYS

    ids, labels = [], []
    for field in template["body"]:
        assert field.get("type") in FIELD_TYPES, field
        attributes = field.get("attributes", {})
        if field["type"] == "markdown":
            assert attributes.get("value", "").strip(), field
            continue
        assert re.fullmatch(r"[A-Za-z0-9_-]+", field.get("id", "")), field
        assert attributes.get("label", "").strip(), field
        if field["type"] == "dropdown":
            # GitHub verlangt Optionen, jede nur einmal, nicht leer und nicht „None“.
            options = attributes.get("options")
            assert options, field
            assert len(options) == len(set(options)), field
            assert all(str(option).strip() and option != "None" for option in options), field
        ids.append(field["id"])
        labels.append(attributes["label"])

    # GitHub verlangt eindeutige Kennungen und Beschriftungen innerhalb einer Vorlage.
    assert len(ids) == len(set(ids))
    assert len(labels) == len(set(labels))


def test_vorlage_review_hat_alle_pflichtfelder_aus_26():
    template = _load("externes-review.yml")
    fields = _fields(template)

    expected = {"phase", "commit", "datum", "bereiche", "modelle", "ergebnisse", "befunde", "abschluss"}
    assert expected <= fields.keys()
    # Beim Anlegen steht nur fest, was geprüft wird. Modelle, Ergebnisse, Befunde und Abschluss
    # werden im Lauf des Reviews nachgetragen und sind deshalb beim Anlegen nicht Pflicht.
    assert {name for name in expected if _required(fields[name])} == {"phase", "commit", "datum", "bereiche"}
    assert "externes-review" in template["labels"]


def test_vorlage_befund_hat_alle_felder_aus_26():
    template = _load("review-befund.yml")
    fields = _fields(template)

    expected = {
        "kategorie",
        "fundstelle",
        "beobachtung",
        "beleg",
        "auswirkung",
        "sicherheit",
        "klaerung",
        "entscheidung",
        "abnahmekriterien",
    }
    assert expected <= fields.keys()
    # Klärung, Entscheidung und Abnahmekriterien entstehen erst mit grill-me, alles andere
    # steht beim Anlegen fest.
    must = {"review", "kategorie", "fundstelle", "beobachtung", "beleg", "auswirkung", "sicherheit", "stufe"}
    assert {name for name, field in fields.items() if _required(field)} == must
    assert "status" not in fields, "Der zweite Status neben Label und Schließen entfällt (#240); die Stufe bleibt"
    assert "stufe" in fields
    assert "review-befund" in template["labels"]


def test_befund_issues_gibt_es_nur_fuer_die_stufen_mit_eigener_bearbeitung():
    # Fehlalarme, Duplikate und akzeptierte Risiken stehen nur im Review-Issue (Leitfaden, Abschnitt 8).
    options = _fields(_load("review-befund.yml"))["stufe"]["attributes"]["options"]

    assert options == STAGES[:3]


def test_leitfaden_enthaelt_beide_pruefauftraege_und_den_datenschutz():
    guide = GUIDE.read_text(encoding="utf-8")

    assert "Prüfauftrag A" in guide
    assert "Prüfauftrag B" in guide
    assert "DSG-08" in guide
    for stage in STAGES:
        assert stage in guide


def test_leitfaden_verlangt_nach_jeder_behebung_alle_pruefungen():
    guide = GUIDE.read_text(encoding="utf-8")

    assert "./pruefen.sh" in guide


def test_pruefauftraege_nennen_phase_und_commit_nur_ueber_platzhalter():
    # Fest eingetragene Phasen übersieht man beim nächsten Review leicht; dann bewertet ein
    # Modell die Abschlusskriterien der falschen Phase.
    guide = GUIDE.read_text(encoding="utf-8")
    # Nur die Textblöcke zum Hineinkopieren in Abschnitt 9, nicht die Erklärungen dazwischen.
    prompts = "\n".join(re.findall(r"```text\n(.*?)```", guide.split("## 9.", 1)[1], flags=re.DOTALL))

    assert "[PHASE]" in prompts
    assert "[KENNUNG]" in prompts
    assert not re.search(r"\bP\d+\b", prompts)
    assert "7d5f673" not in prompts


def _zip_aus_dem_leitfaden(tmp_path) -> zipfile.ZipFile:
    """Erzeugt die ZIP-Datei mit genau dem Befehl aus dem Leitfaden, Schritt 5.

    Nur Zielort und Stand sind anders: der aktuelle Stand statt der Beispielkennung.
    --worktree-attributes: Auch noch nicht übernommene Änderungen an .gitattributes zählen,
    damit ein lokaler Lauf vor dem Commit dasselbe zeigt wie GitHub.
    """
    lines = [line.strip() for line in GUIDE.read_text(encoding="utf-8").splitlines()]
    commands = [line for line in lines if line.startswith("git archive ")]
    assert len(commands) == 1, "Der Leitfaden nennt genau einen Befehl für die ZIP-Datei."
    command = shlex.split(commands[0])
    output_index = command.index("--output") + 1
    archive = tmp_path / "review.zip"
    command[output_index] = str(archive)
    command[-1] = "HEAD"
    command.insert(2, "--worktree-attributes")

    subprocess.run(command, cwd=BASE_DIR, check=True)  # noqa: S603 -- Befehl aus dem eigenen Leitfaden

    return zipfile.ZipFile(archive)


def test_zip_fuer_die_modelle_enthaelt_das_repo_ohne_fremde_bibliotheken(tmp_path):
    names = _zip_aus_dem_leitfaden(tmp_path).namelist()
    for included in ["CLAUDE.md", "CONTRIBUTING.md", "docs/anforderungen.md", "accounts/models.py"]:
        assert included in names
    assert ".env" not in names
    for excluded in ["core/static/core/bootstrap/", "tests/vendor/"]:
        assert not [name for name in names if name.startswith(excluded)], excluded


def test_zip_fuer_die_modelle_ist_unkomprimiert(tmp_path):
    # Beim Review zu P1 konnte Gemini die gepackte ZIP-Datei nicht lesen und sah nur die
    # Dateinamen; die ungepackte desselben Commits schon (#74). Beide Modelle bekommen deshalb
    # dieselbe ungepackte Datei.
    entries = [entry for entry in _zip_aus_dem_leitfaden(tmp_path).infolist() if not entry.is_dir()]

    assert entries
    assert {entry.compress_type for entry in entries} == {zipfile.ZIP_STORED}


def _schritte_fuer_sebastian() -> dict[int, str]:
    """Die nummerierten Schritte aus Abschnitt 6 des Leitfadens, je mit ihrem ganzen Text."""
    section = GUIDE.read_text(encoding="utf-8").split("## 6.", 1)[1].split("\n## ", 1)[0]
    parts = re.split(r"^(\d+)\. ", section, flags=re.MULTILINE)
    return {int(number): text for number, text in zip(parts[1::2], parts[2::2], strict=True)}


def test_vorlage_review_verweist_beim_commit_auf_den_schritt_mit_der_kennung():
    # Die Vorlage verwies beim Review zu P1 auf Schritt 2, die Kennung kommt aber aus dem
    # Schritt mit „git rev-parse HEAD“ (#74). So bleibt der Verweis auch nach neuer Nummerierung richtig.
    steps = _schritte_fuer_sebastian()
    [number] = [number for number, text in steps.items() if "git rev-parse HEAD" in text]
    description = _fields(_load("externes-review.yml"))["commit"]["attributes"]["description"]

    assert re.findall(r"Schritt (\d+)", description) == [str(number)]


def test_rahmen_fuer_berichte_hat_eine_leerzeile_vor_und_nach_dem_bericht():
    # Steht der Bericht direkt unter <summary>, zeigt GitHub die erste Überschrift mit
    # Rautezeichen an (#74). Der Rahmen hält deshalb eine eigene Zeile für den Bericht frei,
    # mit je einer Leerzeile darüber und darunter.
    [frame] = [block for block in re.findall(r"```text\n(.*?)```", GUIDE.read_text(encoding="utf-8"), flags=re.DOTALL)
               if "<details>" in block]
    lines = [line.strip() for line in frame.strip().splitlines()]

    assert lines[0].startswith("<details><summary>") and lines[0].endswith("</summary>")
    assert lines[-1] == "</details>"
    assert lines[1:-1] == ["", lines[2], ""] and lines[2], lines


def test_pruefauftraege_mit_zip_datei_verlangen_einen_hinweis_wenn_sie_nicht_lesbar_ist():
    # Ein Modell, das die ZIP-Datei nicht lesen kann, schreibt sonst einen Bericht ohne
    # Fundstellen, der leicht für gültig gehalten wird (Review zu P1, #74).
    guide = GUIDE.read_text(encoding="utf-8").split("## 9.", 1)[1]
    prompts = [block for block in re.findall(r"```text\n(.*?)```", guide, flags=re.DOTALL) if "ZIP-Datei" in block]

    assert len(prompts) == 3, "Prüfauftrag A, Prüfauftrag B und der strittige Befund bekommen die ZIP-Datei."
    for prompt in prompts:
        assert "ZIP-Datei nicht lesbar" in prompt, prompt[:80]
