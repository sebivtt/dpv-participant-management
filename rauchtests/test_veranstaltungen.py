"""Rauchtest „Veranstaltungen“ im Browser (#100, VG10): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und ist danach Mitglied der Sippe Falken, hat
also eine Zuordnung (VA-01). Geprüft werden die Teile, die nur ein Browser zeigt: der Punkt
„Veranstaltungen“ in der Seitenleiste und im Menü, „Veranstaltung erstellen“ als Dialog, der den Fokus
hält, Beginn und Ende als Baustein „Datumsfeld“ (das Feld des Browsers, N3 zu #117), der Name auch wie am
Handy mit Autokorrektur und Wortvorschlägen, die kurze Meldung, der Stift zum Bearbeiten, nichts steht
seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die Prüfung auf Barrierefreiheit. Das Datum
setzt der Test mit `fill`, weil jeder Browser sein Datumsfeld anders bedienen lässt; erreicht wird das
Feld mit der Tastatur. Die Regeln selbst prüft tests/test_veranstaltungen.py. Alle Namen sind erfunden.
"""

from django.contrib.auth import get_user_model
from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone
from roles.models import Role
from tests.test_rollen import give, unit
from units.models import Unit

R = Role.Kind
U = Unit.Kind
LIST = f"{BASE}/veranstaltungen/"
NAV_LINK = '.a-sidebar .a-navlink[href="/veranstaltungen/"]'
CREATE_BUTTON = '[aria-labelledby="h-veranstaltungen"] .a-flaeche-aktion[href="/veranstaltungen/erstellen/"]'
PENCIL = ".a-stift"
SUBMIT = 'dialog button[type="submit"]'
CREATED = "Probelager 2027 ist angelegt. Du leitest diese Veranstaltung."


def _erika_in_den_falken() -> None:
    """Erika wird Mitglied der Sippe Falken und hat damit eine Zuordnung (BER-03)."""
    erika = get_user_model().objects.get(username="erika.testfrau")
    dpv = unit(U.FEDERATION, "DPV")
    boreas = unit(U.ASSOCIATION, "Pfadfinderbund Boreas", dpv)
    walhall = unit(U.TROOP, "Walhall", boreas)
    give(erika, R.MEMBER, unit(U.GROUP, "Sippe Falken", walhall))


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def test_am_pc_nur_mit_der_tastatur_erstellen_und_bearbeiten(pc):
    login(pc)
    _erika_in_den_falken()
    pc.goto(f"{BASE}/")

    stations = _stations_to_element(pc, NAV_LINK, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    pc.wait_for_url(LIST)
    expect(pc.locator('[aria-labelledby="h-veranstaltungen"]')).to_contain_text("Du leitest noch keine Veranstaltung.")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, CREATE_BUTTON, steps=20)
    _all_visible(stations)
    expect(pc.locator(CREATE_BUTTON)).to_have_text("Veranstaltung erstellen")
    pc.keyboard.press("Enter")
    pc.wait_for_url(f"{LIST}erstellen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Veranstaltung erstellen")
    name = pc.get_by_label("Name")
    expect(name).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("Probelager 2027")
    pc.keyboard.press("Tab")
    start = pc.get_by_label("Beginn")
    expect(start).to_be_focused()
    assert start.get_attribute("type") == "date"
    start.fill("2027-05-15")
    stations = _stations_to_element(pc, 'input[name="end"]', steps=6)
    _all_visible(stations)
    end = pc.get_by_label("Ende")
    assert end.get_attribute("type") == "date"
    end.fill("2027-05-17")
    stations = _stations_to_element(pc, SUBMIT, steps=6)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{LIST}*/")
    expect(pc.locator(".a-kurz")).to_contain_text(CREATED)
    expect(pc.locator("h1")).to_have_text("Probelager 2027")
    expect(pc.locator("main")).to_contain_text("15.05.2027 bis 17.05.2027")
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, PENCIL, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Probelager 2027 bearbeiten")
    expect(pc.get_by_label("Name")).to_be_focused()
    pc.get_by_label("Ende").fill("2027-05-18")
    stations = _stations_to_element(pc, SUBMIT, steps=6)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(pc.locator(".a-kurz")).to_contain_text("Die Angaben zu Probelager 2027 sind gespeichert.")
    expect(pc.locator("main")).to_contain_text("15.05.2027 bis 18.05.2027")


def test_am_pc_fehler_am_feld_kommen_vom_tool(pc):
    login(pc)
    _erika_in_den_falken()
    pc.goto(f"{LIST}erstellen/")
    pc.get_by_label("Beginn").fill("2027-05-17")
    pc.get_by_label("Ende").fill("2027-05-15")
    # Der Browser hält das leere Pflichtfeld nicht selbst an; die Meldungen kommen vom Tool.
    pc.get_by_role("button", name="Anlegen").click()
    expect(_dialog(pc)).to_contain_text("Bitte gib den Namen ein.")
    expect(_dialog(pc)).to_contain_text("Das Ende liegt vor dem Beginn.")
    expect(pc.get_by_label("Name")).to_have_attribute("aria-invalid", "true")
    expect(pc.get_by_label("Ende")).to_have_accessible_description("Das Ende liegt vor dem Beginn.")
    expect(pc.get_by_label("Beginn")).to_have_value("2027-05-17")
    assert run_axe(pc) == []

    pc.keyboard.press("Escape")
    pc.wait_for_url(LIST)
    expect(pc.locator("main")).to_contain_text("Du leitest noch keine Veranstaltung.")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    _erika_in_den_falken()
    handy.goto(LIST)
    _no_side_scroll(handy)
    expect(handy.locator(CREATE_BUTTON)).to_be_visible()
    assert run_axe(handy) == []

    stations = _stations_to_element(handy, CREATE_BUTTON, steps=30)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}erstellen/")
    expect(_dialog(handy)).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    # Wie am Handy: ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
    name = handy.get_by_label("Name")
    _type_like_a_phone(name, "Probe", "l", "lager", " 2027")
    expect(name).to_have_value("Probelager 2027")
    handy.get_by_label("Beginn").fill("2027-05-15")
    handy.get_by_label("Ende").fill("2027-05-17")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, SUBMIT, steps=6)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{LIST}*/")
    expect(handy.locator(".a-kurz")).to_contain_text(CREATED)
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    handy.goto(LIST)
    expect(handy.locator(".a-orgakachel")).to_contain_text("Probelager 2027")
    _no_side_scroll(handy)
