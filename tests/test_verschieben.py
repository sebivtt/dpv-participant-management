"""Tests für „Verschieben“ im Abschnitt „Personen“ auf der Seite einer Organisation (#287, Teil 3 von #65).

Die Kennungen P3, P4, P11, PV4, PV5, PV6, PV9, PG1, U1 und U2 verweisen auf die Szenarien vom
10.11.2026 (https://github.com/sebivtt/dpv-participant-management/issues/287#issuecomment-6766976342),
die Wortlaute auf den Text von #287 und die Nachklärung #65 N4. Dazu kommen Sebastians Antworten bei der
Umsetzung vom 10.11.2026 („1a und 2a“): Der Dialog bestätigt mit einem dunkelblauen Knopf, und die Wahl
ist der Baustein „Auswahl im Dialog“ ohne Vorschau
(https://github.com/sebivtt/dpv-participant-management/issues/287#issuecomment-6774992064), und zur Frage aus der
unabhängigen Prüfung „Ja, gewählt lassen“: Nach einer Ablehnung bleibt die abgelehnte Organisation gewählt
(https://github.com/sebivtt/dpv-participant-management/issues/287#issuecomment-6776012382).
Personen und Einheiten wie in den Tests zu #285 und #286 (`tests/test_personen.py`,
`tests/test_austragen.py`): Wanda heißt „Wirbelwind“, Willi „Wiesel“, Fiete „Funke“, Bruno
„Brummbär“; Wim ist direkt Mitglied von Walhall. Namen, Fahrtennamen und Mails sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from access.rights import Rights
from roles.models import Role, RoleChange
from tests import test_personen
from tests.test_austragen import _outcome, expel, log_since
from tests.test_benennen import _one_after_the_other, appoint, dialog_of, notices, roles_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, lock, page_tree, unit_address
from tests.test_personen import membership_of, persons_on_page
from tests.test_rechtepruefung import remove as remove_by_command
from tests.test_rollen import BY, build_org, give, person

R = Role.Kind
pytestmark = pytest.mark.django_db
User = get_user_model()

base_org = test_personen.base_org
org_189 = test_personen.org_189
org_190 = test_personen.org_190
org = test_personen.org

PG1_MESSAGE = (
    "Bea Boreas ist Stammesleitung von Stamm Zugvögel. Diese Rolle passt nicht zu Stamm Walhall. "
    "Sie kann zuerst beendet werden."
)


def move_address(where, target) -> str:
    return f"{unit_address(where)}verschieben/{target.key}/"


def move(user, where, target, goal, client=None, **more):
    """„Verschieben“ im Dialog bestätigen, wie der blaue Knopf es mit der gewählten Organisation abschickt."""
    return (client or client_for(user)).post(move_address(where, target), {"ziel": goal.key, **more})


def move_dialog(response) -> dict:
    """Der Dialog „Verschieben“: Titel, Zeile darunter, Frage, Möglichkeiten, Knopf und Meldungen.

    Die Optionsfelder gehören über ihr Attribut `form` zum Formular des Knopfs, damit die Wahl
    mitgeht, auch ohne Skript.
    """
    assert response.status_code == 200
    dialog = dialog_of(_tree(response))
    form = _one(_by_tag(dialog, "form", method="post"))
    choice = _one(_all(dialog, lambda e: "a-auswahl" in _classes(e)))
    options = []
    for entry in _by_tag(choice, "input", type="radio"):
        assert _attr(entry, "form") == _attr(form, "id")
        label = _one(_by_tag(choice, "label", **{"for": _attr(entry, "id")}))
        options.append((_attr(entry, "name"), _attr(entry, "value"), _visible_text(label),
                        _attr(entry, "checked") is not None))
    return {
        "title": _visible_text(_one(_by_tag(dialog, "h2"))),
        "subtitle": _visible_text(_one(_all(dialog, lambda e: "a-unterzeile" in _classes(e)))),
        "text": _visible_text(dialog),
        "options": options,
        "previews": _all(dialog, lambda e: "a-auswahl-folge" in _classes(e)),
        "button": _one(_by_tag(form, "button", type="submit")),
        "action": _attr(form, "action"),
        "notices": notices(dialog),
    }


def move_buttons(user, where) -> dict[str, str]:
    """Je Person im Abschnitt „Personen“ die Adresse ihres Knopfs „Verschieben“; ohne Knopf fehlt sie."""
    root = page_tree(user, unit_address(where))
    section = _one(_by_tag(root, "section", aria_labelledby="h-personen"))
    found = {}
    for entry in _all(section, lambda e: "a-leitung" in _classes(e) and e.name == "li"):
        name = _text(_one(_all(entry, lambda e: "a-leitung-name" in _classes(e))))
        links = [link for link in _all(entry, lambda e: "btn-verschieben" in _classes(e))
                 if _visible_text(link).startswith("Verschieben")]
        if links:
            found[name] = _attr(_one(links), "href")
    return found


# ---------- Wer den Knopf „Verschieben“ hat ----------


@pytest.mark.rechtematrix("PK-19", "EP-10")
def test_p3_die_stammesleitung_hat_verschieben_bei_jeder_person_auch_bei_sich(org):
    assert move_buttons(org.walhall_leitung, org.walhall) == {
        "Wirbelwind": move_address(org.walhall, org.walhall_leitung),
        "Wiesel": move_address(org.walhall, org.willi),
        "Wilma Walhall": move_address(org.walhall, org.walhall_mitglied),
        "Wim Wolf": move_address(org.walhall, org.woelfe_leitung),
    }
    assert set(move_buttons(org.bundesleitung, org.boreas)) == {"Bea Boreas", "Brummbär"}


def test_verschieben_steht_als_zart_blauer_knopf_vor_austragen(org):
    """#287: ein neuer kleiner Knopf mit zart blauer Fläche (#65 N5), vor „Austragen“ wie im Zielbild."""
    shown = persons_on_page(page_tree(org.walhall_leitung, unit_address(org.walhall)))

    assert shown["Wilma Walhall"]["buttons"] == ["Verschieben", "Austragen"]
    root = page_tree(org.walhall_leitung, unit_address(org.walhall))
    button = _all(root, lambda e: "btn-verschieben" in _classes(e))[0]
    assert {"btn", "btn-sm", "btn-verschieben"} <= set(_classes(button))
    assert _visible_text(button) == "Verschieben"
    # Vorleseprogramme hören dazu, wen der Knopf betrifft.
    assert _text(_one(_all(button, lambda e: "sr-nur" in _classes(e)))).strip() == ": Wirbelwind"


