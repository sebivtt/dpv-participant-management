"""Tests für die zentrale Rechteprüfung (#90, BER-01, ROL-02, `docs/rechtematrix.md`).

Geprüft wird die Stelle selbst, ohne Seite. Zeilen der Matrix, deren Seite noch fehlt, bleiben auf
„geplant“; die Tests tragen ihre Kennung schon, damit die späteren Issues sie finden (Protokoll der
Nachklärung vom 25.10.2026). Jeder Fall einer Zeile hat einen eigenen Test (#136, A17), eine
Zeile „erlaubt“ prüft den nächsten Nachbarn als verbotenen Fall. Alle Namen sind erfunden.
"""

from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.http import Http404
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from access.rights import Rights, RightsMiddleware, on_lead_path
from roles.models import Role
from tests.query_limit import assert_queries_do_not_grow
from tests.test_rollen import BY, build_org, give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
pytestmark = pytest.mark.django_db


@pytest.fixture
def org() -> SimpleNamespace:
    """Die Einheiten aus tests/test_rollen.py, dazu Personen mit den Rollen der Beispiele.

    Boreas hat keine Ringe: Walhall (Sippe Falken, Meute Wölfe) und Zugvögel (Sippe Adler).
    DPBM Mosaik hat Ringe: Küste (Leuchtturm mit Meute Möwen) und Nord (Sturmvogel).
    """
    o = build_org()
    o.bundesleitung = lead("bruno.bund", R.ASSOCIATION_LEAD, o.boreas)
    o.walhall_leitung = lead("wanda.walhall", R.TROOP_LEAD, o.walhall)
    o.zugvoegel_leitung = lead("zora.zugvogel", R.TROOP_LEAD, o.zugvoegel)
    o.falken_leitung = lead("fiete.falke", R.GROUP_LEAD, o.falken)
    o.woelfe_leitung = lead("wim.wolf", R.GROUP_LEAD, o.woelfe)
    o.adler_leitung = lead("ada.adler", R.GROUP_LEAD, o.adler)
    o.mosaik_leitung = lead("mona.mosaik", R.ASSOCIATION_LEAD, o.mosaik)
    o.kueste_leitung = lead("kai.kueste", R.RING_LEAD, o.kueste)
    o.nord_leitung = lead("nele.nord", R.RING_LEAD, o.nord)
    o.leuchtturm_leitung = lead("lars.leuchtturm", R.TROOP_LEAD, o.leuchtturm)
    o.moewen_leitung = lead("mia.moewe", R.GROUP_LEAD, o.moewen)
    o.verbandsleitung = lead("vera.verband", R.FEDERATION_LEAD, o.dpv)
    o.team = lead("tom.team", R.EVENT_TEAM, o.dpv)
    o.falke = member("finn.falke", o.falken)
    o.wolf = member("wiebke.wolf", o.woelfe)
    o.adler_kind = member("anton.adler", o.adler)
    o.walhall_mitglied = member("wilma.walhall", o.walhall)
    o.boreas_mitglied = member("bea.boreas", o.boreas)
    o.moewe = member("moritz.moewe", o.moewen)
    o.sturmvogel_mitglied = member("svea.sturm", o.sturmvogel)
    o.ohne = person("otto.ohne", "Otto", "Ohne")
    return o


def lead(username: str, kind: str, where):
    first, last = username.split(".")
    user = person(username, first.title(), last.title())
    give(user, kind, where)
    return user


def member(username: str, where):
    first, last = username.split(".")
    user = person(username, first.title(), last.title())
    give(user, R.MEMBER, where)
    return user


def seen(user) -> set[str]:
    """Wessen Personendaten jemand nach BER-01, Grund 1 und 2 sieht."""
    return set(Rights(user).persons().values_list("username", flat=True))


def leads_seen(user) -> set[tuple[str, str]]:
    """Wessen Name und Rolle als Leitung jemand nach BER-01, Grund 3 sieht."""
    return {(entry["first_name"], entry["kind"]) for entry in Rights(user).leads()}


def remove(user, kind: str, where) -> None:
    Role.objects.get(user=user, kind=kind, unit=where).delete(by=BY)


# Grund 1: die Person selbst


@pytest.mark.rechtematrix("PK-05")
def test_jede_person_sieht_sich_selbst(org):
    """BER-01, Grund 1; Gegenprobe zu PK-05, PK-06 und PK-08."""
    for user in (org.falke, org.ohne, org.verbandsleitung, org.team, org.walhall_leitung):
        assert user.username in seen(user)


# Grund 2: Leitungen sehen die Personen ihres Bereichs


@pytest.mark.rechtematrix("PK-01")
def test_gruppenleitung_sieht_die_mitglieder_ihrer_gruppe(org):
    assert "finn.falke" in seen(org.falken_leitung)


