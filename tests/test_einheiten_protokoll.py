"""Tests für das Protokoll der Strukturänderungen (#131, ORG-06).

Die Nummern S1 bis S16 und F1 bis F3 verweisen auf das Issue #131 (Kommentar „Fragen bei der
Umsetzung, 23.10.2026“). Ein Eintrag hält fest, wann wer welche Organisation angelegt,
umbenannt, einem Ring oder Stamm zugeordnet oder bei ihr „hat Ringe“ umgeschaltet hat, mit
altem und neuem Wert und den Namen zum Zeitpunkt der Änderung. In P2 sieht niemand das
Protokoll im Tool (Entscheidung W4); diese Tests lesen es direkt aus der Datenbank. Alle Namen
sind erfunden.
"""

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import DatabaseError, connection, transaction

from roles.models import SERVER_COMMAND, Role, RoleChange
from tests.test_rollen import R, _one_after_the_other, build_org, refused
from tests.test_einheiten_befehle import refused as command_refused
from tests.test_rollen_befehle import run
from units.models import Unit, UnitChange

U = Unit.Kind
A = UnitChange.Action
LOCKED = "Einträge im Protokoll der Strukturänderungen lassen sich nicht ändern oder löschen."


@pytest.fixture
def org(db):
    return build_org()


def entries(since: int = 0) -> list[tuple]:
    """Das Protokoll in Reihenfolge des Schreibens: wer, welche Organisation, was, alt, neu."""
    return [
        (e.actor_name, e.unit_name, e.action, e.old_value, e.new_value)
        for e in UnitChange.objects.filter(pk__gt=since).order_by("pk")
    ]


def mark() -> int:
    """Die Kennung des letzten Eintrags; was danach kommt, gehört zum Test."""
    last = UnitChange.objects.order_by("pk").last()
    return last.pk if last else 0


def last_entry() -> UnitChange:
    return UnitChange.objects.order_by("pk").last()


def make(kind, name, parent=None, by=SERVER_COMMAND, **extra) -> Unit:
    created = Unit(kind=kind, name=name, parent=parent, **extra)
    created.save(by=by)
    return created


def rename(unit: Unit, name: str, by) -> None:
    unit.name = name
    unit.save(by=by)


def place(unit: Unit, parent: Unit, by) -> None:
    unit.parent = parent
    unit.save(by=by)


# Was ins Protokoll kommt


@pytest.mark.rechtematrix("PR-04")
def test_gruppe_umbenennen(org):
    """S1, das Beispiel aus dem Issue."""
    start = mark()

    rename(org.falken, "Sippe Habichte", by=org.erika)

    assert entries(start) == [("Erika Testfrau", "Sippe Falken (Walhall)", A.RENAMED, "Sippe Falken", "Sippe Habichte")]
    entry = last_entry()
    assert (entry.actor_id, entry.unit_id, entry.unit_kind) == (org.erika.pk, org.falken.pk, U.GROUP)
    assert entry.changed_at is not None


def test_alter_eintrag_im_rollenprotokoll_gehoert_ueber_die_kennung_zum_heutigen_namen(org):
    """S2."""
    Role(user=org.max, kind=R.MEMBER, unit=org.falken).save(by=org.erika)

    rename(org.falken, "Sippe Habichte", by=org.erika)

    role_entry = RoleChange.objects.get()
    assert role_entry.unit_name == "Sippe Falken (Walhall)"
    assert UnitChange.objects.get(action=A.RENAMED).unit_id == role_entry.unit_id
    assert Unit.objects.get(pk=role_entry.unit_id).name == "Sippe Habichte"


def test_stamm_wechselt_den_ring(org):
    """S3."""
    start = mark()

    place(org.leuchtturm, org.nord, by=org.erika)

    assert entries(start) == [("Erika Testfrau", "Leuchtturm", A.RING_CHANGED, "Küste", "Nord")]
    entry = last_entry()
    assert (entry.old_parent_id, entry.new_parent_id) == (org.kueste.pk, org.nord.pk)


