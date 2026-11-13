"""Tests für den Befehl mit erfundenen Testdaten und die Szenarien Walhall, Zugvögel und Boreas (#103).

Die Kennungen B1 bis B6, W1 bis W3, Z1, Z2, O1 bis O6 und U1 bis U4 verweisen auf den Kommentar
„Szenarien (12.11.2026)“ in #103
(https://github.com/sebivtt/dpv-participant-management/issues/103#issuecomment-6826598949), mit Sebastians
Entscheidung „Alle Gruppen passen so“. Die Besetzung unten ist die aus diesem Kommentar; „sehen“ meint
Personen mit Konto und verwaltete Personen. Lokal liest der Befehl die Konten aus
`dev/keycloak/dpv-realm.json`; Keycloak selbst ist hier nachgestellt (`tests/keycloak_fake.py`). Alle
Namen sind erfunden.
"""

import json
from datetime import date
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from access.keys import new_key
from access.rights import Rights
from accounts.models import AccountSearch
from events.models import Event
from persons.models import ManagedPerson
from roles.models import AdminAccess, Role, RoleChange
from tests.keycloak_fake import login
from tests.test_dev_realm_datei import ACCOUNT_IDS
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import unit_address
from tests.test_testumgebung import _setting
from units.models import Unit, UnitChange

pytestmark = pytest.mark.django_db

User = get_user_model()
R = Role.Kind
U = Unit.Kind
BASE_DIR = Path(__file__).resolve().parent.parent
COMMAND = "testdata"

# Die Einheiten: Art, Name, Einheit darüber, „hat Ringe“.
UNITS = {
    (U.FEDERATION, "DPV", None, False),
    (U.ASSOCIATION, "Pfadfinderbund Boreas", "DPV", False),
    (U.TROOP, "Walhall", "Pfadfinderbund Boreas", False),
    (U.GROUP, "Sippe Falken", "Walhall", False),
    (U.GROUP, "Meute Wölfe", "Walhall", False),
    (U.TROOP, "Zugvögel", "Pfadfinderbund Boreas", False),
    (U.GROUP, "Sippe Kraniche", "Zugvögel", False),
    (U.ASSOCIATION, "Bund Nordstern", "DPV", True),
    (U.RING, "Küste", "Bund Nordstern", False),
    (U.TROOP, "Leuchtturm", "Küste", False),
    (U.GROUP, "Sippe Möwen", "Leuchtturm", False),
}
BOREAS = ("Pfadfinderbund Boreas", "Walhall", "Sippe Falken", "Meute Wölfe", "Zugvögel", "Sippe Kraniche")
GROUPS = ("Sippe Falken", "Meute Wölfe", "Sippe Kraniche", "Sippe Möwen")