@pytest.mark.rechtematrix("PK-01")
def test_gruppenleitung_sieht_keine_andere_gruppe_ihres_stammes(org):
    """Verbotener Nachbar zu PK-01."""
    assert "wiebke.wolf" not in seen(org.falken_leitung)
    assert "wilma.walhall" not in seen(org.falken_leitung)


@pytest.mark.rechtematrix("PK-02")
def test_stammesleitung_sieht_ihren_stamm_und_seine_gruppen(org):
    assert {"wilma.walhall", "finn.falke", "wiebke.wolf"} <= seen(org.walhall_leitung)


@pytest.mark.rechtematrix("PK-02")
def test_stammesleitung_sieht_den_nachbarstamm_nicht(org):
    """Verbotener Nachbar zu PK-02; das Beispiel aus BER-01."""
    assert "anton.adler" not in seen(org.walhall_leitung)
    assert "bea.boreas" not in seen(org.walhall_leitung)


@pytest.mark.rechtematrix("PK-03")
def test_ringleitung_sieht_ihren_ring_und_alles_darunter(org):
    assert "moritz.moewe" in seen(org.kueste_leitung)


@pytest.mark.rechtematrix("PK-03")
def test_ringleitung_sieht_den_nachbarring_nicht(org):
    assert "svea.sturm" not in seen(org.kueste_leitung)


@pytest.mark.rechtematrix("PK-03")
def test_bundesleitung_sieht_ihren_bund_und_alles_darunter(org):
    """Das Beispiel aus BER-01: die Bundesleitung von Boreas."""
    expected = {"bea.boreas", "wilma.walhall", "finn.falke", "wiebke.wolf", "anton.adler"}
    assert expected <= seen(org.bundesleitung)


@pytest.mark.rechtematrix("PK-03")
def test_bundesleitung_sieht_einen_anderen_bund_nicht(org):
    assert not {"moritz.moewe", "svea.sturm"} & seen(org.bundesleitung)


@pytest.mark.rechtematrix("PK-04")
def test_leitung_sieht_leitungen_ausserhalb_ihres_bereichs_nicht_ganz(org):
    """PK-04: Die Bundesleitung über Walhall steht auf der Kette, ihre Daten sieht Wanda nicht."""
    assert "bruno.bund" not in seen(org.walhall_leitung)
    assert "zora.zugvogel" not in seen(org.walhall_leitung)


@pytest.mark.rechtematrix("PK-04", "RO-03")
def test_zweite_stammesleitung_sieht_die_daten_eines_bundesmitglieds_nicht(org):
    """Das Beispiel zu RO-03: Berta ist Mitglied des Bundes und Stammesleitung von Walhall."""
    berta = member("berta.bund", org.boreas)
    give(berta, R.TROOP_LEAD, org.walhall)

    assert "berta.bund" not in seen(org.walhall_leitung)
    assert ("Berta", R.TROOP_LEAD) in leads_seen(org.walhall_leitung)


@pytest.mark.rechtematrix("PK-05")
def test_mitglied_sieht_keine_anderen_personen_auch_nicht_in_der_eigenen_einheit(org):
    other = member("frieda.falke", org.falken)

    assert seen(org.falke) == {"finn.falke"}
    assert other.username not in seen(org.falke)


@pytest.mark.rechtematrix("PK-06")
def test_konto_ohne_zuordnung_sieht_keine_anderen_personen(org):
    assert seen(org.ohne) == {"otto.ohne"}


@pytest.mark.rechtematrix("PK-07")
def test_verbandsleitung_sieht_keine_personen_der_buende(org):
    """ROL-03: auch nicht die Bundesleitungen als Personen, nur nach Grund 3 (RO-05)."""
    assert seen(org.verbandsleitung) == {"vera.verband"}


@pytest.mark.rechtematrix("PK-07")
def test_dpv_veranstaltungsteam_sieht_keine_personen_der_buende(org):
    assert seen(org.team) == {"tom.team"}


@pytest.mark.rechtematrix("PK-08")
def test_admin_ohne_support_zugang_sieht_keine_personen(org):
    give(org.max, R.ADMIN)

    assert seen(org.max) == {"max.testmann"}


@pytest.mark.rechtematrix("PK-01", "PK-04", "PK-07")
def test_verbandsleitung_als_gruppenleitung_sieht_nur_ihre_gruppe(org):
    """Testfall aus der Prüfung von PR #135: Rechte zählen über alle Rollen zusammen."""
    give(org.verbandsleitung, R.GROUP_LEAD, org.adler)

    assert "anton.adler" in seen(org.verbandsleitung)
    assert "finn.falke" not in seen(org.verbandsleitung)


