"""Tests für die Fristen einer Veranstaltung: Anmeldestart, Anmeldeschluss, Änderungsschluss (#360, VER-09, VER-08).

Die Kennungen F1 bis F10, FV1 und FG1 bis FG9 verweisen auf die Szenarien vom 17.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/360#issuecomment-6956886808), die Wortlaute auf den
Text von #360. FG9 (ohne Skript, nur Tastatur, am Handy) prüft der Rauchtest `rauchtests/test_fristen.py`.
„Heute“ ist der 05.01.2028; die Tests stellen die Uhr des Servers fest, in der Zeit des Tools (Deutschland), auch an den
Grenzen (Tag davor 23:59:59, genau 0:00) und in der Sommerzeit (FG5; Abschlusskriterium P3 „Fristen-Tests grün“).
Personen wie in den Szenarien: Wanda (Stammesleitung Walhall, Veranstaltungsleitung), Fiete (Gruppenleitung Falken,
als weitere Veranstaltungsleitung), Finn (Mitglied Sippe Falken), Vera (Verbandsleitung), Tom (DPV-Veranstaltungsteam),
Max (nur Admin), Otto (Konto ohne Zuordnung). Alle Namen sind erfunden; „Burg Ludwigstein“ ist als Bezeichnung eines
Orts aus dem Zielbild übernommen (#356).
"""

from datetime import UTC, date, datetime, time

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from access.rights import Rights
from events.models import Event
from tests.test_benennen import dialog_of, short_notices
from tests.test_gestaltung import _all, _attr, _by_tag, _classes, _one, _text, _tree, _visible_text
from tests.test_grunddaten import _one_after_the_other
from tests.test_nicht_gefunden import assert_like_missing
from tests.test_organisation import client_for, page_tree, unit_address
from tests.test_veranstaltungen import LIST, SCRIPT, build_people, edit_address, event_address, event_of, field_errors
from tests.test_veroeffentlichen import at, page_state, publish_address, published

pytestmark = pytest.mark.django_db

DRAFT, ANNOUNCED, OPEN, CLOSED, RUNNING = "Entwurf", "Angekündigt", "Anmeldung offen", "Geschlossen", "Läuft"
IS_PUBLISHED = "Die Veranstaltung ist veröffentlicht."
ONLY_LEADS = "Nur die Leitung sieht die Veranstaltung."
SAVED = "Die Fristen von Pfingstlager 2028 sind gespeichert."
CHANGED = "Pfingstlager 2028 wurde inzwischen geändert. Bitte prüfe die Angaben und speichere erneut."
FIELDS = ("registration_opens", "registration_closes", "changes_close")
PFINGSTEN = {"registration_opens": date(2028, 2, 1), "registration_closes": date(2028, 4, 30),
             "changes_close": date(2028, 5, 7)}


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    """Heute ist der 05.01.2028, mittags."""
    at(monkeypatch, 2028, 1, 5)


@pytest.fixture
def org():
    return build_people()


def lager(org, **deadlines) -> Event:
    """Wandas „Pfingstlager 2028“ vom 02.06.2028, 18:00, bis 05.06.2028, 12:00, mit diesen Fristen, als Entwurf."""
    found = event_of(org.wanda, "Pfingstlager 2028", date(2028, 6, 2), date(2028, 6, 5))
    found.start_time, found.end_time, found.location = time(18, 0), time(12, 0), "Burg Ludwigstein"
    for name, value in deadlines.items():
        setattr(found, name, value)
    found.save()
    return found


@pytest.fixture
def pfingstlager(org):
    """Das Pfingstlager mit Anmeldestart 01.02.2028, Anmeldeschluss 30.04.2028 und Änderungsschluss 07.05.2028."""
    return lager(org, **PFINGSTEN)


def entwurf_im_ablauf(org, **deadlines) -> Event:
    """Ein Entwurf, den Wanda gerade in Schritten anlegt (#380), wie nach Schritt 2."""
    found = lager(org, **deadlines)
    found.creating_by = org.wanda
    found.save()
    return found


# ---------- Hilfen ----------


def step_address(entry) -> str:
    """Schritt 3 „Anmeldung“ beim Anlegen."""
    return f"{event_address(entry)}anlegen/anmeldung/"


def summary_address(entry) -> str:
    return f"{event_address(entry)}anlegen/zusammenfassung/"


def dialog_address(entry) -> str:
    """Der Dialog des Stifts der Kachel „Anmeldung“."""
    return f"{event_address(entry)}anmeldung/"


def shown(entry) -> dict[str, str]:
    """Die Fristen, wie das Formular sie zeigt, mit dem Stand beim Öffnen."""
    values = {name: getattr(entry, name).isoformat() if getattr(entry, name) else "" for name in FIELDS}
    return {**values, "deadlines_version": str(entry.deadlines_version)}


def save_dialog(client, entry, **values):
    """Ändert im Dialog des Stifts „Anmeldung“ die Fristen und klickt auf „Speichern“."""
    return client.post(dialog_address(entry), {**shown(entry), **values})


def save_step(client, entry, **values):
    """Trägt in Schritt 3 die Fristen ein und klickt auf „Weiter“."""
    return client.post(step_address(entry), {**shown(entry), **values})


def stored(entry) -> tuple:
    entry.refresh_from_db()
    return tuple(getattr(entry, name) for name in FIELDS)


