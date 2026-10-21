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
        "status",
        "klaerung",
        "entscheidung",
        "abnahmekriterien",
    }
    assert expected <= fields.keys()
    # Klärung, Entscheidung und Abnahmekriterien entstehen erst mit grill-me, alles andere
    # steht beim Anlegen fest.
    must = {"review", "kategorie", "fundstelle", "beobachtung", "beleg", "auswirkung", "sicherheit", "stufe", "status"}
    assert {name for name, field in fields.items() if _required(field)} == must
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


def test_zip_fuer_die_modelle_enthaelt_das_repo_ohne_fremde_bibliotheken(tmp_path):
    # Genau der Befehl aus dem Leitfaden, nur mit anderem Zielort und dem aktuellen Stand statt
    # der Beispielkennung. --worktree-attributes: Auch noch nicht übernommene Änderungen an
    # .gitattributes zählen, damit ein lokaler Lauf vor dem Commit dasselbe zeigt wie GitHub.
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

    names = zipfile.ZipFile(archive).namelist()
    for included in ["CLAUDE.md", "CONTRIBUTING.md", "docs/anforderungen.md", "accounts/models.py"]:
        assert included in names
    assert ".env" not in names
    for excluded in ["core/static/core/bootstrap/", "tests/vendor/"]:
        assert not [name for name in names if name.startswith(excluded)], excluded