@pytest.mark.rechtematrix("PK-01")
def test_wer_mehrere_rollen_hat_darf_was_eine_davon_erlaubt(org):
    """Gegenprobe aus #90: Gruppenleitung zweier Gruppen sieht beide."""
    give(org.falken_leitung, R.GROUP_LEAD, org.woelfe)

    assert {"finn.falke", "wiebke.wolf"} <= seen(org.falken_leitung)


@pytest.mark.rechtematrix("PK-04")
def test_einzelne_person_ohne_recht_ist_nicht_gefunden_wie_eine_nicht_vorhandene(org):
    """#64: Eine fremde und eine nicht vorhandene Person ergeben dieselbe Antwort."""
    rights = Rights(org.walhall_leitung)

    assert rights.person(org.falke.key) == org.falke
    for key in (org.adler_kind.key, "a" * 20):
        with pytest.raises(Http404):
            rights.person(key)


def test_laufende_nummer_fuehrt_nicht_mehr_zur_person(org):
    """#64: Die zentrale Stelle nimmt nur die zufällige Kennung, auch nicht die Nummer eines sichtbaren Eintrags."""
    with pytest.raises(Http404):
        Rights(org.walhall_leitung).person(org.falke.pk)
    with pytest.raises(Http404):
        Rights(org.walhall_leitung).person(str(org.falke.pk))


def test_wer_als_leitung_entfernt_wird_sieht_die_personen_beim_naechsten_klick_nicht_mehr(org):
    """#90, Szenario Leitungswechsel: jeder Klick ist eine neue Prüfung."""
    assert "finn.falke" in seen(org.walhall_leitung)

    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    assert "finn.falke" not in seen(org.walhall_leitung)


# Grund 3: Name und Rolle von Leitungen, Kette nach oben


@pytest.mark.rechtematrix("RO-01")
def test_leitung_sieht_die_leitungen_ueber_ihrer_geleiteten_einheit(org):
    """#150, C3: Berta ist Mitglied des Bundes und leitet Leuchtturm; sie sieht die Ringleitung."""
    berta = member("berta.bund", org.mosaik)
    give(berta, R.TROOP_LEAD, org.leuchtturm)

    assert {("Kai", R.RING_LEAD), ("Mona", R.ASSOCIATION_LEAD)} <= leads_seen(berta)


@pytest.mark.rechtematrix("RO-01")
def test_leitung_sieht_die_leitungen_ab_ihrer_mitgliedschaft(org):
    """RO-01: Die Gruppenleitung der Falken ist Mitglied in Falken und sieht Walhall und Boreas."""
    assert {("Wanda", R.TROOP_LEAD), ("Bruno", R.ASSOCIATION_LEAD)} <= leads_seen(org.falken_leitung)


@pytest.mark.rechtematrix("RO-01")
def test_leitung_sieht_die_leitung_eines_nachbarrings_nicht(org):
    """Verbotener Nachbar zu RO-01."""
    berta = member("berta.bund", org.mosaik)
    give(berta, R.TROOP_LEAD, org.leuchtturm)

    assert ("Nele", R.RING_LEAD) not in leads_seen(berta)
    assert ("Svea", R.MEMBER) not in leads_seen(berta)


@pytest.mark.rechtematrix("RO-02")
def test_mitglied_einer_gruppe_sieht_die_leitungen_bis_zum_bund(org):
    expected = {("Fiete", R.GROUP_LEAD), ("Wanda", R.TROOP_LEAD), ("Bruno", R.ASSOCIATION_LEAD)}
    assert leads_seen(org.falke) == expected


@pytest.mark.rechtematrix("RO-02")
def test_mitglied_einer_gruppe_im_ring_sieht_auch_die_ringleitung(org):
    expected = {("Mia", R.GROUP_LEAD), ("Lars", R.TROOP_LEAD), ("Kai", R.RING_LEAD), ("Mona", R.ASSOCIATION_LEAD)}
    assert leads_seen(org.moewe) == expected


@pytest.mark.rechtematrix("RO-02")
def test_mitglied_direkt_im_bund_sieht_nur_die_bundesleitung(org):
    assert leads_seen(org.boreas_mitglied) == {("Bruno", R.ASSOCIATION_LEAD)}


@pytest.mark.rechtematrix("RO-02")
def test_mitglied_sieht_die_verbandsleitung_nicht(org):
    """Die Kette endet am Bund."""
    assert ("Vera", R.FEDERATION_LEAD) not in leads_seen(org.falke)


