"""Rauchtest „Verwaltete Person anlegen“ und „… bearbeiten“ im Browser (#117): am PC und am Handy, je einmal nur mit der Tastatur.

Erika meldet sich wirklich bei der Keycloak-Testumgebung an und leitet danach Walhall; die Sippe Falken hat
keine Gruppenleitung, also springt sie dort ein und darf anlegen (VP-01, EH-18), wie Wanda in M3.
Geprüft werden die Teile, die nur ein Browser zeigt: Der Dialog ist modal und hält den Fokus, nach dem
Dialog kehrt der Fokus auf den Knopf zurück, der ihn geöffnet hat, der Regler der Einwilligung geht
mit Tab und Leertaste und am Handy mit Antippen (#98, EG5), die Felder gehen auch wie am Handy
mit Autokorrektur und Wortvorschlägen (MG10), das Datumsfeld ist das Feld des Browsers (N3), die kurze
Meldung erscheint, nichts steht seitlich über, der Fokus ist zu sehen, und die Seiten bestehen die
Prüfung auf Barrierefreiheit. Das Datum setzt der Test mit `fill`, weil jeder Browser sein Datumsfeld
anders bedienen lässt; erreicht wird das Feld mit der Tastatur. Die Regeln selbst prüft
tests/test_verwaltete_personen.py. Alle Namen sind erfunden.
"""

from playwright.sync_api import Page, expect

from rauchtests.conftest import BASE, login, run_axe
from rauchtests.test_benennen import _walhall_for_erika
from rauchtests.test_organisation import _no_side_scroll
from rauchtests.test_rauchtest import _all_visible, _stations_to_element, _type_like_a_phone

PERSONS = '[aria-labelledby="h-personen"]'
ADD_BUTTON = f'{PERSONS} .a-flaeche-aktion[href$="/verwaltete-person/anlegen/"]'
EDIT_BUTTON = f'{PERSONS} a[href$="/bearbeiten/"]'
# Der Regler der Einwilligung (#98, DSG-02): ein Ankreuzfeld im Baustein „Schalter“.
CONSENT = 'dialog input[name="consent"]'
SUBMIT = 'dialog button[type="submit"]'


def _dialog(page: Page):
    return page.locator("dialog.a-dialog")


def _focused_matches(page: Page, selector: str) -> bool:
    return page.evaluate("s => document.activeElement.matches(s)", selector)