@pytest.mark.rechtematrix("PK-19", "EP-10")
def test_pv5_die_gruppenleitung_hat_keinen_knopf_verschieben(org):
    """PV5: Unter einer Gruppe gibt es nichts; Fiete verschiebt niemanden, auch sich selbst nicht."""
    shown = persons_on_page(page_tree(org.falken_leitung, unit_address(org.falken)))

    assert move_buttons(org.falken_leitung, org.falken) == {}
    assert all("Verschieben" not in entry["buttons"] for entry in shown.values())
    assert client_for(org.falken_leitung).get(move_address(org.falken, org.falke)).status_code == 404
    assert move(org.falken_leitung, org.falken, org.falken_leitung, org.woelfe).status_code == 404
    assert membership_of(org.falken_leitung) == "Sippe Falken"


@pytest.mark.rechtematrix("PK-20", "EH-19")
def test_in_organisationen_darunter_mit_eigener_leitung_gibt_es_keinen_knopf(org):
    assert move_buttons(org.bundesleitung, org.walhall) == {}
    assert move_buttons(org.kueste_leitung, org.leuchtturm) == {}


# ---------- Dialog „Verschieben“ ----------


@pytest.mark.rechtematrix("PK-19")
def test_p3_der_dialog_bietet_die_organisationen_direkt_darunter(org):
    shown = move_dialog(client_for(org.walhall_leitung).get(move_address(org.walhall, org.walhall_mitglied)))

    assert shown["title"] == "Verschieben"
    assert shown["subtitle"] == "Wilma Walhall aus Stamm Walhall"
    assert "Wohin soll die Person?" in shown["text"]
    assert shown["options"] == [
        ("ziel", org.woelfe.key, "Meute Wölfe", True),
        ("ziel", org.falken.key, "Sippe Falken", False),
    ]
    # Antwort 2a: keine Vorschau unter der Wahl; Antwort 1a: dunkelblauer Knopf, kein roter.
    assert shown["previews"] == []
    assert _visible_text(shown["button"]) == "Verschieben"
    assert "btn-primary" in _classes(shown["button"])
    assert "btn-gefahr" not in _classes(shown["button"])
    assert shown["action"] == move_address(org.walhall, org.walhall_mitglied)
    assert shown["notices"] == []
    # Der Dialog allein ändert nichts.
    assert membership_of(org.walhall_mitglied) == "Walhall"


