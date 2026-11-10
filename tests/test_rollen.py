"""Tests für die Rollen von Personen in Einheiten, Mitgliedschaft eingeschlossen (#89, ROL-01).

Die Nummern S1 bis S21 verweisen auf die Szenarien im Issue #89 (Kommentar „Fragen bei der
Umsetzung, 23.10.2026“). Die Regeln gelten beim Speichern und Löschen jeder Rolle, egal auf
welchem Weg; deshalb prüfen diese Tests direkt am Datenmodell. Den Befehl für Admins prüft
tests/test_rollen_befehle.py. Alle Namen sind erfunden.
"""

import io
import threading
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.urls import get_resolver

from roles.models import SERVER_COMMAND, Role
from tests.keycloak_fake import login
from tests.test_rundumtest import ALL
from units.models import Unit

R = Role.Kind
U = Unit.Kind
LEADS_IN_UNITS = (R.GROUP_LEAD, R.TROOP_LEAD, R.RING_LEAD, R.ASSOCIATION_LEAD)
# Wer die Änderung macht, spielt für diese Regeln keine Rolle; das Protokoll prüft
# tests/test_rollen_protokoll.py (#91).
BY = SERVER_COMMAND


def person(username: str, first_name: str, last_name: str):
    """Ein Konto, wie es nach dem ersten Login im Tool steht."""
    return get_user_model().objects.create(username=username, first_name=first_name, last_name=last_name)


def unit(kind: str, name: str, parent: Unit | None = None, **extra) -> Unit:
    created = Unit(kind=kind, name=name, parent=parent, **extra)
    created.save(by=BY)
    return created


def give(user, kind: str, where: Unit | None = None) -> Role:
    """Gibt eine Rolle auf demselben Weg, den später auch die Seiten nehmen."""
    role = Role(user=user, kind=kind, unit=where)
    role.save(by=BY)
    return role


def refused(action) -> ValidationError:
    """Führt eine Änderung aus, die abgelehnt werden muss, und gibt die Ablehnung zurück."""
    with pytest.raises(ValidationError) as error:
        action()
    return error.value


def message(error: ValidationError) -> str:
    return " ".join(error.messages)


def roles_of(user) -> set[tuple[str, str | None]]:
    return {(role.kind, role.unit.name if role.unit else None) for role in Role.objects.filter(user=user)}


def membership(user) -> Role:
    return Role.objects.get(user=user, kind=R.MEMBER)


def move(user, to: Unit) -> None:
    """Wechselt die Mitgliedschaft in eine andere Einheit."""
    member = membership(user)
    member.unit = to
    member.save(by=BY)


def build_org() -> SimpleNamespace:
    """Verband, zwei Bünde (einer mit Ringen), Stämme und Gruppen, dazu Erika und Max."""
    o = SimpleNamespace()
    o.dpv = unit(U.FEDERATION, "DPV")
    o.boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", o.dpv)
    o.walhall = unit(U.TROOP, "Walhall", o.boreas)
    o.falken = unit(U.GROUP, "Sippe Falken", o.walhall)
    o.woelfe = unit(U.GROUP, "Meute Wölfe", o.walhall)
    o.zugvoegel = unit(U.TROOP, "Zugvögel", o.boreas)
    o.adler = unit(U.GROUP, "Sippe Adler", o.zugvoegel)
    o.mosaik = unit(U.ASSOCIATION, "DPBM Mosaik", o.dpv, has_rings=True)
    o.kueste = unit(U.RING, "Küste", o.mosaik)
    o.leuchtturm = unit(U.TROOP, "Leuchtturm", o.kueste)
    o.moewen = unit(U.GROUP, "Meute Möwen", o.leuchtturm)
    o.nord = unit(U.RING, "Nord", o.mosaik)
    o.sturmvogel = unit(U.TROOP, "Sturmvogel", o.nord)
    o.erika = person("erika.testfrau", "Erika", "Testfrau")
    o.max = person("max.testmann", "Max", "Testmann")
    return o


@pytest.fixture
def org(db) -> SimpleNamespace:
    return build_org()


# Rollen


