"""Tests für das Protokoll der Rollenänderungen (#91, ROL-04).

Die Nummern S1 bis S15 verweisen auf die Szenarien im Issue #91 (Kommentar „Fragen bei der
Umsetzung, 23.10.2026“). Ein Eintrag hält fest, wann wer wem welche Rolle in welcher
Organisation gegeben oder genommen hat, mit den Namen zum Zeitpunkt der Änderung. In P2 sieht
niemand das Protokoll im Tool (Entscheidung W4); diese Tests lesen es direkt aus der Datenbank.
Alle Namen sind erfunden.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction

from roles.models import SERVER_COMMAND, Role, RoleChange
from tests.test_rollen import R, _one_after_the_other, build_org, membership, person, refused
from tests.test_rollen_befehle import run

GRANTED = RoleChange.Action.GRANTED
REMOVED = RoleChange.Action.REMOVED
LOCKED = "Einträge im Protokoll der Rollenänderungen lassen sich nicht ändern oder löschen."


@pytest.fixture
def org(db):
    return build_org()


def give(user, kind, where, by):
    role = Role(user=user, kind=kind, unit=where)
    role.save(by=by)
    return role


def move(user, to, by) -> None:
    member = membership(user)
    member.unit = to
    member.save(by=by)


def entries() -> list[tuple]:
    """Das Protokoll in Reihenfolge des Schreibens: wer, wem, welche Rolle, wo, was."""
    return [
        (e.actor_name, e.person_name, e.kind, e.unit_name, e.action) for e in RoleChange.objects.order_by("pk")
    ]


# Was ins Protokoll kommt


def test_leitung_ohne_mitgliedschaft_ergibt_zwei_eintraege_mit_derselben_uhrzeit(org):
    """S1, das Beispiel aus dem Issue."""
    give(org.max, R.TROOP_LEAD, org.walhall, by=org.erika)

    assert entries() == [
        ("Erika Testfrau", "Max Testmann", R.TROOP_LEAD, "Walhall", GRANTED),
        ("Erika Testfrau", "Max Testmann", R.MEMBER, "Walhall", GRANTED),
    ]
    first, second = RoleChange.objects.order_by("pk")
    assert first.changed_at == second.changed_at
    assert first.changed_at is not None


def test_eintrag_nennt_die_kennungen_von_urheber_person_und_einheit(org):
    give(org.max, R.GROUP_LEAD, org.falken, by=org.erika)

    entry = RoleChange.objects.order_by("pk").first()
    assert (entry.actor_id, entry.person_id, entry.unit_id) == (org.erika.pk, org.max.pk, org.falken.pk)
    assert entry.unit_name == "Sippe Falken (Walhall)"


def test_wechsel_der_mitgliedschaft_ergibt_entfernt_und_vergeben(org):
    """S2."""
    give(org.max, R.MEMBER, org.walhall, by=org.erika)

    move(org.max, org.falken, by=org.erika)

    assert entries()[1:] == [
        ("Erika Testfrau", "Max Testmann", R.MEMBER, "Walhall", REMOVED),
        ("Erika Testfrau", "Max Testmann", R.MEMBER, "Sippe Falken (Walhall)", GRANTED),
    ]
    removed, granted = RoleChange.objects.order_by("pk")[1:]
    assert removed.changed_at == granted.changed_at
    assert (removed.unit_id, granted.unit_id) == (org.walhall.pk, org.falken.pk)


def test_leitung_entfernen_laesst_die_mitgliedschaft_ohne_eintrag(org):
    """S3."""
    lead = give(org.max, R.TROOP_LEAD, org.walhall, by=org.erika)

    lead.delete(by=org.erika)

    assert entries()[2:] == [("Erika Testfrau", "Max Testmann", R.TROOP_LEAD, "Walhall", REMOVED)]
    assert Role.objects.filter(user=org.max, kind=R.MEMBER).exists()


def test_mitgliedschaft_beenden(org):
    """S4: auch, wenn die Person selbst austritt."""
    give(org.max, R.MEMBER, org.falken, by=org.erika)

    membership(org.max).delete(by=org.max)

    assert entries()[1:] == [("Max Testmann", "Max Testmann", R.MEMBER, "Sippe Falken (Walhall)", REMOVED)]


@pytest.mark.parametrize(
    ("kind", "where", "unit_name"),
    [
        (R.FEDERATION_LEAD, "dpv", "DPV"),
        (R.EVENT_TEAM, "dpv", "DPV"),
        (R.RING_LEAD, "kueste", "Küste"),
        (R.ASSOCIATION_LEAD, "boreas", "Pfadfinderbund Boreas"),
    ],
)
def test_jede_rolle_kommt_ins_protokoll(org, kind, where, unit_name):
    """Jede Rolle aus ROL-01, vergeben und entfernt."""
    role = give(org.max, kind, getattr(org, where), by=org.erika)
    role.delete(by=org.erika)

    logged = [e for e in entries() if e[2] == kind]
    assert logged == [
        ("Erika Testfrau", "Max Testmann", kind, unit_name, GRANTED),
        ("Erika Testfrau", "Max Testmann", kind, unit_name, REMOVED),
    ]


def test_admin_ernennen_und_entfernen_per_befehl(org):
    """S5."""
    run("admin", "grant", "max.testmann")
    run("admin", "revoke", "max.testmann")

    assert entries() == [
        ("Befehl auf dem Server", "Max Testmann", R.ADMIN, "", GRANTED),
        ("Befehl auf dem Server", "Max Testmann", R.ADMIN, "", REMOVED),
    ]
    assert all(e.actor_id is None and e.unit_id is None for e in RoleChange.objects.all())


def test_ohne_namen_in_keycloak_steht_der_benutzername(org):
    nameless = person("ohne.namen", "", "")

    give(nameless, R.MEMBER, org.falken, by=SERVER_COMMAND)

    assert entries() == [("Befehl auf dem Server", "ohne.namen", R.MEMBER, "Sippe Falken (Walhall)", GRANTED)]


def test_zweimal_admin_ernennen_ergibt_einen_eintrag(org):
    """S9."""
    run("admin", "grant", "max.testmann")
    run("admin", "grant", "max.testmann")

    assert len(entries()) == 1


def test_speichern_ohne_aenderung_ergibt_keinen_eintrag(org):
    """S10."""
    give(org.max, R.MEMBER, org.falken, by=org.erika)
    lead = give(org.max, R.GROUP_LEAD, org.falken, by=org.erika)

    move(org.max, org.falken, by=org.erika)
    lead.save(by=org.erika)

    assert len(entries()) == 2


def stored_entry(org) -> RoleChange:
    """Ein Eintrag, direkt geschrieben, damit die Tests der Sperre nur die Sperre prüfen."""
    entry = RoleChange(
        actor_id=org.erika.pk,
        actor_name="Erika Testfrau",
        person_id=org.max.pk,
        person_name="Max Testmann",
        kind=R.MEMBER,
        unit_id=org.falken.pk,
        unit_name="Sippe Falken (Walhall)",
        action=GRANTED,
    )
    entry.save()
    return entry


# Abgelehnte Versuche (S6)


def test_abgelehnte_versuche_schreiben_nichts(org):
    """S6: Pfad, zweite Mitgliedschaft, Wechsel mit Leitungsrollen, falsche Ebene, doppelte Rolle."""
    give(org.max, R.GROUP_LEAD, org.falken, by=org.erika)
    before = entries()

    attempts = [
        lambda: give(org.max, R.TROOP_LEAD, org.zugvoegel, by=org.erika),
        lambda: give(org.max, R.MEMBER, org.adler, by=org.erika),
        lambda: move(org.max, org.adler, by=org.erika),
        lambda: membership(org.max).delete(by=org.erika),
        lambda: give(org.max, R.TROOP_LEAD, org.falken, by=org.erika),
        lambda: give(org.max, R.GROUP_LEAD, org.falken, by=org.erika),
    ]
    for attempt in attempts:
        refused(attempt)

    assert entries() == before


def test_eine_rolle_laesst_sich_nicht_umschreiben_und_das_schreibt_nichts(org):
    """S6: Eine andere Rolle als die Mitgliedschaft lässt sich nicht ändern, nur entfernen und neu geben."""
    lead = give(org.max, R.GROUP_LEAD, org.falken, by=org.erika)
    before = entries()

    lead.unit = org.woelfe
    refused(lambda: lead.save(by=org.erika))

    assert entries() == before


# Wer ändert (S15)


def test_aenderung_ohne_urheber_wird_abgelehnt(org):
    """S15: Ohne Angabe, wer ändert, entsteht weder Rolle noch Eintrag."""
    with pytest.raises(TypeError):
        Role(user=org.max, kind=R.MEMBER, unit=org.falken).save()
    with pytest.raises(TypeError):
        Role.objects.create(user=org.max, kind=R.MEMBER, unit=org.falken)
    with pytest.raises(ValueError):
        Role(user=org.max, kind=R.MEMBER, unit=org.falken).save(by=None)
    with pytest.raises(ValueError):
        Role(user=org.max, kind=R.MEMBER, unit=org.falken).save(by="Erika Testfrau")

    assert not Role.objects.exists()
    assert entries() == []


def test_entfernen_ohne_urheber_wird_abgelehnt(org):
    """S15."""
    member = give(org.max, R.MEMBER, org.falken, by=org.erika)

    with pytest.raises(TypeError):
        member.delete()
    with pytest.raises(ValueError):
        member.delete(by=None)

    assert Role.objects.filter(pk=member.pk).exists()
    assert len(entries()) == 1


# Sicherheit


def test_rolle_und_eintrag_nur_zusammen(org, monkeypatch):
    """S11: Lässt sich der Eintrag nicht schreiben, bleibt auch die Rolle unverändert."""
    member = give(org.max, R.MEMBER, org.falken, by=org.erika)

    def broken(*args, **kwargs):
        raise RuntimeError("Protokoll nicht erreichbar")

    monkeypatch.setattr(RoleChange, "save", broken)
    with pytest.raises(RuntimeError):
        give(org.erika, R.TROOP_LEAD, org.walhall, by=org.max)
    with pytest.raises(RuntimeError):
        move(org.max, org.woelfe, by=org.erika)
    with pytest.raises(RuntimeError):
        member.delete(by=org.erika)

    assert not Role.objects.filter(user=org.erika).exists()
    assert membership(org.max).unit == org.falken


def test_auch_der_zweite_eintrag_gehoert_dazu(org, monkeypatch):
    """S11: Scheitert der Eintrag der automatischen Mitgliedschaft, entsteht auch die Leitung nicht."""
    original = RoleChange.save

    def second_fails(entry, *args, **kwargs):
        if entry.kind == R.MEMBER:
            raise RuntimeError("Protokoll nicht erreichbar")
        original(entry, *args, **kwargs)

    monkeypatch.setattr(RoleChange, "save", second_fails)
    with pytest.raises(RuntimeError):
        give(org.max, R.TROOP_LEAD, org.walhall, by=org.erika)

    assert not Role.objects.exists()
    assert not RoleChange.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_zweimal_dieselbe_rolle_ergibt_einen_eintrag():
    """S12."""
    o = build_org()

    results = _one_after_the_other(
        lambda: give(o.max, R.GROUP_LEAD, o.falken, by=o.erika),
        lambda: give(o.max, R.GROUP_LEAD, o.falken, by=o.erika),
    )

    assert results["erste"] == "gespeichert"
    assert "schon Gruppenleitung" in results["zweite"]
    assert entries() == [
        ("Erika Testfrau", "Max Testmann", R.GROUP_LEAD, "Sippe Falken (Walhall)", GRANTED),
        ("Erika Testfrau", "Max Testmann", R.MEMBER, "Sippe Falken (Walhall)", GRANTED),
    ]


def test_umbenennen_aendert_alte_eintraege_nicht(org):
    """S13: Der Eintrag zeigt die Namen zum Zeitpunkt der Änderung."""
    give(org.max, R.GROUP_LEAD, org.falken, by=org.erika)

    org.walhall.name = "Walhall Nord"
    org.walhall.save()
    org.erika.first_name = "Erika Maria"
    org.erika.save()

    assert entries()[0] == ("Erika Testfrau", "Max Testmann", R.GROUP_LEAD, "Sippe Falken (Walhall)", GRANTED)


def test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen(org):
    """S7: auch nicht für Admins; einen Weg dafür gibt es im Tool nicht."""
    entry = stored_entry(org)

    entry.person_name = "Jemand anderes"
    with pytest.raises(ValidationError) as error:
        entry.save()
    assert LOCKED in " ".join(error.value.messages)
    with pytest.raises(ValidationError):
        entry.delete()

    assert entries() == [("Erika Testfrau", "Max Testmann", R.MEMBER, "Sippe Falken (Walhall)", GRANTED)]


@pytest.mark.parametrize(
    "bulk",
    [
        lambda: RoleChange.objects.update(person_name="Jemand anderes"),
        lambda: RoleChange.objects.all().delete(),
        lambda: RoleChange.objects.filter(kind=R.MEMBER)._raw_delete(connection.alias),
    ],
    ids=["sammelaenderung", "sammelloeschung", "loeschen_ohne_pruefung"],
)
def test_sammelaenderungen_scheitern_an_der_datenbank(org, bulk):
    """S7: Die Datenbank selbst lehnt ab, auch an der Sperre im Programm vorbei."""
    stored_entry(org)

    with pytest.raises(DatabaseError, match=LOCKED), transaction.atomic():
        bulk()

    assert entries() == [("Erika Testfrau", "Max Testmann", R.MEMBER, "Sippe Falken (Walhall)", GRANTED)]


def test_aendern_per_sql_scheitert_an_der_datenbank(org):
    """S7."""
    stored_entry(org)

    for statement in ("UPDATE roles_rolechange SET action = 'removed'", "DELETE FROM roles_rolechange"):
        with pytest.raises(DatabaseError, match=LOCKED), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(statement)

    assert len(entries()) == 1


@pytest.mark.django_db(transaction=True)
def test_die_ganze_datenbank_laesst_sich_leeren():
    """S14: Der Testdaten-Befehl (#103) leert lokal und in der Testumgebung alles, auch das Protokoll."""
    o = build_org()
    give(o.max, R.MEMBER, o.falken, by=o.erika)

    call_command("flush", interactive=False, verbosity=0)

    assert not RoleChange.objects.exists()
    assert not Role.objects.exists()


def test_protokoll_hat_kein_feld_fuer_freien_text():
    """S8: kein Grund, keine Bemerkung; freier Text könnte Gesundheitsangaben enthalten."""
    assert {field.name for field in RoleChange._meta.get_fields()} == {
        "id",
        "changed_at",
        "actor_id",
        "actor_name",
        "person_id",
        "person_name",
        "kind",
        "unit_id",
        "unit_name",
        "action",
    }


def test_protokoll_erscheint_nicht_im_log(org, log_output):
    """S8."""
    give(org.max, R.TROOP_LEAD, org.walhall, by=org.erika)
    move(org.max, org.falken, by=org.erika)
    run("admin", "grant", "max.testmann")

    log = log_output()
    assert RoleChange.objects.count() == 5
    for text in ("Max Testmann", "Erika Testfrau", "Walhall", "Falken", "vergeben", "entfernt"):
        assert text not in log
