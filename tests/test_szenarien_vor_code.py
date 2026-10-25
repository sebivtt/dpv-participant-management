"""Tests für die Regel „Szenarien vor Code“ (Issue #158).

Bei #90, #64 und #8 fiel der Schritt aus, weil die Aufträge ihn nicht nannten und nichts die
Umsetzung anhielt. Entschieden ist (#158, 25.10.2026): Ohne den Kommentar „Szenarien (Datum)“
im Issue hält die KI an, auch wenn der Auftrag den Schritt nicht nennt. Diese Tests sorgen
dafür, dass die Regel nicht still aus CLAUDE.md, der Vorlage für Pull Requests oder grill-me
verschwindet. Ob sich eine KI daran hält, prüfen sie nicht.
"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
PR_TEMPLATE = BASE_DIR / ".github" / "pull_request_template.md"
GRILL_ME = BASE_DIR / ".claude" / "skills" / "grill-me" / "SKILL.md"


def _text(path):
    return " ".join(path.read_text(encoding="utf-8").split())


def _sentence_after(text, start):
    match = re.search(re.escape(start) + r"[^.]*\.(?:[^.]*\.){0,2}", text)
    assert match, f"Regel fehlt: {start}"
    return match.group(0)


def test_ohne_szenarien_haelt_die_ki_an_auch_wenn_der_auftrag_den_schritt_nicht_nennt():
    rule = _sentence_after(_text(CLAUDE_MD), "Direkt vor dem Start prüft die KI außerdem")

    assert "„Szenarien (Datum)“" in rule
    assert "hält sie an" in rule
    assert "statt mit Tests oder Code zu beginnen" in rule
    assert "auch, wenn der Auftrag den Schritt nicht nennt" in rule
    assert "ein Auftrag hebt ihn nie auf" in rule


def test_auftraege_nennen_den_schritt_und_nur_die_klaerung_erlaubt_das_weglassen():
    rule = _sentence_after(_text(CLAUDE_MD), "Aufträge an andere Sessions nennen den Schritt")

    assert "ausdrücklich" in rule
    assert "wenn die Klärung festhält, dass das Issue kein fachliches Verhalten hat" in rule
    assert "im Auftrag und im Pull Request" in rule


def test_vorlage_fuer_pull_requests_fragt_nach_den_szenarien():
    text = PR_TEMPLATE.read_text(encoding="utf-8")
    checks = text.split("## Wie geprüft wurde", 1)[1].split("\n## ", 1)[0]
    first = next(line for line in checks.splitlines() if line.startswith("- "))

    assert first.startswith("- Szenarien")
    assert "„Szenarien (Datum)“" in first


def test_grill_me_sammelt_die_szenarien_vor_dem_label_geklaert():
    text = GRILL_ME.read_text(encoding="utf-8")
    headings = re.findall(r"^## (.+)$", text, flags=re.MULTILINE)
    scenarios = next(h for h in headings if "Szenarien" in h)
    release = next(h for h in headings if "Freigeben" in h)

    assert "**Fachliches Verhalten:**" in text
    assert headings.index(scenarios) < headings.index(release)
    release_text = " ".join(text.split("## " + release, 1)[1].split("\n## ", 1)[0].split())
    assert "„Szenarien (Datum)“" in release_text
    assert "keine Szenarien braucht" in release_text
