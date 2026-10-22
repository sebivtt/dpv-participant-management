#!/bin/sh
# Alle automatischen Prüfungen aus CONTRIBUTING.md mit einem Befehl: ./pruefen.sh
# GitHub ruft dasselbe Skript auf (.github/workflows/ci.yml); lokal und auf GitHub wird
# also gleich geprüft. Jede Prüfung läuft, auch wenn eine frühere rot war, damit man
# alle Befunde auf einmal sieht. Am Ende steht, ob alles grün ist.

set -u
cd "$(dirname "$0")"

# Lokal kommen die Zugangsdaten aus .env, auf GitHub aus dem Prüfablauf selbst.
# --locked: uv run würde uv.lock sonst still an pyproject.toml angleichen, und ein
# rotes „uv lock --check“ wäre beim nächsten Lauf unbemerkt grün.
if [ -f .env ]; then
    run="uv run --locked --env-file .env"
else
    run="uv run --locked"
fi

failed=""

check() {
    name="$1"
    shift
    echo ""
    echo "=== $name"
    output="$(mktemp)"
    status="$(mktemp)"
    # Ausgabe mitschreiben, damit auf GitHub die roten Tests als Hinweise erscheinen können.
    { "$@"; echo $? > "$status"; } 2>&1 | tee "$output"
    if [ "$(cat "$status")" = "0" ]; then
        echo "--> grün: $name"
    else
        echo "--> ROT: $name"
        failed="$failed
  - $name"
        report_on_github "$name" "$output"
    fi
    rm -f "$output" "$status"
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
check "Tests (pytest)" $run pytest -rfE
# Eigener Lauf: Playwright betreibt eine Ereignisschleife, neben der Django Datenbankzugriffe
# sonst abbricht (rauchtests/conftest.py). Braucht die Browser (README.md, Schritt 10).
check "Rauchtest im Browser mit Prüfung auf Barrierefreiheit (Playwright, axe)" \
    env DJANGO_ALLOW_ASYNC_UNSAFE=true $run pytest rauchtests -rsfE
# Eigener Lauf: baut das Container-Abbild und startet die Testumgebung so, wie sie nach dem
# README startet (#58). Braucht Docker und die Ports 8000 und 8081; eine laufende Testumgebung
# vorher anhalten (README.md).
check "Testumgebung im Container (Docker)" $run pytest containertests -rfE
check "Bekannte Sicherheitslücken in Paketen (pip-audit)" audit_packages

echo ""
if [ -z "$failed" ]; then
    echo "Alle Prüfungen grün."
    exit 0
fi
echo "Nicht bestanden:$failed"
exit 1
