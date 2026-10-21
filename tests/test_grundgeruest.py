"""Tests für das Grundgerüst (#4): Start, Datenbank, Fassungen und Prüfeinstellungen."""

import os
import subprocess
import sys
from pathlib import Path

import django
import pytest
from django.db import connection

BASE_DIR = Path(__file__).resolve().parent.parent

INVENTED_DATABASE = {"POSTGRES_DB": "beispiel", "POSTGRES_USER": "beispiel", "POSTGRES_PASSWORD": "beispiel"}


def _load_settings(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Lädt die Einstellungen in einem eigenen Prozess mit genau der angegebenen Umgebung."""
    command = [sys.executable, "-c", "from django.conf import settings; print(settings.DEBUG)"]
    return subprocess.run(  # noqa: S603 -- fester Befehl mit dem eigenen Python, keine Eingaben von außen
        command,
        cwd=BASE_DIR,
        env={"PATH": os.environ.get("PATH", ""), "DJANGO_SETTINGS_MODULE": "config.settings", **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_startseite_zeigt_dass_das_tool_laeuft(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Das DPV Anmeldetool läuft" in response.content.decode()


@pytest.mark.django_db
def test_tests_laufen_gegen_postgresql():
    # Läuft ein Test still gegen eine andere Datenbank, fallen Fehler erst im Betrieb auf.
    assert connection.vendor == "postgresql"


def test_es_laufen_python_313_und_django_61():
    # Auf einem Mac mit mehreren Python-Fassungen wich uv einmal still auf Django 5.2 aus.
    assert sys.version_info[:2] == (3, 13)
    assert django.VERSION[:2] == (6, 1)


def test_bekannte_fehler_die_ploetzlich_bestehen_machen_den_lauf_rot(pytester):
    # Ein eigener pytest-Lauf mit den Einstellungen dieses Projekts: Ein als bekannter
    # Fehler markierter Test, der besteht, muss den Lauf rot machen.
    test_file = pytester.makepyfile(
        """
        import pytest

        @pytest.mark.xfail(reason="bekannter Fehler, inzwischen behoben")
        def test_ploetzlich_behoben():
            assert True
        """
    )

    result = pytester.runpytest_subprocess("-c", str(BASE_DIR / "pyproject.toml"), "-p", "no:django", test_file)

    result.assert_outcomes(failed=1)


def test_jede_eigene_app_hat_einen_migrationsordner():
    # Ohne Migrationsordner übersieht die Prüfung auf fehlende Migrationen jedes neue
    # Datenmodell dieser App und bleibt grün.
    from django.apps import apps

    own_apps = [app for app in apps.get_app_configs() if Path(app.path).is_relative_to(BASE_DIR)]

    assert own_apps
    for app in own_apps:
        assert (Path(app.path) / "migrations" / "__init__.py").is_file(), app.label


def test_ohne_geheimen_schluessel_startet_das_projekt_nicht():
    result = _load_settings(INVENTED_DATABASE)

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY fehlt" in result.stderr


def test_fehleranzeige_fuer_entwickler_ist_standardmaessig_aus():
    result = _load_settings({**INVENTED_DATABASE, "DJANGO_SECRET_KEY": "nur-fuer-diesen-test"})

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_umgebungsdatei_kommt_nie_ins_repo():
    # git check-ignore antwortet mit 0, wenn .gitignore die Datei aus dem Repo heraushält.
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", ".env"],  # noqa: S607 -- git aus dem Suchpfad wie bei jedem Aufruf
        cwd=BASE_DIR,
        check=False,
    )

    assert result.returncode == 0
