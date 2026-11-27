"""Rauchtest „Fristen“ im Browser (#360, FG9): Schritt 3 „Anmeldung“ und der Stift der Kachel „Anmeldung“, am PC und am
Handy, je nur mit der Tastatur und ohne Skript.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an, ist Mitglied der Sippe Falken und leitet das
„Pfingstlager 2028“ als Entwurf, mit Beginn in rund einem halben Jahr. Die Uhr bleibt die echte, weil Keycloak die
Zeit seiner Anmeldung selbst prüft; deshalb liegen Beginn und Fristen relativ zu heute (wie in
rauchtests/test_veroeffentlichen.py). Geprüft wird, was nur ein Browser zeigt: Der Stift öffnet den Dialog
„Anmeldung bearbeiten“ mit Enter, auch ohne Skript; die drei Fristen sind Datumsfelder des Browsers (mit `fill`
gesetzt wie in den übrigen Rauchtests, getippter Text kommt hier nicht vor, deshalb keine Autokorrektur); nach dem
Speichern steht die Zeitleiste da, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die
Prüfung auf Barrierefreiheit (nur mit Skript, wie in den übrigen Rauchtests ohne Skript). Die Regeln selbst prüft
tests/test_fristen.py. Alle Namen sind erfunden; „Burg Ludwigstein“ stammt aus dem Zielbild (#356).
"""

from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from playwright.sync_api import Page, expect

from events.models import Event
from rauchtests.conftest import BASE, expect_modal, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from rauchtests.test_veranstaltungen import _dialog, _erika_in_den_falken

LIST = f"{BASE}/veranstaltungen/"
TILE = '[aria-labelledby="h-anmeldung"]'
PENCIL = f"{TILE} a.a-stift"
SUBMIT = 'dialog.a-dialog .a-dialog-fuss button[type="submit"]'
STEP_SUBMIT = 'form#f-schritt .a-schritt-rechts button[type="submit"]'


def _tag(day) -> str:
    return day.strftime("%d.%m.%Y")


def _pfingstlager(creating: bool = False) -> Event:
    erika = get_user_model().objects.get(username="erika.testfrau")
    start = timezone.localdate() + timedelta(days=180)
    found = Event.objects.create(name="Pfingstlager 2028", start=start, start_time=time(18, 0),
                                 end=start + timedelta(days=3), end_time=time(12, 0), location="Burg Ludwigstein",
                                 creating_by=erika if creating else None)
    found.leads.add(erika)
    return found


def _fristen() -> tuple:
    today = timezone.localdate()
    return today + timedelta(days=27), today + timedelta(days=100), today + timedelta(days=107)


def _fristen_eintragen(page: Page, scope: str) -> None:
    opens, closes, changes = _fristen()
    for name, day in (("registration_opens", opens), ("registration_closes", closes), ("changes_close", changes)):
        field = page.locator(f'{scope} input[name="{name}"]')
        assert field.get_attribute("type") == "date"
        field.fill(day.isoformat())


def _zeitleiste(page: Page) -> None:
    opens, closes, changes = _fristen()
    entries = page.locator(f"{TILE} .a-zeitleiste li")
    expect(entries).to_have_count(4)
    expect(entries.nth(0)).to_contain_text("Heute")
    expect(entries.nth(1)).to_contain_text("Anmeldestart")
    expect(entries.nth(1)).to_contain_text(f"{_tag(opens)} · in 27 Tagen")
    expect(entries.nth(2)).to_contain_text(_tag(closes))
    expect(entries.nth(3)).to_contain_text(f"{_tag(changes)} · bis dahin Nachmelden")
    _no_side_scroll(page)


def _mit_der_tastatur(page: Page, steps: int) -> None:
    login(page)
    _erika_in_den_falken()
    entry = _pfingstlager()
    page.goto(f"{LIST}{entry.key}/")
    expect(page.locator(f"{TILE} h2")).to_have_text("Anmeldung")
    expect(page.locator(f"{TILE} .a-zeitleiste li")).to_have_count(4)
    _no_side_scroll(page)
    assert run_axe(page) == []

    _all_visible(_stations_to_element(page, PENCIL, steps=steps))
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}{entry.key}/anmeldung/")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    expect_modal(dialog)
    expect(dialog.locator("h2")).to_have_text("Anmeldung bearbeiten")
    _no_side_scroll(page)
    assert run_axe(page) == []
    for name in ("registration_opens", "registration_closes", "changes_close"):
        _all_visible(_stations_to_element(page, f'dialog input[name="{name}"]', steps=10))
    _fristen_eintragen(page, "dialog")
    _all_visible(_stations_to_element(page, SUBMIT, steps=10))
    page.keyboard.press("Enter")

    page.wait_for_url(f"{LIST}{entry.key}/")
    expect(page.locator(".a-kurz")).to_contain_text("Die Fristen von Pfingstlager 2028 sind gespeichert.")
    _zeitleiste(page)
    page.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(page) == []


def test_am_pc_nur_mit_der_tastatur(pc):
    _mit_der_tastatur(pc, steps=30)


def test_am_handy_nur_mit_der_tastatur(handy):
    _mit_der_tastatur(handy, steps=30)


def _ohne_skript(page: Page) -> None:
    login(page)
    _erika_in_den_falken()
    entry = _pfingstlager(creating=True)

    # Schritt 3 beim Anlegen: „Weiter“ speichert die Fristen und führt zur Zusammenfassung.
    page.goto(f"{LIST}{entry.key}/anlegen/anmeldung/")
    expect(page.locator(".a-schritt.ist-jetzt")).to_contain_text("Anmeldung")
    _fristen_eintragen(page, "")
    _no_side_scroll(page)
    page.locator(STEP_SUBMIT).click()
    page.wait_for_url(f"{LIST}{entry.key}/anlegen/zusammenfassung/")
    # Die Zusammenfassung zeigt dieselbe Zeitleiste wie die Kachel der Leitungsseite (Vorschau, 27.11.2026).
    _zeitleiste(page)

    # Der Stift der Kachel öffnet ohne Skript den Dialog als eigene Seite; ein Fehler steht am Feld.
    page.locator(STEP_SUBMIT).click()
    page.wait_for_url(f"{LIST}{entry.key}/")
    page.locator(PENCIL).click()
    page.wait_for_url(f"{LIST}{entry.key}/anmeldung/")
    expect(_dialog(page)).to_be_visible()
    page.locator('dialog input[name="registration_closes"]').fill("")
    page.locator(SUBMIT).click()
    expect(page.locator("dialog .invalid-feedback")).to_have_text("Trag zuerst einen Anmeldeschluss ein.")
    _fristen_eintragen(page, "dialog")
    _no_side_scroll(page)
    page.locator(SUBMIT).click()
    page.wait_for_url(f"{LIST}{entry.key}/")
    expect(page.get_by_text("Die Fristen von Pfingstlager 2028 sind gespeichert.")).to_be_visible()
    _zeitleiste(page)


def test_am_pc_ohne_skript_mit_der_maus(pc_ohne_skript):
    _ohne_skript(pc_ohne_skript)


def test_am_handy_ohne_skript_mit_tippen(handy_ohne_skript):
    _ohne_skript(handy_ohne_skript)
