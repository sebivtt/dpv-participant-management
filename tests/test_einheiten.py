"""Tests für die Einheiten des DPV: Aufbau, Ringe, Namen und Löschschutz (#88, ORG-01).

Die Nummern S1 bis S16 verweisen auf die Szenarien im Issue #88 (Kommentar „Fragen bei der
Umsetzung, 23.10.2026“). Die Regeln gelten beim Speichern jeder Einheit, egal auf welchem
Weg sie entsteht; deshalb prüfen diese Tests direkt am Datenmodell. Die Befehle für Admins
prüft tests/test_einheiten_befehle.py. Alle Namen sind erfunden oder öffentlich bekannt.
"""

import threading

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.urls import get_resolver

from tests.keycloak_fake import login
from tests.test_rundumtest import ALL
from units.models import Unit

Kind = Unit.Kind


def make(kind: str, name: str, parent: Unit | None = None) -> Unit:
    """Legt eine Einheit an, auf demselben Weg wie jeder andere Teil des Tools."""
    return Unit.objects.create(kind=kind, name=name, parent=parent)


@pytest.fixture
def dpv(db) -> Unit:
    return make(Kind.FEDERATION, "DPV")


@pytest.fixture
def boreas(dpv) -> Unit:
    return make(Kind.ASSOCIATION, "Pfadfinderbund Boreas", dpv)


@pytest.fixture
def mosaik(dpv) -> Unit:
    association = Unit(kind=Kind.ASSOCIATION, name="DPBM Mosaik", parent=dpv, has_rings=True)
    association.save()
    return association


def rejected(unit: Unit) -> str:
    """Speichert und gibt die Meldung der Ablehnung zurück; schlägt fehl, wenn gespeichert wurde."""
    with pytest.raises(ValidationError) as error:
        unit.save()
    return " ".join(error.value.messages)


# Aufbau


@pytest.mark.django_db
def test_es_gibt_genau_einen_verband(dpv):
    """S1."""
    message = rejected(Unit(kind=Kind.FEDERATION, name="Zweiter Verband"))

    assert "Es gibt schon einen Verband: „DPV“." in message
    assert Unit.objects.filter(kind=Kind.FEDERATION).count() == 1


@pytest.mark.django_db
def test_bund_braucht_den_verband():
    """S3."""
    message = rejected(Unit(kind=Kind.ASSOCIATION, name="Pfadfinderbund Boreas"))

    assert "Ein Bund hängt am Verband." in message