def deadline_tile(root):
    """Die Kachel „Anmeldung“ der Leitungsseite."""
    return _one(_by_tag(root, "section", aria_labelledby="h-anmeldung"))


def timeline(root) -> list[str]:
    """Die Einträge der Zeitleiste in der Kachel „Anmeldung“, je der sichtbare Text."""
    found = _one(_all(deadline_tile(root), lambda e: "a-zeitleiste" in _classes(e)))
    return [_visible_text(entry) for entry in _by_tag(found, "li")]


def today_entry(root):
    """Der Eintrag „Heute“ der Zeitleiste."""
    return _one(_all(deadline_tile(root), lambda e: e.name == "li" and "ist-heute" in _classes(e)))


def tile_of(user, entry, client=None) -> list[str]:
    return timeline(_tree((client or client_for(user)).get(event_address(entry))))


def notes(user) -> dict[str, tuple[str | None, str | None]]:
    """Die Zeilen unter „Von mir geleitet“: je Name die Marke und die Frist klein darunter."""
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    found = {}
    for row in _all(section, lambda e: "a-va-zeile" in _classes(e) and e.name == "li"):
        name = _visible_text(_one(_by_tag(row, "a")))
        mark = _visible_text(_one(_all(row, lambda e: "a-kennmarke" in _classes(e))))
        note = _all(row, lambda e: "a-va-zeile-frist" in _classes(e))
        found[name] = (mark, _visible_text(_one(note)) if note else None)
    return found


def grey(user, name) -> bool:
    section = _one(_by_tag(page_tree(user, LIST), "section", aria_labelledby="h-veranstaltungen"))
    for row in _all(section, lambda e: "a-va-zeile" in _classes(e) and e.name == "li"):
        if _visible_text(_one(_by_tag(row, "a"))) == name:
            return "ist-grau" in _classes(row)
    raise AssertionError(name)


def publish_lines(user, entry) -> list[str]:
    """Die Sätze der Rückfrage „… veröffentlichen?“."""
    dialog = dialog_of(_tree(client_for(user).get(publish_address(entry))))
    body = _one(_all(dialog, lambda e: "a-dialog-inhalt" in _classes(e)))
    return [_visible_text(line) for line in _by_tag(body, "p")]




# ---------- Erlaubt ----------


@pytest.mark.rechtematrix("VA-02", "VA-06")
def test_f1_wanda_traegt_in_schritt_3_die_fristen_ein(org):
    entwurf = entwurf_im_ablauf(org)
    client = client_for(org.wanda)

    # Schritt 2 „Weiter“ führt zu Schritt 3 „Anmeldung“ mit der Gruppe „Fristen“.
    assert client.post(f"{event_address(entwurf)}anlegen/einladungstext/",
                       {"invitation_text": "", "invitation_version": "1"}).url == step_address(entwurf)
    step = _tree(client.get(step_address(entwurf)))
    steps = [_visible_text(entry) for entry in _all(step, lambda e: "a-schritt" in _classes(e) and e.name == "li")]
    assert steps == ["Schritt 1 Grunddaten", "Schritt 2 Einladungstext", "Schritt 3 Anmeldung",
                     "Schritt 4 Zusammenfassung"]
    assert "Fristen" in [_text(heading) for heading in _by_tag(step, "h2")]
    labels = [_text(label) for label in _by_tag(step, "label")]
    assert labels == ["Anmeldestart", "Anmeldeschluss", "Änderungsschluss"]

    done = save_step(client, entwurf, registration_opens="2028-02-01", registration_closes="2028-04-30",
                     changes_close="2028-05-07")

    assert done.status_code == 302 and done.url == summary_address(entwurf)
    assert stored(entwurf) == tuple(PFINGSTEN.values())
    summary = _tree(client.get(summary_address(entwurf)))
    # Seit der Vorschau (Sebastian, 27.11.2026) zeigt die Zusammenfassung die Fristen als Zeitleiste wie die Kachel
    # der Leitungsseite, statt „Anmeldung 01.02.2028 bis 30.04.2028“ und „Änderungsschluss 07.05.2028“.
    assert timeline(summary) == ["Heute 05.01.2028", "Anmeldestart Di, 01.02.2028 · in 27 Tagen",
                                 "Anmeldeschluss So, 30.04.2028", "Änderungsschluss So, 07.05.2028 · bis dahin Nachmelden"]
    pencil = _one(_all(_one(_by_tag(summary, "section", aria_labelledby="h-anmeldung")),
                       lambda e: "a-stift" in _classes(e)))
    assert _attr(pencil, "href") == step_address(entwurf)
    # „Zurück“ in der Zusammenfassung führt zu Schritt 3.
    back = _one([link for link in _by_tag(summary, "a") if _visible_text(link) == "Zurück"])
    assert _attr(back, "href") == step_address(entwurf)

    client.post(summary_address(entwurf))
    page = _tree(client.get(event_address(entwurf)))
    assert timeline(page) == ["Heute 05.01.2028", "Anmeldestart Di, 01.02.2028 · in 27 Tagen",
                              "Anmeldeschluss So, 30.04.2028", "Änderungsschluss So, 07.05.2028 · bis dahin Nachmelden"]
    # „Heute“ sonnengelb, ohne Text auf dem Gelb (#356 N4): Der Punkt ist leer.
    assert _visible_text(_one(_all(today_entry(page), lambda e: "a-zeitleiste-punkt" in _classes(e)))) == ""
    # Im Entwurf ändern Fristen den Zustand nicht.
    assert page_state(org.wanda, entwurf) == (DRAFT, ONLY_LEADS)