def test_eine_person_hat_mehrere_rollen_in_verschiedenen_einheiten(org):
    """S1, das Beispiel aus dem Issue."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)
    give(org.erika, R.EVENT_TEAM, org.dpv)

    assert roles_of(org.erika) == {
        (R.MEMBER, "Sippe Falken"),
        (R.GROUP_LEAD, "Meute Wölfe"),
        (R.TROOP_LEAD, "Walhall"),
        (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"),
        (R.EVENT_TEAM, "DPV"),
    }


@pytest.mark.parametrize(
    ("kind", "where"),
    [
        (R.MEMBER, "falken"),
        (R.MEMBER, "walhall"),
        (R.MEMBER, "kueste"),
        (R.MEMBER, "boreas"),
        (R.GROUP_LEAD, "falken"),
        (R.TROOP_LEAD, "walhall"),
        (R.RING_LEAD, "kueste"),
        (R.ASSOCIATION_LEAD, "boreas"),
        (R.FEDERATION_LEAD, "dpv"),
        (R.EVENT_TEAM, "dpv"),
    ],
)
def test_jede_rolle_passt_zu_ihrer_ebene(org, kind, where):
    """Jede Rolle außer Admin hängt an genau einer Einheit der passenden Ebene."""
    give(org.max, kind, getattr(org, where))

    assert (kind, getattr(org, where).name) in roles_of(org.max)


@pytest.mark.parametrize(
    ("kind", "where", "reason"),
    [
        (R.GROUP_LEAD, "walhall", "Eine Gruppenleitung gehört zu einer Gruppe."),
        (R.TROOP_LEAD, "falken", "Eine Stammesleitung gehört zu einem Stamm."),
        (R.RING_LEAD, "boreas", "Eine Ringleitung gehört zu einem Ring."),
        (R.ASSOCIATION_LEAD, "kueste", "Eine Bundesleitung gehört zu einem Bund."),
        (R.FEDERATION_LEAD, "boreas", "Die Verbandsleitung gehört zum Verband."),
        (R.EVENT_TEAM, "walhall", "Das DPV-Veranstaltungsteam gehört zum Verband."),
        (R.MEMBER, "dpv", "Mitglied ist man in einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie im Verband."),
        (R.ADMIN, "dpv", "Admin ist eine Rolle ohne Organisation."),
        (R.GROUP_LEAD, None, "Eine Gruppenleitung gehört zu einer Gruppe."),
        (R.MEMBER, None, "Mitglied ist man in einer Gruppe, einem Stamm, einem Ring oder einem Bund, nie im Verband."),
    ],
)
def test_rolle_an_falscher_ebene_wird_abgelehnt(org, kind, where, reason):
    """S2."""
    error = refused(lambda: give(org.max, kind, getattr(org, where) if where else None))

    assert reason in message(error)
    assert not Role.objects.exists()


def test_admin_hat_keine_einheit(org):
    give(org.max, R.ADMIN)

    assert roles_of(org.max) == {(R.ADMIN, None)}


def test_dieselbe_rolle_in_derselben_einheit_nur_einmal(org):
    """S3."""
    give(org.erika, R.TROOP_LEAD, org.walhall)

    error = refused(lambda: give(org.erika, R.TROOP_LEAD, org.walhall))

    assert "Erika Testfrau ist schon Stammesleitung in „Walhall“." in message(error)
    assert Role.objects.filter(kind=R.TROOP_LEAD).count() == 1


def test_gruppenleitung_in_zwei_gruppen(org):
    """S3: dieselbe Rolle in verschiedenen Einheiten geht."""
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)

    assert Role.objects.filter(user=org.erika, kind=R.GROUP_LEAD).count() == 2


def test_hoechstens_ein_admin_eintrag_je_person(org):
    give(org.max, R.ADMIN)

    assert "Max Testmann ist schon Admin." in message(refused(lambda: give(org.max, R.ADMIN)))


def test_hoechstens_eine_mitgliedschaft(org):
    """S4."""
    give(org.erika, R.MEMBER, org.falken)

    error = refused(lambda: give(org.erika, R.MEMBER, org.woelfe))

    assert (
        "Erika Testfrau ist schon Mitglied in „Sippe Falken“ (Walhall). "
        "Mitglied ist man in höchstens einer Organisation." in message(error)
    )
    assert error.error_list[0].code == "second_membership"
    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken")}


def test_ohne_namen_nennt_die_meldung_den_benutzernamen(org):
    ohne_name = person("ohne.name", "", "")
    give(ohne_name, R.MEMBER, org.walhall)

    assert "ohne.name ist schon Mitglied in „Walhall“." in message(refused(lambda: give(ohne_name, R.MEMBER, org.boreas)))


def test_art_und_person_einer_rolle_bleiben(org):
    """Eine Rolle wird entfernt und neu gegeben, nicht umgewidmet; so bleibt jede Änderung nachvollziehbar (#91)."""
    lead = give(org.erika, R.GROUP_LEAD, org.falken)
    lead.kind = R.TROOP_LEAD
    lead.unit = org.walhall
    assert "Bei einer Rolle lässt sich nur die Organisation einer Mitgliedschaft ändern." in message(refused(lambda: lead.save(by=BY)))

    lead = Role.objects.get(pk=lead.pk)
    lead.user = org.max
    assert "Bei einer Rolle lässt sich nur die Organisation einer Mitgliedschaft ändern." in message(refused(lambda: lead.save(by=BY)))

    lead = Role.objects.get(pk=lead.pk)
    lead.unit = org.woelfe
    assert "Bei einer Rolle lässt sich nur die Organisation einer Mitgliedschaft ändern." in message(refused(lambda: lead.save(by=BY)))
    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Sippe Falken")}


def test_datenbank_verhindert_zweite_mitgliedschaft_auch_am_tool_vorbei(org):
    """Die Regel gilt in der Datenbank, nicht nur beim Speichern über das Tool."""
    give(org.erika, R.MEMBER, org.falken)

    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.bulk_create([Role(user=org.erika, kind=R.MEMBER, unit=org.woelfe)])


def test_datenbank_verhindert_doppelte_rolle_und_admin_mit_einheit(org):
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.max, R.ADMIN)

    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.bulk_create([Role(user=org.erika, kind=R.TROOP_LEAD, unit=org.walhall)])
    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.bulk_create([Role(user=org.max, kind=R.ADMIN)])
    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.bulk_create([Role(user=org.erika, kind=R.ADMIN, unit=org.dpv)])
    with pytest.raises(IntegrityError), transaction.atomic():
        Role.objects.bulk_create([Role(user=org.erika, kind=R.GROUP_LEAD, unit=None)])