@pytest.mark.rechtematrix("RO-03")
def test_leitung_sieht_die_leitungen_aller_einheiten_in_ihrem_bereich(org):
    assert {("Fiete", R.GROUP_LEAD), ("Wim", R.GROUP_LEAD)} <= leads_seen(org.walhall_leitung)
    assert {("Wanda", R.TROOP_LEAD), ("Zora", R.TROOP_LEAD), ("Ada", R.GROUP_LEAD)} <= leads_seen(org.bundesleitung)


@pytest.mark.rechtematrix("RO-03")
def test_leitung_sieht_leitungen_ausserhalb_ihres_bereichs_nicht(org):
    """Verbotener Nachbar zu RO-03: die Gruppenleitung im Nachbarstamm."""
    assert ("Ada", R.GROUP_LEAD) not in leads_seen(org.walhall_leitung)


@pytest.mark.rechtematrix("RO-03")
def test_leitungen_derselben_einheit_sehen_sich_gegenseitig(org):
    """BER-01, Grund 3: wer mit ihr dieselbe Einheit leitet."""
    second = lead("erna.walhall", R.TROOP_LEAD, org.walhall)

    assert ("Wanda", R.TROOP_LEAD) in leads_seen(second)
    assert ("Erna", R.TROOP_LEAD) in leads_seen(org.walhall_leitung)


@pytest.mark.rechtematrix("RO-04")
def test_mitglied_sieht_die_leitung_einer_anderen_gruppe_im_stamm_nicht(org):
    assert ("Wim", R.GROUP_LEAD) not in leads_seen(org.falke)


@pytest.mark.rechtematrix("RO-04")
def test_leitung_sieht_leitungen_des_nachbarstamms_und_anderer_buende_nicht(org):
    seen_leads = leads_seen(org.walhall_leitung)

    assert ("Zora", R.TROOP_LEAD) not in seen_leads
    assert ("Mona", R.ASSOCIATION_LEAD) not in seen_leads


@pytest.mark.rechtematrix("RO-05")
def test_verbandsleitung_sieht_bundesleitungen_verbandsleitungen_und_veranstaltungsteam(org):
    second = lead("viktor.verband", R.FEDERATION_LEAD, org.dpv)

    expected = {
        ("Bruno", R.ASSOCIATION_LEAD),
        ("Mona", R.ASSOCIATION_LEAD),
        ("Vera", R.FEDERATION_LEAD),
        ("Viktor", R.FEDERATION_LEAD),
        ("Tom", R.EVENT_TEAM),
    }
    assert leads_seen(second) == expected


@pytest.mark.rechtematrix("RO-06")
def test_verbandsleitung_sieht_leitungen_von_ringen_staemmen_und_gruppen_nicht(org):
    seen_leads = leads_seen(org.verbandsleitung)

    assert not {("Kai", R.RING_LEAD), ("Wanda", R.TROOP_LEAD), ("Fiete", R.GROUP_LEAD)} & seen_leads
    assert ("Bruno", R.ASSOCIATION_LEAD) in seen_leads


@pytest.mark.rechtematrix("RO-07")
def test_veranstaltungsteam_sieht_keine_leitungen(org):
    assert leads_seen(org.team) == set()


@pytest.mark.rechtematrix("RO-07")
def test_veranstaltungsteam_als_mitglied_sieht_die_leitungen_seiner_kette(org):
    """Gegenprobe zu RO-07: Rechte aus der Mitgliedschaft bleiben."""
    give(org.team, R.MEMBER, org.falken)

    assert ("Fiete", R.GROUP_LEAD) in leads_seen(org.team)


@pytest.mark.rechtematrix("RO-08")
def test_konto_ohne_zuordnung_und_admin_sehen_keine_leitungen(org):
    give(org.max, R.ADMIN)

    assert leads_seen(org.ohne) == set()
    assert leads_seen(org.max) == set()


@pytest.mark.rechtematrix("RO-08")
def test_admin_mit_mitgliedschaft_sieht_die_leitungen_seiner_kette(org):
    """Gegenprobe zu RO-08: Die Rolle Admin nimmt nichts weg."""
    give(org.falke, R.ADMIN)

    assert ("Fiete", R.GROUP_LEAD) in leads_seen(org.falke)


@pytest.mark.rechtematrix("RO-01", "RO-03")
def test_leitungen_zeigen_nur_name_und_rolle_nicht_die_mail(org):
    """#136, B2: Mail und weitere Angaben nur, wer die Person nach BER-01 ohnehin sieht.

    Den Fahrtennamen nennt BER-01, Grund 3 schon; das Feld gibt es seit #111. Interne Nummern
    (`user_id`, `unit_id`) gibt die Liste seit #156 nicht mehr heraus. Seit #189 kommen Benutzername
    (wenn der Name fehlt, A12), die Kennungen von Konto und Einheit und die Kennzeichnung gesperrter
    Leitungen dazu, seit #191 die Kennung der Rolle für „Entfernen“, die Mail weiterhin nicht.
    """
    entries = list(Rights(org.falke).leads())

    assert entries
    for entry in entries:
        assert set(entry) == {"first_name", "last_name", "scout_name", "username", "user_key", "kind",
                              "unit_name", "unit_key", "locked", "role_key"}


