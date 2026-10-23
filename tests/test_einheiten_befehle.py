"""Tests für die Befehle, mit denen Admins Verband und Bünde anlegen (#88, ORG-01).

In P2 gibt es dafür keine Seite im Tool, nur die Befehle `federation` und `association` auf
dem Server (Klärung vom 22.10.2026, Frage 2). Die Nummern verweisen auf die Szenarien im
Issue #88. Erfolg und Ablehnung melden die Befehle in Alltagssprache.
"""

import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from units.models import Unit

pytestmark = pytest.mark.django_db

Kind = Unit.Kind


def run(*arguments: str) -> str:
    """Ruft einen Befehl auf wie ein Admin auf dem Server und gibt seine Ausgabe zurück."""
    output = io.StringIO()
    call_command(*arguments, stdout=output, stderr=output)
    return output.getvalue()


def refused(*arguments: str) -> str:
    """Ruft einen Befehl auf, der ablehnen muss, und gibt den genannten Grund zurück."""
    with pytest.raises(CommandError) as error:
        run(*arguments)
    return str(error.value)


@pytest.fixture
def dpv():
    run("federation", "create", "DPV")
    return Unit.objects.get(kind=Kind.FEDERATION)


def association(name: str) -> Unit:
    return Unit.objects.get(kind=Kind.ASSOCIATION, name=name)


# Verband


def test_verband_anlegen():
    """S1."""
    assert "Den Verband „DPV“ gibt es jetzt." in run("federation", "create", "DPV")

    assert list(Unit.objects.values_list("kind", "name", "parent")) == [(Kind.FEDERATION, "DPV", None)]


def test_zweiter_verband_wird_abgelehnt(dpv):
    """S1."""
    assert "Es gibt schon einen Verband: „DPV“." in refused("federation", "create", "Noch ein Verband")
    assert Unit.objects.count() == 1


def test_verband_umbenennen(dpv):
    assert "Der Verband heißt jetzt „Deutscher Pfadfinderverband“." in run(
        "federation", "rename", " Deutscher Pfadfinderverband "
    )

    dpv.refresh_from_db()
    assert dpv.name == "Deutscher Pfadfinderverband"


def test_verband_umbenennen_ohne_verband():
    assert "Es gibt noch keinen Verband." in refused("federation", "rename", "DPV")


def test_verband_mit_leerem_namen_wird_abgelehnt():
    """S4."""
    assert "Der Name darf nicht leer sein." in refused("federation", "create", "  ")
    assert not Unit.objects.exists()


# Bünde


def test_bund_anlegen(dpv):
    """S2."""
    assert "Den Bund „Pfadfinderbund Boreas“ gibt es jetzt." in run("association", "create", "Pfadfinderbund Boreas")

    boreas = association("Pfadfinderbund Boreas")
    assert (boreas.parent, boreas.has_rings) == (dpv, False)


def test_bund_mit_ringen_anlegen(dpv):
    output = run("association", "create", "DPBM Mosaik", "--rings")

    assert "Den Bund „DPBM Mosaik“ gibt es jetzt." in output
    assert "„Hat Ringe“ ist eingeschaltet." in output
    assert association("DPBM Mosaik").has_rings is True


@pytest.mark.parametrize("name", ["Pfadfinderbund Boreas", " pfadfinderbund boreas ", "PFADFINDERBUND BOREAS"])
def test_gleicher_bund_wird_abgelehnt(dpv, name):
    """S2, mit dem Wortlaut aus dem Issue."""
    run("association", "create", "Pfadfinderbund Boreas")

    assert refused("association", "create", name) == "Den Bund „Pfadfinderbund Boreas“ gibt es schon."
    assert Unit.objects.filter(kind=Kind.ASSOCIATION).count() == 1


def test_bund_ohne_verband_wird_abgelehnt():
    """S3."""
    assert "Es gibt noch keinen Verband." in refused("association", "create", "Pfadfinderbund Boreas")
    assert not Unit.objects.exists()


@pytest.mark.parametrize("name", ["", "   "])
def test_bund_mit_leerem_namen_wird_abgelehnt(dpv, name):
    """S4."""
    assert "Der Name darf nicht leer sein." in refused("association", "create", name)


def test_bund_mit_zu_langem_namen_wird_abgelehnt(dpv):
    """S16."""
    assert "höchstens 100 Zeichen" in refused("association", "create", "B" * 101)
    assert not Unit.objects.filter(kind=Kind.ASSOCIATION).exists()