def test_alter_stamm_ohne_ring_wird_einem_ring_zugeordnet(org):
    """S4: Stämme von vor dem Einschalten von „hat Ringe“ hängen noch direkt am Bund."""
    org.boreas.has_rings = True
    org.boreas.save(by=org.erika)
    sued = make(U.RING, "Süd", org.boreas, by=org.erika)
    start = mark()

    place(org.walhall, sued, by=org.erika)

    assert entries(start) == [("Erika Testfrau", "Walhall", A.RING_ASSIGNED, "", "Süd")]
    entry = last_entry()
    assert (entry.old_parent_id, entry.new_parent_id) == (org.boreas.pk, sued.pk)


def test_gruppe_wechselt_den_stamm_nicht(org):
    """F3 galt bis #95; seitdem lehnt das Datenmodell den Wechsel ab, und nichts kommt ins Protokoll (Frage 13 in #95)."""
    start = mark()

    with pytest.raises(ValidationError):
        place(org.falken, org.zugvoegel, by=org.erika)

    assert entries(start) == []


def test_umbenennen_per_befehl_auch_nur_in_der_schreibweise(db):
    """S5: „boreas“ → „Boreas“ ist eine Umbenennung."""
    run("federation", "create", "DPV")
    run("association", "create", "boreas")
    start = mark()

    run("association", "rename", "boreas", "Boreas")

    assert entries(start) == [("Befehl auf dem Server", "boreas", A.RENAMED, "boreas", "Boreas")]
    assert last_entry().actor_id is None


def test_verband_umbenennen_per_befehl(db):
    """S5."""
    run("federation", "create", "DPV")
    start = mark()

    run("federation", "rename", "Deutscher Pfadfinderverband")

    assert entries(start) == [("Befehl auf dem Server", "DPV", A.RENAMED, "DPV", "Deutscher Pfadfinderverband")]


def test_verband_und_bund_anlegen_per_befehl(db):
    """S6 mit F1: Der Eintrag nennt, wo die neue Organisation hängt."""
    run("federation", "create", "DPV")
    run("association", "create", "Pfadfinderbund Boreas")

    assert entries() == [
        ("Befehl auf dem Server", "DPV", A.CREATED, "", ""),
        ("Befehl auf dem Server", "Pfadfinderbund Boreas", A.CREATED, "", "DPV"),
    ]
    federation, association = UnitChange.objects.order_by("pk")
    assert (federation.unit_kind, federation.new_parent_id) == (U.FEDERATION, None)
    assert (association.unit_kind, association.new_parent_id) == (U.ASSOCIATION, federation.unit_id)


@pytest.mark.parametrize(
    ("kind", "name", "parent", "logged", "where"),
    [
        (U.RING, "West", "mosaik", "West", "DPBM Mosaik"),
        (U.TROOP, "Nordlicht", "kueste", "Nordlicht", "Küste"),
        (U.TROOP, "Nordlicht", "boreas", "Nordlicht", "Pfadfinderbund Boreas"),
        (U.GROUP, "Sippe Neu", "walhall", "Sippe Neu (Walhall)", "Walhall"),
    ],
)
def test_anlegen_nennt_wo_die_organisation_haengt(org, kind, name, parent, logged, where):
    """F1, zum Beispiel „Nordlicht · angelegt · Küste“."""
    start = mark()

    created = make(kind, name, getattr(org, parent), by=org.erika)

    assert entries(start) == [("Erika Testfrau", logged, A.CREATED, "", where)]
    entry = last_entry()
    assert (entry.unit_id, entry.unit_kind, entry.new_parent_id) == (created.pk, kind, getattr(org, parent).pk)


