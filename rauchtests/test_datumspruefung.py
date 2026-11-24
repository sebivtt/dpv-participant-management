"""Rauchtest „Datumsprüfungen schon beim Verlassen des Felds“ im Browser (#411, Teil C von #398): am PC und am Handy.

Die Kennungen CA1 bis CA9 und CG1 bis CG4 verweisen auf die Szenarien vom 24.11.2026
(https://github.com/sebivtt/dpv-participant-management/issues/411#issuecomment-7124250592). Erika meldet sich wirklich
bei der Keycloak-Testumgebung an, ist Mitglied der Sippe Falken (also mit Zuordnung) und steht in den Szenarien für
Wanda. „Heute“ ist der 05.01.2028; der Server läuft im selben Prozess wie der Test. Das Datum setzt der Test mit
`fill` wie in rauchtests/test_veranstaltungen.py; verlassen wird ein Feld mit Tab, wie eine Person mit der Tastatur,
bis zum nächsten Feld. Was der Server dafür mitbringt und dass er weiter prüft, prüft tests/test_datumspruefung.py.
Alle Namen sind erfunden.
"""

from datetime import date, datetime, time

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, expect_modal, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from rauchtests.test_veranstaltungen import _dialog, _erika_in_den_falken

LIST = f"{BASE}/veranstaltungen/"
CREATE = f"{LIST}erstellen/"
STEP = "form#f-schritt"
NEXT = f'{STEP} .a-schritt-rechts button[type="submit"]'
SAVE = 'dialog.a-dialog .a-dialog-fuss button[type="submit"]'
END_BEFORE_START = "Das Ende liegt vor dem Beginn."
PAST = "Der Beginn liegt in der Vergangenheit."
SWITCH = "Ja, die Dauer stimmt"


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


def _schritt_1(page: Page) -> None:
    """Erika mit Zuordnung in Schritt 1 von „Veranstaltung erstellen“; der Name ist eingetragen."""
    login(page)
    _erika_in_den_falken()
    page.goto(CREATE)
    page.get_by_label("Name").fill("Pfingstlager 2028")


def _field(page: Page, name: str, scope: str = STEP):
    return page.locator(f'{scope} input[name="{name}"]')


def _leave_to(page: Page, name: str, scope: str = STEP, steps: int = 15) -> None:
    """Verlässt das Feld mit Tab bis zum Feld `name`; jede Station hat einen sichtbaren Fokus."""
    _all_visible(_stations_to_element(page, f'{scope} input[name="{name}"]', steps=steps))


def _error(page: Page, name: str, scope: str = STEP):
    """Die Meldung unter dem Datumsfeld (Datum und Uhrzeit haben eine gemeinsame)."""
    return page.locator(f'{scope} .a-datumsfeld:has(input[name="{name}"]) .invalid-feedback')


def test_ca1_ca2_ca9_ende_vor_beginn_beim_verlassen_und_weg_beim_korrigieren(pc):
    _schritt_1(pc)
    _field(pc, "start").fill("2028-06-02")
    _field(pc, "end").fill("2028-06-01")
    expect(_error(pc, "end")).to_have_count(0)

    _leave_to(pc, "end_time")

    # CA9: Die Meldung ist mit dem Feld verbunden und wird angesagt; der Fokus bleibt, wohin Erika gewechselt ist.
    expect(_error(pc, "end")).to_have_text(END_BEFORE_START)
    expect(_error(pc, "end")).to_be_visible()
    expect(_error(pc, "end")).to_have_attribute("role", "alert")
    expect(_field(pc, "end")).to_have_accessible_description(END_BEFORE_START)
    expect(_field(pc, "end_time")).to_have_accessible_description(END_BEFORE_START)
    expect(_field(pc, "end")).to_have_attribute("aria-invalid", "true")
    expect(_field(pc, "end_time")).to_be_focused()
    expect(_error(pc, "start")).to_have_count(0)
    _no_side_scroll(pc)
    assert run_axe(pc) == []

    # CA1: Beim Korrigieren verschwindet die Meldung sofort, schon bevor Erika das Feld verlässt.
    _field(pc, "end").fill("2028-06-05")
    expect(_error(pc, "end")).to_have_count(0)
    expect(_field(pc, "end")).not_to_have_attribute("aria-invalid", "true")
    expect(_field(pc, "end")).to_have_accessible_description("")

    # CA2: Am selben Tag mit früherer Uhrzeit kommt dieselbe Meldung beim Verlassen der Uhrzeit „Ende“.
    _field(pc, "start_time").fill("18:00")
    _field(pc, "end").fill("2028-06-02")
    _field(pc, "end_time").fill("12:00")
    _leave_to(pc, "location")
    expect(_error(pc, "end")).to_have_text(END_BEFORE_START)
    expect(_field(pc, "location")).to_be_focused()


