"""Rauchtest „Leitung entfernen“ und „Rolle abgeben“ im Browser (#191): am PC und am Handy, nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien; Fiete ist Gruppenleitung der Falken. Geprüft werden die Teile, die nur ein Browser
zeigt: Der Knopf ist mit der Tastatur erreichbar, die Bestätigung ist modal und hält den Fokus,
Escape führt ohne Änderung zurück, die kurze Meldung erscheint, nichts steht seitlich über, und die
Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_entfernen.py.
Alle Namen sind erfunden.
"""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element
from roles.models import Role
from tests.test_rollen import give, person, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind


def _walhall_for_erika() -> dict:
    """Boreas mit Walhall und Sippe Falken; Erika leitet Walhall, Fiete („Funke“) die Falken."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    falken = unit(U.GROUP, "Sippe Falken", walhall)
    give(erika, R.TROOP_LEAD, walhall)
    fiete = person("fiete.falke", "Fiete", "Falke")
    fiete.scout_name = "Funke"
    fiete.save()
    give(fiete, R.GROUP_LEAD, falken)
    return {"walhall": walhall, "falken": falken, "fiete": fiete}


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_entfernen(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    pc.goto(page_address)
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ".a-leitung-knopf", steps=40)
    _all_visible(stations)
    expect(pc.locator(".a-leitung-knopf")).to_have_text("Entfernen: Funke")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{page_address}entfernen/**")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Funke (Fiete Falke) als Gruppenleitung von Sippe Falken entfernen?")
    expect(dialog).to_contain_text("springt die Leitung von Stamm Walhall ein. Trotzdem entfernen?")
    assert run_axe(pc) == []

    # Der Fokus bleibt im Dialog: Tab geht nie auf die Seite darunter.
    stations = _stations_to_element(pc, ".btn-gefahr", steps=10)
    _all_visible(stations)
    assert pc.evaluate("document.activeElement.closest('dialog') !== null")
    pc.keyboard.press("Enter")

    pc.wait_for_url(page_address)
    expect(pc.locator(".a-kurz")).to_contain_text("Funke (Fiete Falke) ist nicht mehr Gruppenleitung von Sippe Falken.")
    expect(pc.locator(".a-leitungen")).to_have_count(0)
    expect(pc.locator(".a-orga-kopf")).to_contain_text("Du springst ein")
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_escape_aendert_nichts(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    pc.goto(page_address)

    pc.locator(".a-leitung-knopf").click()
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")

    pc.wait_for_url(page_address)
    expect(_dialog(pc)).to_have_count(0)
    expect(pc.locator(".a-leitung")).to_contain_text("Funke")


def test_am_handy_gibt_erika_ihre_rolle_ab(handy):
    login(handy)
    units = _walhall_for_erika()
    handy.goto(f"{BASE}/organisation/{units['walhall'].key}/")
    _no_side_scroll(handy)
    expect(handy.locator(".a-leitung-knopf")).to_be_visible()
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, ".a-leitung-knopf", steps=40)
    _all_visible(stations)
    expect(handy.locator(".a-leitung-knopf")).to_contain_text("Rolle abgeben")
    handy.keyboard.press("Enter")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    expect(dialog.locator("h2")).to_have_text("Deine Rolle als Stammesleitung von Walhall abgeben?")
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, ".btn-gefahr", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")

    handy.wait_for_url(f"{BASE}/profil/")
    expect(handy.locator(".a-kurz")).to_contain_text("Du bist nicht mehr Stammesleitung von Walhall.")
    _no_side_scroll(handy)