def test_am_pc_nur_mit_der_tastatur_anlegen_und_bearbeiten(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    pc.goto(page_address)
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, ADD_BUTTON, steps=60)
    _all_visible(stations)
    expect(pc.locator(ADD_BUTTON)).to_have_text("Verwaltete Person anlegen")
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{page_address}verwaltete-person/anlegen/")
    dialog = _dialog(pc)
    expect(dialog).to_be_visible()
    assert dialog.evaluate("d => d.matches(':modal')")
    expect(dialog.locator("h2")).to_have_text("Verwaltete Person anlegen")
    expect(pc.get_by_label("Vorname")).to_be_focused()
    assert run_axe(pc) == []

    pc.keyboard.type("Lena")
    pc.keyboard.press("Tab")
    expect(pc.get_by_label("Nachname")).to_be_focused()
    pc.keyboard.type("Probe")
    pc.keyboard.press("Tab")
    birth = pc.get_by_label("Geburtsdatum")
    expect(birth).to_be_focused()
    assert birth.get_attribute("type") == "date"
    birth.fill("2015-05-14")
    stations = _stations_to_element(pc, 'input[name="scout_name"]', steps=6)
    _all_visible(stations)
    pc.keyboard.type("Kiwi")
    # Nur mit der Tastatur zum Regler und mit der Leertaste auf „an“ (#98, EG5); er wirkt erst mit „Anlegen“.
    stations = _stations_to_element(pc, CONSENT, steps=4)
    _all_visible(stations)
    consent = pc.locator(CONSENT)
    expect(consent).not_to_be_checked()
    expect(pc.get_by_role("checkbox", name="Die Person bzw. bei Minderjährigen die Erziehungsberechtigten "
                                            "haben der Speicherung der Daten zugestimmt.")).to_have_count(1)
    pc.keyboard.press("Space")
    expect(consent).to_be_checked()
    stations = _stations_to_element(pc, SUBMIT, steps=4)
    _all_visible(stations)
    pc.keyboard.press("Enter")

    pc.wait_for_url(f"{page_address}#verwaltete-person-anlegen")
    expect(pc.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) gehört jetzt zu Sippe Falken.")
    expect(pc.locator(PERSONS)).to_contain_text("Kiwi")
    expect(pc.locator(PERSONS)).to_contain_text("verwaltet")
    # Der Fokus kehrt auf den Knopf zurück, der den Dialog geöffnet hat.
    assert _focused_matches(pc, ADD_BUTTON)
    pc.wait_for_function("() => document.getAnimations().every(animation => animation.playState !== 'running')")
    assert run_axe(pc) == []

    stations = _stations_to_element(pc, EDIT_BUTTON, steps=20)
    _all_visible(stations)
    pc.keyboard.press("Enter")
    expect(_dialog(pc).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")
    expect(pc.get_by_label("Vorname")).to_be_focused()
    assert pc.evaluate("document.activeElement.closest('dialog') !== null")
    pc.keyboard.press("Escape")
    expect(_dialog(pc)).to_have_count(0)
    assert _focused_matches(pc, EDIT_BUTTON)

    pc.keyboard.press("Enter")
    first = pc.get_by_label("Vorname")
    expect(first).to_be_focused()
    first.fill("Lenchen")
    pc.keyboard.press("Enter")
    expect(pc.locator(".a-kurz")).to_contain_text("Die Angaben zu Kiwi (Lenchen Probe) sind gespeichert.")
    assert _focused_matches(pc, EDIT_BUTTON)


def test_am_pc_fehler_am_feld_und_escape_legt_niemanden_an(pc):
    login(pc)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"

    pc.goto(f"{page_address}verwaltete-person/anlegen/")
    pc.get_by_label("Fahrtenname").fill("Kiwi")
    # Der Browser hält das leere Pflichtfeld nicht selbst an; die Meldung kommt vom Tool (MG1, unabhängige Prüfung, Befund 1).
    pc.get_by_role("button", name="Anlegen").click()
    expect(_dialog(pc)).to_contain_text("Bitte gib den Vornamen ein.")
    expect(pc.get_by_label("Vorname")).to_have_attribute("aria-invalid", "true")
    expect(pc.get_by_label("Fahrtenname")).to_have_value("Kiwi")
    # Ohne Bestätigung steht der Fehler rot unter dem Regler und ist mit ihm verbunden (#98, EV1, EG5).
    consent = pc.locator(CONSENT)
    expect(consent).to_have_attribute("aria-invalid", "true")
    expect(consent).to_have_accessible_description(
        "Bitte bestätige die Einwilligung. Ohne sie wird die Person nicht gespeichert.")
    assert run_axe(pc) == []

    pc.keyboard.press("Escape")
    pc.wait_for_url(f"{page_address}#verwaltete-person-anlegen")
    expect(pc.locator(PERSONS)).not_to_contain_text("Kiwi")


def test_am_handy_nur_mit_der_tastatur_und_mit_autokorrektur(handy):
    login(handy)
    units = _walhall_for_erika()
    page_address = f"{BASE}/organisation/{units['falken'].key}/"
    handy.goto(page_address)
    _no_side_scroll(handy)
    expect(handy.locator(ADD_BUTTON)).to_be_visible()

    stations = _stations_to_element(handy, ADD_BUTTON, steps=60)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{page_address}verwaltete-person/anlegen/")
    dialog = _dialog(handy)
    expect(dialog).to_be_visible()
    _no_side_scroll(handy)
    assert run_axe(handy) == []

    # Wie am Handy (MG10): ein Wort als Zusammensetzung, ersetzt per Wortvorschlag; nichts verschwindet.
    first = handy.get_by_label("Vorname")
    _type_like_a_phone(first, "Le", "n", "na", "")
    expect(first).to_have_value("Lena")
    last = handy.get_by_label("Nachname")
    _type_like_a_phone(last, "Pro", "b", "be", "")
    expect(last).to_have_value("Probe")
    handy.get_by_label("Geburtsdatum").fill("2015-05-14")
    scout = handy.get_by_label("Fahrtenname")
    _type_like_a_phone(scout, "Ki", "w", "wi", "")
    expect(scout).to_have_value("Kiwi")
    _no_side_scroll(handy)
    # Am Handy lässt sich der Regler antippen (#98, EG5).
    consent = handy.locator(CONSENT)
    expect(consent).not_to_be_checked()
    handy.locator("dialog .a-schalter").tap()
    expect(consent).to_be_checked()
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, SUBMIT, steps=6)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    handy.wait_for_url(f"{page_address}#verwaltete-person-anlegen")
    expect(handy.locator(".a-kurz")).to_contain_text("Kiwi (Lena Probe) gehört jetzt zu Sippe Falken.")
    expect(handy.locator(PERSONS)).to_contain_text("Kiwi")
    _no_side_scroll(handy)

    stations = _stations_to_element(handy, EDIT_BUTTON, steps=20)
    _all_visible(stations)
    handy.keyboard.press("Enter")
    expect(_dialog(handy).locator("h2")).to_have_text("Kiwi (Lena Probe) bearbeiten")
    expect(handy.get_by_label("Fahrtenname")).to_have_value("Kiwi")
    _no_side_scroll(handy)
    assert run_axe(handy) == []
