#!/bin/sh
# Die automatischen Prüfungen aus CONTRIBUTING.md mit einem Befehl:
#   ./pruefen.sh                              alle acht Prüfungen nacheinander (lokal; GitHub
#                                             startet dieselben in Teilen, siehe unten)
#   ./pruefen.sh schnell [Testdatei ...]      lokal meist der schnelle Lauf: Paketliste, ruff,
#                                             Django-Systemprüfung, Migrationen und nur die
#                                             genannten Dateien aus tests/ und rauchtests/
#                                             (CLAUDE.md, Ablauf je Aufgabe Nr. 4)
#   ./pruefen.sh teil <name>                  nur ein Teil des vollen Laufs; GitHub startet alle
#                                             Teile gleichzeitig auf eigenen Rechnern (#307)
#   ./pruefen.sh teile                        die Namen der Teile, je Zeile einer
#   ./pruefen.sh gesamt <ordner>              fasst die Ergebnisse aller Teile zusammen (GitHub)
# Gleiches Skript lokal und auf GitHub; den vollen Lauf macht dort die Prüfung, aufgeteilt in
# die Teile. Zusammen starten die Teile jede Prüfung des vollen Laufs genau einmal. Jede Prüfung
# läuft, auch wenn eine frühere rot war, damit man alle Befunde auf einmal sieht. Am Ende
# steht, ob alles grün ist, wie viele Tests übersprungen wurden und, im schnellen Lauf, was
# nicht ausgewählt war.

set -u
cd "$(dirname "$0")"

# Die Teile für GitHub (#307): Grundprüfungen mit Container-Prüfung und pip-audit, die Tests aus
# tests/ in zwei Hälften und der Rauchtest je Browser. ci.yml nennt dieselben Teile;
# tests/test_pruefung_auf_github.py vergleicht beide.
PARTS="grund tests-1 tests-2 rauchtest-chromium rauchtest-firefox rauchtest-webkit"

usage_error() {
    echo "pruefen.sh: $1" >&2
    echo "Aufruf: ./pruefen.sh   oder   ./pruefen.sh schnell [Testdatei aus tests/ oder rauchtests/ ...]" >&2
    exit 2
}

is_part() {
    for known in $PARTS; do
        [ "$1" = "$known" ] && return 0
    done
    return 1
}

# Liest einen Wert „name=wert“ aus der Ergebnisdatei eines Teils.
part_value() {
    sed -n "s/^$1=//p" "$2" | head -n 1
}

is_count() {
    case "$1" in
        unbekannt) return 0 ;;
        "" | *[!0-9]*) return 1 ;;
    esac
    return 0
}

