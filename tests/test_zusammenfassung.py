"""Tests für den Hook `.claude/hooks/zusammenfassung.py` (#240, Paket P-04b der Projektprüfung).

Claude Code ruft den Hook beim Fortsetzen einer Sitzung auf (`SessionStart`) und übergibt als JSON
auf der Standardeingabe unter `source`, warum die Sitzung beginnt. Nach einer automatischen
Zusammenfassung ist das `compact`. Nur dann gibt der Hook den Verweis auf `CLAUDE.md` aus, sonst
nichts. Er erinnert nur und beendet keine Sitzung; bei kaputter Eingabe schweigt er und endet
mit Exit 0, damit er nie eine Sitzung stört.

Die Tests rufen den Hook so auf wie Claude Code: als eigenes Programm mit JSON auf der Standardeingabe.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
HOOK = BASE_DIR / ".claude" / "hooks" / "zusammenfassung.py"
HINWEIS = "Claude Code hat das Gespräch zusammengefasst. Weiter nach `CLAUDE.md`, „Steuerungssession und Umsetzungs-Sessions“."


def _run(payload):
    return subprocess.run(  # noqa: S603 -- fester Aufruf des eigenen Hooks mit erfundener Eingabe
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=BASE_DIR,
        timeout=30,
    )


def test_nach_einer_zusammenfassung_gibt_der_hook_nur_den_verweis_aus():
    result = _run(json.dumps({"source": "compact", "hook_event_name": "SessionStart"}))

    assert result.returncode == 0
    assert result.stdout.strip() == HINWEIS
    assert result.stderr == ""


@pytest.mark.parametrize("source", ["startup", "resume", "clear", "", None, 5])
def test_bei_anderen_ausloesern_schweigt_der_hook(source):
    result = _run(json.dumps({"source": source}))

    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("payload", ["", "kein json", "[1, 2]", "null", '{"source": ', '{"ohne": "source"}'])
def test_bei_kaputter_eingabe_schweigt_der_hook_und_endet_mit_exit_0(payload):
    result = _run(payload)

    assert result.returncode == 0
    assert result.stdout == ""


def test_der_verweis_nennt_einen_abschnitt_der_in_claude_md_steht():
    text = (BASE_DIR / "CLAUDE.md").read_text(encoding="utf-8")

    assert "## Steuerungssession und Umsetzungs-Sessions" in text