# Die Rollen der Besetzung: Benutzername, Rolle, Einheit. Wer eine Leitung in einer Einheit bekommt, wird
# dort zugleich Mitglied (#89); auch das steht hier, weil es nach dem Lauf so in der Datenbank steht.
ROLES = {
    ("verbandsleitung", R.FEDERATION_LEAD, "DPV"),
    ("veranstaltungsteam", R.EVENT_TEAM, "DPV"),
    ("ohne.nachname", R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"),
    ("ohne.nachname", R.MEMBER, "Pfadfinderbund Boreas"),
    ("erika.testfrau", R.TROOP_LEAD, "Walhall"),
    ("erika.testfrau", R.MEMBER, "Walhall"),
    ("mitglied.walhall", R.MEMBER, "Walhall"),
    ("gruppenleitung.falken", R.GROUP_LEAD, "Sippe Falken"),
    ("gruppenleitung.falken", R.MEMBER, "Sippe Falken"),
    ("mitglied.falken", R.MEMBER, "Sippe Falken"),
    ("gruppenleitung.woelfe", R.GROUP_LEAD, "Meute Wölfe"),
    ("gruppenleitung.woelfe", R.MEMBER, "Meute Wölfe"),
    ("max.testmann", R.TROOP_LEAD, "Zugvögel"),
    ("max.testmann", R.MEMBER, "Zugvögel"),
    ("gruppenleitung.kraniche", R.GROUP_LEAD, "Sippe Kraniche"),
    ("gruppenleitung.kraniche", R.MEMBER, "Sippe Kraniche"),
    ("bundesleitung.nordstern", R.ASSOCIATION_LEAD, "Bund Nordstern"),
    ("bundesleitung.nordstern", R.MEMBER, "Bund Nordstern"),
    ("ringleitung.kueste", R.RING_LEAD, "Küste"),
    ("ringleitung.kueste", R.MEMBER, "Küste"),
    ("stammesleitung.leuchtturm", R.TROOP_LEAD, "Leuchtturm"),
    ("stammesleitung.leuchtturm", R.MEMBER, "Leuchtturm"),
    ("gruppenleitung.moewen", R.GROUP_LEAD, "Sippe Möwen"),
    ("gruppenleitung.moewen", R.MEMBER, "Sippe Möwen"),
    ("admin", R.ADMIN, None),
}
# Alle Konten der Besetzung: die mit Rollen und das Konto ohne Einheit und Rolle (#9).
ACCOUNTS = {username for username, _kind, _unit in ROLES} | {"ohne.name"}
# Die vier Konten aus #62, die es auch im Test-Realm des DPV gibt, mit ihrer Rolle auf dem Server.
SERVER_ROLES = {
    ("erika.testfrau", R.TROOP_LEAD, "Walhall"),
    ("max.testmann", R.TROOP_LEAD, "Zugvögel"),
    ("ohne.nachname", R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"),
}
# Die vier lokalen Kennungen aus #199; U4 prüft, dass sie bleiben.
IDS_FROM_199 = {
    "erika.testfrau": "00000000-0000-4000-8000-000000000001",
    "max.testmann": "00000000-0000-4000-8000-000000000002",
    "ohne.name": "00000000-0000-4000-8000-000000000003",
    "ohne.nachname": "00000000-0000-4000-8000-000000000004",
}

# Was zu den Konten gehört und deshalb bei jedem Lauf stehen bleibt (Akzeptanzkriterium „Nur die Konten bleiben
# stehen“): das Konto, seine Verknüpfung mit Keycloak, seine Mail-Liste und seine Anmeldung.
KEPT = (User, EmailAddress, SocialAccount, SocialToken, SocialApp, Session, ContentType, Permission, Group)
# Werte, die bei jedem Lauf neu entstehen: zufällige Kennungen und Uhrzeiten.
VOLATILE = {"key", "creation_key", "changed_at", "consent_at", "at"}


@pytest.fixture
def local(settings):
    """Die Einstellungen sagen ausdrücklich „lokal“ (eigener Rechner)."""
    settings.LOCAL_ENVIRONMENT = True
    settings.TEST_ENVIRONMENT = False
    return settings


@pytest.fixture
def test_environment(settings):
    """Die Einstellungen sagen ausdrücklich „Testumgebung“, wie auf dem Server (#58)."""
    settings.LOCAL_ENVIRONMENT = False
    settings.TEST_ENVIRONMENT = True
    return settings


def run() -> str:
    """Führt den Befehl aus und gibt zurück, was er ausgibt."""
    out = StringIO()
    call_command(COMMAND, stdout=out)
    return out.getvalue()


def account(username: str):
    return User.objects.get(username=username)


def unit(name: str) -> Unit:
    return Unit.objects.get(name=name)


def logged_in_before(username: str, first_name: str = "", last_name: str = ""):
    """Ein Konto, das sich schon einmal angemeldet hat: mit Verknüpfung zu einer Kennung aus Keycloak."""
    user = User.objects.create(username=username, first_name=first_name, last_name=last_name,
                               email=f"{username}@example.org")
    SocialAccount.objects.create(user=user, provider="keycloak", uid=f"kennung-{username}")
    return user


@pytest.fixture
def data(local):
    """Nach einem Lauf lokal: Konten und Einheiten unter ihrem Namen."""
    run()
    return SimpleNamespace(
        **{username.replace(".", "_"): account(username) for username in ACCOUNTS},
        **{name: unit(name) for _kind, name, _parent, _rings in UNITS},
    )


def units_now() -> set[tuple]:
    return {(entry.kind, entry.name, entry.parent.name if entry.parent else None, entry.has_rings)
            for entry in Unit.objects.select_related("parent")}


def roles_now() -> set[tuple]:
    return {(role.user.username, role.kind, role.unit.name if role.unit else None)
            for role in Role.objects.select_related("user", "unit")}


def snapshot() -> dict:
    """Alles in der Datenbank außer den Konten und den Werten, die bei jedem Lauf neu entstehen."""
    found = {}
    for model in apps.get_models():
        if model in KEPT:
            continue
        fields = [field.attname for field in model._meta.concrete_fields if field.name not in VOLATILE]
        found[model._meta.label] = list(model.objects.order_by("pk").values_list(*fields))
    return found


def members_in(*names: str) -> set[str]:
    """Die Benutzernamen der Mitglieder dieser Einheiten."""
    return set(Role.objects.filter(kind=R.MEMBER, unit__name__in=names).values_list("user__username", flat=True))


def managed_names(*names: str) -> set[str]:
    """Die Namen der verwalteten Personen in diesen Einheiten."""
    return {person.display_name for person in ManagedPerson.objects.filter(unit__name__in=names)}


def accounts_seen(user) -> set[str]:
    """Die anderen Personen mit Konto, die `user` laut zentraler Rechteprüfung sieht."""
    return set(Rights(user).persons().exclude(pk=user.pk).values_list("username", flat=True))


def managed_seen(user) -> set[str]:
    """Die verwalteten Personen, die `user` laut zentraler Rechteprüfung sieht, in allen Organisationen."""
    rights = Rights(user)
    return {person.display_name for entry in Unit.objects.all() for person in rights.managed_in(entry)}


def leads_seen(user) -> set[tuple[str, str]]:
    """Die Leitungen, die `user` sieht: Benutzername und Rolle."""
    return {(lead["username"], lead["kind"]) for lead in Rights(user).leads()}


def edit_address(person: ManagedPerson) -> str:
    return f"{unit_address(person.unit)}verwaltete-person/{person.key}/bearbeiten/"


# ---------- Befehl ----------


def test_b1_ein_lauf_legt_genau_die_besetzung_an(local):
    run()

    assert units_now() == UNITS
    assert set(User.objects.values_list("username", flat=True)) == ACCOUNTS
    assert roles_now() == ROLES
    assert set(Role.objects.values_list("kind", flat=True)) == set(R.values), "Nicht jede Rolle aus ROL-01 kommt vor"
    assert all(mail.endswith("@example.org") for mail in User.objects.values_list("email", flat=True))


def test_b1_verwaltete_personen_mit_einwilligung_und_einige_mit_fahrtenname(local):
    run()

    persons = list(ManagedPerson.objects.select_related("unit", "consent_by"))
    for name in GROUPS:
        assert 3 <= sum(person.unit.name == name for person in persons) <= 5, name
    assert sum(person.unit.name == "Walhall" for person in persons) == 1
    assert {person.unit.name for person in persons} == {*GROUPS, "Walhall"}
    for person in persons:
        # Bestätigt hat, wer die Person im Tool hätte anlegen dürfen (#98, VP-01).
        assert person.consent_by is not None and person.consent_at is not None, person.display_name
        assert Rights(person.consent_by).may_add_managed(person.unit), person.display_name
    with_scout_name = [person for person in persons if person.scout_name]
    assert 0 < len(with_scout_name) < len(persons)
    assert 15 <= len(persons) + len(members_in("Walhall")) - 1 <= 25, "zusammen rund 20 Personen"


def test_b1_jede_rolle_vergeben_und_jede_einheit_angelegt_im_protokoll(local):
    run()

    for role in Role.objects.all():
        entries = RoleChange.objects.filter(person_id=role.user_id, managed=False, kind=role.kind,
                                            unit_id=role.unit_id, action=RoleChange.Action.GRANTED)
        assert entries.count() == 1, role
    for person in ManagedPerson.objects.all():
        assert RoleChange.objects.filter(person_id=person.pk, managed=True, unit_id=person.unit_id,
                                         action=RoleChange.Action.GRANTED).count() == 1, person.display_name
    for entry in Unit.objects.all():
        assert UnitChange.objects.filter(unit_id=entry.pk, action=UnitChange.Action.CREATED).count() == 1, entry.name
    assert not RoleChange.objects.filter(action=RoleChange.Action.REMOVED).exists()
    assert RoleChange.objects.count() == Role.objects.count() + ManagedPerson.objects.count()
    assert not AdminAccess.objects.exists()


def test_b2_zweiter_lauf_ergibt_dieselben_daten_und_behaelt_alle_konten(local):
    run()
    after_first = snapshot()
    fiete, falken = account("gruppenleitung.falken"), unit("Sippe Falken")
    values = {"first_name": "Nachträglich", "last_name": "Probe", "birth_date": "2015-01-01", "scout_name": "",
              "consent": True}
    Rights(fiete).add_managed(falken, values, new_key())
    falken.name = "Sippe Habichte"
    falken.save(by=fiete)
    extra = logged_in_before("zusatz.konto", "Zara", "Zusatz")
    AdminAccess.record(account("admin"), AdminAccess.Action.STARTED, unit("Walhall"), AdminAccess.Detail.DEBUGGING)
    AccountSearch.objects.create(user=fiete, searched_at=timezone.now())
    assert snapshot() != after_first

    run()

    assert snapshot() == after_first
    assert set(User.objects.values_list("username", flat=True)) == ACCOUNTS | {"zusatz.konto"}
    assert User.objects.filter(pk=extra.pk).exists()
    assert not Role.objects.filter(user=extra).exists()
    assert SocialAccount.objects.get(user=extra).uid == "kennung-zusatz.konto"


def test_ein_zweiter_lauf_leert_auch_veranstaltungen_und_ihre_leitungen(local):
    """Seit #100 hängt an jeder Veranstaltung ihre Leitung in einer eigenen Verbindungstabelle; auch sie wird
    geleert, sonst bräche das Leeren der Veranstaltungen ab und der Befehl liefe gar nicht mehr."""
    run()
    after_first = snapshot()
    fiete = account("gruppenleitung.falken")
    Rights(fiete).create_event({"name": "Probelager 2027", "start": date(2027, 5, 15), "end": date(2027, 5, 17)},
                               new_key())
    assert Event.objects.filter(leads=fiete).exists()

    run()

    assert not Event.objects.exists()
    assert Event.leads.through.objects.count() == 0
    assert snapshot() == after_first


def test_b3_ohne_lokal_oder_testumgebung_bricht_der_befehl_ab_und_loescht_nichts(local):
    run()
    before = snapshot()
    local.LOCAL_ENVIRONMENT = False
    local.TEST_ENVIRONMENT = False

    with pytest.raises(CommandError) as refused:
        run()

    message = str(refused.value)
    assert "lokal" in message and "Testumgebung" in message and "nichts gelöscht" in message
    assert snapshot() == before


def test_b3_nur_ausdruecklich_lokal_oder_testumgebung_erlaubt_den_befehl():
    """LOCAL_ENVIRONMENT ergibt sich aus den Einstellungen des Rechners (config/settings.py)."""
    assert _setting("settings.LOCAL_ENVIRONMENT", {"LOCAL_ENVIRONMENT": "1"}) == "True"
    assert _setting("settings.LOCAL_ENVIRONMENT", {}) == "False"
    # Die Fehleranzeige für Entwickler allein sagt noch nicht „lokal“.
    assert _setting("settings.LOCAL_ENVIRONMENT", {"DJANGO_DEBUG": "1"}) == "False"
    # Sagen die Einstellungen beides, gilt die Testumgebung: Dort legt der Befehl keine Konten an.
    assert _setting("settings.LOCAL_ENVIRONMENT", {"LOCAL_ENVIRONMENT": "1", "TEST_ENVIRONMENT": "1"}) == "False"


def test_b4_fiete_landet_beim_ersten_login_im_konto_aus_dem_befehl(local, client, keycloak):
    run()
    fiete = account("gruppenleitung.falken")
    accounts_before = User.objects.count()
    keycloak.person = {
        "sub": ACCOUNT_IDS["gruppenleitung.falken"],
        "preferred_username": "gruppenleitung.falken",
        "email": "gruppenleitung.falken@example.org",
        "email_verified": True,
        "given_name": fiete.first_name,
        "family_name": fiete.last_name,
    }

    login(client)

    assert int(client.session["_auth_user_id"]) == fiete.pk
    assert User.objects.count() == accounts_before
    assert SocialAccount.objects.get(user=fiete).uid == ACCOUNT_IDS["gruppenleitung.falken"]


def test_b4_jedes_konto_hat_lokal_seine_feste_keycloak_kennung(local):
    run()

    linked = {entry.user.username: entry.uid for entry in SocialAccount.objects.select_related("user")}
    assert linked == {username: ACCOUNT_IDS[username] for username in ACCOUNTS}
    assert set(SocialAccount.objects.values_list("provider", flat=True)) == {"keycloak"}


def test_b5_auf_dem_server_bekommen_nur_angemeldete_konten_ihre_rolle(test_environment):
    logged_in_before("erika.testfrau", "Erika", "Testfrau")
    logged_in_before("ohne.nachname", "Erika")
    ohne_name = logged_in_before("ohne.name")
    # Gegenprobe (unabhängige Prüfung, G2): Auf dem Server bekommen nur die vier Konten aus #62 eine Rolle.
    fiete = logged_in_before("gruppenleitung.falken", "Fiete")

    out = run()

    assert set(User.objects.values_list("username", flat=True)) == {
        "erika.testfrau", "ohne.nachname", "ohne.name", "gruppenleitung.falken"}
    leads = {role for role in roles_now() if role[1] != R.MEMBER}
    assert leads == SERVER_ROLES - {("max.testmann", R.TROOP_LEAD, "Zugvögel")}
    assert not Role.objects.filter(user=ohne_name).exists()
    assert not Role.objects.filter(user=fiete).exists()
    assert units_now() == UNITS
    first_login = [line for line in out.splitlines() if "zuerst" in line]
    assert len(first_login) == 1, out
    assert "max.testmann" in first_login[0]
    assert not any(username in first_login[0] for username in ("erika.testfrau", "ohne.nachname", "ohne.name"))


def test_b5_auf_dem_server_entstehen_verwaltete_personen_nur_wo_eine_leitung_sie_anlegen_darf(test_environment):
    """Sebastian beim Umsetzen, 13.11.2026 (Kommentar in #103): „Nur wo eine Leitung“; die Ausgabe nennt den Rest."""
    erika = logged_in_before("erika.testfrau", "Erika", "Testfrau")
    bund = logged_in_before("ohne.nachname", "Erika")

    out = run()

    persons = ManagedPerson.objects.select_related("unit")
    assert {person.consent_by_id for person in persons if person.unit.name in ("Walhall", *GROUPS[:2])} == {erika.pk}
    # Ohne angemeldete Stammesleitung springt die Bundesleitung für Zugvögel und Kraniche ein (EH-18).
    assert {person.consent_by_id for person in persons if person.unit.name == "Sippe Kraniche"} == {bund.pk}
    assert managed_names("Sippe Möwen") == set()
    assert managed_names("Sippe Falken") and managed_names("Sippe Kraniche")
    assert [line for line in out.splitlines() if "Sippe Möwen" in line], out


def test_b6_wer_vorher_admin_ist_ist_es_danach_wieder_mit_eintrag_im_protokoll(local):
    run()
    ohne_name = account("ohne.name")
    Role(user=ohne_name, kind=R.ADMIN).save(by=account("admin"))

    run()

    assert Role.objects.filter(user=ohne_name, kind=R.ADMIN).exists()
    entries = RoleChange.objects.filter(person_id=ohne_name.pk, kind=R.ADMIN)
    assert list(entries.values_list("action", flat=True)) == [RoleChange.Action.GRANTED]
    assert Role.objects.filter(user=account("admin"), kind=R.ADMIN).exists()


# ---------- Szenario Walhall ----------


@pytest.mark.rechtematrix("PK-02")
@pytest.mark.rechtematrix("VP-02")
def test_w1_erika_sieht_alle_personen_ihres_stammes(data):
    erika = data.erika_testfrau

    assert accounts_seen(erika) == members_in("Walhall", "Sippe Falken", "Meute Wölfe") - {"erika.testfrau"}
    assert {"mitglied.walhall", "gruppenleitung.falken", "mitglied.falken", "gruppenleitung.woelfe"} <= accounts_seen(erika)
    assert managed_seen(erika) == managed_names("Walhall", "Sippe Falken", "Meute Wölfe")
    assert managed_names("Walhall") and managed_names("Sippe Falken") and managed_names("Meute Wölfe")


@pytest.mark.rechtematrix("PK-01")
@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-03")
def test_w2_fiete_sieht_die_falken_aber_nicht_die_woelfe_und_nicht_den_stamm(data):
    fiete = data.gruppenleitung_falken

    assert accounts_seen(fiete) == {"mitglied.falken"}
    assert managed_seen(fiete) == managed_names("Sippe Falken")
    assert not accounts_seen(fiete) & members_in("Meute Wölfe", "Walhall")
    assert not managed_seen(fiete) & managed_names("Meute Wölfe", "Walhall")


@pytest.mark.rechtematrix("PK-05")
@pytest.mark.rechtematrix("VP-06")
def test_w3_finn_sieht_niemanden_nur_die_leitungen_ueber_sich(data):
    finn = data.mitglied_falken

    assert accounts_seen(finn) == set()
    assert managed_seen(finn) == set()
    assert leads_seen(finn) == {
        ("gruppenleitung.falken", R.GROUP_LEAD),
        ("erika.testfrau", R.TROOP_LEAD),
        ("ohne.nachname", R.ASSOCIATION_LEAD),
    }
    assert all("email" not in lead for lead in Rights(finn).leads())


# ---------- Szenario Zugvögel ----------


@pytest.mark.rechtematrix("PK-02")
@pytest.mark.rechtematrix("VP-02")
def test_z1_max_sieht_die_personen_seines_stammes_und_der_kraniche(data):
    max_ = data.max_testmann

    assert accounts_seen(max_) == members_in("Zugvögel", "Sippe Kraniche") - {"max.testmann"}
    assert "gruppenleitung.kraniche" in accounts_seen(max_)
    assert managed_seen(max_) == managed_names("Zugvögel", "Sippe Kraniche")
    assert managed_names("Sippe Kraniche")


@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-03")
def test_z2_max_sieht_niemanden_aus_walhall_und_bekommt_nicht_gefunden(data):
    max_ = data.max_testmann
    walhall = ("Walhall", "Sippe Falken", "Meute Wölfe")

    assert not accounts_seen(max_) & members_in(*walhall)
    assert not managed_seen(max_) & managed_names(*walhall)
    assert_like_missing(max_, unit_address(data.Walhall))
    assert_like_missing(max_, edit_address(ManagedPerson.objects.get(unit=data.Walhall)))


# ---------- Szenario Boreas ----------


@pytest.mark.rechtematrix("PK-03")
@pytest.mark.rechtematrix("VP-02")
def test_o1_bundesleitung_boreas_sieht_alle_personen_im_bund(data):
    bund = data.ohne_nachname

    assert accounts_seen(bund) == members_in(*BOREAS) - {"ohne.nachname"}
    assert managed_seen(bund) == managed_names(*BOREAS)
    assert {"erika.testfrau", "max.testmann", "mitglied.falken"} <= accounts_seen(bund)


@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-03")
def test_o2_nils_sieht_niemanden_aus_boreas_und_walhall_ist_nicht_gefunden(data):
    nils = data.bundesleitung_nordstern

    assert not accounts_seen(nils) & members_in(*BOREAS)
    assert not managed_seen(nils) & managed_names(*BOREAS)
    assert_like_missing(nils, unit_address(data.Walhall))


@pytest.mark.rechtematrix("PK-03")
@pytest.mark.rechtematrix("PK-04")
@pytest.mark.rechtematrix("VP-02")
@pytest.mark.rechtematrix("VP-03")
def test_o3_kai_sieht_leuchtturm_und_moewen_aber_niemanden_aus_boreas(data):
    kai = data.ringleitung_kueste

    assert accounts_seen(kai) == members_in("Küste", "Leuchtturm", "Sippe Möwen") - {"ringleitung.kueste"}
    assert {"stammesleitung.leuchtturm", "gruppenleitung.moewen"} <= accounts_seen(kai)
    assert managed_seen(kai) == managed_names("Leuchtturm", "Sippe Möwen")
    assert managed_names("Sippe Möwen")
    assert not accounts_seen(kai) & members_in(*BOREAS)
    assert not managed_seen(kai) & managed_names(*BOREAS)


@pytest.mark.rechtematrix("PK-07")
@pytest.mark.rechtematrix("VP-06")
@pytest.mark.rechtematrix("RO-05")
def test_o4_vera_sieht_keine_personen_nur_die_bundesleitungen(data):
    vera = data.verbandsleitung

    assert accounts_seen(vera) == set()
    assert managed_seen(vera) == set()
    # Neben den Bundesleitungen sieht sie sich selbst und das DPV-Veranstaltungsteam (RO-05), sonst niemanden.
    assert leads_seen(vera) == {
        ("ohne.nachname", R.ASSOCIATION_LEAD),
        ("bundesleitung.nordstern", R.ASSOCIATION_LEAD),
        ("verbandsleitung", R.FEDERATION_LEAD),
        ("veranstaltungsteam", R.EVENT_TEAM),
    }
    assert all(set(lead) >= {"first_name", "last_name", "scout_name", "kind"} for lead in Rights(vera).leads())


@pytest.mark.rechtematrix("PK-07")
@pytest.mark.rechtematrix("VP-06")
@pytest.mark.rechtematrix("RO-07")
def test_o5_tom_sieht_keine_personen_und_keine_leitungen(data):
    tom = data.veranstaltungsteam

    assert accounts_seen(tom) == set()
    assert managed_seen(tom) == set()
    assert leads_seen(tom) == set()


@pytest.mark.rechtematrix("PK-06")
@pytest.mark.rechtematrix("VP-06")
def test_o6_ohne_name_sieht_nur_das_eigene_profil(data):
    ohne_name = data.ohne_name

    assert list(Rights(ohne_name).persons()) == [ohne_name]
    assert managed_seen(ohne_name) == set()
    assert leads_seen(ohne_name) == set()


# ---------- Was bleibt unverändert? ----------


def _sql_refused(sql: str) -> bool:
    try:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql)
    except DatabaseError:
        return True
    return False


@pytest.mark.rechtematrix("PR-02")
@pytest.mark.rechtematrix("PR-04")
@pytest.mark.rechtematrix("PR-06")
def test_u1_protokolle_bleiben_im_tool_gesperrt_auch_fuer_admins(data):
    AdminAccess.record(data.admin, AdminAccess.Action.STARTED, data.Walhall, AdminAccess.Detail.DEBUGGING)

    for model in (RoleChange, UnitChange, AdminAccess):
        entry = model.objects.first()
        with pytest.raises(ValidationError):
            entry.save()
        with pytest.raises(ValidationError):
            entry.delete()
        table = model._meta.db_table
        assert _sql_refused(f"UPDATE {table} SET actor_name = 'Gekapert'"), table  # noqa: S608 -- feste Tabellennamen
        assert _sql_refused(f"DELETE FROM {table}"), table  # noqa: S608 -- feste Tabellennamen
        assert model.objects.exists()


def test_u2_gleicher_benutzername_mit_anderer_kennung_uebernimmt_kein_konto(data, client, keycloak):
    fiete = data.gruppenleitung_falken
    roles_before = roles_now()
    keycloak.person = {
        "sub": "99999999-aaaa-4bbb-8ccc-000000000099",
        "preferred_username": "gruppenleitung.falken",
        "email": "gruppenleitung.falken@example.org",
        "email_verified": True,
        "given_name": "Fiete",
        "family_name": "Falsch",
    }

    login(client)

    assert int(client.session["_auth_user_id"]) != fiete.pk
    newcomer = User.objects.get(pk=client.session["_auth_user_id"])
    assert not Role.objects.filter(user=newcomer).exists()
    assert roles_now() == roles_before
    assert SocialAccount.objects.get(user=fiete).uid == ACCOUNT_IDS["gruppenleitung.falken"]


def test_u2_der_befehl_uebernimmt_kein_konto_mit_gleichem_benutzernamen_und_anderer_kennung(local):
    stranger = logged_in_before("gruppenleitung.falken", "Fremd", "Konto")

    out = run()

    assert not Role.objects.filter(user=stranger).exists()
    assert SocialAccount.objects.get(user=stranger).uid == "kennung-gruppenleitung.falken"
    assert not SocialAccount.objects.filter(uid=ACCOUNT_IDS["gruppenleitung.falken"]).exists()
    assert "gruppenleitung.falken" in out
    assert roles_now() == {role for role in ROLES if role[0] != "gruppenleitung.falken"}


def test_u3_der_befehl_nimmt_nur_die_normalen_wege_des_tools():
    """Der Befehl prüft bestehende Regeln, er bringt keine eigenen mit (#88, #91, #98).

    Einheiten und Rollen speichert er einzeln über ihr `save(by=…)`, verwaltete Personen legt er über die
    zentrale Rechteprüfung an. Sammeländerungen und eigenes Anlegen umgingen die Regeln und das Protokoll.
    """
    source = (BASE_DIR / "core" / "management" / "commands" / "testdata.py").read_text(encoding="utf-8")

    for bypass in ("bulk_create", ".update(", "objects.create(", "ManagedPerson(", "RoleChange.record", "UnitChange."):
        assert bypass not in source, bypass
    assert "add_managed(" in source
    assert ".save(by=" in source


def test_u4_importdatei_des_test_realms_und_die_kennungen_aus_199_bleiben():
    test_realm = json.loads((BASE_DIR / "testumgebung" / "keycloak" / "dpv-test-realm.json").read_text("utf-8"))
    dev_realm = json.loads((BASE_DIR / "dev" / "keycloak" / "dpv-realm.json").read_text("utf-8"))

    assert {user["username"] for user in test_realm["users"]} == set(IDS_FROM_199)
    assert all("id" not in user for user in test_realm["users"])
    dev_ids = {user["username"]: user.get("id") for user in dev_realm["users"]}
    assert {username: dev_ids.get(username) for username in IDS_FROM_199} == IDS_FROM_199