# Gesamtprüfung auf GitHub: grün nur, wenn jeder Teil ein lesbares, grünes Ergebnis hat. Fehlt
# eins, ist der Teil abgebrochen oder gar nicht gelaufen; das ist rot.
summarize_parts() {
    dir="$1"
    failed=""
    ran_sum=0
    skipped_sum=0
    unknown=0
    table=""
    echo "=== Ergebnisse der Teile"
    for part in $PARTS; do
        file="$dir/$part"
        if [ ! -f "$file" ]; then
            line="kein Ergebnis (abgebrochen oder nicht gelaufen)"
            failed="$failed
  - $part: abgebrochen oder nicht gelaufen"
        else
            name="$(part_value teil "$file")"
            result="$(part_value ergebnis "$file")"
            ran="$(part_value gelaufen "$file")"
            skipped="$(part_value uebersprungen "$file")"
            if [ "$name" != "$part" ] || ! is_count "$ran" || ! is_count "$skipped" ||
                { [ "$result" != "gruen" ] && [ "$result" != "rot" ]; }; then
                line="Ergebnis unlesbar"
                failed="$failed
  - $part: Ergebnis unlesbar"
            else
                if [ "$ran" = "unbekannt" ] || [ "$skipped" = "unbekannt" ]; then
                    unknown=1
                else
                    ran_sum=$((ran_sum + ran))
                    skipped_sum=$((skipped_sum + skipped))
                fi
                if [ "$result" = "gruen" ]; then
                    line="grün, $ran Tests gelaufen, $skipped übersprungen"
                else
                    line="ROT, $ran Tests gelaufen, $skipped übersprungen"
                    failed="$failed
  - $part: rot (die roten Tests stehen im Teil $part)"
                fi
            fi
        fi
        echo "  $part: $line"
        table="$table
| $part | $line |"
    done
    if [ "$unknown" = "1" ]; then
        ran_text="Zahl unbekannt (in einem Teil fehlt die Zusammenfassung von pytest)"
        skipped_text="Zahl unbekannt (in einem Teil fehlt die Zusammenfassung von pytest)"
    else
        ran_text="$ran_sum"
        skipped_text="$skipped_sum"
    fi
    echo ""
    echo "Gelaufene Tests: $ran_text"
    echo "Übersprungene Tests: $skipped_text"
    if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
        {
            echo "### Alle Prüfungen"
            echo ""
            echo "| Teil | Ergebnis |"
            echo "|---|---|$table"
            echo ""
            echo "Gelaufene Tests: $ran_text"
            echo ""
            echo "Übersprungene Tests: $skipped_text"
        } >> "$GITHUB_STEP_SUMMARY"
    fi
    if [ -n "$failed" ]; then
        [ -z "${GITHUB_ACTIONS:-}" ] || echo "::error title=ROT::Nicht alle Teile sind grün.$(echo "$failed" | tr '\n' ' ')"
        echo "ROT. Nicht bestanden:$failed"
        return 1
    fi
    if [ "$unknown" = "0" ] && [ "$skipped_sum" -gt 0 ]; then
        echo "Alle Teile grün, $skipped_sum Tests übersprungen (Gründe in den Teilen unter SKIPPED)."
    else
        echo "Alle Teile grün."
    fi
    return 0
}

# Die Testdateien eines der beiden Teile mit Tests aus tests/: alle Dateien nach den Regeln von
# pytest (test_*.py, *_test.py), sortiert und abwechselnd verteilt. So landet jede Datei in genau
# einem Teil, auch eine neue, ohne dass sie jemand einträgt.
part_test_files() {
    find tests \( -name __pycache__ -o -name ".?*" \) -prune -o -type f \( -name "test_*.py" -o -name "*_test.py" \) -print |
        LC_ALL=C sort | awk -v number="$1" '(NR - 1) % 2 == number - 1'
}

mode="voll"
part=""
tests_files=""
rauch_files=""
if [ "${1:-}" = "teile" ]; then
    [ "$#" -eq 1 ] || usage_error "Hinter „teile“ steht nichts mehr."
    for known in $PARTS; do
        echo "$known"
    done
    exit 0
elif [ "${1:-}" = "gesamt" ]; then
    [ "$#" -eq 2 ] || usage_error "Hinter „gesamt“ steht genau ein Ordner mit den Ergebnissen der Teile."
    summarize_parts "$2"
    exit $?
elif [ "${1:-}" = "teil" ]; then
    [ "$#" -eq 2 ] || usage_error "Hinter „teil“ steht genau ein Name: $PARTS"
    is_part "$2" || usage_error "Unbekannter Teil: $2 (bekannt: $PARTS)"
    mode="teil"
    part="$2"
elif [ "${1:-}" = "schnell" ]; then
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
ran_total=0

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
    # Gelaufen: bestanden, rot und als bekannter Fehler markiert, nicht übersprungen oder abgewählt.
    for outcome in passed failed xfailed xpassed; do
        number="$(echo " $summary" | sed -n -E "s/.*[^0-9]([0-9]+) $outcome.*/\1/p")"
        ran_total=$((ran_total + ${number:-0}))
    done
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