def test_f1_in_der_zusammenfassung_steht_anmeldung_neben_grunddaten(org):
    """Vorschau, Sebastian, 27.11.2026 („Neben Grunddaten“): wie auf der Leitungsseite; darunter der Einladungstext."""
    entwurf = entwurf_im_ablauf(org, **PFINGSTEN)
    root = _tree(client_for(org.wanda).get(summary_address(entwurf)))
    tiles = _one(_all(root, lambda e: "a-kacheln" in _classes(e)))

    assert [_attr(section, "aria-labelledby") for section in _by_tag(tiles, "section")] == ["h-grunddaten",
                                                                                          "h-anmeldung"]
    sections = [_attr(section, "aria-labelledby") for section in _by_tag(root, "section")]
    assert sections.index("h-anmeldung") < sections.index("h-einladungstext")


def test_f1_zurueck_in_schritt_3_fuehrt_zu_schritt_2_und_abbrechen_zur_rueckfrage(org):
    entwurf = entwurf_im_ablauf(org)
    root = _tree(client_for(org.wanda).get(step_address(entwurf)))
    links = {_visible_text(link): _attr(link, "href") for link in _by_tag(root, "a")}

    assert links["Zurück"] == f"{event_address(entwurf)}anlegen/einladungstext/"
    assert links["Abbrechen"] == f"{event_address(entwurf)}anlegen/abbrechen/"


