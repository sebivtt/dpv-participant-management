"""Leistungstest am Ende einer Phase: 5.000 erfundene Personen, jede Seite mit Personen unter 2 Sekunden (#104, NFA-05).

Läuft nur von Hand, nie in `./pruefen.sh` oder im normalen Prüflauf auf GitHub (Szenario U2): Der Name
der Datei beginnt nicht mit `test_`, deshalb sammelt pytest sie nur, wenn sie ausdrücklich genannt ist.
Gestartet wird sie über den Ablauf „Leistungstest“ auf GitHub (`.github/workflows/leistungstest.yml`)
oder lokal mit `pytest tests/leistungstest.py` (README.md, „Leistungstest“).

Die Kennungen G1 bis G3, M1 bis M5 und R1 bis R3 verweisen auf den Kommentar „Szenarien (13.11.2026)“ in
#104 (https://github.com/sebivtt/dpv-participant-management/issues/104#issuecomment-6862671822), mit
Sebastians Entscheidung „Alle passen so“. Die Besetzung ist die aus #103: Bundesleitung Boreas ist
`ohne.nachname`, Max (`max.testmann`) die Stammesleitung der Zugvögel, Nils (`bundesleitung.nordstern`)
die Bundesleitung Nordstern. Alle Namen sind erfunden.

Erweitern am Ende einer Phase (#145): neue Seiten mit Personen oder Anmeldungen als weiteren Eintrag in
`PAGES`; was sie brauchen, kommt in den Zusatz `--mass-data` (`core/management/mass_data.py`).

„Unter 2 Sekunden“ heißt: bis der Server die fertige Seite ausgeliefert hat (Klärung vom 22.10.2026,
Frage 3). Gemessen wird mit dem Test-Client von Django, also durch alle Bausteine einer Anfrage bis zur
fertigen Antwort, ohne Netz und Browser. Je Seite gibt es einen Aufruf vorab, der nicht zählt (Vorlagen
werden beim ersten Aufruf übersetzt), dann `RUNS` gemessene; zählt der mittlere Wert (Median), damit ein
einzelner Ausreißer des Rechners den Lauf nicht rot macht.
"""

import os
import statistics
import time
from collections.abc import Callable
from io import StringIO

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test.utils import override_settings

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import Role
from tests.test_gestaltung import _all, _classes, _tree
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import ADDRESS, client_for, unit_address
from tests.test_personen import persons_section
from units.models import Unit

User = get_user_model()
R = Role.Kind
U = Unit.Kind

LIMIT = 2.0
RUNS = 5
BOREAS = "Pfadfinderbund Boreas"
OUTLIER = "Probestamm 01"
# Die Organisationen aus #103 in Boreas: der Bund, Walhall mit zwei Gruppen, Zugvögel mit einer.
BOREAS_FROM_103 = 6

# Die gemessenen Zeiten je Seite, für die Übersicht am Ende des Laufs.
RESULTS: dict[str, list[float]] = {}


# ---------- Messen ----------


def measure(call: Callable[[], object], clock: Callable[[], float] = time.perf_counter) -> list[float]:
    """Ruft `call` einmal vorab und dann `RUNS`-mal auf und gibt die gemessenen Sekunden zurück."""
    call()
    times = []
    for _ in range(RUNS):
        started = clock()
        call()
        times.append(clock() - started)
    return times


def seconds(value: float) -> str:
    """Sekunden mit Komma und zwei Stellen, z. B. „0,61 s“."""
    return f"{value:.2f} s".replace(".", ",")


def check_page(name: str, times: list[float]) -> float:
    """Der mittlere Wert einer Seite; 2 Sekunden oder mehr macht den Lauf rot und nennt Seite und Zeit (M5)."""
    RESULTS[name] = times
    middle = statistics.median(times)
    if middle >= LIMIT:
        raise AssertionError(f"Zu langsam: „{name}“ braucht {seconds(middle)} (Grenze {seconds(LIMIT)}).")
    return middle


def summary() -> list[str]:
    """Die Übersicht je Seite: mittlerer und langsamster Wert."""
    lines = ["| Seite | Mittel | Langsamste | Ergebnis |", "|---|---|---|---|"]
    for name, times in RESULTS.items():
        middle = statistics.median(times)
        result = "grün" if middle < LIMIT else "ROT"
        lines.append(f"| {name} | {seconds(middle)} | {seconds(max(times))} | {result} |")
    return lines


@pytest.fixture(scope="module", autouse=True)
def _report(request):
    """Schreibt nach dem Lauf die Zeiten je Seite in die Ausgabe und auf GitHub in die Zusammenfassung des Laufs."""
    yield
    if not RESULTS:
        return
    lines = summary()
    reporter = request.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        reporter.write_line("")
        for line in ["Leistungstest (#104), Grenze 2 s je Seite:", *lines]:
            reporter.write_line(line)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write("### Leistungstest (#104)\n\n" + "\n".join(lines) + "\n")


