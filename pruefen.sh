#!/bin/sh
# Die automatischen Prüfungen aus CONTRIBUTING.md mit einem Befehl:
#   ./pruefen.sh                              alle acht Prüfungen (GitHub ruft genau das auf)
#   ./pruefen.sh schnell [Testdatei ...]      lokal meist der schnelle Lauf: Paketliste, ruff,
#                                             Django-Systemprüfung, Migrationen und nur die
#                                             genannten Dateien aus tests/ und rauchtests/
#                                             (CLAUDE.md, Ablauf je Aufgabe Nr. 4)
# Gleiches Skript lokal und auf GitHub; den vollen Lauf macht dort die Prüfung. Jede Prüfung
# läuft, auch wenn eine frühere rot war, damit man alle Befunde auf einmal sieht. Am Ende
# steht, ob alles grün ist, wie viele Tests übersprungen wurden und, im schnellen Lauf, was
# nicht ausgewählt war.

set -u
cd "$(dirname "$0")"

usage_error() {
    echo "pruefen.sh: $1" >&2
    echo "Aufruf: ./pruefen.sh   oder   ./pruefen.sh schnell [Testdatei aus tests/ oder rauchtests/ ...]" >&2
    exit 2
}

mode="voll"
tests_files=""
rauch_files=""
if [ "${1:-}" = "schnell" ]; then
    mode="schnell"
    shift
    for arg in "$@"; do
        case "$arg" in
            -*) usage_error "Unbekannte Option: $arg" ;;
            *[[:space:]]*) usage_error "Leerzeichen im Dateinamen werden nicht unterstützt: $arg" ;;
        esac
        case "/$arg/" in
            */../*) usage_error "Nur Dateien aus tests/ oder rauchtests/ sind erlaubt: $arg" ;;
        esac
        case "$arg" in
            tests/*) tests_files="$tests_files $arg" ;;
            rauchtests/*) rauch_files="$rauch_files $arg" ;;
            *) usage_error "Nur Dateien aus tests/ oder rauchtests/ sind erlaubt: $arg" ;;
        esac
        [ -f "$arg" ] || usage_error "Die Datei gibt es nicht: $arg"
    done
elif [ "$#" -gt 0 ]; then
    usage_error "Unbekannte Option: $1"
fi

# Lokal kommen die Zugangsdaten aus .env, auf GitHub aus dem Prüfablauf selbst.
# --locked: uv run würde uv.lock sonst still an pyproject.toml angleichen, und ein
# rotes „uv lock --check“ wäre beim nächsten Lauf unbemerkt grün.
if [ -f .env ]; then
    run="uv run --locked --env-file .env"
else
    run="uv run --locked"
fi

failed=""
count_skips=0
skipped_total=0
skipped_unknown=0

duration_text() {
    if [ "$1" -ge 60 ]; then
        echo "$(($1 / 60)) min $(($1 % 60)) s"
    else
        echo "$1 s"
    fi
}

count_skipped() {
    # Die Zusammenfassung von pytest ist die letzte Zeile mit „… in 1.23s“. Fehlt sie, ist die
    # Zahl unbekannt; sie wird nie als 0 gezählt.
    summary="$(grep -E ' in [0-9.]+s( \([0-9:]+\))?( =+)?$' "$1" | tail -n 1)"
    if [ -z "$summary" ]; then
        skipped_unknown=1
        return 0
    fi
    skipped="$(echo " $summary" | sed -n -E 's/.*[^0-9]([0-9]+) skipped.*/\1/p')"
    skipped_total=$((skipped_total + ${skipped:-0}))
}

check() {
    name="$1"
    shift
    echo ""
    echo "=== $name"
    output="$(mktemp)"
    status="$(mktemp)"
    started="$(date +%s)"
    # Ausgabe mitschreiben, damit auf GitHub die roten Tests als Hinweise erscheinen können.
    { "$@"; echo $? > "$status"; } 2>&1 | tee "$output"
    took="$(duration_text $(($(date +%s) - started)))"
    if [ "$(cat "$status")" = "0" ]; then
        echo "--> grün: $name ($took)"
    else
        echo "--> ROT: $name ($took)"
        failed="$failed
  - $name"
        report_on_github "$name" "$output"
    fi
    if [ "$count_skips" = "1" ]; then
        count_skipped "$output"
    fi
    rm -f "$output" "$status"
}

# Wie check, zählt aber die von pytest übersprungenen Tests mit.
check_tests() {
    count_skips=1
    check "$@"
    count_skips=0
}