@pytest.mark.rechtematrix("RO-02")
def test_mitglieder_sehen_nur_leitungsrollen_nicht_die_mitgliedschaften(org):
    """Grund 3 nennt nur Leitungen; Mitglieder der Kette sind keine."""
    assert ("Wilma", R.MEMBER) not in leads_seen(org.falke)
    assert all(kind != R.MEMBER for _, kind in leads_seen(org.walhall_leitung))


# Bereich und Kette als Bausteine


def test_bereich_der_gruppenleitung_ist_nur_ihre_gruppe(org):
    assert Rights(org.falken_leitung).area == {org.falken.pk}


def test_bereich_der_stammesleitung_ist_stamm_mit_gruppen(org):
    assert Rights(org.walhall_leitung).area == {org.walhall.pk, org.falken.pk, org.woelfe.pk}


def test_kette_beginnt_bei_mitgliedschaft_und_geleiteter_einheit_und_endet_am_bund(org):
    """#150, C3, das Beispiel Berta."""
    berta = member("berta.bund", org.mosaik)
    give(berta, R.TROOP_LEAD, org.leuchtturm)

    assert Rights(berta).chain == {org.leuchtturm.pk, org.kueste.pk, org.mosaik.pk}


def test_kette_eines_mitglieds_einer_gruppe_schliesst_andere_gruppen_aus(org):
    """#136, B3."""
    assert Rights(org.falke).chain == {org.falken.pk, org.walhall.pk, org.boreas.pk}


# Einspringende Leitung (ROL-02, EH-18, EH-19, EH-27)


@pytest.mark.rechtematrix("EH-18")
def test_stammesleitung_springt_fuer_eine_gruppe_ohne_leitung_ein(org):
    """Das Beispiel aus EH-18: Die Sippe Falken hat keine Gruppenleitung."""
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)

    rights = Rights(org.walhall_leitung)
    assert rights.covers(org.falken)
    assert rights.leads_unit(org.falken)
    assert rights.leads_unit_of(org.falke)


@pytest.mark.rechtematrix("EH-19")
def test_hat_die_gruppe_eine_leitung_springt_die_stammesleitung_nicht_ein(org):
    rights = Rights(org.walhall_leitung)

    assert not rights.covers(org.falken)
    assert not rights.leads_unit(org.falken)
    assert not rights.leads_unit_of(org.falke)
    assert rights.leads_unit(org.walhall)
    assert rights.leads_unit_of(org.walhall_mitglied)


@pytest.mark.rechtematrix("EH-18")
def test_fehlt_auch_die_stammesleitung_springt_die_naechsthoehere_ein(org):
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    rights = Rights(org.bundesleitung)
    assert rights.covers(org.walhall)
    assert rights.covers(org.falken)
    assert not rights.covers(org.woelfe)
    assert not Rights(org.zugvoegel_leitung).covers(org.walhall)


@pytest.mark.rechtematrix("EH-18")
def test_im_bund_mit_ringen_springt_die_ringleitung_vor_der_bundesleitung_ein(org):
    remove(org.leuchtturm_leitung, R.TROOP_LEAD, org.leuchtturm)

    assert Rights(org.kueste_leitung).covers(org.leuchtturm)
    assert not Rights(org.mosaik_leitung).covers(org.leuchtturm)


@pytest.mark.rechtematrix("EH-18")
def test_fuer_einen_ring_ohne_leitung_springt_die_bundesleitung_ein(org):
    remove(org.nord_leitung, R.RING_LEAD, org.nord)

    assert Rights(org.mosaik_leitung).covers(org.nord)
    assert not Rights(org.kueste_leitung).covers(org.nord)


@pytest.mark.rechtematrix("EH-18")
def test_stamm_ohne_ring_im_bund_mit_ringen_bekommt_die_bundesleitung(org):
    """#136, F2.7: Stämme von vor dem Einschalten von „hat Ringe“ dürfen ohne Ring bleiben."""
    alt = unit(U.TROOP, "Altstamm", org.boreas)
    org.boreas.has_rings = True
    org.boreas.save(by=BY)

    assert Rights(org.bundesleitung).covers(alt)