# Pfad


def test_leitung_ausserhalb_des_pfads_wird_abgelehnt(org):
    """S5."""
    give(org.erika, R.MEMBER, org.walhall)

    error = refused(lambda: give(org.erika, R.GROUP_LEAD, org.adler))

    assert (
        "Erika Testfrau ist Mitglied in „Walhall“ und kann deshalb keine Leitung in „Sippe Adler“ (Zugvögel) sein."
        in message(error)
    )
    # Die Seiten aus #93 und #94 erkennen den Fall am Code und nennen dort, wo nötig, keine Einheit.
    assert error.error_list[0].code == "outside_path"
    assert roles_of(org.erika) == {(R.MEMBER, "Walhall")}


def test_pfad_eines_gruppenmitglieds(org):
    """S6: eigener Stamm samt Nachbargruppen und alles darüber."""
    give(org.erika, R.MEMBER, org.falken)

    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)

    assert "keine Leitung in „DPBM Mosaik“" in message(refused(lambda: give(org.erika, R.ASSOCIATION_LEAD, org.mosaik)))
    assert "keine Leitung in „Zugvögel“" in message(refused(lambda: give(org.erika, R.TROOP_LEAD, org.zugvoegel)))
    assert "keine Leitung in „Küste“" in message(refused(lambda: give(org.erika, R.RING_LEAD, org.kueste)))


