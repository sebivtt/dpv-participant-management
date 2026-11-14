"""Tests für die Arbeitsregeln in CLAUDE.md, CONTRIBUTING.md, den Skills und den Vorlagen (#158, #169, #262, #105).

Die Regeln dürfen umformuliert und verschoben werden, ohne dass ein Test angepasst werden muss.
Deshalb vergleichen diese Tests keine einzelnen Sätze (bis #262 taten sie es, siehe
`docs/entscheidungen.md`, 05.11.2026). Sie prüfen stattdessen, dass Verweise auf Dateien, Abschnitte
und Entscheidungen ins Ziel treffen und dass keine der 38 Kernregeln samt Kennung `<!-- Rnn -->`
still verschwindet (die fünf Tests am Ende). Dazu kommen wenige Prüfungen von Form und Aufbau: dass
jeder Skill auf CLAUDE.md verweist, statt Regeln zu wiederholen (ein Ort je Angabe, #169), die
Überschriften der Skills und die Felder der Vorlagen, und dass es jede Musterdatei für neue Seiten
gibt, die CLAUDE.md nennt (#105). Ob sich eine Session an die Regeln hält und ob
eine Regel inhaltlich schwächer wird, prüfen sie nicht; das prüft das Review.
"""

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
CONTRIBUTING = BASE_DIR / "CONTRIBUTING.md"
README = BASE_DIR / "README.md"
PR_TEMPLATE = BASE_DIR / ".github" / "pull_request_template.md"
ENTSCHEIDUNGEN = BASE_DIR / "docs" / "entscheidungen.md"
GESTALTUNG = BASE_DIR / "docs" / "gestaltung.md"
REVIEW_LEITFADEN = BASE_DIR / "docs" / "review-leitfaden.md"
PHASE_TEMPLATE = BASE_DIR / ".github" / "ISSUE_TEMPLATE" / "phase.yml"
SKILL_DIR = BASE_DIR / ".claude" / "skills"
GRILL_ME = SKILL_DIR / "grill-me" / "SKILL.md"
ISSUE_ANLEGEN = SKILL_DIR / "issue-anlegen" / "SKILL.md"
PHASE_STEUERN = SKILL_DIR / "phase-steuern" / "SKILL.md"
VORSCHAU = SKILL_DIR / "vorschau" / "SKILL.md"
SKILLS = [GRILL_ME, ISSUE_ANLEGEN, PHASE_STEUERN, VORSCHAU]
SETTINGS = BASE_DIR / ".claude" / "settings.json"
HOOK = BASE_DIR / ".claude" / "hooks" / "zusammenfassung.py"

# So viele Wörter in Folge darf ein Skill aus CLAUDE.md übernehmen, ohne dass es als
# wiederholte Regel gilt. Kürzere Folgen sind Verweise und feste Begriffe wie
# „das Label `geklärt`“; ab zehn Wörtern ist es fast immer ein abgeschriebener Satz.
MAX_SHARED_WORDS = 9


def _flat(text):
    return " ".join(text.split())


