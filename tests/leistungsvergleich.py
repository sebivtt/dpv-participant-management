"""Vergleich des Leistungstests mit dem Ende der vorigen Phase (#145, NFA-05).

Der Ablauf „Leistungstest“ auf GitHub (`.github/workflows/leistungstest.yml`) misst in einem einzigen Lauf auf
demselben Rechner abwechselnd den Stand vom Ende der vorigen Phase („alt“, die Markierung `phasenende-p<n>`)
und den neuen Stand („neu“), jeden mit `tests/leistungstest.py` und denselben erzeugten Daten. Jeder
Durchgang schreibt seine Zeiten in eine Datei; dieses Skript fasst sie zusammen und vergleicht.

Grenzen (Text von #145, `docs/entscheidungen.md`, 14.11.2026, #145):

- 2 Sekunden oder mehr auf einer Seite: rot, blockiert immer.
- Mehr als 25 % langsamer als der alte Stand: Die Phase hält an, bis Sebastian entschieden hat.
- Darunter steht der Wert nur im Ergebnis. Seiten ohne Wert vom alten Stand prüfen nur gegen die 2 Sekunden.

Die Ausgabe ist der Abschnitt für `docs/leistungstest.md`. Nur Standardbibliothek, damit das Skript ohne
Django und ohne Pakete läuft.

Aufruf im Ablauf:
    python3 tests/leistungsvergleich.py pruefen --phase P3 --vorige phasenende-p2
    python3 tests/leistungsvergleich.py auswerten --phase P3 --vorige phasenende-p2 --commit <sha> \\
        --alt alt-1.json alt-2.json --neu neu-1.json neu-2.json
"""

import argparse
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

LIMIT = 2.0
SLOWER = 0.25
# Am Ende von P2 gibt es noch keine vorige Phase; der erste Lauf legt den Ausgangswert ab.
FIRST_PHASE = 2
PHASE = re.compile(r"P([1-9]\d*)")

VERDICTS = {
    "gruen": "im Rahmen",
    "anhalten": "mehr als 25 % langsamer: Sebastian entscheidet",
    "rot": "2 s oder mehr: blockiert",
}


def marker(phase: str) -> str:
    """Die feste Markierung im Repo für das Ende einer Phase, etwa „phasenende-p2“ für P2."""
    found = PHASE.fullmatch(phase)
    if not found:
        raise ValueError(f"Phase wie „P3“ erwartet, nicht „{phase}“.")
    return f"phasenende-p{found.group(1)}"


def check_inputs(phase: str, previous: str) -> None:
    """Die vorige Phase muss die direkt vorige sein; ohne sie geht es nur am Ende von P2."""
    number = int(marker(phase).removeprefix("phasenende-p"))
    if number == FIRST_PHASE:
        expected = ""
    elif number > FIRST_PHASE:
        expected = marker(f"P{number - 1}")
    else:
        raise ValueError(f"Den Leistungstest gibt es erst ab dem Ende von P{FIRST_PHASE}.")
    if previous != expected:
        wanted = f"„{expected}“" if expected else "leer"
        raise ValueError(f"Vorige Phase zu {phase}: {wanted}, nicht „{previous}“.")


def seconds(value: float) -> str:
    """Sekunden mit Komma und zwei Stellen, z. B. „0,61 s“."""
    return f"{value:.2f} s".replace(".", ",")


def percent(change: float) -> str:
    """Abweichung mit Vorzeichen und Komma, z. B. „+33,3 %“."""
    return f"{change * 100:+.1f} %".replace(".", ",")


def load(paths: list[str]) -> tuple[dict[str, list[float]], list[str]]:
    """Die Zeiten je Seite aus allen Durchgängen zusammen, dazu die Seiten ohne Messung aus dem letzten."""
    times: dict[str, list[float]] = {}
    unmeasured: list[str] = []
    for path in paths:
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        for page, values in content["seiten"].items():
            times.setdefault(page, []).extend(values)
        unmeasured = content["ohne_messung"]
    return times, unmeasured