def test_hat_ringe_einschalten_per_befehl_und_ausschalten_im_datenmodell(db):
    """S7; einen Befehl zum Ausschalten gibt es seit #95 nicht mehr (Frage 16), das Datenmodell protokolliert es weiter (#204)."""
    run("federation", "create", "DPV")
    run("association", "create", "Pfadfinderbund Boreas")
    start = mark()

    run("association", "rings", "Pfadfinderbund Boreas", "on")
    boreas = Unit.objects.get(name="Pfadfinderbund Boreas")
    boreas.has_rings = False
    boreas.save(by=SERVER_COMMAND)

    assert entries(start) == [
        ("Befehl auf dem Server", "Pfadfinderbund Boreas", A.HAS_RINGS, "aus", "ein"),
        ("Befehl auf dem Server", "Pfadfinderbund Boreas", A.HAS_RINGS, "ein", "aus"),
    ]


def test_bund_gleich_mit_ringen_anlegen_ergibt_zwei_eintraege_mit_derselben_uhrzeit(db):
    """F2, S16."""
    run("federation", "create", "DPV")
    start = mark()

    run("association", "create", "DPBM Mosaik", "--rings")

    assert entries(start) == [
        ("Befehl auf dem Server", "DPBM Mosaik", A.CREATED, "", "DPV"),
        ("Befehl auf dem Server", "DPBM Mosaik", A.HAS_RINGS, "aus", "ein"),
    ]
    created, switched = UnitChange.objects.filter(pk__gt=start).order_by("pk")
    assert created.changed_at == switched.changed_at


def test_mehrere_aenderungen_auf_einmal_ergeben_je_einen_eintrag(org):
    """Umbenennen und Ring wechseln in einem Speichern: zwei Einträge mit dem Namen davor."""
    start = mark()

    org.leuchtturm.name = "Leuchtfeuer"
    org.leuchtturm.parent = org.nord
    org.leuchtturm.save(by=org.erika)

    assert entries(start) == [
        ("Erika Testfrau", "Leuchtturm", A.RENAMED, "Leuchtturm", "Leuchtfeuer"),
        ("Erika Testfrau", "Leuchtturm", A.RING_CHANGED, "Küste", "Nord"),
    ]
    first, second = UnitChange.objects.filter(pk__gt=start).order_by("pk")
    assert first.changed_at == second.changed_at


def test_umbenennen_der_einheit_darueber_aendert_alte_eintraege_nicht(org):
    """Namen stehen so im Eintrag, wie sie zum Zeitpunkt der Änderung hießen."""
    rename(org.falken, "Sippe Habichte", by=org.erika)

    rename(org.walhall, "Walhall Nord", by=org.erika)

    assert UnitChange.objects.get(action=A.RENAMED, unit_id=org.falken.pk).unit_name == "Sippe Falken (Walhall)"


# Keine Einträge ohne tatsächliche Änderung (S8)


def test_speichern_ohne_aenderung_ergibt_keinen_eintrag(org):
    """S8: auch nicht mit Leerzeichen am Rand, die das Tool beim Speichern entfernt."""
    start = mark()

    org.walhall.save(by=org.erika)
    rename(org.walhall, "Walhall ", by=org.erika)
    place(org.leuchtturm, org.kueste, by=org.erika)
    org.mosaik.has_rings = True
    org.mosaik.save(by=org.erika)

    assert entries(start) == []


def test_befehle_ohne_aenderung_ergeben_keinen_eintrag(db):
    """S8."""
    run("federation", "create", "DPV")
    run("association", "create", "DPBM Mosaik", "--rings")
    start = mark()

    run("association", "rings", "DPBM Mosaik", "on")
    run("association", "rename", "DPBM Mosaik", " DPBM Mosaik ")
    run("federation", "rename", "DPV")

    assert entries(start) == []


def test_umbenennen_schreibt_einen_veralteten_schalter_nicht_ins_protokoll(org):
    """Nur, was tatsächlich gespeichert wird, kommt ins Protokoll (Befehle schreiben nur ein Feld)."""
    stale = Unit.objects.get(pk=org.boreas.pk)
    org.boreas.has_rings = True
    org.boreas.save(by=org.erika)
    start = mark()

    stale.name = "Bund Boreas"
    stale.save(update_fields=["name"], by=org.erika)

    assert entries(start) == [("Erika Testfrau", "Pfadfinderbund Boreas", A.RENAMED, "Pfadfinderbund Boreas", "Bund Boreas")]