@pytest.mark.rechtematrix("EH-27")
def test_fuer_einen_bund_ohne_leitung_springt_niemand_ein(org):
    remove(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    for user in (org.verbandsleitung, org.team, org.zugvoegel_leitung, org.mosaik_leitung):
        rights = Rights(user)
        assert not rights.covers(org.boreas)
        assert not rights.covers(org.walhall)
        assert not rights.leads_unit(org.boreas)


@pytest.mark.rechtematrix("EH-27")
def test_verbandsleitung_springt_nie_ein(org):
    """Gegenprobe zu EH-27: Die Bundesleitung springt für den Stamm weiter ein."""
    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)

    assert not Rights(org.verbandsleitung).covers(org.walhall)
    assert Rights(org.bundesleitung).covers(org.walhall)


@pytest.mark.rechtematrix("EH-18")
def test_einspringen_endet_mit_der_benennung_einer_leitung(org):
    """ROL-02: berechnet, nicht als Rolle gespeichert; endet beim nächsten Klick."""
    remove(org.falken_leitung, R.GROUP_LEAD, org.falken)
    roles_before = Role.objects.count()
    assert Rights(org.walhall_leitung).covers(org.falken)
    assert Role.objects.count() == roles_before

    give(org.falken_leitung, R.GROUP_LEAD, org.falken)

    assert not Rights(org.walhall_leitung).covers(org.falken)


@pytest.mark.rechtematrix("EH-18")
def test_fuer_eine_gesperrte_leitung_springt_die_leitung_darueber_ein(org):
    """Sebastian, 25.10.2026: Eine im Tool gesperrte Leitung zählt nicht als Leitung mit Konto."""
    org.falken_leitung.is_active = False
    org.falken_leitung.save()

    assert Rights(org.walhall_leitung).covers(org.falken)
    assert not Rights(org.walhall_leitung).covers(org.woelfe)


@pytest.mark.rechtematrix("EH-19")
def test_leitung_springt_nicht_fuer_einheiten_ueber_oder_neben_ihr_ein(org):
    remove(org.bundesleitung, R.ASSOCIATION_LEAD, org.boreas)
    remove(org.adler_leitung, R.GROUP_LEAD, org.adler)

    rights = Rights(org.walhall_leitung)
    assert not rights.covers(org.boreas)
    assert not rights.covers(org.adler)
    assert not rights.leads_unit(org.zugvoegel)


# Leitung der eigenen Einheit einer Person


@pytest.mark.rechtematrix("PK-21")
def test_leitung_der_eigenen_einheit_der_person(org):
    assert Rights(org.falken_leitung).leads_unit_of(org.falke)
    assert Rights(org.walhall_leitung).leads_unit_of(org.walhall_mitglied)


@pytest.mark.rechtematrix("PK-22")
def test_leitung_darueber_ist_nicht_die_leitung_der_eigenen_einheit(org):
    assert not Rights(org.walhall_leitung).leads_unit_of(org.falke)
    assert not Rights(org.bundesleitung).leads_unit_of(org.walhall_mitglied)
    assert not Rights(org.falken_leitung).leads_unit_of(org.walhall_mitglied)


def test_person_ohne_mitgliedschaft_hat_keine_leitung_der_eigenen_einheit(org):
    """Absicherung gegen leere Werte: Ein Konto ohne Zuordnung gehört zu keiner Einheit."""
    for user in (org.bundesleitung, org.verbandsleitung, org.falken_leitung):
        assert not Rights(user).leads_unit_of(org.ohne)


# Leitungspfad (#89)


def test_leitungspfad_gilt_im_eigenen_stamm_und_darueber(org):
    assert on_lead_path(org.falke, org.woelfe)
    assert on_lead_path(org.falke, org.boreas)
    assert on_lead_path(org.boreas_mitglied, org.adler)


def test_leitungspfad_gilt_nicht_im_nachbarstamm_und_ohne_mitgliedschaft(org):
    assert not on_lead_path(org.falke, org.adler)
    assert not on_lead_path(org.falke, org.mosaik)
    assert not on_lead_path(org.ohne, org.falken)


# Absicherung gegen leere Werte (F4.3)


@pytest.mark.parametrize("who", ["anonym", "ungespeichert", "inaktiv"])
def test_ohne_gueltiges_konto_ist_alles_verboten(org, who):
    """Ohne Login, mit einem nicht gespeicherten oder einem gesperrten Konto."""
    if who == "anonym":
        user = AnonymousUser()
    elif who == "ungespeichert":
        user = type(org.ohne)(username="niemand")
    else:
        user = org.walhall_leitung
        user.is_active = False
        user.save()
    rights = Rights(user)

    assert list(rights.persons()) == []
    assert list(rights.leads()) == []
    assert rights.area == frozenset()
    assert rights.chain == frozenset()
    assert not rights.leads_unit(org.walhall)
    assert not rights.leads_unit_of(org.falke)
    with pytest.raises(Http404):
        rights.person(org.falke.key)