@pytest.mark.rechtematrix("PK-19")
def test_beim_bund_stehen_die_staemme_zur_wahl(org):
    shown = move_dialog(client_for(org.bundesleitung).get(move_address(org.boreas, org.boreas_mitglied)))

    assert [(label, checked) for _name, _value, label, checked in shown["options"]] == [
        ("Stamm Walhall", True), ("Stamm Zugvögel", False)]


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("PK-19")
def test_p3_wanda_verschiebt_wilma_in_die_meute_woelfe(org):
    before = RoleChange.objects.count()
    client = client_for(org.walhall_leitung)

    response = move(org.walhall_leitung, org.walhall, org.walhall_mitglied, org.woelfe, client=client)

    assert response.status_code == 302
    assert response["Location"] == unit_address(org.walhall)
    assert short_notices(client.get(response["Location"])) == ["Wilma Walhall gehört jetzt zu Meute Wölfe."]
    assert roles_of(org.walhall_mitglied) == {(R.MEMBER, "Meute Wölfe")}
    # Jedes Verschieben steht im Protokoll der Rollenänderungen (#91).
    assert log_since(before) == [
        ("Wanda Walhall", "Wilma Walhall", R.MEMBER, "Walhall", "removed"),
        ("Wanda Walhall", "Wilma Walhall", R.MEMBER, "Meute Wölfe (Walhall)", "granted"),
    ]
    assert "Wilma Walhall" not in persons_on_page(page_tree(org.walhall_leitung, unit_address(org.walhall)))
    assert "Wilma Walhall" in persons_on_page(page_tree(org.walhall_leitung, unit_address(org.woelfe)))
    assert len(mail.outbox) == 0


@pytest.mark.rechtematrix("EP-10", "PK-19", "PK-25")
def test_p4_wanda_verschiebt_sich_selbst_und_bleibt_stammesleitung(org):
    client = client_for(org.walhall_leitung)

    response = move(org.walhall_leitung, org.walhall, org.walhall_leitung, org.woelfe, client=client)

    assert response["Location"] == unit_address(org.walhall)
    assert short_notices(client.get(response["Location"])) == [
        "Wirbelwind (Wanda Walhall) gehört jetzt zu Meute Wölfe."]
    assert roles_of(org.walhall_leitung) == {(R.MEMBER, "Meute Wölfe"), (R.TROOP_LEAD, "Walhall")}


@pytest.mark.rechtematrix("PK-19", "PK-21", "PK-17")
def test_p11_weg_2_anton_zieht_ueber_boreas_nach_walhall_um(org):
    """P11 (Weg 2, #65 Frage 7): Ada und Zora tragen Anton je eine Ebene nach oben aus, Bruno verschiebt ihn."""
    expel(org.adler_leitung, org.adler, org.adler_kind, "hoch")
    assert membership_of(org.adler_kind) == "Zugvögel"
    expel(org.zugvoegel_leitung, org.zugvoegel, org.adler_kind, "hoch")
    assert membership_of(org.adler_kind) == "Pfadfinderbund Boreas"

    response = move(org.bundesleitung, org.boreas, org.adler_kind, org.walhall)

    assert response.status_code == 302
    assert roles_of(org.adler_kind) == {(R.MEMBER, "Walhall")}
    assert "Anton Adler" in persons_on_page(page_tree(org.walhall_leitung, unit_address(org.walhall)))


@pytest.mark.rechtematrix("PK-20")
def test_pv4_gegenprobe_bruno_verschiebt_bea_in_einen_stamm(org):
    move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.zugvoegel)

    assert membership_of(org.boreas_mitglied) == "Zugvögel"