def test_neuer_ort_steht_mit_seinem_gespeicherten_namen_im_eintrag(org):
    """Befund der zweiten unabhängigen Prüfung: auch wenn die Einheit darüber im Programm veraltet ist."""
    stale_ring = Unit.objects.get(pk=org.kueste.pk)
    stale_troop = Unit.objects.get(pk=org.walhall.pk)
    rename(org.kueste, "Küste Ost", by=org.erika)
    rename(org.walhall, "Walhall Nord", by=org.erika)
    start = mark()

    place(org.sturmvogel, stale_ring, by=org.erika)
    make(U.GROUP, "Sippe Neu", stale_troop, by=org.erika)

    assert entries(start) == [
        ("Erika Testfrau", "Sturmvogel", A.RING_CHANGED, "Nord", "Küste Ost"),
        ("Erika Testfrau", "Sippe Neu (Walhall Nord)", A.CREATED, "", "Walhall Nord"),
    ]


def test_felder_zum_schreiben_auch_als_einmal_lesbare_folge(org):
    """Befund der unabhängigen Prüfung: Auch dann kommt die Umbenennung ins Protokoll."""
    start = mark()

    org.walhall.name = "Walhall Nord"
    org.walhall.save(update_fields=iter(["name"]), by=org.erika)

    assert entries(start) == [("Erika Testfrau", "Walhall", A.RENAMED, "Walhall", "Walhall Nord")]


def test_loeschen_einer_leeren_einheit_steht_nicht_in_diesem_protokoll(org):
    """Das Notfall-Löschen durch Admins steht im Protokoll der Admin-Zugriffe (#92)."""
    start = mark()

    org.moewen.delete()

    assert entries(start) == []


# Abgelehnte Versuche (S9)


def test_abgelehnte_versuche_schreiben_nichts(org):
    """S9: doppelter Name, Ausschalten mit Ringen, Stamm ohne Ring, anderer Bund, andere Ebene."""
    start = mark()

    def change(unit, **values):
        def attempt():
            fresh = Unit.objects.get(pk=unit.pk)
            for field, value in values.items():
                setattr(fresh, field, value)
            fresh.save(by=org.erika)

        return attempt

    attempts = [
        change(org.zugvoegel, name="walhall"),
        change(org.mosaik, has_rings=False),
        lambda: make(U.TROOP, "Neu", org.mosaik, by=org.erika),
        change(org.leuchtturm, parent=org.mosaik),
        change(org.walhall, parent=org.kueste),
        change(org.kueste, kind=U.TROOP),
        lambda: make(U.GROUP, "sippe falken ", org.walhall, by=org.erika),
    ]
    for attempt in attempts:
        refused(attempt)

    assert entries(start) == []


def test_abgelehnte_befehle_schreiben_nichts(db):
    """S9."""
    run("federation", "create", "DPV")
    run("association", "create", "DPBM Mosaik", "--rings")
    run("association", "create", "Pfadfinderbund Boreas")
    Unit(kind=U.RING, name="Küste", parent=Unit.objects.get(name="DPBM Mosaik")).save(by=SERVER_COMMAND)
    start = mark()

    for arguments in [
        ("federation", "create", "Zweiter Verband"),
        ("association", "create", "pfadfinderbund boreas"),
        ("association", "rename", "DPBM Mosaik", "Pfadfinderbund Boreas"),
        ("association", "rings", "DPBM Mosaik", "off"),
    ]:
        command_refused(*arguments)

    assert entries(start) == []


# Sicherheit


