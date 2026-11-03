"""Erinnerung nach einer automatischen Zusammenfassung in Claude Code (#240, `CLAUDE.md`, „Steuerungssession und Umsetzungs-Sessions“).

Claude Code ruft diese Datei beim Fortsetzen einer Sitzung auf (`.claude/settings.json`, Hook
`SessionStart` mit Auslöser `compact`) und übergibt als JSON auf der Standardeingabe unter `source`,
warum die Sitzung beginnt. Nur bei `compact`, also nach einer automatischen Zusammenfassung, gibt
der Hook den Verweis aus; die Ausgabe kommt als Hinweis in die fortgesetzte Sitzung. Bei jedem
anderen Auslöser und bei kaputter Eingabe gibt er nichts aus. Er endet immer mit Exit 0: Er erinnert
nur, er beendet keine Sitzung und stört keine.
"""

import contextlib
import json
import sys

HINWEIS = "Claude Code hat das Gespräch zusammengefasst. Weiter nach `CLAUDE.md`, „Steuerungssession und Umsetzungs-Sessions“."


def main():
    # Kaputte Eingabe darf nie eine Sitzung stören: dann keine Ausgabe, Exit 0.
    with contextlib.suppress(Exception):
        daten = json.load(sys.stdin)
        if isinstance(daten, dict) and daten.get("source") == "compact":
            sys.stdout.write(HINWEIS + "\n")


if __name__ == "__main__":
    main()
