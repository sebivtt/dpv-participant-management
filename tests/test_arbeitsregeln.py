"""Tests für die Arbeitsregeln in CLAUDE.md, den Skills und den Vorlagen (#158, #162, #169, #176).

Diese Tests sorgen dafür, dass die Kernregeln nicht still aus CLAUDE.md verschwinden, dass die
Skills auf CLAUDE.md verweisen, statt Regeln zu wiederholen (ein Ort je Angabe, #169), und dass
die Vorlagen ihre Felder haben. Ob sich eine Session an die Regeln hält, prüfen sie nicht.

Bis #169 hieß die Datei `test_szenarien_vor_code.py` und verlangte die Regeln zu „Szenarien vor
Code“ zusätzlich in grill-me. Seit #169 stehen sie nur in CLAUDE.md und der Vorlage für Pull
Requests; grill-me verweist darauf (`docs/entscheidungen.md`, 26.10.2026). Für „Zielbild vor
Gestaltung“ (#162) hat grill-me die Handgriffe, die Regel selbst steht in CLAUDE.md.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
PR_TEMPLATE = BASE_DIR / ".github" / "pull_request_template.md"
ENTSCHEIDUNGEN = BASE_DIR / "docs" / "entscheidungen.md"
GESTALTUNG = BASE_DIR / "docs" / "gestaltung.md"
PHASE_TEMPLATE = BASE_DIR / ".github" / "ISSUE_TEMPLATE" / "phase.yml"
SKILL_DIR = BASE_DIR / ".claude" / "skills"
GRILL_ME = SKILL_DIR / "grill-me" / "SKILL.md"
ISSUE_ANLEGEN = SKILL_DIR / "issue-anlegen" / "SKILL.md"
PHASE_STEUERN = SKILL_DIR / "phase-steuern" / "SKILL.md"
VORSCHAU = SKILL_DIR / "vorschau" / "SKILL.md"
SKILLS = [GRILL_ME, ISSUE_ANLEGEN, PHASE_STEUERN, VORSCHAU]

# So viele Wörter in Folge darf ein Skill aus CLAUDE.md übernehmen, ohne dass es als
# wiederholte Regel gilt. Kürzere Folgen sind Verweise und feste Begriffe wie
# „das Label `geklärt`“; ab zehn Wörtern ist es fast immer ein abgeschriebener Satz.
MAX_SHARED_WORDS = 9


def _flat(text):
    return " ".join(text.split())


def _text(path):
    return _flat(path.read_text(encoding="utf-8"))


def _section(path, heading):
    """Text eines Abschnitts (## oder ###) bis zur nächsten Überschrift gleicher oder höherer Ebene."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^(#+) (?:\d+\. )?{re.escape(heading)}[^\n]*\n", text, re.M)
    assert match, f"Abschnitt „{heading}“ fehlt in {path.name}"
    level = len(match.group(1))
    body = re.split(rf"^#{{1,{level}}} ", text[match.end() :], flags=re.M)[0]
    return _flat(body)


def _sentence_after(text, start):
    match = re.search(re.escape(start) + r"[^.]*\.(?:[^.]*\.){0,2}", text)
    assert match, f"Regel fehlt: {start}"
    return match.group(0)


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


# --- CLAUDE.md: Kernregeln -------------------------------------------------------------------


# Je Angabe der Ort, der für sie zuständig ist, so wie #169 sie zuordnet.
PLACES = {
    "Was gilt": ["`docs/anforderungen.md`", "`docs/rechtematrix.md`"],
    "Warum": ["`docs/entscheidungen.md`"],
    "Phasen, Abschlusskriterien, Stunden": ["`docs/fahrplan.md`"],
    "Arbeitsregeln": ["diese Datei"],
    "Handgriffe": ["Skills"],
    "Was ein Issue verlangt": ["Text des Issues"],
    "Ob ein Issue geklärt ist": ["Label `geklärt`"],
    "Ob ein Issue erledigt ist": ["geschlossen"],
    "Reihenfolge einer Phase und Belege der Abschlusskriterien": ["Phasen-Issue", "Issue-Nummern"],
    "Was technisch zuerst da sein muss": ["Abhängigkeiten auf GitHub"],
}


def test_ein_ort_je_angabe_ordnet_jeder_angabe_ihren_ort_zu():
    section = _section(CLAUDE_MD, "Ein Ort je Angabe")
    entries = dict(re.findall(r"- \*\*(.+?):\*\* (.*?)(?= - \*\*|$)", section))

    assert entries.keys() == PLACES.keys()
    for topic, places in PLACES.items():
        for place in places:
            assert place in entries[topic], (topic, place)
    assert "verweisen nur darauf" in section
    assert "Kommentare sind nur Protokoll" in section
    assert "Eine Reihenfolge ohne technischen Grund steht nur im Phasen-Issue" in section


def test_ablauf_einer_phase_von_start_bis_abschluss():
    section = _section(CLAUDE_MD, "Ablauf einer Phase")

    for part in ["**Start:**", "**Klären läuft voraus:**", "**Umsetzen:**", "**Neues während der Phase:**"]:
        assert part in section, part
    start = _sentence_after(section, "**Start:**")
    assert "Phasen-Issue nach Vorlage" in start
    assert "Widersprüche legt sie Sebastian mit Vorschlag vor" in start
    assert "mit `issue-anlegen`" in start
    assert "Zuerst werden die Grundlagen geklärt" in section
    assert "zweite KI prüft die Planung, bevor die erste Umsetzung beginnt" in section
    assert "nächsten drei Issues" in section
    assert "spätestens in Klärung, wenn die Umsetzung der laufenden beginnt" in section
    assert "etwa zwei Gruppen vorher" in section
    assert "Zielbild" in _sentence_after(section, "**Klären läuft voraus:**"), "Vorlauf für Zielbilder fehlt"
    assert "nur sein Häkchen mit Beleg" in section
    assert "Stunden aus dem Puffer, die Stunden nur mit Sebastians Zustimmung" in section
    assert "sofort in den Text des Issues, das Label `geklärt` kommt ab" in section
    # Abschluss in dieser Reihenfolge: Belege, Review, Rückblick, erst dann der „Stand“.
    closing = section.split("**Abschluss:**", 1)[1]
    order = ["Beleg", "externe Review", "Rückblick", "„Stand“"]
    positions = [closing.find(step) for step in order]
    assert -1 not in positions, dict(zip(order, positions, strict=True))
    assert positions == sorted(positions)


def test_steuerungssession_entscheidet_nichts_fachliches_und_wechselt_rechtzeitig():
    section = _section(CLAUDE_MD, "Steuerungssession und Umsetzungs-Sessions")

    assert "entscheidet nichts Fachliches" in section
    assert "in seinen eigenen Worten im Issue oder Pull Request" in section
    assert "„Setze #123 um, nach `CLAUDE.md`.“" in section
    assert "Was sonst wichtig ist, steht vorher im Issue" in section
    rule = _sentence_after(section, "**Wechsel der Steuerungssession:**")
    assert "Sie wechselt nach jedem Issue, dessen Pull Request übernommen und im Phasen-Issue eingetragen ist" in rule
    assert "nie mitten in einer Umsetzung" in section
    assert "Issues ohne Pull Request (Klärungen, Sammel-Issues) lösen keinen Wechsel aus" in section
    assert "mit allem, was noch läuft (Klärungen, wartende Pull Requests, Hintergrundaufträge)" in section
    assert "beginnt sie nichts Neues mehr, schreibt sofort den Stand ins Phasen-Issue und endet" in section
    assert "ein Hook erinnert sie daran" in section
    assert "automatisch zusammen" in section
    assert "%" not in section, "Prozentangaben der Kontextanzeige sind ersetzt (#240)"


def test_umsetzung_in_einer_frischen_session_je_issue():
    section = _section(CLAUDE_MD, "Steuerungssession und Umsetzungs-Sessions")
    rule = _sentence_after(section, "**Umsetzungs-Sessions:**")

    assert "frischen Session für genau ein Issue" in rule
    assert "kein weiteres" in rule
    assert "Fasst Claude Code das Gespräch trotzdem automatisch zusammen (Notfall), beginnt sie nichts Neues mehr" in rule
    assert "mit einem laufenden Prüflauf oder Hintergrundauftrag, der Arbeitskopie und dem letzten Commit" in rule
    assert "als Kommentar ins Issue" in rule
    assert "endet, sobald der Lauf beendet oder sein Ergebnis vermerkt ist" in rule
    assert "Eine neue Session prüft zuerst, ob in derselben Arbeitskopie noch ein Lauf läuft" in rule
    assert "macht dann mit genau diesem Issue weiter" in rule
    assert "%" not in rule


def test_ohne_szenarien_haelt_die_ki_an_auch_wenn_der_auftrag_den_schritt_nicht_nennt():
    rule = _sentence_after(_text(CLAUDE_MD), "Direkt vor dem Start prüft die KI außerdem")

    assert "„Szenarien (Datum)“" in rule
    assert "hält sie an" in rule
    assert "statt mit Tests oder Code zu beginnen" in rule
    assert "auch, wenn der Auftrag den Schritt nicht nennt" in rule
    assert "ein Auftrag hebt ihn nie auf" in rule


def test_ohne_szenarien_nur_wenn_die_klaerung_kein_fachliches_verhalten_festhaelt():
    step = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    rule = step.split("Ohne Szenarien geht nur ein Issue", 1)[-1].split("\n", 1)[0][:300]

    assert "Ohne Szenarien geht nur ein Issue" in step
    assert "die Klärung festhält, dass es kein fachliches Verhalten hat" in rule
    assert "Fehlt diese Angabe, sind Szenarien nötig" in rule


def _zielbild_rule():
    section = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    assert "**Zielbild vor Gestaltung:**" in section, "Regel „Zielbild vor Gestaltung“ fehlt"
    return section.split("**Zielbild vor Gestaltung:**", 1)[1].split("Für die Umsetzung gilt außerdem", 1)[0]


def test_zielbild_noetig_bei_neuer_seite_oder_neuem_sichtbarem_baustein():
    rule = _zielbild_rule()

    assert "neue Seite mit eigener Adresse" in rule
    assert "neuen sichtbaren gemeinsamen Baustein für den Bausteinkatalog" in rule
    assert "Zielbild von Sebastian" in rule
    # Neuer Abschnitt einer bestehenden Seite: Sebastian wird gefragt; Proben und Erweiterungen ohne.
    assert "neuen Abschnitt einer bestehenden Seite" in rule
    assert "#100 bis #102" in rule
    assert "Entscheidung F1" in rule
    assert "reine Erweiterungen bestehender Seiten" in rule


def test_zielbild_reihenfolge_bis_geklaert():
    rule = _zielbild_rule()
    assert "in dieser Reihenfolge:" in rule
    steps = rule.split("in dieser Reihenfolge:", 1)[1]
    order = ["Szenarien", "grober Entwurf", "Zielbild", "Nachklärung", "`geklärt`"]
    positions = [steps.find(step) for step in order]

    assert -1 not in positions, dict(zip(order, positions, strict=True))
    assert positions == sorted(positions)
    assert "von der klärenden Session als Kommentar im Issue" in rule
    assert "als Kommentar mit Prüfsumme im Issue" in rule
    assert "jede Abweichung einzeln mit Sebastian" in rule
    assert "Issue und Szenarien angepasst" in rule


def test_zielbild_ist_orientierung_mit_erfundenen_daten_unter_docs_zielbilder():
    rule = _zielbild_rule()

    assert "Orientierung für das Aussehen, keine Anforderung" in rule
    for first in ["Rechtematrix", "Anforderungen", "Entscheidungen", "`docs/gestaltung.md`"]:
        assert first in rule, first
    assert "als Abweichung genannt" in rule
    assert "nur erfundene Daten" in rule
    assert "`docs/zielbilder/`" in rule
    assert "`docs/zielbilder/README.md`" in rule


def test_ohne_noetiges_zielbild_haelt_die_ki_vor_dem_start_an():
    section = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    rule = _sentence_after(section.split("Für die Umsetzung gilt außerdem", 1)[1], "Braucht das Issue ein Zielbild")

    assert "direkt vor dem Start" in rule
    assert "hält sie an" in rule
    assert "nur Link und Verweis" in rule


# --- Skills: Verweis statt Wiederholung ------------------------------------------------------


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
    short = _section(GRILL_ME, "Kurzform")

    assert "höchstens einem neuen Punkt" in short
    assert "ohne fachliches Verhalten" in short
    assert "Abhängigkeiten" in short
    for kept in ["Fragen", "Zusammenfassung", "Protokoll", "Szenarien"]:
        assert kept in short, kept
    assert "Sebastian bestätigt" in short
    assert "volle Klärung" in short


def test_grill_me_sammelt_die_szenarien_vor_dem_label_geklaert():
    text = GRILL_ME.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    scenarios = next(h for h in headings if "Szenarien" in h)
    release = next(h for h in headings if "Freigeben" in h)

    assert "**Fachliches Verhalten:**" in text
    assert headings.index(scenarios) < headings.index(release)
    release_text = _section(GRILL_ME, release)
    assert "„Szenarien (Datum)“" in release_text
    assert "keine Szenarien braucht" in release_text


def test_grill_me_fragt_nach_dem_zielbild_und_fuehrt_die_schritte():
    text = GRILL_ME.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    scenarios = next(h for h in headings if "Szenarien" in h)
    target = next((h for h in headings if "Zielbild" in h), None)
    release = next(h for h in headings if "Freigeben" in h)

    assert target, "Abschnitt zum Zielbild fehlt in grill-me"
    assert "**Zielbild:**" in _section(GRILL_ME, "Übersicht zeigen")
    assert headings.index(scenarios) < headings.index(target) < headings.index(release)
    steps = _section(GRILL_ME, target)
    assert "`CLAUDE.md`" in steps
    for part in ["Grober Entwurf", "Prüfsumme", "Nachklärung", "erfundene", "65 536 Zeichen"]:
        assert part in steps, part
    assert "Zielbild" in _section(GRILL_ME, release)


def test_issue_anlegen_traegt_neue_issues_der_laufenden_phase_ins_phasen_issue_ein():
    section = _section(ISSUE_ANLEGEN, "Laufende Phase")

    assert "Phasen-Issue" in section
    assert "im selben Schritt" in section
    for part in ["Platz", "Abhängigkeiten", "Stunden"]:
        assert part in section, part


def test_phase_steuern_hat_die_handgriffe_fuer_die_ganze_phase():
    text = PHASE_STEUERN.read_text(encoding="utf-8")
    headings = " ".join(re.findall(r"^## (.+)$", text, flags=re.MULTILINE))

    assert "name: phase-steuern" in text
    for step in ["Phasenstart", "Aufträge", "Phasen-Issue pflegen", "Übergabe", "Abschluss"]:
        assert step in headings, step
    assert "phase.yml" in text
    # Die Steuerungssession ändert keine Dateien selbst (CLAUDE.md); im Abschluss gibt sie
    # Erfahrungen und den „Stand“ als Auftrag an eine Umsetzungs-Session.
    closing = _section(PHASE_STEUERN, "Abschluss")
    assert "Auftrag" in closing
    assert "Umsetzungs-Session" in closing


# --- Vorlagen --------------------------------------------------------------------------------


def test_vorlage_fuer_pull_requests_fragt_nach_den_szenarien():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    checks = text.split("## Wie geprüft wurde", 1)[1].split("\n## ", 1)[0]
    first = next(line for line in checks.splitlines() if line.startswith("- "))

    assert first.startswith("- Szenarien")
    assert "„Szenarien (Datum)“" in first


def test_vorlage_fuer_pull_requests_fragt_nach_zielbild_und_abweichungen():
    section = _section(PR_TEMPLATE, "Zielbild")

    assert "Abweichung" in section
    assert "`docs/zielbilder/README.md`" in section


def test_entscheidung_zu_zielbild_vor_gestaltung_und_verweis_in_gestaltung():
    entries = re.findall(r"^## (.+)$", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.MULTILINE)

    assert any("(#162)" in entry for entry in entries)
    assert any("(#161)" in entry for entry in entries), "Eintrag vom 25.10.2026 bleibt"
    assert "„Zielbild vor Gestaltung“ (Entscheidung in `docs/entscheidungen.md`, Eintrag vom 26.10.2026 zu #162)" in _text(GESTALTUNG)


# Bausteinkatalog (#176): Regeln in CLAUDE.md, docs/gestaltung.md und CONTRIBUTING.md

CONTRIBUTING = BASE_DIR / "CONTRIBUTING.md"


def test_katalog_statt_musterseite_in_claude_md_gestaltung_und_contributing():
    for path in (CLAUDE_MD, GESTALTUNG, CONTRIBUTING, GRILL_ME):
        text = _text(path)
        assert "Bausteinkatalog" in text, path.name
        assert "muster.html" not in text, path.name
    assert "/muster/" not in _text(CLAUDE_MD)
    assert "einbinden, nicht kopieren" in _text(CONTRIBUTING)


def test_gestaltung_nennt_die_regeln_des_katalogs_und_den_alten_namen():
    text = _text(GESTALTUNG)

    assert "einbinden, nicht kopieren" in text
    assert "sobald Sebastian ihn entschieden hat, spätestens mit seiner ersten Seite" in text
    assert "noch auf keiner Seite" in text
    assert "Wo ein Issue „Musterseite“ oder `/muster/` sagt, ist seit #176 der Bausteinkatalog gemeint." in text


def test_ki_haelt_an_wenn_ein_baustein_nicht_genau_passt():
    rules = _text(CLAUDE_MD)
    rule = _sentence_after(rules, "Passt ein vorhandener Baustein nicht genau")

    assert "hält die KI an und fragt Sebastian" in rule
    assert "nie eine stille Kopie" in rule


def test_unabhaengige_pruefung_prueft_selbst_gebaut_statt_baustein():
    section = _section(CLAUDE_MD, "Unabhängige Prüfung")

    assert "selbst gebaut statt Baustein eingebunden" in section


def test_entscheidung_zum_bausteinkatalog():
    entries = re.findall(r"^## (.+)$", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.MULTILINE)

    assert any("(#176)" in entry for entry in entries)


def _phase_fields():
    template = yaml.safe_load(PHASE_TEMPLATE.read_text(encoding="utf-8"))
    return {field["id"]: field["attributes"] for field in template["body"] if field["type"] != "markdown"}


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


# Sperren für die KI (#233): Regel in CLAUDE.md, Sperrliste und Prüfschritt, grill-me ohne Label-Befehl

SETTINGS = BASE_DIR / ".claude" / "settings.json"


def test_claude_md_nennt_gesperrte_handlungen_dateien_und_werkzeuggrenze():
    rule = _section(CLAUDE_MD, "Was die KI nie allein entscheidet oder tut")
    release = _sentence_after(_section(CLAUDE_MD, "Steuerungssession und Umsetzungs-Sessions"), "**Freigaben:**")

    for action in ["Pull Requests übernehmen", "auf `main` oder mit Force pushen", "`.env` lesen", "`geklärt` setzen"]:
        assert action in rule, action
    assert "In Claude Code sperren `.claude/settings.json` und `.claude/hooks/sperren.py`" in rule
    assert "als Schutz vor Versehen" in rule
    assert "andere KI-Werkzeuge haben diese Sperre nicht und arbeiten im Projekt nur lesend" in rule
    assert "Eine Sperre nie umgehen, auch nicht nach einem Okay im Chat" in rule
    assert "Nur Sebastian setzt `geklärt` und übernimmt Pull Requests, jeweils selbst auf GitHub" in release


def test_settings_sperrt_env_und_uebernehmen_und_bindet_den_pruefschritt_ein():
    settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks = [hook for entry in settings["hooks"]["PreToolUse"] if entry["matcher"] == "Bash" for hook in entry["hooks"]]

    assert {"Read(./.env)", "Read(./**/.env)", "Bash(gh pr merge:*)"} <= set(settings["permissions"]["deny"])
    # Der Pfad über $CLAUDE_PROJECT_DIR gilt auch, wenn die Sitzung in einem Unterordner arbeitet.
    # „|| exit 2“: Auch wenn der Prüfschritt selbst scheitert, weist Claude Code den Befehl ab.
    assert any(hook["command"] == 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/sperren.py" || exit 2' for hook in hooks)
    assert (BASE_DIR / ".claude" / "hooks" / "sperren.py").is_file()


def test_grill_me_bittet_sebastian_um_geklaert_statt_es_selbst_zu_setzen():
    text = GRILL_ME.read_text(encoding="utf-8")
    head = text.split("---", 2)[1]
    release = _section(GRILL_ME, "Freigeben")

    assert not re.search(r"labels\[\]=geklärt|(--add-label|--label|-l)[ =]\S*geklärt", text), "Befehl setzt `geklärt`"
    assert "für Sebastians Freigabe mit dem Label „geklärt“ vorbereiten" in head
    assert "bittet die KI Sebastian, das Label `geklärt` selbst zu setzen" in release
    assert "prüft die KI auf GitHub, ob das Label da ist" in release
    assert "die Freigabe durch Sebastian (Abschnitt 9)" in _section(GRILL_ME, "Kurzform")


# --- Prüfumfang nach Art der Änderung (#235) ------------------------------------------------------


def _schritt(nummer):
    """Text eines nummerierten Schritts aus „Ablauf je Aufgabe“ (bis zum nächsten Schritt)."""
    section = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    match = re.search(rf"(?:^| ){nummer}\. \*\*(.*?)(?= {nummer + 1}\. \*\*|$)", section)
    assert match, f"Schritt {nummer} fehlt in „Ablauf je Aufgabe“"
    return match.group(0)


def test_ablauf_nr3_je_szenario_ein_test_weitere_nur_mit_fehlermechanismus_oder_risiko():
    step = _schritt(3)

    assert "je Szenario einer" in step
    assert "Fehlermechanismus, den noch kein Test prüft" in step
    assert "begründete Risikovariante" in step
    assert "von gleichartigen Schreibweisen nur eine Auswahl" in step
    assert "die Pflichtfälle aus `CONTRIBUTING.md` bleiben" in step


def test_ablauf_nr4_prueft_passend_zur_aenderung_mit_schnellem_lauf():
    step = _schritt(4)

    assert "`./pruefen.sh schnell`" in step
    assert "betroffenen Testdateien" in step
    assert "ihrer Aufrufer" in step
    for guard in ["Rundumtests", "Prüfung der Rechtematrix", "Rauchtests der betroffenen Seiten"]:
        assert guard in step, guard
    assert "Regeltexten, Doku und `.claude/`" in step
    assert "begründet die Auswahl in einem Satz" in step


def test_ablauf_nr4_voller_lauf_auf_github_lokal_nur_in_den_ausnahmen():
    step = _schritt(4)

    assert "Den vollen Lauf (`./pruefen.sh`) macht die Prüfung auf GitHub" in step
    assert "nur bei Änderungen an Paketen, Docker, `pruefen.sh` oder dem Prüfablauf auf GitHub" in step
    assert "vor der unabhängigen Prüfung" in step
    assert "ausgeführt, übersprungen, nicht ausgewählt und nur empfohlen" in step
    assert "alle automatischen Prüfungen lokal" not in step


def test_ablauf_nr5_unabhaengige_pruefung_einmal_zweite_nur_nach_hoch():
    step = _schritt(5)

    assert "einmal, sobald der Stand fertig zur Prüfung und der schnelle Lauf grün ist" in step
    assert "nie gleichzeitig mit einem Prüflauf derselben Arbeitskopie" in step
    assert "Eine zweite gibt es nur nach einem Befund „hoch“, und nur für dessen Korrektur" in step


def test_unabhaengige_pruefung_nennt_die_drei_schweregrade_nach_der_folge():
    section = _section(CLAUDE_MD, "Unabhängige Prüfung")

    assert "der Schweregrad nach der Folge" in section
    for level in ["**hoch** bei", "**mittel** bei", "**gering** bei"]:
        assert level in section, level
    assert "unberechtigtem Zugriff" in section
    assert "doppeltem Mailversand" in section
    assert "Ausfall eines Kernablaufs" in section
    assert "einem fehlenden Test ohne belegten Fehler" in section


def test_pull_request_begruendet_zusaetzliche_tests_mit_fehlermechanismus_oder_risiko():
    rules = _text(CLAUDE_MD)

    assert "begründet zusätzliche Tests mit ihrem Fehlermechanismus oder Risiko" in rules
    assert "nennt die Tests, die über die Szenarien hinaus dazugekommen sind" not in rules


def test_vorlage_und_leitfaden_verweisen_fuer_die_pruefungen_auf_claude_md():
    template = _text(PR_TEMPLATE)
    guide = _text(BASE_DIR / "docs" / "review-leitfaden.md")

    assert "nach `CLAUDE.md`, Ablauf je Aufgabe Nr. 4" in template
    assert "welcher Lauf, welche Tests mit Begründung, wie viele übersprungen" in template
    assert "wird geprüft wie in `CLAUDE.md`, Ablauf je Aufgabe Nr. 4" in guide
    assert "laufen die betroffenen Tests und alle Prüfungen" not in guide


def test_entscheidung_zum_pruefumfang_loest_den_satz_zu_gleichem_pruefen_ab():
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    entries = re.split(r"^## ", text, flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#235)")), None)

    assert entry, "Eintrag zu #235 fehlt in docs/entscheidungen.md"
    flat = _flat(entry)
    assert "lokal und auf GitHub wird gleich geprüft" in flat
    assert "löst" in flat


# --- Pflichtangaben im Pull Request werden geprüft (#237) --------------------------------------


def test_vorlage_hat_die_zeile_test_commit_hinter_der_szenarien_zeile_und_erklaert_sie():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    checks = text.split("## Wie geprüft wurde", 1)[1].split("\n## ", 1)[0]
    zeilen = [line for line in checks.splitlines() if line.startswith("- ")]
    flat = _flat(checks)

    assert zeilen[0].startswith("- Szenarien (Link zum Kommentar „Szenarien (Datum)“")
    assert zeilen[1] == "- Test-Commit:"
    assert "Die Prüfung „PR-Angaben“ auf GitHub liest „Closes #…“, die Szenarien-Links in diesem Abschnitt" in flat
    assert "Test-Commit: Kennung des Commits, der nur Tests hinzufügt, vor dem Code; mehrere durch Komma" in flat
    assert "ein leeres Gerüst davor als „Gerüst-Commit:“; ohne Codeänderung „entfällt, weil …“" in flat
    assert "(Begriffe in `CONTRIBUTING.md`, Abschnitt 3)" in flat


def test_vorlage_sagt_sebastian_was_er_bei_rotem_oder_laufendem_pr_angaben_tut():
    kopf = _flat(PR_TEMPLATE.read_text(encoding="utf-8").split("\n## ", 1)[0])

    assert "Für Sebastian: Ist „PR-Angaben“ rot oder läuft noch, nicht übernehmen." in kopf
    assert "Unter „Details“ steht, was fehlt" in kopf
    assert "den neuen grünen Lauf abwarten" in kopf


def test_claude_md_verlangt_test_commit_vor_dem_code_und_gruene_pr_angaben_vor_dem_link():
    rules = _text(CLAUDE_MD)

    assert "Ändert er Code, kommen die Tests als eigener Commit vor den Code" in rules
    assert "die Beschreibung nennt „Closes #<nummer>“ und diesen Test-Commit" in rules
    assert "Die Prüfung „PR-Angaben“ auf GitHub prüft diese Angaben, den Szenarien-Link und das Label `geklärt`" in rules
    assert "auch nach der letzten Bearbeitung der Beschreibung" in rules
    assert "Ändert sich danach am Issue etwas (Text, Label, Szenarien), läuft sie vor dem Link neu." in rules
    assert "Ein Issue ergibt einen Pull Request mit eigenem Test. Die Beschreibung nennt" not in rules


def test_claude_md_kennt_vor_dem_start_auch_die_zeile_szenarien_keine():
    rules = _text(CLAUDE_MD)

    assert "ein Auftrag hebt ihn nie auf. Statt des Kommentars genügt, wenn das Issue nach Schritt 3" in rules
    assert "die Zeile „Szenarien: keine.“ mit dem Grund aus der Klärung enthält." in rules


def test_contributing_erklaert_test_commit_code_und_was_automatisch_geprueft_wird():
    abschnitt = _section(CONTRIBUTING, "Korrektheit und Tests")

    assert "Ändert ein Pull Request Code, kommen die Tests als eigener Commit vor dem Code" in abschnitt
    assert "ein leeres Gerüst darf als eigener Commit davor stehen" in abschnitt
    assert "*Code* heißt dabei jede Datei außer unter `docs/`, `tests/`, `rauchtests/`, `containertests/`, " in abschnitt
    assert "`.github/ISSUE_TEMPLATE/` und außer `*.md`" in abschnitt
    assert "auch Prüfskripte, CI und `.claude/`-Einstellungen sind Code" in abschnitt
    assert "Ohne Code entfällt der Test-Commit; das ist unabhängig davon, ob Szenarien nötig sind." in abschnitt
    assert "Prüfung „PR-Angaben“ prüft, dass der Test-Commit genannt ist, nur Tests ändert und kein Code vor ihm liegt" in abschnitt
    assert "ob er aus dem richtigen Grund rot ist und ob ein Gerüst nur Gerüst ist: Review" in abschnitt


def test_grill_me_nennt_den_verzicht_als_zeile_im_issue_text():
    freigeben = _section(GRILL_ME, "Freigeben")

    assert "dass es keine Szenarien braucht, und zwar als Zeile „Szenarien: keine.“ mit dem Grund im Text des Issues" in freigeben
    assert "diese Form liest die Prüfung „PR-Angaben“" in freigeben


def test_entscheidung_zu_den_pflichtangaben_im_pull_request_nennt_regel_und_grenzen():
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    entries = re.split(r"^## ", text, flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#237)")), None)

    assert entry, "Eintrag zu #237 fehlt in docs/entscheidungen.md"
    assert entry.startswith("2026-11-03 · ")
    flat = _flat(entry)
    for teil in [
        "Prüfung „PR-Angaben“",
        "Test-Commit vor dem Code",
        "Gerüst-Commit",
        "`geklärt`",
        "*Code*",
        "Mensch und KI schreiben unter demselben Konto",
        "aus dem richtigen Grund",
        "Commit-Zeiten lassen sich fälschen",
        "sperrt das Übernehmen weiterhin nicht (#16)",
    ]:
        assert teil in flat, teil


# Warten auf GitHub und kurzer Kopf der Pull-Request-Beschreibung (#239)


def test_claude_md_verlangt_selbst_warten_und_den_link_erst_bei_gruen():
    step = _section(CLAUDE_MD, "Ablauf je Aufgabe")

    assert "Gewartet wird selbst: Die Sitzung startet einen Hintergrundauftrag, der sie am Ende des Laufs weckt" in step
    assert "und bittet Sebastian nie, Bescheid zu geben" in step
    assert "meldet sie nur „PR angelegt, Prüfung läuft“, ohne Link" in step
    assert "den Link gibt es auch dann erst bei Grün" in step
    assert "Lässt sich keine Beobachtung starten, sagt sie das offen und fragt den Stand selbst ab" in step
    assert "stehen Nummer des Pull Requests und letzter geprüfter Stand im Issue" in step
    assert "die nächste Sitzung stellt den Stand selbst neu fest" in step


def test_das_warten_steht_im_schritt_zum_pull_request_nach_der_regel_zum_link():
    step = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    pull_request = step.split("6. **Pull Request**", 1)[1]

    assert pull_request.index("in der Beschreibung nennen.") < pull_request.index("Gewartet wird selbst")
    assert "Neustart" in pull_request.split("Gewartet wird selbst", 1)[1]


def test_phase_steuern_stellt_lauf_und_uebernahme_selbst_fest():
    section = _section(PHASE_STEUERN, "Aufträge")

    assert "**Stand selbst feststellen:**" in section
    assert "nicht über Sebastians Meldung" in section
    assert "für Läufe wie in `CLAUDE.md`, Ablauf je Aufgabe Nr. 6" in section
    assert "`gh pr view <nummer> --json state,mergedAt`" in section
    assert "bei jedem Wiedereinstieg" in section
    assert "Hintergrundauftrag, der diese Abfrage wiederholt und sie bei der Übernahme weckt" in section


def test_contributing_verlangt_den_kopf_fuer_sebastian_und_nennt_die_pruefung():
    section = _section(BASE_DIR / "CONTRIBUTING.md", "Pull Requests")

    assert "Die Beschreibung beginnt mit dem Abschnitt „Für Sebastian“: höchstens fünf Zeilen und 600 Zeichen" in section
    assert "Regeländerungen als „vorher / nachher“" in section
    assert "Prüfung „PR-Angaben“ prüft Platz und Länge; ob der Kopf verständlich ist: Review" in section
    assert section.index("Für Sebastian") < section.index("erklärt in Alltagssprache")


def test_vorlage_hat_den_abschnitt_fuer_sebastian_als_ersten_nach_dem_anfangskommentar():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    anfang, rest = text.split("\n## ", 1)

    assert rest.startswith("Für Sebastian\n")
    assert anfang.count("<!--") == 1
    assert "<!-- Kurz, nach CONTRIBUTING.md, Abschnitt 8. -->" in rest.split("\n## ", 1)[0]


def test_entscheidung_zum_kopf_und_zum_warten_nennt_regel_und_grenzen():
    entries = re.split(r"^## ", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#239)")), None)

    assert entry, "Eintrag zu #239 fehlt in docs/entscheidungen.md"
    assert entry.startswith("2026-11-03 · ")
    flat = _flat(entry)
    for teil in [
        "Hintergrundauftrag",
        "„Für Sebastian“",
        "600 Zeichen",
        "nicht, ob der Kopf verständlich ist",
        "ob das Wecken in jeder Umgebung klappt",
    ]:
        assert teil in flat, teil


# Verweise statt Fassungen, Memory, Sitzungswechsel (#240)

HOOK = BASE_DIR / ".claude" / "hooks" / "zusammenfassung.py"


def _stand_abschnitt():
    """Abschnitt 4 des Skills phase-steuern (Übergabe)."""
    return _section(PHASE_STEUERN, "Übergabe an die nächste Steuerungssession")


def test_ein_ort_je_angabe_gilt_auch_fuer_texte_der_ki_und_schaltet_die_memory_ab():
    section = _section(CLAUDE_MD, "Ein Ort je Angabe")

    assert "Das gilt auch für Texte, die die KI selbst schreibt" in section
    assert "Aufträge, Prompts für die nächste Sitzung und der Stand im Phasen-Issue enthalten nur Verweise und den Stand" in section
    assert "nie eine eigene Fassung einer Regel" in section
    assert "Kürzel aus einer Klärung stehen immer mit der Issue-Nummer (etwa „#106 F1“)" in section
    assert "Die automatische Memory von Claude Code ist für dieses Projekt abgeschaltet (`.claude/settings.json`)" in section
    assert "was eine spätere Sitzung wissen muss, steht im Issue oder in diesen Dateien" in section
    # nach dem ersten Absatz, vor der Liste der Orte
    assert section.index("Das gilt auch für Texte") < section.index("**Was gilt:**")
    assert section.index("Das gilt auch für Texte") > section.index("statt sie zu wiederholen")


def test_ablauf_nr4_nennt_den_bericht_wenn_ein_lokaler_lauf_technisch_nicht_geht():
    step = _schritt(4)

    assert "Lässt sich ein lokaler Lauf in einer Umgebung technisch nicht ausführen" in step
    assert "ein roter Lauf zählt nicht" in step
    assert "nennt der Bericht, was ausgelassen wurde und warum" in step
    assert "die unabhängige Prüfung beginnt dann ohne ihn" in step
    assert "Beleg ist der grüne Lauf auf GitHub für den letzten Stand" in step


def test_ablauf_nr6_weckt_bei_gruen_wie_bei_rot_und_erlaubt_die_abfragen_ausdruecklich():
    step = _schritt(6)

    assert "der sie am Ende des Laufs weckt, bei Grün wie bei Rot (`gh pr checks <nummer> --watch` für den eigenen Pull Request" in step
    assert "`gh pr view <nummer> --json state,mergedAt`" in step
    assert "gibt Sebastian hiermit ausdrücklich seine Erlaubnis" in step
    assert "auch wo ein Werkzeug solche Abfragen sonst nicht von sich aus vorsieht" in step
    assert "technische Sperren gelten weiter" in step
    assert "eine Beobachtung, die nur bei Rot weckt, genügt nicht" in step
    assert "die PR-Beobachtung des Werkzeugs, wo es eine hat" not in step


def test_neuer_inhalt_zu_einem_geklaerten_issue_klaert_die_steuerung_nicht_selbst():
    section = _section(CLAUDE_MD, "Ablauf einer Phase")
    rule = section.split("**Neuer Inhalt zu einem geklärten Issue**", 1)[1].split(" - **", 1)[0]

    assert "Danach läuft `grill-me` nur für den neuen Teil." in rule
    assert "Die Steuerungssession klärt ihn nicht selbst; sie gibt ihn an eine Klärung." in rule


def test_nach_einer_uebernahme_wird_der_lauf_auf_main_abgefragt_ohne_darauf_zu_warten():
    section = _section(CLAUDE_MD, "Ablauf einer Phase")
    rule = section.split("**Umsetzen:**", 1)[1].split(" - **", 1)[0]

    assert "Nach einer Übernahme fragt die Steuerungssession den Lauf auf `main` ab" in rule
    assert "auf sein Ende warten muss sie vor dem nächsten Auftrag nicht" in rule


def test_phase_steuern_haelt_den_stand_kurz_und_gibt_den_startsatz_vor():
    section = _stand_abschnitt()

    assert "höchstens 15 Zeilen" in section
    assert "Nichts Abgeschlossenes als „Davor: …“" in section
    assert "Bearbeitungshistorie des Issues" in section
    assert "keine Zeile länger als ein Satz" in section
    assert "Steuere Phase <Pn> weiter, Phasen-Issue #<nr>, nach `CLAUDE.md` und Skill `phase-steuern`." in section


def test_phase_steuern_gibt_nachtraege_an_grill_me_und_kennt_den_lauf_auf_main():
    auftraege = _section(PHASE_STEUERN, "Aufträge")
    # Der Abschnitt „Phasen-Issue pflegen“ enthält einen Codeblock mit „#“-Zeilen; deshalb der ganze Skill.
    pflegen = _text(PHASE_STEUERN).split("Nach jeder übernommenen Umsetzung:", 1)[1].split("Neues Issue in der Phase:", 1)[0]

    assert "**Nachträge** zu einem geklärten Issue" in auftraege
    assert "an eine Klärung mit `grill-me` geben (Kurzform möglich)" in auftraege
    assert "`gh run list --branch main --limit 1`" in pflegen
    # Die Regel steht in CLAUDE.md; der Skill verweist nur darauf (Ein Ort je Angabe).
    assert "Regel in `CLAUDE.md`, „Ablauf einer Phase“, „Umsetzen“" in pflegen
    assert "nicht warten" not in pflegen


def test_phase_steuern_kennt_die_grenzen_von_desktop_app_und_cloud():
    text = _text(PHASE_STEUERN)

    assert "In der Claude-Code-Desktop-App" in text
    assert "kann sie selbst keine neue Session starten" in text
    assert "eine Karte in der App" in text
    assert "den Sebastian mit einem Klick startet" in text
    assert "In der Cloud-Umgebung von Claude Code ist die GitHub-Suche (`search/issues`) gesperrt" in text
    assert "nur Adressen unter `repos/...`" in text


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


def test_entscheidung_zu_verweisen_memory_und_sitzungswechsel_nennt_regel_und_grenzen():
    entries = re.split(r"^## ", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#240)")), None)

    assert entry, "Eintrag zu #240 fehlt in docs/entscheidungen.md"
    assert entry.startswith("2026-11-03 · ")
    flat = _flat(entry)
    for teil in [
        "nur Verweise und den Stand",
        "`autoMemoryEnabled`",
        "erinnert nur",
        "beendet keine Sitzung",
        "Codex und Gemini kennen ihn nicht",
        "nur lesend",
    ]:
        assert teil in flat, teil


# --- #244 (P-05a): Prüfumfang der unabhängigen Prüfung, Nachziehen, Übersicht der Grundsätze ---

REVIEW_LEITFADEN = BASE_DIR / "docs" / "review-leitfaden.md"

UEBERSICHT_THEMEN = [
    "Lokaler Prüfumfang",
    "Wechsel der Sessions",
    "Länge des Fahrtennamens",
    "Zweite Zeile der Rollenkacheln",
    "Marke am eigenen Bund, Seite „Verband“",
    "Felder der Liste der Leitungen",
    "Zwei Prüfläufe gleichzeitig",
    "Bedienung des Felds Fahrtenname",
    "Stelle für den fehlenden Namen",
    "Aufträge nennen den Schritt",
    "Wortlaut „E-Mail-Adresse“, „stammen aus“",
    "Kennungen in Adressen",
    "„hat Ringe“ ausschalten",
    "Wechsel und Ende der Mitgliedschaft",
    "Wer Leitungen sieht",
    "Stunden erfassen",
    "Code aus dem alten Repo",
]


def _entscheidungen_kopf():
    """Alles vor dem ersten Eintrag (erste Überschrift `## <Jahr>-…`)."""
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    return re.split(r"^## \d{4}-\d{2}-\d{2} ", text, maxsplit=1, flags=re.M)[0]


def test_unabhaengige_pruefung_liest_auch_ausserhalb_des_diffs_und_aendert_nichts():
    section = _section(CLAUDE_MD, "Unabhängige Prüfung")

    assert "prüft lesend; sie ändert nichts" in section
    assert "Sie liest Text und Szenarien des Issues" in section
    assert "die zum Verstehen nötigen Aufrufer, Rechtehilfen, Modelle und Tests, auch außerhalb des Diffs" in section
    assert "sucht nach Stellen, die sich auf Geändertes beziehen" in section
    assert "Ihr Bericht nennt, was sie außerhalb des Diffs geprüft hat, auch wenn sie dort nichts fand" in section
    assert "Geprüft wird der Diff gegen `CONTRIBUTING.md` und diese Punkte:" in section
    # Die sieben Punkte und die Schweregrade bleiben.
    assert "7. selbst gebaut statt Baustein eingebunden" in section
    assert "**hoch**" in section and "**mittel**" in section and "**gering**" in section


def test_fehler_ausserhalb_des_diffs_wird_nicht_mitbehoben_sondern_eigenes_issue():
    section = _section(CLAUDE_MD, "Unabhängige Prüfung")

    assert section.rstrip().endswith(
        "Einen Fehler außerhalb des Diffs, den der Pull Request nicht verursacht hat, behebt er nicht mit; "
        "er kommt als eigenes Issue (Skill `issue-anlegen`)."
    )


def test_erfahrung_zur_unabhaengigen_pruefung_begrenzt_den_auftrag_auf_die_punkte_des_abschnitts():
    text = _text(CLAUDE_MD)

    assert "Ihren Auftrag auf die Punkte im Abschnitt „Unabhängige Prüfung“ begrenzen" in text
    assert "Ihren Auftrag eng fassen" not in text


def test_nachziehen_vor_der_unabhaengigen_pruefung_mit_suchbegriffen_im_pull_request():
    text = _text(CLAUDE_MD)
    start = text.index("Für die Umsetzung gilt außerdem:")
    ende = text.index("## Ablauf einer Phase")
    umsetzung = text[start:ende]

    assert "**Nachziehen:** Vor der unabhängigen Prüfung sucht die KI mit `git grep \"#<nummer>\"`" in umsetzung
    assert "nach Verweisen auf das Issue und mit Stichworten des Geänderten" in umsetzung
    assert "nach Grundsätzen, Kommentaren und Doku, die sich darauf beziehen" in umsetzung
    assert "zieht nach, was durch diese Änderung veraltet ist" in umsetzung
    assert "Der Pull Request nennt unter „Wie geprüft wurde“ Suchbegriffe und Ergebnis." in umsetzung


def test_ersetzender_eintrag_nennt_den_aelteren_und_schreibt_die_uebersicht_fort():
    section = _section(CLAUDE_MD, "Was die KI nie allein entscheidet oder tut")

    assert "neue kommen im Pull Request dazu und werden in der Beschreibung genannt. Ersetzt ein neuer Eintrag" in section
    assert "nennt er ihn („ersetzt den Eintrag vom … (#…), Punkt …“)" in section
    assert "Übersicht „Geltende Grundsätze“ am Anfang der Datei" in section
    assert "gibt es das Thema dort schon, wird seine Zeile fortgeschrieben" in section
    assert "Die Übersicht verweist nur, sie fasst keine Regel neu." in section


def test_nur_den_diff_steht_nirgends_mehr_ausser_in_alten_eintraegen():
    treffer = []
    for path in [CLAUDE_MD, REVIEW_LEITFADEN, GRILL_ME, ISSUE_ANLEGEN, PHASE_STEUERN, PR_TEMPLATE, CONTRIBUTING]:
        if re.search(r"nur (den|der) Diff", path.read_text(encoding="utf-8")):
            treffer.append(path.name)

    assert treffer == []


def test_entscheidungen_hat_oben_die_uebersicht_geltende_grundsaetze():
    kopf = _flat(_entscheidungen_kopf())

    assert "Neue Einträge oben, unter der Übersicht." in kopf
    assert "## Geltende Grundsätze" in _entscheidungen_kopf()
    assert (
        "Nur Themen, bei denen ein Eintrag einen älteren ganz oder teilweise ersetzt, je Teilthema eine Zeile. "
        "Die Übersicht verweist nur; maßgeblich ist der genannte Eintrag. Die alten Einträge bleiben unverändert."
    ) in kopf
    assert "| Thema | Gilt | Ersetzt |" in _entscheidungen_kopf()


def test_uebersicht_enthaelt_den_anfangsbestand_nur_als_verweis():
    # Neue und fortgeschriebene Zeilen sind erlaubt (CLAUDE.md); geprüft wird nur, dass kein Thema
    # des Anfangsbestands fehlt und jede Zeile drei gefüllte Zellen hat.
    zeilen = [z for z in _entscheidungen_kopf().splitlines() if z.startswith("| ") and not z.startswith(("| Thema", "| ---"))]
    zellen = [[z.strip() for z in zeile.strip("|").split("|")] for zeile in zeilen]

    assert all(len(zeile) == 3 and all(zeile) for zeile in zellen), zellen
    themen = [zeile[0] for zeile in zellen]
    for thema in UEBERSICHT_THEMEN:
        assert thema in themen, thema


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


def test_entscheidung_zu_pruefumfang_und_nachziehen_nennt_freigabe_und_ersetzt_nichts():
    entries = re.split(r"^## ", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#244)")), None)

    assert entry, "Eintrag zu #244 fehlt in docs/entscheidungen.md"
    assert entry.startswith("2026-11-04 · ")
    flat = _flat(entry)
    for teil in ["E-074", "E-075", "E-076", "G-11", "Nachziehen", "Geltende Grundsätze", "ersetzt keinen", "#78, Nr. 3"]:
        assert teil in flat, teil


def test_grill_me_fragt_je_issue_mit_szenarien_was_unveraendert_bleiben_muss():
    section = _section(GRILL_ME, "Szenarien")

    assert "**Was bleibt unverändert?**" in section
    assert "welche bestehenden Abläufe dieselben Daten, Adressen oder Rechte berühren und was dort gleich bleiben muss" in section
    assert "Abschnitt „Was bleibt unverändert?“" in section
    assert "berührt das Issue nichts Bestehendes, steht dort genau das mit Grund" in section


def test_vorlage_fuer_pull_requests_hat_nachziehen_vor_der_unabhaengigen_pruefung():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    nachziehen = "- Nachziehen (Suchbegriffe und Ergebnis, `CLAUDE.md`, „Nachziehen“):"
    pruefung = (
        "- Unabhängige Prüfung: alle Befunde mit Schweregrad und einem Stichwort zur Fehlerart und was daraus wurde "
        "(keine Befunde: das nennen):"
    )

    assert nachziehen in text and pruefung in text
    assert text.index(nachziehen) < text.index(pruefung)
    assert text.index("- Rauchtest des Hauptablaufs:") < text.index(nachziehen)
    assert "- Unabhängige Prüfung: Befunde und was daraus wurde:" not in text


def test_review_leitfaden_beschreibt_den_umfang_der_unabhaengigen_pruefung_wie_claude_md():
    text = _text(REVIEW_LEITFADEN)

    assert "der Diff, dazu Issue, nötige Aufrufer und Nachbarstellen" in text


# --- #245 (P-05b): Aufräumen je Phase, Rückblick, roter main, gelockerte Prüfbedingungen, Neustarts ---


def _phase_punkt(name):
    """Text eines Punkts („**Start:**“ usw.) aus „Ablauf einer Phase“ bis zum nächsten Punkt."""
    section = _section(CLAUDE_MD, "Ablauf einer Phase")
    rest = section.split(f"**{name}:**", 1)[1]
    return re.split(r" - \*\*", rest, maxsplit=1)[0]


def test_ab_p3_gibt_es_je_phase_ein_issue_aufraeumen_das_wie_jedes_issue_laeuft():
    start = _phase_punkt("Start")

    assert (
        "Ab P3 legt sie dabei ein Issue „Aufräumen“ an; es benennt die Zusammenführungen und Bereinigungen "
        "dieser Phase, die das Verhalten nicht ändern, und läuft wie jedes andere Issue."
    ) in start
    # Der bisherige Start bleibt davor stehen.
    assert start.index("Eine zweite KI prüft die Planung, bevor die erste Umsetzung beginnt.") < start.index("Ab P3 legt sie")


def test_phase_steuern_legt_ab_p3_das_issue_aufraeumen_beim_phasenstart_an():
    schritt = _section(PHASE_STEUERN, "Phasenstart").split("2. **Bestandsaufnahme:**", 1)[1].split("3. **Grundlagen", 1)[0]

    assert (
        "Ab P3 dabei das Issue „Aufräumen“ anlegen (Regel in `CLAUDE.md`, „Ablauf einer Phase“, „Start“), "
        "mit Vorschlägen aus dem letzten Rückblick und offenen Befunden."
    ) in schritt


def test_rueckblick_streicht_zuerst_wertet_die_pruefbefunde_aus_und_fragt_vor_jeder_neuen_regel_nach_einer_schranke():
    abschluss = _phase_punkt("Abschluss")

    assert "folgt ein Rückblick. Er prüft zuerst, welche Regeln sich streichen, zusammenfassen oder durch eine Prüfschranke ersetzen lassen" in abschluss
    assert "und wertet die Befunde der unabhängigen Prüfung nach Fehlerarten aus" in abschluss
    assert "erst dann kommt Neues dazu, und vor jeder neuen Regel die Frage, ob eine Prüfschranke genügt" in abschluss
    assert "Neue Erfahrungen kommen unten in diese Datei." in abschluss
    # Die Reihenfolge des Abschlusses bleibt: Review, Rückblick, erst dann der „Stand“.
    assert abschluss.index("externe Review") < abschluss.index("Rückblick") < abschluss.index("„Stand“")


def test_phase_steuern_wertet_im_rueckblick_die_befunde_aus_und_gleicht_neustarts_mit_dem_issue_ab():
    schritt = _section(PHASE_STEUERN, "Abschluss").split("3. Sind alle", 1)[1].split("4. Erst danach", 1)[0]

    assert "was lief gut, was nicht. Dazu aus den Zeilen „Unabhängige Prüfung“ der Pull Requests der Phase" in schritt
    assert "bis zu drei häufige Fehlerarten mit je einer Folgerung" in schritt
    assert "mit der Zahl der ausgewerteten Pull Requests und fehlenden Angaben" in schritt
    assert "die gestrichenen oder zusammengefassten Regeln oder der Grund, warum es keine gibt (Regel in `CLAUDE.md`, „Abschluss“)" in schritt
    assert "Neustarts mit dem Issue „Wackelnde Prüfungen“ abgleichen" in schritt
    assert '`gh run list --workflow "Prüfungen" --created ">=<Phasenstart>" --limit 1000 --json attempt,headSha,url`, Versuch über 1' in schritt
    assert "kommen genau 1000 zurück, das offen sagen" in schritt
    assert "Streichungen und neue Erfahrungen kommen als Issue" in schritt


def test_roter_main_geht_vor_und_andere_umsetzungen_warten_auf_gruen():
    umsetzen = _phase_punkt("Umsetzen")

    assert "auf sein Ende warten muss sie vor dem nächsten Auftrag nicht." in umsetzen
    for teil in [
        "Ist der letzte beendete Lauf „Prüfungen“ auf `main` rot, oder abgebrochen, ohne dass ein neuerer läuft, beginnt keine andere Umsetzung, bis er grün ist.",
        "Die Steuerungssession stellt die Ursache fest.",
        "Erfüllt der Lauf die Bedingungen für den Neustart aus Nr. 6, startet sie ihn neu;",
        "sieht es sonst nur nach einer Störung oder einem wackelnden Test aus, entscheidet Sebastian, ob sie neu startet.",
        "Sonst legt sie ein Fehler-Issue an; es läuft wie jedes Issue, auch vor einem offenen Pull Request.",
    ]:
        assert teil in umsetzen, teil
    assert "bekommt ihren Link erst dann" not in umsetzen
    # Die Regel zum roten Lauf kommt nach dem Satz zum Warten, der bleibt.
    assert umsetzen.index("auf sein Ende warten muss sie") < umsetzen.index("Ist der letzte beendete Lauf")


def test_phase_steuern_prueft_vor_dem_auftrag_den_letzten_beendeten_lauf_auf_main():
    vor_dem_auftrag = _section(PHASE_STEUERN, "Aufträge").split("- **Vor dem Auftrag**", 1)[1].split("- **Den Auftrag**", 1)[0]

    assert (
        'und der Lauf auf `main` nicht dagegen spricht (`gh run list --workflow "Prüfungen" --branch main --limit 2`; '
        "Regel in `CLAUDE.md`, „Umsetzen“; außer für die Behebung selbst). "
        "Geht die Abfrage nicht, das offen sagen und Sebastian fragen."
    ) in vor_dem_auftrag
    assert "Dazu den Lauf auf `main` abfragen (Befehl in Abschnitt 2)." in _section(PHASE_STEUERN, "Einstieg")


def test_befehle_im_skill_nennen_den_namen_des_laufs_aus_der_pruefung_auf_github():
    name = re.search(r"^name: (.+)$", (BASE_DIR / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"), flags=re.M).group(1)

    for abschnitt in ["Aufträge", "Abschluss"]:
        assert f'gh run list --workflow "{name}"' in _section(PHASE_STEUERN, abschnitt), abschnitt


def test_contributing_lockert_keine_pruefbedingung_um_einen_lauf_gruen_zu_bekommen():
    section = _section(CONTRIBUTING, "Korrektheit und Tests")

    assert "**Eine Prüfbedingung wird nicht gelockert, um einen Lauf grün zu bekommen.**" in section
    assert (
        "Wird in einem bestehenden Test oder gegenüber einem Szenario oder Akzeptanzkriterium eine Zusicherung, ein Grenzwert "
        "oder ein Zeitfenster schwächer oder ein Test übersprungen, geschieht das nur in einem eigenen Issue, nie im selben Pull Request."
    ) in section
    assert (
        "Hat ein neuer Test eine Anforderung falsch übersetzt, wird er im selben Pull Request korrigiert; "
        "die Beschreibung nennt das unveränderte Kriterium, vorher und nachher."
    ) in section
    assert (
        "Das ist die einzige Ausnahme vom Punkt davor: Das Issue nennt die unveränderte Anforderung und warum die bisherige "
        "Prüfung falsch war, und Sebastian entscheidet."
    ) in section
    assert "Ein roter Lauf allein ist für beides kein Grund. (Review)" in section
    # Der Satz zu bestehenden Tests bleibt, die neue Regel steht dahinter.
    assert section.index("Bestehende Tests werden nur geändert oder gelöscht") < section.index("Eine Prüfbedingung wird nicht gelockert")


def test_jeder_neustart_kommt_als_kommentar_ins_issue_wackelnde_pruefungen():
    pull_request = _section(CLAUDE_MD, "Ablauf je Aufgabe").split("6. **Pull Request**", 1)[1]

    assert (
        "Jeder Neustart, auch auf `main` und durch Sebastian, kommt als Kommentar mit Link zum Lauf, Commit, Versuch und Grund "
        "ins Issue „Wackelnde Prüfungen“ (#243); das erlaubt keinen weiteren Neustart."
    ) in pull_request
    # Der Neustart ohne Rückfrage bleibt, wie er war.
    assert "darf die KI ihn einmal pro Stand ohne Rückfrage neu starten" in pull_request


def test_entscheidung_zu_aufraeumen_rueckblick_rotem_main_und_neustarts_nennt_freigabe_regel_und_grenzen():
    entries = re.split(r"^## ", ENTSCHEIDUNGEN.read_text(encoding="utf-8"), flags=re.M)
    entry = next((e for e in entries if e.split("\n", 1)[0].endswith("(#245)")), None)

    assert entry, "Eintrag zu #245 fehlt in docs/entscheidungen.md"
    assert entry.startswith("2026-11-04 · ")
    flat = _flat(entry)
    for teil in ["E-074", "E-075", "E-078", "G-11", "G-12", "Aufräumen", "Rückblick", "`main`", "#243", "CONTRIBUTING.md"]:
        assert teil in flat, teil
    # Die Übersicht „Geltende Grundsätze“ wird nur fortgeschrieben, wenn der Eintrag etwas ersetzt; er sagt, was gilt.
    assert "ersetzt keinen" in flat or "ersetzt den Eintrag vom" in flat


# --- Vorschau vor dem Pull Request (#249) -------------------------------------------------------


def _vorschau_regel():
    rules = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    assert "**Vorschau:**" in rules, "Regel „Vorschau“ fehlt unter „Für die Umsetzung gilt außerdem“"
    return rules.split("**Vorschau:**", 1)[1].split("- **Nachziehen:**", 1)[0]


def test_vorschau_steht_unter_fuer_die_umsetzung_vor_nachziehen_ohne_neue_nummer():
    section = _section(CLAUDE_MD, "Ablauf je Aufgabe")
    umsetzung = section.split("Für die Umsetzung gilt außerdem", 1)[1]

    assert "- **Vorschau:**" in umsetzung
    assert umsetzung.index("- **Vorschau:**") < umsetzung.index("- **Nachziehen:**")
    assert not re.search(r"(?:^| )7\. \*\*", section), "Die Nummern 1 bis 6 bleiben; die Vorschau ist keine Nummer 7"
    assert not re.search(r"\d\. \*\*Vorschau", section)


def test_vorschau_wann_und_was_wird_gezeigt():
    rule = _vorschau_regel()

    assert "Ändert ein Issue, was man auf einer Seite sieht oder bedient" in rule
    assert "auch Fehlerseiten, Meldungen und den Bausteinkatalog; nicht Mails und nicht reine Tests" in rule
    assert "zeigt die KI Sebastian das Ergebnis, nachdem die Tests rot waren und bevor die unabhängige Prüfung beginnt" in rule
    assert "eine HTML-Datei aus den echten Vorlagen mit erfundenen Daten (Skill `vorschau`)" in rule
    assert "Sie nennt dabei, was die Datei nicht zeigt" in rule
    assert "lokal ausprobiert wird nur auf seinen Wunsch (`README.md`, „Pull Request lokal ausprobieren“)" in rule


def test_vorschau_verzicht_nur_durch_die_klaerung_mit_zeile_im_issue():
    rule = _vorschau_regel()

    assert "Verzichten kann nur die Klärung, mit der Zeile „Vorschau: keine.“ und dem Grund im Text des Issues" in rule


def test_vorschau_anmerkungen_aussehen_direkt_verhalten_ueber_die_nachklaerung():
    rule = _vorschau_regel()

    assert "Anmerkungen zu Aussehen, Abständen und gleichbedeutendem Wortlaut setzt die KI direkt um" in rule
    assert "auch wenn ein Szenario den alten Text nennt, und zeigt die neue Fassung" in rule
    assert "`geklärt` bleibt, und der Text des Issues hält die Änderung fest" in rule
    assert "Ändern sich Voraussetzung, Handlung, Ergebnis oder Rechte eines Szenarios, oder kommt eines dazu" in rule
    assert "gilt „Neuer Inhalt zu einem geklärten Issue“, mit neuer Fassung der Szenarien" in rule


def test_vorschau_laesst_bausteine_und_zielbild_gelten_und_fordert_okay_im_kommentar():
    rule = _vorschau_regel()

    assert "„Bausteine einbinden“ und „Zielbild vor Gestaltung“ gelten weiter" in rule
    assert "Der Kommentar „Vorschau (Datum)“ im Issue hält beim Zeigen den Stand fest" in rule
    assert "danach Sebastians Anmerkungen und sein Okay in seinen Worten; der Pull Request verlinkt ihn" in rule
    assert "Ohne dieses Okay beginnt die unabhängige Prüfung nicht" in rule
    assert "Ändert sich danach noch etwas Sichtbares, zeigt sie es erneut" in rule


def test_neuer_inhalt_zu_einem_geklaerten_issue_nimmt_die_vorschau_anmerkungen_aus():
    section = _section(CLAUDE_MD, "Ablauf einer Phase")
    rule = section.split("**Neuer Inhalt zu einem geklärten Issue**", 1)[1].split("- **Labels:**", 1)[0]

    assert "Ausgenommen sind Anmerkungen aus der Vorschau zu Aussehen, Abständen und gleichbedeutendem Wortlaut" in rule
    assert "(Punkt „Vorschau“ unter „Für die Umsetzung gilt außerdem“)" in rule
    assert rule.rstrip().endswith("(Punkt „Vorschau“ unter „Für die Umsetzung gilt außerdem“).")


def test_reihenfolge_szenarien_tests_code_bleibt():
    step = _schritt(3)

    assert "Szenarien vor Code:" in step
    assert "sie müssen fehlschlagen, und zwar aus dem richtigen Grund" in step
    assert "Erst dann kommt der Code" in step
    for nummer in range(1, 7):
        assert _schritt(nummer)


def test_grill_me_fragt_nach_der_vorschau_nach_dem_zielbild():
    themen = _section(GRILL_ME, "Übersicht zeigen")

    assert "- **Vorschau:**" in themen
    assert themen.index("**Zielbild:**") < themen.index("**Vorschau:**") < themen.index("**Abhängigkeiten:**")
    thema = themen.split("**Vorschau:**", 1)[1].split(" - **", 1)[0]
    assert "gehört sie zur Umsetzung (`CLAUDE.md`, „Vorschau“)" in thema
    assert "Spricht etwas dagegen, entscheidet Sebastian über den Verzicht; die Zeile dazu kommt in den Text des Issues" in thema


def test_skill_vorschau_hat_kopf_und_vier_schritte():
    text = VORSCHAU.read_text(encoding="utf-8")
    kopf = text.split("---", 2)[1]
    ueberschriften = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)

    assert "name: vorschau" in kopf
    assert "description: Eine sichtbare Änderung vor dem Pull Request als HTML-Datei aus den echten Vorlagen zeigen." in kopf
    assert "Verwenden, sobald bei einem Issue mit sichtbarer Änderung die Seite steht und die Tests vorher rot waren." in kopf
    assert text.index("# Vorschau: das Ergebnis zeigen, bevor der Pull Request entsteht") > 0
    assert [u.split(".")[0] for u in ueberschriften] == ["1", "2", "3", "4"]
    assert ueberschriften == ["1. Fälle wählen", "2. Datei erzeugen", "3. Zeigen", "4. Antwort festhalten"]


def test_skill_vorschau_verweist_fuer_die_regel_auf_claude_md():
    text = _text(VORSCHAU)

    assert "Wann sie nötig ist und was aus Anmerkungen wird: `CLAUDE.md`, Punkt „Vorschau“. Hier steht nur der Handgriff." in text


def test_skill_vorschau_erzeugt_die_datei_mit_dem_helfer_und_loescht_den_test():
    text = _section(VORSCHAU, "Datei erzeugen")

    assert "`tests/test_zz_vorschau_<nummer>.py`" in text
    assert "git ignoriert ihn" in text
    assert "`schreibe_vorschau` aus `tests/vorschau.py`" in text
    assert "`lokal/vorschau-<nummer>.html`" in text
    assert "Gleich danach den vorübergehenden Test löschen, sonst liefe er im vollen Prüflauf mit" in text
    assert "braucht keinen laufenden Server" in text
    assert "Nicht gleichzeitig mit einem anderen Prüflauf derselben Arbeitskopie" in text


def test_skill_vorschau_zeigen_committet_zuerst_und_prueft_ob_der_ordner_den_stand_kennt():
    text = _section(VORSCHAU, "Zeigen")

    assert "Den Stand committen; die Tests liegen schon als eigener Commit davor." in text
    assert "Dann den Kommentar „Vorschau (Datum)“ ins Issue" in text
    assert "„wartet auf Sebastian“" in text
    assert "Links und Speichern sind gesperrt, Neuladen und Springen der Seite sind nicht zu sehen" in text
    assert "„Pull Request lokal ausprobieren“ im `README.md`" in text
    assert "git -C ~/Entwicklung/dpv-participant-management cat-file -e <kennung>" in text
    assert "sonst den Zweig hochladen, ohne Pull Request" in text


def test_skill_vorschau_haelt_anmerkungen_im_vorschau_kommentar_nicht_bei_den_szenarien():
    text = _section(VORSCHAU, "Antwort festhalten")

    assert "Sebastians Anmerkungen wörtlich" in text
    assert "sein Okay wörtlich" in text
    assert "Den Kommentar „Szenarien (Datum)“ nicht bearbeiten, sonst wird die Prüfung „PR-Angaben“ rot" in text
    assert "gilt `CONTRIBUTING.md`, Abschnitt 3: erst der Test, dann der Code" in text
    assert "nennt die neue Fassung die anderen Seiten, die sich mitändern" in text


def test_vorlage_hat_den_abschnitt_vorschau_zwischen_nutzende_und_zielbild():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    ueberschriften = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    abschnitt = _section(PR_TEMPLATE, "Vorschau")

    assert ueberschriften.index("Was sich für Nutzende ändert") + 1 == ueberschriften.index("Vorschau")
    assert ueberschriften.index("Vorschau") + 1 == ueberschriften.index("Zielbild")
    assert "Link zum Kommentar „Vorschau (Datum)“ im Issue (CLAUDE.md, „Vorschau“)" in abschnitt
    assert "Ohne sichtbare Änderung „nicht nötig“ mit Grund; bei einem Verzicht der Grund aus dem Issue" in abschnitt
    assert "Der Link steht hier, nicht unter „Wie geprüft wurde“" in abschnitt
    assert "„PR-Angaben“ jeden Kommentar-Link als Szenarien-Link" in abschnitt


def test_readme_erklaert_den_pull_request_lokal_auszuprobieren():
    readme = BASE_DIR / "README.md"
    text = readme.read_text(encoding="utf-8")
    ueberschriften = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    abschnitt = _section(readme, "Pull Request lokal ausprobieren")

    assert ueberschriften.index("Pull Request lokal ausprobieren") + 1 == ueberschriften.index("Testumgebung im Container (Mac)")
    assert abschnitt.startswith("Setzt eine eingerichtete Umgebung voraus (Schritte 1 bis 5 unter „Projekt starten (Mac)“).")
    for befehl in [
        "cd ~/Entwicklung/dpv-participant-management",
        "git fetch origin",
        "git switch --detach origin/<zweig>",
        "uv sync",
        "docker compose -f dev/docker-compose.yml up -d --wait",
        "git diff --name-only origin/main...HEAD -- '*/migrations/*'",
        "uv run --env-file .env python manage.py migrate",
        "uv run --env-file .env python manage.py runserver",
        "git switch main",
    ]:
        assert befehl in abschnitt, befehl
    assert abschnitt.count("Danach:") >= 6
    assert "vor dem Pull Request statt `origin/<zweig>` die Kennung, die die Sitzung nennt" in abschnitt
    assert "`--detach` holt nur den Stand, ohne den Zweig zu belegen." in abschnitt
    assert "scheitert mit `is already used by worktree`" in abschnitt
    assert "nennt die Sitzung vorher den Befehl zum Zurückstellen und sagt, ob er alles wiederherstellt" in abschnitt
    assert "einen festen Befehl für Testdaten bringt #103" in abschnitt
    assert "solange der Stand noch ausgecheckt ist, denn auf `main` fehlen die Dateien dazu" in abschnitt
    # Reihenfolge: Zurückstellen vor dem Wechsel auf main
    assert abschnitt.index("Zurückstellen ausführen") < abschnitt.index("git switch main")


def test_entscheidung_zur_vorschau_nennt_was_sie_ersetzt_und_steht_in_der_uebersicht():
    text = ENTSCHEIDUNGEN.read_text(encoding="utf-8")
    uebersicht = text.split("## Geltende Grundsätze", 1)[1].split("\n---\n", 1)[0]
    eintraege = re.split(r"^## ", text, flags=re.M)
    eintrag = next((e for e in eintraege if e.split("\n", 1)[0].endswith("(#249)")), None)

    assert eintrag, "Eintrag zu #249 fehlt in docs/entscheidungen.md"
    assert eintrag.startswith("2026-11-04 · ")
    flat = _flat(eintrag)
    assert "ersetzt den Eintrag vom 26.10.2026 (#169), Punkt 2, nur für Anmerkungen aus der Vorschau zu Aussehen, Abständen und gleichbedeutendem Wortlaut" in flat
    assert "Vorschau" in uebersicht
    assert "#249" in uebersicht
    assert "26.10.2026, #169, Nr. 2" in _flat(uebersicht.split("Vorschau", 1)[1].split("\n", 1)[0])
    assert "Vorschau" in eintrag.split("\n", 1)[0]
    assert text.index(eintrag.split("\n", 1)[0]) < text.index("(#245)"), "Neue Einträge stehen oben"
