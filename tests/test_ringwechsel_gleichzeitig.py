"""Tests für Handgriffe der Leitungen im selben Augenblick wie ein Ringwechsel (#295).

Die Kennungen RG1 bis RG9 und RU1 bis RU4 verweisen auf den Kommentar „Szenarien (12.11.2026)“ in #295
(https://github.com/sebivtt/dpv-participant-management/issues/295#issuecomment-6830312761). Personen wie in
den Szenarien zu #95 (`tests/test_einheiten_anlegen.py`): Mosaik (mit Ringen) mit Mona (Bundesleitung),
Kai (Ringleitung Küste) und Nele (Ringleitung Nord). Dazu Stamm Düne in Ring Küste ohne Stammesleitung, Kai
springt dort ein (EH-18); darin die Gruppe Sippe Möwen mit Gerd als Gruppenleitung, Dana als Mitglied von
Düne und die verwaltete Person Emil in Düne. Pia hat ein Konto und ist noch nirgends Mitglied. Namen sind
erfunden.

Gemeinsame Regel für RG1 bis RG7: Mona verschiebt Düne von Küste nach Nord, und im selben Augenblick handelt
Kai in Düne. Ist Monas Wechsel zuerst gespeichert, sieht Kai „nicht gefunden“, nichts von seiner Handlung ist
gespeichert, und im Protokoll steht nur der Wechsel. Ist Kais Handlung zuerst gespeichert, gilt sie, und
danach liegt Düne in Nord. Je Szenario ein Test mit beiden Reihenfolgen. RU1 und RU2 prüfen die bestehenden
Tests der sieben Handgriffe und von #95 (O7, OG9); RU3 betrifft Handgriffe, die hier nicht geändert werden;
RU4 prüft jeder Test der Reihenfolge „Wechsel zuerst“ mit dem Protokoll.
"""

import threading
from datetime import date
from types import SimpleNamespace

import pytest
from django.db import connection, transaction
from django.http import Http404
from django.utils import timezone

from access.rights import Rights
from persons.models import ManagedPerson
from roles.models import Role, RoleChange
from tests import test_rechtepruefung
from tests.test_rechtepruefung import lead, member
from tests.test_rollen import person
from tests.test_rollen import unit as new_unit
from units.models import Kind as U
from units.models import Unit, UnitChange

R = Role.Kind
NOT_FOUND = "nicht gefunden"
EMIL = {"first_name": "Emil", "last_name": "Probe", "birth_date": date(2014, 3, 1), "scout_name": ""}

base_org = test_rechtepruefung.org


@pytest.fixture
def org(transactional_db, base_org) -> SimpleNamespace:
    """Die Personen aus tests/test_rechtepruefung.py, dazu Düne mit Sippe Möwen, Gerd, Dana, Emil und Pia."""
    org = base_org
    org.duene = new_unit(U.TROOP, "Düne", org.kueste)
    org.sippe_moewen = new_unit(U.GROUP, "Sippe Möwen", org.duene)
    org.gerd = lead("gerd.gruppe", R.GROUP_LEAD, org.sippe_moewen)
    org.dana = member("dana.duene", org.duene)
    org.pia = person("pia.probe", "Pia", "Probe")
    # Pia war schon einmal angemeldet; sonst fände Kai sie nicht (BER-01).
    org.pia.last_login = timezone.now()
    org.pia.save()
    org.emil = ManagedPerson.objects.create(unit=org.duene, **EMIL)
    return org


def _at_once(first_work, second_work) -> tuple:
    """Die erste Anfrage hält ihre Transaktion offen, während die zweite schon startet; gibt beide Ergebnisse zurück.

    Wie `_one_after_the_other()` in tests/test_benennen.py, aber in fester Reihenfolge der Anfragen statt in der
    Reihenfolge, in der sie fertig werden: Wartet die zweite nicht auf die erste, ist sie sonst zuerst fertig.
    „Nicht gefunden“ steht als Text da, wie die Seite es als 404 zeigt.
    """
    first_done, release = threading.Event(), threading.Event()
    results: dict = {}

    def run(name, work):
        try:
            results[name] = work()
        except Http404:
            results[name] = NOT_FOUND
        finally:
            connection.close()

    def first():
        with transaction.atomic():
            result = first_work()
            first_done.set()
            release.wait(10)
        return result

    def second():
        first_done.wait(10)
        return second_work()

    one = threading.Thread(target=run, args=("first", first))
    two = threading.Thread(target=run, args=("second", second))
    one.start()
    two.start()
    two.join(1)
    release.set()
    one.join(10)
    two.join(10)
    return results.get("first"), results.get("second")


def _mona_moves_duene(org):
    return lambda: Rights(org.mosaik_leitung).change_ring(org.duene, org.nord.key)


def _mark() -> tuple[int, int]:
    """Die letzten Einträge beider Protokolle: Rollenänderungen und Strukturänderungen."""
    last_role = RoleChange.objects.order_by("pk").last()
    last_unit = UnitChange.objects.order_by("pk").last()
    return (last_role.pk if last_role else 0, last_unit.pk if last_unit else 0)


def _duene_in_nord(org) -> bool:
    return Unit.objects.get(pk=org.duene.pk).parent_id == org.nord.pk


