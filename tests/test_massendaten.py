"""Massendaten für den Leistungstest (#104): was bei jedem Prüflauf mitläuft.

Den Leistungstest selbst mit 5.000 Personen (G1 bis G3, M1 bis M4, R1 bis R3) enthält `tests/leistungstest.py`;
er läuft nur am Ende einer Phase. Hier stehen die Szenarien U1 bis U3 und M5 aus dem Kommentar
„Szenarien (13.11.2026)“ in #104
(https://github.com/sebivtt/dpv-participant-management/issues/104#issuecomment-6862671822), mit Sebastians
Entscheidung „Alle passen so“.

Zusätzlich prüfen die Tests mit „klein“ im Namen den Generator mit wenigen Personen (2 Probestämme,
60 Personen). Grund (Risiko): Der Generator läuft sonst nur am Ende einer Phase; bricht ihn dazwischen eine
neue Tabelle oder Regel, fiele das erst dann auf, wenn #145 ihn braucht. Mit wenigen Personen kostet das
nur Sekunden (U2). Alle Namen sind erfunden.
"""

import ast
import re
from io import StringIO
from pathlib import Path

import pytest
import yaml
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from persons.models import ManagedPerson
from roles.models import Role
from tests.keycloak_fake import login
from tests.leistungstest import check_page, measure
from tests.test_testdaten import ROLES, UNITS, logged_in_before, roles_now, snapshot, units_now
from units.models import Unit

pytestmark = pytest.mark.django_db

User = get_user_model()
R = Role.Kind
U = Unit.Kind
BASE_DIR = Path(__file__).resolve().parent.parent
WORKFLOW = BASE_DIR / ".github" / "workflows" / "leistungstest.yml"


@pytest.fixture
def local(settings):
    """Die Einstellungen sagen ausdrücklich „lokal“ (eigener Rechner)."""
    settings.LOCAL_ENVIRONMENT = True
    settings.TEST_ENVIRONMENT = False
    return settings


@pytest.fixture
def small(local, monkeypatch):
    """Der Zusatz mit wenigen Personen: 2 Probestämme mit je 5 Gruppen, 60 Personen, 12 davon in einer Organisation."""
    monkeypatch.setattr("core.management.mass_data.TROOPS", 2)
    monkeypatch.setattr("core.management.mass_data.PERSONS", 60)
    monkeypatch.setattr("core.management.mass_data.OUTLIER", 12)


def run(*args: str) -> str:
    out = StringIO()
    call_command("testdata", *args, stdout=out)
    return out.getvalue()


def probe_units():
    return Unit.objects.filter(name__startswith="Probe")


def probe_accounts():
    return User.objects.filter(username__startswith="probe.")


def direct_persons(unit: Unit) -> int:
    return Role.objects.filter(kind=R.MEMBER, unit=unit).count() + ManagedPerson.objects.filter(unit=unit).count()


# ---------- Generator mit wenigen Personen ----------


def test_g1_klein_probestaemme_gruppen_und_personen_neben_der_besetzung(small):
    out = run("--mass-data")

    boreas = Unit.objects.get(name="Pfadfinderbund Boreas")
    troops = Unit.objects.filter(kind=U.TROOP, parent=boreas, name__startswith="Probestamm ")
    assert sorted(troops.values_list("name", flat=True)) == ["Probestamm 01", "Probestamm 02"]
    assert all(Unit.objects.filter(kind=U.GROUP, parent=troop).count() == 5 for troop in troops)
    accounts = Role.objects.filter(kind=R.MEMBER, unit__in=probe_units()).count()
    managed = ManagedPerson.objects.filter(unit__in=probe_units()).count()
    assert accounts + managed == 60
    assert accounts and managed
    assert max(direct_persons(unit) for unit in probe_units()) == 12
    assert direct_persons(Unit.objects.get(name="Probestamm 01")) == 12
    assert set(probe_accounts().values_list("last_name", flat=True)) <= {"Probe", "Muster"}
    assert all(mail.endswith("@example.org") for mail in probe_accounts().values_list("email", flat=True))
    # Die Konten sind über die genaue Mail auffindbar wie nach einem Login (für die Suche bei „Person aufnehmen“).
    for account in probe_accounts():
        assert EmailAddress.objects.filter(user=account, email=account.email, verified=True).exists()
        assert account.last_login is not None and account.is_active
    # Je Probestamm und Gruppe eine Leitung aus den eigenen Mitgliedern.
    for unit in probe_units():
        kind = R.TROOP_LEAD if unit.kind == U.TROOP else R.GROUP_LEAD
        assert Role.objects.filter(kind=kind, unit=unit).count() == 1, unit.name
    # Die Besetzung aus #103 ist unverändert da.
    assert UNITS <= units_now()
    assert ROLES <= roles_now()
    assert "Massendaten" in out


def test_g2_klein_ein_zweiter_lauf_ergibt_genau_dieselben_daten(small):
    run("--mass-data")
    assert probe_units().count() == 2 * 6
    before = snapshot()
    accounts = list(probe_accounts().order_by("pk").values_list("pk", "username", "first_name", "last_name", "email",
                                                                 "last_login"))
    mails = list(EmailAddress.objects.filter(user__in=probe_accounts()).order_by("pk").values_list(
        "user_id", "email", "verified", "primary"))

    run("--mass-data")

    assert snapshot() == before
    assert list(probe_accounts().order_by("pk").values_list("pk", "username", "first_name", "last_name", "email",
                                                             "last_login")) == accounts
    assert list(EmailAddress.objects.filter(user__in=probe_accounts()).order_by("pk").values_list(
        "user_id", "email", "verified", "primary")) == mails


