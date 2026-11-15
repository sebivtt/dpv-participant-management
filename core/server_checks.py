"""Startprüfung: Auf einem Server startet das Tool nicht mit unsicheren Einstellungen (#325).

Eine Systemprüfung von Django. Sie läuft bei jedem Befehl von manage.py, also auch bei
`migrate` in docker/start.sh, bevor der Webserver startet; findet sie etwas, bricht der Start ab,
und das Log nennt jedes Problem in einer eigenen Zeile, nie den Wert. Was als Server gilt und
was dort verboten ist, steht im Text von #325; die Bedeutung jeder Einstellung beschreibt
testumgebung/.env.example.

Gelesen wird die Umgebung selbst, nicht config/settings.py: Dort sind manche Schalter in der
Testumgebung schon still abgeschaltet (DJANGO_DEBUG, LOCAL_ENVIRONMENT), die Startprüfung soll
sie aber gerade dann melden.
"""

import os
from collections.abc import Mapping
from urllib.parse import urlparse

from django.core.checks import WARNING, Error, register
from django.core.checks.registry import registry
from django.core.checks.security.base import _check_secret_key

PREFIX = "Unsichere Einstellung für den Server: "
SUFFIX = " (docs/betrieb.md)."

# Namen, die nur den eigenen Rechner meinen. Jeder andere Name in DJANGO_ALLOWED_HOSTS heißt Server.
OWN_MACHINE = {"localhost", "127.0.0.1"}
# Wohin KEYCLOAK_REALM_URL auf dem Server nie zeigen darf: eigener Rechner und Container der Testumgebung.
LOCAL_KEYCLOAK = {"localhost", "127.0.0.1", "::1", "keycloak"}
TEST_REALM = "dpv-test"

# Einstellungen mit geheimem Wert.
SECRET_SETTINGS = ("DJANGO_SECRET_KEY", "POSTGRES_PASSWORD", "KEYCLOAK_CLIENT_SECRET")

# Öffentlich bekannte Beispielwerte aus .env.example und testumgebung/.env.example. Die Vorlagen
# kommen nicht ins Abbild (.dockerignore), deshalb stehen sie hier; tests/test_startpruefung.py
# meldet jeden Beispielwert in den Vorlagen, der hier fehlt (G6).
EXAMPLE_VALUES = frozenset(
    {
        "nur-lokal-nicht-geheim-bitte-auf-servern-ersetzen",
        "testumgebung-lokal-nicht-geheim-auf-dem-server-ersetzen",
        "nur-lokal-nicht-geheim",
        "testumgebung-lokal-nicht-geheim",
    }
)

# Funde aus Djangos Prüfung für den Betrieb (check --deploy), die nicht gemeldet werden:
# HSTS gilt absichtlich nur für genau diese Adresse und ohne Vorab-Liste der Browser (Klärung von #324).
DEPLOY_DECIDED = {"security.W005", "security.W021"}
# Djangos Funde, die schon eine eigene Zeile meldet, mit derselben Ursache. Sie entfallen nur, wenn
# diese Zeile kommt; so steht jedes Problem genau einmal im Log.
DEPLOY_COVERED = {
    "core.E102": {"security.W009"},
    "core.E101": {"security.W009"},
    "core.E103": {"security.W004", "security.W008", "security.W012", "security.W016"},
    "core.E109": {"security.W018"},
}


def _hosts(env: Mapping[str, str]) -> list[str]:
    # Wie ALLOWED_HOSTS in config/settings.py, mit derselben Angabe ohne Wert.
    return [h.strip().lower() for h in env.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]


def is_server(env: Mapping[str, str]) -> bool:
    """Läuft das Tool auf einem Server? Ja, sobald ein Name außer localhost und 127.0.0.1 erlaubt ist."""
    return any(host not in OWN_MACHINE for host in _hosts(env))