def _assert_exactly_one(org, kai_action, kai_done, moving_first: bool) -> None:
    """Die gemeinsame Regel für RG1 bis RG7; `kai_done()` sagt, ob Kais Handlung gespeichert ist."""
    start = _mark()
    if moving_first:
        move_result, kai_result = _at_once(_mona_moves_duene(org), kai_action)
    else:
        kai_result, move_result = _at_once(kai_action, _mona_moves_duene(org))

    assert move_result[0] is True
    assert _duene_in_nord(org)
    if moving_first:
        assert kai_result == NOT_FOUND
        assert not kai_done()
        # RU4: Im Protokoll steht nur der Wechsel.
        assert not RoleChange.objects.filter(pk__gt=start[0]).exists()
        assert list(UnitChange.objects.filter(pk__gt=start[1]).values_list("actor_id", "unit_name", "action")) == [
            (org.mosaik_leitung.pk, "Düne", UnitChange.Action.RING_CHANGED)]
    else:
        assert kai_result != NOT_FOUND
        assert kai_done()
        assert RoleChange.objects.filter(pk__gt=start[0], actor_id=org.kueste_leitung.pk).exists()


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg1_kai_benennt_dana_zur_stammesleitung_waehrend_mona_duene_verschiebt(org, moving_first):
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).appoint(org.duene, org.dana.key),
        lambda: Role.objects.filter(user=org.dana, kind=R.TROOP_LEAD, unit=org.duene).exists(),
        moving_first)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg2_kai_nimmt_pia_in_duene_auf_waehrend_mona_duene_verschiebt(org, moving_first):
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).admit(org.duene, org.pia.key),
        lambda: Role.objects.filter(user=org.pia, kind=R.MEMBER, unit=org.duene).exists(),
        moving_first)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg3_kai_verschiebt_dana_in_die_sippe_moewen_waehrend_mona_duene_verschiebt(org, moving_first):
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).move(org.duene, org.dana.key, org.sippe_moewen.key),
        lambda: Role.objects.get(user=org.dana, kind=R.MEMBER).unit_id == org.sippe_moewen.pk,
        moving_first)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg4_kai_traegt_dana_aus_duene_aus_waehrend_mona_duene_verschiebt(org, moving_first):
    """Mit „hoch“: Nach altem Stand käme Dana in Ring Küste, obwohl Düne schon in Nord liegt."""
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).expel(org.duene, org.dana.key, "hoch"),
        lambda: Role.objects.get(user=org.dana, kind=R.MEMBER).unit_id != org.duene.pk,
        moving_first)
    if not moving_first:
        assert Role.objects.get(user=org.dana, kind=R.MEMBER).unit_id == org.kueste.pk


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg5_kai_entfernt_gerd_als_gruppenleitung_waehrend_mona_duene_verschiebt(org, moving_first):
    role_key = Role.objects.get(user=org.gerd, kind=R.GROUP_LEAD).key
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).remove(org.sippe_moewen, role_key),
        lambda: not Role.objects.filter(user=org.gerd, kind=R.GROUP_LEAD).exists(),
        moving_first)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg6_kai_legt_ella_in_duene_an_waehrend_mona_duene_verschiebt(org, moving_first):
    ella = {"first_name": "Ella", "last_name": "Probe", "birth_date": date(2015, 6, 1), "scout_name": "",
            "consent": True}
    _assert_exactly_one(
        org,
        lambda: Rights(org.kueste_leitung).add_managed(org.duene, ella, "e" * 20),
        lambda: ManagedPerson.objects.filter(first_name="Ella").exists(),
        moving_first)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg7_kai_aendert_emils_angaben_waehrend_mona_duene_verschiebt(org, moving_first):
    """Das Bearbeiten schreibt nichts ins Protokoll der Rollenänderungen; geprüft wird die Person selbst."""
    start = _mark()

    def action():
        return Rights(org.kueste_leitung).edit_managed(org.duene, org.emil.key, {**EMIL, "first_name": "Emilio"}, "1")

    if moving_first:
        move_result, kai_result = _at_once(_mona_moves_duene(org), action)
    else:
        kai_result, move_result = _at_once(action, _mona_moves_duene(org))

    assert move_result[0] is True
    assert _duene_in_nord(org)
    emil = ManagedPerson.objects.get(pk=org.emil.pk)
    if moving_first:
        assert kai_result == NOT_FOUND
        assert (emil.first_name, emil.version) == ("Emil", 1)
        assert not RoleChange.objects.filter(pk__gt=start[0]).exists()
        assert UnitChange.objects.filter(pk__gt=start[1]).count() == 1
    else:
        assert kai_result[0] is True
        assert (emil.first_name, emil.version) == ("Emilio", 2)


@pytest.mark.parametrize("moving_first", [True, False])
def test_rg8_mona_benennt_dana_in_einem_zweiten_fenster_waehrend_sie_duene_verschiebt(org, moving_first):
    """Gegenprobe: Mona hat das Recht vor und nach dem Wechsel; beides ist gespeichert, in jeder Reihenfolge."""

    def appoint():
        return Rights(org.mosaik_leitung).appoint(org.duene, org.dana.key)

    if moving_first:
        move_result, appoint_result = _at_once(_mona_moves_duene(org), appoint)
    else:
        appoint_result, move_result = _at_once(appoint, _mona_moves_duene(org))

    assert (move_result[0], appoint_result[0]) == (True, True)
    assert _duene_in_nord(org)
    assert Role.objects.filter(user=org.dana, kind=R.TROOP_LEAD, unit=org.duene).exists()


def test_rg9_kai_benennt_in_leuchtturm_waehrend_mona_duene_verschiebt(org):
    """Gegenprobe: In einem anderen Stamm von Küste merkt Kai nichts vom Wechsel, auch wenn er auf ihn wartet."""
    move_result, appoint_result = _at_once(
        _mona_moves_duene(org), lambda: Rights(org.kueste_leitung).appoint(org.moewen, org.moewe.key))

    assert (move_result[0], appoint_result[0]) == (True, True)
    assert _duene_in_nord(org)
    assert Role.objects.filter(user=org.moewe, kind=R.GROUP_LEAD, unit=org.moewen).exists()
