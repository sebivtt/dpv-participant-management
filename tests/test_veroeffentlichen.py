"""Tests für Entwurf, Zustand und den Schalter „Veröffentlicht“ einer Veranstaltung (#359, VER-07, VER-08, VER-03).

Die Kennungen Z1 bis Z9, ZV1 bis ZV4 und ZG1 bis ZG5 verweisen auf die Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/359#issuecomment-6956474559), die Wortlaute auf den
Text von #359. ZG5 (ohne Skript, nur Tastatur, Handy) prüft der Rauchtest `rauchtests/test_veroeffentlichen.py`.
„Heute“ ist der 05.01.2028; die Tests stellen die Uhr des Servers fest, in der Zeit des Tools (Deutschland).
Personen wie in den Szenarien: Wanda (Stammesleitung Walhall, Veranstaltungsleitung), Fiete (Gruppenleitung Falken,
als weitere Veranstaltungsleitung), Finn (Mitglied Sippe Falken), Vera (Verbandsleitung), Tom (DPV-Veranstaltungsteam),
Max (nur Admin), Otto (Konto ohne Zuordnung). Alle Namen sind erfunden; „Burg Ludwigstein“ ist als Bezeichnung eines
Orts aus dem Zielbild übernommen (#356). VA-08 ist die neue Zeile der Rechtematrix „veröffentlichen, Veröffentlichung
zurücknehmen“ (in den Szenarien noch „VA-07“; diese Kennung hat seit #163 die Adresssuche).
"""

from datetime import date, datetime, time
from pathlib import Path

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from events.models import Event
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_veranstaltungen import LIST, SCRIPT, build_people, edit_address, event_address, event_of

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parent.parent

DRAFT, ANNOUNCED, RUNNING, ENDED = "Entwurf", "Angekündigt", "Läuft", "Beendet"
ONLY_LEADS = "Nur die Leitung sieht die Veranstaltung."
IS_PUBLISHED = "Die Veranstaltung ist veröffentlicht."
PAST = "Der Beginn liegt in der Vergangenheit. Ändere ihn in den Grunddaten, um zu veröffentlichen."
BEGUN = "Die Veranstaltung hat schon begonnen. Die Veröffentlichung lässt sich nicht mehr zurücknehmen."
SWITCH = "Veröffentlicht"
# Nach der Rückfrage bekommt der Schalter wieder den Fokus (Muster „Zurück aus einem Dialog“, #117).
BACK = "#schalter-veroeffentlicht"