@pytest.mark.rechtematrix("EH-18", "PK-19", "PK-20")
def test_ohne_stammesleitung_springt_bruno_ein_und_verschiebt_wilma(org):
    remove_by_command(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove_by_command(org.willi, R.TROOP_LEAD, org.walhall)

    assert "Wilma Walhall" in move_buttons(org.bundesleitung, org.walhall)
    response = move(org.bundesleitung, org.walhall, org.walhall_mitglied, org.falken)

    assert response.status_code == 302
    assert membership_of(org.walhall_mitglied) == "Sippe Falken"


@pytest.mark.rechtematrix("EH-18", "PK-19")
def test_auch_bei_gesperrten_stammesleitungen_springt_bruno_ein(org):
    lock(org.walhall_leitung)
    lock(org.willi)

    response = move(org.bundesleitung, org.walhall, org.walhall_mitglied, org.woelfe)

    assert response.status_code == 302
    assert membership_of(org.walhall_mitglied) == "Meute Wölfe"


@pytest.mark.rechtematrix("EP-10", "EH-18")
def test_als_einspringende_leitung_verschiebt_bruno_sich_selbst(org):
    """Bruno ist direkt Mitglied von Walhall, und Walhall hat keine Stammesleitung mehr."""
    membership = Role.objects.get(user=org.bundesleitung, kind=R.MEMBER)
    membership.unit = org.walhall
    membership.save(by=BY)
    remove_by_command(org.walhall_leitung, R.TROOP_LEAD, org.walhall)
    remove_by_command(org.willi, R.TROOP_LEAD, org.walhall)

    response = move(org.bundesleitung, org.walhall, org.bundesleitung, org.falken)

    assert response.status_code == 302
    assert roles_of(org.bundesleitung) == {(R.MEMBER, "Sippe Falken"), (R.ASSOCIATION_LEAD, "Pfadfinderbund Boreas")}


# ---------- Verboten ----------


@pytest.mark.rechtematrix("PK-20", "EH-19")
@pytest.mark.wie_nicht_vorhanden("organisation/<key:unit>/verschieben/<key:person>/")
def test_pv4_bruno_verschiebt_wilma_nicht_in_die_falken(org):
    """PV4: Wilma gehört nicht direkt zu Boreas, und Walhall hat eine eigene Leitung."""
    assert_like_missing(org.bundesleitung, move_address(org.boreas, org.walhall_mitglied))
    assert move(org.bundesleitung, org.boreas, org.walhall_mitglied, org.falken).status_code == 404
    assert_like_missing(org.bundesleitung, move_address(org.walhall, org.walhall_mitglied))
    assert move(org.bundesleitung, org.walhall, org.walhall_mitglied, org.falken).status_code == 404

    assert membership_of(org.walhall_mitglied) == "Walhall"


@pytest.mark.rechtematrix("PK-20")
def test_pv4_bruno_verschiebt_bea_nur_in_einen_stamm_nicht_in_eine_gruppe(org):
    before = RoleChange.objects.count()

    assert move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.falken).status_code == 404

    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PK-20")
def test_pv9_wanda_schickt_die_sippe_adler_als_ziel_und_nichts_aendert_sich(org):
    before = RoleChange.objects.count()
    client = client_for(org.walhall_leitung)
    for goal in (org.adler, org.zugvoegel, org.boreas, org.walhall, org.leuchtturm):
        assert move(org.walhall_leitung, org.walhall, org.walhall_mitglied, goal, client=client).status_code == 404
    for value in ("", "irgendwas", str(org.woelfe.pk), org.walhall_mitglied.key):
        address = move_address(org.walhall, org.walhall_mitglied)
        assert client.post(address, {"ziel": value}).status_code == 404
    assert client.post(move_address(org.walhall, org.walhall_mitglied)).status_code == 404

    assert membership_of(org.walhall_mitglied) == "Walhall"
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PK-23", "EP-10")
def test_pv6_ohne_leitungsrolle_verschiebt_niemand(org):
    """PV6: Vera, Tom, Max ohne Support-Zugang, Wilma als Mitglied (auch sich selbst) und Otto."""
    org.max.refresh_from_db()
    cases = ((org.walhall, org.walhall_mitglied, org.woelfe), (org.boreas, org.boreas_mitglied, org.walhall))
    for user in (org.verbandsleitung, org.team, org.max, org.walhall_mitglied, org.ohne):
        for where, target, goal in cases:
            assert_like_missing(user, move_address(where, target))
            assert move(user, where, target, goal).status_code == 404

    assert membership_of(org.walhall_mitglied) == "Walhall"
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


@pytest.mark.rechtematrix("PK-23")
def test_pk23_gegenprobe_die_stammesleitung_nimmt_auf_verschiebt_und_traegt_aus(org):
    """Gegenprobe zu PK-23: Was Verbandsleitung, Team, Mitglieder und Konten ohne Zuordnung nicht dürfen, darf die Leitung."""
    assert test_personen.admit(org.walhall_leitung, org.walhall, org.ohne).status_code == 302
    assert move(org.walhall_leitung, org.walhall, org.walhall_mitglied, org.woelfe).status_code == 302
    assert expel(org.walhall_leitung, org.walhall, org.ohne, "ganz").status_code == 302

    assert membership_of(org.ohne) is None
    assert membership_of(org.walhall_mitglied) == "Meute Wölfe"


