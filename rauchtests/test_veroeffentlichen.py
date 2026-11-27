"""Rauchtest „Veröffentlichen und zurücknehmen“ im Browser (#359, ZG5): am PC und am Handy, je nur mit der Tastatur
und ohne Skript.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an, ist Mitglied der Sippe Falken und leitet das
„Pfingstlager 2028“ als Entwurf, mit Beginn in rund einem halben Jahr, 18:00, und Ende drei Tage später, 12:00.
Die Uhr bleibt die echte, weil Keycloak die Zeit seiner Anmeldung selbst prüft; deshalb liegt der Beginn immer
relativ zu heute in der Zukunft (Befund G5 der unabhängigen Prüfung). Geprüft wird, was nur ein Browser zeigt: Der
Schalter „Veröffentlicht“ (Baustein „Schalter mit Rückfrage“) öffnet mit Leertaste, Enter, Klick oder Tippen die
Rückfrage, auch ohne Skript; Escape schließt sie, ohne dass sich etwas ändert (Z3); nach dem Bestätigen steht die
Marke „Anmeldung offen“ (seit #360 ohne Fristen statt „Angekündigt“) und der Schalter hat wieder den Fokus; nichts steht seitlich über, der Fokus ist zu sehen, und
die Seiten bestehen die Prüfung auf Barrierefreiheit (nur mit Skript: axe läuft selbst als Skript und kommt ohne nie zu
Ende, wie in den übrigen Rauchtests ohne Skript). Die Regeln selbst prüft tests/test_veroeffentlichen.py. Alle
Namen sind erfunden; „Burg Ludwigstein“ stammt aus dem Zielbild (#356).
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
SWITCH = ".a-zustand [role=switch]"
MARK = ".a-zustand .a-kennmarke"
SENTENCE = ".a-zustand .a-zustand-satz"


def _pfingstlager() -> Event:
    erika = get_user_model().objects.get(username="erika.testfrau")
    start = timezone.localdate() + timedelta(days=180)
    found = Event.objects.create(name="Pfingstlager 2028", start=start, start_time=time(18, 0),
                                 end=start + timedelta(days=3), end_time=time(12, 0), location="Burg Ludwigstein")
    found.leads.add(erika)
    return found


def _leitungsseite(page: Page, entry: Event, axe: bool = True) -> None:
    page.goto(f"{LIST}{entry.key}/")
    expect(page.locator(MARK)).to_have_text("Entwurf")
    expect(page.locator(SENTENCE)).to_have_text("Nur die Leitung sieht die Veranstaltung.")
    switch = page.get_by_role("switch", name="Veröffentlicht")
    expect(switch).to_have_attribute("aria-checked", "false")
    _no_side_scroll(page)
    if axe:
        assert run_axe(page) == []


def _rueckfrage(page: Page, entry: Event, title: str, path: str, axe: bool = True) -> None:
    page.wait_for_url(f"{LIST}{entry.key}/{path}/")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    expect(dialog.locator("h2")).to_have_text(title)
    _no_side_scroll(page)
    if axe:
        assert run_axe(page) == []


def _angekuendigt(page: Page, entry: Event, axe: bool = True) -> None:
    page.wait_for_url(f"{LIST}{entry.key}/*")
    # Ohne Skript bleibt die kurze Meldung fest oben stehen (#186); deshalb nach dem Text, nicht nach dem Bereich.
    expect(page.get_by_text("Pfingstlager 2028 ist veröffentlicht.")).to_be_visible()
    # Seit #360 ist sie ohne Fristen gleich „Anmeldung offen“, bis zum Beginn.
    expect(page.locator(MARK)).to_have_text("Anmeldung offen")
    expect(page.locator(SENTENCE)).to_have_text(
        "Die Veranstaltung ist veröffentlicht. Die Anmeldung läuft bis zum Beginn.")
    expect(page.get_by_role("switch", name="Veröffentlicht")).to_have_attribute("aria-checked", "true")
    _no_side_scroll(page)
    if axe:
        page.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
        assert run_axe(page) == []


def _nur_mit_der_tastatur(page: Page, key: str) -> None:
    login(page)
    _erika_in_den_falken()
    entry = _pfingstlager()
    _leitungsseite(page, entry)

    # Z3: Rückfrage öffnen und mit Escape schließen; es bleibt ein Entwurf, der Schalter hat wieder den Fokus.
    _all_visible(_stations_to_element(page, SWITCH, steps=30))
    page.keyboard.press(key)
    _rueckfrage(page, entry, "Pfingstlager 2028 veröffentlichen?", "veroeffentlichen")
    expect_modal(_dialog(page))
    page.keyboard.press("Escape")
    page.wait_for_url(f"{LIST}{entry.key}/*")
    expect(page.locator(MARK)).to_have_text("Entwurf")
    expect(page.locator(SWITCH)).to_be_focused()

    # Z2: erneut öffnen und mit „Veröffentlichen“ bestätigen.
    page.keyboard.press(key)
    _rueckfrage(page, entry, "Pfingstlager 2028 veröffentlichen?", "veroeffentlichen")
    expect_modal(_dialog(page))
    _all_visible(_stations_to_element(page, "dialog .a-dialog-fuss button[type=submit]", steps=6))
    page.keyboard.press("Enter")
    _angekuendigt(page, entry)
    expect(page.locator(SWITCH)).to_be_focused()

    # Z4: zurücknehmen mit dem roten Knopf.
    page.keyboard.press(key)
    _rueckfrage(page, entry, "Veröffentlichung von Pfingstlager 2028 zurücknehmen?", "zuruecknehmen")
    expect_modal(_dialog(page))
    _all_visible(_stations_to_element(page, "dialog .a-dialog-fuss button[type=submit]", steps=6))
    page.keyboard.press("Enter")
    page.wait_for_url(f"{LIST}{entry.key}/*")
    expect(page.locator(".a-kurz")).to_contain_text("Die Veröffentlichung von Pfingstlager 2028 ist zurückgenommen.")
    expect(page.locator(MARK)).to_have_text("Entwurf")


def test_am_pc_nur_mit_der_tastatur_veroeffentlichen_und_zuruecknehmen(pc):
    _nur_mit_der_tastatur(pc, "Space")


def test_am_handy_nur_mit_der_tastatur_veroeffentlichen_und_zuruecknehmen(handy):
    _nur_mit_der_tastatur(handy, "Enter")


def _ohne_skript(page: Page) -> None:
    login(page)
    _erika_in_den_falken()
    entry = _pfingstlager()
    _leitungsseite(page, entry, axe=False)

    page.get_by_role("switch", name="Veröffentlicht").click()
    _rueckfrage(page, entry, "Pfingstlager 2028 veröffentlichen?", "veroeffentlichen", axe=False)
    page.get_by_role("link", name="Abbrechen").click()
    page.wait_for_url(f"{LIST}{entry.key}/*")
    expect(page.locator(MARK)).to_have_text("Entwurf")

    page.get_by_role("switch", name="Veröffentlicht").click()
    _rueckfrage(page, entry, "Pfingstlager 2028 veröffentlichen?", "veroeffentlichen", axe=False)
    page.get_by_role("button", name="Veröffentlichen").click()
    _angekuendigt(page, entry, axe=False)

    page.goto(LIST)
    row = page.locator(".a-va-zeile", has_text="Pfingstlager 2028")
    expect(row.locator(".a-kennmarke")).to_have_text("Anmeldung offen")
    _no_side_scroll(page)


def test_am_pc_ohne_skript_mit_der_maus(pc_ohne_skript):
    _ohne_skript(pc_ohne_skript)


def test_am_handy_ohne_skript_mit_tippen(handy_ohne_skript):
    _ohne_skript(handy_ohne_skript)