report_on_github() {
    # Nur auf GitHub: Die Namen der roten Tests und ihr Grund in einer Zeile werden zu Hinweisen
    # am Prüflauf („annotations“). Die lassen sich auch ohne Zugriff auf das volle Protokoll
    # lesen. Die Tests arbeiten nur mit erfundenen Daten.
    [ -n "${GITHUB_ACTIONS:-}" ] || return 0
    # GitHub zeigt je Schritt höchstens zehn Fehler und zehn Warnungen. Deshalb je Prüfung eine
    # Zeile als Fehler und die roten Tests als Warnungen, damit jede rote Prüfung sichtbar bleibt.
    echo "::error title=ROT::$1"
    grep -E '^(FAILED|ERROR) [A-Za-z_]+/' "$2" | head -n 5 | cut -c1-300 | sed 's/^/::warning title=Test::/'
}

audit_packages() {
    # Geprüft werden genau die festen Fassungen aus uv.lock, auch die Pakete nur zum Prüfen.
    list="$(mktemp)"
    uv export --frozen --format requirements-txt --no-emit-project --quiet -o "$list" &&
        $run pip-audit --disable-pip --require-hashes -r "$list"
    result=$?
    rm -f "$list"
    return $result
}

check "Liste mit festen Fassungen passt zur Paketliste (uv lock --check)" uv lock --check
check "Code-Regeln (ruff)" $run ruff check .
check "Django-Systemprüfung" $run python manage.py check
check "Fehlen Migrationen?" $run python manage.py makemigrations --check --dry-run
if [ "$mode" = "voll" ]; then
    check_tests "Tests (pytest)" $run pytest -rsfE
else
    # shellcheck disable=SC2086  # Die Dateinamen sind absichtlich eine Liste (ohne Leerzeichen).
    [ -z "$tests_files" ] || check_tests "Tests (pytest):$tests_files" $run pytest -rsfE $tests_files
fi
# Eigener Lauf: Playwright betreibt eine Ereignisschleife, neben der Django Datenbankzugriffe
# sonst abbricht (rauchtests/conftest.py). Braucht die Browser (README.md, Schritt 10) und
# einen eigenen Port (tests/check_ports.py), nicht Port 8000 des eigenen Tools (#167).
if [ "$mode" = "voll" ]; then
    check_tests "Rauchtest im Browser mit Prüfung auf Barrierefreiheit (Playwright, axe)" \
        env DJANGO_ALLOW_ASYNC_UNSAFE=true $run pytest rauchtests -rsfE
else
    [ -z "$rauch_files" ] || check_tests "Rauchtest im Browser (Playwright, axe):$rauch_files" \
        env DJANGO_ALLOW_ASYNC_UNSAFE=true $run pytest -rsfE $rauch_files
fi
# Eigener Lauf: baut das Container-Abbild und startet die Testumgebung so, wie sie nach dem
# README startet (#58). Braucht Docker und eigene Ports (tests/check_ports.py); das eigene Tool
# und die eigene Testumgebung auf 8000 und 8081 dürfen weiterlaufen (#167). Nur im vollen Lauf.
if [ "$mode" = "voll" ]; then
    check_tests "Testumgebung im Container (Docker)" $run pytest containertests -rsfE
    check "Bekannte Sicherheitslücken in Paketen (pip-audit)" audit_packages
fi

# Schlussmeldung für beide Betriebsarten: was gelaufen ist, was übersprungen wurde und, im
# schnellen Lauf, was nicht ausgewählt war. Grün heißt „alles Ausgewählte ist gelaufen“.
if [ "$skipped_unknown" = "1" ]; then
    skipped_text="Zahl unbekannt (die Zusammenfassung von pytest fehlt)"
else
    skipped_text="$skipped_total"
fi
not_selected=""
if [ "$mode" = "schnell" ]; then
    if [ -z "$tests_files" ]; then not_selected="alle Tests"; else not_selected="übrige Tests"; fi
    if [ -z "$rauch_files" ]; then
        not_selected="$not_selected, alle Rauchtests"
    else
        not_selected="$not_selected, übrige Rauchtests"
    fi
    not_selected="$not_selected, Testumgebung im Container, pip-audit"
fi

echo ""
if [ "$mode" = "schnell" ]; then
    echo "Betriebsart: schneller Lauf"
else
    echo "Betriebsart: voller Lauf"
fi
echo "Übersprungene Tests: $skipped_text"
if [ -n "$failed" ]; then
    [ -z "$not_selected" ] || echo "Nicht ausgewählt: $not_selected"
    echo "ROT. Nicht bestanden:$failed"
    exit 1
fi

if [ "$skipped_unknown" = "1" ]; then
    skipped_line=", übersprungene Tests: $skipped_text"
elif [ "$skipped_total" -gt 0 ]; then
    skipped_line=", $skipped_total Tests übersprungen (Gründe oben unter SKIPPED)"
else
    skipped_line=""
fi
if [ "$mode" = "schnell" ]; then
    echo "Schneller Lauf grün$skipped_line. Nicht ausgewählt: $not_selected."
elif [ -z "$skipped_line" ]; then
    echo "Alle Prüfungen grün."
else
    echo "Alle gelaufenen Prüfungen grün$skipped_line."
fi
exit 0