def test_pfad_eines_stammesmitglieds_im_ring(org):
    """S6 mit Ring: Stamm, Ring und Bund darüber; der andere Ring nicht."""
    give(org.erika, R.MEMBER, org.leuchtturm)

    give(org.erika, R.GROUP_LEAD, org.moewen)
    give(org.erika, R.RING_LEAD, org.kueste)
    give(org.erika, R.ASSOCIATION_LEAD, org.mosaik)

    assert "keine Leitung in „Nord“" in message(refused(lambda: give(org.erika, R.RING_LEAD, org.nord)))


def test_pfad_eines_ringmitglieds(org):
    """S7: alles darunter und darüber; ein Stamm in einem anderen Ring nicht."""
    give(org.max, R.MEMBER, org.kueste)

    give(org.max, R.TROOP_LEAD, org.leuchtturm)
    give(org.max, R.GROUP_LEAD, org.moewen)
    give(org.max, R.RING_LEAD, org.kueste)
    give(org.max, R.ASSOCIATION_LEAD, org.mosaik)

    assert "keine Leitung in „Sturmvogel“" in message(refused(lambda: give(org.max, R.TROOP_LEAD, org.sturmvogel)))


def test_pfad_eines_bundesmitglieds(org):
    """S7: wer direkt Mitglied eines Bundes ist, kann alles darin leiten."""
    give(org.max, R.MEMBER, org.boreas)

    give(org.max, R.GROUP_LEAD, org.adler)
    give(org.max, R.TROOP_LEAD, org.walhall)
    give(org.max, R.ASSOCIATION_LEAD, org.boreas)

    assert "keine Leitung in „Leuchtturm“" in message(refused(lambda: give(org.max, R.TROOP_LEAD, org.leuchtturm)))


# Automatische Mitgliedschaft


def test_leitung_ohne_mitgliedschaft_wird_mitglied_der_geleiteten_einheit(org):
    """S8; die Mitgliedschaft bleibt, wenn die Leitung endet."""
    lead = give(org.max, R.GROUP_LEAD, org.falken)

    assert roles_of(org.max) == {(R.GROUP_LEAD, "Sippe Falken"), (R.MEMBER, "Sippe Falken")}

    lead.delete(by=BY)

    assert roles_of(org.max) == {(R.MEMBER, "Sippe Falken")}