@pytest.mark.rechtematrix("PK-20")
def test_leitungen_anderer_organisationen_verschieben_niemanden(org):
    for user, where, target, goal in (
        (org.zugvoegel_leitung, org.walhall, org.walhall_mitglied, org.woelfe),
        (org.mosaik_leitung, org.boreas, org.boreas_mitglied, org.walhall),
        (org.woelfe_leitung, org.walhall, org.walhall_mitglied, org.woelfe),
    ):
        assert move(user, where, target, goal).status_code == 404

    assert membership_of(org.walhall_mitglied) == "Walhall"
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


def test_nur_direkte_mitglieder_der_organisation_aus_der_adresse(org):
    """Finn gehört zu den Falken, nicht direkt zu Walhall; auch ein Formularfeld „unit“ ändert das nicht."""
    assert move(org.walhall_leitung, org.walhall, org.falke, org.woelfe).status_code == 404
    assert move(org.walhall_leitung, org.walhall, org.walhall_mitglied, org.woelfe, unit=org.falken.key,
                person=org.falke.key).status_code == 302

    assert membership_of(org.falke) == "Sippe Falken"
    assert membership_of(org.walhall_mitglied) == "Meute Wölfe"


def test_falsche_oder_fehlende_kennung_einer_person_ist_nicht_gefunden(org):
    client = client_for(org.walhall_leitung)
    for address in (f"{unit_address(org.walhall)}verschieben/{org.walhall.key}/",
                    f"{unit_address(org.walhall)}verschieben/{org.walhall_mitglied.pk}/"):
        assert client.get(address).status_code == 404
        assert client.post(address, {"ziel": org.woelfe.key}).status_code == 404
    assert membership_of(org.walhall_mitglied) == "Walhall"


def test_nur_lesen_und_abschicken_andere_anfragen_sind_nicht_gefunden(org):
    response = client_for(org.walhall_leitung).put(move_address(org.walhall, org.walhall_mitglied))

    assert response.status_code == 404
    assert membership_of(org.walhall_mitglied) == "Walhall"


# ---------- Grenzfall: Leitungsrolle passt nicht zum Ziel (PK-25) ----------


@pytest.mark.rechtematrix("PK-25", "PK-16")
def test_pg1_bruno_verschiebt_bea_nicht_solange_sie_stammesleitung_der_zugvoegel_ist(org):
    give(org.boreas_mitglied, R.TROOP_LEAD, org.zugvoegel)
    before = RoleChange.objects.count()

    shown = move_dialog(move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.walhall))

    # Die Meldung steht im Dialog an der Stelle der Handlung (#186, #65 N4); der Dialog bleibt offen.
    assert shown["notices"] == [PG1_MESSAGE]
    assert shown["title"] == "Verschieben"
    assert roles_of(org.boreas_mitglied) == {(R.MEMBER, "Pfadfinderbund Boreas"), (R.TROOP_LEAD, "Zugvögel")}
    assert RoleChange.objects.count() == before


@pytest.mark.rechtematrix("PK-25")
def test_pg1_mit_zwei_rollen_nennt_die_meldung_beide(org):
    """Risikovariante: Der zweite Wortlaut der Meldung (mehrere Rollen) hat sonst keinen Test."""
    give(org.boreas_mitglied, R.TROOP_LEAD, org.zugvoegel)
    give(org.boreas_mitglied, R.GROUP_LEAD, org.adler)

    shown = move_dialog(move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.walhall))

    assert shown["notices"] == [
        "Bea Boreas ist Gruppenleitung von Sippe Adler und Stammesleitung von Stamm Zugvögel. Diese Rollen passen "
        "nicht zu Stamm Walhall. Sie können zuerst beendet werden."]
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


def test_nach_der_ablehnung_bleibt_die_abgelehnte_organisation_gewaehlt(org):
    """Frage aus der unabhängigen Prüfung, Antwort „Ja, gewählt lassen“: sonst verschöbe ein zweiter Klick woandershin."""
    give(org.boreas_mitglied, R.GROUP_LEAD, org.falken)

    shown = move_dialog(move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.zugvoegel))

    assert shown["notices"] == [
        "Bea Boreas ist Gruppenleitung von Sippe Falken. Diese Rolle passt nicht zu Stamm Zugvögel. "
        "Sie kann zuerst beendet werden."]
    assert [(label, checked) for _name, _value, label, checked in shown["options"]] == [
        ("Stamm Walhall", False), ("Stamm Zugvögel", True)]
    assert membership_of(org.boreas_mitglied) == "Pfadfinderbund Boreas"


