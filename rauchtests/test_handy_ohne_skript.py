"""Rauchtest: am Handy ohne Skript über „Menü“ ans Seitenende, dort Seite wechseln und abmelden (#281, NFA-01).

Die Kennungen E1 bis G1 verweisen auf den Kommentar „Szenarien (06.11.2026)“ im Issue #281. Was die
Seite vom Server mitbringt und wer welchen Punkt sieht (V1, G2), prüft tests/test_handy_ohne_skript.py.
Erika meldet sich wirklich bei der Keycloak-Testumgebung an und bekommt danach die Stammesleitung von
Walhall. Alle Namen sind erfunden.
"""

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page, Route, expect

from rauchtests.conftest import BASE, PC, _context, login, run_axe
from rauchtests.test_abmelden import FINISH_BUTTON, _logged_out_hint
from rauchtests.test_rauchtest import _all_visible, _on_login_page, _password_requested_again, _tab_to
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

pytestmark = pytest.mark.django_db(transaction=True)

SCRIPT = "**/core/app.js"


def _erika_leads_walhall() -> None:
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(Unit.Kind.FEDERATION, "DPV")
    boreas = unit(Unit.Kind.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    give(erika, Role.Kind.TROOP_LEAD, unit(Unit.Kind.TROOP, "Walhall", boreas))


def _bottom(page: Page):
    return page.locator("#menue-unten")


def _jump_down(page: Page) -> None:
    """Tippt „Menü“ an; ohne Skript ist das ein Sprung ans Seitenende zur Liste."""
    page.get_by_role("link", name="Menü").tap()
    expect(_bottom(page)).to_be_in_viewport()
    page.wait_for_url("**#menue-unten")


def _change_page_and_log_out(page: Page) -> None:
    """E1 und E2: über die Liste zu „Organisation“, dann über die Liste abmelden."""
    login(page)
    _erika_leads_walhall()
    page.reload()

    _jump_down(page)
    bottom = _bottom(page)
    expect(bottom.get_by_role("link", name="Mein Profil")).to_be_visible()
    bottom.get_by_role("link", name="Organisation").tap()
    page.wait_for_url(f"{BASE}/organisation/**")
    expect(page.locator(".a-orga-name")).to_have_text("Walhall")

    _jump_down(page)
    _bottom(page).get_by_role("button", name="Abmelden").tap()
    page.wait_for_url(f"{BASE}/abmelden/")
    page.get_by_role("button", name=FINISH_BUTTON).tap()

    _on_login_page(page)
    expect(_logged_out_hint(page)).to_be_visible()
    _password_requested_again(page)


# E1 und E2: Skript abgeschaltet
def test_e1_e2_ohne_skript_seite_wechseln_und_abmelden(handy_ohne_skript):
    _change_page_and_log_out(handy_ohne_skript)


# E1 und E2 nur mit der Tastatur: „Menü“ mit Enter, der nächste Tab landet in der Liste, dort abmelden
def test_e1_e2_ohne_skript_nur_mit_der_tastatur(handy_ohne_skript):
    page = handy_ohne_skript
    login(page)

    stations = _tab_to(page, "Menü")
    page.keyboard.press("Enter")
    page.wait_for_url("**#menue-unten")
    stations += _tab_to(page, "Startseite", steps=1)
    assert page.evaluate("document.getElementById('menue-unten').contains(document.activeElement)")
    stations += _tab_to(page, "Abmelden", steps=5)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/abmelden/")
    stations += _tab_to(page, FINISH_BUTTON)
    _all_visible(stations)
    page.keyboard.press("Enter")

    _on_login_page(page)
    _password_requested_again(page)


# E3: Skript erlaubt, kommt aber nicht an
def test_e3_skript_kommt_nicht_an_seite_wechseln_und_abmelden(handy):
    handy.route(SCRIPT, lambda route: route.abort())
    _change_page_and_log_out(handy)


# E3: Auch mit sichtbarer Liste besteht die Seite die Prüfung auf Barrierefreiheit (axe kommt nicht über das Netz).
def test_e3_liste_besteht_die_pruefung_auf_barrierefreiheit(handy):
    login(handy)
    handy.route(SCRIPT, lambda route: route.abort())
    handy.goto(f"{BASE}/")
    _jump_down(handy)

    assert run_axe(handy) == []


# G1: Das Skript kommt erst nach dem Sprung; dann verschwindet die Liste, und „Menü“ öffnet das Menü von links.
def test_g1_skript_kommt_spaet_liste_verschwindet_und_menue_oeffnet(handy):
    login(handy)
    held: list[Route] = []
    handy.route(SCRIPT, held.append)
    handy.goto(f"{BASE}/", wait_until="commit")
    expect(handy.get_by_role("link", name="Menü")).to_be_visible()
    _jump_down(handy)
    assert held, "das Skript wurde nicht angefragt"

    held[0].continue_()

    expect(_bottom(handy)).to_have_count(0)
    expect(handy.get_by_role("link", name="Menü")).to_have_count(0)
    handy.get_by_role("button", name="Menü").tap()
    expect(handy.get_by_role("dialog", name="Menü")).to_be_visible()


# E4: Mit Skript gibt es die Liste nicht, weder zu sehen noch mit der Tastatur; „Menü“ ist der Knopf wie bisher.
def test_e4_mit_skript_keine_liste_und_menue_ist_der_knopf(handy):
    login(handy)

    expect(handy.get_by_role("button", name="Menü")).to_be_visible()
    expect(handy.get_by_role("link", name="Menü")).to_have_count(0)
    expect(_bottom(handy)).to_have_count(0)


# E5: Am PC keine Liste, mit und ohne Skript
def test_e5_am_pc_keine_liste_mit_und_ohne_skript(pc, browser, browser_name):
    login(pc)
    expect(_bottom(pc)).to_have_count(0)

    context = _context(browser, browser_name, PC, java_script_enabled=False, storage_state=pc.context.storage_state())
    page = context.new_page()
    page.goto(f"{BASE}/")
    expect(page.get_by_role("complementary", name="Seitenleiste")).to_be_visible()
    expect(_bottom(page)).to_be_hidden()
    expect(page.get_by_role("link", name="Menü")).to_be_hidden()
    context.close()