def test_bundesleitung_ohne_mitgliedschaft_wird_mitglied_des_bundes(org):
    """S9."""
    give(org.max, R.ASSOCIATION_LEAD, org.boreas)

    assert roles_of(org.max) == {(R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"), (R.MEMBER, "Pfadfinderbund Boreas")}


def test_leitung_mit_mitgliedschaft_legt_keine_zweite_an(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)

    assert Role.objects.filter(user=org.erika, kind=R.MEMBER).count() == 1


@pytest.mark.parametrize("kind", [R.FEDERATION_LEAD, R.EVENT_TEAM])
def test_verbandsrollen_legen_keine_mitgliedschaft_an(org, kind):
    """S10: am Verband ist niemand Mitglied."""
    give(org.max, kind, org.dpv)

    assert roles_of(org.max) == {(kind, "DPV")}


def test_admin_legt_keine_mitgliedschaft_an(org):
    give(org.max, R.ADMIN)

    assert not Role.objects.filter(kind=R.MEMBER).exists()


def test_verbandsleitung_mit_mitgliedschaft_in_einem_stamm(org):
    """S10b: die Pfad-Regel gilt für Verbandsrollen nicht."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)
    give(org.erika, R.EVENT_TEAM, org.dpv)

    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken"), (R.FEDERATION_LEAD, "DPV"), (R.EVENT_TEAM, "DPV")}


def test_verbandsleitung_wird_bundesleitung_und_dadurch_mitglied(org):
    """S10c: ab der Mitgliedschaft gilt der Pfad."""
    give(org.max, R.FEDERATION_LEAD, org.dpv)
    give(org.max, R.ASSOCIATION_LEAD, org.mosaik)

    assert membership(org.max).unit == org.mosaik
    assert "keine Leitung in „Pfadfinderbund Boreas“" in message(
        refused(lambda: give(org.max, R.ASSOCIATION_LEAD, org.boreas))
    )


def test_verbandsleitung_wechselt_die_mitgliedschaft_in_einen_anderen_bund(org):
    """S10d."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)

    move(org.erika, org.leuchtturm)

    assert roles_of(org.erika) == {(R.MEMBER, "Leuchtturm"), (R.FEDERATION_LEAD, "DPV")}


# Wechsel und Austritt


def test_wechsel_mit_leitungsrolle_ausserhalb_des_neuen_pfads_wird_abgelehnt(org):
    """S11; nach dem Entfernen der Rolle geht der Wechsel."""
    give(org.erika, R.MEMBER, org.falken)
    lead = give(org.erika, R.GROUP_LEAD, org.woelfe)

    error = refused(lambda: move(org.erika, org.adler))

    assert (
        "Erika Testfrau ist noch Gruppenleitung in „Meute Wölfe“ (Walhall). Diese Rolle muss zuerst entfernt werden."
        in message(error)
    )
    assert error.error_list[0].code == "remove_roles_first"
    assert membership(org.erika).unit == org.falken

    lead.delete(by=BY)
    move(org.erika, org.adler)

    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Adler")}


def test_wechsel_nennt_alle_rollen_die_zuerst_weg_muessen(org):
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)

    error = refused(lambda: move(org.erika, org.leuchtturm))

    assert (
        "Erika Testfrau ist noch Gruppenleitung in „Meute Wölfe“ (Walhall), Stammesleitung in „Walhall“ "
        "und Bundesleitung in „Pfadfinderbund Boreas“. Diese Rollen müssen zuerst entfernt werden."
    ) in message(error)


def test_wechsel_auf_dem_pfad_geht_trotz_leitungsrollen(org):
    """S12: innerhalb des Stammes und nach oben."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)

    move(org.erika, org.woelfe)
    move(org.erika, org.walhall)
    move(org.erika, org.boreas)

    assert membership(org.erika).unit == org.boreas


def test_wechsel_nach_unten_geht_nur_wenn_die_leitungen_darueber_auf_dem_pfad_bleiben(org):
    give(org.max, R.MEMBER, org.boreas)
    give(org.max, R.TROOP_LEAD, org.zugvoegel)

    assert "noch Stammesleitung in „Zugvögel“" in message(refused(lambda: move(org.max, org.walhall)))
    move(org.max, org.adler)


def test_austritt_beendet_alle_leitungsrollen_in_einheiten(org):
    """S13, geändert mit #65 (ROL-01, EP-06, PK-21): Wer ganz austritt, verliert alle Leitungsrollen in Einheiten.

    Vor #65 lehnte das Tool den Austritt ab, solange Leitungsrollen bestanden (Frage F1 vom 23.10.2026).
    """
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)

    membership(org.erika).delete(by=BY)

    assert not Role.objects.filter(user=org.erika).exists()


def test_austritt_eine_ebene_hoch_beendet_die_leitungen_in_der_verlassenen_einheit(org):
    """#65, P9: Fiete tritt aus den Falken aus, gehört danach direkt zum Stamm und ist keine Gruppenleitung mehr."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.GROUP_LEAD, org.woelfe)
    give(org.erika, R.TROOP_LEAD, org.walhall)

    membership(org.erika).leave(org.falken, by=BY)

    # Die Wölfe und der Stamm liegen danach weiter auf dem Pfad (ROL-01); nur die Falken enden.
    assert roles_of(org.erika) == {(R.MEMBER, "Walhall"), (R.GROUP_LEAD, "Meute Wölfe"), (R.TROOP_LEAD, "Walhall")}


def test_austritt_aus_einer_einheit_darueber_beendet_alles_darunter(org):
    """#65, Frage 10: Die Ebene kommt aus der eigenen Kette; aus dem Stamm auszutreten beendet auch die Gruppenleitung."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.ASSOCIATION_LEAD, org.boreas)

    membership(org.erika).leave(org.walhall, by=BY)

    assert roles_of(org.erika) == {(R.MEMBER, "Pfadfinderbund Boreas"), (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas")}


def test_austritt_aus_dem_bund_heisst_keine_zuordnung(org):
    """#65, P10: aus dem Bund auszutreten beendet die Mitgliedschaft und alle Leitungen in Einheiten."""
    give(org.erika, R.MEMBER, org.walhall)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)

    membership(org.erika).leave(org.boreas, by=BY)

    assert roles_of(org.erika) == {(R.FEDERATION_LEAD, "DPV")}