def test_organisation_und_eintrag_nur_zusammen(org, monkeypatch):
    """S10: Lässt sich der Eintrag nicht schreiben, bleibt auch die Organisation unverändert."""

    def broken(*args, **kwargs):
        raise RuntimeError("Protokoll nicht erreichbar")

    monkeypatch.setattr(UnitChange, "save", broken)
    with pytest.raises(RuntimeError):
        rename(org.falken, "Sippe Habichte", by=org.erika)
    with pytest.raises(RuntimeError):
        place(org.leuchtturm, org.nord, by=org.erika)
    with pytest.raises(RuntimeError):
        make(U.TROOP, "Nordlicht", org.boreas, by=org.erika)

    assert Unit.objects.get(pk=org.falken.pk).name == "Sippe Falken"
    assert Unit.objects.get(pk=org.leuchtturm.pk).parent_id == org.kueste.pk
    assert not Unit.objects.filter(name="Nordlicht").exists()


def test_auch_der_zweite_eintrag_gehoert_dazu(db, monkeypatch):
    """S10: Scheitert der Eintrag zu „hat Ringe“, entsteht auch der Bund nicht."""
    run("federation", "create", "DPV")
    original = UnitChange.save

    def second_fails(entry, *args, **kwargs):
        if entry.action == A.HAS_RINGS:
            raise RuntimeError("Protokoll nicht erreichbar")
        original(entry, *args, **kwargs)

    monkeypatch.setattr(UnitChange, "save", second_fails)
    with pytest.raises(RuntimeError):
        make(U.ASSOCIATION, "DPBM Mosaik", Unit.objects.get(kind=U.FEDERATION), has_rings=True)

    assert not Unit.objects.filter(kind=U.ASSOCIATION).exists()
    assert entries() == [("Befehl auf dem Server", "DPV", A.CREATED, "", "")]


def stored_entry(org) -> UnitChange:
    """Ein Eintrag, direkt geschrieben, damit die Tests der Sperre nur die Sperre prüfen."""
    entry = UnitChange(
        actor_id=org.erika.pk,
        actor_name="Erika Testfrau",
        unit_id=org.falken.pk,
        unit_kind=U.GROUP,
        unit_name="Sippe Falken (Walhall)",
        action=A.RENAMED,
        old_value="Sippe Falken",
        new_value="Sippe Habichte",
    )
    entry.save()
    return entry


@pytest.mark.rechtematrix("PR-04")
def test_eintrag_laesst_sich_im_programm_nicht_aendern_oder_loeschen(org):
    """S11: auch nicht für Admins; einen Weg dafür gibt es im Tool nicht."""
    entry = stored_entry(org)
    count = UnitChange.objects.count()

    entry.new_value = "Sippe Adler"
    with pytest.raises(ValidationError) as error:
        entry.save()
    assert LOCKED in " ".join(error.value.messages)
    with pytest.raises(ValidationError):
        entry.delete()

    assert UnitChange.objects.count() == count
    assert UnitChange.objects.get(pk=entry.pk).new_value == "Sippe Habichte"


@pytest.mark.rechtematrix("PR-04")
@pytest.mark.parametrize(
    "bulk",
    [
        lambda: UnitChange.objects.update(new_value="Sippe Adler"),
        lambda: UnitChange.objects.all().delete(),
        lambda: UnitChange.objects.filter(action=A.RENAMED)._raw_delete(connection.alias),
    ],
    ids=["sammelaenderung", "sammelloeschung", "loeschen_ohne_pruefung"],
)
def test_sammelaenderungen_scheitern_an_der_datenbank(org, bulk):
    """S11: Die Datenbank selbst lehnt ab, auch an der Sperre im Programm vorbei."""
    entry = stored_entry(org)
    before = entries()

    with pytest.raises(DatabaseError, match=LOCKED), transaction.atomic():
        bulk()

    assert entries() == before
    assert UnitChange.objects.get(pk=entry.pk).new_value == "Sippe Habichte"