def _realm(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/realms/", 1)[1] if "/realms/" in path else ""


def _secrets(env: Mapping[str, str]) -> list[tuple[str, str]]:
    found = [
        ("core.E101", f"{name} ist ein öffentlich bekannter Beispielwert. Bitte einen eigenen geheimen Wert eintragen")
        for name in SECRET_SETTINGS
        if env.get(name, "") in EXAMPLE_VALUES
    ]
    secret_key = env.get("DJANGO_SECRET_KEY", "")
    if secret_key and secret_key not in EXAMPLE_VALUES and not _check_secret_key(secret_key):
        found.append(
            (
                "core.E102",
                "DJANGO_SECRET_KEY ist zu schwach: Django verlangt mindestens 50 Zeichen, davon 5 verschiedene, "
                "ohne Kennzeichen als unsicherer Schlüssel. Bitte einen langen Zufallswert eintragen",
            )
        )
    return found


def _keycloak(env: Mapping[str, str]) -> list[tuple[str, str]]:
    found = []
    realm_url = env.get("KEYCLOAK_REALM_URL", "").strip()
    # Fehlt die Adresse ganz, meldet das schon die Prüfung der Keycloak-Angaben (accounts/checks.py).
    if realm_url and (not realm_url.startswith("https://") or (urlparse(realm_url).hostname or "") in LOCAL_KEYCLOAK):
        found.append(
            (
                "core.E104",
                "KEYCLOAK_REALM_URL beginnt nicht mit https:// oder zeigt auf localhost, 127.0.0.1, [::1] oder keycloak. "
                "Bitte die Adresse des Realms im Keycloak des DPV eintragen",
            )
        )
    test_environment = env.get("TEST_ENVIRONMENT") == "1"
    if realm_url and test_environment and _realm(realm_url) != TEST_REALM:
        found.append(
            (
                "core.E107",
                f"KEYCLOAK_REALM_URL zeigt in der Testumgebung (TEST_ENVIRONMENT=1) nicht auf den Realm {TEST_REALM}; "
                "so kämen echte Mitglieder in die Testumgebung. Bitte den Test-Realm eintragen",
            )
        )
    if realm_url and not test_environment and _realm(realm_url) == TEST_REALM:
        found.append(
            (
                "core.E108",
                f"KEYCLOAK_REALM_URL zeigt auf den Realm {TEST_REALM}, aber TEST_ENVIRONMENT=1 fehlt. Bitte im Betrieb "
                "den Realm des DPV eintragen; in der Testumgebung setzt die Compose-Datei den Schalter",
            )
        )
    if env.get("KEYCLOAK_REALM_URL_INTERN", "").strip():
        found.append(
            (
                "core.E105",
                "KEYCLOAK_REALM_URL_INTERN ist gesetzt; diese Adresse gilt nur für den eigenen Rechner. "
                "Bitte die Zeile löschen",
            )
        )
    return found


def _switches(env: Mapping[str, str]) -> list[tuple[str, str]]:
    found = []
    if env.get("DJANGO_BEHIND_HTTPS_PROXY") != "1":
        found.append(
            (
                "core.E103",
                "DJANGO_BEHIND_HTTPS_PROXY=1 fehlt; ohne den Schalter gehen Cookies auch unverschlüsselt. "
                "Bitte den Schalter setzen, wenn das Programm davor HTTPS annimmt",
            )
        )
    if env.get("LOCAL_ENVIRONMENT") == "1":
        found.append(
            (
                "core.E106",
                "LOCAL_ENVIRONMENT=1 ist gesetzt; der Schalter gilt nur für den eigenen Rechner. Bitte die Zeile löschen",
            )
        )
    if env.get("DJANGO_DEBUG") == "1":
        found.append(
            (
                "core.E109",
                "DJANGO_DEBUG=1 ist gesetzt; die Fehleranzeige für Entwickler zeigt Einstellungen und "
                "Formularinhalte. Bitte die Zeile löschen",
            )
        )
    if "*" in _hosts(env):
        found.append(
            (
                "core.E110",
                "DJANGO_ALLOWED_HOSTS enthält *; dann antwortet das Tool unter jedem Namen. "
                "Bitte nur die Namen des Servers eintragen",
            )
        )
    return found


def problems(env: Mapping[str, str]) -> list[tuple[str, str]]:
    """Unsichere Einstellungen als Paare aus Kennung und Zeile fürs Log; auf dem eigenen Rechner keine.

    Keine Zeile enthält einen Wert oder einen Teil davon (#325, G2).
    """
    if not is_server(env):
        return []
    return [(key, f"{PREFIX}{text}{SUFFIX}") for key, text in _secrets(env) + _switches(env) + _keycloak(env)]


def _deploy_findings(app_configs, skip: set[str], **kwargs) -> list[str]:
    """Djangos Prüfung für den Betrieb (check --deploy) als Zeilen fürs Log, ohne die übersprungenen Funde."""
    lines = []
    for check in registry.deployment_checks:
        for message in check(app_configs=app_configs, **kwargs):
            if message.level >= WARNING and message.id not in skip:
                lines.append(
                    f"{PREFIX}Djangos Prüfung für den Betrieb meldet {message.id}: {message.msg} "
                    f"Bitte die genannte Einstellung beheben{SUFFIX}"
                )
    return lines


@register()
def server_settings_safe(app_configs, **kwargs) -> list[Error]:
    """Meldet auf einem Server jede unsichere Einstellung als Fehler, der den Start verhindert.

    Dazu gehören Djangos eigene Funde für den Betrieb; sie brechen den Start ebenso ab.
    """
    env = os.environ
    if not is_server(env):
        return []
    own = problems(env)
    skip = set(DEPLOY_DECIDED)
    for key, _ in own:
        skip |= DEPLOY_COVERED.get(key, set())
    errors = [Error(line, id=key) for key, line in own]
    errors += [Error(line, id="core.E120") for line in _deploy_findings(app_configs, skip, **kwargs)]
    return errors