def test_ca3_cg3_cg4_beginn_in_der_vergangenheit_nach_dem_tag_des_servers(pc):
    _schritt_1(pc)
    # CG3: Der Rechner steht versehentlich auf 2029; es gilt trotzdem der heutige Tag des Servers.
    pc.clock.set_fixed_time(datetime(2029, 3, 1, 10, 0))
    pc.goto(CREATE)
    pc.get_by_label("Name").fill("Pfingstlager 2028")

    # CA3 und CG4: Beginn gestern, dazu 29 Tage: nur die Meldung am Beginn, noch keine Nachfrage zur Dauer.
    _field(pc, "start").fill("2028-01-04")
    _field(pc, "end").fill("2028-02-01")
    _leave_to(pc, "end_time")
    expect(_error(pc, "start")).to_have_text(PAST)
    expect(_field(pc, "start")).to_have_accessible_description(PAST)
    expect(_error(pc, "end")).to_have_count(0)
    expect(pc.get_by_role("checkbox", name=SWITCH)).to_have_count(0)

    # CA3: Heute ist zu jeder Uhrzeit erlaubt; bis zum 01.02. sind es dann 28 Tage, ohne Nachfrage.
    _field(pc, "start").fill("2028-01-05")
    _field(pc, "start_time").fill("00:00")
    _leave_to(pc, "end")
    expect(_error(pc, "start")).to_have_count(0)
    expect(_error(pc, "end")).to_have_count(0)

    # Mit 2029 auf der Uhr des Rechners wäre auch der 05.01.2028 vergangen; die Seite fragt danach nicht.
    _field(pc, "start").fill("2028-01-04")
    _leave_to(pc, "end")
    expect(_error(pc, "start")).to_have_text(PAST)


def test_ca4_ca5_nachfrage_zur_dauer_mit_schalter_und_weiter(pc):
    _schritt_1(pc)
    _field(pc, "start").fill("2028-06-02")

    # CA4: 28 Tage ohne Nachfrage.
    _field(pc, "end").fill("2028-06-29")
    _leave_to(pc, "end_time")
    expect(_error(pc, "end")).to_have_count(0)
    expect(pc.get_by_role("checkbox", name=SWITCH)).to_have_count(0)

    # CA4: 29 Tage mit Nachfrage am Ende und dem Schalter darunter, auf aus.
    _field(pc, "end").fill("2028-06-30")
    _leave_to(pc, "end_time")
    expect(_error(pc, "end")).to_have_text("Die Veranstaltung dauert 29 Tage. Stimmt das?")
    switch = pc.get_by_role("checkbox", name=SWITCH)
    expect(switch).to_be_visible()
    expect(switch).not_to_be_checked()
    expect(_field(pc, "end_time")).to_be_focused()
    _no_side_scroll(pc)
    assert run_axe(pc) == []

    # CA5: Bestätigt, dann das Ende geändert: die Frage kommt neu mit 30 Tagen, der Schalter steht wieder auf aus.
    switch.check()
    _field(pc, "end").fill("2028-07-01")
    _leave_to(pc, "end_time")
    expect(_error(pc, "end")).to_have_text("Die Veranstaltung dauert 30 Tage. Stimmt das?")
    expect(switch).to_have_count(1)
    expect(switch).not_to_be_checked()

    # CA4: Eingeschaltet geht es mit „Weiter“ zur Zusammenfassung; gespeichert ist der Entwurf.
    _all_visible(_stations_to_element(pc, f'{STEP} input[name="duration_ok"]', steps=25))
    pc.keyboard.press("Space")
    expect(switch).to_be_checked()
    pc.locator(NEXT).click()
    pc.wait_for_url(f"{LIST}*/anlegen/zusammenfassung/")
    assert Event.objects.get(name="Pfingstlager 2028").end == date(2028, 7, 1)