@pytest.mark.rechtematrix("PR-04")
def test_aendern_per_sql_scheitert_an_der_datenbank(org):
    """S11."""
    stored_entry(org)
    before = entries()

    for statement in ("UPDATE units_unitchange SET new_value = 'x'", "DELETE FROM units_unitchange"):
        with pytest.raises(DatabaseError, match=LOCKED), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(statement)

    assert entries() == before


# Wer ändert (S12)


def test_aenderung_ohne_urheber_wird_abgelehnt(org):
    """S12: Ohne Angabe, wer ändert, entsteht weder Organisation noch Eintrag."""
    start = mark()

    with pytest.raises(TypeError):
        Unit(kind=U.TROOP, name="Nordlicht", parent=org.boreas).save()
    with pytest.raises(TypeError):
        Unit.objects.create(kind=U.TROOP, name="Nordlicht", parent=org.boreas)
    with pytest.raises(ValueError):
        make(U.TROOP, "Nordlicht", org.boreas, by=None)
    with pytest.raises(ValueError):
        make(U.TROOP, "Nordlicht", org.boreas, by="Erika Testfrau")
    org.walhall.name = "Walhall Nord"
    with pytest.raises(TypeError):
        org.walhall.save()

    assert not Unit.objects.filter(name="Nordlicht").exists()
    assert entries(start) == []


def test_umbenennen_ohne_urheber_wird_abgelehnt(org):
    """S12."""
    start = mark()

    with pytest.raises(ValueError):
        rename(org.walhall, "Walhall Nord", by=None)

    assert Unit.objects.get(pk=org.walhall.pk).name == "Walhall"
    assert entries(start) == []


@pytest.mark.django_db(transaction=True)
def test_die_ganze_datenbank_laesst_sich_leeren():
    """S13: Der Testdaten-Befehl (#103) leert lokal und in der Testumgebung alles, auch das Protokoll."""
    build_org()
    assert UnitChange.objects.exists()

    call_command("flush", interactive=False, verbosity=0)

    assert not UnitChange.objects.exists()
    assert not Unit.objects.exists()


def test_protokoll_hat_kein_feld_fuer_freien_text():
    """S14: kein Grund, keine Bemerkung; freier Text könnte Gesundheitsangaben enthalten."""
    assert {field.name for field in UnitChange._meta.get_fields()} == {
        "id",
        "changed_at",
        "actor_id",
        "actor_name",
        "unit_id",
        "unit_kind",
        "unit_name",
        "action",
        "old_value",
        "new_value",
        "old_parent_id",
        "new_parent_id",
    }


def test_protokoll_erscheint_nicht_im_log(org, log_output):
    """S14."""
    rename(org.falken, "Sippe Habichte", by=org.erika)
    place(org.leuchtturm, org.nord, by=org.erika)
    run("association", "rings", "Pfadfinderbund Boreas", "on")

    log = log_output()
    assert UnitChange.objects.filter(action__in=(A.RENAMED, A.RING_CHANGED, A.HAS_RINGS)).count() == 4
    for text in ("Erika Testfrau", "Habichte", "Leuchtturm", "umbenannt", "Ring gewechselt", "hat Ringe", *A.values):
        assert text not in log


@pytest.mark.django_db(transaction=True)
def test_zwei_gleichzeitige_umbenennungen_stehen_in_der_richtigen_reihenfolge():
    """S15: Die zweite sieht den Namen, den die erste gespeichert hat, nicht den von vorher."""
    o = build_org()
    start = mark()

    def second():
        stale = Unit.objects.get(pk=o.falken.pk)
        rename(stale, "Sippe Adler", by=o.max)

    results = _one_after_the_other(lambda: rename(o.falken, "Sippe Habichte", by=o.erika), second)

    assert results == {"erste": "gespeichert", "zweite": "gespeichert"}
    assert entries(start) == [
        ("Erika Testfrau", "Sippe Falken (Walhall)", A.RENAMED, "Sippe Falken", "Sippe Habichte"),
        ("Max Testmann", "Sippe Habichte (Walhall)", A.RENAMED, "Sippe Habichte", "Sippe Adler"),
    ]