@pytest.mark.rechtematrix("PK-25", "PK-19")
def test_pg1_gegenprobe_bea_mit_rolle_in_den_zugvoegeln_darf_dorthin(org):
    give(org.boreas_mitglied, R.TROOP_LEAD, org.zugvoegel)

    response = move(org.bundesleitung, org.boreas, org.boreas_mitglied, org.zugvoegel)

    assert response.status_code == 302
    assert roles_of(org.boreas_mitglied) == {(R.MEMBER, "Zugvögel"), (R.TROOP_LEAD, "Zugvögel")}


# ---------- Gleichzeitige Änderungen ----------


@pytest.mark.django_db(transaction=True)
def test_zwei_leitungen_verschieben_dieselbe_person_gleichzeitig():
    """Genau eine gelingt, die zweite sieht „nicht gefunden“; im Protokoll steht ein Wechsel (entfernt und vergeben)."""
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    give(wilma, R.MEMBER, o.walhall)
    before = RoleChange.objects.count()

    results = _one_after_the_other(lambda: _outcome(lambda: Rights(wanda).move(o.walhall, wilma.key, o.woelfe.key)),
                                   lambda: _outcome(lambda: Rights(willi).move(o.walhall, wilma.key, o.falken.key)))

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    assert roles_of(wilma) == {(R.MEMBER, "Meute Wölfe")}
    assert RoleChange.objects.count() == before + 2


@pytest.mark.django_db(transaction=True)
def test_verschieben_waehrend_eine_andere_leitung_austraegt():
    o = build_org()
    wanda = person("wanda.walhall", "Wanda", "Walhall")
    willi = person("willi.walhall", "Willi", "Walhall")
    wilma = person("wilma.walhall", "Wilma", "Walhall")
    give(wanda, R.TROOP_LEAD, o.walhall)
    give(willi, R.TROOP_LEAD, o.walhall)
    give(wilma, R.MEMBER, o.walhall)
    before = RoleChange.objects.count()

    results = _one_after_the_other(lambda: _outcome(lambda: Rights(willi).expel(o.walhall, wilma.key, "ganz")),
                                   lambda: _outcome(lambda: Rights(wanda).move(o.walhall, wilma.key, o.woelfe.key)))

    assert sorted(results) == ["gelungen", "nicht gefunden"]
    assert roles_of(wilma) == set()
    assert RoleChange.objects.count() == before + 1


# ---------- Was unverändert bleibt ----------


@pytest.mark.rechtematrix("RO-13")
def test_u1_leitung_benennen_lehnt_weiter_mit_der_meldung_aus_89_ab(org):
    response = appoint(org.bundesleitung, org.woelfe, org.adler_kind)

    assert notices(dialog_of(_tree(response))) == [
        "Anton Adler ist Mitglied in Sippe Adler und kann deshalb keine Leitung bei Gruppe Meute Wölfe sein."
    ]


def test_u1_der_wechsel_im_datenmodell_lehnt_weiter_mit_der_meldung_aus_89_ab(org):
    from django.core.exceptions import ValidationError

    membership = Role.objects.get(user=org.falken_leitung, kind=R.MEMBER)
    membership.unit = org.adler
    with pytest.raises(ValidationError) as error:
        membership.save(by=BY)

    assert "Diese Rolle muss zuerst entfernt werden." in str(error.value)


def test_u2_austragen_bleibt_neben_verschieben(org):
    shown = persons_on_page(page_tree(org.bundesleitung, unit_address(org.boreas)))

    assert shown["Bea Boreas"]["buttons"] == ["Verschieben", "Austragen"]
    # Auf einer Gruppe gibt es nichts darunter: nur „Austragen“.
    shown = persons_on_page(page_tree(org.falken_leitung, unit_address(org.falken)))
    assert shown["Flink"]["buttons"] == ["Austragen"]


# ---------- Baustein „Knopf Verschieben“ ----------


@pytest.mark.bausteinkatalog
def test_der_bausteinkatalog_zeigt_den_knopf_verschieben(settings, org):
    settings.BUILDING_BLOCKS_VISIBLE = True
    root = page_tree(org.falke, "/bausteine/")
    names = [_text(_one(_by_tag(entry, "h2")))
             for entry in _all(root, lambda e: e.name == "section" and "a-baustein" in _classes(e))]

    # Seit #92 (N4a) heißt der Baustein „Zart blauer Knopf“; „Verschieben“ bindet ihn weiter ein.
    assert "Zart blauer Knopf" in names