@pytest.mark.django_db
def test_einheiten_haengen_in_der_reihenfolge_verband_bund_ring_stamm_gruppe(boreas, mosaik):
    kueste = make(Kind.RING, "Küste", mosaik)
    leuchtturm = make(Kind.TROOP, "Leuchtturm", kueste)
    walhall = make(Kind.TROOP, "Walhall", boreas)
    falken = make(Kind.GROUP, "Sippe Falken", walhall)
    moewen = make(Kind.GROUP, "Meute Möwen", leuchtturm)

    assert [falken.parent, walhall.parent, boreas.parent.kind] == [walhall, boreas, Kind.FEDERATION]
    assert [moewen.parent, leuchtturm.parent, kueste.parent] == [leuchtturm, kueste, mosaik]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "parent_name", "message"),
    [
        (Kind.FEDERATION, "DPV", "Über dem Verband gibt es nichts."),
        (Kind.ASSOCIATION, "Pfadfinderbund Boreas", "Ein Bund hängt am Verband."),
        (Kind.RING, "DPV", "Ein Ring hängt an einem Bund."),
        (Kind.RING, "Walhall", "Ein Ring hängt an einem Bund."),
        (Kind.TROOP, "DPV", "Ein Stamm hängt an einem Ring oder direkt an einem Bund."),
        (Kind.TROOP, "Walhall", "Ein Stamm hängt an einem Ring oder direkt an einem Bund."),
        (Kind.GROUP, "Pfadfinderbund Boreas", "Eine Gruppe hängt an einem Stamm."),
        (Kind.GROUP, "Sippe Falken", "Eine Gruppe hängt an einem Stamm."),
        (Kind.GROUP, None, "Eine Gruppe hängt an einem Stamm."),
    ],
)
def test_falsche_ebene_wird_abgelehnt(boreas, kind, parent_name, message):
    """S13."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)
    parent = Unit.objects.get(name=parent_name) if parent_name else None
    before = Unit.objects.count()

    assert message in rejected(Unit(kind=kind, name="Neu", parent=parent))
    assert Unit.objects.count() == before


@pytest.mark.django_db
def test_gruppen_werden_frei_benannt(boreas):
    walhall = make(Kind.TROOP, "Walhall", boreas)

    for name in ("Meute Wölfe", "Sippe Falken", "Runde der Alten", "Irgendwas ganz anderes"):
        assert make(Kind.GROUP, name, walhall).kind == Kind.GROUP


# Ringe


@pytest.mark.django_db
def test_ring_nur_in_einem_bund_mit_ringen(boreas, mosaik):
    """S7."""
    message = rejected(Unit(kind=Kind.RING, name="Küste", parent=boreas))

    assert "Im Bund „Pfadfinderbund Boreas“ ist „hat Ringe“ ausgeschaltet." in message
    assert make(Kind.RING, "Küste", mosaik).parent == mosaik


@pytest.mark.django_db
def test_schalter_hat_ringe_ist_standardmaessig_aus(boreas):
    assert boreas.has_rings is False


@pytest.mark.django_db
def test_im_bund_mit_ringen_haengt_jeder_neue_stamm_in_einem_ring(mosaik):
    """S8."""
    kueste = make(Kind.RING, "Küste", mosaik)

    message = rejected(Unit(kind=Kind.TROOP, name="Walhall", parent=mosaik))

    assert "Im Bund „DPBM Mosaik“ hängt jeder neue Stamm in einem Ring." in message
    assert make(Kind.TROOP, "Walhall", kueste).parent == kueste


@pytest.mark.django_db
def test_ringe_einschalten_obwohl_es_schon_staemme_gibt(boreas):
    """S9: Bestehende Stämme bleiben ohne Ring und lassen sich weiter bearbeiten."""
    walhall = make(Kind.TROOP, "Walhall", boreas)

    boreas.has_rings = True
    boreas.save()
    walhall.refresh_from_db()
    walhall.name = "Walhall am See"
    walhall.save()

    walhall.refresh_from_db()
    assert (walhall.name, walhall.parent) == ("Walhall am See", boreas)


@pytest.mark.django_db
def test_ringe_ausschalten_nur_ohne_ring(mosaik):
    """S10."""
    ring = make(Kind.RING, "Küste", mosaik)

    mosaik.has_rings = False
    message = rejected(mosaik)

    assert "Der Bund „DPBM Mosaik“ hat noch Ringe." in message
    mosaik.refresh_from_db()
    assert mosaik.has_rings is True

    ring.delete()
    mosaik.has_rings = False
    mosaik.save()
    mosaik.refresh_from_db()
    assert mosaik.has_rings is False


@pytest.mark.django_db
@pytest.mark.parametrize("kind", [Kind.RING, Kind.TROOP, Kind.GROUP])
def test_nur_ein_bund_hat_den_schalter_hat_ringe(mosaik, kind):
    kueste = make(Kind.RING, "Küste", mosaik)
    leuchtturm = make(Kind.TROOP, "Leuchtturm", kueste)
    parent = {Kind.RING: mosaik, Kind.TROOP: kueste, Kind.GROUP: leuchtturm}[kind]

    assert "Nur ein Bund hat Ringe." in rejected(Unit(kind=kind, name="Neu", parent=parent, has_rings=True))


@pytest.mark.django_db
def test_auch_der_verband_hat_keinen_schalter_hat_ringe():
    assert "Nur ein Bund hat Ringe." in rejected(Unit(kind=Kind.FEDERATION, name="DPV", has_rings=True))


@pytest.mark.django_db
def test_die_ebene_einer_einheit_bleibt(mosaik):
    """Befund der unabhängigen Prüfung: Aus einem Ring mit Stämmen darf kein Stamm werden."""
    nord = make(Kind.RING, "Nord", mosaik)
    make(Kind.TROOP, "Leuchtturm", nord)

    nord.kind = Kind.TROOP

    assert "Die Ebene lässt sich nachträglich nicht ändern." in rejected(nord)
    assert Unit.objects.get(pk=nord.pk).kind == Kind.RING


@pytest.mark.django_db
def test_stamm_und_ring_wechseln_nicht_den_bund(boreas, mosaik):
    """Befund der unabhängigen Prüfung: Sonst stimmt der gemerkte Bund der Einheiten darunter nicht mehr."""
    nord = make(Kind.RING, "Nord", mosaik)
    walhall = make(Kind.TROOP, "Walhall", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)
    boreas.has_rings = True
    boreas.save()

    walhall.parent = nord
    assert "Ein Ring oder Stamm bleibt in seinem Bund." in rejected(walhall)
    nord.parent = boreas
    assert "Ein Ring oder Stamm bleibt in seinem Bund." in rejected(nord)


@pytest.mark.django_db
def test_stamm_im_bund_mit_ringen_kommt_nicht_aus_dem_ring_heraus(mosaik):
    """Frage 4 der Klärung: In einem Bund mit Ringen ist der Ring Pflicht, auch beim Verschieben."""
    nord = make(Kind.RING, "Nord", mosaik)
    leuchtturm = make(Kind.TROOP, "Leuchtturm", nord)

    leuchtturm.parent = mosaik

    assert "Im Bund „DPBM Mosaik“ hängt jeder neue Stamm in einem Ring." in rejected(leuchtturm)


@pytest.mark.django_db
def test_stamm_im_bund_in_einen_ring_verschieben_geht(boreas):
    """Gegenprobe: Zuordnen zu einem Ring und Wechsel des Rings im selben Bund bleiben möglich (#95)."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    boreas.has_rings = True
    boreas.save()
    nord = make(Kind.RING, "Nord", boreas)
    sued = make(Kind.RING, "Süd", boreas)

    for ring in (nord, sued):
        walhall.parent = ring
        walhall.save()
        walhall.refresh_from_db()
        assert walhall.parent == ring


# Namen


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["", "   "])
def test_kein_name_ist_leer(dpv, name):
    """S4."""
    assert "Der Name darf nicht leer sein." in rejected(Unit(kind=Kind.ASSOCIATION, name=name, parent=dpv))