if [ "$mode" != "teil" ] || [ "$part" = "grund" ]; then
    check "Liste mit festen Fassungen passt zur Paketliste (uv lock --check)" uv lock --check
    check "Code-Regeln (ruff)" $run ruff check .
    check "Django-Systemprüfung" $run python manage.py check
    check "Fehlen Migrationen?" $run python manage.py makemigrations --check --dry-run
fi
if [ "$mode" = "voll" ]; then
    check_tests "Tests (pytest)" $run pytest -rsfE
elif [ "$mode" = "teil" ]; then
    case "$part" in
        tests-*)
            part_files="$(part_test_files "${part#tests-}" | tr '\n' ' ')"
            case "$part_files" in
                *[!\ ]*)
                    # shellcheck disable=SC2086  # Die Dateinamen sind absichtlich eine Liste.
                    check_tests "Tests (pytest), Teil $part" $run pytest -rsfE $part_files
                    ;;
                *)
                    # Ohne Dateien würde pytest alle Tests sammeln; die liefen dann doppelt.
                    echo ""
                    echo "=== Tests (pytest), Teil $part: keine Testdateien in diesem Teil"
                    ;;
            esac
            ;;
    esac
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
elif [ "$mode" = "teil" ]; then
    # Je Teil ein Browser (rauchtests/conftest.py, RAUCHTEST_BROWSER).
    case "$part" in
        rauchtest-*)
            check_tests "Rauchtest im Browser mit Prüfung auf Barrierefreiheit (Playwright, axe), ${part#rauchtest-}" \
                env DJANGO_ALLOW_ASYNC_UNSAFE=true RAUCHTEST_BROWSER="${part#rauchtest-}" $run pytest rauchtests -rsfE
            ;;
    esac
else
    [ -z "$rauch_files" ] || check_tests "Rauchtest im Browser (Playwright, axe):$rauch_files" \
        env DJANGO_ALLOW_ASYNC_UNSAFE=true $run pytest -rsfE $rauch_files
fi
# Eigener Lauf: baut das Container-Abbild und startet die Testumgebung so, wie sie nach dem
# README startet (#58). Braucht Docker und eigene Ports (tests/check_ports.py); das eigene Tool
# und die eigene Testumgebung auf 8000 und 8081 dürfen weiterlaufen (#167). Nur im vollen Lauf
# und im Teil „grund“.
if [ "$mode" = "voll" ] || [ "$part" = "grund" ]; then
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
elif [ "$mode" = "teil" ]; then
    echo "Betriebsart: Teil $part (auf GitHub gleichzeitig mit den anderen Teilen)"
else
    echo "Betriebsart: voller Lauf"
fi
echo "Übersprungene Tests: $skipped_text"

# Ergebnis des Teils für die Gesamtprüfung auf GitHub (ci.yml, ./pruefen.sh gesamt).
if [ "$mode" = "teil" ]; then
    if [ "$skipped_unknown" = "1" ]; then
        ran_value="unbekannt"
        skipped_value="unbekannt"
    else
        ran_value="$ran_total"
        skipped_value="$skipped_total"
    fi
    echo "Gelaufene Tests: $ran_value"
    if [ -n "${PRUEFTEIL_ERGEBNIS:-}" ]; then
        if [ -n "$failed" ]; then result="rot"; else result="gruen"; fi
        printf 'teil=%s\nergebnis=%s\ngelaufen=%s\nuebersprungen=%s\n' \
            "$part" "$result" "$ran_value" "$skipped_value" > "$PRUEFTEIL_ERGEBNIS"
    fi
fi
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
elif [ "$mode" = "teil" ]; then
    if [ "$skipped_unknown" = "1" ]; then
        echo "Teil $part grün, Zahl der Tests unbekannt (die Zusammenfassung von pytest fehlt)."
    else
        echo "Teil $part grün, $ran_total Tests gelaufen, $skipped_total übersprungen."
    fi
elif [ -z "$skipped_line" ]; then
    echo "Alle Prüfungen grün."
else
    echo "Alle gelaufenen Prüfungen grün$skipped_line."
fi
exit 0
