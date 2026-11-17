"""Rauchtest „Leitungsseite mit Kachel ‚Grunddaten‘“ im Browser (#379, AG8): am PC und am Handy, je nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an, ist Mitglied der Sippe Falken und leitet „Pfingstlager
2028“ (02.06. bis 05.06.2028, ohne Uhrzeit und Ort, wie aus P2). „Heute“ ist wie in den Szenarien der 05.01.2028;
der Server läuft im selben Prozess wie der Test. Geprüft werden die Teile, die nur ein Browser zeigt: von der Liste
„Von mir geleitet“ zur Leitungsseite, der Stift der Kachel öffnet den Dialog, Uhrzeiten (Feld des Browsers, mit
`fill` gesetzt wie das Datum) und Ort (am Handy wie mit Autokorrektur und Wortvorschlägen getippt), die Nachfrage
zur Dauer mit dem Schalter, die Kalenderblätter danach, nichts steht seitlich über, der Fokus ist zu sehen, und die
Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_grunddaten.py. Alle Namen sind
erfunden; „Burg Ludwigstein“ stammt aus dem Zielbild (#356).
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from rauchtests.test_veranstaltungen import _dialog, _erika_in_den_falken

LIST = f"{BASE}/veranstaltungen/"
ROW_LINK = '[aria-labelledby="h-veranstaltungen"] .a-va-zeile a'
PENCIL = '[aria-labelledby="h-grunddaten"] a.a-stift'
SUBMIT = 'dialog.a-dialog button[type="submit"]'
TILE = '[aria-labelledby="h-grunddaten"]'


@pytest.fixture(autouse=True)
def heute(monkeypatch):
    monkeypatch.setattr(timezone, "localdate", lambda *args, **kwargs: date(2028, 1, 5))


def _pfingstlager() -> Event:
    """Erika leitet das „Pfingstlager 2028“ aus P2, ohne Uhrzeit und ohne Ort (A1)."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    found = Event.objects.create(name="Pfingstlager 2028", start=date(2028, 6, 2), end=date(2028, 6, 5))
    found.leads.add(erika)
    return found


def _zur_leitungsseite(page: Page, steps: int) -> None:
    """Von der Liste mit Tab zur Zeile und mit Enter zur Leitungsseite."""
    page.goto(LIST)
    expect(page.locator('[aria-labelledby="h-veranstaltungen"] h2')).to_have_text("Von mir geleitet")
    _no_side_scroll(page)
    assert run_axe(page) == []
    stations = _stations_to_element(page, ROW_LINK, steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}*/")
    expect(page.locator("h1")).to_have_text("Pfingstlager 2028")
    expect(page.locator(".a-kopf p")).to_have_text("02.06.2028 bis 05.06.2028")
    expect(page.locator(f"{TILE} .a-kalenderblatt")).to_have_text(["Beginn: Fr 02 Jun 2028", "Ende: Mo 05 Jun 2028"])
    expect(page.locator(f"{TILE} .a-kalender-dauer")).to_have_text("4 Tage")
    _no_side_scroll(page)
    assert run_axe(page) == []


def _stift_oeffnen(page: Page, steps: int) -> None:
    stations = _stations_to_element(page, PENCIL, steps=steps)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}*/bearbeiten/")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Pfingstlager 2028 bearbeiten")
    expect(page.get_by_label("Name")).to_be_focused()
    _no_side_scroll(page)
    assert run_axe(page) == []


def _danach(page: Page) -> None:
    """Die Leitungsseite nach dem Speichern von 18:00, 12:00 und „Burg Ludwigstein“ (A2)."""
    page.wait_for_url(f"{LIST}*/")
    expect(page.locator(".a-kurz")).to_contain_text("Die Angaben zu Pfingstlager 2028 sind gespeichert.")
    expect(page.locator(".a-kopf p")).to_have_text("02.06.2028 bis 05.06.2028 · Burg Ludwigstein")
    expect(page.locator(f"{TILE} .a-kalenderblatt")).to_have_text(
        ["Beginn: Fr 02 Jun 2028 18:00", "Ende: Mo 05 Jun 2028 12:00"])
    expect(page.locator(f"{TILE} .a-kalender-ort")).to_have_text("Ort: Burg Ludwigstein")
    _no_side_scroll(page)
    page.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(page) == []


def test_am_pc_nur_mit_der_tastatur_grunddaten_bearbeiten(pc):
    login(pc)
    _erika_in_den_falken()
    _pfingstlager()
    _zur_leitungsseite(pc, steps=25)
    _stift_oeffnen(pc, steps=25)

    # Vom Namen mit Tab über das Datum zur Uhrzeit des Beginns, dann zum Ende und seiner Uhrzeit, dann zum Ort.
    stations = _stations_to_element(pc, 'dialog input[name="start_time"]', steps=10)
    _all_visible(stations)
    start_time = pc.locator('dialog input[name="start_time"]')
    assert start_time.get_attribute("type") == "time"
    expect(start_time).to_have_accessible_name("Uhrzeit Beginn")
    start_time.fill("18:00")
    stations = _stations_to_element(pc, 'dialog input[name="end_time"]', steps=10)
    _all_visible(stations)
    pc.locator('dialog input[name="end_time"]').fill("12:00")
    stations = _stations_to_element(pc, 'dialog input[name="location"]', steps=10)
    _all_visible(stations)
    pc.keyboard.type("Burg Ludwigstein")
    stations = _stations_to_element(pc, SUBMIT, steps=6)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    _danach(pc)


def test_am_pc_nur_mit_der_tastatur_die_nachfrage_zur_dauer(pc):
    """AG4 im Browser: Die Frage steht am Feld „Ende“, der Schalter darunter geht mit der Leertaste."""
    login(pc)
    _erika_in_den_falken()
    found = _pfingstlager()
    pc.goto(f"{LIST}{found.key}/bearbeiten/")
    pc.locator('dialog input[name="end"]').fill("2028-07-12")
    pc.get_by_role("button", name="Speichern").click()

    end = pc.locator('dialog input[name="end"]')
    expect(end).to_have_accessible_description("Die Veranstaltung dauert 41 Tage. Stimmt das?")
    switch = pc.get_by_role("checkbox", name="Ja, die Dauer stimmt")
    expect(switch).not_to_be_checked()
    _no_side_scroll(pc)
    assert run_axe(pc) == []
    stations = _stations_to_element(pc, 'dialog input[name="duration_ok"]', steps=25)
    _all_visible(stations)
    pc.keyboard.press("Space")
    expect(switch).to_be_checked()
    stations = _stations_to_element(pc, SUBMIT, steps=6)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{LIST}{found.key}/")
    expect(pc.locator(".a-kopf p")).to_have_text("02.06.2028 bis 12.07.2028")
    expect(pc.locator(f"{TILE} .a-kalender-dauer")).to_have_text("41 Tage")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    _erika_in_den_falken()
    _pfingstlager()
    _zur_leitungsseite(handy, steps=30)
    _stift_oeffnen(handy, steps=30)

    handy.locator('dialog input[name="start_time"]').fill("18:00")
    handy.locator('dialog input[name="end_time"]').fill("12:00")
    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
    location = handy.get_by_label("Ort")
    _type_like_a_phone(location, "Burg ", "Lud", "Ludwig", "stein")
    expect(location).to_have_value("Burg Ludwigstein")
    _no_side_scroll(handy)
    stations = _stations_to_element(handy, SUBMIT, steps=6)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    _danach(handy)
