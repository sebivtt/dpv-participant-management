"""Rauchtest „angezeigte Leitungsrolle“ im Browser (#99): am PC und am Handy, je nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall; die Sippe Falken hat
keine Gruppenleitung, also springt sie dort ein, wie Wanda in den Szenarien. Verwaltet ist Lena Probe „Kiwi“ in
der Sippe Falken. Geprüft werden die Teile, die nur ein Browser zeigt: Die Vorschläge zeigen Lena mit der Marke
„verwaltet“ und dem Satz zur Anzeige, auch wie am Handy mit Autokorrektur; „Benennen“ und „Entfernen“ sind mit
der Tastatur erreichbar, der Dialog ist modal, die kurzen Meldungen erscheinen, nichts steht seitlich über, und
die Seiten bestehen die Prüfung auf Barrierefreiheit. Die Regeln selbst prüft
tests/test_angezeigte_leitungsrollen.py. Alle Namen sind erfunden.
"""

from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import APPOINT_BUTTON
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from rauchtests.test_verwaltete_personen_verschieben import _with_managed

FIELD = "Name, Fahrtenname, Mail oder Benutzername"
HINT = "Kiwi (Lena Probe) hat kein Konto. Die Rolle wird nur angezeigt und gibt keine Rechte."
LEADS = '[aria-labelledby="h-leitungen"]'
PERSONS = '[aria-labelledby="h-personen"]'
REMOVE = f'{LEADS} a[href*="/entfernen-anzeige/"]'


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _appoint_lena(page: Page, units: dict, phone: bool) -> None:
    """Öffnet „Gruppenleitung benennen“ nur mit der Tastatur, tippt Lenas Fahrtennamen und benennt sie."""
    page.goto(f"{BASE}/organisation/{units['falken'].key}/")
    stations = _stations_to_element(page, APPOINT_BUTTON, steps=40)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/benennen/")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    field = page.get_by_label(FIELD)
    if phone:
        # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; die Vorschläge kommen trotzdem.
        _type_like_a_phone(field, "Ki", "w", "wi", "")
        expect(field).to_have_value("Kiwi")
    else:
        page.keyboard.type("Kiw")
    hit = dialog.locator(".a-treffer", has_text="Kiwi")
    expect(hit).to_contain_text("verwaltet")
    expect(hit).to_contain_text(HINT)
    if phone:
        _no_side_scroll(page)
    assert run_axe(page) == []
    stations = _stations_to_element(page, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    assert page.evaluate("document.activeElement.closest('dialog') !== null")
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    expect(page.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) ist jetzt Gruppenleitung von Sippe Falken.")
    expect(page.locator(f"{LEADS} .a-leitung", has_text="Kiwi")).to_contain_text("ohne Konto, nur Anzeige")
    expect(page.locator(f"{PERSONS} .a-leitung", has_text="Kiwi")).to_contain_text(
        "Gruppenleitung Sippe Falken (nur Anzeige)")


def _remove_lena(page: Page, units: dict) -> None:
    """Entfernt Lenas angezeigte Rolle nur mit der Tastatur über „Entfernen“ in der Liste der Leitungen."""
    stations = _stations_to_element(page, REMOVE, steps=60)
    _all_visible(stations)
    page.keyboard.press("Enter")
    dialog = _dialog(page)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Kiwi (Lena Probe) als Gruppenleitung von Sippe Falken entfernen?")
    assert run_axe(page) == []
    stations = _stations_to_element(page, "dialog .btn-gefahr", steps=10)
    _all_visible(stations)
    page.keyboard.press("Enter")
    page.wait_for_url(f"{BASE}/organisation/{units['falken'].key}/")
    expect(page.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) ist nicht mehr Gruppenleitung von Sippe Falken.")
    expect(page.locator(REMOVE)).to_have_count(0)
    expect(page.locator(f"{PERSONS} .a-leitung", has_text="Kiwi")).to_be_visible()


def test_am_pc_nur_mit_der_tastatur_eintragen_und_entfernen(pc):
    login(pc)
    units = _with_managed()

    _appoint_lena(pc, units, phone=False)
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []
    _remove_lena(pc, units)


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    units = _with_managed()

    _appoint_lena(handy, units, phone=True)
    _no_side_scroll(handy)
    _remove_lena(handy, units)
    _no_side_scroll(handy)