def test_bund_umbenennen(dpv):
    """S5."""
    run("association", "create", "Pfadfinderbund Boreas")

    output = run("association", "rename", "pfadfinderbund boreas", "Bund Boreas")

    assert "Der Bund „Pfadfinderbund Boreas“ heißt jetzt „Bund Boreas“." in output
    assert association("Bund Boreas").parent == dpv


def test_bund_nur_in_der_schreibweise_umbenennen(dpv):
    """S5."""
    run("association", "create", "pfadfinderbund boreas")

    run("association", "rename", "pfadfinderbund boreas", "Pfadfinderbund Boreas")

    assert association("Pfadfinderbund Boreas")


def test_bund_auf_vergebenen_namen_umbenennen_wird_abgelehnt(dpv):
    """S6."""
    run("association", "create", "Pfadfinderbund Boreas")
    run("association", "create", "DPBM Mosaik")

    message = refused("association", "rename", "DPBM Mosaik", "Pfadfinderbund boreas")

    assert message == "Den Bund „Pfadfinderbund Boreas“ gibt es schon."
    assert association("DPBM Mosaik")


def test_unbekannten_bund_umbenennen(dpv):
    assert refused("association", "rename", "Gibt es nicht", "Neu") == "Den Bund „Gibt es nicht“ gibt es nicht."


# Schalter „hat Ringe“


def test_ringe_einschalten_und_ausschalten(dpv):
    run("association", "create", "DPBM Mosaik")

    assert "Im Bund „DPBM Mosaik“ ist „hat Ringe“ jetzt eingeschaltet." in run(
        "association", "rings", "dpbm mosaik", "on"
    )
    assert association("DPBM Mosaik").has_rings is True
    assert "Im Bund „DPBM Mosaik“ ist „hat Ringe“ jetzt ausgeschaltet." in run("association", "rings", "DPBM Mosaik", "off")
    assert association("DPBM Mosaik").has_rings is False


def test_ringe_einschalten_obwohl_es_schon_staemme_gibt(dpv):
    """S9."""
    run("association", "create", "Pfadfinderbund Boreas")
    walhall = Unit.objects.create(kind=Kind.TROOP, name="Walhall", parent=association("Pfadfinderbund Boreas"))

    run("association", "rings", "Pfadfinderbund Boreas", "on")

    walhall.refresh_from_db()
    assert walhall.parent == association("Pfadfinderbund Boreas")
    assert association("Pfadfinderbund Boreas").has_rings is True


def test_ringe_ausschalten_mit_ring_nennt_den_grund(dpv):
    """S10."""
    run("association", "create", "DPBM Mosaik", "--rings")
    Unit.objects.create(kind=Kind.RING, name="Küste", parent=association("DPBM Mosaik"))

    message = refused("association", "rings", "DPBM Mosaik", "off")

    assert message == (
        "Der Bund „DPBM Mosaik“ hat noch Ringe. „Hat Ringe“ lässt sich erst ausschalten, "
        "wenn er keinen Ring mehr hat."
    )
    assert association("DPBM Mosaik").has_rings is True


def test_gleichzeitiges_umbenennen_und_umschalten_verlieren_nichts(dpv, monkeypatch):
    """Befund der unabhängigen Prüfung: Der Befehl schreibt nur, was er ändert."""
    from units.management.commands import association as command

    run("association", "create", "Pfadfinderbund Boreas")
    read_before_rename = association("Pfadfinderbund Boreas")
    run("association", "rename", "Pfadfinderbund Boreas", "Bund Boreas")
    monkeypatch.setattr(command, "association", lambda name: read_before_rename)

    run("association", "rings", "Bund Boreas", "on")

    boreas = Unit.objects.get(kind=Kind.ASSOCIATION)
    assert (boreas.name, boreas.has_rings) == ("Bund Boreas", True)


def test_schalter_nur_mit_on_oder_off(dpv):
    run("association", "create", "DPBM Mosaik")

    with pytest.raises(CommandError):
        run("association", "rings", "DPBM Mosaik", "vielleicht")
    assert association("DPBM Mosaik").has_rings is False


# Liste (Antwort D)


def test_liste_zeigt_verband_und_buende_mit_schalter(dpv):
    run("association", "create", "Pfadfinderbund Boreas")
    run("association", "create", "DPBM Mosaik", "--rings")

    assert run("association", "list").splitlines() == [
        "Verband: DPV",
        "Bünde:",
        "  DPBM Mosaik (hat Ringe)",
        "  Pfadfinderbund Boreas (ohne Ringe)",
    ]


def test_liste_ohne_verband():
    assert run("association", "list").splitlines() == ["Es gibt noch keinen Verband."]


def test_liste_ohne_buende(dpv):
    assert run("association", "list").splitlines() == ["Verband: DPV", "Bünde: noch keine"]