def compare(new: dict[str, list[float]], old: dict[str, list[float]] | None) -> list[dict]:
    """Je Seite des neuen Stands: mittlere Zeit, Wert des alten Stands, Abweichung und Ergebnis."""
    rows = []
    for page, values in new.items():
        time = statistics.median(values)
        previous = statistics.median(old[page]) if old and old.get(page) else None
        change = time / previous - 1 if previous else None
        if time >= LIMIT:
            verdict = "rot"
        elif change is not None and change > SLOWER:
            verdict = "anhalten"
        else:
            verdict = "gruen"
        rows.append({"page": page, "time": time, "previous": previous, "change": change, "verdict": verdict})
    return rows


def section(rows: list[dict], *, phase: str, previous: str, commit: str, day: str, unmeasured: list[str],
            dropped: list[str]) -> str:
    """Der Abschnitt einer Phase für `docs/leistungstest.md`."""
    if previous:
        intro = (f"Lauf vom {day}, Commit `{commit[:7]}`, verglichen mit `{previous}`: beide Stände abwechselnd "
                 "im selben Lauf mit denselben erzeugten Daten.")
    else:
        intro = (f"Lauf vom {day}, Commit `{commit[:7]}`. Ausgangswert: Es gibt noch keine vorige Phase, jede Seite "
                 "prüft nur gegen die 2 Sekunden.")
    lines = [f"## {phase}", "", intro, "",
             "| Seite | Zeit | Wert der vorigen Phase | Abweichung | Ergebnis |", "|---|---|---|---|---|"]
    for row in rows:
        before = seconds(row["previous"]) if row["previous"] is not None else "–"
        if row["change"] is not None:
            change = percent(row["change"])
        else:
            change = "neue Seite" if previous else "–"
        lines.append(f"| {row['page']} | {seconds(row['time'])} | {before} | {change} | {VERDICTS[row['verdict']]} |")
    lines.append("")
    lines.append("Seiten mit Personen ohne Messung: " + (", ".join(f"`{name}`" for name in unmeasured) or "keine")
                 + ".")
    if dropped:
        lines.append("Am Ende der vorigen Phase gemessen, jetzt nicht mehr gemessen: " + ", ".join(dropped) + ".")
    return "\n".join(lines) + "\n"


def _say(text: str) -> None:
    sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Leistungstest am Phasenende auswerten (#145).")
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("pruefen", "auswerten"):
        action = actions.add_parser(name)
        action.add_argument("--phase", required=True)
        action.add_argument("--vorige", default="")
        if name == "auswerten":
            action.add_argument("--commit", required=True)
            action.add_argument("--alt", nargs="*", default=[])
            action.add_argument("--neu", nargs="+", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """`pruefen`: Eingaben prüfen. `auswerten`: Abschnitt ausgeben; 1, wenn eine Seite rot ist oder anhält."""
    args = _arguments(argv)
    try:
        check_inputs(args.phase, args.vorige)
    except ValueError as error:
        _say(f"Falsche Eingabe: {error}")
        return 1
    if args.action == "pruefen":
        return 0
    missing = [path for path in [*args.alt, *args.neu] if not Path(path).is_file()]
    if missing or (args.vorige and not args.alt):
        _say("Ergebnis fehlt, ein Durchgang hat keine Zeiten geschrieben: " + (", ".join(missing) or "alter Stand"))
        return 1
    new, unmeasured = load(args.neu)
    old = load(args.alt)[0] if args.alt else None
    if not new:
        _say("Ergebnis fehlt: Der neue Stand hat keine Seite gemessen.")
        return 1
    rows = compare(new, old)
    dropped = sorted(set(old or {}) - set(new))
    _say(section(rows, phase=args.phase, previous=args.vorige, commit=args.commit,
                 day=date.today().strftime("%d.%m.%Y"), unmeasured=unmeasured, dropped=dropped))
    return 0 if all(row["verdict"] == "gruen" for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
