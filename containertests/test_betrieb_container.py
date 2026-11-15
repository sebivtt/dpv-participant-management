"""Absicherungen für den Serverbetrieb im laufenden Container (#324).

Die Kennungen verweisen auf den Kommentar „Szenarien (14.11.2026)“ in #324. Die Aufbauten dazu
prüft tests/test_betrieb.py ohne Container. Mail und Sitzungen sind erfunden.
"""

import time

from containertests.conftest import compose

MAIL = "erika.testfrau@example.org"


def _manage_shell(env_file, code: str) -> str:
    result = compose("exec", "-T", "tool", "python", "manage.py", "shell", "-c", code, env_file=env_file)
    return result.stdout.strip().splitlines()[-1]


# E5, G1: Eine abgelaufene Sitzung räumt der Dienst „aufraeumen“ bei seinem Start weg, eine gültige bleibt.
def test_e5_g1_abgelaufene_sitzung_weg_gueltige_bleibt(testumgebung):
    keys = _manage_shell(
        testumgebung,
        "from datetime import timedelta; "
        "from django.contrib.sessions.backends.db import SessionStore; "
        "expired = SessionStore(); expired['erika'] = 'abgelaufen'; expired.set_expiry(1); expired.create(); "
        "valid = SessionStore(); valid['erika'] = 'gueltig'; valid.create(); "
        "print(expired.session_key, valid.session_key)",
    )
    expired, valid = keys.split()
    time.sleep(2)

    # So wie beim Start der Testumgebung: Der Dienst räumt sofort auf.
    compose("restart", "aufraeumen", env_file=testumgebung)
    remaining = ""
    for _ in range(30):
        remaining = _manage_shell(
            testumgebung,
            "from django.contrib.sessions.models import Session; "
            f"print(sorted(Session.objects.filter(session_key__in=['{expired}', '{valid}'])"
            ".values_list('session_key', flat=True)))",
        )
        if expired not in remaining:
            break
        time.sleep(1)

    assert expired not in remaining
    assert valid in remaining


# V1: Ein Fehler in der Datenbank mit einer erfundenen Mail landet nicht samt Mail und Befehl im Log.
def test_v1_fehler_mit_mail_hinterlaesst_im_datenbank_log_weder_mail_noch_befehl(testumgebung):
    # Ein doppelter Eintrag und ein Wert der falschen Art: Bei beiden nennt PostgreSQL sonst den Wert.
    result = compose(
        "exec",
        "-T",
        "datenbank",
        "sh",
        "-c",
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
        "-c 'CREATE TEMP TABLE probe (mail text UNIQUE)' "
        "-c \"INSERT INTO probe VALUES ('erika.testfrau@example.org')\" "
        "-c \"INSERT INTO probe VALUES ('erika.testfrau@example.org')\" "
        "-c \"SELECT 'erika.testfrau@example.org'::integer\"",
        env_file=testumgebung,
        check=False,
    )
    assert "duplicate key" in result.stderr or "doppelter Schlüsselwert" in result.stderr, result.stderr
    time.sleep(1)

    log = compose("logs", "--no-color", "datenbank", env_file=testumgebung).stdout

    assert "database system is ready to accept connections" in log
    assert MAIL not in log
    assert "INSERT INTO" not in log
    assert "probe" not in log