def _section(path, heading):
    """Text eines Abschnitts (## oder ###) bis zur nächsten Überschrift gleicher oder höherer Ebene."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^(#+) (?:\d+\. )?{re.escape(heading)}[^\n]*\n", text, re.M)
    assert match, f"Abschnitt „{heading}“ fehlt in {path.name}"
    level = len(match.group(1))
    body = re.split(rf"^#{{1,{level}}} ", text[match.end() :], flags=re.M)[0]
    return _flat(body)


def _words(text):
    return re.findall(r"\w+", text.lower())


def _shared_passages(skill, rules, length):
    """Wortfolgen der Länge `length`, die im Skill und in CLAUDE.md gleich vorkommen."""
    rule_words = _words(rules)
    known = {tuple(rule_words[i : i + length]) for i in range(len(rule_words) - length + 1)}
    skill_words = _words(skill)
    return sorted(
        {
            " ".join(skill_words[i : i + length])
            for i in range(len(skill_words) - length + 1)
            if tuple(skill_words[i : i + length]) in known
        }
    )


def _phase_fields():
    template = yaml.safe_load(PHASE_TEMPLATE.read_text(encoding="utf-8"))
    return {field["id"]: field["attributes"] for field in template["body"] if field["type"] != "markdown"}


def _entscheidungen_kopf():
    """Alles vor dem ersten Eintrag (erste Überschrift `## <Jahr>-…`)."""
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    return re.split(r"^## \d{4}-\d{2}-\d{2} ", text, maxsplit=1, flags=re.M)[0]


# --- Skills: Verweis statt Wiederholung, Aufbau ----------------------------------------------


@pytest.mark.parametrize("path", SKILLS, ids=lambda path: path.parent.name)
def test_skill_verweist_auf_claude_md_und_wiederholt_keine_regel(path):
    skill = path.read_text(encoding="utf-8")
    passages = _shared_passages(skill, CLAUDE_MD.read_text(encoding="utf-8"), MAX_SHARED_WORDS + 1)

    assert skill.startswith("---\nname: "), "Kopf mit Name und Beschreibung fehlt"
    assert "`CLAUDE.md`" in skill
    assert not passages, "Aus CLAUDE.md wiederholt, bitte durch einen Verweis ersetzen:\n" + "\n".join(passages)


def test_grill_me_verweist_fuer_die_umsetzung_nur_auf_claude_md():
    after = _section(GRILL_ME, "Danach")

    assert "`CLAUDE.md`" in after
    assert len(after.split()) <= 40, "„Danach“ soll nur verweisen"


def test_grill_me_hat_eine_kurzform_die_sebastian_bestaetigt():
    assert _section(GRILL_ME, "Kurzform"), "Abschnitt „Kurzform“ ist leer"


def test_grill_me_sammelt_die_szenarien_vor_dem_label_geklaert():
    headings = re.findall(r"^## (.+)$", GRILL_ME.read_text(encoding="utf-8"), flags=re.MULTILINE)
    scenarios = next(h for h in headings if "Szenarien" in h)
    release = next(h for h in headings if "Freigeben" in h)

    assert headings.index(scenarios) < headings.index(release)


def test_grill_me_fragt_nach_dem_zielbild_und_fuehrt_die_schritte():
    headings = re.findall(r"^## (.+)$", GRILL_ME.read_text(encoding="utf-8"), flags=re.MULTILINE)
    scenarios = next(h for h in headings if "Szenarien" in h)
    target = next((h for h in headings if "Zielbild" in h), None)
    release = next(h for h in headings if "Freigeben" in h)

    assert target, "Abschnitt zum Zielbild fehlt in grill-me"
    assert headings.index(scenarios) < headings.index(target) < headings.index(release)


def test_issue_anlegen_traegt_neue_issues_der_laufenden_phase_ins_phasen_issue_ein():
    assert "Phasen-Issue" in _section(ISSUE_ANLEGEN, "Laufende Phase")


def test_phase_steuern_hat_die_handgriffe_fuer_die_ganze_phase():
    text = PHASE_STEUERN.read_text(encoding="utf-8")
    headings = " ".join(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))

    assert "name: phase-steuern" in text
    for step in ["Phasenstart", "Aufträge", "Phasen-Issue pflegen", "Übergabe", "Abschluss"]:
        assert step in headings, step
    assert "phase.yml" in text


def test_grill_me_bittet_sebastian_um_geklaert_statt_es_selbst_zu_setzen():
    text = GRILL_ME.read_text(encoding="utf-8")

    assert not re.search(r"labels\[\]=geklärt|(--add-label|--label|-l)[ =]\S*geklärt", text), "Befehl setzt `geklärt`"


def test_befehle_im_skill_nennen_den_namen_des_laufs_aus_der_pruefung_auf_github():
    name = re.search(r"^name: (.+)$", (BASE_DIR / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"), flags=re.M).group(1)

    assert f'gh run list --workflow "{name}"' in PHASE_STEUERN.read_text(encoding="utf-8")


def test_skill_vorschau_hat_kopf_und_vier_schritte():
    text = VORSCHAU.read_text(encoding="utf-8")
    kopf = text.split("---", 2)[1]
    ueberschriften = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)

    assert "name: vorschau" in kopf
    assert ueberschriften == ["1. Fälle wählen", "2. Datei erzeugen", "3. Zeigen", "4. Antwort festhalten"]


# --- Vorlagen --------------------------------------------------------------------------------


def test_vorlage_fuer_pull_requests_fragt_nach_den_szenarien():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    checks = text.split("## Wie geprüft wurde", 1)[1].split("\n## ", 1)[0]
    first = next(line for line in checks.splitlines() if line.startswith("- "))

    assert first.startswith("- Szenarien")
    assert "„Szenarien (Datum)“" in first


def test_vorlage_hat_die_zeile_test_commit_hinter_der_szenarien_zeile_und_erklaert_sie():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    checks = text.split("## Wie geprüft wurde", 1)[1].split("\n## ", 1)[0]
    zeilen = [line for line in checks.splitlines() if line.startswith("- ")]

    assert zeilen[0].startswith("- Szenarien")
    assert zeilen[1] == "- Test-Commit:"


def test_vorlage_fuer_pull_requests_hat_nachziehen_vor_der_unabhaengigen_pruefung():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    rauchtest, nachziehen, pruefung = "- Rauchtest des Hauptablaufs:", "- Nachziehen (", "- Unabhängige Prüfung:"

    assert all(zeile in text for zeile in (rauchtest, nachziehen, pruefung))
    assert text.index(rauchtest) < text.index(nachziehen) < text.index(pruefung)


def test_vorlage_hat_den_abschnitt_vorschau_zwischen_nutzende_und_zielbild():
    ueberschriften = re.findall(r"^## (.+)$", PR_TEMPLATE.read_text(encoding="utf-8"), flags=re.MULTILINE)

    assert ueberschriften.index("Was sich für Nutzende ändert") + 1 == ueberschriften.index("Vorschau")
    assert ueberschriften.index("Vorschau") + 1 == ueberschriften.index("Zielbild")


def test_vorlage_phase_hat_reihenfolge_abschlusskriterien_und_stand():
    fields = _phase_fields()

    template = yaml.safe_load(PHASE_TEMPLATE.read_text(encoding="utf-8"))
    types = {field["id"]: field for field in template["body"] if field["type"] != "markdown"}

    assert {"phase", "reihenfolge", "abschlusskriterien", "stand"} <= fields.keys()
    assert fields["stand"]["label"] == "Stand für die nächste Steuerungssession"
    assert types["phase"]["type"] == "dropdown"
    assert fields["phase"]["options"] == [f"P{n}" for n in range(11)]
    for name in ["phase", "reihenfolge", "abschlusskriterien"]:
        assert types[name].get("validations", {}).get("required") is True, name


def test_vorlage_phase_reihenfolge_nur_als_issue_nummern():
    example = _phase_fields()["reihenfolge"]["placeholder"]
    lines = [line.strip() for line in example.splitlines() if line.strip()]

    assert lines
    assert all(re.fullmatch(r"\d+\. #\d+", line) for line in lines), lines


def test_vorlage_phase_abschlusskriterien_als_haekchen_mit_beleg_und_verweis():
    attributes = _phase_fields()["abschlusskriterien"]
    lines = [line.strip() for line in attributes["placeholder"].splitlines() if line.strip()]

    assert "`docs/fahrplan.md`" in attributes["description"]
    assert lines
    assert all(line.startswith("- [") and "Beleg:" in line for line in lines), lines


def test_vorlage_phase_kennt_kein_geklaert_als_text():
    # Ob ein Issue geklärt ist, zeigt allein das Label; das Phasen-Issue vermerkt es nicht.
    for name, attributes in _phase_fields().items():
        for key in ["label", "description", "placeholder"]:
            assert "geklärt" not in attributes.get(key, ""), (name, key)


# --- Einstellungen für Claude Code (#233, #240) ------------------------------------------------


def test_settings_sperrt_env_und_uebernehmen_und_bindet_den_pruefschritt_ein():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = [hook for entry in settings["hooks"]["PreToolUse"] if entry["matcher"] == "Bash" for hook in entry["hooks"]]

    assert {"Read(./.env)", "Read(./**/.env)", "Bash(gh pr merge:*)"} <= set(settings["permissions"]["deny"])
    # Der Pfad über $CLAUDE_PROJECT_DIR gilt auch, wenn die Sitzung in einem Unterordner arbeitet.
    # „|| exit 2“: Auch wenn der Prüfschritt selbst scheitert, weist Claude Code den Befehl ab.
    assert any(hook["command"] == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/sperren.py" || exit 2' for hook in hooks)
    assert (BASE_DIR / ".claude" / "hooks" / "sperren.py").is_file()


def test_settings_schaltet_die_memory_ab_und_bindet_den_hook_zum_zusammenfassen_ein():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))

    assert settings["autoMemoryEnabled"] is False
    entries = [entry for entry in settings["hooks"]["SessionStart"] if entry["matcher"] == "compact"]
    commands = [hook["command"] for entry in entries for hook in entry["hooks"]]
    assert any("$CLAUDE_PROJECT_DIR/.claude/hooks/zusammenfassung.py" in command for command in commands)
    # Die bisherigen Einträge bleiben.
    assert {"Read(./.env)", "Read(./**/.env)", "Bash(gh pr merge:*)"} <= set(settings["permissions"]["deny"])
    assert any(entry["matcher"] == "Bash" for entry in settings["hooks"]["PreToolUse"])
    assert HOOK.is_file()


# --- Übersicht der Grundsätze in docs/entscheidungen.md (#244) ----------------------------------


def test_entscheidungen_hat_oben_die_uebersicht_geltende_grundsaetze():
    assert "## Geltende Grundsätze" in _entscheidungen_kopf()
    assert "| Thema | Gilt | Ersetzt |" in _entscheidungen_kopf()


def test_uebersicht_enthaelt_den_anfangsbestand_nur_als_verweis():
    # Neue und fortgeschriebene Zeilen sind erlaubt (CLAUDE.md); geprüft wird nur die Form der Tabelle:
    # Jede Zeile hat drei gefüllte Zellen.
    zeilen = [z for z in _entscheidungen_kopf().splitlines() if z.startswith("| ") and not z.startswith(("| Thema", "| ---"))]
    zellen = [[z.strip() for z in zeile.strip("|").split("|")] for zeile in zeilen]

    assert zellen, "Übersicht fehlt"
    assert all(len(zeile) == 3 and all(zeile) for zeile in zellen), zellen


def test_uebersicht_verweist_nur_auf_vorhandene_eintraege():
    entries = re.split(r"^## (?=\d{4}-\d{2}-\d{2} · )", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)[1:]
    zeilen = [z for z in _entscheidungen_kopf().splitlines() if z.startswith("| ") and not z.startswith(("| Thema", "| ---"))]
    assert zeilen, "Übersicht fehlt"
    for zeile in zeilen:
        gilt, ersetzt = [zelle.strip() for zelle in zeile.strip("|").split("|")[1:]]
        for tag, monat, jahr, _, nummer in re.findall(r"(\d{2})\.(\d{2})\.(\d{4})(, #(\d+))?", f"{gilt} {ersetzt}"):
            vom_tag = [e for e in entries if e.startswith(f"{jahr}-{monat}-{tag} · ")]
            assert vom_tag, f"{zeile}: kein Eintrag vom {tag}.{monat}.{jahr}"
            if nummer:
                assert any(re.search(rf"#{nummer}\b", e) for e in vom_tag), f"{zeile}: #{nummer} fehlt am {tag}.{monat}.{jahr}"


# --- Musterdateien für neue Seiten (#105) -----------------------------------------------------
#
# Der Abschnitt in CLAUDE.md nennt die Dateien, nach deren Vorbild neue Seiten entstehen. Nach einer
# Umbenennung soll er nicht unbemerkt ins Leere zeigen. Strenger als der Test
# test_dateien_und_ordner_in_backticks_gibt_es_im_repo weiter unten: Jede Angabe mit „/“ oder einer
# Endung aus DATEIENDUNGEN ist ein voller Pfad ab dem Wurzelordner, den Git verfolgt; ein bloßer
# Dateiname gilt hier nicht, damit klar ist, welche Datei gemeint ist. Welche Datei als Muster taugt,
# prüft das Review.

MUSTER_ABSCHNITT = "Musterdateien für neue Seiten"


def _verfolgte_dateien():
    befehl = ["git", "ls-files"]
    return set(subprocess.run(befehl, cwd=BASE_DIR, capture_output=True, text=True, check=True).stdout.splitlines())  # noqa: S603 -- fester Befehl


def _fehlende_musterdateien(text, verfolgt):
    """Die Punkte des Abschnitts ohne Datei und die genannten Pfade, die Git nicht verfolgt."""
    punkte = [zeile for zeile in text.splitlines() if zeile.startswith("- ")]
    ohne_datei, fehlt = [], []
    for punkt in punkte:
        # Mit „/“ zählt jede Angabe als Pfad, damit auch eine verstümmelte Endung („config/urls.p“) auffällt.
        pfade = [angabe for angabe in re.findall(r"`([^`\n]+)`", punkt)
                 if "/" in angabe or Path(angabe).suffix in DATEIENDUNGEN]
        if not pfade:
            ohne_datei.append(punkt[:60])
        fehlt += [pfad for pfad in pfade if pfad not in verfolgt]
    return punkte, ohne_datei, fehlt


def _muster_text():
    text = CLAUDE_MD.read_text(encoding="utf-8")
    match = re.search(rf"^## {re.escape(MUSTER_ABSCHNITT)}\n(.*?)(?=^## )", text, flags=re.M | re.S)
    assert match, f"Abschnitt „{MUSTER_ABSCHNITT}“ fehlt in CLAUDE.md"
    return match.group(1)


def test_jede_musterdatei_fuer_neue_seiten_gibt_es():
    punkte, ohne_datei, fehlt = _fehlende_musterdateien(_muster_text(), _verfolgte_dateien())

    assert punkte, "Der Abschnitt nennt keine Musterdateien"
    assert not ohne_datei, f"Diese Punkte nennen keine Datei: {ohne_datei}"
    assert not fehlt, f"Diese Musterdateien gibt es nicht (umbenannt oder gelöscht?): {fehlt}"


@pytest.mark.parametrize("anders", ["_gibt_es_nicht.py", ".p"], ids=["anderer_name", "verstuemmelte_endung"])
def test_gegenprobe_ein_falscher_pfad_bei_den_musterdateien_wird_gemeldet(anders):
    text = _muster_text()
    # Ein Pfad aus der Liste, nicht aus der Einleitung davor.
    pfad = re.search(r"^- .*?`([^`\n]+\.py)`", text, flags=re.M).group(1)
    falsch = text.replace(f"`{pfad}`", f"`{pfad[:-3]}{anders}`", 1)

    _punkte, _ohne_datei, fehlt = _fehlende_musterdateien(falsch, _verfolgte_dateien())

    assert fehlt == [f"{pfad[:-3]}{anders}"]


# --- Verweise und Kennungen statt fester Sätze (#262) -----------------------------------------
#
# Diese fünf Tests schützen die Regeln, ohne einen Wortlaut festzuhalten: Eine Regel darf
# umformuliert und verschoben werden. Rot wird nur, wenn ein Verweis ins Leere geht oder eine
# Kernregel samt Kennung verschwindet. Nicht geprüft wird, ob eine Regel inhaltlich schwächer wird
# und ob ein Punkt unter dem richtigen Elternabschnitt steht; das prüft das Review.

VERWEISDATEIEN = [CLAUDE_MD, CONTRIBUTING, README, PR_TEMPLATE, *SKILLS, GESTALTUNG, REVIEW_LEITFADEN]
REGELDATEIEN = [CLAUDE_MD, CONTRIBUTING, *SKILLS]
# Als Datei oder Ordner gilt eine Angabe in Backticks mit diesen Endungen oder mit „/“ am Ende;
# alles andere (Benutzernamen wie `ohne.mail`, Adressen wie `search/issues`) ist kein Verweis.
DATEIENDUNGEN = {".md", ".py", ".yml", ".json", ".html", ".svg", ".js", ".css", ".sh", ".toml", ".lock", ".example"}
# Einzige Ausnahme: CONTRIBUTING.md meint damit einen Ordner des alten Repos.
KEIN_VERWEIS = {"backend/notifications/"}


def _ohne_codebloecke(path):
    return re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)


def test_dateien_und_ordner_in_backticks_gibt_es_im_repo():
    befehl = ["git", "ls-files"]
    verfolgt = subprocess.run(befehl, cwd=BASE_DIR, capture_output=True, text=True, check=True).stdout  # noqa: S603 -- fester Befehl
    namen = Counter(Path(zeile).name for zeile in verfolgt.splitlines())
    uebersprungen, fehlt = 0, []

    for path in VERWEISDATEIEN:
        for angabe in re.findall(r"`([^`\n]+)`", _ohne_codebloecke(path)):
            if re.search(r"[<*…\s]", angabe) or angabe.startswith(("/", "http")):
                uebersprungen += 1
            elif (angabe.endswith("/") or Path(angabe).suffix in DATEIENDUNGEN) and angabe not in KEIN_VERWEIS:
                ziel = angabe.removeprefix("./")
                # Ein bloßer Name gilt, wenn er im Wurzelordner steht oder genau einmal im Repo vorkommt.
                if not (BASE_DIR / ziel).exists() and not ("/" not in ziel.rstrip("/") and namen[ziel] == 1):
                    fehlt.append(f"{path.name}: `{angabe}`")

    print(f"{uebersprungen} Angaben übersprungen (mit <, *, …, Leerzeichen, Anfang / oder http)")  # noqa: T201 -- Zahl für den Bericht
    assert not fehlt, f"Diese Dateien oder Ordner gibt es nicht ({uebersprungen} Angaben übersprungen): {fehlt}"


def _gliederung(path):
    """Überschriften (mit ihrer Nummer) und fette Punkte eines Dokuments, ohne Codeblöcke."""
    text = _ohne_codebloecke(path)
    nummern, namen = set(), set()
    for nummer, name in re.findall(r"^#+ (?:(\d+)\. )?(.+)$", text, flags=re.M):
        namen.add(name.strip())
        if nummer:
            nummern.add(int(nummer))
    namen |= {name.strip().rstrip(":,.") for name in re.findall(r"\*\*([^*]+)\*\*", text)}
    return nummern, namen


# Verweis auf eine der drei Dateien samt allem, was danach als Ziel folgt: Namen in „…“, „Abschnitt n“
# oder ein Schritt von „Ablauf je Aufgabe“, auch mehrere hintereinander, in Klammern und ohne Backticks.
_ZIEL = re.compile(
    r"[,;]? ?\(?(?:vor allem )?(?:(?:unter|im|in|und) )?(?:Punkt |Abschnitte? )?"
    r"(?:„Ablauf je Aufgabe“, Schritt (?P<schritt1>\d+)|Ablauf je Aufgabe Nr\. (?P<schritt2>\d+)|„(?P<name>[^“]+)“|Abschnitt (?P<nummer>\d+))"
)
_ZIELDATEIEN = {"CLAUDE.md": CLAUDE_MD, "CONTRIBUTING.md": CONTRIBUTING, "README.md": README}


def test_verweise_auf_abschnitte_treffen_eine_ueberschrift_oder_einen_fetten_punkt():
    fehlt = []

    for path in VERWEISDATEIEN:
        text = path.read_text(encoding="utf-8")
        for treffer in re.finditer(r"(?<![\w/.-])`?(CLAUDE\.md|CONTRIBUTING\.md|README\.md)`?", text):
            nummern, namen = _gliederung(_ZIELDATEIEN[treffer.group(1)])
            ort = treffer.end()
            while ziel := _ZIEL.match(text, ort):
                ort = ziel.end()
                name, nummer, schritt = ziel["name"], ziel["nummer"], ziel["schritt1"] or ziel["schritt2"]
                if name and name not in namen:
                    fehlt.append(f"{path.name}: {treffer.group(1)}, „{name}“")
                if nummer and int(nummer) not in nummern:
                    fehlt.append(f"{path.name}: {treffer.group(1)}, Abschnitt {nummer}")
                if schritt and not re.search(rf"(?:^| ){schritt}\. \*\*", _section(CLAUDE_MD, "Ablauf je Aufgabe")):
                    fehlt.append(f"{path.name}: Ablauf je Aufgabe Nr. {schritt}")

    # Ein „Abschnitt n“ ohne Dateiangabe meint in einem Skill dessen eigene Überschrift n.
    for skill in SKILLS:
        text = _ohne_codebloecke(skill)
        eigene, _ = _gliederung(skill)
        for treffer in re.finditer(r"Abschnitt (\d+)", text):
            if not text[: treffer.start()].rstrip(" ,").endswith("`") and int(treffer.group(1)) not in eigene:
                fehlt.append(f"{skill.parent.name}: Abschnitt {treffer.group(1)}")

    assert not fehlt, f"Diese Verweise treffen keinen Abschnitt: {fehlt}"


_ENTSCHEIDUNG = re.compile(r"(?:entscheidungen\.md`?,? (?:Eintrag vom )?|Entscheidung vom )(\d{2})\.(\d{2})\.(\d{4})(?:,? (?:zu )?#(\d+))?")


def _eintraege():
    """Kopfzeilen der Einträge in docs/entscheidungen.md; die Übersicht oben ist kein Eintrag."""
    kopfzeilen = re.findall(r"^## (.+)$", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)
    return [kopf for kopf in kopfzeilen if kopf != "Geltende Grundsätze"]


def test_verweise_auf_entscheidungen_treffen_einen_eintrag_des_tages():
    eintraege = _eintraege()
    fehlt = []

    assert all(re.match(r"\d{4}-\d{2}-\d{2} · \S", kopf) for kopf in eintraege), "Kopfzeile ohne „JJJJ-MM-TT · …“"
    for path in VERWEISDATEIEN:
        for tag, monat, jahr, nummer in _ENTSCHEIDUNG.findall(path.read_text(encoding="utf-8")):
            vom_tag = [kopf for kopf in eintraege if kopf.startswith(f"{jahr}-{monat}-{tag} · ")]
            if not vom_tag:
                fehlt.append(f"{path.name}: kein Eintrag vom {tag}.{monat}.{jahr}")
            elif nummer and not any(re.search(rf"#{nummer}\b", kopf) for kopf in vom_tag):
                fehlt.append(f"{path.name}: #{nummer} fehlt am {tag}.{monat}.{jahr}")

    assert not fehlt, f"Diese Verweise treffen keinen Eintrag: {fehlt}"


# Diese Einträge schützen heute Regeln; ihre Kopfzeilen ändern sich nie (CLAUDE.md).
GESCHUETZTE_EINTRAEGE = [161, 162, 176, 235, 237, 239, 240, 244, 245, 249]


def test_die_eintraege_zu_den_geschuetzten_regeln_gibt_es():
    fehlt = [n for n in GESCHUETZTE_EINTRAEGE if not any(re.search(rf"#{n}\b", kopf) for kopf in _eintraege())]

    assert not fehlt, f"In docs/entscheidungen.md fehlen die Einträge zu {fehlt}"


# Die Kernregeln, die eine Kennung `<!-- Rnn -->` hinter ihrem Satz tragen (#262). Geschützt ist die
# Regel, nicht ihr Wortlaut: Die Kennung geht mit, wenn die Regel wandert.
KENNUNGEN = {
    "R01": "Ein Ort je Angabe",
    "R02": "Texte der KI enthalten nur Verweise",
    "R03": "Phasenstart",
    "R04": "Klären läuft voraus",
    "R05": "Neuer Inhalt zu einem geklärten Issue",
    "R06": "Rückblick streicht zuerst",
    "R07": "Issue „Aufräumen“ ab P3",
    "R08": "Roter Lauf auf `main` geht vor",
    "R09": "Steuerungssession entscheidet nichts Fachliches",
    "R10": "Freigaben gibt nur Sebastian",
    "R11": "Auftrag ist nur Link und Verweis",
    "R12": "Wechsel der Steuerungssession",
    "R13": "Frische Session je Issue",
    "R14": "Szenarien vor Code",
    "R15": "Ohne Szenarien nur mit Klärung",
    "R16": "Ohne Szenarien anhalten",
    "R17": "Zielbild vor Gestaltung",
    "R18": "Zielbild ist Orientierung, nur erfundene Daten",
    "R19": "Ohne Zielbild anhalten",
    "R20": "Passt ein Baustein nicht, fragen",
    "R21": "Vorschau vor der Prüfung",
    "R22": "Nachziehen",
    "R23": "Test-Commit vor dem Code",
    "R24": "Prüfumfang passend zur Änderung",
    "R25": "Unabhängige Prüfung einmal, zweite nur nach „hoch“",
    "R26": "Umfang der unabhängigen Prüfung",
    "R27": "Schweregrade nach der Folge",
    "R28": "Fremder Fehler wird eigenes Issue",
    "R29": "Selbst warten, Link erst bei Grün",
    "R30": "Neustart nach gescheiterter Browser-Installation",
    "R31": "Neustarts werden gezählt",
    "R32": "Sperren nie umgehen, andere Werkzeuge nur lesend",
    "R33": "Ersetzender Eintrag nennt den älteren",
    "R34": "Prüfbedingung nicht lockern",
    "R35": "Kopf „Für Sebastian“ mit „vorher / nachher“",
    "R36": "Was bleibt unverändert",
    "R37": "Kurzform nur mit Sebastians Bestätigung",
    "R38": "Vorübergehenden Vorschau-Test löschen",
}


def test_jede_kernregel_hat_ihre_kennung_genau_einmal_hinter_ihrem_satz():
    gefunden, zu_kurz = {}, []

    for path in REGELDATEIEN:
        for zeile in path.read_text(encoding="utf-8").splitlines():
            davor = 0
            for treffer in re.finditer(r"<!-- (R\d+) -->", zeile):
                woerter = len(re.findall(r"\w+", zeile[davor : treffer.start()]))
                gefunden.setdefault(treffer.group(1), []).append(path.name)
                if woerter < 5:
                    zu_kurz.append(f"{treffer.group(1)} in {path.name} (nur {woerter} Wörter davor)")
                davor = treffer.end()

    fehlt = sorted(set(KENNUNGEN) - set(gefunden))
    mehrfach = sorted(kennung for kennung, orte in gefunden.items() if len(orte) > 1)
    unbekannt = sorted(set(gefunden) - set(KENNUNGEN))
    hinweis = (
        "Wird die Regel verschoben, geht die Kennung mit; wird sie bewusst gestrichen, kommt die Kennung aus der "
        "Liste KENNUNGEN in tests/test_arbeitsregeln.py, und der Pull Request nennt das."
    )
    assert not (fehlt or mehrfach or unbekannt or zu_kurz), (
        f"Kennungen fehlen: {[f'{k} ({KENNUNGEN[k]})' for k in fehlt]}; mehrfach: {mehrfach}; "
        f"unbekannt: {unbekannt}; zu dicht hinter der vorigen: {zu_kurz}. {hinweis}"
    )
