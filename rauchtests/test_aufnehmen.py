"""Rauchtest „Personen“ und „Person aufnehmen“ im Browser (#285): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall, wie Wanda in
den Szenarien. Geprüft werden die Teile, die nur ein Browser zeigt: Der Abschnitt „Personen“ steht da,
der Dialog ist modal und hält den Fokus, die Suche geht auch wie am Handy mit Autokorrektur, die kurze
Meldung erscheint, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die
Prüfung auf Barrierefreiheit. Die Regeln selbst prüft tests/test_personen.py. Alle Namen sind erfunden.
"""

from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone

PERSONS = '[aria-labelledby="h-personen"]'
# Seit #117 steht daneben „Verwaltete Person anlegen“; gemeint ist der Knopf, der zum Aufnehmen führt.
ADMIT_BUTTON = f'{PERSONS} .a-flaeche-aktion[href$="/aufnehmen/"]'


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_aufnehmen(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['walhall'].key}/"
    pc.goto(page_address)
    expect(pc.locator(PERSONS)).to_contain_text("1 Person")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ADMIT_BUTTON, steps=60)
    _all_visible(stations)
    expect(pc.locator(ADMIT_BUTTON)).to_have_text("Person mit Konto aufnehmen")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{page_address}aufnehmen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Person mit Konto aufnehmen")
    expect(dialog).to_contain_text("Die Person muss sich schon einmal im Tool angemeldet haben.")
    field = pc.get_by_label("Mail oder Benutzername")
    expect(field).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("otto.ohne@example.org")
    pc.keyboard.press("Enter")
    expect(dialog.locator(".a-treffer")).to_contain_text("Otto Ohne")
    stations = _stations_to_element(pc, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    assert pc.evaluate("document.activeElement.closest('dialog') !== null")
    pc.keyboard.press("Enter")

    pc.wait_for_url(page_address)
    expect(pc.locator(".a-kurz")).to_contain_text("Otto Ohne gehört jetzt zu Stamm Walhall.")
    expect(pc.locator(PERSONS)).to_contain_text("Otto Ohne")
    expect(pc.locator(PERSONS)).to_contain_text("2 Personen")
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []


def test_am_pc_escape_fuehrt_zurueck_und_nimmt_niemanden_auf(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['walhall'].key}/"

    pc.goto(f"{page_address}aufnehmen/")
    expect(_dialog(pc)).to_be_visible()
    pc.keyboard.press("Escape")
    pc.wait_for_url(page_address)
    expect(_dialog(pc)).to_have_count(0)
    expect(pc.locator(PERSONS)).not_to_contain_text("Otto")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['walhall'].key}/"
    handy.goto(page_address)
    _no_side_scroll(handy)
    expect(handy.locator(ADMIT_BUTTON)).to_be_visible()

    stations = _stations_to_element(handy, ADMIT_BUTTON, steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{page_address}aufnehmen/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    field = handy.get_by_label("Mail oder Benutzername")
    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; gesucht wird der ganze Benutzername.
    _type_like_a_phone(field, "otto", ".ohn", ".ohne", "")
    expect(field).to_have_value("otto.ohne")
    handy.keyboard.press("Enter")
    expect(dialog.locator(".a-treffer")).to_contain_text("Otto Ohne")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, ".a-treffer-knopf button", steps=10)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(page_address)
    expect(handy.locator(".a-kurz")).to_contain_text("Otto Ohne gehört jetzt zu Stamm Walhall.")
    _no_side_scroll(handy)