@pytest.mark.django_db
def test_name_hoechstens_100_zeichen(dpv):
    """S16."""
    assert make(Kind.ASSOCIATION, "B" * 100, dpv).name == "B" * 100

    assert "höchstens 100 Zeichen" in rejected(Unit(kind=Kind.ASSOCIATION, name="C" * 101, parent=dpv))


@pytest.mark.django_db
def test_leerzeichen_am_rand_werden_beim_speichern_entfernt(dpv):
    assert make(Kind.ASSOCIATION, "  Pfadfinderbund Boreas ", dpv).name == "Pfadfinderbund Boreas"
    assert Unit.objects.get(kind=Kind.ASSOCIATION).name == "Pfadfinderbund Boreas"


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["Pfadfinderbund Boreas", " pfadfinderbund boreas ", "PFADFINDERBUND BOREAS"])
def test_bund_ist_im_verband_eindeutig(boreas, name):
    """S2."""
    message = rejected(Unit(kind=Kind.ASSOCIATION, name=name, parent=boreas.parent))

    assert "Den Bund „Pfadfinderbund Boreas“ gibt es schon." in message


@pytest.mark.django_db
def test_gleich_ist_auch_mit_umlauten_in_anderer_schreibweise(dpv):
    make(Kind.ASSOCIATION, "Bund Übermut", dpv)

    assert "gibt es schon" in rejected(Unit(kind=Kind.ASSOCIATION, name="BUND üBERMUT", parent=dpv))


@pytest.mark.django_db
def test_leerzeichen_in_der_mitte_machen_einen_anderen_namen(boreas):
    """Antwort B im Issue: Nur Groß- und Kleinschreibung und Leerzeichen am Rand zählen."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)

    assert make(Kind.GROUP, "Sippe  Falken", walhall).name == "Sippe  Falken"


@pytest.mark.django_db
def test_stamm_ist_im_bund_eindeutig_auch_ueber_verschiedene_ringe(boreas, mosaik):
    """S11."""
    nord = make(Kind.RING, "Nord", mosaik)
    sued = make(Kind.RING, "Süd", mosaik)
    make(Kind.TROOP, "Walhall", boreas)
    make(Kind.TROOP, "Walhall", nord)

    message = rejected(Unit(kind=Kind.TROOP, name="walhall", parent=sued))

    assert "Im Bund „DPBM Mosaik“ gibt es schon den Stamm „Walhall“." in message


@pytest.mark.django_db
def test_stamm_ohne_ring_und_stamm_im_ring_teilen_sich_die_namen(boreas):
    """S11: Ein Stamm, der aus der Zeit vor dem Schalter noch ohne Ring ist, zählt mit."""
    make(Kind.TROOP, "Walhall", boreas)
    boreas.has_rings = True
    boreas.save()
    nord = make(Kind.RING, "Nord", boreas)

    assert "gibt es schon den Stamm „Walhall“" in rejected(Unit(kind=Kind.TROOP, name="Walhall", parent=nord))


@pytest.mark.django_db
def test_ring_und_stamm_im_selben_bund_heissen_nie_gleich(mosaik):
    """Antwort A im Issue."""
    kueste = make(Kind.RING, "Küste", mosaik)
    make(Kind.TROOP, "Leuchtturm", kueste)

    assert "Im Bund „DPBM Mosaik“ gibt es schon den Ring „Küste“." in rejected(
        Unit(kind=Kind.TROOP, name="küste", parent=kueste)
    )
    assert "Im Bund „DPBM Mosaik“ gibt es schon den Stamm „Leuchtturm“." in rejected(
        Unit(kind=Kind.RING, name="Leuchtturm", parent=mosaik)
    )


@pytest.mark.django_db
def test_gruppe_ist_im_stamm_eindeutig_darf_aber_in_anderem_stamm_gleich_heissen(boreas):
    """S12."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    zugvoegel = make(Kind.TROOP, "Zugvögel", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)

    assert make(Kind.GROUP, "Sippe Falken", zugvoegel).parent == zugvoegel
    message = rejected(Unit(kind=Kind.GROUP, name="sippe falken ", parent=walhall))
    assert "Im Stamm „Walhall“ gibt es schon die Gruppe „Sippe Falken“." in message