def at(monkeypatch, year, month, day, hour=12, minute=0) -> None:
    """Stellt die Uhr des Servers auf diesen Zeitpunkt in der Zeit des Tools (Deutschland)."""
    moment = timezone.make_aware(datetime(year, month, day, hour, minute))
    monkeypatch.setattr(timezone, "now", lambda: moment)


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Heute ist der 05.01.2028, mittags."""
    at(monkeypatch, 2028, 1, 5)


@pytest.fixture
def org():
    return build_people()


@pytest.fixture
def pfingstlager(org):
    """Wandas „Pfingstlager 2028“ vom 02.06.2028, 18:00, bis 05.06.2028, 12:00, als Entwurf."""
    found = event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    found.start_time, found.end_time, found.location = time(18, 0), time(12, 0), "Burg Ludwigstein"
    found.save()
    return found


def published(entry) -> Event:
    """Dieselbe Veranstaltung, veröffentlicht wie nach Z2."""
    Event.objects.filter(pk=entry.pk).update(published=True)
    entry.refresh_from_db()
    return entry


# ---------- Hilfen ----------


def publish_address(entry) -> str:
    return f"{event_address(entry)}veroeffentlichen/"


def withdraw_address(entry) -> str:
    return f"{event_address(entry)}zuruecknehmen/"


def state_section(root):
    """Die Zeile unter dem Kopf der Leitungsseite mit Zustandsmarke, Satz und Schalter."""
    return _one(_all(root, lambda e: "a-zustand" in _classes(e)))


def state_of(root) -> tuple[str, str]:
    """Zustandsmarke und Satz darunter auf der Leitungsseite."""
    found = state_section(root)
    mark = _one(_all(found, lambda e: "a-kennmarke" in _classes(e)))
    sentence = _one(_all(found, lambda e: "a-zustand-satz" in _classes(e)))
    return _visible_text(mark), _visible_text(sentence)


def switch_of(root):
    """Der Schalter „Veröffentlicht“ (Baustein „Schalter mit Rückfrage“)."""
    return _one(_all(state_section(root), lambda e: _attr(e, "role") == "switch"))


def switch(user, entry, client=None) -> dict:
    """Wie der Schalter auf der Leitungsseite steht: an oder aus, gesperrt, wohin er führt und seine Beschriftung."""
    root = _tree((client or client_for(user)).get(event_address(entry)))
    found = switch_of(root)
    label = _one(_all(root, lambda e: _attr(e, "id") == _attr(found, "aria-labelledby")))
    return {"on": _attr(found, "aria-checked") == "true", "locked": _attr(found, "aria-disabled") == "true",
            "href": _attr(found, "href"), "label": _visible_text(label)}


def page_state(user, entry, client=None) -> tuple[str, str]:
    return state_of(_tree((client or client_for(user)).get(event_address(entry))))


def dialog_text(response) -> tuple[str, str, list[str], dict[str, str]]:
    """Titel, Zeile darunter, die Knöpfe unten und wohin sie führen (Link oder Formular)."""
    dialog = dialog_of(_tree(response))
    title = _text(_one(_by_tag(dialog, "h2", id="h-dialog")))
    body = _one(_all(dialog, lambda e: "a-dialog-inhalt" in _classes(e)))
    line = _visible_text(_by_tag(body, "p")[0])
    foot = _one(_all(dialog, lambda e: "a-dialog-fuss" in _classes(e)))
    buttons, targets = [], {}
    for link in _by_tag(foot, "a"):
        buttons.append(_visible_text(link))
        targets[_visible_text(link)] = _attr(link, "href")
    for form in _by_tag(foot, "form"):
        for button in _by_tag(form, "button"):
            label = _visible_text(button)
            buttons.append(label)
            targets[label] = _attr(form, "action")
            colour = "rot" if "btn-gefahr" in _classes(button) else "dunkelblau" if "btn-primary" in _classes(button) else ""
            targets[f"{label} ({colour})"] = _attr(form, "action")
    return title, line, buttons, targets


def dialog_errors(response) -> list[str]:
    dialog = dialog_of(_tree(response))
    return [_visible_text(entry) for entry in _all(dialog, lambda e: "ist-fehler" in _classes(e))]


def list_rows(user) -> dict[str, dict]:
    """Die Zeilen unter „Von mir geleitet“: je Name die Marke und ob gestrichelt (Entwurf) oder grau."""
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    found = {}
    for row in _all(section, lambda e: "a-va-zeile" in _classes(e) and e.name == "li"):
        name = _visible_text(_one(_by_tag(row, "a")))
        marks = _all(row, lambda e: "a-kennmarke" in _classes(e))
        found[name] = {"mark": _visible_text(_one(marks)) if marks else None,
                       "dashed": "ist-entwurf" in _classes(row), "grey": "ist-grau" in _classes(row)}
    return found


def confirm_publish(user, entry, client=None):
    return (client or client_for(user)).post(publish_address(entry))


def confirm_withdraw(user, entry, client=None):
    return (client or client_for(user)).post(withdraw_address(entry))


# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-02")
def test_z1_neu_ist_entwurf_nur_die_leitung_sieht_ihn(org, pfingstlager):
    assert pfingstlager.published is False
    assert page_state(org.wanda, pfingstlager) == (DRAFT, ONLY_LEADS)
    shown = switch(org.wanda, pfingstlager)
    assert shown == {"on": False, "locked": False, "href": publish_address(pfingstlager), "label": SWITCH}
    assert list_rows(org.wanda)["Pfingstlager 2028"] == {"mark": DRAFT, "dashed": True, "grey": False}


def test_z1_auch_ueber_das_anlegen_in_schritten_entsteht_ein_entwurf(org):
    client = client_for(org.wanda)
    root = _tree(client.get("/veranstaltungen/erstellen/"))
    form = _one(_all(root, lambda e: e.name == "form" and _by_tag(e, "input", name="creation_key")))
    key = _attr(_one(_by_tag(form, "input", name="creation_key")), "value")
    client.post("/veranstaltungen/erstellen/", {"name": "Sommerfahrt 2028", "start": "2028-07-20", "start_time": "18:00",
                                                 "end": "2028-07-30", "end_time": "12:00", "creation_key": key})
    entry = Event.objects.get(name="Sommerfahrt 2028")
    client.post(f"{event_address(entry)}anlegen/zusammenfassung/")

    entry.refresh_from_db()
    assert entry.published is False
    assert page_state(org.wanda, entry, client=client) == (DRAFT, ONLY_LEADS)


@pytest.mark.rechtematrix("VA-08")
def test_z2_wanda_veroeffentlicht_das_pfingstlager_nach_der_rueckfrage(org, pfingstlager):
    client = client_for(org.wanda)

    asked = client.get(publish_address(pfingstlager))
    assert asked.status_code == 200
    title, line, buttons, targets = dialog_text(asked)
    assert title == "Pfingstlager 2028 veröffentlichen?"
    assert line == "Danach sieht der Teilnahmekreis die Einladung."
    assert buttons == ["Abbrechen", "Veröffentlichen"]
    assert targets["Abbrechen"] == event_address(pfingstlager) + BACK
    assert targets["Veröffentlichen (dunkelblau)"] == publish_address(pfingstlager)

    done = confirm_publish(org.wanda, pfingstlager, client=client)
    assert done.status_code == 302 and done.url == event_address(pfingstlager) + BACK
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True
    after = client.get(done.url)
    assert short_notices(after) == ["Pfingstlager 2028 ist veröffentlicht."]
    assert state_of(_tree(after)) == (ANNOUNCED, IS_PUBLISHED)
    assert switch(org.wanda, pfingstlager)["on"] is True
    assert list_rows(org.wanda)["Pfingstlager 2028"] == {"mark": ANNOUNCED, "dashed": False, "grey": True}


def test_z3_abbrechen_in_der_rueckfrage_laesst_den_entwurf(org, pfingstlager):
    client = client_for(org.wanda)
    _title, _line, _buttons, targets = dialog_text(client.get(publish_address(pfingstlager)))

    back = client.get(targets["Abbrechen"])

    assert back.status_code == 200
    assert state_of(_tree(back)) == (DRAFT, ONLY_LEADS)
    assert switch(org.wanda, pfingstlager, client=client)["on"] is False
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False


@pytest.mark.rechtematrix("VA-08")
def test_z4_wanda_nimmt_die_veroeffentlichung_zurueck(org, pfingstlager):
    published(pfingstlager)
    client = client_for(org.wanda)
    assert switch(org.wanda, pfingstlager, client=client)["href"] == withdraw_address(pfingstlager)

    title, line, buttons, targets = dialog_text(client.get(withdraw_address(pfingstlager)))
    assert title == "Veröffentlichung von Pfingstlager 2028 zurücknehmen?"
    assert line == "Danach sieht nur noch die Leitung die Veranstaltung; beim Teilnahmekreis verschwindet die Einladung."
    assert buttons == ["Abbrechen", "Zurücknehmen"]
    assert targets["Zurücknehmen (rot)"] == withdraw_address(pfingstlager)

    done = confirm_withdraw(org.wanda, pfingstlager, client=client)
    assert done.status_code == 302 and done.url == event_address(pfingstlager) + BACK
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False
    after = client.get(done.url)
    assert short_notices(after) == ["Die Veröffentlichung von Pfingstlager 2028 ist zurückgenommen."]
    assert state_of(_tree(after)) == (DRAFT, ONLY_LEADS)

    # Später veröffentlicht sie erneut (Beispiel im Text von #359).
    assert confirm_publish(org.wanda, pfingstlager, client=client).status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True


@pytest.mark.rechtematrix("VA-08")
def test_z5_fiete_als_mitleitung_veroeffentlicht_und_nimmt_zurueck(org, pfingstlager):
    pfingstlager.leads.add(org.fiete)
    client = client_for(org.fiete)

    assert page_state(org.fiete, pfingstlager, client=client) == (DRAFT, ONLY_LEADS)
    assert confirm_publish(org.fiete, pfingstlager, client=client).status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True
    assert confirm_withdraw(org.fiete, pfingstlager, client=client).status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False


def test_z6_ab_beginn_laeuft_die_veranstaltung(org, pfingstlager, monkeypatch):
    published(pfingstlager)

    at(monkeypatch, 2028, 6, 2, 17, 59)
    assert page_state(org.wanda, pfingstlager) == (ANNOUNCED, IS_PUBLISHED)

    at(monkeypatch, 2028, 6, 2, 18, 0)
    assert page_state(org.wanda, pfingstlager) == (RUNNING, "Die Veranstaltung läuft bis 05.06.2028, 12:00.")
    assert list_rows(org.wanda)["Pfingstlager 2028"] == {"mark": RUNNING, "dashed": False, "grey": False}


def test_z7_ab_ende_ist_sie_beendet(org, pfingstlager, monkeypatch):
    published(pfingstlager)

    at(monkeypatch, 2028, 6, 5, 11, 59)
    assert page_state(org.wanda, pfingstlager)[0] == RUNNING

    at(monkeypatch, 2028, 6, 5, 12, 0)
    assert page_state(org.wanda, pfingstlager) == (ENDED, "Die Veranstaltung ist am 05.06.2028 zu Ende gegangen.")
    assert list_rows(org.wanda)["Pfingstlager 2028"] == {"mark": ENDED, "dashed": False, "grey": True}


def test_z8_ohne_uhrzeit_gilt_der_ganze_tag(org, monkeypatch):
    aktion = published(event_of(org.wanda, "Sippenaktion Falken", date(2028, 1, 21), date(2028, 1, 23)))

    at(monkeypatch, 2028, 1, 20, 23, 59)
    assert page_state(org.wanda, aktion)[0] == ANNOUNCED
    at(monkeypatch, 2028, 1, 21, 0, 0)
    assert page_state(org.wanda, aktion) == (RUNNING, "Die Veranstaltung läuft bis 23.01.2028.")
    at(monkeypatch, 2028, 1, 23, 23, 59)
    assert page_state(org.wanda, aktion)[0] == RUNNING
    at(monkeypatch, 2028, 1, 24, 0, 0)
    assert page_state(org.wanda, aktion) == (ENDED, "Die Veranstaltung ist am 23.01.2028 zu Ende gegangen.")


@pytest.mark.rechtematrix("VA-08")
def test_z9_beginn_heute_ist_erlaubt_auch_nach_der_uhrzeit(org, monkeypatch):
    at(monkeypatch, 2028, 1, 5, 14, 0)
    treffen = event_of(org.wanda, "Leitungstreffen Walhall", date(2028, 1, 5), date(2028, 1, 7))
    treffen.start_time = time(10, 0)
    treffen.save()
    assert switch(org.wanda, treffen)["locked"] is False

    assert confirm_publish(org.wanda, treffen).status_code == 302

    treffen.refresh_from_db()
    assert treffen.published is True
    assert page_state(org.wanda, treffen)[0] == RUNNING


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-08")
def test_zv1_beginn_vorbei_schalter_gesperrt_und_der_server_lehnt_ab(org):
    winterfahrt = event_of(org.wanda, "Winterfahrt 2027", date(2027, 12, 27), date(2027, 12, 30))
    client = client_for(org.wanda)

    assert page_state(org.wanda, winterfahrt, client=client) == (DRAFT, PAST)
    shown = switch(org.wanda, winterfahrt, client=client)
    assert (shown["on"], shown["locked"], shown["href"]) == (False, True, None)

    refused = confirm_publish(org.wanda, winterfahrt, client=client)

    assert refused.status_code == 200
    assert dialog_errors(refused) == [PAST]
    winterfahrt.refresh_from_db()
    assert winterfahrt.published is False


@pytest.mark.rechtematrix("VA-08")
def test_zv2_ab_beginn_laesst_sich_nicht_zuruecknehmen(org, pfingstlager, monkeypatch):
    published(pfingstlager)
    for moment in ((2028, 6, 2, 18, 0), (2028, 6, 6, 9, 0)):
        at(monkeypatch, *moment)
        client = client_for(org.wanda)
        shown = switch(org.wanda, pfingstlager, client=client)
        assert (shown["on"], shown["locked"], shown["href"]) == (True, True, None), moment

        refused = confirm_withdraw(org.wanda, pfingstlager, client=client)

        assert refused.status_code == 200
        assert dialog_errors(refused) == [BEGUN]
        pfingstlager.refresh_from_db()
        assert pfingstlager.published is True


@pytest.mark.rechtematrix("VA-03", "VA-08")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/veroeffentlichen/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/zuruecknehmen/")
def test_zv3_niemand_ausser_der_leitung_veroeffentlicht_oder_nimmt_zurueck(org, pfingstlager):
    draft = event_of(org.wanda, "Stammesthing Walhall", date(2028, 1, 14), date(2028, 1, 16))
    published(pfingstlager)
    for user in (org.finn, org.fiete, org.vera, org.tom, org.otto, org.max, org.bruno, org.rita):
        client = client_for(user)
        for address in (publish_address(draft), withdraw_address(pfingstlager)):
            assert_like_missing(user, address)
            assert client.get(address, **SCRIPT).status_code == 404
            assert client.post(address, **SCRIPT).status_code == 404

    draft.refresh_from_db()
    pfingstlager.refresh_from_db()
    assert (draft.published, pfingstlager.published) == (False, True)


@pytest.mark.rechtematrix("VA-03", "VA-08")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/veroeffentlichen/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/zuruecknehmen/")
def test_zv3_auch_im_support_zugang_fuer_walhall_aendert_max_nichts(org, pfingstlager):
    client = client_for(org.max)
    assert client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    assert client.post(publish_address(pfingstlager)).status_code == 404
    assert client.post(publish_address(pfingstlager), **SCRIPT).status_code == 404
    assert_like_missing(org.max, publish_address(pfingstlager))
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False

    published(pfingstlager)
    assert client.post(withdraw_address(pfingstlager)).status_code == 404
    assert_like_missing(org.max, withdraw_address(pfingstlager))
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/veroeffentlichen/")
def test_zv3_fiete_tauscht_die_kennung_gegen_die_des_pfingstlagers_und_findet_nichts(org, pfingstlager):
    own = event_of(org.fiete, "Sippenfahrt Falken", date(2028, 8, 1), date(2028, 8, 5))
    client = client_for(org.fiete)
    assert client.get(publish_address(own)).status_code == 200

    response = client.post(publish_address(pfingstlager))

    assert response.status_code == 404
    assert_like_missing(org.fiete, publish_address(pfingstlager))
    pfingstlager.refresh_from_db()
    own.refresh_from_db()
    assert (pfingstlager.published, own.published) == (False, False)


@pytest.mark.rechtematrix("VA-03")
def test_zv4_finn_sieht_den_entwurf_weder_in_der_liste_noch_ueber_die_adresse(org, pfingstlager):
    client = client_for(org.finn)

    assert "Pfingstlager" not in client.get(LIST).content.decode()
    assert_like_missing(org.finn, event_address(pfingstlager))


# ---------- Grenzfälle ----------


@pytest.mark.django_db(transaction=True)
def test_zg1_veranstaltungen_aus_p2_werden_beim_umbau_entwuerfe(org):
    before = [("events", "0005_adresse")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    old = executor.loader.project_state(before).apps.get_model("events", "Event")
    old.objects.create(name="Probelager 2027", start=date(2027, 5, 15), end=date(2027, 5, 17))
    old.objects.create(name="Pfingstlager 2028", start=date(2028, 6, 2), end=date(2028, 6, 5))

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert sorted(Event.objects.values_list("name", "published")) == [("Pfingstlager 2028", False),
                                                                      ("Probelager 2027", False)]
    assert {entry.status for entry in Event.objects.all()} == {Event.Status.DRAFT}


def test_zg2_alter_entwurf_bleibt_entwurf_bis_der_beginn_in_der_zukunft_liegt(org):
    winterfahrt = event_of(org.wanda, "Winterfahrt 2027", date(2027, 12, 27), date(2027, 12, 30))
    client = client_for(org.wanda)
    assert page_state(org.wanda, winterfahrt, client=client) == (DRAFT, PAST)
    assert switch(org.wanda, winterfahrt, client=client)["locked"] is True
    assert list_rows(org.wanda)["Winterfahrt 2027"] == {"mark": DRAFT, "dashed": True, "grey": False}

    saved = client.post(edit_address(winterfahrt), {"name": "Winterfahrt 2027", "start": "2028-12-27",
                                                     "start_time": "", "end": "2028-12-30", "end_time": "",
                                                     "location": "", "version": str(winterfahrt.version)})
    assert saved.status_code == 302

    assert switch(org.wanda, winterfahrt, client=client)["locked"] is False
    assert confirm_publish(org.wanda, winterfahrt, client=client).status_code == 302
    winterfahrt.refresh_from_db()
    assert winterfahrt.published is True


def test_zg2_speichern_ueber_den_stift_aendert_veroeffentlicht_nicht(org, pfingstlager):
    published(pfingstlager)
    client = client_for(org.wanda)

    saved = client.post(edit_address(pfingstlager), {"name": "Pfingstlager 2028", "start": "2028-06-02",
                                                      "start_time": "18:00", "end": "2028-06-05", "end_time": "12:00",
                                                      "location": "Burg Ludwigstein", "published": "",
                                                      "version": str(pfingstlager.version)})

    assert saved.status_code == 302
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True


def test_zg3_zwei_leitungen_gleichzeitig_veroeffentlichen(org, pfingstlager):
    pfingstlager.leads.add(org.fiete)
    wanda, fiete = client_for(org.wanda), client_for(org.fiete)
    assert fiete.get(publish_address(pfingstlager)).status_code == 200
    assert confirm_publish(org.wanda, pfingstlager, client=wanda).status_code == 302

    again = confirm_publish(org.fiete, pfingstlager, client=fiete)

    assert again.status_code == 302
    assert short_notices(fiete.get(again.url)) == ["Pfingstlager 2028 ist schon veröffentlicht."]
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is True


def test_zg3_zwei_leitungen_gleichzeitig_zuruecknehmen(org, pfingstlager):
    published(pfingstlager)
    pfingstlager.leads.add(org.fiete)
    wanda, fiete = client_for(org.wanda), client_for(org.fiete)
    assert fiete.get(withdraw_address(pfingstlager)).status_code == 200
    assert confirm_withdraw(org.wanda, pfingstlager, client=wanda).status_code == 302

    again = confirm_withdraw(org.fiete, pfingstlager, client=fiete)

    assert again.status_code == 302
    assert short_notices(fiete.get(again.url)) == ["Pfingstlager 2028 ist schon nicht mehr veröffentlicht."]
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False


def test_zg4_seite_ueber_mitternacht_offen_veroeffentlichen_schlaegt_fehl(org, monkeypatch):
    heute_lager = event_of(org.wanda, "Tagesaktion Walhall", date(2028, 1, 5), date(2028, 1, 5))
    at(monkeypatch, 2028, 1, 5, 23, 50)
    client = client_for(org.wanda)
    assert client.get(publish_address(heute_lager)).status_code == 200

    at(monkeypatch, 2028, 1, 6, 0, 1)
    refused = confirm_publish(org.wanda, heute_lager, client=client)

    assert refused.status_code == 200
    assert dialog_errors(refused) == [PAST]
    heute_lager.refresh_from_db()
    assert heute_lager.published is False


def test_zg4_zuruecknehmen_nach_dem_beginn_schlaegt_fehl(org, monkeypatch):
    abend = published(event_of(org.wanda, "Singeabend Walhall", date(2028, 1, 5), date(2028, 1, 5)))
    abend.start_time = time(18, 0)
    abend.save()
    at(monkeypatch, 2028, 1, 5, 17, 59)
    client = client_for(org.wanda)
    assert client.get(withdraw_address(abend)).status_code == 200

    at(monkeypatch, 2028, 1, 5, 18, 0)
    refused = confirm_withdraw(org.wanda, abend, client=client)

    assert refused.status_code == 200
    assert dialog_errors(refused) == [BEGUN]
    abend.refresh_from_db()
    assert abend.published is True


def test_andere_anfragen_als_lesen_und_abschicken_sind_nicht_gefunden(org, pfingstlager):
    client = client_for(org.wanda)
    for address in (publish_address(pfingstlager), withdraw_address(pfingstlager)):
        assert client.put(address).status_code == 404
        assert client.delete(address).status_code == 404
    pfingstlager.refresh_from_db()
    assert pfingstlager.published is False


def test_die_liste_waechst_nicht_mit_den_abfragen_auch_mit_zustaenden(org):
    event_of(org.wanda, "Erste", date(2028, 2, 1), date(2028, 2, 2))
    client = client_for(org.wanda)
    client.get(LIST)
    with CaptureQueriesContext(connection) as one:
        client.get(LIST)
    for number in range(9):
        published(event_of(org.wanda, f"Weitere {number}", date(2028, 3, 1 + number), date(2028, 3, 2 + number)))
    with CaptureQueriesContext(connection) as ten:
        client.get(LIST)
    assert len(ten) <= len(one)


# ---------- Bausteine und Doku ----------


@pytest.mark.bausteinkatalog
def test_zustandsmarke_und_schalter_mit_rueckfrage_stehen_im_bausteinkatalog(org):
    root = page_tree(org.wanda, "/bausteine/")
    marks = _one(_by_tag(root, "section", aria_labelledby="h-kennmarke"))
    shown = {_visible_text(mark): _classes(mark) for mark in _all(marks, lambda e: "a-kennmarke" in _classes(e))}
    for word, kind in ((DRAFT, "ist-entwurf"), (ANNOUNCED, "ist-angekuendigt"), (RUNNING, "ist-laeuft"),
                       (ENDED, "ist-beendet")):
        assert kind in shown[word], word
    for word in (DRAFT, ANNOUNCED, RUNNING, ENDED):
        mark = next(m for m in _all(marks, lambda e: "a-kennmarke" in _classes(e)) if _visible_text(m) == word)
        assert _by_tag(mark, "svg"), f"„{word}“ ohne Symbol"
    block = _one(_by_tag(root, "section", aria_labelledby="h-schalterrueckfrage"))
    switches = _all(block, lambda e: _attr(e, "role") == "switch")
    assert {(_attr(s, "aria-checked"), _attr(s, "aria-disabled")) for s in switches} >= {("false", None),
                                                                                        ("true", "true")}
    rows = _one(_by_tag(root, "section", aria_labelledby="h-veranstaltungszeile"))
    assert any("ist-entwurf" in _classes(row) for row in _all(rows, lambda e: "a-va-zeile" in _classes(e)))


def test_gestaltung_nennt_die_endgueltigen_zustaende():
    text = (ROOT / "docs" / "gestaltung.md").read_text(encoding="utf-8")
    assert "endgültig in #29" not in text
    assert "Schalter mit Rückfrage" in text


def test_lebenszyklus_steht_als_diagramm_in_den_anforderungen():
    text = (ROOT / "docs" / "anforderungen.md").read_text(encoding="utf-8")
    assert "embedded content" not in text
    assert "```mermaid" in text
    for label in ("veröffentlichen", "Veröffentlichung zurücknehmen",
                  "veröffentlichen ohne oder nach dem Anmeldestart"):
        assert label in text, label
    assert "Der Schalter „sichtbar“ aus VER-08 heißt im Tool „Veröffentlicht“ (#356, E2)." in text
    skill = (ROOT / ".claude" / "skills" / "grill-me" / "SKILL.md").read_text(encoding="utf-8")
    assert "Fehlendes Diagramm zum Lebenszyklus" not in skill