@pytest.mark.parametrize("value", [None, "", "abc", "1; DROP", -1, 0, 3.5, [1], "A" * 20, "a" * 21, "a" * 19 + "1"])
def test_unbrauchbare_kennung_ist_nicht_gefunden(org, value):
    """Manipulierte Kennungen ergeben „nicht gefunden“, nie eine Fehlerseite."""
    with pytest.raises(Http404):
        Rights(org.walhall_leitung).person(value)


def test_ohne_einheit_ist_niemand_leitung(org):
    rights = Rights(org.bundesleitung)

    assert not rights.leads_unit(None)
    assert not rights.covers(None)
    assert not rights.leads_unit_of(None)


def test_admin_rolle_ohne_einheit_gibt_keinen_bereich(org):
    give(org.max, R.ADMIN)

    rights = Rights(org.max)
    assert rights.area == frozenset()
    assert rights.chain == frozenset()


def test_verband_liegt_nie_im_bereich_oder_auf_der_kette(org):
    """Verbandsleitung und Veranstaltungsteam hängen am Verband; ihr Bereich bleibt leer."""
    for user in (org.verbandsleitung, org.team, org.bundesleitung, org.falke):
        rights = Rights(user)
        assert org.dpv.pk not in rights.area
        assert org.dpv.pk not in rights.chain
    assert not Rights(org.verbandsleitung).leads_unit(org.dpv)


# Einmal pro Anfrage laden, nie über Anfragen hinweg (F4.6)


def request_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return request


def test_jede_anfrage_bekommt_ihre_rechte(org):
    request = request_for(org.walhall_leitung)
    RightsMiddleware(lambda req: None)(request)

    assert "finn.falke" in set(request.rights.persons().values_list("username", flat=True))


def test_rollen_werden_einmal_pro_anfrage_geladen(org):
    """Viele Prüfungen in einer Anfrage fragen die Rollen nicht jedes Mal neu."""
    rights = Rights(org.walhall_leitung)
    rights.leads_unit(org.walhall)
    rights.covers(org.falken)
    with CaptureQueriesContext(connection) as later:
        for target in (org.falken, org.woelfe, org.walhall, org.adler, org.boreas):
            rights.leads_unit(target)
            rights.covers(target)
        assert rights.area
        assert rights.chain

    assert len(later) == 0