@pytest.mark.django_db
def test_umbenennen_nur_in_der_schreibweise_geht(boreas):
    """S5."""
    boreas.name = "PFADFINDERBUND BOREAS"
    boreas.save()

    boreas.refresh_from_db()
    assert boreas.name == "PFADFINDERBUND BOREAS"


@pytest.mark.django_db
def test_umbenennen_auf_einen_vergebenen_namen_wird_abgelehnt(boreas, mosaik):
    """S6."""
    mosaik.name = "pfadfinderbund boreas"

    assert "Den Bund „Pfadfinderbund Boreas“ gibt es schon." in rejected(mosaik)
    mosaik.refresh_from_db()
    assert mosaik.name == "DPBM Mosaik"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "change",
    [
        {"name": ""},
        {"name": " Walhall "},
        {"name": "walhall", "kind": Kind.RING},
        {"has_rings": True},
        {"kind": Kind.FEDERATION, "parent": None, "association": None},
    ],
    ids=["leer", "leerzeichen", "ring-gleichnamig", "schalter-am-stamm", "zweiter-verband"],
)
def test_datenbank_haelt_die_regeln_auch_ohne_pruefung_des_tools(mosaik, change):
    """Wer an `save()` vorbei direkt in die Datenbank schreibt, scheitert an ihren eigenen Regeln."""
    kueste = make(Kind.RING, "Küste", mosaik)
    make(Kind.TROOP, "Walhall", kueste)
    other = make(Kind.TROOP, "Leuchtturm", kueste)

    with pytest.raises(IntegrityError), transaction.atomic():
        Unit.objects.filter(pk=other.pk).update(**change)


# Löschen (Entscheidung W5)


@pytest.mark.django_db
def test_einheit_mit_untereinheiten_laesst_sich_nicht_loeschen(boreas):
    """S14: über das Tool."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)

    for unit in (walhall, boreas, boreas.parent):
        with pytest.raises(ProtectedError):
            unit.delete()
    assert Unit.objects.count() == 4


@pytest.mark.django_db
def test_auch_die_datenbank_selbst_verhindert_das_loeschen(boreas):
    """S14: auch wer an der Prüfung des Tools vorbei direkt in der Datenbank löscht."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    make(Kind.GROUP, "Sippe Falken", walhall)

    with pytest.raises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute(f"DELETE FROM {Unit._meta.db_table} WHERE id = %s", [walhall.pk])  # noqa: S608 -- fester Tabellenname
    assert Unit.objects.filter(pk=walhall.pk).exists()


@pytest.mark.django_db
def test_leere_einheit_laesst_sich_im_notfall_loeschen(boreas):
    """S14: Notfallweg aus W5, ein Admin löscht eine leere Einheit von Hand."""
    walhall = make(Kind.TROOP, "Walhall", boreas)
    falken = make(Kind.GROUP, "Sippe Falken", walhall)

    falken.delete()
    walhall.delete()

    assert list(Unit.objects.values_list("name", flat=True).order_by("name")) == ["DPV", "Pfadfinderbund Boreas"]


# Wer darf das nicht?