def test_g3_klein_ohne_keycloak_konto_und_ohne_passwort(small):
    run("--mass-data")

    assert probe_accounts().count() > 10
    assert not SocialAccount.objects.filter(user__in=probe_accounts()).exists()
    assert not any(account.has_usable_password() for account in probe_accounts())


def test_g3_ein_login_mit_gleichem_benutzernamen_und_gleicher_mail_landet_nicht_im_erfundenen_konto(
        small, client, keycloak):
    run("--mass-data")
    account = probe_accounts().order_by("username").first()
    keycloak.person = {
        "sub": "99999999-aaaa-4bbb-8ccc-000000000104",
        "preferred_username": account.username,
        "email": account.email,
        "email_verified": True,
        "given_name": account.first_name,
        "family_name": account.last_name,
    }

    login(client)

    assert int(client.session["_auth_user_id"]) != account.pk
    assert not SocialAccount.objects.filter(user=account).exists()


def test_g3_gehoert_ein_benutzername_einem_verknuepften_konto_bricht_der_zusatz_ab_und_aendert_nichts(small):
    """Risiko: Ein echtes Konto mit dem Benutzernamen eines erfundenen bekäme sonst Rollen in den Probestämmen."""
    run()
    before = snapshot()
    stranger = logged_in_before("probe.0001", "Fremd", "Konto")

    with pytest.raises(CommandError) as refused:
        run("--mass-data")

    assert "probe.0001" in str(refused.value)
    assert snapshot() == before
    assert not Role.objects.filter(user=stranger).exists()


# ---------- Was bleibt unverändert? ----------


def test_u1_ohne_zusatz_genau_die_daten_aus_103_auch_nach_einem_lauf_mit_zusatz(small):
    run()
    plain = snapshot()

    run("--mass-data")
    assert snapshot() != plain
    run()

    assert snapshot() == plain
    assert not probe_units().exists()
    assert units_now() == UNITS
    assert roles_now() == ROLES


def test_u2_normale_prueflaeufe_legen_keine_massendaten_an_und_messen_nicht():
    """Der Leistungstest heißt nicht test_*.py; pytest sammelt ihn nur, wenn er ausdrücklich genannt ist."""
    assert (BASE_DIR / "tests" / "leistungstest.py").is_file()
    assert not re.fullmatch(r"test_.*\.py|.*_test\.py", "leistungstest.py")
    pyproject = (BASE_DIR / "pyproject.toml").read_text(encoding="utf-8")
    assert "python_files" not in pyproject
    for path in (BASE_DIR / "pruefen.sh", BASE_DIR / ".github" / "workflows" / "ci.yml"):
        text = path.read_text(encoding="utf-8")
        assert "leistungstest" not in text.lower(), path.name
        assert "--mass-data" not in text, path.name
    for path in (BASE_DIR / "tests").rglob("test_*.py"):
        source = path.read_text(encoding="utf-8")
        if path.name != "test_massendaten.py":
            assert "--mass-data" not in source, path.name


def test_u2_der_leistungstest_laeuft_auf_github_nur_von_hand():
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # YAML liest den Schlüssel „on“ als Wahrheitswert.
    triggers = workflow.get("on", workflow.get(True))

    assert set(triggers) == {"workflow_dispatch"}
    runs = [step["run"] for job in workflow["jobs"].values() for step in job["steps"] if "run" in step]
    assert any("pytest tests/leistungstest.py" in command for command in runs), runs


QUERY_LIMIT_TESTS = {
    "tests/test_organisation.py": "test_abfragen_wachsen_nicht_mit_der_zahl_der_organisationen",
    "tests/test_personen.py": "test_pg8_die_liste_personen_waechst_nicht_mit_den_abfragen",
    "tests/test_verwaltete_personen.py": "test_mg9_der_abschnitt_waechst_nicht_mit_den_abfragen",
}


def test_u3_die_abfragegrenzen_tests_laufen_weiter_bei_jedem_lauf():
    for name, function in QUERY_LIMIT_TESTS.items():
        tree = ast.parse((BASE_DIR / name).read_text(encoding="utf-8"))
        found = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function]
        assert len(found) == 1, (name, function)
        assert "assert_queries_do_not_grow" in ast.unparse(found[0]), (name, function)
        assert not [mark for mark in found[0].decorator_list if re.search(r"skip|xfail", ast.unparse(mark))]


# ---------- Messung ----------


def test_m5_eine_seite_mit_2_sekunden_oder_mehr_macht_den_lauf_rot_und_nennt_seite_und_zeit():
    ticks = iter(range(100))

    def clock() -> float:
        # Jeder gemessene Aufruf dauert genau 2 Sekunden.
        return 2.0 * next(ticks)

    times = measure(lambda: None, clock=clock)

    assert times == [2.0] * len(times)
    with pytest.raises(AssertionError) as slow:
        check_page("Seite mit 500 Personen", times)
    assert "„Seite mit 500 Personen“" in str(slow.value)
    assert "2,00 s" in str(slow.value)


def test_m5_unter_2_sekunden_ist_gruen():
    assert check_page("Gliederung „Organisation“", [0.5, 1.99, 0.7]) == 0.7