def test_kein_zwischenspeicher_ueber_anfragen_hinweg(org):
    """#90: Wer eine Rolle verliert, verliert die Rechte beim nächsten Klick."""
    first = request_for(org.walhall_leitung)
    RightsMiddleware(lambda req: None)(first)
    assert first.rights.leads_unit(org.walhall)

    remove(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    second = request_for(org.walhall_leitung)
    RightsMiddleware(lambda req: None)(second)

    assert not second.rights.leads_unit(org.walhall)


def test_die_middleware_ist_eingetragen(settings):
    """Sie muss nach dem Login-Baustein stehen, sonst kennt sie die Person nicht."""
    order = settings.MIDDLEWARE
    entry = "access.rights.RightsMiddleware"

    assert entry in order
    assert order.index(entry) > order.index("django.contrib.auth.middleware.AuthenticationMiddleware")


# Die Listen wachsen nicht mit (CONTRIBUTING.md, Abschnitt 5; #104)


def test_personenliste_fragt_nicht_pro_person(org):
    def add(number: int) -> None:
        member(f"kim.falke{number}", org.falken)

    assert_queries_do_not_grow(add, lambda: list(Rights(org.bundesleitung).persons()))


def test_leitungsliste_fragt_nicht_pro_leitung(org):
    def add(number: int) -> None:
        group = unit(U.GROUP, f"Sippe {number}", org.walhall)
        lead(f"lea.sippe{number}", R.GROUP_LEAD, group)

    assert_queries_do_not_grow(add, lambda: list(Rights(org.bundesleitung).leads()))


# Lücken aus den nachträglichen Szenarien zu #90 (#156, Szenarien vom 25.10.2026)


def block(user) -> None:
    """Sperrt ein Konto im Tool."""
    user.is_active = False
    user.save()


@pytest.mark.rechtematrix("PK-03")
def test_bundesleitung_eines_bundes_mit_ringen_sieht_die_personen_in_allen_ringen(org):
    """S1: Mona sieht Moritz aus dem Ring Küste und Svea aus dem Ring Nord."""
    assert {"moritz.moewe", "svea.sturm"} <= seen(org.mosaik_leitung)


@pytest.mark.rechtematrix("PK-03")
def test_bundesleitung_mit_ringen_sieht_keinen_anderen_bund_und_die_ringleitung_nicht_den_nachbarring(org):
    """V1: Mona sieht niemanden aus Boreas; Kai sieht Svea aus dem Nachbarring weiterhin nicht."""
    assert not {"bea.boreas", "finn.falke", "bruno.bund"} & seen(org.mosaik_leitung)
    assert "svea.sturm" not in seen(org.kueste_leitung)


@pytest.mark.rechtematrix("EH-19", "PK-01")
def test_niemand_springt_ein_solange_eine_leitung_der_einheit_nicht_gesperrt_ist(org):
    """V2 und S5: Nur Fiete ist gesperrt, Frida nicht. Wanda springt nicht ein, Frida behält ihre Rechte."""
    frida = lead("frida.falke", R.GROUP_LEAD, org.falken)
    block(org.falken_leitung)

    wanda = Rights(org.walhall_leitung)
    assert not wanda.covers(org.falken)
    assert not wanda.leads_unit(org.falken)
    assert not wanda.leads_unit_of(org.falke)
    assert Rights(frida).leads_unit(org.falken)
    assert Rights(frida).leads_unit_of(org.falke)
    assert "finn.falke" in seen(frida)


@pytest.mark.rechtematrix("EH-18")
def test_sind_alle_leitungen_der_einheit_gesperrt_springt_die_leitung_darueber_ein(org):
    """S2: Fiete und Frida sind beide gesperrt; Wanda springt für die Falken ein."""
    frida = lead("frida.falke", R.GROUP_LEAD, org.falken)
    block(org.falken_leitung)
    block(frida)

    wanda = Rights(org.walhall_leitung)
    assert wanda.covers(org.falken)
    assert wanda.leads_unit_of(org.falke)


@pytest.mark.rechtematrix("EH-18")
def test_bei_gesperrten_leitungen_auf_zwei_ebenen_springt_die_naechsthoehere_ein(org):
    """S3: Fiete und Wanda sind gesperrt; Bruno springt für die Falken und für Walhall ein."""
    block(org.falken_leitung)
    block(org.walhall_leitung)

    bruno = Rights(org.bundesleitung)
    assert bruno.covers(org.falken)
    assert bruno.covers(org.walhall)
    assert bruno.leads_unit_of(org.falke)
    assert bruno.leads_unit_of(org.walhall_mitglied)


@pytest.mark.rechtematrix("EH-18", "EH-27")
def test_bei_gesperrten_leitungen_auf_zwei_ebenen_springt_niemand_sonst_ein(org):
    """V3: nicht für die Wölfe mit Wim; Fiete und Wanda ohne Rechte; ist auch Bruno gesperrt, springt Vera nicht ein."""
    block(org.falken_leitung)
    block(org.walhall_leitung)

    assert not Rights(org.bundesleitung).covers(org.woelfe)
    assert not Rights(org.bundesleitung).leads_unit_of(org.wolf)
    for blocked in (org.falken_leitung, org.walhall_leitung):
        rights = Rights(blocked)
        assert not rights.leads_unit(org.falken)
        assert not rights.leads_unit(org.walhall)
        assert seen(blocked) == set()
        assert leads_seen(blocked) == set()

    block(org.bundesleitung)

    vera = Rights(org.verbandsleitung)
    for target in (org.boreas, org.walhall, org.falken):
        assert not vera.covers(target)
        assert not vera.leads_unit(target)
    assert seen(org.verbandsleitung) == {"vera.verband"}


@pytest.mark.rechtematrix("RO-02")
def test_mitglied_direkt_im_ring_sieht_die_ringleitung_und_die_bundesleitung(org):
    """S4 und V4: Rieke sieht genau Kai und Mona, nicht Lars, Mia oder Nele."""
    rieke = member("rieke.ring", org.kueste)

    assert leads_seen(rieke) == {("Kai", R.RING_LEAD), ("Mona", R.ASSOCIATION_LEAD)}


@pytest.mark.rechtematrix("RO-02")
def test_liste_der_leitungen_zeigt_name_rolle_und_einheit_ohne_interne_nummern(org):
    """S6 (#156, Lücke L2 aus #64): Finn sieht Fiete, Wanda und Bruno mit Name, Rolle und Einheit, ohne Nummern."""
    entries = list(Rights(org.falke).leads())

    shown = {(entry["first_name"], entry["last_name"], entry["kind"], entry["unit_name"]) for entry in entries}
    assert shown == {
        ("Fiete", "Falke", R.GROUP_LEAD, "Sippe Falken"),
        ("Wanda", "Walhall", R.TROOP_LEAD, "Walhall"),
        ("Bruno", "Bund", R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas"),
    }
    for entry in entries:
        assert not {"user_id", "unit_id", "id", "pk"} & set(entry)