def test_keine_adresse_im_tool_legt_einheiten_an_oder_aendert_sie():
    """S15: Verband und Bünde gibt es in P2 nur per Befehl; auch Djangos Verwaltungsseite fehlt."""
    from django.conf import settings

    views = {f"{entry.callback.__module__}.{entry.callback.__name__}" for _pattern, entry in ALL}

    assert ALL, "Der Rundumtest findet keine Adressen"
    assert not [view for view in views if view.startswith("units")]
    assert "django.contrib.admin" not in settings.INSTALLED_APPS
    assert "units" not in {str(pattern.pattern) for pattern in get_resolver().url_patterns}


@pytest.mark.django_db
def test_login_legt_keine_einheiten_an(client, keycloak):
    """Die Struktur kommt nie aus Keycloak (OP-1)."""
    login(client)

    assert Unit.objects.count() == 0


# Gleichzeitige Änderungen


def _in_thread(work, results: dict, key: str) -> threading.Thread:
    """Führt eine Änderung in einem eigenen Thread mit eigener Datenbankverbindung aus."""

    def run():
        try:
            work()
            results[key] = "gespeichert"
        except ValidationError as error:
            results[key] = " ".join(error.messages)
        finally:
            connection.close()

    thread = threading.Thread(target=run)
    thread.start()
    return thread


@pytest.mark.django_db(transaction=True)
def test_ring_anlegen_und_gleichzeitig_ringe_ausschalten():
    """Der Ring entsteht zuerst; das gleichzeitige Ausschalten muss danach den Ring sehen."""
    dpv = make(Kind.FEDERATION, "DPV")
    mosaik = Unit(kind=Kind.ASSOCIATION, name="DPBM Mosaik", parent=dpv, has_rings=True)
    mosaik.save()
    ring_saved, release = threading.Event(), threading.Event()
    results: dict[str, str] = {}

    def create_ring():
        with transaction.atomic():
            make(Kind.RING, "Küste", mosaik)
            ring_saved.set()
            release.wait(10)

    def switch_off():
        ring_saved.wait(10)
        stale = Unit.objects.get(pk=mosaik.pk)
        stale.has_rings = False
        stale.save()

    first = _in_thread(create_ring, results, "ring")
    second = _in_thread(switch_off, results, "aus")
    second.join(1)
    release.set()
    first.join(10)
    second.join(10)

    mosaik.refresh_from_db()
    assert results["ring"] == "gespeichert"
    assert "hat noch Ringe" in results["aus"]
    assert mosaik.has_rings is True


@pytest.mark.django_db(transaction=True)
def test_ringe_ausschalten_und_gleichzeitig_ring_anlegen():
    """Das Ausschalten kommt zuerst; der gleichzeitige Ring muss danach abgelehnt werden."""
    dpv = make(Kind.FEDERATION, "DPV")
    mosaik = Unit(kind=Kind.ASSOCIATION, name="DPBM Mosaik", parent=dpv, has_rings=True)
    mosaik.save()
    switched, release = threading.Event(), threading.Event()
    results: dict[str, str] = {}

    def switch_off():
        with transaction.atomic():
            fresh = Unit.objects.get(pk=mosaik.pk)
            fresh.has_rings = False
            fresh.save()
            switched.set()
            release.wait(10)

    def create_ring():
        switched.wait(10)
        make(Kind.RING, "Küste", mosaik)

    first = _in_thread(switch_off, results, "aus")
    second = _in_thread(create_ring, results, "ring")
    second.join(1)
    release.set()
    first.join(10)
    second.join(10)

    assert results["aus"] == "gespeichert"
    assert "ist „hat Ringe“ ausgeschaltet" in results["ring"]
    assert not Unit.objects.filter(kind=Kind.RING).exists()


@pytest.mark.django_db(transaction=True)
def test_zwei_gleichnamige_staemme_gleichzeitig():
    """Nur einer entsteht; der zweite bekommt dieselbe Meldung wie sonst auch."""
    dpv = make(Kind.FEDERATION, "DPV")
    boreas = make(Kind.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    first_saved, release = threading.Event(), threading.Event()
    results: dict[str, str] = {}

    def first_troop():
        with transaction.atomic():
            make(Kind.TROOP, "Walhall", boreas)
            first_saved.set()
            release.wait(10)

    def second_troop():
        first_saved.wait(10)
        make(Kind.TROOP, "walhall", boreas)

    first = _in_thread(first_troop, results, "erster")
    second = _in_thread(second_troop, results, "zweiter")
    second.join(1)
    release.set()
    first.join(10)
    second.join(10)

    assert results["erster"] == "gespeichert"
    assert "Im Bund „Pfadfinderbund Boreas“ gibt es schon den Stamm „Walhall“." in results["zweiter"]
    assert Unit.objects.filter(kind=Kind.TROOP).count() == 1