# ---------- Daten ----------


@pytest.fixture(scope="module")
def mass(django_db_setup, django_db_blocker):
    """Einmal je Lauf: die Testdaten aus #103 mit dem Zusatz für die Massendaten, wie lokal."""
    with django_db_blocker.unblock(), override_settings(LOCAL_ENVIRONMENT=True, TEST_ENVIRONMENT=False):
        call_command("testdata", "--mass-data", stdout=StringIO())
    yield
    # Die Daten stehen außerhalb der Transaktion eines Tests; ohne Aufräumen fänden Tests danach sie vor.
    with django_db_blocker.unblock():
        call_command("flush", interactive=False, verbosity=0)


@pytest.fixture
def data(mass, db):
    """Die Konten der Besetzung, Boreas und der Probestamm mit 500 direkten Personen."""

    class Data:
        bund = User.objects.get(username="ohne.nachname")
        max_ = User.objects.get(username="max.testmann")
        nils = User.objects.get(username="bundesleitung.nordstern")
        boreas = Unit.objects.get(name=BOREAS)
        outlier = Unit.objects.get(name=OUTLIER)
        zugvoegel = Unit.objects.get(name="Zugvögel")

    return Data


def probe_units() -> list[Unit]:
    return list(Unit.objects.filter(name__startswith="Probe"))


def mass_accounts():
    return User.objects.filter(roles__unit__name__startswith="Probe").distinct()


def snapshot_accounts() -> list[tuple]:
    """Die Konten der Massendaten mit allem, was ein Lauf an ihnen schreibt."""
    accounts = mass_accounts().order_by("username")
    return list(accounts.values_list("pk", "username", "first_name", "last_name", "email", "last_login", "is_active"))


def entries_on_page(response) -> int:
    """Wie viele Personen der Abschnitt „Personen“ zeigt, mit und ohne Konto."""
    section = persons_section(_tree(response))
    return len(_all(section, lambda element: "a-leitung" in _classes(element) and element.name == "li"))


# ---------- Generator ----------


def test_g1_boreas_hat_40_probestaemme_mit_je_5_gruppen_und_5000_personen(data):
    troops = Unit.objects.filter(kind=U.TROOP, name__startswith="Probestamm ", parent=data.boreas)
    assert troops.count() == 40
    for troop in troops:
        assert Unit.objects.filter(kind=U.GROUP, parent=troop).count() == 5, troop.name
    units = probe_units()
    accounts = Role.objects.filter(kind=R.MEMBER, unit__in=units).count()
    managed = ManagedPerson.objects.filter(unit__in=units).count()
    assert accounts + managed == 5000
    assert 0.2 < accounts / 5000 < 0.8, "gemischt mit und ohne Konto"
    direct = (Role.objects.filter(kind=R.MEMBER, unit=data.outlier).count()
              + ManagedPerson.objects.filter(unit=data.outlier).count())
    assert direct == 500
    # Erkennbar erfunden.
    assert set(mass_accounts().values_list("last_name", flat=True)) <= {"Probe", "Muster"}
    assert set(ManagedPerson.objects.filter(unit__in=units).values_list("last_name", flat=True)) <= {"Probe", "Muster"}
    assert all(mail.endswith("@example.org") for mail in mass_accounts().values_list("email", flat=True))
    # Die Besetzung aus #103 ist unverändert da.
    assert Role.objects.get(user=data.bund, kind=R.ASSOCIATION_LEAD).unit == data.boreas
    assert Role.objects.get(user=data.max_, kind=R.TROOP_LEAD).unit == data.zugvoegel


def test_g2_ein_zweiter_lauf_ergibt_genau_dieselben_daten(data):
    from tests.test_testdaten import snapshot

    before, accounts_before = snapshot(), snapshot_accounts()

    with override_settings(LOCAL_ENVIRONMENT=True, TEST_ENVIRONMENT=False):
        call_command("testdata", "--mass-data", stdout=StringIO())

    assert snapshot() == before
    assert snapshot_accounts() == accounts_before


def test_g3_die_erfundenen_konten_koennen_sich_nicht_anmelden(data):
    accounts = mass_accounts()
    assert accounts.count() > 1000
    assert not SocialAccount.objects.filter(user__in=accounts).exists()
    assert not any(account.has_usable_password() for account in accounts)


# ---------- Messung ----------


def call_outline(client):
    def call():
        response = client.get(ADDRESS)
        assert response.status_code == 200
        return response

    return call


def test_m1_gliederung_organisation_der_bundesleitung(data):
    client = client_for(data.bund)
    response = call_outline(client)()
    assert response.content.decode().count("Probestamm ") >= 40
    assert Unit.objects.filter(kind__in=(U.TROOP, U.GROUP, U.ASSOCIATION), pk__in=Rights(data.bund).area).count() \
        == BOREAS_FROM_103 + 40 * 6

    check_page("Gliederung „Organisation“", measure(call_outline(client)))