def test_ca6_bearbeiten_nur_geaendertes_und_ohne_aenderung_nichts(pc):
    login(pc)
    _erika_in_den_falken()
    erika = get_user_model().objects.get(username="erika.testfrau")
    # Das Pfingstlager läuft schon (Beginn 02.01.2028, heute 05.01.2028).
    found = Event.objects.create(name="Pfingstlager 2028", start=date(2028, 1, 2), start_time=time(18, 0),
                                 end=date(2028, 1, 9))
    found.leads.add(erika)
    pc.goto(f"{LIST}{found.key}/bearbeiten/")
    dialog = _dialog(pc)
    expect_modal(dialog)

    # Ohne Änderung mit Tab durch alle Felder: keine Meldung.
    # Vom Namen über Datum und Uhrzeit von Beginn und Ende, je mit ihren Teilen.
    _leave_to(pc, "location", scope="dialog", steps=30)
    expect(dialog.locator(".a-datumsfeld .invalid-feedback")).to_have_count(0)

    # Nur das Ende geändert: keine Meldung zum Beginn, der in der Vergangenheit liegt.
    _field(pc, "end", scope="dialog").fill("2028-01-12")
    _leave_to(pc, "end_time", scope="dialog")
    expect(dialog.locator(".a-datumsfeld .invalid-feedback")).to_have_count(0)

    # Wird doch der Beginn geändert, kommt die Meldung, wie beim Speichern.
    _field(pc, "start", scope="dialog").fill("2028-01-03")
    _leave_to(pc, "start_time", scope="dialog")
    expect(_error(pc, "start", scope="dialog")).to_have_text(PAST)
    # Zurück auf den gespeicherten Beginn: die Meldung ist weg.
    _field(pc, "start", scope="dialog").fill("2028-01-02")
    expect(_error(pc, "start", scope="dialog")).to_have_count(0)

    pc.locator(SAVE).click()
    pc.wait_for_url(f"{LIST}{found.key}/")
    found.refresh_from_db()
    assert found.end == date(2028, 1, 12)


def test_cg1_cg2_keine_meldung_zu_leeren_oder_unvollstaendigen_feldern(pc):
    _schritt_1(pc)
    # CG1: Nur der Beginn, das Ende leer: keine Meldung zum leeren Ende, auch nicht beim Verlassen des Endes.
    _field(pc, "start").fill("2028-06-02")
    _leave_to(pc, "end")
    _leave_to(pc, "location")
    expect(pc.locator(f"{STEP} .a-datumsfeld .invalid-feedback")).to_have_count(0)

    # CG2: Im Ende steht erst der Tag (wie in Safari beim Tippen): keine Meldung, bis das Datum vollständig ist.
    _field(pc, "end").focus()
    pc.keyboard.type("01")
    _leave_to(pc, "location")
    expect(pc.locator(f"{STEP} .a-datumsfeld .invalid-feedback")).to_have_count(0)


def test_ca1_ca4_am_handy(handy):
    _schritt_1(handy)
    _field(handy, "start").fill("2028-06-02")
    _field(handy, "end").fill("2028-06-01")
    _leave_to(handy, "end_time")
    expect(_error(handy, "end")).to_have_text(END_BEFORE_START)
    expect(_error(handy, "end")).to_be_visible()

    _field(handy, "end").fill("2028-06-30")
    _leave_to(handy, "end_time")
    expect(_error(handy, "end")).to_have_text("Die Veranstaltung dauert 29 Tage. Stimmt das?")
    expect(handy.get_by_role("checkbox", name=SWITCH)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []


def test_ca8_ohne_skript_erst_nach_weiter(pc_ohne_skript):
    page = pc_ohne_skript
    _schritt_1(page)
    _field(page, "start").fill("2028-06-02")
    _field(page, "end").fill("2028-06-01")
    _leave_to(page, "end_time")
    expect(_error(page, "end")).to_have_count(0)

    page.locator(NEXT).click()

    page.wait_for_url(CREATE)
    expect(_error(page, "end")).to_have_text(END_BEFORE_START)