def test_ganz_austragen_aus_einer_gruppe(org):
    """#65, Frage 17: „gehört danach keiner Organisation mehr an“ geht auch aus einer Gruppe."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)

    membership(org.erika).leave(org.falken, by=BY, entirely=True)

    assert roles_of(org.erika) == set()


def test_austritt_endet_auch_leitungen_die_danach_nicht_mehr_auf_dem_pfad_liegen(org):
    """#65 (ROL-01): Ein direktes Ringmitglied leitet einen Stamm im Ring; tritt es aus dem Ring aus, endet auch das."""
    give(org.erika, R.MEMBER, org.kueste)
    give(org.erika, R.TROOP_LEAD, org.leuchtturm)
    give(org.erika, R.ASSOCIATION_LEAD, org.mosaik)

    assert membership(org.erika).ending_leads(org.kueste) == [Role.objects.get(user=org.erika, kind=R.TROOP_LEAD)]
    membership(org.erika).leave(org.kueste, by=BY)

    assert roles_of(org.erika) == {(R.MEMBER, "DPBM Mosaik"), (R.ASSOCIATION_LEAD, "DPBM Mosaik")}


def test_vorschau_nennt_die_rollen_die_enden_und_aendert_nichts(org):
    """#65, Fragen 10 und 11: Die Vorschau nennt die Rollen; ausgeführt wird erst danach."""
    give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.GROUP_LEAD, org.falken)
    give(org.erika, R.TROOP_LEAD, org.walhall)
    member = membership(org.erika)

    assert [(r.kind, r.unit.name) for r in member.ending_leads(org.falken)] == [(R.GROUP_LEAD, "Sippe Falken")]
    assert [(r.kind, r.unit.name) for r in member.ending_leads(org.walhall)] == [
        (R.GROUP_LEAD, "Sippe Falken"), (R.TROOP_LEAD, "Walhall")]
    assert [(r.kind, r.unit.name) for r in member.ending_leads(org.falken, entirely=True)] == [
        (R.GROUP_LEAD, "Sippe Falken"), (R.TROOP_LEAD, "Walhall")]
    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Sippe Falken"), (R.TROOP_LEAD, "Walhall")}


@pytest.mark.parametrize("left", ["woelfe", "zugvoegel", "mosaik", "dpv"])
def test_austritt_nur_aus_der_eigenen_kette(org, left):
    """#65, PG6: Eine Einheit außerhalb der eigenen Kette und der Verband werden abgelehnt; nichts ändert sich."""
    give(org.erika, R.MEMBER, org.falken)

    refused(lambda: membership(org.erika).leave(getattr(org, left), by=BY))

    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken")}


def test_austritt_nur_fuer_eine_mitgliedschaft(org):
    lead = give(org.erika, R.GROUP_LEAD, org.falken)

    refused(lambda: lead.leave(org.falken, by=BY))

    assert roles_of(org.erika) == {(R.MEMBER, "Sippe Falken"), (R.GROUP_LEAD, "Sippe Falken")}


def test_austritt_einer_schon_beendeten_mitgliedschaft_aendert_nichts(org):
    """#65, PG3: Wer schon draußen ist, kann nicht noch einmal austreten; die zweite Änderung sieht „nicht gefunden“."""
    member = give(org.erika, R.MEMBER, org.falken)
    stale = Role.objects.get(pk=member.pk)
    member.leave(org.falken, by=BY)

    assert stale.leave(org.falken, by=BY) is False
    assert roles_of(org.erika) == {(R.MEMBER, "Walhall")}


def test_verbandsrollen_stehen_dem_austritt_nicht_im_weg(org):
    """S13."""
    member = give(org.erika, R.MEMBER, org.falken)
    give(org.erika, R.FEDERATION_LEAD, org.dpv)
    give(org.erika, R.EVENT_TEAM, org.dpv)
    give(org.erika, R.ADMIN)

    member.delete(by=BY)

    assert roles_of(org.erika) == {(R.FEDERATION_LEAD, "DPV"), (R.EVENT_TEAM, "DPV"), (R.ADMIN, None)}