def test_m2_seite_der_organisation_mit_500_direkten_personen(data):
    client = client_for(data.bund)

    def call():
        response = client.get(unit_address(data.outlier))
        assert response.status_code == 200
        return response

    assert entries_on_page(call()) == 500
    check_page("Seite mit 500 Personen", measure(call))


def test_m3_namensvorschlaege_beim_benennen_einer_leitung(data):
    client = client_for(data.bund)
    address = f"{unit_address(data.outlier)}benennen/vorschlaege/"
    assert len(Rights(data.bund).persons().filter(last_name="Probe")) > 1000, "„Pro“ passt auf Tausende"

    def call():
        response = client.post(address, {"suche": "Pro"})
        assert response.status_code == 200
        return response

    assert call().content.decode().count('class="a-treffer"') == 10
    check_page("Namensvorschläge zu „Pro“", measure(call))


def test_m4_suche_bei_person_aufnehmen_ueber_die_genaue_mail(data):
    client = client_for(data.bund)
    # Aufnehmen darf die Bundesleitung nur in den eigenen Bund; die Probestämme haben eine eigene Leitung (PK-17).
    address = f"{unit_address(data.boreas)}aufnehmen/suchen/"
    account = mass_accounts().order_by("username").first()
    mail = EmailAddress.objects.get(user=account, verified=True).email

    def call():
        response = client.post(address, {"suche": mail})
        assert response.status_code == 200
        return response

    # Die Person ist schon Mitglied in einem Probestamm; der Dialog nennt sie dann mit ihrer Organisation (PG5).
    content = call().content.decode()
    assert f"{account.first_name} {account.last_name}" in content
    assert "Probestamm 01" in content
    check_page("Suche bei „Person aufnehmen“", measure(call))


# ---------- Rechte bei 5.000 Personen ----------


@pytest.mark.rechtematrix("PK-02")
@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-03")
def test_r1_max_sieht_nur_seinen_stamm_und_ein_probestamm_ist_nicht_gefunden(data):
    from tests.test_testdaten import accounts_seen, managed_names, members_in

    rights = Rights(data.max_)
    assert accounts_seen(data.max_) == members_in("Zugvögel", "Sippe Kraniche") - {"max.testmann"}
    managed = {person.display_name for unit in Unit.objects.all() for person in rights.managed_in(unit)}
    assert managed == managed_names("Zugvögel", "Sippe Kraniche")
    # Die Namen der Organisationen zeigt die Gliederung allen Leitungen im Bund; Personen daraus nicht.
    probe_keys = {*ManagedPerson.objects.filter(unit__name__startswith="Probe").values_list("key", flat=True),
                  *mass_accounts().values_list("key", flat=True)}
    for address in (ADDRESS, unit_address(data.zugvoegel)):
        content = client_for(data.max_).get(address).content.decode()
        assert "probe.0" not in content, address
        assert not [key for key in probe_keys if key in content], address
    assert_like_missing(data.max_, unit_address(data.outlier))


@pytest.mark.rechtematrix("PK-09")
@pytest.mark.rechtematrix("PK-10")
def test_r2_max_bekommt_bei_pro_nur_vorschlaege_aus_seinem_bereich(data):
    own = {*Unit.objects.filter(name__in=("Zugvögel", "Sippe Kraniche")).values_list("pk", flat=True)}
    own_keys = {*Role.objects.filter(kind=R.MEMBER, unit__in=own).values_list("user__key", flat=True),
                *ManagedPerson.objects.filter(unit__in=own).values_list("key", flat=True)}

    found = Rights(data.max_).suggestions("Pro", unit=data.zugvoegel)
    response = client_for(data.max_).post(f"{unit_address(data.zugvoegel)}benennen/vorschlaege/", {"suche": "Pro"})

    assert found, "Ole und Clara Probe aus den Kranichen"
    assert {hit["key"] for hit in found} <= own_keys
    content = response.content.decode()
    assert content.count('class="a-treffer"') == len(found)
    probe_keys = {*ManagedPerson.objects.filter(unit__name__startswith="Probe").values_list("key", flat=True),
                  *mass_accounts().values_list("key", flat=True)}
    assert not [key for key in probe_keys if key in content]


@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-03")
def test_r3_nils_sieht_keine_person_aus_boreas(data):
    from tests.test_testdaten import accounts_seen

    boreas = Unit.objects.filter(pk__in=Rights(data.bund).area)
    assert not accounts_seen(data.nils) & set(
        Role.objects.filter(kind=R.MEMBER, unit__in=boreas).values_list("user__username", flat=True))
    rights = Rights(data.nils)
    assert not [person for unit in boreas for person in rights.managed_in(unit)]
    assert_like_missing(data.nils, unit_address(data.outlier))
