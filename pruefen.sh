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
    if "$@"; then
        echo "--> grün: $name"
    else
        echo "--> ROT: $name"
        failed="$failed
  - $name"
    fi
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
check "Tests (pytest)" $run pytest
check "Bekannte Sicherheitslücken in Paketen (pip-audit)" audit_packages

echo ""
if [ -z "$failed" ]; then
    echo "Alle Prüfungen grün."
    exit 0
fi
echo "Nicht bestanden:$failed"
exit 1