def test_f2_ablauf_vom_veroeffentlichen_bis_zum_beginn(org, pfingstlager, monkeypatch):
    assert publish_lines(org.wanda, pfingstlager) == [
        "Danach sieht der Teilnahmekreis die Einladung.", "Die Anmeldung öffnet am 01.02.2028 und läuft bis 30.04.2028."]
    assert client_for(org.wanda).post(publish_address(pfingstlager)).status_code == 302

    at(monkeypatch, 2028, 1, 31, 23, 59)
    assert page_state(org.wanda, pfingstlager) == (ANNOUNCED, f"{IS_PUBLISHED} Die Anmeldung öffnet am 01.02.2028.")
    assert notes(org.wanda)["Pfingstlager 2028"] == (ANNOUNCED, "Anmeldung ab 01.02.2028")
    assert grey(org.wanda, "Pfingstlager 2028") is True

    at(monkeypatch, 2028, 2, 1, 0, 0)
    assert page_state(org.wanda, pfingstlager) == (OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis 30.04.2028.")
    assert notes(org.wanda)["Pfingstlager 2028"] == (OPEN, "bis 30.04.2028")
    assert grey(org.wanda, "Pfingstlager 2028") is False

    at(monkeypatch, 2028, 5, 1, 0, 0)
    assert page_state(org.wanda, pfingstlager) == (
        CLOSED, f"{IS_PUBLISHED} Die Anmeldung ist geschlossen. Nachmelden und Ändern bis 07.05.2028.")
    assert notes(org.wanda)["Pfingstlager 2028"] == (CLOSED, "Nachmelden bis 07.05.2028")
    assert grey(org.wanda, "Pfingstlager 2028") is False

    at(monkeypatch, 2028, 5, 8, 0, 0)
    assert page_state(org.wanda, pfingstlager) == (CLOSED, f"{IS_PUBLISHED} Die Anmeldung ist geschlossen.")
    assert notes(org.wanda)["Pfingstlager 2028"] == (CLOSED, None)

    at(monkeypatch, 2028, 6, 2, 18, 0)
    assert page_state(org.wanda, pfingstlager)[0] == RUNNING
    assert notes(org.wanda)["Pfingstlager 2028"] == (RUNNING, None)


def test_f2_die_naechste_frist_zaehlt_die_tage_morgen_und_heute(org, pfingstlager, monkeypatch):
    published(pfingstlager)

    at(monkeypatch, 2028, 1, 31, 9, 0)
    assert tile_of(org.wanda, pfingstlager)[:2] == ["Heute 31.01.2028", "Anmeldestart Di, 01.02.2028 · morgen"]

    at(monkeypatch, 2028, 4, 30, 9, 0)
    assert tile_of(org.wanda, pfingstlager) == [
        "Anmeldestart Di, 01.02.2028", "Heute 30.04.2028", "Anmeldeschluss So, 30.04.2028 · heute",
        "Änderungsschluss So, 07.05.2028 · bis dahin Nachmelden"]

    at(monkeypatch, 2028, 5, 2, 9, 0)
    assert tile_of(org.wanda, pfingstlager) == [
        "Anmeldestart Di, 01.02.2028", "Anmeldeschluss So, 30.04.2028", "Heute 02.05.2028",
        "Änderungsschluss So, 07.05.2028 · in 5 Tagen · bis dahin Nachmelden"]


def test_f2_vergangene_fristen_sind_in_der_zeitleiste_als_vorbei_markiert(org, pfingstlager, monkeypatch):
    """Vorschau, Sebastian, 27.11.2026: Vorbei und bevorstehend sind in der Zeitleiste zu unterscheiden; eine vergangene
    Frist hat einen grünen Punkt mit Haken, Vorleseprogramme hören „vorbei“."""
    published(pfingstlager)
    at(monkeypatch, 2028, 5, 2, 9, 0)
    root = _tree(client_for(org.wanda).get(event_address(pfingstlager)))
    found = _one(_all(deadline_tile(root), lambda e: "a-zeitleiste" in _classes(e)))

    past = [("ist-vorbei" in _classes(entry), [_text(note) for note in _all(entry, lambda e: "sr-nur" in _classes(e))])
            for entry in _by_tag(found, "li")]
    assert past == [(True, ["vorbei"]), (True, ["vorbei"]), (False, []), (False, [])]
    # Ohne Tag ist nichts vorbei, auch wenn „Heute“ dahinter steht.
    entry = lager(org, registration_closes=date(2028, 4, 30))
    entry.name = "Sommerfahrt 2028"
    entry.save()
    found = _one(_all(deadline_tile(_tree(client_for(org.wanda).get(event_address(entry)))),
                      lambda e: "a-zeitleiste" in _classes(e)))
    assert ["ist-vorbei" in _classes(item) for item in _by_tag(found, "li")] == [False, True, False, False]


@pytest.mark.rechtematrix("VA-02")
def test_f3_nachmeldephase_wanda_verschiebt_den_anmeldeschluss(org, pfingstlager, monkeypatch):
    published(pfingstlager)
    at(monkeypatch, 2028, 5, 2, 10, 0)
    client = client_for(org.wanda)
    assert page_state(org.wanda, pfingstlager, client=client)[0] == CLOSED

    opened = client.get(dialog_address(pfingstlager))
    assert opened.status_code == 200
    dialog = dialog_of(_tree(opened))
    assert _text(_one(_by_tag(dialog, "h2", id="h-dialog"))) == "Anmeldung bearbeiten"
    done = save_dialog(client, pfingstlager, registration_closes="2028-05-05")

    assert done.status_code == 302 and done.url == event_address(pfingstlager)
    after = client.get(done.url)
    assert short_notices(after) == [SAVED]
    assert page_state(org.wanda, pfingstlager, client=client) == (
        OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis 05.05.2028.")
    assert stored(pfingstlager)[1] == date(2028, 5, 5)


def test_f3_der_stift_der_kachel_fuehrt_zum_dialog(org, pfingstlager):
    tile = deadline_tile(_tree(client_for(org.wanda).get(event_address(pfingstlager))))
    assert _text(_one(_by_tag(tile, "h2"))) == "Anmeldung"
    pencil = _one(_all(tile, lambda e: "a-stift" in _classes(e)))
    assert _attr(pencil, "href") == dialog_address(pfingstlager)
    assert [_text(label) for label in _all(pencil, lambda e: "sr-nur" in _classes(e))] == ["Anmeldung bearbeiten"]


def test_f4_ohne_fristen_offen_vom_veroeffentlichen_bis_zum_beginn(org):
    aktion = event_of(org.wanda, "Sippenaktion Falken", date(2028, 1, 21), date(2028, 1, 23))

    assert publish_lines(org.wanda, aktion)[1:] == ["Die Anmeldung öffnet sofort und läuft bis zum Beginn."]
    assert tile_of(org.wanda, aktion) == [
        "Heute 05.01.2028", "Anmeldestart nicht festgelegt, öffnet mit dem Veröffentlichen",
        "Anmeldeschluss nicht festgelegt, offen bis zum Beginn",
        "Änderungsschluss nicht festgelegt, Nachmelden bis zum Beginn"]
    assert client_for(org.wanda).post(publish_address(aktion)).status_code == 302

    assert page_state(org.wanda, aktion) == (OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis zum Beginn.")
    assert notes(org.wanda)["Sippenaktion Falken"] == (OPEN, "bis zum Beginn")


def test_f4_die_zusammenfassung_zeigt_fehlende_fristen_wie_die_kachel(org):
    """Zusammenfassung und Kachel der Leitungsseite zeigen dieselbe Zeitleiste (Vorschau, Sebastian, 27.11.2026)."""
    entwurf = entwurf_im_ablauf(org)
    client = client_for(org.wanda)
    summary = _tree(client.get(summary_address(entwurf)))
    assert timeline(summary) == [
        "Heute 05.01.2028", "Anmeldestart nicht festgelegt, öffnet mit dem Veröffentlichen",
        "Anmeldeschluss nicht festgelegt, offen bis zum Beginn",
        "Änderungsschluss nicht festgelegt, Nachmelden bis zum Beginn"]

    Event.objects.filter(pk=entwurf.pk).update(registration_closes=date(2028, 4, 30))
    summary = _tree(client.get(summary_address(entwurf)))
    assert timeline(summary) == timeline(_tree(client.get(event_address(entwurf))))


def test_f5_nur_anmeldeschluss(org, monkeypatch):
    thing = event_of(org.wanda, "Stammesthing Walhall", date(2028, 1, 14), date(2028, 1, 16))
    thing.registration_closes = date(2028, 1, 9)
    thing.save()
    assert publish_lines(org.wanda, thing)[1:] == ["Die Anmeldung öffnet sofort und läuft bis 09.01.2028."]
    published(thing)

    assert page_state(org.wanda, thing) == (OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis 09.01.2028.")
    assert notes(org.wanda)["Stammesthing Walhall"] == (OPEN, "bis 09.01.2028")

    at(monkeypatch, 2028, 1, 10, 0, 0)
    assert page_state(org.wanda, thing) == (
        CLOSED, f"{IS_PUBLISHED} Die Anmeldung ist geschlossen. Nachmelden und Ändern bis zum Beginn.")
    assert notes(org.wanda)["Stammesthing Walhall"] == (CLOSED, "Nachmelden bis zum Beginn")


def test_f6_nur_anmeldestart(org, monkeypatch):
    treffen = event_of(org.wanda, "Vorbereitungstreffen 2028", date(2028, 7, 7), date(2028, 7, 9))
    treffen.registration_opens = date(2028, 3, 1)
    treffen.save()
    assert publish_lines(org.wanda, treffen)[1:] == ["Die Anmeldung öffnet am 01.03.2028 und läuft bis zum Beginn."]
    published(treffen)

    assert page_state(org.wanda, treffen)[0] == ANNOUNCED
    assert notes(org.wanda)["Vorbereitungstreffen 2028"] == (ANNOUNCED, "Anmeldung ab 01.03.2028")

    at(monkeypatch, 2028, 3, 1, 0, 0)
    assert page_state(org.wanda, treffen)[0] == OPEN
    assert notes(org.wanda)["Vorbereitungstreffen 2028"] == (OPEN, "bis zum Beginn")


@pytest.mark.rechtematrix("VA-02")
def test_f7_vorzeitig_schliessen_und_anmeldestart_in_der_vergangenheit(org, pfingstlager, monkeypatch):
    published(pfingstlager)
    at(monkeypatch, 2028, 2, 10, 10, 0)
    client = client_for(org.wanda)
    assert page_state(org.wanda, pfingstlager, client=client)[0] == OPEN

    assert save_dialog(client, pfingstlager, registration_closes="2028-02-09").status_code == 302
    assert page_state(org.wanda, pfingstlager, client=client)[0] == CLOSED

    pfingstlager.refresh_from_db()
    assert save_dialog(client, pfingstlager, registration_opens="2028-01-03").status_code == 302
    assert stored(pfingstlager)[:2] == (date(2028, 1, 3), date(2028, 2, 9))


def test_f8_frist_am_tag_des_beginns(org, pfingstlager, monkeypatch):
    client = client_for(org.wanda)
    assert save_dialog(client, pfingstlager, registration_closes="2028-06-02", changes_close="2028-06-02").status_code == 302
    published(pfingstlager)

    at(monkeypatch, 2028, 6, 2, 17, 59)
    assert page_state(org.wanda, pfingstlager)[0] == OPEN
    at(monkeypatch, 2028, 6, 2, 18, 0)
    assert page_state(org.wanda, pfingstlager)[0] == RUNNING


@pytest.mark.rechtematrix("VA-02")
def test_f9_fiete_als_mitleitung_aendert_die_fristen(org, pfingstlager):
    pfingstlager.leads.add(org.fiete)
    client = client_for(org.fiete)

    assert client.get(dialog_address(pfingstlager)).status_code == 200
    assert save_dialog(client, pfingstlager, changes_close="2028-05-14").status_code == 302

    assert stored(pfingstlager)[2] == date(2028, 5, 14)


def test_f10_wanda_leert_den_anmeldeschluss(org, monkeypatch):
    entry = lager(org, registration_opens=date(2028, 2, 1), registration_closes=date(2028, 4, 30))
    published(entry)
    at(monkeypatch, 2028, 5, 2, 10, 0)
    client = client_for(org.wanda)
    assert page_state(org.wanda, entry, client=client)[0] == CLOSED

    assert save_dialog(client, entry, registration_closes="").status_code == 302

    assert stored(entry) == (date(2028, 2, 1), None, None)
    assert page_state(org.wanda, entry, client=client) == (OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis zum Beginn.")


# ---------- Verboten ----------


@pytest.mark.rechtematrix("VA-02", "VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anmeldung/")
def test_fv1_andere_schicken_fristen_an_den_stift_und_finden_nichts(org, pfingstlager):
    for user in (org.finn, org.vera, org.tom, org.otto, org.max, org.fiete):
        client = client_for(user)
        assert client.get(dialog_address(pfingstlager)).status_code == 404, user.username
        assert client.get(dialog_address(pfingstlager), **SCRIPT).status_code == 404, user.username
        assert save_dialog(client, pfingstlager, registration_closes="2028-05-05").status_code == 404, user.username
        assert client.post(dialog_address(pfingstlager), {**shown(pfingstlager), "registration_closes": "2028-05-05"},
                           **SCRIPT).status_code == 404, user.username
    assert_like_missing(org.finn, dialog_address(pfingstlager))
    assert_like_missing(org.otto, dialog_address(pfingstlager))

    assert stored(pfingstlager) == tuple(PFINGSTEN.values())


@pytest.mark.rechtematrix("VA-03")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anmeldung/")
def test_fv1_auch_im_support_zugang_fuer_walhall_aendert_max_nichts(org, pfingstlager):
    client = client_for(org.max)
    assert client.post(f"{unit_address(org.walhall)}support-zugang/", {"anlass": "lead_request"}).status_code == 302

    assert save_dialog(client, pfingstlager, registration_closes="2028-05-05").status_code == 404
    assert_like_missing(org.max, dialog_address(pfingstlager))

    assert stored(pfingstlager) == tuple(PFINGSTEN.values())


@pytest.mark.rechtematrix("VA-03", "VA-06")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anmeldung/")
@pytest.mark.wie_nicht_vorhanden("veranstaltungen/<key:event>/anlegen/anmeldung/")
def test_fv1_fiete_tauscht_die_kennung_gegen_die_des_pfingstlagers_und_findet_nichts(org, pfingstlager):
    eigene = event_of(org.fiete, "Sippenaktion Falken", date(2028, 1, 21), date(2028, 1, 23))
    client = client_for(org.fiete)
    assert client.get(dialog_address(eigene)).status_code == 200

    assert save_dialog(client, pfingstlager, registration_closes="2028-05-05").status_code == 404
    assert_like_missing(org.fiete, dialog_address(pfingstlager))
    # Schritt 3 hat nur, wer den Entwurf gerade anlegt (VA-06), auch keine Mitleitung.
    entwurf = entwurf_im_ablauf(org)
    assert_like_missing(org.fiete, step_address(entwurf))
    entwurf.leads.add(org.fiete)
    assert save_step(client, entwurf, registration_closes="2028-05-05").status_code == 404
    assert_like_missing(org.otto, step_address(entwurf))

    assert stored(pfingstlager) == tuple(PFINGSTEN.values())
    assert stored(entwurf) == (None, None, None)


@pytest.mark.rechtematrix("VA-03")
def test_fv1_gegenprobe_wanda_speichert_weiter(org, pfingstlager):
    assert save_dialog(client_for(org.wanda), pfingstlager, registration_closes="2028-05-05").status_code == 302
    assert stored(pfingstlager)[1] == date(2028, 5, 5)


# ---------- Grenzfälle ----------


@pytest.mark.parametrize(("values", "errors"), [
    ({"registration_closes": "2028-01-31"}, {"registration_closes": "Der Anmeldeschluss liegt vor dem Anmeldestart."}),
    ({"changes_close": "2028-04-29"}, {"changes_close": "Der Änderungsschluss liegt vor dem Anmeldeschluss."}),
])
def test_fg1_reihenfolge_im_stift_und_in_schritt_3(org, pfingstlager, values, errors):
    client = client_for(org.wanda)
    refused = save_dialog(client, pfingstlager, **values)
    assert refused.status_code == 200
    assert field_errors(dialog_of(_tree(refused))) == errors
    assert stored(pfingstlager) == tuple(PFINGSTEN.values())

    entwurf = entwurf_im_ablauf(org, **PFINGSTEN)
    refused = save_step(client, entwurf, **values)
    assert refused.status_code == 200
    assert field_errors(_tree(refused)) == errors
    assert stored(entwurf) == tuple(PFINGSTEN.values())


def test_fg1_alle_drei_am_selben_tag_sind_erlaubt(org, pfingstlager):
    same = "2028-04-30"
    done = save_dialog(client_for(org.wanda), pfingstlager, registration_opens=same, registration_closes=same,
                       changes_close=same)
    assert done.status_code == 302
    assert stored(pfingstlager) == (date(2028, 4, 30),) * 3


def test_fg2_aenderungsschluss_ohne_anmeldeschluss(org, pfingstlager):
    refused = save_dialog(client_for(org.wanda), pfingstlager, registration_closes="")
    assert refused.status_code == 200
    assert field_errors(dialog_of(_tree(refused))) == {"changes_close": "Trag zuerst einen Anmeldeschluss ein."}
    assert stored(pfingstlager) == tuple(PFINGSTEN.values())


@pytest.mark.parametrize(("name", "error"), [
    ("registration_opens", "Der Anmeldestart liegt nach dem Beginn."),
    ("registration_closes", "Der Anmeldeschluss liegt nach dem Beginn."),
    ("changes_close", "Der Änderungsschluss liegt nach dem Beginn."),
])
def test_fg3_jede_frist_spaetestens_am_tag_des_beginns(org, name, error):
    entry = lager(org)
    refused = save_dialog(client_for(org.wanda), entry,
                          **{"registration_closes": "2028-06-02", name: "2028-06-03"})
    assert refused.status_code == 200
    assert field_errors(dialog_of(_tree(refused)))[name] == error
    assert stored(entry) == (None, None, None)


def test_fg3_eine_unmoegliche_frist_ist_ein_fehler_am_feld(org, pfingstlager):
    refused = save_dialog(client_for(org.wanda), pfingstlager, registration_opens="2028-02-30")
    assert field_errors(dialog_of(_tree(refused))) == {"registration_opens": "Bitte gib ein gültiges Datum ein."}


@pytest.mark.rechtematrix("VA-02")
def test_fg4_beginn_vor_einer_frist_im_stift_grunddaten(org, pfingstlager):
    client = client_for(org.wanda)
    values = {"name": "Pfingstlager 2028", "start": "2028-05-05", "start_time": "18:00", "end": "2028-06-05",
              "end_time": "12:00", "location": "Burg Ludwigstein", "version": str(pfingstlager.version),
              "duration_ok": "32"}

    refused = client.post(edit_address(pfingstlager), values)

    assert refused.status_code == 200
    assert field_errors(dialog_of(_tree(refused)))["start"] == (
        "Der Beginn liegt vor einer Frist der Anmeldung. Ändere zuerst die Fristen.")
    pfingstlager.refresh_from_db()
    assert pfingstlager.start == date(2028, 6, 2)
    # Gegenprobe: ein Beginn am Tag des Änderungsschlusses geht.
    assert client.post(edit_address(pfingstlager), {**values, "start": "2028-05-07", "duration_ok": "30"}).status_code == 302


def test_fg4_auch_in_schritt_1_eines_entwurfs(org):
    entwurf = entwurf_im_ablauf(org, **PFINGSTEN)
    values = {"name": "Pfingstlager 2028", "start": "2028-05-05", "start_time": "18:00", "end": "2028-06-05",
              "end_time": "12:00", "version": str(entwurf.version), "duration_ok": "32"}

    refused = client_for(org.wanda).post(f"{event_address(entwurf)}anlegen/", values)

    assert refused.status_code == 200
    assert field_errors(_tree(refused))["start"] == (
        "Der Beginn liegt vor einer Frist der Anmeldung. Ändere zuerst die Fristen.")


@pytest.mark.django_db(transaction=True)
def test_fg4_gleichzeitig_beginn_und_frist_geaendert_beides_zusammen_geht_nie():
    """Fristen und Grunddaten haben je einen eigenen Stand; gleichzeitig gespeichert, prüft jede Seite unter Sperre die
    andere neu, und die Datenbank lässt eine Frist nach dem Beginn nicht zu."""
    o = build_people()
    entry = lager(o, **PFINGSTEN)
    basics = {"name": "Pfingstlager 2028", "start": date(2028, 5, 8), "start_time": None, "end": date(2028, 6, 5),
              "end_time": None, "location": ""}
    later = {**PFINGSTEN, "changes_close": date(2028, 5, 20)}

    results = _one_after_the_other(
        lambda: Rights(o.wanda).edit_deadlines(entry.key, later, "1"),
        lambda: Rights(o.wanda).edit_event(entry.key, basics, "1"))

    assert sorted(done for done, _entry, _text in results) == [False, True]
    entry.refresh_from_db()
    assert max(entry.registration_opens, entry.registration_closes, entry.changes_close) <= entry.start


def test_fg5_mitternacht_in_deutscher_zeit_auch_in_der_sommerzeit(org, pfingstlager, monkeypatch):
    published(pfingstlager)

    moment = timezone.make_aware(datetime(2028, 4, 30, 23, 59, 59))
    monkeypatch.setattr(timezone, "now", lambda: moment)
    assert page_state(org.wanda, pfingstlager)[0] == OPEN
    at(monkeypatch, 2028, 5, 1, 0, 0)
    assert page_state(org.wanda, pfingstlager)[0] == CLOSED

    # 30.04., 22:30 Weltzeit ist in Deutschland (Sommerzeit) der 01.05., 0:30.
    world = datetime(2028, 4, 30, 22, 30, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: world)
    assert page_state(org.wanda, pfingstlager)[0] == CLOSED
    world = datetime(2028, 4, 30, 21, 59, 59, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: world)
    assert page_state(org.wanda, pfingstlager)[0] == OPEN

    # Der Anmeldestart gilt ab 0:00 seines Tags: davor 23:59:59 angekündigt (Winterzeit).
    moment = timezone.make_aware(datetime(2028, 1, 31, 23, 59, 59))
    monkeypatch.setattr(timezone, "now", lambda: moment)
    assert page_state(org.wanda, pfingstlager)[0] == ANNOUNCED
    world = datetime(2028, 1, 31, 23, 0, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: world)
    assert page_state(org.wanda, pfingstlager)[0] == OPEN


def test_fg5_grenzen_des_aenderungsschlusses_und_der_zeitleiste(org, pfingstlager, monkeypatch):
    """Befund G1 der unabhängigen Prüfung: Der Änderungsschluss gilt bis zum Ende seines Tags, und die Zeitleiste
    rechnet „Heute“ und „vorbei“ in deutscher Zeit, auch in der Sommerzeit."""
    published(pfingstlager)
    late = f"{IS_PUBLISHED} Die Anmeldung ist geschlossen. Nachmelden und Ändern bis 07.05.2028."

    moment = timezone.make_aware(datetime(2028, 5, 7, 23, 59, 59))
    monkeypatch.setattr(timezone, "now", lambda: moment)
    assert page_state(org.wanda, pfingstlager) == (CLOSED, late)
    at(monkeypatch, 2028, 5, 8, 0, 0)
    assert page_state(org.wanda, pfingstlager) == (CLOSED, f"{IS_PUBLISHED} Die Anmeldung ist geschlossen.")

    # 30.04., 22:30 Weltzeit ist in Deutschland schon der 01.05.: „Heute“ steht hinter dem Anmeldeschluss, der vorbei ist.
    world = datetime(2028, 4, 30, 22, 30, tzinfo=UTC)
    monkeypatch.setattr(timezone, "now", lambda: world)
    root = _tree(client_for(org.wanda).get(event_address(pfingstlager)))
    assert timeline(root)[1:3] == ["Anmeldeschluss So, 30.04.2028", "Heute 01.05.2028"]
    found = _one(_all(deadline_tile(root), lambda e: "a-zeitleiste" in _classes(e)))
    assert ["ist-vorbei" in _classes(entry) for entry in _by_tag(found, "li")][:2] == [True, True]


def test_eine_frist_am_letzten_moeglichen_tag_bringt_keine_seite_zum_absturz(org):
    """Befund M1 der unabhängigen Prüfung: Fristen am 31.12.9999 rechnen nicht über das letzte Datum hinaus."""
    last = date(9999, 12, 31)
    entry = event_of(org.wanda, "Fernes Lager", last, last)
    entry.start_time, entry.end_time = time(18, 0), time(20, 0)
    entry.registration_closes = entry.changes_close = last
    entry.published = True
    entry.save()
    client = client_for(org.wanda)

    for address in (LIST, event_address(entry), dialog_address(entry), publish_address(entry)):
        assert client.get(address).status_code == 200, address
    assert page_state(org.wanda, entry, client=client) == (OPEN, f"{IS_PUBLISHED} Die Anmeldung läuft bis 31.12.9999.")


def test_fg6_schluss_schon_vorbei_beim_veroeffentlichen(org):
    entry = lager(org, registration_closes=date(2028, 1, 3))

    assert publish_lines(org.wanda, entry)[1:] == ["Die Anmeldung ist schon geschlossen."]
    assert client_for(org.wanda).post(publish_address(entry)).status_code == 302

    assert page_state(org.wanda, entry) == (
        CLOSED, f"{IS_PUBLISHED} Die Anmeldung ist geschlossen. Nachmelden und Ändern bis zum Beginn.")


def test_fg6_ein_vergangener_anmeldestart_oeffnet_sofort(org):
    entry = lager(org, registration_opens=date(2028, 1, 2), registration_closes=date(2028, 4, 30))
    assert publish_lines(org.wanda, entry)[1:] == ["Die Anmeldung öffnet sofort und läuft bis 30.04.2028."]


def test_fg7_ein_aelteres_zweites_fenster_ueberschreibt_nichts(org, pfingstlager):
    first, second = client_for(org.wanda), client_for(org.wanda)
    opened = shown(pfingstlager)
    first.get(dialog_address(pfingstlager))
    second.get(dialog_address(pfingstlager))

    assert first.post(dialog_address(pfingstlager), {**opened, "registration_closes": "2028-05-05"}).status_code == 302
    response = second.post(dialog_address(pfingstlager), {**opened, "changes_close": "2028-05-14"})

    assert response.status_code == 200
    assert stored(pfingstlager) == (date(2028, 2, 1), date(2028, 5, 5), date(2028, 5, 7))
    found = dialog_of(_tree(response))
    assert CHANGED in _visible_text(found)
    # Der Dialog zeigt den neuen Stand; erneut gespeichert gilt die Änderung.
    assert _attr(_one(_by_tag(found, "input", name="registration_closes")), "value") == "2028-05-05"
    version = _attr(_one(_by_tag(found, "input", name="deadlines_version")), "value")
    assert second.post(dialog_address(pfingstlager), {**shown(pfingstlager), "changes_close": "2028-05-14",
                                                      "deadlines_version": version}).status_code == 302
    assert stored(pfingstlager) == (date(2028, 2, 1), date(2028, 5, 5), date(2028, 5, 14))


def test_fg7_doppelklick_mit_denselben_fristen_gilt_als_gespeichert(org, pfingstlager):
    client = client_for(org.wanda)
    form = {**shown(pfingstlager), "registration_closes": "2028-05-05"}

    assert client.post(dialog_address(pfingstlager), form).status_code == 302
    assert client.post(dialog_address(pfingstlager), form).status_code == 302
    assert short_notices(client.get(event_address(pfingstlager))) == [SAVED]


def test_fg7_grunddaten_aus_einem_zweiten_fenster_aendern_die_fristen_nicht(org, pfingstlager):
    client = client_for(org.wanda)
    opened = shown(pfingstlager)
    basics = {"name": "Pfingstlager Walhall", "start": "2028-06-02", "start_time": "18:00", "end": "2028-06-05",
              "end_time": "12:00", "location": "Burg Ludwigstein", "version": str(pfingstlager.version)}
    assert client.post(edit_address(pfingstlager), basics).status_code == 302

    assert client.post(dialog_address(pfingstlager), {**opened, "registration_closes": "2028-05-05"}).status_code == 302
    pfingstlager.refresh_from_db()
    assert (pfingstlager.name, pfingstlager.registration_closes) == ("Pfingstlager Walhall", date(2028, 5, 5))


@pytest.mark.django_db(transaction=True)
def test_fg8_veranstaltungen_aus_p2_haben_nach_dem_umbau_keine_fristen():
    before = [("events", "0007_einladungstext")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    old = executor.loader.project_state(before).apps.get_model("events", "Event")
    old.objects.create(name="Probelager 2027", start=date(2027, 5, 15), end=date(2027, 5, 17))

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())

    assert list(Event.objects.values_list("name", *FIELDS)) == [("Probelager 2027", None, None, None)]


def test_die_datenbank_laesst_keine_frist_nach_dem_beginn_und_keine_falsche_reihenfolge_zu(org):
    for values in ({"registration_closes": date(2028, 6, 3)}, {"registration_opens": date(2028, 6, 3)},
                   {"registration_opens": date(2028, 3, 1), "registration_closes": date(2028, 2, 1)},
                   {"registration_closes": date(2028, 3, 1), "changes_close": date(2028, 2, 1)},
                   {"changes_close": date(2028, 2, 1)}):
        with pytest.raises(IntegrityError), transaction.atomic():
            lager(org, **values)