# Admin


def test_admin_bekommt_keine_rechte_einer_leitung(org):
    """S15: kein Zugriff aus der Rolle Admin selbst und keiner über Djangos eingebaute Rechte."""
    give(org.max, R.ADMIN)
    org.max.refresh_from_db()

    assert not org.max.is_superuser
    assert not org.max.is_staff
    assert not org.max.has_perm("units.change_unit")
    assert not org.max.has_perm("roles.add_role")
    assert roles_of(org.max) == {(R.ADMIN, None)}


def test_admin_mit_leitungsrolle_behaelt_sie(org):
    """S18."""
    give(org.erika, R.TROOP_LEAD, org.walhall)
    admin = give(org.erika, R.ADMIN)

    admin.delete(by=BY)

    assert roles_of(org.erika) == {(R.TROOP_LEAD, "Walhall"), (R.MEMBER, "Walhall")}


# Woher Rechte nicht kommen


@pytest.mark.django_db
def test_login_legt_keine_rolle_an_auch_nicht_beim_ersten_konto(client, keycloak):
    """S19: auch nicht, wenn Keycloak Rollen oder Gruppen mitschickt."""
    keycloak.person["realm_access"] = {"roles": ["admin", "Bundesleitung"]}
    keycloak.person["groups"] = ["/admin", "/Boreas/Walhall"]

    login(client)

    user = get_user_model().objects.get()
    assert not Role.objects.exists()
    assert not user.is_superuser
    assert not user.is_staff


def test_wer_eine_einheit_anlegt_bekommt_keine_rolle(org):
    """S20: Rechte entstehen nie daraus, wer etwas angelegt hat."""
    call_command("association", "create", "Bund Neu", stdout=io.StringIO())

    assert not Role.objects.exists()


def test_die_app_rollen_hat_keine_eigenen_adressen():
    """S20: Die App „roles“ hat keine Adressen. Rollen vergibt seit #190 die Seite „Organisation“ über die zentrale Rechteprüfung (`Rights.appoint()`, Tests in tests/test_benennen.py)."""
    views = {f"{entry.callback.__module__}.{entry.callback.__name__}" for _pattern, entry in ALL}

    assert ALL, "Der Rundumtest findet keine Adressen"
    assert not [view for view in views if view.startswith("roles")]
    assert "roles" not in {str(pattern.pattern) for pattern in get_resolver().url_patterns}


def test_einheit_und_konto_mit_rollen_lassen_sich_nicht_loeschen(org):
    """S21."""
    give(org.erika, R.GROUP_LEAD, org.falken)

    with pytest.raises(ProtectedError), transaction.atomic():
        org.falken.delete()
    with pytest.raises(ProtectedError), transaction.atomic():
        org.erika.delete()

    assert roles_of(org.erika) == {(R.GROUP_LEAD, "Sippe Falken"), (R.MEMBER, "Sippe Falken")}


# Gleichzeitige Änderungen (S14)


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


def _one_after_the_other(first_work, second_work) -> dict[str, str]:
    """Die erste Änderung hält ihre Transaktion offen, während die zweite schon startet."""
    first_done, release = threading.Event(), threading.Event()
    results: dict[str, str] = {}

    def first():
        with transaction.atomic():
            first_work()
            first_done.set()
            release.wait(10)

    def second():
        first_done.wait(10)
        second_work()

    one = _in_thread(first, results, "erste")
    two = _in_thread(second, results, "zweite")
    two.join(1)
    release.set()
    one.join(10)
    two.join(10)
    return results


def _all_leads_on_path(user) -> bool:
    """Prüft von außen, ob jede Leitungsrolle in einer Einheit auf dem Pfad der Mitgliedschaft liegt."""
    member = Role.objects.filter(user=user, kind=R.MEMBER).first()
    leads = Role.objects.filter(user=user, kind__in=LEADS_IN_UNITS)
    if member is None:
        return not leads.exists()
    anchor = member.unit.parent if member.unit.kind == U.GROUP else member.unit

    def chain(start):
        while start is not None:
            yield start.pk
            start = start.parent

    return all(anchor.pk in chain(lead.unit) or lead.unit.pk in chain(anchor) for lead in leads)


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_wechsel_und_neue_leitung_im_alten_stamm():
    """S14: Der Wechsel kommt zuerst; die gleichzeitige Leitung im alten Stamm muss abgelehnt werden."""
    o = build_org()
    give(o.erika, R.MEMBER, o.falken)

    results = _one_after_the_other(lambda: move(o.erika, o.adler), lambda: give(o.erika, R.GROUP_LEAD, o.woelfe))

    assert results["erste"] == "gespeichert"
    assert "keine Leitung in „Meute Wölfe“" in results["zweite"]
    assert _all_leads_on_path(o.erika)


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_neue_leitung_und_wechsel_weg():
    """S14: Die Leitung kommt zuerst; der gleichzeitige Wechsel muss abgelehnt werden."""
    o = build_org()
    give(o.erika, R.MEMBER, o.falken)

    results = _one_after_the_other(lambda: give(o.erika, R.GROUP_LEAD, o.woelfe), lambda: move(o.erika, o.adler))

    assert results["erste"] == "gespeichert"
    assert "noch Gruppenleitung in „Meute Wölfe“" in results["zweite"]
    assert _all_leads_on_path(o.erika)


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_zwei_mitgliedschaften():
    """S14: nur eine entsteht; die zweite bekommt dieselbe Meldung wie sonst."""
    o = build_org()

    results = _one_after_the_other(lambda: give(o.max, R.MEMBER, o.falken), lambda: give(o.max, R.MEMBER, o.adler))

    assert results["erste"] == "gespeichert"
    assert "Mitglied ist man in höchstens einer Organisation." in results["zweite"]
    assert roles_of(o.max) == {(R.MEMBER, "Sippe Falken")}


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_zwei_leitungen_ohne_mitgliedschaft_in_verschiedenen_staemmen():
    """S14: Die erste legt die Mitgliedschaft an; die zweite liegt danach nicht mehr auf dem Pfad."""
    o = build_org()

    results = _one_after_the_other(
        lambda: give(o.max, R.GROUP_LEAD, o.falken), lambda: give(o.max, R.GROUP_LEAD, o.adler)
    )

    assert results["erste"] == "gespeichert"
    assert "keine Leitung in „Sippe Adler“" in results["zweite"]
    assert roles_of(o.max) == {(R.GROUP_LEAD, "Sippe Falken"), (R.MEMBER, "Sippe Falken")}


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_leitung_und_austritt():
    """S14, geändert mit #65: Die Leitung kommt zuerst; der gleichzeitige Austritt beendet sie mit."""
    o = build_org()
    give(o.erika, R.MEMBER, o.falken)

    results = _one_after_the_other(
        lambda: give(o.erika, R.TROOP_LEAD, o.walhall), lambda: membership(o.erika).delete(by=BY)
    )

    assert results == {"erste": "gespeichert", "zweite": "gespeichert"}
    assert roles_of(o.erika) == set()
    assert _all_leads_on_path(o.erika)


@pytest.mark.django_db(transaction=True)
def test_gleichzeitig_austritt_und_neue_leitung_im_verlassenen_stamm():
    """#65, S14: Der Austritt aus dem Bund kommt zuerst; die gleichzeitige Leitung braucht eine Mitgliedschaft und legt sie neu an."""
    o = build_org()
    give(o.erika, R.MEMBER, o.falken)

    results = _one_after_the_other(
        lambda: membership(o.erika).leave(o.boreas, by=BY), lambda: give(o.erika, R.GROUP_LEAD, o.adler)
    )

    assert results == {"erste": "gespeichert", "zweite": "gespeichert"}
    assert roles_of(o.erika) == {(R.MEMBER, "Sippe Adler"), (R.GROUP_LEAD, "Sippe Adler")}
    assert _all_leads_on_path(o.erika)
